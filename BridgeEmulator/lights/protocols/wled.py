import socket
import urllib.request
import json
import random
import math
import sys
import logManager
from functions.colors import convert_rgb_xy, convert_xy, rgbBrightness
from time import sleep
from zeroconf import IPVersion, ServiceBrowser, ServiceStateChange, Zeroconf, ZeroconfServiceTypes

logging = logManager.logger.get_logger(__name__)

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


def discover(detectedLights):
    logging.info('wled discovery started')
    ip_version = IPVersion.V4Only
    zeroconf = Zeroconf(ip_version=ip_version)
    services = ["_http._tcp.local."]
    browser = ServiceBrowser(zeroconf, services, handlers=[on_mdns_discover])
    sleep(2)
    for device in mdns:
        try:
            x = WledDevice(device[0], device[1])
            logging.info("Found wled: " + device[1])
            modelid = "LST002"
            lightName = x.name
            detectedLights.append({"protocol": "wled", "name": lightName, "modelid": modelid, "protocol_cfg": {
                              "ip": device[0], "ledCount": x.ledCount, "mdns_name": device[1], "mac": x.mac}})
        except:
            break

def set_light(light, data, rgb):
    ip = light.protocol_cfg['ip']
    if ip in Connections:
        c = Connections[ip]
    else:
        c = WledDevice(ip, light.protocol_cfg['mdns_name'])
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
    r = 255 if tmpKelvin <= 66 else clamp(
        329.698727446 * pow(tmpKelvin - 60, -0.1332047592), 0, 255)
    g = clamp(99.4708025861 * math.log(tmpKelvin) - 161.1195681661, 0,
              255) if tmpKelvin <= 66 else clamp(288.1221695283 * (pow(tmpKelvin - 60, -0.0755148492)), 0, 255)
    if tmpKelvin >= 66:
        b = 255
    elif tmpKelvin <= 19:
        b = 0
    else:
        b = clamp(138.5177312231 * math.log(tmpKelvin - 10) -
                  305.0447927307, 0, 255)
    return [r, g, b]


class WledDevice:

    def __init__(self, ip, mdns_name):
        self.ip = ip
        self.name = mdns_name.split(".")[0]
        self.url = 'http://' + self.ip
        self.ledCount = 0
        self.mac = None
        self.getInitialState()

    def getLightState(self):
        with urllib.request.urlopen(self.url + '/json') as resp:
            data = json.loads(resp.read())
            return data

    def getInitialState(self):
        self.getLedCount()
        self.getMacAddr()

    def getLedCount(self):
        self.ledCount = self.getLightState()['info']['leds']['count']

    def getMacAddr(self):
        self.mac = ':'.join(self.getLightState()[
                            'info']['mac'][i:i+2] for i in range(0, 12, 2))

    def sendJson(self, data):
        req = urllib.request.Request(self.url + "/json")
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        jsondata = json.dumps(data)
        jsondataasbytes = jsondata.encode('utf-8')
        req.add_header('Content-Length', len(jsondataasbytes))
        response = urllib.request.urlopen(req, jsondataasbytes)
