from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from lights.protocols import wled  # noqa: E402


def device_reporting(bri):
    device = object.__new__(wled.WledDevice)
    segment = {"bri": bri, "on": True, "col": [[255, 128, 0]]}
    device.getLightState = lambda: {"state": {"seg": [segment]}}
    return device


class BrightnessTests(unittest.TestCase):
    def test_reported_brightness_stays_in_hue_range(self):
        self.assertEqual(device_reporting(255).getSegState(0)["bri"], 254)
        self.assertEqual(device_reporting(1).getSegState(0)["bri"], 1)
        self.assertEqual(device_reporting(0).getSegState(0)["bri"], 1)

    def test_brightness_round_trips(self):
        device = device_reporting(0)
        light = SimpleNamespace(protocol_cfg={"segmentId": 0}, dynamics={})
        for bri in (1, 127, 254):
            with self.subTest(bri=bri):
                with patch.object(device, "sendJson", create=True) as send:
                    wled.send_light_data(device, light, {"bri": bri})
                sent = send.call_args.args[0]["seg"][0]["bri"]
                self.assertEqual(device_reporting(sent).getSegState(0)["bri"], bri)


if __name__ == "__main__":
    unittest.main()
