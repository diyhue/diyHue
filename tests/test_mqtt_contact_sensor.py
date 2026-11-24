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
from sensors import sensor_types  # noqa: E402
from sensors import discover as sensors_discover  # noqa: E402


def device(model_id, friendly_name, ieee_address):
    return {
        "model_id": model_id,
        "friendly_name": friendly_name,
        "ieee_address": ieee_address,
        "definition": {"model": model_id},
    }


class ContactSensorTests(unittest.TestCase):
    """Hue Secure contact sensor (SOC001).

    Zigbee2MQTT reports `contact` (true = magnet in place, door closed), while
    Hue's CLIPOpenClose sensor reports `open`, so the value is inverted.
    """

    def setUp(self):
        self.config = {"config": {"mqtt": {"enabled": True}, "alarm": {"enabled": False, "email": "", "lasttriggered": 0}}, "sensors": {}, "lights": {}, "groups": {}, "rules": {}, "behavior_instance": {}}
        self.sensors = self.config["sensors"]
        for module in (mqtt, sensors_discover):
            patcher = patch.object(module, "bridgeConfig", self.config)
            patcher.start()
            self.addCleanup(patcher.stop)
        for module in (mqtt,):
            patcher = patch.object(module, "devices_ids", {}, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)
        patch.object(mqtt, "rulesProcessor", Mock()).start()
        patch.object(mqtt, "checkBehaviorInstances", Mock()).start()

    def discover(self, devices):
        msg = SimpleNamespace(topic=mqtt.getBaseTopic() + "/bridge/devices", payload=json.dumps(devices).encode())
        mqtt.on_message(None, None, msg)

    def send_state(self, friendly_name, payload):
        msg = SimpleNamespace(topic=mqtt.getBaseTopic() + "/" + friendly_name, payload=json.dumps(payload).encode())
        mqtt.on_message(None, None, msg)

    def only_sensor(self):
        self.assertEqual(len(self.sensors), 1)
        return list(self.sensors.values())[0]

    def test_contact_sensor_is_imported(self):
        self.discover([device("SOC001", "door terrace", "0x0017880100000011")])
        sensor = self.only_sensor()
        self.assertEqual(sensor.type, "CLIPOpenClose")
        self.assertEqual(sensor.modelid, "SOC001")
        self.assertTrue(sensor.config["on"], "sensor must be enabled so state updates apply")

    def test_open_contact_marks_sensor_open(self):
        self.discover([device("SOC001", "door terrace", "0x0017880100000011")])
        sensor = self.only_sensor()
        self.send_state("door terrace", {"contact": False, "battery": 90})
        self.assertTrue(sensor.state["open"])
        self.assertNotEqual(sensor.state["lastupdated"], "none")

    def test_closed_contact_marks_sensor_closed(self):
        self.discover([device("SOC001", "door terrace", "0x0017880100000011")])
        sensor = self.only_sensor()
        self.send_state("door terrace", {"contact": False})
        self.send_state("door terrace", {"contact": True})
        self.assertFalse(sensor.state["open"])

    def test_battery_only_message_does_not_raise(self):
        self.discover([device("SOC001", "door terrace", "0x0017880100000011")])
        sensor = self.only_sensor()
        self.send_state("door terrace", {"battery": 87})
        self.assertEqual(sensor.config["battery"], 87)
        self.assertFalse(sensor.state["open"])


if __name__ == "__main__":
    unittest.main()
