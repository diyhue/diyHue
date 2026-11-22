import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from lights.protocols import elgato  # noqa: E402


def response(status=200, body=None):
    return SimpleNamespace(status_code=status, content=json.dumps(body or {}).encode(),
                           json=lambda: body, text=json.dumps(body or {}))


def accessory(name, mac):
    return response(body={"productName": "Elgato Key Light", "displayName": name, "macAddress": mac})


class BrightnessTests(unittest.TestCase):
    light = SimpleNamespace(protocol_cfg={"ip": "10.0.0.5"})

    def test_full_brightness_stays_in_hue_range(self):
        body = {"lights": [{"on": 1, "brightness": 100, "temperature": 143}]}
        with patch.object(elgato.requests, "get", return_value=response(body=body)):
            self.assertEqual(elgato.get_light_state(self.light)["bri"], 254)

    def test_hue_brightness_maps_to_percent(self):
        with patch.object(elgato.requests, "put", return_value=response()) as put:
            elgato.set_light(self.light, {"bri": 254})
            elgato.set_light(self.light, {"bri": 1})
        sent = [json.loads(call.kwargs["data"])["lights"][0]["brightness"] for call in put.call_args_list]
        self.assertEqual(sent, [100, 1])


URL = "http://{}:9123/elgato/accessory-info"


class DiscoveryTests(unittest.TestCase):
    def discover(self, get):
        found = []
        zeroconf = Mock()
        with patch.object(elgato, "Zeroconf", return_value=zeroconf), \
                patch.object(elgato, "ServiceBrowser"), \
                patch.object(elgato, "sleep"), \
                patch.object(elgato.requests, "get", side_effect=get):
            elgato.discover(found, ["10.0.0.5", "10.0.0.6", "10.0.0.7"])
        zeroconf.close.assert_called_once_with()
        return found

    def test_one_failing_light_does_not_stop_discovery(self):
        flaky_calls = []

        def get(url, timeout):
            if url == URL.format("10.0.0.6"):
                # Answers the probe, then fails when its details are fetched.
                flaky_calls.append(url)
                if len(flaky_calls) > 1:
                    raise ConnectionError("gone")
                return accessory("Flaky", "CC")
            return {URL.format("10.0.0.5"): accessory("Desk", "AA"),
                    URL.format("10.0.0.7"): accessory("Shelf", "BB")}[url]

        found = self.discover(get)
        self.assertEqual([light["name"] for light in found], ["Desk", "Shelf"])

    def test_repeated_scans_do_not_duplicate_lights(self):
        def get(url, timeout):
            if url == URL.format("10.0.0.5"):
                return accessory("Desk", "AA")
            return response(404)

        self.discover(get)
        found = self.discover(get)
        self.assertEqual([light["name"] for light in found], ["Desk"])


if __name__ == "__main__":
    unittest.main()
