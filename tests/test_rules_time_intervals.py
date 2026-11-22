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
from functions import rules  # noqa: E402

# 2026-10-21 is a Wednesday, 2026-10-24 a Saturday.
WED_9 = datetime(2026, 10, 21, 9, 0)
SAT_9 = datetime(2026, 10, 24, 9, 0)
WORKDAYS = "W124"  # Monday to Friday


class IntervalTests(unittest.TestCase):
    def test_plain_interval(self):
        self.assertTrue(rules.in_time_interval("T08:00:00/T10:00:00", WED_9))
        self.assertFalse(rules.in_time_interval("T10:00:00/T12:00:00", WED_9))

    def test_weekday_mask(self):
        self.assertTrue(rules.in_time_interval(WORKDAYS + "/T08:00:00/T10:00:00", WED_9))
        self.assertFalse(rules.in_time_interval(WORKDAYS + "/T08:00:00/T10:00:00", SAT_9))

    def test_interval_past_midnight_counts_from_its_start_day(self):
        # Friday 22:00 to Saturday 06:00 is a workday interval, Saturday night is not.
        self.assertTrue(rules.in_time_interval(WORKDAYS + "/T22:00:00/T06:00:00", datetime(2026, 10, 24, 1, 0)))
        self.assertFalse(rules.in_time_interval(WORKDAYS + "/T22:00:00/T06:00:00", datetime(2026, 10, 25, 1, 0)))


class ConditionTests(unittest.TestCase):
    def check(self, operator, value, now):
        device = SimpleNamespace(getObjectPath=lambda: {"resource": "sensors", "id": "5"})
        rule = SimpleNamespace(name="r", conditions=[
            {"address": "/sensors/5/state/presence", "operator": "eq", "value": "true"},
            {"address": "/config/localtime", "operator": operator, "value": value},
        ])
        config = {"sensors": {"5": SimpleNamespace(state={"presence": True})}}
        fake_datetime = Mock(wraps=datetime)
        fake_datetime.now.return_value = now
        with patch.object(rules, "bridgeConfig", config), patch.object(rules, "datetime", fake_datetime):
            return rules.checkRuleConditions(rule, device, now)[0]

    def test_in_with_weekdays_does_not_fire_on_other_days(self):
        self.assertTrue(self.check("in", WORKDAYS + "/T08:00:00/T10:00:00", WED_9))
        self.assertFalse(self.check("in", WORKDAYS + "/T08:00:00/T10:00:00", SAT_9))

    def test_not_in(self):
        self.assertFalse(self.check("not in", "T08:00:00/T10:00:00", WED_9))
        self.assertTrue(self.check("not in", "T10:00:00/T12:00:00", WED_9))


if __name__ == "__main__":
    unittest.main()
