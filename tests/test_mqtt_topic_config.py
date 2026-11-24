import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

# Import the real MQTT service without loading a user's bridge configuration or
# parsing the test runner's CLI arguments (same approach as the other tests).
# The guard keeps the shared configManager stub of other test modules intact:
# whichever module is imported first provides it.
if not isinstance(sys.modules.get("configManager"), SimpleNamespace):
    sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
        yaml_config={}, mark_dirty=Mock(), save_config=Mock()))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from services import mqtt  # noqa: E402


def device(model_id, friendly_name, ieee_address):
    return {
        "model_id": model_id,
        "friendly_name": friendly_name,
        "ieee_address": ieee_address,
        "definition": {"model": model_id},
    }


class MqttBaseTopicTests(unittest.TestCase):
    def setUp(self):
        self.config = {"config": {"mqtt": {"enabled": True}}, "sensors": {}, "lights": {}, "groups": {}}
        self.sensors = self.config["sensors"]
        # The service binds the bridge configuration at import time, so it has
        # to be pointed at this test's own configuration.
        self.bridge_config = patch.object(mqtt, "bridgeConfig", self.config)
        self.bridge_config.start()
        self.addCleanup(self.bridge_config.stop)

    def discover(self, topic, devices):
        msg = SimpleNamespace(topic=topic, payload=json.dumps(devices).encode())
        mqtt.on_message(None, None, msg)

    def sensor_names(self):
        return [sensor.name for sensor in self.sensors.values()]

    def test_default_base_topic_is_zigbee2mqtt(self):
        self.assertEqual(mqtt.getBaseTopic(), "zigbee2mqtt")

    def test_devices_on_default_topic_are_discovered(self):
        self.discover("zigbee2mqtt/bridge/devices", [
            device("RWL021", "hallway dimmer", "0x0017880100000002"),
        ])
        self.assertIn("hallway dimmer", self.sensor_names())

    def test_configured_base_topic_is_used_for_device_list(self):
        self.config["config"]["mqtt"]["baseTopic"] = "hue"
        self.assertEqual(mqtt.getBaseTopic(), "hue")
        self.discover("hue/bridge/devices", [
            device("RWL021", "hallway dimmer", "0x0017880100000002"),
        ])
        self.assertIn("hallway dimmer", self.sensor_names())

    def test_default_topic_is_ignored_when_base_topic_is_configured(self):
        self.config["config"]["mqtt"]["baseTopic"] = "hue"
        self.discover("zigbee2mqtt/bridge/devices", [
            device("RWL021", "hallway dimmer", "0x0017880100000002"),
        ])
        self.assertNotIn("hallway dimmer", self.sensor_names())

    def test_base_topic_is_stripped_of_slashes(self):
        self.config["config"]["mqtt"]["baseTopic"] = "/hue/"
        self.assertEqual(mqtt.getBaseTopic(), "hue")

    def test_subscriptions_use_configured_base_topic(self):
        self.config["config"]["mqtt"]["baseTopic"] = "hue"
        client = Mock()
        mqtt.on_connect(client, None, None, 0)
        topics = [call.args[0] for call in client.subscribe.call_args_list]
        self.assertIn("hue/+", topics)
        self.assertIn("hue/bridge/devices", topics)
        self.assertIn("hue/bridge/log", topics)
        self.assertNotIn("zigbee2mqtt/bridge/devices", topics)

    def test_light_discovery_publishes_to_configured_base_topic(self):
        from lights.protocols import mqtt as light_mqtt
        mqtt_config = {
            "enabled": True,
            "mqttUser": "",
            "mqttPassword": "",
            "mqttServer": "127.0.0.1",
            "mqttPort": 1883,
            "baseTopic": "hue",
        }
        with patch.object(light_mqtt.publish, "single") as publish_single:
            light_mqtt.discover(mqtt_config)
        published = [call.args[0] for call in publish_single.call_args_list]
        self.assertIn("hue/bridge/request/permit_join", published)
        self.assertIn("hue/bridge/config/devices/get", published)


if __name__ == "__main__":
    unittest.main()
