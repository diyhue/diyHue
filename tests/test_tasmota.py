import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from functions.colors import convert_rgb_xy  # noqa: E402
from lights.protocols import tasmota  # noqa: E402


def light_state(status):
    light = SimpleNamespace(protocol_cfg={"ip": "192.168.1.50"})
    with patch.object(tasmota, "sendRequest", return_value=json.dumps({"StatusSTS": status})):
        return tasmota.get_light_state(light)


class ColorParsingTests(unittest.TestCase):
    def test_hex_with_white_channels(self):
        self.assertEqual(tasmota.color_to_rgb("643C0A"), [100, 60, 10])
        self.assertEqual(tasmota.color_to_rgb("643C0A00"), [100, 60, 10])
        self.assertEqual(tasmota.color_to_rgb("643C0A0000"), [100, 60, 10])

    def test_decimal_with_setoption17(self):
        # SetOption17 1 reports decimals, which used to be parsed as hex.
        self.assertEqual(tasmota.color_to_rgb("100,60,10"), [100, 60, 10])
        self.assertEqual(tasmota.color_to_rgb("100,60,10,0,0"), [100, 60, 10])

    def test_light_state_uses_the_same_color_for_both_formats(self):
        expected = convert_rgb_xy(100, 60, 10)
        for color in ("643C0A", "643C0A0000", "100,60,10"):
            with self.subTest(color=color):
                state = light_state({"POWER": "ON", "Color": color, "Dimmer": 50})
                self.assertEqual(state["xy"], expected)
                self.assertEqual(state["bri"], 127)
                self.assertTrue(state["on"])


if __name__ == "__main__":
    unittest.main()
