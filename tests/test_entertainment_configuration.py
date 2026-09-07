"""Isolated v2 placement tests: no bridge config, keys, sockets or lamp output.

Run with python -m unittest discover -s tests -p test_entertainment_configuration.py.
Only Flask/Flask-RESTful and PyYAML from the normal requirements are needed.
"""
import copy
import importlib.util
import logging
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
import uuid
from unittest.mock import Mock, patch

from flask import Flask
from flask_restful import Api
import yaml

ROOT = Path(os.environ.get("DIYHUE_TEST_SOURCE", Path(__file__).resolve().parents[1] / "BridgeEmulator"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Lamp:
    """Synthetic light device: dev resolves Entertainment services to devices."""
    def __init__(self, index, model="LCT001"):
        self.id_v2 = str(uuid.uuid5(uuid.NAMESPACE_URL, "synthetic-lamp-" + str(index)))
        self.id_v1 = self.id_v2  # Device.id_v1 is its persistence identifier.
        self.modelid = model
        self.state = {"on": False}

    @property
    def service_id(self):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + "entertainment"))


def location(lamp, *points):
    return {"service": {"rid": lamp.service_id, "rtype": "entertainment"},
            "positions": [dict(zip(("x", "y", "z"), p)) for p in points]}


class PlacementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.events = []
        hue = types.ModuleType("HueObjects")
        self.hue = hue
        hue.genV2Uuid = lambda: str(uuid.uuid4())
        hue.StreamEvent = self.events.append
        hue.v1StateToV2 = hue.v2StateToV1 = lambda state: state
        hue.setGroupAction = Mock(side_effect=AssertionError("No physical output allowed"))
        for name in ("Group", "Scene", "BehaviorInstance", "GeofenceClient", "SmartScene",
                     "Light", "ApiUser", "Rule", "ResourceLink", "Schedule", "Sensor", "Device"):
            setattr(hue, name, types.SimpleNamespace())
        manager = types.ModuleType("configManager")
        manager.configInit = types.SimpleNamespace()
        arguments = types.ModuleType("configManager.argumentHandler")
        arguments.parse_arguments = lambda: {"CONFIG_PATH": self.temp.name, "HOST_IP": "127.0.0.1"}
        arguments.generate_certificate = Mock(side_effect=AssertionError("No certificates needed"))
        modules = {
            "HueObjects": hue,
            "configManager": manager,
            "configManager.argumentHandler": arguments,
            "logManager": types.SimpleNamespace(logger=types.SimpleNamespace(get_logger=lambda _: Mock())),
            "sensors.sensor_types": types.SimpleNamespace(SUB_SENSOR_TYPES={}),
            "services.entertainment": types.SimpleNamespace(entertainmentService=Mock()),
            "functions.core": types.SimpleNamespace(nextFreeId=Mock()),
            "functions.scripts": types.SimpleNamespace(behaviorScripts={}),
            "lights.discover": types.SimpleNamespace(scanForLights=Mock()),
            "functions.daylightSensor": types.SimpleNamespace(daylightSensor=Mock()),
        }
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.model = load("placement_model", "HueObjects/EntertainmentConfiguration.py")
        hue.EntertainmentConfiguration = self.model
        config_module = load("placement_config", "configManager/configHandler.py")
        self.config = config_module.Config()
        self.lamps = [Lamp(1), Lamp(2), Lamp(3, "LCX004")]
        self.area = self.model.EntertainmentConfiguration({"id_v1": "2", "name": "Synthetic room", "configuration_type": "monitor"})
        for lamp in self.lamps[:2]:
            self.area.add_light(lamp)
        self.config.yaml_config = {"groups": {"2": self.area}, "lights": {}, "device": {l.id_v2: l for l in self.lamps},
                                   "apiUsers": {}, "config": {}, "scenes": {}, "sensors": {}, "geofence_clients": {}}
        manager.bridgeConfig = self.config
        self.api_module = load("placement_api", "flaskUI/v2restapi.py")
        self.api_module.authorizeV2 = lambda _: {"user": types.SimpleNamespace(username="synthetic-app")}
        self.api_module.Thread = Mock(side_effect=AssertionError("No entertainment worker allowed"))
        self.app = Flask(__name__)
        self.app.testing = True
        self.app.logger.disabled = True
        Api(self.app).add_resource(self.api_module.ClipV2ResourceId, "/clip/v2/resource/<resource>/<resourceid>")
        self.client = self.app.test_client()
        self.url = "/clip/v2/resource/entertainment_configuration/" + self.area.getV2Api()["id"]
        self.events.clear()

    def tearDown(self):
        # Keep this test's weak-reference owners alive until the area's cleanup.
        self.area.lights.clear()

    def put(self, body):
        return self.client.put(self.url, json=body)

    def edit(self):
        return {"locations": {"service_locations": [
            location(self.lamps[0], (0.3, -1, 0.5)),
            location(self.lamps[1], (-0.9, 1, -0.8))]}}

    def test_put_get_save_and_reconstruction_preserve_positions(self):
        body = self.edit()
        response = self.put(body)
        self.assertEqual(response.status_code, 200)
        current = self.client.get(self.url).json["data"][0]
        self.assertEqual([c["position"] for c in current["channels"]],
                         [e["positions"][0] for e in body["locations"]["service_locations"]])
        saved = yaml.safe_load((Path(self.temp.name) / "groups.yaml").read_text(encoding="utf-8"))["2"]
        self.assertEqual(saved["locations"][self.lamps[1].id_v1][0]["y"], 1)
        restored = self.model.EntertainmentConfiguration(dict(saved, id_v1="2"))
        for light_id in saved["lights"]:
            lamp = self.config.yaml_config["device"][light_id]
            restored.add_light(lamp)
            restored.locations[lamp] = saved["locations"][light_id]
        self.assertEqual(restored.getV2Api()["channels"], current["channels"])
        self.assertEqual(self.events[0]["data"][0]["channels"], current["channels"])
        self.assertFalse(self.area.stream["active"])

    def test_retained_channel_order_is_stable_and_payload_not_aliased(self):
        body = self.edit()
        body["locations"]["service_locations"].reverse()
        self.area.update_configuration(body, self.api_module.getObject)
        self.assertEqual([ref() for ref in self.area.lights], self.lamps[:2])
        body["locations"]["service_locations"][0]["positions"][0]["x"] = 999
        self.assertEqual(self.area.locations[self.lamps[1]][0]["x"], -0.9)

    def test_membership_and_gradient_points_round_trip(self):
        body = {"locations": {"service_locations": [
            location(self.lamps[1], (0.2, 1, 0.3)),
            location(self.lamps[2], (-0.5, 1, -0.4), (0.5, 1, 0.4))]}}
        self.assertEqual(self.put(body).status_code, 200)
        self.assertEqual([ref() for ref in self.area.lights], self.lamps[1:])
        self.assertNotIn(self.lamps[0], self.area.locations)
        saved = yaml.safe_load((Path(self.temp.name) / "groups.yaml").read_text(encoding="utf-8"))["2"]
        self.assertEqual(saved["lights"], [l.id_v1 for l in self.lamps[1:]])
        self.assertEqual(saved["locations"][self.lamps[2].id_v1], body["locations"]["service_locations"][1]["positions"])

    def test_legacy_position_and_metadata(self):
        entry = location(self.lamps[0], (0.1, -0.5, 0.8))
        entry["position"] = entry.pop("positions")[0]
        self.assertEqual(self.put({"metadata": {"name": "Renamed"}, "configuration_type": "screen",
                                  "locations": {"service_locations": [entry]}}).status_code, 200)
        self.assertEqual(self.area.name, "Renamed")
        self.assertEqual(self.area.configuration_type, "screen")
        self.assertEqual(self.area.locations[self.lamps[0]][0], entry["position"])

    def test_invalid_edit_is_atomic_and_returns_400(self):
        for bad in (None, [], [{"x": 0, "y": 0}], [{"x": True, "y": 0, "z": 0}],
                    [{"x": float("nan"), "y": 0, "z": 0}], [{"x": 0, "y": float("inf"), "z": 0}]):
            with self.subTest(points=bad):
                before = copy.deepcopy(self.area.save())
                body = self.edit()
                body["metadata"] = {"name": "Must not be applied"}
                body["locations"]["service_locations"][1]["positions"] = bad
                self.assertEqual(self.put(body).status_code, 400)
                self.assertEqual(self.area.save(), before)
                self.assertEqual(self.events, [])
                self.assertFalse((Path(self.temp.name) / "groups.yaml").exists())

    def test_unknown_duplicate_and_wrong_type_services_are_rejected(self):
        for change in (lambda e: e["service"].update(rid=str(uuid.uuid4())),
                       lambda e: e["service"].update(rtype="light"),
                       lambda e: e["service"].update(rid=self.lamps[0].service_id)):
            body = self.edit()
            change(body["locations"]["service_locations"][1])
            before = copy.deepcopy(self.area.save())
            self.assertEqual(self.put(body).status_code, 400)
            self.assertEqual(self.area.save(), before)

    def test_active_or_combined_stream_edit_is_rejected(self):
        before = copy.deepcopy(self.area.save())
        self.area.stream["active"] = True
        self.assertEqual(self.put(self.edit()).status_code, 409)
        self.assertEqual(self.area.save(), before)
        self.area.stream["active"] = False
        self.assertEqual(self.put(dict(self.edit(), action="start")).status_code, 409)
        self.assertEqual(self.area.save(), before)

    def test_disk_failure_does_not_report_success_or_emit_update(self):
        self.config.save_config = Mock(side_effect=OSError("Synthetic disk failure"))
        with self.assertRaises(OSError):
            self.put(self.edit())
        self.assertEqual(self.events, [])

    def test_missing_area_is_404(self):
        response = self.client.put(self.url + "-missing", json=self.edit())
        self.assertEqual(response.status_code, 404)

    def test_put_does_not_log_application_key(self):
        response = self.client.put(self.url, json=self.edit(), headers={"hue-application-key": "synthetic-sensitive-key"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("synthetic-sensitive-key", repr(self.api_module.logging.mock_calls))

    def test_metadata_only_edit_preserves_membership_and_positions(self):
        self.assertEqual(self.put(self.edit()).status_code, 200)
        before = copy.deepcopy(self.area.save())
        self.assertEqual(self.put({"metadata": {"name": "Renamed only"}}).status_code, 200)
        after = self.area.save()
        self.assertEqual(after["lights"], before["lights"])
        self.assertEqual(after["locations"], before["locations"])
        self.assertEqual(after["name"], "Renamed only")

    def test_real_config_reload_uses_saved_device_locations(self):
        # Seed this independently of PUT so it also detects the loader regression
        # on an unpatched dev checkout, where PUT itself is still a no-op.
        for lamp, entry in zip(self.lamps, self.edit()["locations"]["service_locations"]):
            self.area.locations[lamp] = entry["positions"]
        self.config.save_config(backup=False, resource="groups")
        before = self.area.getV2Api()["channels"]
        devices = {l.id_v2: l for l in self.lamps}
        self.hue.Device.Device = lambda data: devices[data["id"]]
        self.hue.Group.Group = lambda data: Mock()
        # Only fixture files in the temporary directory; the actual Config loader
        # reloads groups.yaml and resolves saved UUIDs through its device registry.
        (Path(self.temp.name) / "sensors.yaml").write_text("{}", encoding="utf-8")
        (Path(self.temp.name) / "device.yaml").write_text(yaml.safe_dump({
            rid: {"id": rid, "elements": [], "group_v1": "lights"} for rid in devices
        }), encoding="utf-8")
        self.config.load_config()
        restored = self.config.yaml_config["groups"]["2"]
        try:
            self.assertEqual(restored.getV2Api()["channels"], before)
            self.assertEqual([ref() for ref in restored.lights], self.lamps[:2])
        finally:
            restored.lights.clear()


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main()
