import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

# Import the real MQTT service without loading a user's bridge configuration or
# parsing the test runner's CLI arguments (same approach as the other tests).
CONFIG = {}
sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
    yaml_config=CONFIG, mark_dirty=Mock(), save_config=Mock()))

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


class MqttDiscoveryTests(unittest.TestCase):
    def setUp(self):
        CONFIG.clear()
        CONFIG.update({"config": {"mqtt": {"enabled": True}}, "sensors": {}, "lights": {}, "groups": {}})
        self.sensors = CONFIG["sensors"]

    def discover(self, devices):
        msg = SimpleNamespace(topic="zigbee2mqtt/bridge/devices", payload=json.dumps(devices).encode())
        mqtt.on_message(None, None, msg)

    def test_model_without_sensor_type_does_not_stop_discovery(self):
        # These models have a button mapping in standardSensors but no entry in
        # sensorTypes; one of them used to raise KeyError and abort discovery
        # for every device after it.
        missing = [m for m in mqtt.standardSensors if m not in mqtt.sensorTypes]
        self.assertTrue(missing, "test needs a standardSensors model without a sensorTypes entry")

        self.discover([
            device(missing[0], "unsupported switch", "0x00158d0000000001"),
            device("RWL021", "hallway dimmer", "0x0017880100000002"),
        ])

        names = [sensor.name for sensor in self.sensors.values()]
        self.assertIn("hallway dimmer", names)
        self.assertNotIn("unsupported switch", names)


if __name__ == "__main__":
    unittest.main()
