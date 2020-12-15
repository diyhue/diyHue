import json
import logging
import random
import re

import socket

from functions import light_types, nextFreeId
from functions.colors import convert_rgb_xy, convert_xy, hsv_to_rgb

Connections = {}

PRIORITY = 75

def discover(bridge_config, new_lights):
    logging.debug("Hyperion: <discover> invoked!")
    group = ("239.255.255.250", 1900)
    message = "\r\n".join([
        'M-SEARCH * HTTP/1.1',
        'HOST: 239.255.255.250:1900',
        'MAN: "ssdp:discover"',
        'ST: urn:hyperion-project.org:device:basic:1'
    ])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(10)
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
            device_exist = False
            for light in bridge_config["lights_address"].keys():
                if bridge_config["lights_address"][light]["protocol"] == "hyperion" and  bridge_config["lights_address"][light]["uid"] == properties["id"]:
                    device_exist = True
                    bridge_config["lights_address"][light]["ip"] = properties["ip"]
                    logging.debug("light id " + properties["id"] + " already exist, updating ip...")
                    break
            if (not device_exist and "name" in properties):
                light_name = properties["name"]
                logging.debug("Add Hyperion: " + properties["id"])
                modelid = "LCT015"
                manufacturername = "Philips"
                swversion = "1.46.13_r26312"

                new_light_id = nextFreeId(bridge_config, "lights")

        
                # Create the light with data from auto discovery
                bridge_config["lights"][new_light_id] = { "name": light_name, "uniqueid": "4a:e0:ad:7f:cf:" + str(random.randrange(0, 99)) + "-1" }
                bridge_config["lights"][new_light_id]["modelid"] = modelid
                #bridge_config["lights"][new_light_id]["swversion"] = properties["version"]
                bridge_config["lights"][new_light_id]["manufacturername"] = manufacturername
                bridge_config["lights"][new_light_id]["swversion"] = swversion
                
                # Set the type, a default state and possibly a light config
                bridge_config["lights"][new_light_id]["type"] = light_types[modelid]["type"]
                bridge_config["lights"][new_light_id]["state"] = light_types[modelid]["state"]
                bridge_config["lights"][new_light_id]["config"] = light_types[modelid]["config"]

                # Add the lights to new lights, so it shows up in the search screen
                new_lights.update({new_light_id: {"name": light_name}})
                
                # Save the configuration
                bridge_config["lights_address"][new_light_id] = { "protocol": "hyperion", "uid": properties["id"], "ip": properties["ip"] }
                bridge_config["lights_address"][new_light_id]["fbs_port"] = properties["fbs_port"]
                bridge_config["lights_address"][new_light_id]["jss_port"] = properties["jss_port"]


        except socket.timeout:
            logging.debug('Hyperion search end')
            sock.close()
            break


def set_light(address, light, data):
    ip = address["ip"]
    if ip in Connections:
        c = Connections[ip]
    else:
        c = HyperionConnection(ip, address["jss_port"])
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


def get_light_state(address, light):
    ip = address["ip"]
    if ip in Connections:
        c = Connections[ip]
    else:
        c = HyperionConnection(ip, address["jss_port"])
        Connections[ip] = c

    state = {"on": False}

    c.command({"command":"serverinfo"})
    try:
        response = c.recv(1024 * 1024).decode('utf-8').split("\r\n")
        for data in response:
            info = json.loads(data)
            if "success" in info and info["success"] == True and len(info["info"]["priorities"]) >= 0:
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
