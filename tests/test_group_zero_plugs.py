import sys
from pathlib import Path
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "BridgeEmulator"))

from HueObjects import setGroupAction  # noqa: E402


class FakeLight:
    def __init__(self, id_v1, modelid, on=True):
        self.id_v1 = id_v1
        self.modelid = modelid
        self.protocol = "native"
        self.protocol_cfg = {"ip": "127.0.0.1"}
        self.state = {"on": on, "bri": 100}
        self.updateLightState = Mock()
        self.setV1State = Mock()


class FakeGroup:
    def __init__(self, id_v1, lights):
        self.id_v1 = id_v1
        self.lights = [lambda light=light: light for light in lights]
        self.action = {}
        self.state = {}

    def update_state(self):
        return {"any_on": False, "all_on": False, "avr_bri": 100, "avr_ct": 300}


class GroupZeroPlugTests(unittest.TestCase):
    """Group 0 means "all lights" and must not switch sockets.

    Sockets appear as Hue on/off plug-in units (LOM001/LOM004/...), so
    turning every light off would cut power to whatever is plugged in.
    """

    def setUp(self):
        self.bulb = FakeLight("1", "LWB010")
        self.plug = FakeLight("15", "LOM001", on=True)
        self.group = FakeGroup("0", [self.bulb, self.plug])

    def test_all_lights_off_leaves_plug_untouched(self):
        setGroupAction(self.group, {"on": False})
        self.assertEqual(self.bulb.setV1State.call_count, 1)
        self.assertEqual(self.plug.setV1State.call_count, 0)
        self.assertTrue(self.plug.state["on"], "plug must stay switched on")

    def test_all_lights_on_leaves_plug_untouched(self):
        setGroupAction(self.group, {"on": True})
        self.assertEqual(self.bulb.setV1State.call_count, 1)
        self.assertEqual(self.plug.setV1State.call_count, 0)

    def test_regular_group_still_switches_plug(self):
        group = FakeGroup("3", [self.bulb, self.plug])
        setGroupAction(group, {"on": False})
        self.assertEqual(self.plug.setV1State.call_count, 1)


if __name__ == "__main__":
    unittest.main()
