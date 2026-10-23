from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from lights.protocols import milight  # noqa: E402


def light(**state):
    return SimpleNamespace(
        protocol_cfg={"ip": "192.0.2.10", "miID": "0x1", "miModes": "rgb_cct", "miGroups": 1},
        state=state,
    )


class MilightColorTemperatureTests(unittest.TestCase):
    def test_coldest_and_warmest_hue_values_reach_the_milight_range_ends(self):
        self.assertEqual(milight.hue_ct_to_milight(153), 153)
        self.assertEqual(milight.hue_ct_to_milight(500), 370)

    def test_out_of_range_values_are_clamped(self):
        self.assertEqual(milight.hue_ct_to_milight(100), 153)
        self.assertEqual(milight.hue_ct_to_milight(600), 370)
        self.assertEqual(milight.milight_ct_to_hue(400), 500)

    def test_reported_state_maps_back_to_the_hue_range(self):
        self.assertEqual(milight.milight_ct_to_hue(153), 153)
        self.assertEqual(milight.milight_ct_to_hue(370), 500)
        for ct in range(153, 501):
            self.assertLessEqual(abs(milight.milight_ct_to_hue(milight.hue_ct_to_milight(ct)) - ct), 1)

    def test_set_light_sends_the_coldest_milight_value(self):
        with patch.object(milight.requests, "put") as put:
            milight.set_light(light(bri=254), {"ct": 153})
        self.assertEqual(put.call_args.kwargs["json"], {"color_temp": 153})

    def test_get_light_state_reports_hue_ct(self):
        response = Mock(text='{"state": "ON", "brightness": 200, "color_temp": 370}')
        with patch.object(milight.requests, "get", return_value=response):
            state = milight.get_light_state(light())
        self.assertEqual(state["ct"], 500)
        self.assertEqual(state["colormode"], "ct")


if __name__ == "__main__":
    unittest.main()
