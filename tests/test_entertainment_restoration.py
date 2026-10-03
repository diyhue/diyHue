"""Run with: PYTHONPATH=BridgeEmulator python -m unittest discover -s tests -v."""

from copy import deepcopy
from io import BytesIO
import gc
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid
import weakref

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

# Import the real models, drivers, worker and API handlers without loading or
# writing a user's bridge configuration or parsing unittest's CLI arguments.
CONFIG = {}
config_manager = SimpleNamespace(bridgeConfig=SimpleNamespace(
    yaml_config=CONFIG, mark_dirty=Mock(), save_config=Mock()))
sys.modules["configManager"] = config_manager

import logManager
logManager.logger.configure_logger("CRITICAL")
from HueObjects import eventstream
from HueObjects.Light import Light
from HueObjects.EntertainmentConfiguration import EntertainmentConfiguration
from HueObjects.BehaviorInstance import BehaviorInstance
from functions.entertainment import RECIPES, STOP_SCRIPT_ID, apply_stop_preference, snapshot_lights
from services import entertainment
from flask import Flask
from flaskUI import restful, v2restapi
from lights.protocols import mqtt, native_multi


class RestorationTests(unittest.TestCase):
    def setUp(self):
        CONFIG.clear()
        CONFIG.update({"lights": {}, "groups": {}, "behavior_instance": {},
                       "apiUsers": {}, "config": {"ipaddress": "127.0.0.1"}})
        self.group = EntertainmentConfiguration({"id_v1": "5", "name": "TV"})
        CONFIG["groups"]["5"] = self.group
        self.user = SimpleNamespace(username="test", client_key="test-key")
        CONFIG["apiUsers"]["test"] = self.user
        self.app = Flask(__name__)
        self.light = self.add_light()
        eventstream.clear()
        entertainment.lastAppliedFrame.clear()

    def add_light(self, model="LCT015", protocol="dummy", **state):
        lid = str(len(CONFIG["lights"]) + 1)
        light = Light({"id_v1": lid, "modelid": model, "name": "Light " + lid,
                       "protocol": protocol, "protocol_cfg": {"points_capable": 5}})
        light.state.update({"on": True, "bri": 87, "colormode": "ct", "ct": 320})
        light.state.update(state)
        CONFIG["lights"][lid] = light
        self.group.add_light(light)
        return light

    def tearDown(self):
        # Models emit events from __del__; destroy groups before their weak
        # light references expire, and collect mock/model cycles during tests.
        self.group.lights.clear()
        CONFIG.clear()
        v2restapi.v2Resources["entertainment_configuration"].clear()
        self.group = None
        self.light = None
        gc.collect()

    def preference(self, end_state="last_state", **configuration):
        config = {"end_state": end_state, "where": [{"group": {
            "rid": self.group.getV2Api()["id"],
            "rtype": "entertainment_configuration"}}]}
        config.update(configuration)
        behavior = BehaviorInstance({"metadata": {"name": "state_after_streaming"},
                                     "script_id": STOP_SCRIPT_ID, "enabled": True,
                                     "configuration": config})
        CONFIG["behavior_instance"][behavior.id_v2] = behavior
        return behavior

    def stream_changed(self):
        for light in CONFIG["lights"].values():
            light.state.update({"mode": "streaming", "on": True, "bri": 240,
                                "xy": [0.17, 0.7], "colormode": "xy"})

    def finish(self, snapshots, proc=None, relay=None):
        proc = proc or Mock()
        self.group.stream.update({"active": True, "_proc": proc, "owner": "test"})
        entertainment.finish_entertainment(self.group, proc, relay, snapshots)
        return proc

    def test_last_state_restores_each_light_including_off(self):
        self.preference()
        off = self.add_light(on=False, bri=45, ct=400)
        snapshots = snapshot_lights(self.group)
        self.stream_changed()
        with patch.object(off, "setV1State", wraps=off.setV1State) as send:
            self.finish(snapshots)
        self.assertEqual(send.call_args.args[0], {"on": False})
        self.assertFalse(off.state["on"])
        self.assertEqual((off.state["bri"], off.state["ct"]), (45, 400))
        self.assertEqual((self.light.state["bri"], self.light.state["ct"]), (87, 320))
        self.assertEqual(self.light.state["colormode"], "ct")
        self.assertEqual(self.group.state, {"any_on": True, "all_on": False})
        self.assertFalse(self.group.stream["active"])
        self.assertIsNone(self.group.stream["owner"])
        self.assertNotIn("_proc", self.group.stream)

    def test_snapshot_is_a_deep_copy_and_not_persisted(self):
        self.light.state.update({"colormode": "xy", "xy": [0.4, 0.5]})
        snapshots = snapshot_lights(self.group)
        self.light.state["xy"][0] = 0.9
        self.assertEqual(snapshots["1"]["state"]["xy"], [0.4, 0.5])
        self.assertNotIn("snapshot", self.group.save())
        self.assertNotIn("snapshot", self.group.stream)

    def test_restoration_only_sends_the_active_colour_mode(self):
        self.preference()
        for mode, values, expected in (
            ("ct", {"ct": 330}, {"ct"}),
            ("xy", {"xy": [0.4, 0.5]}, {"xy"}),
            ("hs", {"hue": 12345, "sat": 100}, {"hue", "sat"}),
        ):
            with self.subTest(mode=mode):
                self.light.state.update({"colormode": mode, **values})
                snapshots = snapshot_lights(self.group)
                self.stream_changed()
                with patch.object(self.light, "setV1State", wraps=self.light.setV1State) as send:
                    apply_stop_preference(self.group, CONFIG, snapshots)
                colour_keys = {"ct", "xy", "hue", "sat"} & send.call_args.args[0].keys()
                self.assertEqual(colour_keys, expected)

    def test_gradient_snapshot_restores_independent_points(self):
        self.preference()
        light = self.add_light(model="LCX004", colormode="xy", gradient={"points": [
            {"color": {"xy": {"x": 0.4, "y": 0.5}}},
            {"color": {"xy": {"x": 0.2, "y": 0.3}}}]})
        snapshots = snapshot_lights(self.group)
        light.state["gradient"]["points"][0]["color"]["xy"]["x"] = 0.9
        with patch.object(light, "setV1State", wraps=light.setV1State) as send:
            apply_stop_preference(self.group, CONFIG, snapshots)
        self.assertEqual(send.call_args.args[0]["gradient"], snapshots[light.id_v1]["state"]["gradient"])
        self.assertNotIn("ct", send.call_args.args[0])

    def test_off_ignores_stale_recipe_reference(self):
        self.preference("off", end_scene={"rtype": "recipe", "rid": next(iter(RECIPES))})
        self.finish(snapshot_lights(self.group))
        self.assertFalse(self.light.state["on"])
        self.assertFalse(self.group.state["any_on"])

    def test_pause_keeps_last_frame_and_ignores_stale_recipe(self):
        self.preference("do_nothing", end_scene={"rtype": "recipe", "rid": next(iter(RECIPES))})
        snapshots = snapshot_lights(self.group)
        self.stream_changed()
        with patch.object(self.light, "setV1State") as send:
            self.finish(snapshots)
        send.assert_not_called()
        self.assertEqual((self.light.state["bri"], self.light.state["xy"]), (240, [0.17, 0.7]))
        self.assertEqual(self.light.state["colormode"], "xy")
        self.assertEqual(self.light.state["mode"], "homeautomation")
        self.assertFalse(self.group.stream["active"])

    def test_all_seven_presets_send_colour_and_brightness(self):
        expected = {
            "Bright": (254, [0.4596, 0.4105]), "Dimmed": (77, [0.4596, 0.4105]),
            "Nightlight": (1, [0.5610, 0.4042]), "Relax": (143, [0.5019, 0.4152]),
            "Read": (254, [0.4450, 0.4067]), "Concentrate": (254, [0.3691, 0.3719]),
            "Energize": (254, [0.3143, 0.3301]),
        }
        for rid, recipe in RECIPES.items():
            with self.subTest(recipe=recipe["name"]):
                CONFIG["behavior_instance"].clear()
                self.preference("scene", end_scene={"rtype": "recipe", "rid": rid})
                self.light.state["on"] = False
                self.finish(snapshot_lights(self.group))
                self.assertTrue(self.light.state["on"])
                self.assertEqual((self.light.state["bri"], self.light.state["xy"]), expected[recipe["name"]])

    def test_recipe_uses_temperature_for_white_lights_and_brightness_for_dimmers(self):
        self.preference("scene", end_scene={"rtype": "recipe", "rid": "a1f7da49-d181-4328-abea-68c9dc4b5416"})
        white = self.add_light(model="LTW001")
        dimmer = self.add_light(model="LWB010")
        self.stream_changed()  # Includes injected xy, which is not a capability.
        with patch.object(white, "setV1State", wraps=white.setV1State) as send_white, \
                patch.object(dimmer, "setV1State", wraps=dimmer.setV1State) as send_dimmer:
            self.finish(snapshot_lights(self.group))
        self.assertEqual(send_white.call_args.args[0], {"on": True, "bri": 143, "ct": 454})
        self.assertEqual(send_dimmer.call_args.args[0], {"on": True, "bri": 143})

    def test_disabled_unrelated_and_unknown_preferences_leave_output_unchanged(self):
        for kind in ("disabled", "other_area", "other_script", "unknown_recipe", "unsupported_state", "missing"):
            with self.subTest(kind=kind):
                CONFIG["behavior_instance"].clear()
                behavior = self.preference("off")
                if kind == "disabled":
                    behavior.enabled = False
                elif kind == "other_area":
                    behavior.configuration["where"][0]["group"]["rid"] = str(uuid.uuid4())
                elif kind == "other_script":
                    behavior.script_id = str(uuid.uuid4())
                elif kind == "unknown_recipe":
                    behavior.configuration.update({"end_state": "scene", "end_scene": {"rtype": "recipe", "rid": "unknown"}})
                elif kind == "unsupported_state":
                    behavior.configuration["end_state"] = "unverified_pause_value"
                else:
                    CONFIG["behavior_instance"].clear()
                with patch.object(self.light, "setV1State") as send:
                    self.finish(snapshot_lights(self.group))
                send.assert_not_called()

    def test_changed_preference_is_read_at_shutdown(self):
        behavior = self.preference("last_state")
        snapshots = snapshot_lights(self.group)
        self.stream_changed()
        behavior.update_attr({"configuration": {"end_state": "off"}})
        self.finish(snapshots)
        self.assertFalse(self.light.state["on"])

    def test_replacement_light_does_not_receive_the_old_snapshot(self):
        self.preference()
        snapshots = snapshot_lights(self.group)
        self.light.id_v2 = str(uuid.uuid4())
        with patch.object(self.light, "setV1State") as send:
            apply_stop_preference(self.group, CONFIG, snapshots)
        send.assert_not_called()

    def test_expired_light_reference_is_skipped(self):
        light = Light({"id_v1": "99", "modelid": "LCT015", "name": "Removed"})
        ref = weakref.ref(light)
        self.group.lights.append(ref)
        del light
        self.assertIsNone(ref())
        self.preference("off")
        self.finish(snapshot_lights(self.group))
        self.assertFalse(self.light.state["on"])

    def test_stale_worker_does_not_restore_or_disconnect_new_session(self):
        self.preference("off")
        old, current, relay = Mock(), Mock(), Mock()
        self.group.stream.update({"active": True, "_proc": current})
        entertainment.finish_entertainment(self.group, old, relay, snapshot_lights(self.group))
        self.assertTrue(self.light.state["on"])
        self.assertIs(self.group.stream["_proc"], current)
        relay.disconnect.assert_not_called()

    def test_relay_is_released_before_restoration_and_cleanup_is_idempotent(self):
        self.preference("off")
        snapshots = snapshot_lights(self.group)
        relay = Mock()
        order = []
        relay.disconnect.side_effect = lambda: order.append("disconnect")
        with patch.object(self.light, "setV1State", side_effect=lambda *a, **k: order.append("restore")):
            proc = self.finish(snapshots, relay=relay)
            entertainment.finish_entertainment(self.group, proc, relay, snapshots)
        self.assertEqual(order, ["disconnect", "restore"])

    def test_one_failed_light_does_not_prevent_other_lights_restoring(self):
        self.preference("off")
        other = self.add_light()
        with patch.object(self.light, "setV1State", side_effect=RuntimeError("device failed")):
            self.finish(snapshot_lights(self.group))
        self.assertFalse(other.state["on"])
        self.assertFalse(self.group.stream["active"])

    def test_stop_emits_normal_light_and_inactive_area_events(self):
        self.preference("off")
        eventstream.clear()
        self.finish(snapshot_lights(self.group))
        updates = [item for event in eventstream for item in event.get("data", [])]
        light = next(item for item in updates if item["type"] == "light")
        area = next(item for item in updates if item["type"] == "entertainment_configuration")
        grouped = next(item for item in updates if item["type"] == "grouped_light")
        self.assertEqual(light["mode"], "normal")
        self.assertFalse(light["on"]["on"])
        self.assertEqual(area["status"], "inactive")
        self.assertFalse(grouped["on"]["on"])

    def test_off_uses_real_mqtt_and_native_multi_drivers(self):
        self.preference("off")
        for protocol in ("mqtt", "native_multi"):
            with self.subTest(protocol=protocol):
                self.light.protocol = protocol
                self.light.state["on"] = True
                self.light.protocol_cfg = {"ip": "192.0.2.1", "light_nr": 1,
                    "command_topic": "light/set", "mqtt_server": {
                        "mqttServer": "192.0.2.2", "mqttPort": 1883,
                        "mqttUser": "", "mqttPassword": ""}}
                with patch.object(mqtt.publish, "multiple") as publish, \
                        patch.object(native_multi.requests, "put") as put:
                    self.finish(snapshot_lights(self.group))
                if protocol == "mqtt":
                    self.assertEqual(json.loads(publish.call_args.args[0][0]["payload"])["state"], "OFF")
                else:
                    self.assertEqual(put.call_args.kwargs["json"], {1: {"on": False}})

    def test_real_worker_snapshots_before_a_frame_overwrites_state(self):
        self.preference()
        self.light.state["on"] = False
        before = deepcopy(self.light.state)
        self.group.stream["active"] = True
        frame = bytearray(59)
        frame[:9] = b"HueStream"
        frame[9] = 2
        frame[53:59] = b"\xff\xff\x00\x00\x00\x00"
        proc = Mock(stdout=BytesIO(bytes(frame) * 2), stderr=BytesIO())
        proc.poll.return_value = None
        with patch.object(entertainment, "Popen", return_value=proc), \
                patch("subprocess.run", return_value=SimpleNamespace(stdout="test", stderr="")), \
                patch.object(entertainment.select, "select", return_value=([proc.stdout], [], [])):
            entertainment.entertainmentService(self.group, self.user)
        self.assertEqual(self.light.state, before)
        self.assertFalse(self.group.stream["active"])

    def test_worker_restores_and_cleans_up_on_startup_failure(self):
        self.preference()
        self.light.state["on"] = False
        self.group.stream["active"] = True
        with patch.object(entertainment, "Popen", side_effect=OSError("openssl missing")), \
                patch("subprocess.run"):
            entertainment.entertainmentService(self.group, self.user)
        self.assertFalse(self.light.state["on"])
        self.assertFalse(self.group.stream["active"])

    def test_both_api_starts_use_shared_worker_without_changing_snapshot_values(self):
        self.preference()
        for api in ("v1", "v2"):
            with self.subTest(api=api):
                self.group.stream["active"] = False
                before = deepcopy(self.light.state)
                module = restful if api == "v1" else v2restapi
                with patch.object(module, "Thread") as thread, \
                        patch.object(v2restapi, "sleep"), \
                        patch.object(restful, "rulesProcessor"), \
                        patch.object(v2restapi, "getObject", return_value=self.group), \
                        self.app.test_request_context(method="PUT", json=(
                            {"stream": {"active": True}} if api == "v1" else {"action": "start"}),
                            headers={"hue-application-key": "test"}):
                    if api == "v1":
                        restful.Element().put("test", "groups", "5")
                        restful.Element().put("test", "groups", "5")
                    else:
                        v2restapi.ClipV2ResourceId().put("entertainment_configuration", self.group.id_v2)
                        v2restapi.ClipV2ResourceId().put("entertainment_configuration", self.group.id_v2)
                self.assertEqual(thread.call_count, 1)
                self.assertIs(thread.call_args.kwargs["target"], entertainment.entertainmentService)
                self.assertEqual(self.light.state, before)

    def test_both_api_stops_leave_restoration_to_worker(self):
        self.preference("off")
        for api in ("v1", "v2"):
            with self.subTest(api=api):
                snapshots = snapshot_lights(self.group)
                proc = Mock()
                self.group.stream.update({"active": True, "_proc": proc})
                self.stream_changed()
                with patch.object(restful, "rulesProcessor"), \
                        patch.object(v2restapi, "getObject", return_value=self.group), \
                        self.app.test_request_context(method="PUT", json=(
                            {"stream": {"active": False}} if api == "v1" else {"action": "stop"}),
                            headers={"hue-application-key": "test"}):
                    if api == "v1":
                        restful.Element().put("test", "groups", "5")
                    else:
                        v2restapi.ClipV2ResourceId().put("entertainment_configuration", self.group.id_v2)
                proc.kill.assert_called_once()
                self.assertEqual(self.light.state["mode"], "streaming")
                entertainment.finish_entertainment(self.group, proc, None, snapshots)
                self.assertEqual(self.light.state["mode"], "homeautomation")
                self.assertFalse(self.light.state["on"])

    def test_hue_relay_stop_sends_json(self):
        CONFIG["config"]["hue"] = {"hueUser": "test"}
        relay = entertainment.HueConnection("192.0.2.1")
        with patch.object(entertainment.requests, "put") as put:
            relay.disconnect()
        self.assertEqual(put.call_args.kwargs["json"], {"stream": {"active": False}})
        self.assertEqual(put.call_args.kwargs["timeout"], 3)


if __name__ == "__main__":
    unittest.main()
