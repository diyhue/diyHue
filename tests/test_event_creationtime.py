"""Run with: PYTHONPATH=BridgeEmulator python -m unittest discover -s tests -v."""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

if not isinstance(sys.modules.get("configManager"), SimpleNamespace):
    sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
        yaml_config={}, mark_dirty=Mock(), save_config=Mock()))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from HueObjects import eventstream  # noqa: E402
from HueObjects.BehaviorInstance import BehaviorInstance  # noqa: E402
from HueObjects.EntertainmentConfiguration import EntertainmentConfiguration  # noqa: E402
from HueObjects.GeofenceClient import GeofenceClient  # noqa: E402
from HueObjects.Group import Group  # noqa: E402
from HueObjects.Light import Light  # noqa: E402


@unittest.skipUnless(hasattr(time, "tzset"), "needs time.tzset")
class EventCreationTimeTests(unittest.TestCase):
    def setUp(self):
        # 12 hours behind UTC, so local time is never mistaken for UTC
        env = patch.dict(os.environ, {"TZ": "XXX+12"})
        env.start()
        time.tzset()
        self.addCleanup(time.tzset)
        self.addCleanup(env.stop)
        eventstream.clear()
        self.addCleanup(eventstream.clear)

    def assert_events_in_utc(self):
        self.assertTrue(eventstream)
        for event in eventstream:
            created = datetime.strptime(event["creationtime"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            self.assertLess(abs(datetime.now(timezone.utc) - created), timedelta(minutes=1), event)

    def test_light(self):
        Light({"name": "Lamp", "modelid": "LCT015", "id_v1": "1", "protocol": "dummy"})
        self.assert_events_in_utc()

    def test_group_update(self):
        group = Group({"name": "Room", "id_v1": "1", "type": "Room"})
        eventstream.clear()
        group.update_attr({"name": "Other room"})
        self.assert_events_in_utc()

    def test_entertainment_configuration_update(self):
        area = EntertainmentConfiguration({"name": "Area", "id_v1": "1"})
        eventstream.clear()
        area.update_attr({"name": "Other area"})
        self.assert_events_in_utc()

    def test_behavior_instance(self):
        instance = BehaviorInstance({"metadata": {"name": "Routine"}, "configuration": {}})
        instance.update_attr({"enabled": False})
        self.assert_events_in_utc()

    def test_geofence_client_update(self):
        client = GeofenceClient({"name": "Phone"})
        eventstream.clear()
        client.update_attr({"is_at_home": True})
        self.assert_events_in_utc()


if __name__ == "__main__":
    unittest.main()
