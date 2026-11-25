"""Lights created from the same model template must not share state.

Run with: PYTHONPATH=BridgeEmulator python -m unittest discover -s tests -v
"""

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

# Same stub the other tests use: never load a bridge config or parse CLI args.
if not isinstance(sys.modules.get("configManager"), SimpleNamespace):
    sys.modules["configManager"] = SimpleNamespace(bridgeConfig=SimpleNamespace(
        yaml_config={}, mark_dirty=Mock(), save_config=Mock()))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from flask import Flask  # noqa: E402
from HueObjects.Light import Light  # noqa: E402
from HueObjects.Sensor import Sensor  # noqa: E402
from flaskUI.core import views  # noqa: E402
from lights import discover  # noqa: E402
from lights.light_types import lightTypes  # noqa: E402
from sensors.sensor_types import sensorTypes  # noqa: E402


class _GroupZero:
    def __init__(self):
        self.id_v2 = "group-zero"

    def add_light(self, light):
        return None

    def groupZeroStream(self, rooms, lights):
        return None


class SharedLightStateTests(unittest.TestCase):
    def setUp(self):
        self.config = {"lights": {}, "groups": {"0": _GroupZero()}}
        self.bridge = patch.object(discover, "bridgeConfig", self.config)
        self.bridge.start()

    def tearDown(self):
        self.bridge.stop()
        self.config["lights"].clear()

    def test_new_lights_of_the_same_model_do_not_share_state(self):
        template = lightTypes["LCT015"]
        original_bri = template["state"]["bri"]
        original_ct = template["state"]["ct"]
        first = discover.addNewLight("LCT015", "Lamp A", "dummy", {"ip": "a"})
        second = discover.addNewLight("LCT015", "Lamp B", "dummy", {"ip": "b"})
        lamp_a = self.config["lights"][first]
        lamp_b = self.config["lights"][second]

        lamp_a.setV1State({"on": True, "bri": 12, "ct": 250})
        lamp_a.state["xy"][0] = 0.2
        lamp_a.config["startup"]["configured"] = False

        self.assertTrue(lamp_a.state["on"])
        self.assertFalse(lamp_b.state["on"])
        self.assertFalse(lamp_b.getV1Api()["state"]["on"])
        self.assertEqual(lamp_b.state["bri"], original_bri)
        self.assertEqual(lamp_b.state["ct"], original_ct)
        self.assertEqual(template["state"]["bri"], original_bri)
        self.assertIsNot(lamp_a.state, lamp_b.state)
        self.assertIsNot(lamp_a.state, template["state"])
        self.assertIsNot(lamp_a.state["xy"], lamp_b.state["xy"])
        self.assertIsNot(lamp_a.config, lamp_b.config)
        self.assertIsNot(lamp_a.config["startup"], lamp_b.config["startup"])
        self.assertFalse(template["state"]["on"])
        self.assertNotEqual(template["state"]["xy"][0], 0.2)
        self.assertTrue(template["config"]["startup"]["configured"])
        self.assertNotIn("name", template)
        self.assertNotIn("protocol", template)

        # Nested lists on gradient templates have to be copied too.
        strip_a_id = discover.addNewLight("LCX002", "Strip A", "dummy", {"points_capable": 5})
        strip_b_id = discover.addNewLight("LCX002", "Strip B", "dummy", {"points_capable": 5})
        strip_a = self.config["lights"][strip_a_id]
        strip_b = self.config["lights"][strip_b_id]
        strip_a.state["gradient"]["points"].append({"color": {"xy": {"x": 0.1, "y": 0.2}}})
        self.assertEqual(strip_b.state["gradient"]["points"], [])
        self.assertEqual(lightTypes["LCX002"]["state"]["gradient"]["points"], [])

    def test_constructor_copies_state_taken_from_the_template(self):
        template_state = lightTypes["LTW001"]["state"]
        template_config = lightTypes["LTW001"]["config"]
        first = Light({"name": "A", "modelid": "LTW001", "id_v1": "1",
                       "state": template_state, "config": template_config})
        second = Light({"name": "B", "modelid": "LTW001", "id_v1": "2",
                        "state": template_state, "config": template_config})
        try:
            first.state["on"] = True
            first.state["ct"] = 400
            self.assertFalse(second.state["on"])
            self.assertNotEqual(second.state["ct"], 400)
            self.assertFalse(template_state["on"])
            self.assertNotEqual(template_state["ct"], 400)
            self.assertIsNot(first.config, second.config)
        finally:
            del first, second

    def test_model_change_assigns_a_private_copy(self):
        lights = {}
        for light_id in ("1", "2"):
            lights[light_id] = Light({
                "id_v1": light_id, "modelid": "LWB010", "name": "Light " + light_id,
                "protocol": "dummy", "protocol_cfg": {}})
        app = Flask(__name__)
        try:
            with patch.object(views, "bridgeConfig", {"lights": lights}):
                for light_id in ("1", "2"):
                    with app.test_request_context(method="POST", json={light_id: "LCT015"}):
                        self.assertEqual(views.get_light_types(), "success")
            lights["1"].state["on"] = True
            lights["1"].state["ct"] = 153
            self.assertFalse(lights["2"].state["on"])
            self.assertNotEqual(lights["2"].state["ct"], 153)
            self.assertIsNot(lights["1"].state, lights["2"].state)
            self.assertIsNot(lights["1"].state, lightTypes["LCT015"]["state"])
            self.assertIsNot(lights["1"].config, lightTypes["LCT015"]["config"])
            self.assertFalse(lightTypes["LCT015"]["state"]["on"])
        finally:
            lights.clear()

    def test_api_documents_do_not_reuse_templates(self):
        first = discover.addNewLight("LCT015", "Lamp A", "dummy", {})
        second = discover.addNewLight("LCT015", "Lamp B", "dummy", {})
        lamp_a = self.config["lights"][first]
        lamp_b = self.config["lights"][second]

        api_a = lamp_a.getV1Api()
        api_b = lamp_b.getV1Api()
        self.assertIsNot(api_a, api_b)
        self.assertEqual(api_a["name"], "Lamp A")
        self.assertEqual(api_b["name"], "Lamp B")
        self.assertNotIn("name", lightTypes["LCT015"]["v1_static"])
        self.assertNotIn("uniqueid", lightTypes["LCT015"]["v1_static"])

        device_a = lamp_a.getDevice()
        device_b = lamp_b.getDevice()
        self.assertIsNot(device_a["product_data"], device_b["product_data"])
        self.assertIsNot(device_a["product_data"], lightTypes["LCT015"]["device"])
        self.assertEqual(device_a["product_data"]["model_id"], "LCT015")
        self.assertNotIn("model_id", lightTypes["LCT015"]["device"])

    def test_sensors_do_not_share_template_state_or_static_metadata(self):
        static = sensorTypes["SML001"]["ZLLPresence"]["static"]
        first = Sensor({"name": "Hall", "id_v1": "1", "modelid": "SML001", "type": "ZLLPresence",
                        "uniqueid": "00:17:88:01:00:00:00:01-02-0406"})
        second = Sensor({"name": "Kitchen", "id_v1": "2", "modelid": "SML001", "type": "ZLLPresence",
                         "uniqueid": "00:17:88:01:00:00:00:02-02-0406"})
        try:
            first.state["presence"] = True
            self.assertIsNot(first.state, second.state)
            self.assertNotEqual(second.state["presence"], True)
            api_a = first.getV1Api()
            api_b = second.getV1Api()
            self.assertIsNot(api_a, api_b)
            self.assertEqual(api_a["name"], "Hall")
            self.assertEqual(api_b["name"], "Kitchen")
            self.assertNotIn("name", static)
            self.assertNotIn("state", static)
        finally:
            del first, second


if __name__ == "__main__":
    unittest.main()
