import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

# The guard keeps the shared configManager stub of other test modules intact.
if not isinstance(sys.modules.get("configManager"), SimpleNamespace):
    sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
        yaml_config={}, mark_dirty=Mock(), save_config=Mock()))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from services import mqtt  # noqa: E402
from sensors import sensor_types  # noqa: E402
from sensors import discover as sensors_discover  # noqa: E402
from HueObjects import Sensor as sensor_object  # noqa: E402


def device(model_id, friendly_name, ieee_address):
    return {
        "model_id": model_id,
        "friendly_name": friendly_name,
        "ieee_address": ieee_address,
        "definition": {"model": model_id},
    }


class MotionSensorRevisionTests(unittest.TestCase):
    """Zigbee2MQTT reports the hardware revision as the model id.

    The current Hue motion sensor reports SML003 and the older one SML002,
    while the bridge definition is keyed on SML001.
    """

    def setUp(self):
        self.config = {"config": {"mqtt": {"enabled": True}}, "sensors": {}, "lights": {}, "groups": {}}
        self.sensors = self.config["sensors"]
        # Every module binds the bridge configuration once at import time, so the
        # ones involved in discovery have to be pointed at this test's config.
        modules = (mqtt, sensors_discover)
        for module in modules:
            patcher = patch.object(module, "bridgeConfig", self.config)
            patcher.start()
            self.addCleanup(patcher.stop)

    def discover(self, devices):
        msg = SimpleNamespace(topic=mqtt.getBaseTopic() + "/bridge/devices", payload=json.dumps(devices).encode())
        mqtt.on_message(None, None, msg)

    def sensor_names(self):
        return [sensor.name for sensor in self.sensors.values()]

    def test_every_revision_has_its_own_definition(self):
        for revision in ("SML001", "SML002", "SML003"):
            self.assertIn(revision, sensor_types.sensorTypes)
            self.assertEqual(
                set(sensor_types.sensorTypes[revision]),
                {"ZLLPresence", "ZLLLightLevel", "ZLLTemperature"},
            )
            # Each revision keeps its own model id instead of being aliased.
            self.assertNotIn(revision, sensor_types.MODEL_ALIASES)

    def test_motion_sensor_with_current_revision_is_imported(self):
        self.discover([device("SML003", "kitchen motion", "0x0017880100000001")])

        names = self.sensor_names()
        self.assertTrue(
            any("kitchen motion" in name for name in names),
            "motion sensor was not imported: " + repr(names),
        )
        types = {sensor.type for sensor in self.sensors.values()}
        self.assertIn("ZLLPresence", types)
        self.assertIn("ZLLLightLevel", types)
        self.assertIn("ZLLTemperature", types)

    def test_motion_sensor_keeps_its_revision_as_model(self):
        self.discover([device("SML003", "kitchen motion", "0x0017880100000001")])
        self.assertEqual({sensor.modelid for sensor in self.sensors.values()}, {"SML003"})


if __name__ == "__main__":
    unittest.main()
