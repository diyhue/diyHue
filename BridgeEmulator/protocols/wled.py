import socket
import urllib.request
import json
import random
import math
import sys
import logging
from functions import light_types, nextFreeId
from functions.colors import convert_rgb_xy, convert_xy, rgbBrightness
from time import sleep
from zeroconf import IPVersion, ServiceBrowser, ServiceStateChange, Zeroconf, ZeroconfServiceTypes


mdns = []
Connections = {}


def on_mdns_discover(zeroconf, service_type, name, state_change):
    global mdns
    if "wled" in name and state_change is ServiceStateChange.Added:
        info = zeroconf.get_service_info(service_type, name)
        if info:
            addresses = ["%s" % (socket.inet_ntoa(addr))
                         for addr in info.addresses]
            mdns.append([addresses[0], name])


def discover(bridge_config, new_lights):
    logging.debug('wled discovery started')
    ip_version = IPVersion.V4Only
    zeroconf = Zeroconf(ip_version=ip_version)
    services = ["_http._tcp.local."]
    browser = ServiceBrowser(zeroconf, services, handlers=[on_mdns_discover])
    sleep(2)
    for device in mdns:
        try:
            x = WledDevice(device[0], device[1])
            device_exist = False
            for light in bridge_config["lights_address"].keys():
                if bridge_config["lights_address"][light]["protocol"] == "wled" and bridge_config["lights_address"][light]["name"] == x.name:
                    device_exist = True
                    bridge_config["lights_address"][light]["ip"] = properties["ip"]
                    logging.debug("wled light with mdns name " +
                                  properties["id"] + " already exist, updating ip...")
                    break
            if (not device_exist):
                modelid = "LCT015"
                light_name = x.name
                logging.debug("Adding wled device " + device[1])
                new_light_id = nextFreeId(bridge_config, "lights")
                bridge_config["lights"][new_light_id] = {"state": light_types[modelid]["state"], "type": light_types[modelid]["type"], "name": light_name, "uniqueid": "4a:e0:ad:7f:cf:" + str(
                    random.randrange(0, 99)) + "-1", "modelid": modelid, "manufacturername": "Philips", "swversion": light_types[modelid]["swversion"]}
                new_lights.update({new_light_id: {"name": light_name}})
                bridge_config["lights_address"][new_light_id] = {
                    "ip": device[0], "mdns_name": device[1], "protocol": "wled", "backlight": False, "ledCount": x.ledCount, "name": light_name}
        except:
            break


def set_light(address, light, data, rgb=None):
    ip = address['ip']
    if ip in Connections:
        c = Connections[ip]
    else:
        c = WledDevice(ip, address['mdns_name'])
        Connections[ip] = c

    state = {}
    for k, v in data.items():
        if k == "on":
            if v:
                state['on'] = True
            else:
                state['on'] = False
        elif k == "bri":
            state['bri'] = v+1
        elif k == "ct":
            kelvin = round(translateRange(v, 153, 500, 6500, 2000))
            color = kelvinToRgb(kelvin)
            state = {"seg": [{"col": [[color[0], color[1], color[2]]]}]}
            c.sendJson(state)
        elif k == "xy":
            if rgb:
                color = rgbBrightness(rgb, 255)
                state = {"seg": [{"col": [[color[0], color[1], color[2]]]}]}
                c.sendJson(state)
            else:
                color = convert_xy(v[0], v[1], 255)
                state = {"seg": [{"col": [[color[0], color[1], color[2]]]}]}
        c.sendJson(state)


def get_light_state(address, light):
    state = {}
    with urllib.request.urlopen('http://' + address['ip'] + '/json/state') as resp:
        data = json.loads(resp.read())
        state['on'] = data['on']
        state['bri'] = data['bri']
        # Weird division by zero when a color is 0
        r = int(data['seg'][0]['col'][0][0])+1
        g = int(data['seg'][0]['col'][1][0])+1
        b = int(data['seg'][0]['col'][2][0])+1
        state['xy'] = convert_rgb_xy(r, g, b)
        state["colormode"] = "xy"
        return state

def translateRange(value, leftMin, leftMax, rightMin, rightMax):
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin
    valueScaled = float(value - leftMin) / float(leftSpan)
    return rightMin + (valueScaled * rightSpan)

def clamp(num, min_val, max_val):
     return max(min(num, max_val), min_val)

def kelvinToRgb(temp):
    tmpKelvin = clamp(temp, 1000, 40000) / 100
    r =  255 if tmpKelvin <= 66 else clamp(329.698727446 * pow(tmpKelvin - 60, -0.1332047592), 0, 255)
    g = clamp(99.4708025861 * math.log(tmpKelvin) - 161.1195681661, 0, 255) if tmpKelvin <= 66 else clamp(288.1221695283 * (pow(tmpKelvin - 60, -0.0755148492)), 0, 255)
    if tmpKelvin >= 66: 
        b = 255 
    elif tmpKelvin <= 19:
        b = 0
    else:
        b = clamp(138.5177312231 * math.log(tmpKelvin - 10) - 305.0447927307, 0, 255)
    return [r,g,b]


class WledDevice:

    def __init__(self, ip, mdns_name):
        self.ip = ip
        self.name = mdns_name.split(".")[0]
        self.url = 'http://' + self.ip
        self.ledCount = 0
        self.getLedCount()

    def getLightState(self):
        with urllib.request.urlopen(self.url + '/json') as resp:
            data = json.loads(resp.read())
            return data

    def getLedCount(self):
        self.ledCount = self.getLightState()['info']['leds']['count']

    def sendJson(self, data):
        req = urllib.request.Request(self.url + "/json")
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        jsondata = json.dumps(data)
        jsondataasbytes = jsondata.encode('utf-8')
        req.add_header('Content-Length', len(jsondataasbytes))
        response = urllib.request.urlopen(req, jsondataasbytes)
