"""PUT/GET of the diyhue v2 resource (Hue Essentials remote API settings).

Sorts last for the same reason as test_zz_dev_regressions.py.
"""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

if not isinstance(sys.modules.get("configManager"), SimpleNamespace):
    sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
        yaml_config={}, mark_dirty=Mock(), save_config=Mock()))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from flask import Flask  # noqa: E402
from flask_restful import Api  # noqa: E402
from flaskUI import v2restapi  # noqa: E402


class DiyHueResourceTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "apiUsers": {"user": SimpleNamespace(username="user", client_key="K", last_use_date=None,
                                                 matches_key=lambda key: key == "user")},
            "config": {"bridgeid": "001788FFFE000000", "Hue Essentials key": "hek",
                       "Remote API enabled": False, "discovery": True},
        }
        self.mark_dirty = Mock()
        self.events = Mock()
        patches = [
            patch.object(v2restapi, "bridgeConfig", self.config),
            patch.object(v2restapi.configManager, "bridgeConfig",
                         SimpleNamespace(yaml_config=self.config, mark_dirty=self.mark_dirty)),
            patch.object(v2restapi, "StreamEvent", self.events),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        app = Flask(__name__)
        api = Api(app)
        api.add_resource(v2restapi.ClipV2Resource, '/clip/v2/resource/<string:resource>', strict_slashes=False)
        api.add_resource(v2restapi.ClipV2ResourceId, '/clip/v2/resource/<string:resource>/<string:resourceid>', strict_slashes=False)
        self.client = app.test_client()
        self.headers = {"hue-application-key": "user"}
        self.rid = v2restapi.v2DiyHueBridge()["id"]

    def test_put_on_the_collection_updates_the_settings(self):
        response = self.client.put("/clip/v2/resource/diyhue", headers=self.headers,
                                   json={"remote_api_enabled": True, "remote_discovery": False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"errors": [], "data": [{"rid": self.rid, "rtype": "diyhue"}]})
        self.assertTrue(self.config["config"]["Remote API enabled"])
        self.assertFalse(self.config["config"]["discovery"])
        self.mark_dirty.assert_called_with("config")
        event = self.events.call_args.args[0]
        self.assertEqual(event["type"], "update")
        self.assertEqual(event["data"][0]["remote_api_enabled"], True)

        data = self.client.get("/clip/v2/resource/diyhue", headers=self.headers).json["data"][0]
        self.assertTrue(data["remote_api_enabled"])
        self.assertFalse(data["remote_discovery"])

    def test_put_and_get_by_id(self):
        response = self.client.put("/clip/v2/resource/diyhue/" + self.rid, headers=self.headers,
                                   json={"remote_api_enabled": True})
        self.assertEqual(response.status_code, 200)
        data = self.client.get("/clip/v2/resource/diyhue/" + self.rid, headers=self.headers).json["data"]
        self.assertEqual(data[0]["remote_api_enabled"], True)

    def test_invalid_requests_change_nothing(self):
        for path, body, status in (
            ("/clip/v2/resource/diyhue", {"hue_essentials_key": "x"}, 400),
            ("/clip/v2/resource/diyhue", {"remote_api_enabled": "yes"}, 400),
            ("/clip/v2/resource/diyhue", {}, 400),
            ("/clip/v2/resource/diyhue/unknown-id", {"remote_api_enabled": True}, 404),
        ):
            with self.subTest(body=body):
                response = self.client.put(path, headers=self.headers, json=body)
                self.assertEqual(response.status_code, status)
                self.assertTrue(response.json["errors"])
        self.assertFalse(self.config["config"]["Remote API enabled"])
        self.mark_dirty.assert_not_called()

    def test_requires_application_key(self):
        response = self.client.put("/clip/v2/resource/diyhue", json={"remote_api_enabled": True})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.config["config"]["Remote API enabled"])


if __name__ == "__main__":
    unittest.main()
