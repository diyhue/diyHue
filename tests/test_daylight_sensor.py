from datetime import datetime, timedelta
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
from functions import daylightSensor as daylight  # noqa: E402

NOW = datetime(2026, 6, 1, 18, 0)


def sensor(sunsetoffset=0, sunriseoffset=0):
    return SimpleNamespace(config={"configured": True, "sunsetoffset": sunsetoffset, "sunriseoffset": sunriseoffset},
                           protocol_cfg={"lat": "52.0", "long": "5.0"}, state={}, dxState={})


def routine(kind, minutes=None):
    time_point = {"type": kind}
    if minutes is not None:
        time_point["offset"] = {"minutes": minutes}
    return SimpleNamespace(configuration={"when_extended": {"start_at": {"time_point": time_point}}})


class DaylightSensorTests(unittest.TestCase):
    def run_sensor(self, s, routines, sunset_in, tz="Europe/Amsterdam"):
        events = []
        clock = {"now": NOW}

        def fake_sleep(seconds):
            events.append(("sleep", seconds))
            clock["now"] += timedelta(seconds=seconds)

        fake_datetime = Mock(wraps=datetime)
        fake_datetime.now.side_effect = lambda tz=None: clock["now"]
        sun_times = {"sunset": NOW + timedelta(seconds=sunset_in), "sunrise": NOW - timedelta(hours=12)}
        threads = []

        def fake_thread(target, args):
            events.append(("routine", args[1]))
            threads.append(args)
            return Mock()

        with patch.object(daylight, "bridgeConfig", {"behavior_instance": routines}), \
                patch.object(daylight, "datetime", fake_datetime), \
                patch.object(daylight, "sun", return_value=sun_times), \
                patch.object(daylight, "sleep", side_effect=fake_sleep), \
                patch.object(daylight, "Thread", side_effect=fake_thread), \
                patch.object(daylight, "rulesProcessor") as rules:
            daylight.daylightSensor(tz, s)
        return events, rules

    def test_routines_are_scheduled_before_the_sensor_sleeps(self):
        events, _ = self.run_sensor(sensor(), {"1": routine("sunset")}, sunset_in=1800)
        self.assertEqual(events, [("routine", 1800), ("sleep", 1800)])

    def test_routine_uses_its_own_offset_not_the_sensors(self):
        events, _ = self.run_sensor(sensor(sunsetoffset=-20), {"1": routine("sunset", minutes=10)}, sunset_in=1800)
        self.assertIn(("routine", 1800 + 600), events)
        self.assertIn(("sleep", 1800 - 1200), events)

    def test_lastupdated_is_the_time_the_sleep_ended(self):
        s = sensor()
        _, rules = self.run_sensor(s, {}, sunset_in=1800)
        ended = NOW + timedelta(seconds=1800)
        self.assertEqual(s.state, {"daylight": False, "lastupdated": ended.strftime("%Y-%m-%dT%H:%M:%S")})
        self.assertEqual(rules.call_args.args[1], ended)

    def test_timezone_without_a_region(self):
        events, _ = self.run_sensor(sensor(), {}, sunset_in=1800, tz="UTC")
        self.assertIn(("sleep", 1800), events)


if __name__ == "__main__":
    unittest.main()
