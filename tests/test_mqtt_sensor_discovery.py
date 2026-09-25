"""Regression tests for Zigbee2MQTT sensor discovery.

A standardSensors entry without a matching sensorTypes definition must not
abort discovery of devices that follow it in bridge/devices.
"""

import importlib.util
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


ROOT = Path(
    os.environ.get(
        "DIYHUE_TEST_SOURCE",
        Path(__file__).resolve().parents[1] / "BridgeEmulator",
    )
)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    return module


class MqttSensorDiscoveryTests(unittest.TestCase):
    def setUp(self):
        logger = Mock()

        config_manager = types.ModuleType("configManager")
        config_manager.bridgeConfig = types.SimpleNamespace(
            yaml_config={
                "config": {
                    "mqtt": {
                        "enabled": True,
                        "mqttUser": "",
                        "mqttPassword": "",
                    }
                },
                "device": {},
                "sensors": {},
                "lights": {},
                "groups": {},
            }
        )

        hue_objects = types.ModuleType("HueObjects")
        hue_objects.Sensor = types.SimpleNamespace(Sensor=Mock())
        hue_objects.Device = types.SimpleNamespace(Device=Mock())

        paho = package("paho")
        paho_mqtt = package("paho.mqtt")
        paho_client = types.ModuleType("paho.mqtt.client")
        paho_client.Client = Mock(return_value=Mock())

        functions = package("functions")
        functions_core = types.ModuleType("functions.core")
        functions_core.nextFreeId = Mock(return_value="1")
        functions_rules = types.ModuleType("functions.rules")
        functions_rules.rulesProcessor = Mock()
        functions_behavior = types.ModuleType("functions.behavior_instance")
        functions_behavior.checkBehaviorInstances = Mock()

        sensors = package("sensors")
        sensors_discover = types.ModuleType("sensors.discover")
        sensors_discover.addHueMotionSensor = Mock()
        sensors_discover.addHueSecureContactSensor = Mock()
        sensors_types = types.ModuleType("sensors.sensor_types")
        sensors_types.sensorTypes = {}

        lights = package("lights")
        lights_discover = types.ModuleType("lights.discover")
        lights_discover.addNewLight = Mock()

        log_manager = types.ModuleType("logManager")
        log_manager.logger = types.SimpleNamespace(
            get_logger=lambda _: logger
        )

        requests = types.ModuleType("requests")

        modules = {
            "logManager": log_manager,
            "configManager": config_manager,
            "HueObjects": hue_objects,
            "paho": paho,
            "paho.mqtt": paho_mqtt,
            "paho.mqtt.client": paho_client,
            "functions": functions,
            "functions.core": functions_core,
            "functions.rules": functions_rules,
            "functions.behavior_instance": functions_behavior,
            "sensors": sensors,
            "sensors.discover": sensors_discover,
            "sensors.sensor_types": sensors_types,
            "lights": lights,
            "lights.discover": lights_discover,
            "requests": requests,
        }

        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)

        self.mqtt = load(
            "mqtt_sensor_discovery_test",
            "services/mqtt.py",
        )

        self.mqtt.getObject = Mock(return_value=False)

    def test_missing_sensor_type_does_not_abort_following_device(self):
        payload = [
            {
                "friendly_name": "broken_remote",
                "model_id": "Remote Control N2",
                "definition": {
                    "model": "Remote Control N2",
                    "exposes": [],
                },
            },
            {
                "friendly_name": "door_contact",
                "model_id": "TEST_CONTACT",
                "definition": {
                    "model": "TEST_CONTACT",
                    "exposes": [
                        {"property": "contact"},
                    ],
                },
            },
        ]

        msg = types.SimpleNamespace(
            topic="zigbee2mqtt/bridge/devices",
            payload=json.dumps(payload).encode(),
        )

        self.mqtt.on_message(None, None, msg)

        self.mqtt.addHueSecureContactSensor.assert_called_once_with(
            "door_contact",
            "mqtt",
            {
                "modelid": "TEST_CONTACT",
                "friendly_name": "door_contact",
            },
        )

    def test_all_incomplete_standard_sensor_mappings_are_nonfatal(self):
        incomplete = [
            "WXKG01LM",
            "Remote Control N2",
            "PTM 215Z",
        ]

        for model_id in incomplete:
            with self.subTest(model_id=model_id):
                payload = [
                    {
                        "friendly_name": "unsupported",
                        "model_id": model_id,
                        "definition": {
                            "model": model_id,
                            "exposes": [],
                        },
                    },
                    {
                        "friendly_name": "door_contact",
                        "model_id": "TEST_CONTACT",
                        "definition": {
                            "model": "TEST_CONTACT",
                            "exposes": [
                                {"property": "contact"},
                            ],
                        },
                    },
                ]

                msg = types.SimpleNamespace(
                    topic="zigbee2mqtt/bridge/devices",
                    payload=json.dumps(payload).encode(),
                )

                self.mqtt.addHueSecureContactSensor.reset_mock()
                self.mqtt.on_message(None, None, msg)

                self.mqtt.addHueSecureContactSensor.assert_called_once()


if __name__ == "__main__":
    unittest.main()
