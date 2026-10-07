import importlib.util
import pathlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

from flask import Flask


ROOT = pathlib.Path(__file__).parents[1] / "BridgeEmulator"
sys.path.insert(0, str(ROOT))


def load(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EventStreamAuthTests(unittest.TestCase):
    def setUp(self):
        self.user = SimpleNamespace(last_use_date="old")
        self.bridge_config = SimpleNamespace(
            yaml_config={
                "apiUsers": {
                    "valid-application-key": self.user,
                }
            }
        )

        hue_objects = types.ModuleType("HueObjects")
        hue_objects.EventStreamSequence = Mock(return_value=0)
        hue_objects.EventStreamSnapshot = Mock(return_value=[])

        modules = {
            "HueObjects": hue_objects,
            "configManager": types.SimpleNamespace(
                bridgeConfig=self.bridge_config
            ),
            "logManager": types.SimpleNamespace(
                logger=types.SimpleNamespace(
                    get_logger=lambda _name: Mock()
                )
            ),
        }

        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)

        self.event_streamer = load(
            "eventstream_auth_event_streamer",
            "services/eventStreamer.py",
        )

        app = Flask(__name__)
        app.testing = True
        app.register_blueprint(self.event_streamer.stream)
        self.client = app.test_client()

    def test_event_stream_rejects_missing_or_invalid_application_key(self):
        missing = self.client.get("/eventstream/clip/v2")
        self.assertEqual(missing.status_code, 403)

        invalid = self.client.get(
            "/eventstream/clip/v2",
            headers={"hue-application-key": "invalid-application-key"},
        )
        self.assertEqual(invalid.status_code, 403)

    def test_event_stream_accepts_valid_application_key(self):
        response = self.client.get(
            "/eventstream/clip/v2",
            headers={"hue-application-key": "valid-application-key"},
            buffered=False,
        )
        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "text/event-stream")
            self.assertEqual(next(response.response), b": hi\n\n")
            self.assertNotEqual(self.user.last_use_date, "old")
        finally:
            response.close()


if __name__ == "__main__":
    unittest.main()
