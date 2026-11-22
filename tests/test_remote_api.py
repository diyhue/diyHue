"""End-to-end tests for the Hue Essentials remote API relay.

App  --HTTP-->  RemoteApi/remoteApiServer.py  <--long poll--  services/remoteApi.py  --HTTP-->  fake local bridge
"""
import base64
import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys
from socketserver import ThreadingMixIn
from threading import Thread
from time import sleep
import unittest
from unittest.mock import patch

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "BridgeEmulator"))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from services import remoteApi  # noqa: E402

_spec = importlib.util.spec_from_file_location("remoteApiServer", ROOT / "RemoteApi" / "remoteApiServer.py")
relay = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(relay)

APP_KEY = "valid-hue-application-key"
LIGHT_ID = "3f1c1b8e-0000-4000-8000-000000000001"


class Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class FakeBridge(BaseHTTPRequestHandler):
    """Tiny stand-in for the diyHue Flask API."""
    protocol_version = "HTTP/1.1"
    deleted = []

    def log_message(self, *args):
        pass

    def _reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length)) if length else None

    def _v2(self, method):
        if self.headers.get("hue-application-key") != APP_KEY:
            self._reply(403, {"errors": [{"description": "unauthorized user"}], "data": []})
            return
        if method == "GET":
            sleep(0.2)  # make concurrent requests overlap
            self._reply(200, {"errors": [], "data": [{"id": LIGHT_ID, "type": "light"}]})
        elif method == "PUT":
            self._reply(200, {"errors": [], "data": [{"rid": LIGHT_ID, "rtype": "light", "echo": self._body()}]})
        elif method == "DELETE":
            FakeBridge.deleted.append(self.path)
            self._reply(200, {"errors": [], "data": [{"rid": "x", "rtype": "scene"}]})

    def do_GET(self):
        if self.path.startswith("/clip/v2/"):
            self._v2("GET")
        elif self.path == "/api/user/lights":
            self._reply(200, {"1": {"name": "Lamp"}})
        else:
            self._reply(404, {"error": "not found"})

    def do_PUT(self):
        if self.path.startswith("/clip/v2/"):
            self._v2("PUT")
        else:
            self._reply(200, [{"success": self._body()}])

    def do_DELETE(self):
        self._v2("DELETE")

    def do_POST(self):
        self._reply(200, [{"success": self._body()}])


class RelayHandler(relay.S):
    """nginx in production adds X-Forwarded-Host; do it here."""
    def parse_request(self):
        ok = super().parse_request()
        if ok and "X-Forwarded-Host" not in self.headers:
            self.headers["X-Forwarded-Host"] = relay.REMOTE_HOST
        return ok


def start(handler):
    server = Server(("127.0.0.1", 0), handler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server


def legacy_client(remote_url, local_base, key):
    """The bridge client shipped before remote API v2 (behaviour copy)."""
    enc = base64.urlsafe_b64encode(key.encode()).decode()
    while True:
        r = requests.get(remote_url + "?apikey=" + enc, timeout=35)
        if r.status_code == 200 and r.text != "{renew}":
            data = json.loads(r.text)
            if data["method"] == "GET":
                b = requests.get(local_base + "/" + data["address"], timeout=5)
            elif data["method"] == "POST":
                b = requests.post(local_base + "/" + data["address"], json=data["body"], timeout=5)
            elif data["method"] == "PUT":
                b = requests.put(local_base + "/" + data["address"], json=data["body"], timeout=5)
            requests.post(remote_url + "?apikey=" + enc, timeout=5, json=json.loads(b.text))


class RemoteApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = start(FakeBridge)
        cls.relay = start(RelayHandler)
        cls.relay_url = f"http://127.0.0.1:{cls.relay.server_address[1]}"
        cls.remote_url = cls.relay_url + "/devices"
        cls.local_base = f"http://127.0.0.1:{cls.bridge.server_address[1]}"

        cls.v2_key = "v2bridgekey000000000000000000001"
        cls.patcher = patch.object(remoteApi, "REMOTE_URL", cls.remote_url)
        cls.patcher.start()
        config = {"Remote API enabled": True, "Hue Essentials key": cls.v2_key}
        Thread(target=remoteApi.runRemoteApi, args=["127.0.0.1", config, cls.bridge.server_address[1]],
               daemon=True).start()

        cls.legacy_key = "legacybridgekey00000000000000002"
        Thread(target=legacy_client, args=[cls.remote_url, cls.local_base, cls.legacy_key], daemon=True).start()

        for _ in range(50):
            if relay.get_bridge(cls.v2_key) and relay.get_bridge(cls.legacy_key):
                break
            sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

    def app(self, method, path, key, app_key=None, body=None):
        headers = {"apikey": key}
        if app_key:
            headers["hue-application-key"] = app_key
        return requests.request(method, self.relay_url + path, headers=headers, json=body, timeout=30)

    # ---- v2 bridge client ----
    def test_v2_get_passes_application_key(self):
        r = self.app("GET", "/route/clip/v2/resource/light", self.v2_key, APP_KEY)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["data"][0]["id"], LIGHT_ID)

    def test_v2_status_code_and_error_body_reach_the_app(self):
        r = self.app("GET", "/route/clip/v2/resource/light", self.v2_key, "wrong")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["errors"][0]["description"], "unauthorized user")

    def test_v2_put_forwards_body(self):
        r = self.app("PUT", f"/route/clip/v2/resource/light/{LIGHT_ID}", self.v2_key, APP_KEY, {"on": {"on": True}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["data"][0]["echo"], {"on": {"on": True}})

    def test_v2_delete(self):
        r = self.app("DELETE", "/route/clip/v2/resource/scene/abc", self.v2_key, APP_KEY)
        self.assertEqual(r.status_code, 200)
        self.assertIn("/clip/v2/resource/scene/abc", FakeBridge.deleted)

    def test_v1_paths_still_work_with_v2_client(self):
        self.assertEqual(self.app("GET", "/bridge/user/lights", self.v2_key).json(), {"1": {"name": "Lamp"}})
        self.assertEqual(self.app("GET", "/route/api/user/lights", self.v2_key).json(), {"1": {"name": "Lamp"}})

    def test_parallel_requests_get_their_own_answers(self):
        paths = ["/route/clip/v2/resource/light"] * 4 + ["/bridge/user/lights"] * 4
        with ThreadPoolExecutor(8) as pool:
            results = list(pool.map(lambda p: self.app("GET", p, self.v2_key, APP_KEY), paths))
        self.assertTrue(all(r.status_code == 200 for r in results))
        self.assertTrue(all("data" in r.json() for r in results[:4]))
        self.assertTrue(all(r.json() == {"1": {"name": "Lamp"}} for r in results[4:]))

    def test_non_hue_paths_are_refused_by_the_bridge(self):
        r = self.app("GET", "/route/save", self.v2_key)
        self.assertEqual(r.status_code, 403)
        r = self.app("GET", "/route/api/../save", self.v2_key)
        self.assertEqual(r.status_code, 403)

    def test_eventstream_is_not_relayed(self):
        r = self.app("GET", "/route/eventstream/clip/v2", self.v2_key, APP_KEY)
        self.assertEqual(r.status_code, 501)

    def test_unknown_bridge(self):
        r = self.app("GET", "/route/clip/v2/resource/light", "nobody", APP_KEY)
        self.assertEqual(r.status_code, 404)

    # ---- legacy bridge client ----
    def test_legacy_client_v1_get_and_put(self):
        self.assertEqual(self.app("GET", "/bridge/user/lights", self.legacy_key).json(), {"1": {"name": "Lamp"}})
        r = self.app("PUT", "/bridge/user/lights/1/state", self.legacy_key, body={"on": True})
        self.assertEqual(r.json(), [{"success": {"on": True}}])

    def test_legacy_client_gets_clear_error_for_v2(self):
        r = self.app("GET", "/route/clip/v2/resource/light", self.legacy_key, APP_KEY)
        self.assertEqual(r.status_code, 501)
        self.assertIn("too old", r.json()["errors"][0]["description"])

    # ---- report ----
    def test_report(self):
        r = requests.get(self.relay_url + "/devices?report=true", timeout=5)
        self.assertGreaterEqual(r.json()["bridges"], 2)


class OldRelayServerCompatTests(unittest.TestCase):
    def test_action_without_id_gets_bare_json_back(self):
        class Resp:
            status_code = 200
            headers = {"Content-Type": "application/json"}
            text = '{"1":{"name":"Lamp"}}'
        with patch.object(remoteApi.requests, "request", return_value=Resp()), \
                patch.object(remoteApi.requests, "post") as post:
            remoteApi.handle_action("http://bridge", {"Hue Essentials key": "k"},
                                    {"method": "GET", "address": "api/user/lights"})
        self.assertEqual(post.call_args.kwargs["json"], {"1": {"name": "Lamp"}})


class DiscoveryTests(unittest.TestCase):
    def test_cleanup_removes_only_expired_entries(self):
        from datetime import datetime, timedelta
        old = datetime.now() - timedelta(seconds=relay.DISCOVERY_EXPIRY + 10)
        relay.discovery["1.2.3.4"] = [{"id": "a", "ip": "x", "lastseen": old},
                                      {"id": "b", "ip": "y", "lastseen": datetime.now()},
                                      {"id": "c", "ip": "z", "lastseen": old}]
        relay.discovery["5.6.7.8"] = [{"id": "d", "ip": "x", "lastseen": old}]
        relay.cleanup()
        self.assertEqual([b["id"] for b in relay.discovery["1.2.3.4"]], ["b"])
        self.assertNotIn("5.6.7.8", relay.discovery)


if __name__ == "__main__":
    unittest.main()
