"""Regression tests for Hue Entertainment process lifecycle."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1] / "BridgeEmulator"


def package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    return module


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(
        name,
        ROOT / relative_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeGroup:
    def __init__(self):
        self.id_v1 = "1"
        self.name = "Regression Entertainment Area"
        self.lights = []
        self.stream = {
            "proxymode": "auto",
            "proxynode": "/bridge",
            "active": True,
            "owner": None,
        }
        self.state = {
            "all_on": False,
            "any_on": False,
        }

        self.action = {"on": False}

    def getV2Api(self):
        return {"channels": []}

    def update_state(self):
        return dict(self.state)

    def update_attr(self, data):
        if "stream" in data:
            self.stream.update(data["stream"])

    def getV2GroupedLight(self):
        return {"id": "grouped-light", "type": "grouped_light"}


class FakeStdout:
    """Synthetic decrypted DTLS stream for lifecycle regression tests."""

    def __init__(self, process, group, eof_before_init=False):
        self.process = process
        self.group = group
        self.eof_before_init = eof_before_init
        self.one_byte_reads = 0
        self.read_after_kill = 0

    def read(self, size=-1):
        if self.process.killed:
            self.read_after_kill += 1

            # Safety valve for a buggy implementation: prevent an
            # accidental infinite busy-loop during the regression test.
            self.group.stream["active"] = False
            return b""

        if size == 1:
            self.one_byte_reads += 1

            if self.eof_before_init:
                return b""

            # 20 filler bytes, then the HueStream magic sequence.
            if self.one_byte_reads <= 20:
                return b"\x00"

            magic_index = self.one_byte_reads - 21
            if 0 <= magic_index < len(b"HueStream"):
                return bytes([b"HueStream"[magic_index]])

            return b"\x00"

        if size == 7:
            # Rest of the frame header: API version 1.
            return b"\x01" + b"\x00" * 6

        if size == 16:
            # Deliberately malformed next Entertainment frame (16-byte v1 header, no lights).
            return b"BADFRAME!" + (b"x" * 7)

        return b"\x00" * max(size, 0)


class FakeProcess:
    def __init__(self, group, eof_before_init=False):
        self.killed = False
        self.kill_calls = 0
        self.stdout = FakeStdout(
            self,
            group,
            eof_before_init=eof_before_init,
        )
        self.stderr = Mock()

        self.pid = 4242
        self.returncode = None

    def poll(self):
        return None

    def kill(self):
        self.kill_calls += 1
        self.killed = True


class EntertainmentLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.group = FakeGroup()

        bridge_config = {
            "groups": {
                self.group.id_v1: self.group,
            },
            "lights": {},
            "config": {
                "ipaddress": "127.0.0.1",
                "hue": {
                    "ip": "127.0.0.1",
                },
                "mqtt": {
                    "mqttUser": "",
                    "mqttPassword": "",
                    "mqttServer": "127.0.0.1",
                    "mqttPort": 1883,
                },
            },
        }

        self.logger = Mock()

        config_manager = types.ModuleType("configManager")
        config_manager.bridgeConfig = types.SimpleNamespace(
            yaml_config=bridge_config
        )

        log_manager = types.ModuleType("logManager")
        log_manager.logger = types.SimpleNamespace(
            get_logger=lambda _: self.logger,
            logLevel=20,
        )

        functions = package("functions")
        colors = types.ModuleType("functions.colors")
        colors.convert_rgb_xy = Mock(return_value=[0.0, 0.0])
        colors.convert_xy = Mock(return_value=(0, 0, 0))
        functions.colors = colors

        paho = package("paho")
        paho_mqtt = package("paho.mqtt")
        paho_publish = types.ModuleType("paho.mqtt.publish")
        paho_publish.multiple = Mock()
        paho.mqtt = paho_mqtt
        paho_mqtt.publish = paho_publish

        requests = types.ModuleType("requests")
        requests.get = Mock()
        requests.put = Mock()

        functions_entertainment = types.ModuleType("functions.entertainment")
        functions_entertainment.apply_stop_preference = Mock()
        functions_entertainment.snapshot_lights = Mock(return_value={})
        functions.entertainment = functions_entertainment

        hue_objects = types.ModuleType("HueObjects")
        hue_objects.StreamEvent = Mock()

        modules = {
            "configManager": config_manager,
            "logManager": log_manager,
            "functions": functions,
            "functions.colors": colors,
            "functions.entertainment": functions_entertainment,
            "HueObjects": hue_objects,
            "paho": paho,
            "paho.mqtt": paho_mqtt,
            "paho.mqtt.publish": paho_publish,
            "requests": requests,
        }

        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)

        self.entertainment = load_module(
            "entertainment_lifecycle_regression",
            "services/entertainment.py",
        )

        self.user = types.SimpleNamespace(
            username="regression-user",
            client_key="0123456789abcdef0123456789abcdef",
        )

    def run_service(self, eof_before_init=False):
        process = FakeProcess(
            self.group,
            eof_before_init=eof_before_init,
        )
        self.entertainment.Popen = Mock(return_value=process)
        # the fake stdout is always readable
        self.entertainment.select = types.SimpleNamespace(
            select=lambda r, w, x, timeout=None: (r, [], []))
        self.entertainment._sp = types.SimpleNamespace(run=Mock())
        self.entertainment.entertainmentService(
            self.group,
            self.user,
        )
        return process

    def test_malformed_frame_does_not_read_from_killed_openssl_process(self):
        process = self.run_service()

        self.assertEqual(
            process.stdout.read_after_kill,
            0,
            (
                "Entertainment worker read from openssl stdout after the "
                "process had already been killed. This can create the "
                "HueStream log/CPU busy loop reported in #984."
            ),
        )
        self.assertEqual(process.kill_calls, 1)
        self.assertFalse(self.group.stream["active"])

        self.logger.info.assert_any_call(
            "HueStream was missing in the frame, client disconnected"
        )

    def test_eof_before_huestream_initialization_stops_cleanly(self):
        process = self.run_service(eof_before_init=True)

        self.assertEqual(process.stdout.read_after_kill, 0)
        self.assertEqual(process.kill_calls, 1)
        self.assertFalse(self.group.stream["active"])

        messages = [call.args[0] for call in self.logger.info.call_args_list]
        self.assertIn(
            "entertainment: openssl stdout EOF before HueStream after %.1fs",
            messages,
        )


if __name__ == "__main__":
    unittest.main()
