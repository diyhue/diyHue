from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

if not isinstance(sys.modules.get("configManager"), SimpleNamespace):
    sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
        yaml_config={}, mark_dirty=Mock(), save_config=Mock()))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from services import mqtt  # noqa: E402


class LightLevelTests(unittest.TestCase):
    def test_follows_the_hue_formula(self):
        self.assertEqual(mqtt.lux_to_lightlevel(1), 1)
        self.assertEqual(mqtt.lux_to_lightlevel(10), 10001)
        self.assertEqual(mqtt.lux_to_lightlevel(1000), 30001)

    def test_dim_light_is_never_negative(self):
        # log10 of anything under 1 lux is negative
        self.assertEqual(mqtt.lux_to_lightlevel(0.5), 0)
        self.assertEqual(mqtt.lux_to_lightlevel(0), 0)

    def test_capped_at_the_hue_maximum(self):
        self.assertEqual(mqtt.lux_to_lightlevel(10 ** 7), 65535)


class TemperatureTests(unittest.TestCase):
    def test_rounds_instead_of_truncating(self):
        # 0.29 * 100 is 28.999999999999996 in floating point
        self.assertEqual(mqtt.celsius_to_hue(0.29), 29)
        self.assertEqual(mqtt.celsius_to_hue(21.37), 2137)
        self.assertEqual(mqtt.celsius_to_hue(-4.1), -410)


if __name__ == "__main__":
    unittest.main()
