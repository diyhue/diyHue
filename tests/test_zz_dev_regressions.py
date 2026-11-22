"""Regression tests for bugs found in the dev branch's v2 device model.

The file name sorts last on purpose: it imports the Flask/MQTT modules for
real, and several older test files expect to be the first to import them
with their own configManager stub.
"""
from pathlib import Path
import json
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import weakref

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

# Reuse the stubbed configManager if another test installed it; never load a
# user's bridge configuration or parse the test runner's CLI arguments.
if not isinstance(sys.modules.get("configManager"), SimpleNamespace):
    sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
        yaml_config={}, mark_dirty=Mock(), save_config=Mock()))
CONFIG = {}

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from flask import Flask  # noqa: E402
from HueObjects import Device, Group, Scene, Sensor  # noqa: E402
from HueObjects.Light import Light  # noqa: E402
from flaskUI import v2restapi, restful  # noqa: E402
from functions import behavior_instance, rules, request as local_request  # noqa: E402
from functions.linkButton import linkButtonIsOpen, pressLinkButton  # noqa: E402
from services import mqtt  # noqa: E402

# Modules keep the bridgeConfig dict of whichever stub was installed when they
# were first imported; point all of them at this test's dict.
_BOUND = [restful, v2restapi, rules, behavior_instance, mqtt]


def make_light(id_v1, name):
    return Light({"id_v1": id_v1, "name": name, "modelid": "LCT015", "protocol": "dummy",
                  "uniqueid": "00:17:88:01:00:00:00:0%s-0b" % id_v1})


def light_device(light):
    device = Device.Device({"name": light.name, "modelid": light.modelid, "group_v1": "lights"})
    device.add_element("light", light)
    light.owner = device.id_v2
    return device


def sensor(id_v1, modelid, type_, **extra):
    data = {"id_v1": id_v1, "name": "Sensor " + id_v1, "modelid": modelid, "type": type_,
            "uniqueid": "00:17:88:01:02:00:00:01-02-%04d" % int(id_v1)}
    data.update(extra)
    return Sensor.Sensor(data)


def sensor_device(modelid, *elements):
    device = Device.Device({"name": "Device", "modelid": modelid, "type": "sensors"})
    for element in elements:
        device.add_element(element.type, element)
    return device


class Fixture(unittest.TestCase):
    def setUp(self):
        self._saved = dict(CONFIG)
        self.addCleanup(lambda: (CONFIG.clear(), CONFIG.update(self._saved)))
        CONFIG.clear()
        CONFIG.update({"lights": {}, "sensors": {}, "groups": {}, "scenes": {}, "device": {},
                       "behavior_instance": {}, "rules": {}, "smart_scene": {}, "geofence_clients": {}, "temp": {},
                       "apiUsers": {"user": SimpleNamespace(username="user", client_key="K",
                                                            matches_key=lambda key: key == "user",
                                                            last_use_date=None)},
                       "config": {"bridgeid": "001788FFFE000000", "linkbutton": {}, "mqtt": {"enabled": True}}})
        self.keep = []  # strong references, the model holds weak ones
        for module in _BOUND:
            patcher = patch.object(module, "bridgeConfig", CONFIG)
            patcher.start()
            self.addCleanup(patcher.stop)
        for module in (restful, v2restapi, mqtt):
            patcher = patch.object(module.configManager, "bridgeConfig",
                                   SimpleNamespace(yaml_config=CONFIG, mark_dirty=Mock(), save_config=Mock()))
            patcher.start()
            self.addCleanup(patcher.stop)

    def room_with_lights(self):
        lamps = [make_light("1", "Lamp A"), make_light("2", "Lamp B")]
        devices = [light_device(lamp) for lamp in lamps]
        room = Group.Group({"id_v1": "3", "name": "Living", "type": "Room", "class": "Living room"})
        for device in devices:
            room.add_light(device)
            CONFIG["device"][device.id_v2] = device
        for lamp in lamps:
            CONFIG["lights"][lamp.id_v1] = lamp
        CONFIG["groups"]["3"] = room
        self.keep += lamps + devices + [room]
        return room, lamps


class SceneTests(Fixture):
    def test_v1_group_scene_lists_light_ids_and_states(self):
        room, lamps = self.room_with_lights()
        scene = Scene.Scene({"id_v1": "10", "name": "Relax", "type": "GroupScene",
                             "group": weakref.ref(room), "owner": CONFIG["apiUsers"]["user"]})
        self.keep.append(scene)
        api = scene.getV1Api()
        self.assertEqual(api["lights"], ["1", "2"])
        self.assertEqual(sorted(api["lightstates"]), ["1", "2"])

    def test_v1_group_scene_can_be_created_from_current_state(self):
        room, lamps = self.room_with_lights()
        app = Flask(__name__)
        with app.test_request_context(method="POST", json={"name": "Snapshot", "type": "GroupScene", "group": "3"}), \
                patch.object(restful, "StreamEvent", Mock(), create=True):
            response = restful.ResourceElements().post("user", "scenes")
        self.assertIn("success", response[0], response)
        scene = CONFIG["scenes"][response[0]["success"]["id"]]
        self.keep.append(scene)
        self.assertEqual(sorted(scene.getV1Api()["lightstates"]), ["1", "2"])


class V2LookupTests(Fixture):
    def test_buttons_rotary_and_device_power_resolve_by_id(self):
        switch = sensor("5", "RDM002", "ZLLSwitch", config={"on": True, "battery": 80, "reachable": True})
        rotary = sensor("6", "RDM002", "ZLLRelativeRotary")
        device = sensor_device("RDM002", switch, rotary)
        CONFIG["device"][device.id_v2] = device
        self.keep += [switch, rotary, device]

        for button in device.getButtons():
            self.assertIs(v2restapi.getObject("button", button["id"]), device)
        power = device.getDevicePower()
        self.assertIs(v2restapi.getObject("device_power", power["id"]), device)

        app = Flask(__name__)
        second = device.getButtons()[1]
        rotary_id = device.getRotary()[0]["id"]
        with app.test_request_context(headers={"hue-application-key": "user"}):
            result = v2restapi.ClipV2ResourceId().get("button", second["id"])
            self.assertEqual(result["data"], [second])
            result = v2restapi.ClipV2ResourceId().get("relative_rotary", rotary_id)
            self.assertEqual([r["id"] for r in result["data"]], [rotary_id])

    def test_unknown_behavior_instance_is_not_found(self):
        self.assertFalse(v2restapi.getObject("behavior_instance", "missing"))


class DeviceTests(Fixture):
    def test_hue_tap_switch_device_document(self):
        tap = sensor("7", "ZGPSWITCH", "ZGPSwitch")
        device = sensor_device("ZGPSWITCH", tap)
        self.keep += [tap, device]
        document = device.getDevice()
        self.assertEqual(document["product_data"]["model_id"], "ZGPSWITCH")
        self.assertEqual(document["product_data"]["manufacturer_name"], "Signify Netherlands B.V.")

    def test_destroying_a_device_after_its_elements_is_quiet(self):
        tap = sensor("8", "ZGPSWITCH", "ZGPSwitch")
        device = sensor_device("ZGPSWITCH", tap)
        errors = []
        with patch.object(sys, "unraisablehook", errors.append):
            del tap
            del device
        self.assertEqual(errors, [])


class LinkButtonTests(Fixture):
    def test_bool_link_button_does_not_break_pairing(self):
        config = {"linkbutton": True}
        self.assertFalse(linkButtonIsOpen(config))
        pressLinkButton(config)
        self.assertTrue(linkButtonIsOpen(config))

    def test_v1_config_put_does_not_replace_link_button_state(self):
        app = Flask(__name__)
        with app.test_request_context(method="PUT", json={"linkbutton": True, "name": "Bridge"}):
            restful.ResourceElements().put("user", "config")
        self.assertIsInstance(CONFIG["config"]["linkbutton"], dict)
        self.assertEqual(CONFIG["config"]["name"], "Bridge")


class RuleTests(Fixture):
    def test_condition_that_cannot_be_evaluated_does_not_fire(self):
        presence = sensor("4", "SML001", "ZLLPresence", state={"presence": True, "lastupdated": "none"})
        self.keep.append(presence)
        CONFIG["sensors"]["4"] = presence
        rule = SimpleNamespace(name="r", conditions=[
            {"address": "/sensors/4/state/presence", "operator": "eq", "value": "true"},
            {"address": "/sensors/99/state/presence", "operator": "eq", "value": "true"},
        ])
        self.assertFalse(rules.checkRuleConditions(rule, presence, None)[0])

    def test_local_api_url_follows_http_port_and_bind_ip(self):
        runtime = SimpleNamespace(arg={"BIND_IP": "192.168.1.5", "HTTP_PORT": 8080})
        with patch.dict(sys.modules, {"configManager": SimpleNamespace(runtimeConfig=runtime)}):
            self.assertEqual(rules.localApiUrl(), "http://192.168.1.5:8080/api/local")
            self.assertEqual(local_request.localBaseUrl(), "http://192.168.1.5:8080")
        runtime = SimpleNamespace(arg={"BIND_IP": "0.0.0.0", "HTTP_PORT": 80})
        with patch.dict(sys.modules, {"configManager": SimpleNamespace(runtimeConfig=runtime)}):
            self.assertEqual(rules.localApiUrl(), "http://127.0.0.1:80/api/local")


class MotionSensorTests(Fixture):
    def motion_device(self, protocol_cfg):
        elements = [
            sensor("11", "SML001", "ZLLPresence", protocol="mqtt", protocol_cfg=dict(protocol_cfg)),
            sensor("12", "SML001", "ZLLLightLevel", protocol="mqtt", protocol_cfg=dict(protocol_cfg)),
            sensor("13", "SML001", "ZLLTemperature", protocol="mqtt", protocol_cfg=dict(protocol_cfg)),
        ]
        for element in elements:
            element.config["on"] = True
            CONFIG["sensors"][element.id_v1] = element
        device = sensor_device("SML001", *elements)
        device.protocol = "mqtt"
        device.protocol_cfg = dict(protocol_cfg)
        CONFIG["device"][device.id_v2] = device
        CONFIG["sensors"]["1"] = SimpleNamespace(state={"daylight": True})
        self.keep += elements + [device]
        mqtt.devices_ids.clear()
        return device, elements

    def publish(self, name, payload):
        msg = SimpleNamespace(topic="zigbee2mqtt/" + name, payload=json.dumps(payload).encode())
        with patch.object(mqtt, "updateMotionAwareOccupancySensor"), \
                patch.object(mqtt, "notifyEmail", create=True), \
                patch.object(mqtt, "rulesProcessor") as processor, \
                patch.object(mqtt, "checkBehaviorInstances"):
            mqtt.on_message(None, None, msg)
        return processor

    def test_rules_are_checked_for_every_element(self):
        device, elements = self.motion_device({"friendly_name": "hall", "lightSensor": "off"})
        processor = self.publish("hall", {"occupancy": True, "illuminance": 100, "temperature": 21.5})
        self.assertEqual({call.args[0].id_v1 for call in processor.call_args_list}, {"11", "12", "13"})

    def test_a_real_light_sensor_keeps_the_measured_level(self):
        device, elements = self.motion_device({"friendly_name": "hall", "lightSensor": "off"})
        self.publish("hall", {"illuminance": 1000})
        self.assertEqual(elements[1].state["lightlevel"], mqtt.lux_to_lightlevel(1000))
        self.assertFalse(elements[1].state["dark"])

    def test_routine_daylight_check_without_light_sensor_setting(self):
        # ESP motion sensors are created without "lightSensor" in protocol_cfg
        device, elements = self.motion_device({"mac": "aa"})
        instance = SimpleNamespace(enabled=True, name="Hall", configuration={
            "source": {"rtype": "device", "rid": device.id_v2},
            "settings": {"daylight_sensitivity": {"dark_threshold": 50000}},
            "where": [], "when": {}})
        CONFIG["behavior_instance"] = {"1": instance}
        behavior_instance.checkBehaviorInstances(device)  # must not raise


if __name__ == "__main__":
    unittest.main()
