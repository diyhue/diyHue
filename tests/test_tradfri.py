import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

import logManager  # noqa: E402
logManager.logger.configure_logger("CRITICAL")
from functions.colors import convert_rgb_xy, hsv_to_rgb  # noqa: E402
from lights.protocols import tradfri  # noqa: E402


def make_light(**state):
    return SimpleNamespace(protocol_cfg={"ip": "10.0.0.3", "id": 65537, "identity": "me", "psk": "key"},
                           state={"hue": 0, "sat": 254, "bri": 200, **state})


def sent_payload(light, data):
    with patch.object(tradfri, "check_output", return_value=b"") as run:
        tradfri.set_light(light, data)
    cmd = run.call_args.args[0]
    return json.loads(cmd[cmd.index("-e") + 1])["3311"][0]


def xy_payload(hue, sat, bri):
    x, y = convert_rgb_xy(*hsv_to_rgb(hue, sat, bri))
    return int(x * 65535), int(y * 65535)


class HueSatTests(unittest.TestCase):
    def test_hue_alone_uses_the_lights_saturation_and_brightness(self):
        payload = sent_payload(make_light(sat=127, bri=150), {"hue": 21845})
        self.assertEqual((payload["5709"], payload["5710"]), xy_payload(21845, 127, 150))

    def test_sat_alone_uses_the_lights_hue(self):
        payload = sent_payload(make_light(hue=43690), {"sat": 200, "bri": 254})
        self.assertEqual((payload["5709"], payload["5710"]), xy_payload(43690, 200, 254))


if __name__ == "__main__":
    unittest.main()
