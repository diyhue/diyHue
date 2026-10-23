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
from services import homeAssistantWS  # noqa: E402


def light(**state):
    return SimpleNamespace(protocol_cfg={"entity_id": "light.desk"}, state=state)


class ChangeLightTests(unittest.TestCase):
    def setUp(self):
        self.client = homeAssistantWS.HomeAssistantClient("ws://127.0.0.1:1/api/websocket")
        self.sent = []
        patcher = patch.object(self.client, "_send", side_effect=self.sent.append)
        patcher.start()
        self.addCleanup(patcher.stop)

    def service_data(self):
        return self.sent[-1]["service_data"]

    def test_hs_color_is_converted_to_home_assistant_ranges(self):
        self.client.change_light(light(), {"hue": 65535, "sat": 254})
        self.assertEqual(self.service_data()["hs_color"], [360.0, 100.0])

        self.client.change_light(light(), {"hue": 21845, "sat": 127})
        self.assertEqual(self.service_data()["hs_color"], [120.0, 50.0])

    def test_hue_alone_uses_the_lights_current_saturation(self):
        self.client.change_light(light(hue=0, sat=254), {"hue": 32768})
        self.assertEqual(self.service_data()["hs_color"], [180.0, 100.0])

    def test_sat_alone_uses_the_lights_current_hue(self):
        self.client.change_light(light(hue=43690, sat=0), {"sat": 254})
        self.assertEqual(self.service_data()["hs_color"], [240.0, 100.0])


if __name__ == "__main__":
    unittest.main()
