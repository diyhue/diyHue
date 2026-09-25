"""Isolated wiring tests for profile-controlled bridge surfaces.

The test replaces the application runtime dependencies with small in-memory
fixtures.  That keeps it safe to run without a bridge configuration, sockets,
or network access while still exercising the real route and V2 functions.
"""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1] / "BridgeEmulator"
sys.path.insert(0, str(ROOT))


def load(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Response:
    def __init__(self, body):
        self.body = body
        self.headers = {}
        self.status_code = 200


class BridgeProfileSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "bridge_profile": "pro",
            "bridgeid": "001788FFFE000001",
            "ipaddress": "192.0.2.1",
            "name": "Synthetic Bridge",
            "swversion": "1972076030",
            "apiversion": "1.97.0",
            "mac": "00:17:88:00:00:01",
        }
        manager = types.ModuleType("configManager")
        manager.bridgeConfig = types.SimpleNamespace(yaml_config={"config": self.config})
        manager.runtimeConfig = types.SimpleNamespace(
            arg={"HTTP_PORT": 80, "MAC": "001788000001"}
        )

        logger = Mock()
        hue_objects = types.ModuleType("HueObjects")
        for name in (
            "ApiUser",
            "BehaviorInstance",
            "Device",
            "EntertainmentConfiguration",
            "GeofenceClient",
            "Group",
            "Scene",
            "SmartScene",
            "StreamEvent",
        ):
            setattr(hue_objects, name, types.SimpleNamespace())

        self.render_template = Mock(return_value="<root />")
        flask = types.ModuleType("flask")
        flask.Blueprint = lambda *_args, **_kwargs: types.SimpleNamespace(
            route=lambda *_route_args, **_route_kwargs: lambda function: function
        )
        flask.make_response = Response
        flask.redirect = flask.send_file = flask.url_for = Mock()
        flask.render_template = self.render_template
        flask.request = types.SimpleNamespace()

        flask_login = types.ModuleType("flask_login")
        flask_login.login_required = lambda function: function
        flask_login.login_user = flask_login.logout_user = Mock()

        requests = types.ModuleType("requests")
        requests.get = Mock()
        self.requests_get = requests.get

        flask_ui = types.ModuleType("flaskUI")
        flask_ui.__path__ = []
        flask_ui_core = types.ModuleType("flaskUI.core")
        flask_ui_core.User = type("User", (), {})
        flask_ui_core_forms = types.ModuleType("flaskUI.core.forms")
        flask_ui_core_forms.LoginForm = object
        services = types.ModuleType("services")
        services.__path__ = []
        lights = types.ModuleType("lights")
        lights.__path__ = []
        werkzeug = types.ModuleType("werkzeug")
        werkzeug.__path__ = []
        werkzeug_security = types.ModuleType("werkzeug.security")
        werkzeug_security.check_password_hash = Mock()
        werkzeug_security.generate_password_hash = Mock()

        modules = {
            "HueObjects": hue_objects,
            "configManager": manager,
            "logManager": types.SimpleNamespace(
                logger=types.SimpleNamespace(get_logger=lambda _name: logger)
            ),
            "flask": flask,
            "flask_restful": types.SimpleNamespace(Resource=object),
            "flask_login": flask_login,
            "flaskUI": flask_ui,
            "flaskUI.core": flask_ui_core,
            "flaskUI.core.forms": flask_ui_core_forms,
            "functions.daylightSensor": types.SimpleNamespace(daylightSensor=Mock()),
            "functions.scripts": types.SimpleNamespace(behaviorScripts={}),
            "lights": lights,
            "lights.discover": types.SimpleNamespace(scanForLights=Mock()),
            "lights.light_types": types.SimpleNamespace(lightTypes={}),
            "requests": requests,
            "services": services,
            "services.entertainment": types.SimpleNamespace(entertainmentService=Mock()),
            "werkzeug": werkzeug,
            "werkzeug.security": werkzeug_security,
        }
        self.module_patch = patch.dict(sys.modules, modules)
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)

        self.v2 = load("profile_surface_v2", "flaskUI/v2restapi.py")
        self.views = load("profile_surface_views", "flaskUI/core/views.py")
        self.updates = load("profile_surface_updates", "services/updateManager.py")

    def test_v2_bridge_device_uses_profile_identity(self):
        device = self.v2.v2BridgeDevice()
        self.assertEqual(device["metadata"]["archetype"], "bridge_v3")
        self.assertEqual(device["product_data"]["model_id"], "BSB003")
        self.assertEqual(device["product_data"]["product_archetype"], "bridge_v3")
        self.assertEqual(device["product_data"]["product_name"], "Hue Bridge")
        self.assertEqual(device["product_data"]["software_version"], "1.78.2071442000")

        self.config["bridge_profile"] = "classic"
        device = self.v2.v2BridgeDevice()
        self.assertEqual(device["metadata"]["archetype"], "bridge_v2")
        self.assertEqual(device["product_data"]["model_id"], "BSB002")
        self.assertEqual(device["product_data"]["product_archetype"], "bridge_v2")
        self.assertEqual(device["product_data"]["product_name"], "Philips hue")
        self.assertEqual(device["product_data"]["software_version"], "1.97.2076030")

    def test_description_is_classic_only(self):
        self.assertEqual(self.views.description_xml(), ("", 404))

        self.config["bridge_profile"] = "classic"
        response = self.views.description_xml()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, "<root />")
        self.render_template.assert_called_once()

    def test_firmware_check_skips_pro_and_keeps_classic_request(self):
        self.updates.versionCheck()
        self.requests_get.assert_not_called()

        self.config["bridge_profile"] = "classic"
        self.requests_get.return_value = types.SimpleNamespace(
            status_code=200,
            text='{"updates": []}',
        )
        self.updates.versionCheck()
        self.requests_get.assert_called_once_with(
            "https://firmware.meethue.com/v1/checkupdate/?deviceTypeId=BSB002&version=1972076030"
        )



    def test_bridge_home_child_references_bridge_device(self):
        self.config["timezone"] = "Europe/Amsterdam"
        self.v2.bridgeConfig["groups"] = {
            "0": types.SimpleNamespace(id_v2="group-zero", type="LightGroup")
        }
        self.v2.bridgeConfig["device"] = {}

        bridge = self.v2.v2Bridge()
        home = self.v2.v2BridgeHome()

        self.assertIn(
            {"rid": bridge["owner"]["rid"], "rtype": "device"},
            home["children"],
        )
        self.assertNotIn(
            {"rid": bridge["id"], "rtype": "device"},
            home["children"],
        )

if __name__ == "__main__":
    unittest.main()
