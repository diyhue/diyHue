"""Regression coverage for bridge_home event-stream updates."""

import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1] / "BridgeEmulator"


def load_group_module(name):
    spec = importlib.util.spec_from_file_location(
        name,
        ROOT / "HueObjects" / "Group.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BridgeHomeStreamTests(unittest.TestCase):

    def setUp(self):
        self.events = []

        hue_objects = types.ModuleType("HueObjects")
        hue_objects.genV2Uuid = lambda: "generated-v2-id"
        hue_objects.v1StateToV2 = lambda value: value
        hue_objects.v2StateToV1 = lambda value: value
        hue_objects.setGroupAction = Mock()
        hue_objects.StreamEvent = self.events.append

        log_manager = types.ModuleType("logManager")
        log_manager.logger = types.SimpleNamespace(
            get_logger=lambda _name: Mock()
        )

        self.modules = patch.dict(
            sys.modules,
            {
                "HueObjects": hue_objects,
                "logManager": log_manager,
            },
        )
        self.modules.start()
        self.addCleanup(self.modules.stop)

        self.group_module = load_group_module(
            "bridge_home_stream_group"
        )

    def test_bridge_home_stream_matches_device_and_room_graph(self):
        group_zero = self.group_module.Group({
            "id_v1": "0",
            "id_v2": "group-zero",
            "type": "LightGroup",
        })

        # Group construction publishes its normal creation event.
        # This test covers only the subsequent bridge_home update.
        self.events.clear()

        room = types.SimpleNamespace(
            id_v1="1",
            type="Room",
            getV2Room=lambda: {
                "id": "room-one",
                "type": "room",
            },
        )

        # Zones are not bridge_home children on the BSB003 graph.
        zone = types.SimpleNamespace(
            id_v1="2",
            type="Zone",
            getV2Zone=lambda: {
                "id": "zone-one",
                "type": "zone",
            },
        )

        devices = [
            types.SimpleNamespace(id_v2="device-one"),
            types.SimpleNamespace(id_v2="device-two"),
        ]

        group_zero.groupZeroStream(
            [group_zero, room, zone],
            devices,
            "bridge-device",
        )

        self.assertEqual(len(self.events), 1)

        event = self.events[0]
        children = event["data"][0]["children"]

        self.assertEqual(
            children,
            [
                {
                    "rid": "bridge-device",
                    "rtype": "device",
                },
                {
                    "rid": "device-one",
                    "rtype": "device",
                },
                {
                    "rid": "device-two",
                    "rtype": "device",
                },
                {
                    "rid": "room-one",
                    "rtype": "room",
                },
            ],
        )

        self.assertTrue(
            all(
                isinstance(child["rid"], str)
                for child in children
            )
        )

        self.assertFalse(
            any(
                child["rtype"] == "light"
                for child in children
            )
        )

        # Regression: the old implementation could put Light objects
        # directly in rid and break event-stream JSON serialization.
        json.dumps(event)


if __name__ == "__main__":
    unittest.main()
