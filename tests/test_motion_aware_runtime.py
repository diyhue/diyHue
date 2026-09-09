import copy
import importlib.util
import pathlib
import sys
import types
import unittest
import uuid


ROOT = pathlib.Path(__file__).parents[1]
EMULATOR = ROOT / "BridgeEmulator"
sys.path.insert(0, str(EMULATOR))


class SaveSpy:
    def __init__(self, yaml_config):
        self.yaml_config = yaml_config
        self.saves = []

    def save_config(self, **kwargs):
        self.saves.append(kwargs)


class FakeDevice:
    def __init__(self, identifier, reachable=True):
        self.id_v2 = identifier
        self.group_v1 = "lights"
        self.protocol = "mqtt"
        self.protocol_cfg = {"state_topic": f"zigbee2mqtt/{identifier}"}
        self.reachable = reachable

    def getDevice(self):
        return {
            "id": self.id_v2,
            "services": [],
            "state": {"reachable": self.reachable},
        }

    def firstElement(self):
        return types.SimpleNamespace(state={"reachable": self.reachable})


class FakeRoom:
    type = "Room"

    def __init__(self, identifier, devices):
        self.id_v2 = identifier
        self.name = "Test room"
        self.lights = list(devices)
        self.sensors = []

    def getV2Room(self):
        return {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + "room")),
            "type": "room",
        }


def load_module(config, events):
    """Load motionAware.py with an isolated, in-memory diyHue graph."""
    old_modules = {
        key: sys.modules.get(key)
        for key in ("configManager", "logManager", "HueObjects", "functions", "functions.core")
    }

    config_manager = types.ModuleType("configManager")
    config_manager.bridgeConfig = SaveSpy(config)
    logger = types.SimpleNamespace(
        get_logger=lambda _name: types.SimpleNamespace(
            info=lambda *_args, **_kwargs: None,
            warning=lambda *_args, **_kwargs: None,
        )
    )
    log_manager = types.ModuleType("logManager")
    log_manager.logger = logger
    hue_objects = types.ModuleType("HueObjects")
    hue_objects.StreamEvent = events.append
    functions = types.ModuleType("functions")
    core = types.ModuleType("functions.core")
    core.bridgeIdentity = lambda value: {
        "profile": "pro" if value.get("bridge_profile") == "pro" else "classic"
    }

    sys.modules.update({
        "configManager": config_manager,
        "logManager": log_manager,
        "HueObjects": hue_objects,
        "functions": functions,
        "functions.core": core,
    })

    try:
        spec = importlib.util.spec_from_file_location(
            "motion_aware_under_test", EMULATOR / "functions" / "motionAware.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module._test_save_spy = config_manager.bridgeConfig
        return module
    finally:
        for key, value in old_modules.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


class MotionAwareRuntimeTests(unittest.TestCase):
    def make_graph(self, profile="pro", areas=None, device_count=7):
        devices = [FakeDevice(f"device-{index}") for index in range(device_count)]
        room = FakeRoom("room-1", devices)
        config = {
            "config": {
                "bridge_profile": profile,
                "motion_aware": {"areas": areas if areas is not None else {}},
            },
            "device": {
                device.id_v2: device for device in devices
            },
            "groups": {"1": room},
        }
        return config, room, devices

    def payload(self, module, room, devices, count=3):
        return {
            "name": "Entry area",
            "group": {"rid": room.getV2Room()["id"], "rtype": "room"},
            "participants": [
                {"resource": module.v2MotionAreaCandidateService(device)}
                for device in devices[:count]
            ],
        }

    def test_capability_is_profile_not_config_presence(self):
        config, _room, _devices = self.make_graph(profile="classic")
        events = []
        module = load_module(config, events)
        self.assertFalse(module.isMotionAwareAvailable())
        self.assertEqual(module.v2MotionAwareRooms(), [])
        self.assertEqual(module.v2MotionAwareResources()["motion_area_configuration"], [])

    def test_create_subset_persists_and_gets_complete_graph(self):
        config, room, devices = self.make_graph()
        events = []
        module = load_module(config, events)
        created = module.createMotionAwareArea(self.payload(module, room, devices))
        self.assertEqual(created["type"], "motion_area_configuration")
        self.assertEqual(len(created["participants"]), 3)
        area_id = created["id"]
        stored = config["config"]["motion_aware"]["areas"][area_id]
        self.assertEqual(len(stored["participants"]), 3)
        self.assertTrue(stored["enabled"])
        self.assertTrue(module._test_save_spy.saves)
        resources = module.v2MotionAwareResources()
        self.assertEqual(len(resources["motion_area_configuration"]), 1)
        self.assertEqual(len(resources["convenience_area_motion"]), 1)
        self.assertEqual(len(resources["security_area_motion"]), 1)
        self.assertEqual(
            resources["convenience_area_motion"][0]["owner"]["rid"], area_id
        )
        self.assertTrue(all(event["data"][0]["type"] for event in events))

    def test_false_and_zero_survive_update_and_resource_render(self):
        config, room, devices = self.make_graph()
        events = []
        module = load_module(config, events)
        created = module.createMotionAwareArea(self.payload(module, room, devices))
        area_id = created["id"]
        _area_id, convenience_id, _security_id = module.v2MotionAreaServiceIds(area_id)
        updated_area = module.updateMotionAwareResource(
            "motion_area_configuration", area_id, {"enabled": False}
        )
        updated_service = module.updateMotionAwareResource(
            "convenience_area_motion",
            convenience_id,
            {"enabled": False, "sensitivity": {"sensitivity": 0}},
        )
        self.assertFalse(updated_area["enabled"])
        self.assertFalse(updated_service["enabled"])
        self.assertEqual(updated_service["sensitivity"]["sensitivity"], 0)
        self.assertFalse(
            config["config"]["motion_aware"]["areas"][area_id]["enabled"]
        )
        self.assertEqual(
            config["config"]["motion_aware"]["areas"][area_id]
            ["convenience_area_motion"]["sensitivity"],
            0,
        )
        self.assertEqual(events[-1]["data"][0], updated_service)

    def test_disabled_area_does_not_emit_runtime_motion(self):
        config, room, devices = self.make_graph()
        events = []
        module = load_module(config, events)
        created = module.createMotionAwareArea(self.payload(module, room, devices))
        area_id = created["id"]
        module.updateMotionAwareResource(
            "motion_area_configuration", area_id, {"enabled": False}
        )
        before = len(events)
        self.assertEqual(module.setMotionAwareRuntimeMotion(area_id, True), [])
        self.assertEqual(len(events), before)

    def test_quiet_changed_is_stable_and_runtime_only(self):
        config, room, devices = self.make_graph()
        events = []
        module = load_module(config, events)
        created = module.createMotionAwareArea(self.payload(module, room, devices))
        area_id = created["id"]
        _area_id, convenience_id, _security_id = module.v2MotionAreaServiceIds(area_id)
        first = module.findMotionAwareResource(
            "convenience_area_motion", convenience_id
        )["motion"]
        second = module.findMotionAwareResource(
            "convenience_area_motion", convenience_id
        )["motion"]
        self.assertEqual(
            first["motion_report"]["changed"],
            second["motion_report"]["changed"],
        )
        self.assertTrue(module.setMotionAwareRuntimeMotion(area_id, True))
        self.assertEqual(module.setMotionAwareRuntimeMotion(area_id, True), [])
        resource = module.findMotionAwareResource(
            "convenience_area_motion", convenience_id
        )
        self.assertTrue(resource["motion"]["motion"])
        self.assertNotIn("runtime", config["config"]["motion_aware"])

    def test_persisted_area_remains_visible_when_participant_unreachable(self):
        config, room, devices = self.make_graph()
        events = []
        module = load_module(config, events)
        created = module.createMotionAwareArea(self.payload(module, room, devices))
        area_id = created["id"]
        devices[1].reachable = False

        # Existing areas retain their complete graph and expose participant
        # health rather than disappearing when a light temporarily drops.
        resources = module.v2MotionAwareResources()
        self.assertEqual(len(resources["motion_area_configuration"]), 1)
        participants = resources["motion_area_configuration"][0]["participants"]
        self.assertEqual(len(participants), 3)
        self.assertEqual(participants[1]["status"]["health"], "unhealthy")
        self.assertEqual(
            len(module.motionAwareCandidates()), 6,
            "unreachable candidates remain resolvable only through persisted areas",
        )

    def test_malformed_stored_area_does_not_crash_or_expose_ghost(self):
        config, room, _devices = self.make_graph(areas={})
        events = []
        module = load_module(config, events)
        area_id, _convenience_id, _security_id = module.v2MotionAreaIds(room)
        config["config"]["motion_aware"]["areas"][area_id] = None
        resources = module.v2MotionAwareResources()
        self.assertEqual(resources["motion_area_configuration"], [])

    def test_delete_clears_area_and_runtime(self):
        config, room, devices = self.make_graph()
        events = []
        module = load_module(config, events)
        created = module.createMotionAwareArea(self.payload(module, room, devices))
        area_id = created["id"]
        module.setMotionAwareRuntimeMotion(area_id, True)
        self.assertTrue(module.deleteMotionAwareArea(area_id))
        self.assertNotIn(area_id, config["config"]["motion_aware"]["areas"])
        self.assertIsNone(module.motionAwareRuntimeState(area_id))
        self.assertEqual(module.v2MotionAwareResources()["motion_area_configuration"], [])

    def test_create_rejects_dangling_or_duplicate_candidates(self):
        config, room, devices = self.make_graph()
        events = []
        module = load_module(config, events)
        payload = self.payload(module, room, devices)
        payload["participants"][2] = copy.deepcopy(payload["participants"][0])
        with self.assertRaises(ValueError):
            module.createMotionAwareArea(payload)
        payload = self.payload(module, room, devices)
        payload["participants"][2]["resource"]["rid"] = "missing"
        with self.assertRaises(ValueError):
            module.createMotionAwareArea(payload)

    def test_multiple_subset_areas_have_distinct_stable_ids_and_reservations(self):
        config, room, devices = self.make_graph(device_count=7)
        events = []
        module = load_module(config, events)
        first = module.createMotionAwareArea(self.payload(module, room, devices[:3]))
        second = module.createMotionAwareArea(self.payload(module, room, devices[3:6]))
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(
            first["id"],
            module.newMotionAreaId(first["group"], [
                item["resource"]["rid"] for item in first["participants"]
            ]),
        )
        self.assertEqual(len(module.v2MotionAwareResources()["motion_area_configuration"]), 2)
        reused = self.payload(module, room, devices[2:5])
        with self.assertRaises(ValueError):
            module.createMotionAwareArea(reused)

    def test_create_rejects_dangling_group_reference(self):
        config, room, devices = self.make_graph()
        events = []
        module = load_module(config, events)
        payload = self.payload(module, room, devices)
        payload["group"] = {"rid": "missing-room", "rtype": "room"}
        with self.assertRaises(ValueError):
            module.createMotionAwareArea(payload)

    def test_configuration_update_validates_group_and_unknown_fields(self):
        config, room, devices = self.make_graph()
        events = []
        module = load_module(config, events)
        created = module.createMotionAwareArea(self.payload(module, room, devices))
        area_id = created["id"]
        updated = module.updateMotionAwareResource(
            "motion_area_configuration",
            area_id,
            {"id": area_id, "group": created["group"]},
        )
        self.assertEqual(updated["group"], created["group"])
        with self.assertRaises(ValueError):
            module.updateMotionAwareResource(
                "motion_area_configuration", area_id, {"future": True}
            )
        with self.assertRaises(ValueError):
            module.updateMotionAwareResource(
                "motion_area_configuration", area_id, {"id": "other"}
            )


if __name__ == "__main__":
    unittest.main()
