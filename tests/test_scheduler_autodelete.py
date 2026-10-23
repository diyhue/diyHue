from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

if not isinstance(sys.modules.get("configManager"), SimpleNamespace):
    sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
        yaml_config={}, mark_dirty=Mock(), save_config=Mock()))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from services import scheduler  # noqa: E402

NOW = datetime(2026, 10, 23, 7, 30, 0)


class StopLoop(Exception):
    pass


def one_time(autodelete):
    return SimpleNamespace(status="enabled", localtime=NOW.strftime("%Y-%m-%dT%H:%M:%S"), autodelete=autodelete,
                           command={"address": "/api/x/groups/1/action", "method": "PUT", "body": {"on": True}})


class AutodeleteTests(unittest.TestCase):
    def run_once(self, schedules):
        config = {"schedules": schedules, "behavior_instance": {}, "smart_scene": {},
                  "config": {"swupdate2": {"autoinstall": {"updatetime": "T14:00:00", "on": False}},
                             "timezone": "UTC"},
                  "sensors": {}}
        fake_datetime = Mock(wraps=datetime)
        fake_datetime.now.return_value = NOW
        bridge = SimpleNamespace(mark_dirty=Mock(), save_dirty_if_needed=Mock(), save_config=Mock())
        with patch.object(scheduler, "bridgeConfig", config), \
                patch.object(scheduler, "datetime", fake_datetime), \
                patch.object(scheduler.configManager, "bridgeConfig", bridge, create=True), \
                patch.object(scheduler, "sendRequest") as send, \
                patch.object(scheduler, "sleep", side_effect=StopLoop):
            with self.assertRaises(StopLoop):
                scheduler.runScheduler()
        return send, bridge

    def test_autodelete_schedule_is_removed_after_it_runs(self):
        schedules = {"1": one_time(autodelete=True), "2": one_time(autodelete=False)}
        send, bridge = self.run_once(schedules)
        self.assertEqual(send.call_count, 2)
        self.assertEqual(list(schedules), ["2"])
        bridge.mark_dirty.assert_any_call("schedules")


if __name__ == "__main__":
    unittest.main()
