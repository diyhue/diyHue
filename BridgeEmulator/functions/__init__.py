from .colors import *
from .html import *
from .ssdp import *


def nextFreeId(bridge_config, element):
    i = 1
    while (str(i)) in bridge_config[element]:
        i += 1
    return str(i)


light_types = {"LCT015": {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}, "type": "Extended color light", "swversion": "1.29.0_r21169"}, "LST002": {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}, "type": "Color light", "swversion": "5.105.0.21169"}, "LWB010": {"state": {"on": False, "bri": 254,"alert": "none", "reachable": True}, "type": "Dimmable light", "swversion": "1.15.0_r18729"}, "LTW001": {"state": {"on": False, "colormode": "ct", "alert": "none", "reachable": True, "bri": 254, "ct": 230}, "type": "Color temperature light", "swversion": "5.50.1.19085"}, "Plug 01": {"state": {"on": False, "alert": "none", "reachable": True}, "type": "On/Off plug-in unit", "swversion": "V1.04.12"}}
