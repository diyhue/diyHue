from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

# Reuse the stubbed configManager if another test installed it; never load a
# user's bridge configuration or parse the test runner's CLI arguments.
if not isinstance(sys.modules.get("configManager"), SimpleNamespace):
    sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
        yaml_config={}, mark_dirty=Mock(), save_config=Mock()))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from flask import Flask  # noqa: E402
from flaskUI import v2restapi  # noqa: E402
from functions import scripts  # noqa: E402
from HueObjects.SmartScene import SmartScene  # noqa: E402

# The dict the API module actually reads, whichever stub was installed first.
CONFIG = v2restapi.bridgeConfig


class SmartSceneTests(unittest.TestCase):
    def setUp(self):
        self._saved = dict(CONFIG)
        self.addCleanup(lambda: (CONFIG.clear(), CONFIG.update(self._saved)))
        CONFIG["apiUsers"] = {"test": SimpleNamespace(username="test", client_key="test-key")}
        self.app = Flask(__name__)

    def test_recalling_a_scene_stops_the_smart_scene_running_on_its_group(self):
        living, kitchen = object(), object()
        natural_light = Mock(state="active", group={"rid": "living-room", "rtype": "room"})
        kitchen_cycle = Mock(state="active", group={"rid": "kitchen", "rtype": "room"})
        already_off = Mock(state="inactive", group={"rid": "living-room", "rtype": "room"})
        CONFIG["smart_scene"] = {"1": natural_light, "2": kitchen_cycle, "3": already_off}
        scene = Mock(group=lambda: living)
        groups = {"living-room": living, "kitchen": kitchen}

        with patch.object(v2restapi, "getObject", return_value=scene), \
                patch.object(scripts, "findGroup", side_effect=groups.get), \
                self.app.test_request_context(method="PUT", json={"recall": {"action": "active"}},
                                              headers={"hue-application-key": "test"}):
            v2restapi.ClipV2ResourceId().put("scene", "scene-id")

        scene.activate.assert_called_once()
        natural_light.stop.assert_called_once_with()
        kitchen_cycle.stop.assert_not_called()
        already_off.stop.assert_not_called()

    def test_stop_marks_the_smart_scene_inactive_without_turning_lights_off(self):
        smart_scene = SmartScene({"name": "Natural light", "id_v1": "1", "state": "active",
                                  "group": {"rid": "living-room", "rtype": "room"}})
        with patch.object(scripts, "findGroup") as findGroup:
            smart_scene.stop()

        self.assertEqual(smart_scene.state, "inactive")
        self.assertEqual(smart_scene.getV2Api()["state"], "inactive")
        findGroup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
