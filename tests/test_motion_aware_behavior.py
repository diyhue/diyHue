import importlib.util
import pathlib
import sys
import types
import unittest
import uuid


ROOT = pathlib.Path(__file__).parents[1]
EMULATOR = ROOT / "BridgeEmulator"
sys.path.insert(0, str(EMULATOR))


class FakeGroup:
    type = "Room"

    def __init__(self):
        self.id_v2 = "group-v2"
        self.name = "Test room"
        self.actions = []
        self.state = {"any_on": False}

    def setV1Action(self, action):
        self.actions.append(action)


class FakeScene:
    id_v2 = "scene-v2"

    def __init__(self):
        self.calls = 0

    def activate(self, _transition):
        self.calls += 1


class FakeInstance:
    enabled = True
    id_v2 = "behavior-v2"

    def __init__(self, area_id, group_id):
        self.configuration = {
            "source": {
                "rtype": "motion_area_configuration",
                "rid": area_id,
            },
            "motion": {
                "motion_service": {
                    "rid": "service-v2",
                    "rtype": "convenience_area_motion",
                },
                "where": [{
                    "group": {
                        "rtype": "room",
                        "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, group_id + "room")),
                    }
                }],
                "when": {
                    "timeslots": [{
                        "start_time": {"time": {"hour": 0, "minute": 0}},
                        "on_motion": {
                            "recall_single": [{
                                "action": {
                                    "recall": {"rtype": "scene", "rid": "scene-v2"}
                                }
                            }]
                        },
                        "on_no_motion": {"recall_single": [{"action": "all_off"}]},
                    }]
                },
            },
        }


def load_module(group, instance, scene):
    old = {key: sys.modules.get(key) for key in ("configManager", "logManager")}
    config_manager = types.ModuleType("configManager")
    config_manager.bridgeConfig = types.SimpleNamespace(yaml_config={
        "groups": {"1": group},
        "scenes": {"1": scene},
        "behavior_instance": {instance.id_v2: instance},
    })
    log_manager = types.ModuleType("logManager")
    log_manager.logger = types.SimpleNamespace(get_logger=lambda _name: types.SimpleNamespace(
        info=lambda *_args, **_kwargs: None,
        warning=lambda *_args, **_kwargs: None,
        debug=lambda *_args, **_kwargs: None,
    ))
    sys.modules.update({"configManager": config_manager, "logManager": log_manager})
    try:
        spec = importlib.util.spec_from_file_location(
            "behavior_under_test", EMULATOR / "functions" / "behavior_instance.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for key, value in old.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


class MotionAwareBehaviorTests(unittest.TestCase):
    def test_motion_area_true_recalls_configured_scene(self):
        group = FakeGroup()
        scene = FakeScene()
        area_id = "area-v2"
        instance = FakeInstance(area_id, group.id_v2)
        module = load_module(group, instance, scene)
        self.assertEqual(module.checkMotionAwareBehaviorInstances(area_id, True), 1)
        self.assertEqual(scene.calls, 1)

    def test_motion_area_false_executes_no_motion_action(self):
        group = FakeGroup()
        scene = FakeScene()
        area_id = "area-v2"
        instance = FakeInstance(area_id, group.id_v2)
        module = load_module(group, instance, scene)
        self.assertEqual(module.checkMotionAwareBehaviorInstances(area_id, False), 1)
        # No delay is configured, so the daemon action is observable immediately.
        self.assertEqual(group.actions, [{"on": False}])


if __name__ == "__main__":
    unittest.main()
