from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from lights.protocols import yeelight  # noqa: E402


def make_light(**state):
    return SimpleNamespace(name="Lamp", protocol_cfg={"ip": "10.0.0.9", "backlight": False}, state=state)


def bulb_with(properties):
    bulb = Mock()
    bulb.get_properties.return_value = properties
    return bulb


class GetLightStateTests(unittest.TestCase):
    def state(self, properties):
        with patch.object(yeelight, "connect", return_value=bulb_with(properties)):
            return yeelight.get_light_state(make_light())

    def test_hs_mode_reads_the_bulbs_string_values(self):
        # get_properties returns strings; "240" * 182 used to repeat the string
        # and "100" * 2.54 raised TypeError.
        state = self.state({"power": "on", "bright": "50", "color_mode": "3", "hue": "240", "sat": "100"})
        self.assertEqual(state["colormode"], "hs")
        self.assertEqual(state["hue"], 240 * 182)
        self.assertEqual(state["sat"], 254)

    def test_music_mode_cache_with_int_color_mode(self):
        # In music mode the library returns its own cache, where color_mode is an int.
        state = self.state({"power": "on", "bright": 50, "color_mode": 2, "ct": 2700})
        self.assertEqual(state["colormode"], "ct")
        self.assertEqual(state["ct"], yeelight.calculate_color_temp(2700))


class SetLightTests(unittest.TestCase):
    def test_full_hue_stays_in_yeelight_range(self):
        bulb = Mock()
        with patch.object(yeelight, "connect", return_value=bulb), patch.object(yeelight, "sleep"):
            yeelight.set_light(make_light(sat=254, hue=0), {"hue": 65535})
        bulb.send_command.assert_called_once_with("set_hsv", [359, 100, "smooth", 400])


if __name__ == "__main__":
    unittest.main()
