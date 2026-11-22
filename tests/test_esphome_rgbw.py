from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from lights.protocols import esphome  # noqa: E402


def rgbw_light(colormode):
    return SimpleNamespace(
        protocol_cfg={"ip": "10.0.0.8", "esphome_model": "ESPHome-RGBW", "ct_boost": 0, "rgb_boost": 0},
        state={"colormode": colormode, "bri": 100, "xy": [0.3, 0.3], "ct": 300})


class RgbwWithoutColourTests(unittest.TestCase):
    def requests_for(self, colormode, data):
        sent = []
        with patch.object(esphome, "postRequest", side_effect=lambda ip, path: sent.append(path)):
            esphome.set_light(rgbw_light(colormode), data)
        return sent

    def test_on_alone_uses_the_current_colour_mode(self):
        self.assertTrue(self.requests_for("ct", {"on": True})[-1].startswith("/light/white_led/turn_on"))
        self.assertTrue(self.requests_for("xy", {"on": True})[-1].startswith("/light/color_led/turn_on"))

    def test_brightness_alone_uses_the_current_colour_mode(self):
        self.assertTrue(self.requests_for("hs", {"bri": 50})[-1].startswith("/light/color_led/turn_on"))


if __name__ == "__main__":
    unittest.main()
