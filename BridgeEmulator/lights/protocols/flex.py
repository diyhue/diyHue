import json
import logManager
import socket
from functions.colors import convert_xy, rgbBrightness

logging = logManager.logger.get_logger(__name__)

def pretty_json(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))

def set_light(light, data):
    msg = bytearray()
    if "on" in data:
        if data["on"]:
            msg = bytearray([0x71, 0x23, 0x8a, 0x0f])
        else:
            msg = bytearray([0x71, 0x24, 0x8a, 0x0f])
        checksum = sum(msg) & 0xFF
        msg.append(checksum)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.sendto(msg, (light.protocol_cfg["ip"], 48899))
    if ("bri" in data and light.state["colormode"] == "xy") or "xy" in data:
        logging.info(pretty_json(data))
        bri = data["bri"] if "bri" in data else light.state["bri"]
        xy = data["xy"] if "xy" in data else light.state["xy"]
        if "rgb" in data:
            color = rgbBrightness(data["rgb"], bri)
        else:
            color = convert_xy(xy[0], xy[1], bri)
        msg = bytearray([0x41, color[0], color[1], color[2], 0x00, 0xf0, 0x0f])
        checksum = sum(msg) & 0xFF
        msg.append(checksum)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.sendto(msg, (light.protocol_cfg["ip"], 48899))
    elif ("bri" in data and light.state["colormode"] == "ct") or "ct" in data:
        bri = data["bri"] if "bri" in data else light.state["bri"]
        msg = bytearray([0x41, 0x00, 0x00, 0x00, bri, 0x0f, 0x0f])
        checksum = sum(msg) & 0xFF
        msg.append(checksum)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.sendto(msg, (light.protocol_cfg["ip"], 48899))

def get_light_state(light):
    return {}

def discover():
    pass
