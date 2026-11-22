from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from functions.colors import convert_xy, hsv_to_rgb  # noqa: E402
from lights.protocols import hyperion  # noqa: E402


def make_light(**state):
    return SimpleNamespace(protocol_cfg={"ip": "10.0.0.20", "jss_port": 19444},
                           state={"on": True, "bri": 200, "colormode": "xy", "xy": [0.3, 0.3],
                                  "hue": 0, "sat": 254, **state})


def sent(light, data):
    connection = Mock()
    with patch.dict(hyperion.Connections, {"10.0.0.20": connection}):
        hyperion.set_light(light, data)
    return connection.command.call_args.args[0]


class SetLightTests(unittest.TestCase):
    def test_xy_colour_is_sent(self):
        light = make_light(xy=[0.6, 0.3], bri=200)
        self.assertEqual(sent(light, {"xy": [0.6, 0.3]})["color"], convert_xy(0.6, 0.3, 200))

    def test_hs_colour_is_sent(self):
        light = make_light(colormode="hs", hue=21845, sat=200, bri=150)
        self.assertEqual(sent(light, {"hue": 21845, "sat": 200})["color"], hsv_to_rgb(21845, 200, 150))

    def test_off_clears_the_priority(self):
        self.assertEqual(sent(make_light(), {"on": False})["command"], "clear")


if __name__ == "__main__":
    unittest.main()
