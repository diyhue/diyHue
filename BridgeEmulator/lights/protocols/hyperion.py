import json
import logManager
import re
import socket
from functions.colors import convert_rgb_xy, convert_xy, hsv_to_rgb

logging = logManager.logger.get_logger(__name__)

Connections = {}

PRIORITY = 75

def discover(detectedLights):
    logging.debug("Hyperion: <discover> invoked!")
    group = ("239.255.255.250", 1900)
    message = "\r\n".join([
        'M-SEARCH * HTTP/1.1',
        'HOST: 239.255.255.250:1900',
        'MAN: "ssdp:discover"',
        'ST: urn:hyperion-project.org:device:basic:1'
    ])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(5)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.sendto(message.encode(), group)
    while True:
        try:
            response = sock.recv(1024).decode('utf-8').split("\r\n")
            properties = {"rgb": False, "ct": False}
            for line in response:
                if line[:3] == "USN":
                    properties["id"] = line[10:]
                elif line[:13] == "HYPERION-NAME":
                    properties["name"] = line[15:]
                elif line[:17] == "HYPERION-FBS-PORT":
                    properties["fbs_port"] = line[19:]
                elif line[:17] == "HYPERION-JSS-PORT":
                    properties["jss_port"] = line[19:]
                elif line[:8] == "LOCATION":
                    properties["ip"] = line.split(":")[2][2:]
                elif line[:6] == "SERVER":
                    properties["version"] = re.match("Hyperion/\S*", line)
            if "name" in properties:
                detectedLights.append({"protocol": "hyperion", "name": properties["name"], "modelid": "LCT015", "protocol_cfg": properties})

        except socket.timeout:
            logging.debug('Hyperion search end')
            sock.close()
            break


def set_light(light, data):
    ip = light.protocol_cfg["ip"]
    if ip in Connections:
        c = Connections[ip]
    else:
        c = HyperionConnection(ip, light.protocol_cfg["jss_port"])
        Connections[ip] = c

    if "on" in data and data["on"] == False:
        request_data = {"command": "clear", "priority": PRIORITY}
    else:
        request_data = {"command": "color", "origin": "diyHue", "priority": PRIORITY}
        if light["state"]["colormode"] == "hs":
            if "hue" in data and "sat" in data:
                color = hsv_to_rgb(data["hue"], data["sat"], light["state"]["bri"])
            else:
                color = hsv_to_rgb(light["state"]["hue"], light["state"]["sat"], light["state"]["bri"])
        else:
            color = convert_xy(light["state"]["xy"][0], light["state"]["xy"][1], light["state"]["bri"])
        request_data["color"] = color

    c.command(request_data)


def get_light_state(light):
    ip = light.protocol_cfg["ip"]
    if ip in Connections:
        c = Connections[ip]
    else:
        c = HyperionConnection(ip, light.protocol_cfg["jss_port"])
        Connections[ip] = c

    state = {"on": False}

    c.command({"command":"serverinfo"})
    try:
        response = c.recv(1024 * 1024).decode('utf-8').split("\r\n")
        for data in response:
            info = json.loads(data)
            if "success" in info and info["success"] == True and len(info["info"]["priorities"]) > 0:
                activeColor = info["info"]["priorities"][0]
                if activeColor["priority"] == PRIORITY:
                    rgb = activeColor["value"]["RGB"]
                    state["on"] = True
                    state["xy"] = convert_rgb_xy(rgb[0],rgb[1],rgb[2])
                    state["bri"] = max(rgb[0],rgb[1],rgb[2])
                    state["colormode"] = "xy"
    except Exception as e:
        logging.warning(e)
        return { 'reachable': False }

    return state

class HyperionConnection(object):
    _connected = False
    _socket = None
    _host_ip = ""

    def __init__(self, ip, port):
        self._ip = ip
        self._port = port

    def connect(self):
        self.disconnect()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(5)
        self._socket.connect((self._ip, int(self._port)))
        self._connected = True

    def disconnect(self):
        self._connected = False
        if self._socket:
            self._socket.close()
        self._socket = None

    def send(self, data: bytes, flags: int = 0):
        try:
            if not self._connected:
                self.connect()
            self._socket.send(data, flags)
        except Exception as e:
            self._connected = False
            raise e

    def recv(self, bufsize: int, flags: int = 0) -> bytes:
        try:
            if not self._connected:
                self.connect()
            return self._socket.recv(bufsize, flags)
        except Exception as e:
            self._connected = False
            raise e

    def command(self, data):
        try:
            msg = json.dumps(data) + "\r\n"
            self.send(msg.encode())
        except Exception as e:
            logging.warning("Hyperion command error: %s", e)
