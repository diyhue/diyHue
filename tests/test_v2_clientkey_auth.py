"""Run with: PYTHONPATH=BridgeEmulator python -m unittest discover -s tests -v."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

# Import the API handlers without loading or writing a user's bridge config.
config_manager = SimpleNamespace(bridgeConfig=SimpleNamespace(
    yaml_config={}, mark_dirty=Mock(), save_config=Mock()))
sys.modules["configManager"] = config_manager

import logManager
logManager.logger.configure_logger("CRITICAL")
from HueObjects import ApiUser
from flaskUI import v2restapi

# Use the config object the API module actually holds, so the test does not
# depend on which test module was imported first.
CONFIG = v2restapi.bridgeConfig


class ClientKeyAuthTests(unittest.TestCase):
    def setUp(self):
        CONFIG.setdefault("apiUsers", {}).clear()
        self.username = "syncboxusername"
        self.client_key = "0E89C42026A94FEBB10B89118E5D76C7"
        CONFIG["apiUsers"][self.username] = ApiUser.ApiUser(
            self.username, "Sync Box", self.client_key)

    def test_username_is_accepted(self):
        result = v2restapi.authorizeV2({"hue-application-key": self.username})
        self.assertIn("user", result)
        self.assertEqual(result["user"].username, self.username)

    def test_client_key_is_accepted(self):
        result = v2restapi.authorizeV2({"hue-application-key": self.client_key})
        self.assertIn("user", result)
        self.assertEqual(result["user"].username, self.username)

    def test_unknown_key_is_rejected(self):
        result = v2restapi.authorizeV2({"hue-application-key": "nope"})
        self.assertNotIn("user", result)

    def test_missing_header_is_rejected(self):
        result = v2restapi.authorizeV2({})
        self.assertNotIn("user", result)

    def test_client_key_without_client_key_set_is_rejected(self):
        CONFIG["apiUsers"]["nokey"] = ApiUser.ApiUser("nokey", "App", None)
        result = v2restapi.authorizeV2({"hue-application-key": "nokey"})
        self.assertIn("user", result)
        result = v2restapi.authorizeV2({"hue-application-key": ""})
        self.assertNotIn("user", result)

    def test_result_carries_the_key_used(self):
        result = v2restapi.authorizeV2({"hue-application-key": self.client_key})
        self.assertEqual(result["key"], self.client_key)


if __name__ == "__main__":
    unittest.main()
