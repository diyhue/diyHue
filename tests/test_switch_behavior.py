from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

# Reuse the stubbed configManager if another test installed it; never load a
# user's bridge configuration or parse the test runner's CLI arguments.
if not isinstance(sys.modules.get("configManager"), SimpleNamespace):
    sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
        yaml_config={}, mark_dirty=Mock(), save_config=Mock()))
CONFIG = sys.modules["configManager"].bridgeConfig.yaml_config

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from functions import behavior_instance  # noqa: E402

DEVICE_ID = "11111111-1111-1111-1111-111111111111"
ROOM_RID = "room-rid"
SCENE_RID = "scene-rid"


def button_id(n):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, DEVICE_ID + "button%d" % n))


def instance(buttons):
    # Shape the Hue app sends when a Hue dimmer switch is configured: "where"
    # sits on each button and actions use the *_extended keys (issue #1055).
    return SimpleNamespace(enabled=True, configuration={
        "device": {"rtype": "device", "rid": DEVICE_ID},
        "buttons": buttons,
    })


class HueDimmerBehaviorTests(unittest.TestCase):
    def setUp(self):
        self._saved = dict(CONFIG)
        self.addCleanup(lambda: (CONFIG.clear(), CONFIG.update(self._saved)))
        self.group = Mock()
        self.group.update_state.return_value = {"any_on": False}
        patcher = patch.object(behavior_instance, "findGroup", side_effect=lambda rid, rtype: self.group if rid == ROOM_RID else None)
        patcher.start()
        self.addCleanup(patcher.stop)
        scenes = patch.object(behavior_instance, "callScene")
        self.callScene = scenes.start()
        self.addCleanup(scenes.stop)

    def press(self, config, buttonevent):
        CONFIG.update({"sensors": {}, "behavior_instance": {"1": config}})
        device = SimpleNamespace(type="ZLLSwitch", id_v2=DEVICE_ID, parent_id_v2=None, uniqueid=None,
                                 state={"buttonevent": buttonevent})
        behavior_instance.checkBehaviorInstances(device)

    def test_time_based_extended_recalls_the_scene_for_the_buttons_room(self):
        where = [{"group": {"rtype": "room", "rid": ROOM_RID}}]
        config = instance({button_id(1): {"where": where, "on_short_release": {"time_based_extended": {
            "slots": [{"start_time": {"hour": 0, "minute": 0},
                       "actions": [{"action": {"recall": {"rtype": "scene", "rid": SCENE_RID}}}]}],
            "with_off": {"enabled": True}}}}})

        self.press(config, 1002)

        self.callScene.assert_called_once_with(SCENE_RID)

    def test_time_based_extended_with_off_turns_the_room_off_when_on(self):
        self.group.update_state.return_value = {"any_on": True}
        where = [{"group": {"rtype": "room", "rid": ROOM_RID}}]
        config = instance({button_id(1): {"where": where, "on_short_release": {"time_based_extended": {
            "slots": [{"start_time": {"hour": 0, "minute": 0},
                       "actions": [{"action": {"recall": {"rtype": "scene", "rid": SCENE_RID}}}]}],
            "with_off": {"enabled": True}}}}})

        self.press(config, 1002)

        self.group.setV1Action.assert_called_once_with({"on": False})
        self.callScene.assert_not_called()

    def test_dim_up_uses_the_buttons_own_where(self):
        where = [{"group": {"rtype": "room", "rid": ROOM_RID}}]
        self.press(instance({button_id(2): {"where": where, "on_repeat": {"action": "dim_up"}}}), 2001)

        self.group.setV1Action.assert_called_once_with({"bri_inc": +30})

    def test_scene_cycle_extended_recalls_a_scene(self):
        where = [{"group": {"rtype": "room", "rid": ROOM_RID}}]
        config = instance({button_id(4): {"where": where, "on_short_release": {"scene_cycle_extended": {
            "slots": [[{"action": {"recall": {"rtype": "scene", "rid": SCENE_RID}}}]],
            "with_off": {"enabled": False}}}}})

        self.press(config, 4002)

        self.callScene.assert_called_once_with(SCENE_RID)


if __name__ == "__main__":
    unittest.main()
