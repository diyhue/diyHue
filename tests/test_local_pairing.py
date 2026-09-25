"""Regression tests for the local Hue application registration flow."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

from flask import Flask
from flask_restful import Api


ROOT = Path(__file__).resolve().parents[1] / "BridgeEmulator"
sys.path.insert(0, str(ROOT))

from functions.linkButton import pressLinkButton  # noqa: E402


def load(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LocalPairingTests(unittest.TestCase):
    def setUp(self):
        self.config = {"linkbutton": {"lastlinkbuttonpushed": 0}}
        self.logger = Mock()
        bridge_config = types.SimpleNamespace(
            yaml_config={"config": self.config, "apiUsers": {}},
            save_config=Mock(),
        )

        class ApiUser:
            def __init__(self, username, name, client_key):
                self.username = username
                self.name = name
                self.client_key = client_key

        hue_objects = types.ModuleType("HueObjects")
        hue_objects.ApiUser = types.SimpleNamespace(ApiUser=ApiUser)
        for name in (
            "EntertainmentConfiguration",
            "Group",
            "ResourceLink",
            "Rule",
            "Scene",
            "Schedule",
            "Sensor",
        ):
            setattr(hue_objects, name, types.SimpleNamespace())

        modules = {
            "HueObjects": hue_objects,
            "configManager": types.SimpleNamespace(bridgeConfig=bridge_config),
            "logManager": types.SimpleNamespace(
                logger=types.SimpleNamespace(get_logger=lambda _name: self.logger)
            ),
            "functions.core": types.SimpleNamespace(
                bridgeReportedApiversion=Mock(),
                bridgeReportedSwversion=Mock(),
                capabilities=Mock(),
                nextFreeId=Mock(),
                staticConfig=Mock(),
            ),
            "functions.rules": types.SimpleNamespace(rulesProcessor=Mock()),
            "lights.discover": types.SimpleNamespace(
                manualAddLight=Mock(), scanForLights=Mock()
            ),
            "lights.protocols": types.SimpleNamespace(hue=Mock()),
            "services.entertainment": types.SimpleNamespace(entertainmentService=Mock()),
            "services.updateManager": types.SimpleNamespace(
                githubCheck=Mock(), githubInstall=Mock(), versionCheck=Mock()
            ),
        }
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.restful = load("local_pairing_restful", "flaskUI/restful.py")

        self.app = Flask(__name__)
        self.app.testing = True
        Api(self.app).add_resource(self.restful.NewUser, "/api/")
        self.client = self.app.test_client()
        self.bridge_config = bridge_config

    def post_registration(self):
        return self.client.post(
            "/api/",
            json={"devicetype": "onboarding-regression", "generateclientkey": True},
        )

    def test_registration_requires_a_recent_virtual_button_press(self):
        rejected = self.post_registration()
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json[0]["error"]["type"], 101)
        self.bridge_config.save_config.assert_not_called()

        pressLinkButton(self.config)
        accepted = self.post_registration()
        self.assertEqual(accepted.status_code, 200)
        success = accepted.json[0]["success"]
        self.assertTrue(success["username"])
        self.assertTrue(success["clientkey"])
        self.assertIn(success["username"], self.bridge_config.yaml_config["apiUsers"])
        self.bridge_config.save_config.assert_called_once()

        # API credentials are returned only to the requesting client, never
        # emitted through the registration logger.
        self.assertFalse(self.logger.debug.called)


if __name__ == "__main__":
    unittest.main()
