"""Regression contract for Classic-first Bridge Pro onboarding."""
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

from functions.core import bridgeIdentity
from functions.linkButton import pressLinkButton


def load(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProOnboardingLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "bridge_profile": "classic",
            "linkbutton": {"lastlinkbuttonpushed": 0},
        }

        self.yaml_config = {
            "config": self.config,
            "apiUsers": {},
            "device": {},
            "groups": {},
            "lights": {},
            "scenes": {},
            "sensors": {},
            "geofence_clients": {},
            "smart_scene": {},
            "behavior_instance": {},
        }

        self.logger = Mock()

        bridge_config = types.SimpleNamespace(
            yaml_config=self.yaml_config,
            save_config=Mock(),
        )

        # Use diyHue's real ApiUser serialization contract.  This lets the
        # lifecycle test cover the same whitelist representation that
        # configHandler persists across a bridge restart.
        api_user_module = load(
            "pro_onboarding_api_user",
            "HueObjects/ApiUser.py",
        )

        hue_objects = types.ModuleType("HueObjects")
        hue_objects.ApiUser = api_user_module

        for name in (
            "EntertainmentConfiguration",
            "Group",
            "ResourceLink",
            "Rule",
            "Scene",
            "Schedule",
            "Sensor",
            "BehaviorInstance",
            "GeofenceClient",
            "SmartScene",
            "Device",
        ):
            setattr(hue_objects, name, types.SimpleNamespace())

        hue_objects.StreamEvent = Mock()

        modules = {
            "HueObjects": hue_objects,
            "configManager": types.SimpleNamespace(
                bridgeConfig=bridge_config
            ),
            "logManager": types.SimpleNamespace(
                logger=types.SimpleNamespace(
                    get_logger=lambda _name: self.logger
                )
            ),
            "functions.rules": types.SimpleNamespace(
                rulesProcessor=Mock()
            ),
            "functions.scripts": types.SimpleNamespace(
                behaviorScripts={}
            ),
            "functions.daylightSensor": types.SimpleNamespace(
                daylightSensor=Mock()
            ),
            "lights.discover": types.SimpleNamespace(
                manualAddLight=Mock(),
                scanForLights=Mock(),
            ),
            "lights.protocols": types.SimpleNamespace(
                hue=Mock()
            ),
            "services.entertainment": types.SimpleNamespace(
                entertainmentService=Mock()
            ),
            "services.updateManager": types.SimpleNamespace(
                githubCheck=Mock(),
                githubInstall=Mock(),
                versionCheck=Mock(),
            ),
        }

        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)

        self.restful = load(
            "pro_onboarding_restful",
            "flaskUI/restful.py",
        )
        self.v2restapi = load(
            "pro_onboarding_v2restapi",
            "flaskUI/v2restapi.py",
        )
        self.config_init = load(
            "pro_onboarding_config_init",
            "configManager/configInit.py",
        )

        self.app = Flask(__name__)
        self.app.testing = True

        api = Api(self.app)
        api.add_resource(
            self.restful.NewUser,
            "/api/",
        )
        api.add_resource(
            self.v2restapi.AuthV1,
            "/auth/v1",
        )

        self.client = self.app.test_client()
        self.bridge_config = bridge_config

    def test_classic_registration_survives_transition_to_pro(self):
        # The onboarding client first sees a normal Classic bridge.
        self.assertEqual(
            bridgeIdentity(self.config)["modelid"],
            "BSB002",
        )

        pressLinkButton(self.config)

        registration = self.client.post(
            "/api/",
            json={
                "devicetype": "pro-onboarding-lifecycle",
                "generateclientkey": True,
            },
        )

        self.assertEqual(registration.status_code, 200)

        credentials = registration.json[0]["success"]
        application_key = credentials["username"]
        client_key = credentials["clientkey"]

        self.assertTrue(application_key)
        self.assertTrue(client_key)
        self.assertNotEqual(application_key, client_key)
        self.assertIn(
            application_key,
            self.yaml_config["apiUsers"],
        )

        registered_user = self.yaml_config["apiUsers"][
            application_key
        ]

        # Persist exactly the whitelist payload written by configHandler.
        persisted_whitelist = {
            username: user.save()
            for username, user in self.yaml_config["apiUsers"].items()
        }

        self.assertIn(application_key, persisted_whitelist)
        persisted_user = persisted_whitelist[application_key]

        self.assertEqual(
            persisted_user["client_key"],
            client_key,
        )

        # Simulate the ApiUser reconstruction performed by load_config()
        # after a real process/container restart.
        api_user_class = type(registered_user)

        self.yaml_config["apiUsers"] = {
            username: api_user_class(
                username,
                data["name"],
                data["client_key"],
                data["create_date"],
                data["last_use_date"],
            )
            for username, data in persisted_whitelist.items()
        }

        restarted_user = self.yaml_config["apiUsers"][
            application_key
        ]

        self.assertIsNot(restarted_user, registered_user)
        self.assertEqual(
            restarted_user.username,
            application_key,
        )
        self.assertEqual(
            restarted_user.client_key,
            client_key,
        )

        # Switch the same persisted bridge identity/configuration to Pro.
        self.config_init.write_args(
            {
                "HOST_IP": "192.0.2.10",
                "FULLMAC": "02:00:00:00:00:01",
                "MAC": "020000000001",
                "BRIDGE_PROFILE": "pro",
            },
            self.yaml_config,
        )

        self.assertEqual(
            bridgeIdentity(self.config)["modelid"],
            "BSB003",
        )

        # Profile selection must preserve the API user restored after restart.
        self.assertIs(
            self.yaml_config["apiUsers"][application_key],
            restarted_user,
        )

        # Hue V2 authenticates with the V1 registration username as
        # hue-application-key after the bridge becomes BSB003.
        auth = self.client.get(
            "/auth/v1",
            headers={
                "hue-application-key": application_key,
            },
        )

        self.assertEqual(auth.status_code, 200)
        self.assertEqual(
            auth.headers.get("hue-application-id"),
            application_key,
        )

        # The DTLS client key is deliberately not the V2 application key.
        wrong_credential = self.client.get(
            "/auth/v1",
            headers={
                "hue-application-key": client_key,
            },
        )

        self.assertEqual(wrong_credential.status_code, 403)


if __name__ == "__main__":
    unittest.main()
