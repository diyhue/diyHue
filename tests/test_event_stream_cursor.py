"""Regression tests for the V2 SSE cursor contract without a live server."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest


EMULATOR = Path(__file__).parents[1] / "BridgeEmulator"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, EMULATOR / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EventStreamCursorTests(unittest.TestCase):
    def setUp(self):
        self.old_modules = {
            key: sys.modules.get(key)
            for key in ("HueObjects", "logManager", "flask")
        }

        logger = types.SimpleNamespace(get_logger=lambda _name: object())
        sys.modules["logManager"] = types.SimpleNamespace(logger=logger)
        self.hue_objects = load_module("HueObjects", "HueObjects/__init__.py")
        sys.modules["HueObjects"] = self.hue_objects

        flask = types.ModuleType("flask")
        flask.Blueprint = lambda *_args, **_kwargs: types.SimpleNamespace(
            route=lambda *_route_args, **_route_kwargs: lambda function: function
        )
        flask.Response = lambda *args, **kwargs: (args, kwargs)
        flask.request = types.SimpleNamespace(headers={})
        flask.stream_with_context = lambda function: function
        sys.modules["flask"] = flask
        self.streamer = load_module("event_streamer_under_test", "services/eventStreamer.py")

    def tearDown(self):
        for key, value in self.old_modules.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value

    def test_fresh_and_stale_clients_do_not_replay_or_block(self):
        self.hue_objects.StreamEvent({"event": 1})
        self.hue_objects.StreamEvent({"event": 2})

        self.assertEqual(self.streamer._event_cursor(None), 2)
        self.assertEqual(self.streamer._event_cursor("not-a-number"), 2)
        self.assertEqual(self.streamer._event_cursor("-99"), 0)
        self.assertEqual(self.streamer._event_cursor("99"), 2)

    def test_post_restart_cursor_delivers_the_next_event(self):
        # A newly imported HueObjects module is the same state as an SSE
        # process restart: its first sequence is 1, while a client can retain
        # a much larger Last-Event-ID from the previous process.
        cursor = self.streamer._event_cursor("500")
        self.assertEqual(cursor, 0)
        self.hue_objects.StreamEvent({"event": "after-restart"})
        self.assertEqual(
            self.hue_objects.EventStreamSnapshot(cursor),
            [(1, {"event": "after-restart"})],
        )

    def test_retained_history_has_explicit_bounds(self):
        for value in range(2001):
            self.hue_objects.StreamEvent({"event": value})

        self.assertEqual(self.hue_objects.EventStreamBounds(), (2, 2001))
        self.assertEqual(self.streamer._event_cursor("0"), 1)
        self.assertEqual(len(self.hue_objects.EventStreamSnapshot(1)), 2000)


if __name__ == "__main__":
    unittest.main()
