import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

# Keep the shared configManager stub of the other test modules intact.
if not isinstance(sys.modules.get("configManager"), SimpleNamespace):
    sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
        yaml_config={}, mark_dirty=Mock(), save_config=Mock()))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from services import mqtt  # noqa: E402


class SwitchDiscoveryTests(unittest.TestCase):
    """Zigbee2MQTT announces sockets as Home Assistant "switch" entities.

    They carry the same command/state topics as a light, so the bridge should
    import them as a Hue on/off plug (LOM001).
    """

    def setUp(self):
        self.config = {"config": {"mqtt": {"enabled": True}, "alarm": {"enabled": False, "email": "", "lasttriggered": 0}}, "sensors": {}, "lights": {}, "groups": {}, "rules": {}, "behavior_instance": {}}
        patcher = patch.object(mqtt, "bridgeConfig", self.config)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(mqtt, "devices_ids", {}, create=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addNewLight = Mock()
        patcher = patch.object(mqtt, "addNewLight", self.addNewLight)
        patcher.start()
        self.addCleanup(patcher.stop)

    def discovery_payload(self, name="Steckdose Flur"):
        return {
            "unique_id": "0x0017880100000022_switch",
            "name": name,
            "state_topic": "hue/" + name,
            "command_topic": "hue/" + name + "/set",
            "device": {"name": name},
        }

    def discover(self, name="Steckdose Flur"):
        topic = mqtt.discoveryPrefix + "/switch/0x0017880100000022/switch/config"
        msg = SimpleNamespace(topic=topic, payload=json.dumps(self.discovery_payload(name)).encode())
        mqtt.on_message(None, None, msg)

    def test_socket_becomes_on_off_plug(self):
        self.discover()
        self.assertEqual(self.addNewLight.call_count, 1)
        args = self.addNewLight.call_args[0]
        self.assertEqual(args[0], "LOM001")
        self.assertEqual(args[1], "Steckdose Flur")
        self.assertEqual(args[2], "mqtt")
        self.assertEqual(args[3]["state_topic"], "hue/Steckdose Flur")
        self.assertEqual(args[3]["command_topic"], "hue/Steckdose Flur/set")

    def test_switch_config_is_subscribed(self):
        client = Mock()
        mqtt.on_connect(client, None, None, 0)
        topics = [c[0][0] for c in client.subscribe.call_args_list]
        self.assertIn(mqtt.discoveryPrefix + "/switch/+/+/config", topics)


if __name__ == "__main__":
    unittest.main()
