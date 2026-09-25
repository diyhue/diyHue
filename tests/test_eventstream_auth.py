import pathlib
import sys
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from flask import Flask


BRIDGE_EMULATOR = pathlib.Path(__file__).parents[1] / "BridgeEmulator"
sys.path.insert(0, str(BRIDGE_EMULATOR))

from services import eventStreamer  # noqa: E402


class EventStreamAuthTests(unittest.TestCase):
    def setUp(self):
        self.user = SimpleNamespace(last_use_date="old")
        self.bridge_config = {
            "apiUsers": {
                "valid-application-key": self.user,
            }
        }

        self.bridge_config_patch = patch.object(
            eventStreamer,
            "bridgeConfig",
            self.bridge_config,
        )
        self.bridge_config_patch.start()

        app = Flask(__name__)
        app.register_blueprint(eventStreamer.stream)
        self.client = app.test_client()

    def tearDown(self):
        self.bridge_config_patch.stop()

    def test_event_stream_rejects_missing_or_invalid_application_key(self):
        missing = self.client.get("/eventstream/clip/v2")
        self.assertEqual(missing.status_code, 403)

        invalid = self.client.get(
            "/eventstream/clip/v2",
            headers={"hue-application-key": "invalid-application-key"},
        )
        self.assertEqual(invalid.status_code, 403)

    def test_event_stream_accepts_valid_application_key(self):
        with patch.object(
            eventStreamer.HueObjects,
            "EventStreamSequence",
            return_value=0,
        ):
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
