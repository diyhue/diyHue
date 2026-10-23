from pathlib import Path
import sys
import threading
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
from lights.protocols import homeassistant_ws  # noqa: E402


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


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.client = homeAssistantWS.HomeAssistantClient("ws://127.0.0.1:1/api/websocket")
        self.sent = []
        for target, attrs in (
            (self.client, {"_send": Mock(side_effect=self.sent.append)}),
            (homeAssistantWS, {"connect_if_required": Mock(return_value=self.client),
                               "auth_timeout_seconds": 0.5}),
            (homeAssistantWS.discovery_result, {"wait": Mock(return_value=True)}),
        ):
            patcher = patch.multiple(target, **attrs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def receive(self, message):
        self.client.received_message(SimpleNamespace(
            data=homeAssistantWS.json.dumps(message).encode(), encoding="utf-8"))

    def sent_types(self):
        return [payload["type"] for payload in self.sent]

    def test_discovery_waits_for_auth_ok_before_get_states(self):
        self.receive({"type": "auth_required"})
        threading.Timer(0.05, self.receive, [{"type": "auth_ok"}]).start()

        homeAssistantWS.discover([])

        # Before the fix, get_states went out right after connecting, ahead of auth_ok.
        self.assertEqual(self.sent_types()[0], "auth")
        self.assertIn("get_states", self.sent_types())

    def test_discovery_sends_nothing_without_auth_ok(self):
        self.receive({"type": "auth_required"})
        homeAssistantWS.auth_timeout_seconds = 0.01

        homeAssistantWS.discover([])

        self.assertEqual(self.sent_types(), ["auth"])

    def test_discovery_without_a_connection_does_not_raise(self):
        homeAssistantWS.connect_if_required.return_value = None
        homeAssistantWS.discover([])
        self.assertEqual(self.sent, [])

    def test_set_light_without_auth_raises_instead_of_sending(self):
        homeAssistantWS.auth_timeout_seconds = 0.01
        with self.assertRaises(ConnectionError):
            homeassistant_ws.set_light(light(), {"on": True})
        self.assertEqual(self.sent, [])

    def test_closing_the_connection_resets_auth(self):
        self.receive({"type": "auth_ok"})
        self.assertTrue(self.client.authenticated.is_set())
        self.client.closed(1000)
        self.assertFalse(self.client.authenticated.is_set())


if __name__ == "__main__":
    unittest.main()
