import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from functions.colors import hsv_to_rgb  # noqa: E402
from lights.protocols import govee  # noqa: E402


def make_light(**state):
    return SimpleNamespace(
        protocol_cfg={"device_id": "AA:BB", "sku_model": "H6008", "segmentedID": -1,
                      "bri_range": {"min": 1, "max": 100, "precision": 0}},
        state={"hue": 0, "sat": 254, "bri": 254, **state})


def sent(light, data):
    with patch.object(govee, "get_headers", return_value={}), \
            patch.object(govee.requests, "put", return_value=Mock()) as put:
        govee.set_light(light, data)
    return [json.loads(call.kwargs["data"])["payload"]["capability"] for call in put.call_args_list]


def rgb_value(r, g, b):
    return (r << 16) | (g << 8) | b


class ColorTests(unittest.TestCase):
    def test_hue_alone_keeps_the_lights_saturation(self):
        caps = sent(make_light(sat=254, bri=254), {"hue": 21845})
        self.assertEqual([c["value"] for c in caps], [rgb_value(*hsv_to_rgb(21845, 254, 254))])

    def test_hue_and_sat_together_send_one_colour(self):
        caps = sent(make_light(), {"hue": 43690, "sat": 127})
        self.assertEqual(len(caps), 1)
        self.assertEqual(caps[0]["value"], rgb_value(*hsv_to_rgb(43690, 127, 254)))


class BrightnessTests(unittest.TestCase):
    def test_hue_range_maps_onto_the_device_range(self):
        caps = sent(make_light(), {"bri": 254})
        self.assertEqual(caps[0]["value"], 100)
        self.assertEqual(sent(make_light(), {"bri": 1})[0]["value"], 1)

    def test_state_maps_back_into_hue_range(self):
        state = govee.parse_light_state([
            {"type": "devices.capabilities.online", "instance": "online", "state": {"value": True}},
            {"type": "devices.capabilities.range", "instance": "brightness", "state": {"value": 100}},
        ], make_light())
        self.assertTrue(state["reachable"])
        self.assertEqual(state["bri"], 254)


if __name__ == "__main__":
    unittest.main()
