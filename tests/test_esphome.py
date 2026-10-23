from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from lights.protocols import esphome  # noqa: E402


def make_light(model, ct_boost=0, rgb_boost=0, **state):
    return SimpleNamespace(
        protocol_cfg={"ip": "10.0.0.8", "esphome_model": model, "ct_boost": ct_boost, "rgb_boost": rgb_boost},
        state={"colormode": "ct", "bri": 100, **state})


def reply(**body):
    return SimpleNamespace(json=lambda: body)


class BrightnessTests(unittest.TestCase):
    def state(self, light, **body):
        with patch.object(esphome.requests, "get", return_value=reply(**body)):
            return esphome.get_light_state(light)

    def test_full_brightness_stays_in_hue_range(self):
        state = self.state(make_light("ESPHome-Dimmable"), state="ON", brightness=255)
        self.assertEqual(state["bri"], 254)

    def test_boost_is_taken_off_again(self):
        light = make_light("ESPHome-RGB", rgb_boost=20)
        sent = []
        with patch.object(esphome, "postRequest", side_effect=lambda ip, data: sent.append(data)):
            esphome.set_light(light, {"bri": 100})
        self.assertIn("brightness=120", sent[-1])
        state = self.state(light, state="ON", brightness=120, color={"r": 255, "g": 0, "b": 0})
        self.assertEqual(state["bri"], 100)

    def test_ct_boost_on_ct_light(self):
        state = self.state(make_light("ESPHome-CT", ct_boost=30), state="ON", brightness=60, color_temp=300)
        self.assertEqual(state["bri"], 30)


if __name__ == "__main__":
    unittest.main()
