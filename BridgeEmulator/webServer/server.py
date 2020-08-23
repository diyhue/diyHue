import configManager
import base64
import copy
import logManager
import json
import random
import requests
import ssl
import socket
import uuid
from functions.json import pretty_json
from time import sleep
from functions import light_types, nextFreeId
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from functions.lightRequest import sendLightRequest
from functions.html import (description, webform_hue, webform_linkbutton,
                            webform_milight, webformDeconz, webformTradfri, lightsHttp)
from protocols.hue.sensors import addHueSwitch, addHueMotionSensor, motionDetected
from protocols import yeelight, tasmota, shelly, native_single, native_multi, esphome, mqtt, hyperion, deconz, tradfri
from functions.request import sendRequest
from socketserver import ThreadingMixIn
from subprocess import Popen, check_output
from protocols import tradfri
from threading import Thread
from datetime import datetime, timedelta
from protocols.hue.scheduler import generateDxState, rulesProcessor
from functions.updateGroup import updateGroupStats

bridge_config = configManager.bridgeConfig.json_config
logging = logManager.logger.get_logger(__name__)
new_lights = configManager.runtimeConfig.newLights
dxState = configManager.runtimeConfig.dxState
HOST_HTTP_PORT = configManager.runtimeConfig.arg["HTTP_PORT"]

# random functions here are only used in the webserver class

def switchScene(group, direction):
    group_scenes = []
    current_position = -1
    possible_current_position = -1 # used in case the brigtness was changes and will be no perfect match (scene lightstates vs light states)
    break_next = False
    for scene in bridge_config["scenes"]:
        if bridge_config["groups"][group]["lights"][0] in bridge_config["scenes"][scene]["lights"]:
            group_scenes.append(scene)
            if break_next: # don't lose time as this is the scene we need
                break
            is_current_scene = True
            is_possible_current_scene = True
            for light in bridge_config["scenes"][scene]["lightstates"]:
                for key in bridge_config["scenes"][scene]["lightstates"][light].keys():
                    if key == "xy":
                        if not bridge_config["scenes"][scene]["lightstates"][light]["xy"][0] == bridge_config["lights"][light]["state"]["xy"][0] and not bridge_config["scenes"][scene]["lightstates"][light]["xy"][1] == bridge_config["lights"][light]["state"]["xy"][1]:
                            is_current_scene = False
                    else:
                        if not bridge_config["scenes"][scene]["lightstates"][light][key] == bridge_config["lights"][light]["state"][key]:
                            is_current_scene = False
                            if not key == "bri":
                                is_possible_current_scene = False
            if is_current_scene:
                current_position = len(group_scenes) -1
                if direction == -1 and len(group_scenes) != 1:
                    break
                elif len(group_scenes) != 1:
                    break_next = True
            elif  is_possible_current_scene:
                possible_current_position = len(group_scenes) -1

    matched_scene = ""
    if current_position + possible_current_position == -2:
        logging.info("current scene not found, reset to zero")
        if len(group_scenes) != 0:
            matched_scene = group_scenes[0]
        else:
            logging.info("error, no scenes found")
            return
    elif current_position != -1:
        if len(group_scenes) -1 < current_position + direction:
            matched_scene = group_scenes[0]
        else:
            matched_scene = group_scenes[current_position + direction]
    elif possible_current_position != -1:
        if len(group_scenes) -1 < possible_current_position + direction:
            matched_scene = group_scenes[0]
        else:
            matched_scene = group_scenes[possible_current_position + direction]
    logging.info("matched scene " + bridge_config["scenes"][matched_scene]["name"])

    for light in bridge_config["scenes"][matched_scene]["lights"]:
        bridge_config["lights"][light]["state"].update(bridge_config["scenes"][matched_scene]["lightstates"][light])
        if "xy" in bridge_config["scenes"][matched_scene]["lightstates"][light]:
            bridge_config["lights"][light]["state"]["colormode"] = "xy"
        elif "ct" in bridge_config["scenes"][matched_scene]["lightstates"][light]:
            bridge_config["lights"][light]["state"]["colormode"] = "ct"
        elif "hue" or "sat" in bridge_config["scenes"][matched_scene]["lightstates"][light]:
            bridge_config["lights"][light]["state"]["colormode"] = "hs"
        sendLightRequest(light, bridge_config["scenes"][matched_scene]["lightstates"][light], bridge_config["lights"], bridge_config["lights_address"])
        updateGroupStats(light, bridge_config["lights"], bridge_config["groups"])


def generate_unique_id():
    rand_bytes = [random.randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0],rand_bytes[1],rand_bytes[2])

def iter_ips(port):
    argsDict = configManager.runtimeConfig.arg
    HOST_IP = argsDict["HOST_IP"]
    scan_on_host_ip = argsDict["scanOnHostIP"]
    ip_range_start = argsDict["IP_RANGE_START"]
    ip_range_end = argsDict["IP_RANGE_END"]
    host = HOST_IP.split('.')
    if scan_on_host_ip:
        yield ('127.0.0.1', port)
        return
    for addr in range(ip_range_start, ip_range_end + 1):
        host[3] = str(addr)
        test_host = '.'.join(host)
        if test_host != HOST_IP:
            yield (test_host, port)

def scanHost(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.02) # Very short timeout. If scanning fails this could be increased
    result = sock.connect_ex((host, port))
    sock.close()
    return result

def find_hosts(port):
    validHosts = []
    for host, port in iter_ips(port):
        if scanHost(host, port) == 0:
            hostWithPort = '%s:%s' % (host, port)
            validHosts.append(hostWithPort)

    return validHosts

def find_light_in_config_from_uid(bridge_config, unique_id):
    for light in bridge_config["lights"].keys():
        if bridge_config["lights"][light]["uniqueid"] == unique_id:
            return light
    return None

def getLightsVersions():
    lights = {}
    githubCatalog = json.loads(requests.get('https://raw.githubusercontent.com/diyhue/Lights/master/catalog.json').text)
    for light in bridge_config["lights_address"].keys():
        if bridge_config["lights_address"][light]["protocol"] in ["native_single", "native_multi"]:
            if "light_nr" not in bridge_config["lights_address"][light] or bridge_config["lights_address"][light]["light_nr"] == 1:
                currentData = json.loads(requests.get('http://' + bridge_config["lights_address"][light]["ip"] + '/detect', timeout=3).text)
                lights[light] = {"name": currentData["name"], "currentVersion": currentData["version"], "lastVersion": githubCatalog[currentData["type"]]["version"], "firmware": githubCatalog[currentData["type"]]["filename"]}
    return lights

def manageDeviceLights(lights_state):
    protocol = bridge_config["lights_address"][list(lights_state.keys())[0]]["protocol"]
    payload = {}
    for light in lights_state.keys():
        if protocol == "native_multi":
            payload[bridge_config["lights_address"][light]["light_nr"]] = lights_state[light]
        elif protocol in ["native", "native_single", "milight"]:
            sendLightRequest(light, lights_state[light], bridge_config["lights"], bridge_config["lights_address"])
            if protocol == "milight": #hotfix to avoid milight hub overload
                sleep(0.05)
        else:
            Thread(target=sendLightRequest, args=[light, lights_state[light], bridge_config["lights"], bridge_config["lights_address"]]).start()
            sleep(0.1)
    if protocol == "native_multi":
        requests.put("http://"+bridge_config["lights_address"][list(lights_state.keys())[0]]["ip"]+"/state", json=payload, timeout=3)


def generate_light_name(base_name, light_nr):
    # Light name can only contain 32 characters
    suffix = ' %s' % light_nr
    return '%s%s' % (base_name[:32-len(suffix)], suffix)


def updateLight(light, filename):
    firmware = requests.get('https://github.com/diyhue/Lights/raw/master/Arduino/bin/' + filename, allow_redirects=True)
    open('/tmp/' + filename, 'wb').write(firmware.content)
    file = {'update': open('/tmp/' + filename,'rb')}
    update = requests.post('http://' + bridge_config["lights_address"][light]["ip"] + '/update', files=file)

def splitLightsToDevices(group, state, scene={}):
    groups = []
    if group == "0":
        for grp in bridge_config["groups"].keys():
            groups.append(grp)
    else:
        groups.append(group)

    lightsData = {}
    if len(scene) == 0:
        for grp in groups:
            if "bri_inc" in state:
                bridge_config["groups"][grp]["action"]["bri"] += int(state["bri_inc"])
                if bridge_config["groups"][grp]["action"]["bri"] > 254:
                    bridge_config["groups"][grp]["action"]["bri"] = 254
                elif bridge_config["groups"][grp]["action"]["bri"] < 1:
                    bridge_config["groups"][grp]["action"]["bri"] = 1
                del state["bri_inc"]
                state.update({"bri": bridge_config["groups"][grp]["action"]["bri"]})
            elif "ct_inc" in state:
                bridge_config["groups"][grp]["action"]["ct"] += int(state["ct_inc"])
                if bridge_config["groups"][grp]["action"]["ct"] > 500:
                    bridge_config["groups"][grp]["action"]["ct"] = 500
                elif bridge_config["groups"][grp]["action"]["ct"] < 153:
                    bridge_config["groups"][grp]["action"]["ct"] = 153
                del state["ct_inc"]
                state.update({"ct": bridge_config["groups"][grp]["action"]["ct"]})
            elif "hue_inc" in state:
                bridge_config["groups"][grp]["action"]["hue"] += int(state["hue_inc"])
                if bridge_config["groups"][grp]["action"]["hue"] > 65535:
                    bridge_config["groups"][grp]["action"]["hue"] -= 65535
                elif bridge_config["groups"][grp]["action"]["hue"] < 0:
                    bridge_config["groups"][grp]["action"]["hue"] += 65535
                del state["hue_inc"]
                state.update({"hue": bridge_config["groups"][grp]["action"]["hue"]})
            for light in bridge_config["groups"][grp]["lights"]:
                lightsData[light] = state
    else:
        lightsData = scene

    # Make sure any lights haven't been deleted
    lightsData = {k: v for k, v in lightsData.items() if k in bridge_config["lights_address"]}

    deviceIp = {}
    if group != "0": #only set light state if light is part of group
        lightdel=[]
        for light in lightsData.keys():
            if light not in bridge_config["groups"][group]["lights"]:
                lightdel.append(light)
        for light in lightdel:
            del lightsData[light]

    for light in lightsData.keys():
        if bridge_config["lights_address"][light]["ip"] not in deviceIp:
            deviceIp[bridge_config["lights_address"][light]["ip"]] = {}
        deviceIp[bridge_config["lights_address"][light]["ip"]][light] = lightsData[light]
    for ip in deviceIp:
        Thread(target=manageDeviceLights, args=[deviceIp[ip]]).start()
    ### update light details
    for light in lightsData.keys():
        if "xy" in lightsData[light]:
            bridge_config["lights"][light]["state"]["colormode"] = "xy"
        elif "ct" in lightsData[light]:
            bridge_config["lights"][light]["state"]["colormode"] = "ct"
        elif "hue" in lightsData[light]:
            bridge_config["lights"][light]["state"]["colormode"] = "hs"
        # if "transitiontime" in lightsData[light]:
        #     del lightsData[light]["transitiontime"]
        bridge_config["lights"][light]["state"].update(lightsData[light])
    updateGroupStats(list(lightsData.keys())[0], bridge_config["lights"], bridge_config["groups"])


def groupZero(state):
    lightsData = {}
    for light in bridge_config["lights"].keys():
        lightsData[light] = state
    Thread(target=splitLightsToDevices, args=["0", {}, lightsData]).start()
    for group in bridge_config["groups"].keys():
        bridge_config["groups"][group]["action"].update(state)
        if "on" in state:
            bridge_config["groups"][group]["state"]["any_on"] = state["on"]
            bridge_config["groups"][group]["state"]["all_on"] = state["on"]

def scan_for_lights(): #scan for ESP8266 lights and strips
    Thread(target=yeelight.discover, args=[bridge_config, new_lights]).start()
    Thread(target=tasmota.discover, args=[bridge_config, new_lights]).start()
    Thread(target=shelly.discover, args=[bridge_config, new_lights]).start()
    Thread(target=esphome.discover, args=[bridge_config, new_lights]).start()
    Thread(target=mqtt.discover, args=[bridge_config, new_lights]).start()
    Thread(target=hyperion.discover, args=[bridge_config, new_lights]).start()
    Thread(target=deconz.scanDeconz).start()
    #return all host that listen on port 80
    device_ips = find_hosts(80)
    logging.info(pretty_json(device_ips))
    #logging.debug('devs', device_ips)
    for ip in device_ips:
        try:
            response = requests.get("http://" + ip + "/detect", timeout=3)
            if response.status_code == 200:
                # XXX JSON validation
                try:
                    device_data = json.loads(response.text)
                    logging.info(pretty_json(device_data))
                    if "modelid" in device_data:
                        logging.info(ip + " is " + device_data['name'])
                        if "protocol" in device_data:
                            protocol = device_data["protocol"]
                        else:
                            protocol = "native"

                        # Get number of lights
                        lights = 1
                        if "lights" in device_data:
                            lights = device_data["lights"]

                        # Add each light to config
                        logging.info("Add new light: " + device_data["name"])
                        for x in range(1, lights + 1):
                            light = find_light_in_config_from_mac_and_nr(bridge_config,
                                    device_data['mac'], x)

                            # Try to find light in existing config
                            if light:
                                logging.info("Updating old light: " + device_data["name"])
                                # Light found, update config
                                light_address = bridge_config["lights_address"][light]
                                light_address["ip"] = ip
                                light_address["protocol"] = protocol
                                if "version" in device_data:
                                    light_address.update({
                                        "version": device_data["version"],
                                        "type": device_data["type"],
                                        "name": device_data["name"]
                                    })
                                continue

                            new_light_id = nextFreeId(bridge_config, "lights")

                            light_name = generate_light_name(device_data['name'], x)

                            # Construct the configuration for this light from a few sources, in order of precedence
                            # (later sources override earlier ones).
                            # Global defaults
                            new_light = {
                                "manufacturername": "Philips",
                                "uniqueid": generate_unique_id(),
                            }
                            # Defaults for this specific modelid
                            if device_data["modelid"] in light_types:
                                new_light.update(light_types[device_data["modelid"]])
                                # Make sure to make a copy of the state dictionary so we don't share the dictionary
                                new_light['state'] = light_types[device_data["modelid"]]['state'].copy()
                            # Overrides from the response JSON
                            new_light["modelid"] = device_data["modelid"]
                            new_light["name"] = light_name

                            # Add the light to new lights, and to bridge_config (in two places)
                            new_lights[new_light_id] = {"name": light_name}
                            bridge_config["lights"][new_light_id] = new_light
                            bridge_config["lights_address"][new_light_id] = {
                                "ip": ip,
                                "light_nr": x,
                                "protocol": protocol,
                                "mac": device_data["mac"]
                            }
                except ValueError:
                    logging.info('Decoding JSON from %s has failed', ip)
        except Exception as e:
            logging.info("ip %s is unknown device: %s", ip, e)
            #raise
    tradfri.discover.scanTradfri()
    configManager.bridgeConfig.save_config()

def find_light_in_config_from_mac_and_nr(bridge_config, mac_address, light_nr):
    for light_id, light_address in bridge_config["lights_address"].items():
        if (light_address["protocol"] in ["native", "native_single",  "native_multi"]
                and light_address["mac"] == mac_address
                and ('light_nr' not in light_address or
                    light_address['light_nr'] == light_nr)):
            return light_id
    return None

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


# TODO: Fix this class, replacing with response built elsewhere, should not have logic here

class S(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'nginx'
    sys_version = ''

    logging = logManager.logger.get_logger("WebServer")

    def log_message(self, format, *args) -> None:
        try:
            if not args[1] == str(200):
                self.logging.warning("%s - %s" %
                             (self.address_string(),
                              format%args))
            else:
                self.logging.debug("%s - %s" %
                                 (self.address_string(),
                                  format%args))
        except:
            self.logging.warning("Could not get return code: %s - %s" %
                               (self.address_string(),
                                format % args))
        return

    def _set_headers(self):

        self.send_response(200)

        mimetypes = {"json": "application/json", "map": "application/json", "html": "text/html", "xml": "application/xml", "js": "text/javascript", "css": "text/css", "png": "image/png"}
        if self.path.endswith((".html",".json",".css",".map",".png",".js", ".xml")):
            self.send_header('Content-type', mimetypes[self.path.split(".")[-1]])
        elif self.path.startswith("/api"):
            self.send_header('Content-type', mimetypes["json"])
        else:
            self.send_header('Content-type', mimetypes["html"])

    def _set_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Hue\"')
        self.send_header('Content-type', 'text/html')

    def _set_end_headers(self, data):
        self.send_header('Content-Length', len(data))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods',
                         'GET, OPTIONS, POST, PUT, DELETE')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        #Some older Philips Tv's sent non-standard HTTP GET requests with a Content-Lenght and a
        # body. The HTTP body needs to be consumed and ignored in order to request be handle correctly.
        cwd = configManager.bridgeConfig.projectDir
        self.read_http_request_body()

        if self.path == '/' or self.path == '/index.html':
            self._set_headers()
            f = open(cwd + '/web-ui/index.html')
            self._set_end_headers(bytes(f.read(), "utf8"))
        elif self.path == "/debug/clip.html":
            self._set_headers()
            f = open(cwd + '/debug/clip.html', 'rb')
            self._set_end_headers(f.read())
        elif self.path == "/factory-reset":
            self._set_headers()
            previous = configManager.bridgeConfig.reset_config()
            previous = configManager.bridgeConfig.configDir + previous
            self._set_end_headers(bytes(json.dumps([{"success":{"configuration":"reset","backup-filename": previous}}] ,separators=(',', ':'),ensure_ascii=False), "utf8"))
        elif self.path == '/config.js':
            self._set_headers()
            #create a new user key in case none is available
            if len(bridge_config["config"]["whitelist"]) == 0:
                bridge_config["config"]["whitelist"]["web-ui-" + str(random.randrange(0, 99999))] = {"create date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),"last use date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),"name": "WebGui User"}
            self._set_end_headers(bytes('window.config = { API_KEY: "' + list(bridge_config["config"]["whitelist"])[0] + '",};', "utf8"))
        elif self.path.endswith((".css",".map",".png",".js",".webmanifest")):
            self._set_headers()
            f = open(cwd + '/web-ui' + self.path, 'rb')
            self._set_end_headers(f.read())
        elif self.path == '/description.xml':
            self._set_headers()
            HOST_HTTP_PORT = configManager.runtimeConfig.arg["HTTP_PORT"]
            mac = configManager.runtimeConfig.arg["MAC"]
            self._set_end_headers(bytes(description(bridge_config["config"]["ipaddress"], HOST_HTTP_PORT, mac, bridge_config["config"]["name"]), "utf8"))
        elif self.path == "/lights.json":
            self._set_headers()
            self._set_end_headers(bytes(json.dumps(getLightsVersions() ,separators=(',', ':'),ensure_ascii=False), "utf8"))
        elif self.path.startswith("/lights"):
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            if "light" in get_parameters:
                updateLight(get_parameters["light"][0], get_parameters["filename"][0])
            self._set_end_headers(bytes(lightsHttp(), "utf8"))

        elif self.path == '/save':
            self._set_headers()
            configManager.bridgeConfig.save_config()
            self._set_end_headers(bytes(json.dumps([{"success":{"configuration":"saved","filename":"/opt/hue-emulator/config.json"}}] ,separators=(',', ':'),ensure_ascii=False), "utf8"))
        elif self.path.startswith("/tradfri"): #setup Tradfri gateway
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            if "code" in get_parameters:
                #register new identity
                new_identity = "Hue-Emulator-" + str(random.randrange(0, 999))
                registration = json.loads(check_output("./coap-client-linux -m post -u \"Client_identity\" -k \"" + get_parameters["code"][0] + "\" -e '{\"9090\":\"" + new_identity + "\"}' \"coaps://" + get_parameters["ip"][0] + ":5684/15011/9063\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
                bridge_config["tradfri"] = {"psk": registration["9091"], "ip": get_parameters["ip"][0], "identity": new_identity}
                lights_found = tradfri.discover.scanTradfri()
                if lights_found == 0:
                    self._set_end_headers(bytes(webformTradfri() + "<br> No lights where found", "utf8"))
                else:
                    self._set_end_headers(bytes(webformTradfri() + "<br> " + str(lights_found) + " lights where found", "utf8"))
            else:
                self._set_end_headers(bytes(webformTradfri(), "utf8"))
        elif self.path.startswith("/milight"): #setup milight bulb
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            if "device_id" in get_parameters:
                #register new mi-light
                new_light_id = nextFreeId(bridge_config, "lights")
                bridge_config["lights"][new_light_id] = {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}, "type": "Extended color light", "name": "MiLight " + get_parameters["mode"][0] + " " + get_parameters["device_id"][0], "uniqueid": "1a2b3c4" + str(random.randrange(0, 99)), "modelid": "LCT015", "swversion": "1.46.13_r26312", "manufacturername": "Philips"}
                new_lights.update({new_light_id: {"name": "MiLight " + get_parameters["mode"][0] + " " + get_parameters["device_id"][0]}})
                bridge_config["lights_address"][new_light_id] = {"device_id": get_parameters["device_id"][0], "mode": get_parameters["mode"][0], "group": int(get_parameters["group"][0]), "ip": get_parameters["ip"][0], "protocol": "milight"}
                self._set_end_headers(bytes(webform_milight() + "<br> Light added", "utf8"))
            else:
                self._set_end_headers(bytes(webform_milight(), "utf8"))
        elif self.path.startswith("/hue"): #setup hue bridge
            if "linkbutton" in self.path: #Hub button emulated
                if self.headers['Authorization'] == None:
                    self._set_AUTHHEAD()
                    self._set_end_headers(bytes('You are not authenticated', "utf8"))
                    pass
                elif self.headers['Authorization'] == 'Basic ' + bridge_config["linkbutton"]["linkbutton_auth"]:
                    get_parameters = parse_qs(urlparse(self.path).query)
                    if "action=Activate" in self.path:
                        self._set_headers()
                        bridge_config["config"]["linkbutton"] = False
                        bridge_config["linkbutton"]["lastlinkbuttonpushed"] = str(int(datetime.now().timestamp()))
                        configManager.bridgeConfig.save_config()
                        self._set_end_headers(bytes(webform_linkbutton() + "<br> You have 30 sec to connect your device", "utf8"))
                    elif "action=Exit" in self.path:
                        self._set_AUTHHEAD()
                        self._set_end_headers(bytes('You are succesfully disconnected', "utf8"))
                    elif "action=ChangePassword" in self.path:
                        self._set_headers()
                        tmp_password = str(base64.b64encode(bytes(get_parameters["username"][0] + ":" + get_parameters["password"][0], "utf8"))).split('\'')
                        bridge_config["linkbutton"]["linkbutton_auth"] = tmp_password[1]
                        configManager.bridgeConfig.save_config()
                        self._set_end_headers(bytes(webform_linkbutton() + '<br> Your credentials are succesfully change. Please logout then login again', "utf8"))
                    else:
                        self._set_headers()
                        self._set_end_headers(bytes(webform_linkbutton(), "utf8"))
                    pass
                else:
                    self._set_AUTHHEAD()
                    self._set_end_headers(bytes(self.headers['Authorization'], "utf8"))
                    self._set_end_headers(bytes('not authenticated', "utf8"))
                    pass
            else:
                self._set_headers()
                get_parameters = parse_qs(urlparse(self.path).query)
                if "ip" in get_parameters:
                    response = json.loads(sendRequest("http://" + get_parameters["ip"][0] + "/api/", "POST", "{\"devicetype\":\"Hue Emulator\"}"))
                    if "success" in response[0]:
                        hue_lights = json.loads(sendRequest("http://" + get_parameters["ip"][0] + "/api/" + response[0]["success"]["username"] + "/lights", "GET", "{}"))
                        logging.debug('Got response from hue bridge: %s', hue_lights)

                        # Look through all lights in the response, and check if we've seen them before
                        lights_found = 0
                        for light_nr, data in hue_lights.items():
                            light_id = find_light_in_config_from_uid(bridge_config, data['uniqueid'])
                            if light_id is None:
                                light_id = nextFreeId(bridge_config, "lights")
                                logging.info('Found new light: %s %s', light_id, data)
                                lights_found += 1
                                bridge_config["lights_address"][light_id] = {
                                    "username": response[0]["success"]["username"],
                                    "light_id": light_nr,
                                    "ip": get_parameters["ip"][0],
                                    "protocol": "hue"
                                }
                            else:
                                logging.info('Found duplicate light: %s %s', light_id, data)
                            bridge_config["lights"][light_id] = data

                        if lights_found == 0:
                            self._set_end_headers(bytes(webform_hue() + "<br> No lights where found", "utf8"))
                        else:
                            configManager.bridgeConfig.save_config()
                            self._set_end_headers(bytes(webform_hue() + "<br> " + str(lights_found) + " lights were found", "utf8"))
                    else:
                        self._set_end_headers(bytes(webform_hue() + "<br> unable to connect to hue bridge", "utf8"))
                else:
                    self._set_end_headers(bytes(webform_hue(), "utf8"))
        elif self.path.startswith("/deconz"): #setup imported deconz sensors
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            #clean all rules related to deconz Switches
            if get_parameters:
                emulator_resourcelinkes = []
                for resourcelink in bridge_config["resourcelinks"].keys(): # delete all previews rules of IKEA remotes
                    if bridge_config["resourcelinks"][resourcelink]["classid"] == 15555:
                        emulator_resourcelinkes.append(resourcelink)
                        for link in bridge_config["resourcelinks"][resourcelink]["links"]:
                            pices = link.split('/')
                            if pices[1] == "rules":
                                try:
                                    del bridge_config["rules"][pices[2]]
                                except:
                                    logging.info("unable to delete the rule " + pices[2])
                for resourcelink in emulator_resourcelinkes:
                    del bridge_config["resourcelinks"][resourcelink]
                for key in get_parameters.keys():
                    if get_parameters[key][0] in ["ZLLSwitch", "ZGPSwitch"]:
                        try:
                            del bridge_config["sensors"][key]
                        except:
                            pass
                        hueSwitchId = addHueSwitch("", get_parameters[key][0])
                        for sensor in bridge_config["deconz"]["sensors"].keys():
                            if bridge_config["deconz"]["sensors"][sensor]["bridgeid"] == key:
                                bridge_config["deconz"]["sensors"][sensor] = {"hueType": get_parameters[key][0], "bridgeid": hueSwitchId}
                    else:
                        if not key.startswith("mode_"):
                            if bridge_config["sensors"][key]["modelid"] == "TRADFRI remote control":
                                if get_parameters["mode_" + key][0]  == "CT":
                                    tradfri.sensors.addTradfriCtRemote(key, get_parameters[key][0])
                                elif get_parameters["mode_" + key][0]  == "SCENE":
                                    tradfri.sensors.addTradfriSceneRemote(key, get_parameters[key][0])
                            elif bridge_config["sensors"][key]["modelid"] == "TRADFRI wireless dimmer":
                                tradfri.sensors.addTradfriDimmer(key, get_parameters[key][0])
                            elif bridge_config["sensors"][key]["modelid"] == "TRADFRI on/off switch":
                                tradfri.sensors.addTradfriOnOffSwitch(key, get_parameters[key][0])
                            elif bridge_config["deconz"]["sensors"][key]["modelid"] == "TRADFRI motion sensor":
                                bridge_config["deconz"]["sensors"][key]["lightsensor"] = get_parameters[key][0]
                            #store room id in deconz sensors
                            for sensor in bridge_config["deconz"]["sensors"].keys():
                                if bridge_config["deconz"]["sensors"][sensor]["bridgeid"] == key:
                                    bridge_config["deconz"]["sensors"][sensor]["room"] = get_parameters[key][0]
                                    if bridge_config["sensors"][key]["modelid"] == "TRADFRI remote control":
                                        bridge_config["deconz"]["sensors"][sensor]["opmode"] = get_parameters["mode_" + key][0]

            else:
                Thread(target=deconz.scanDeconz).start()
            self._set_end_headers(bytes(webformDeconz({"deconz": bridge_config["deconz"], "sensors": bridge_config["sensors"], "groups": bridge_config["groups"]}), "utf8"))
        elif self.path.startswith("/switch"): #request from an ESP8266 switch or sensor
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            logging.info(pretty_json(get_parameters))
            if "devicetype" in get_parameters and get_parameters["mac"][0] not in bridge_config["emulator"]["sensors"]: #register device request
                logging.info("registering new sensor " + get_parameters["devicetype"][0])
                if get_parameters["devicetype"][0] in ["ZLLSwitch","ZGPSwitch"]:
                    logging.info(get_parameters["devicetype"][0])
                    bridge_config["emulator"]["sensors"][get_parameters["mac"][0]] = {"bridgeId": addHueSwitch("", get_parameters["devicetype"][0])}
                elif get_parameters["devicetype"][0] == "ZLLPresence":
                    logging.info("ZLLPresence")
                    bridge_config["emulator"]["sensors"][get_parameters["mac"][0]] = {"bridgeId": addHueMotionSensor(""), "lightSensorId": "0"}
                    ### detect light sensor id and save it to update directly the lightdata
                    for sensor in bridge_config["sensors"].keys():
                        if bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel" and bridge_config["sensors"][sensor]["uniqueid"] == bridge_config["sensors"][bridge_config["emulator"]["sensors"][get_parameters["mac"][0]]["bridgeId"]]["uniqueid"][:-1] + "0":
                            bridge_config["emulator"]["sensors"][get_parameters["mac"][0]]["lightSensorId"] = sensor
                            break
                    generateDxState()
            else: #switch action request
                if get_parameters["mac"][0] in bridge_config["emulator"]["sensors"]:
                    sensorId = bridge_config["emulator"]["sensors"][get_parameters["mac"][0]]["bridgeId"]
                    logging.info("match sensor " + sensorId)
                    if bridge_config["sensors"][sensorId]["config"]["on"]: #match senser id based on mac address
                        current_time = datetime.now()
                        if bridge_config["sensors"][sensorId]["type"] in ["ZLLSwitch","ZGPSwitch"]:
                            bridge_config["sensors"][sensorId]["state"].update({"buttonevent": int(get_parameters["button"][0]), "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                            if "battery" in get_parameters:
                                bridge_config["sensors"][sensorId]["config"]["battery"] = int(get_parameters["battery"][0])
                            dxState["sensors"][sensorId]["state"]["lastupdated"] = current_time
                        elif bridge_config["sensors"][sensorId]["type"] == "ZLLPresence":
                            lightSensorId = bridge_config["emulator"]["sensors"][get_parameters["mac"][0]]["lightSensorId"]
                            if bridge_config["sensors"][sensorId]["state"]["presence"] != True:
                                bridge_config["sensors"][sensorId]["state"]["presence"] = True
                                dxState["sensors"][sensorId]["state"]["presence"] = current_time
                            bridge_config["sensors"][sensorId]["state"]["lastupdated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                            Thread(target=motionDetected, args=[sensorId]).start()

                            if "lightlevel" in get_parameters:
                                bridge_config["sensors"][lightSensorId]["state"].update({"lightlevel": int(get_parameters["lightlevel"][0]), "dark": bool(get_parameters["dark"][0]), "daylight": bool(get_parameters["daylight"][0]), "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                            else:
                                if bridge_config["sensors"]["1"]["modelid"] == "PHDL00" and bridge_config["sensors"]["1"]["state"]["daylight"]:
                                    bridge_config["sensors"][lightSensorId]["state"].update({"lightlevel": 25000, "dark": False, "daylight": True, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") })
                                else:
                                    bridge_config["sensors"][lightSensorId]["state"].update({"lightlevel": 6000, "dark": True, "daylight": False, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") })

                            #trigger the alarm if active
                            if bridge_config["emulator"]["alarm"]["on"] and bridge_config["emulator"]["alarm"]["lasttriggered"] + 300 < datetime.now().timestamp():
                                logging.info("Alarm triggered, sending email...")
                                requests.post("https://diyhue.org/cdn/mailNotify.php", json={"to": bridge_config["emulator"]["alarm"]["email"], "sensor": bridge_config["sensors"][sensorId]["name"]})
                                bridge_config["emulator"]["alarm"]["lasttriggered"] = int(datetime.now().timestamp())
                                #triger_horn() need development
                        rulesProcessor(["sensors", sensorId], current_time) #process the rules to perform the action configured by application
            self._set_end_headers(bytes("done", "utf8"))
        elif self.path.startswith("/scan"): # rescan
            self._set_headers()
            scan_for_lights()
            self._set_end_headers(bytes("done", "utf8"))
        else:
            url_pices = self.path.rstrip('/').split('/')
            if len(url_pices) < 3:
                #self._set_headers_error()
                self.send_error(404, 'not found')
                return
            else:
                self._set_headers()
            if url_pices[2] in bridge_config["config"]["whitelist"]: #if username is in whitelist
                bridge_config["config"]["UTC"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                bridge_config["config"]["localtime"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                bridge_config["config"]["whitelist"][url_pices[2]]["last use date"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                bridge_config["config"]["linkbutton"] = int(bridge_config["linkbutton"]["lastlinkbuttonpushed"]) + 30 >= int(datetime.now().timestamp())
                if len(url_pices) == 3: #print entire config
                    #trim off lightstates as per hue api
                    scenelist = {}
                    scenelist["scenes"] = copy.deepcopy(bridge_config["scenes"])
                    for scene in list(scenelist["scenes"]):
                        if "lightstates" in list(scenelist["scenes"][scene]):
                            del scenelist["scenes"][scene]["lightstates"]
                        if ("type" in scenelist["scenes"][scene]) and ("GroupScene" == scenelist["scenes"][scene]["type"]):
                            scenelist["scenes"][scene]["lights"] = {}
                            scenelist["scenes"][scene]["lights"] = bridge_config["groups"][bridge_config["scenes"][scene]["group"]]["lights"]
                    configManager.bridgeConfig.sanitizeBridgeScenes()
                    self._set_end_headers(bytes(json.dumps({"lights": bridge_config["lights"], "groups": bridge_config["groups"], "config": bridge_config["config"], "scenes": scenelist["scenes"], "schedules": bridge_config["schedules"], "rules": bridge_config["rules"], "sensors": bridge_config["sensors"], "resourcelinks": bridge_config["resourcelinks"]},separators=(',', ':'),ensure_ascii=False), "utf8"))
                elif len(url_pices) == 4: #print specified object config
                    if "scenes" == url_pices[3]: #trim lightstates for scenes
                        scenelist = {}
                        scenelist["scenes"] = copy.deepcopy(bridge_config["scenes"])
                        for scene in list(scenelist["scenes"]):
                            if "lightstates" in list(scenelist["scenes"][scene]):
                                del scenelist["scenes"][scene]["lightstates"]
                            if ("type" in scenelist["scenes"][scene]) and ("GroupScene" == scenelist["scenes"][scene]["type"]):
                                scenelist["scenes"][scene]["lights"] = {}
                                scenelist["scenes"][scene]["lights"] = bridge_config["groups"][bridge_config["scenes"][scene]["group"]]["lights"]
                        self._set_end_headers(bytes(json.dumps(scenelist["scenes"],separators=(',', ':'),ensure_ascii=False), "utf8"))
                    else:
                        self._set_end_headers(bytes(json.dumps(bridge_config[url_pices[3]],separators=(',', ':'),ensure_ascii=False), "utf8"))
                elif (len(url_pices) == 5 or (len(url_pices) == 6 and url_pices[5] == 'state')):
                    if url_pices[4] == "new": #return new lights and sensors only
                        new_lights.update({"lastscan": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")})
                        self._set_end_headers(bytes(json.dumps(new_lights ,separators=(',', ':'),ensure_ascii=False), "utf8"))
                    elif url_pices[3] == "groups" and url_pices[4] == "0":
                        any_on = False
                        all_on = True
                        for group_state in bridge_config["groups"].keys():
                            if bridge_config["groups"][group_state]["state"]["any_on"] == True:
                                any_on = True
                            else:
                                all_on = False
                        self._set_end_headers(bytes(json.dumps({"name":"Group 0","lights": [l for l in bridge_config["lights"]],"sensors": [s for s in bridge_config["sensors"]],"type":"LightGroup","state":{"all_on":all_on,"any_on":any_on},"recycle":False,"action":{"on":False,"alert":"none"}},separators=(',', ':'),ensure_ascii=False), "utf8"))
                    elif url_pices[3] == "info" and url_pices[4] == "timezones":
                        self._set_end_headers(bytes(json.dumps(bridge_config["capabilities"][url_pices[4]]["values"],separators=(',', ':'),ensure_ascii=False), "utf8"))
                    elif "scenes" == url_pices[3]: #trim lightstates for scenes
                        scenelist = {}
                        scenelist["scenes"] = copy.deepcopy(bridge_config["scenes"])
                        for scene in list(scenelist["scenes"]):
                            if ("type" in scenelist["scenes"][scene]) and ("GroupScene" == scenelist["scenes"][scene]["type"]):
                                scenelist["scenes"][scene]["lights"] = {}
                                scenelist["scenes"][scene]["lights"] = bridge_config["groups"][bridge_config["scenes"][scene]["group"]]["lights"]
                        self._set_end_headers(bytes(json.dumps(scenelist["scenes"][url_pices[4]],separators=(',', ':'),ensure_ascii=False), "utf8"))
                    else:
                        self._set_end_headers(bytes(json.dumps(bridge_config[url_pices[3]][url_pices[4]],separators=(',', ':'),ensure_ascii=False), "utf8"))
            elif (len(url_pices) == 4 and url_pices[3] == "config") or (len(url_pices) == 3 and url_pices[2] == "config"): #used by applications to discover the bridge
                self._set_end_headers(bytes(json.dumps({"name": bridge_config["config"]["name"],"datastoreversion": 70, "swversion": bridge_config["config"]["swversion"], "apiversion": bridge_config["config"]["apiversion"], "mac": bridge_config["config"]["mac"], "bridgeid": bridge_config["config"]["bridgeid"], "factorynew": False, "replacesbridgeid": None, "modelid": bridge_config["config"]["modelid"],"starterkitid":""},separators=(',', ':'),ensure_ascii=False), "utf8"))
            else: #user is not in whitelist
                self._set_end_headers(bytes(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],separators=(',', ':'),ensure_ascii=False), "utf8"))

    def read_http_request_body(self):
        return b"{}" if self.headers['Content-Length'] is None or self.headers[
            'Content-Length'] == '0' else self.rfile.read(int(self.headers['Content-Length']))

    def do_POST(self):
        self._set_headers()
        logging.info("in post method")
        logging.info(self.path)
        self.data_string = self.read_http_request_body()
        if self.path == "/updater":
            logging.info("check for updates")
            update_data = json.loads(sendRequest("https://raw.githubusercontent.com/diyhue/diyHue/master/BridgeEmulator/updater", "GET", "{}"))
            for category in update_data.keys():
                for key in update_data[category].keys():
                    logging.info("patch " + category + " -> " + key )
                    bridge_config[category][key] = update_data[category][key]
            self._set_end_headers(bytes(json.dumps([{"success": {"/config/swupdate/checkforupdate": True}}],separators=(',', ':'),ensure_ascii=False), "utf8"))
        else:
            raw_json = self.data_string.decode('utf8')
            raw_json = raw_json.replace("\t","")
            raw_json = raw_json.replace("\n","")
            post_dictionary = json.loads(raw_json)
            logging.info(self.data_string)
        url_pices = self.path.rstrip('/').split('/')
        if len(url_pices) == 4: #data was posted to a location
            if url_pices[2] in bridge_config["config"]["whitelist"]: #check to make sure request is authorized
                if ((url_pices[3] == "lights" or url_pices[3] == "sensors") and not bool(post_dictionary)):
                    #if was a request to scan for lights of sensors
                    new_lights.clear()
                    Thread(target=scan_for_lights).start()
                    sleep(7) #give no more than 5 seconds for light scanning (otherwise will face app disconnection timeout)
                    self._set_end_headers(bytes(json.dumps([{"success": {"/" + url_pices[3]: "Searching for new devices"}}],separators=(',', ':'),ensure_ascii=False), "utf8"))
                elif url_pices[3] == "":
                    self._set_end_headers(bytes(json.dumps([{"success": {"clientkey": "321c0c2ebfa7361e55491095b2f5f9db"}}],separators=(',', ':'),ensure_ascii=False), "utf8"))
                else: #create object
                    # find the first unused id for new object
                    new_object_id = nextFreeId(bridge_config, url_pices[3])
                    if url_pices[3] == "scenes": # store scene
                        post_dictionary.update({"version": 2, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "owner" :url_pices[2]})
                        if "locked" not in post_dictionary:
                            post_dictionary["locked"] = False
                        if "picture" not in post_dictionary:
                            post_dictionary["picture"] = ""
                        if "type" not in post_dictionary:
                            post_dictionary["type"] = "LightScene"
                        if "lightstates" not in post_dictionary or len(post_dictionary["lightstates"]) == 0:
                            post_dictionary["lightstates"] = {}
                            if "lights" in post_dictionary:
                                lights = post_dictionary["lights"]
                            elif "group" in post_dictionary:
                                lights = bridge_config["groups"][post_dictionary["group"]]["lights"]
                            for light in lights:
                                post_dictionary["lightstates"][light] = {"on": bridge_config["lights"][light]["state"]["on"]}
                                if "bri" in bridge_config["lights"][light]["state"]:
                                    post_dictionary["lightstates"][light]["bri"] = bridge_config["lights"][light]["state"]["bri"]
                                if "colormode" in bridge_config["lights"][light]["state"]:
                                    if bridge_config["lights"][light]["state"]["colormode"] in ["ct", "xy"] and bridge_config["lights"][light]["state"]["colormode"] in bridge_config["lights"][light]["state"]:
                                        post_dictionary["lightstates"][light][bridge_config["lights"][light]["state"]["colormode"]] = bridge_config["lights"][light]["state"][bridge_config["lights"][light]["state"]["colormode"]]
                                    elif bridge_config["lights"][light]["state"]["colormode"] == "hs":
                                        post_dictionary["lightstates"][light]["hue"] = bridge_config["lights"][light]["state"]["hue"]
                                        post_dictionary["lightstates"][light]["sat"] = bridge_config["lights"][light]["state"]["sat"]

                    elif url_pices[3] == "groups":
                        if "type" not in post_dictionary:
                            post_dictionary["type"] = "LightGroup"
                        if post_dictionary["type"] in ["Room", "Zone"] and "class" not in post_dictionary:
                            post_dictionary["class"] = "Other"
                        elif post_dictionary["type"] == "Entertainment" and "stream" not in post_dictionary:
                            post_dictionary["stream"] = {"active": False, "owner": url_pices[2], "proxymode": "auto", "proxynode": "/bridge"}
                        post_dictionary.update({"action": {"on": False}, "state": {"any_on": False, "all_on": False}})
                    elif url_pices[3] == "schedules":
                        try:
                            post_dictionary.update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "time": post_dictionary["localtime"]})
                        except KeyError:
                            post_dictionary.update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "localtime": post_dictionary["time"]})
                        if post_dictionary["localtime"].startswith("PT") or post_dictionary["localtime"].startswith("R/PT"):
                            post_dictionary.update({"starttime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                        if not "status" in post_dictionary:
                            post_dictionary.update({"status": "enabled"})
                    elif url_pices[3] == "rules":
                        post_dictionary.update({"owner": url_pices[2], "lasttriggered" : "none", "created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "timestriggered": 0})
                        if not "status" in post_dictionary:
                            post_dictionary.update({"status": "enabled"})
                    elif url_pices[3] == "sensors":
                        if "state" not in post_dictionary:
                            post_dictionary["state"] = {}
                        if "lastupdated" not in post_dictionary["state"]:
                            post_dictionary["state"]["lastupdated"] = "none"
                        if post_dictionary["modelid"] == "PHWA01":
                            post_dictionary["state"]["status"] = 0
                        elif post_dictionary["modelid"] == "PHA_CTRL_START":
                            post_dictionary.update({"state": {"flag": False, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}, "config": {"on": True,"reachable": True}})
                    elif url_pices[3] == "resourcelinks":
                        post_dictionary.update({"owner" :url_pices[2]})
                    generateDxState()
                    bridge_config[url_pices[3]][new_object_id] = post_dictionary
                    logging.info(json.dumps([{"success": {"id": new_object_id}}], sort_keys=True, indent=4, separators=(',', ': ')))
                    self._set_end_headers(bytes(json.dumps([{"success": {"id": new_object_id}}], separators=(',', ':'),ensure_ascii=False), "utf8"))
            else:
                self._set_end_headers(bytes(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}], separators=(',', ':'),ensure_ascii=False), "utf8"))
                logging.info(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],sort_keys=True, indent=4, separators=(',', ': ')))
        elif self.path.startswith("/api") and "devicetype" in post_dictionary: #new registration by linkbutton
            last_button_press = int(bridge_config["linkbutton"]["lastlinkbuttonpushed"])
            if (configManager.runtimeConfig.arg["noLinkButton"] or last_button_press+30 >= int(datetime.now().timestamp()) or
                    bridge_config["config"]["linkbutton"]):
                username = str(uuid.uuid1()).replace('-', '')
                if post_dictionary["devicetype"].startswith("Hue Essentials"):
                    username = "hueess" + username[-26:]
                bridge_config["config"]["whitelist"][username] = {"last use date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"create date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"name": post_dictionary["devicetype"]}
                response = [{"success": {"username": username}}]
                if "generateclientkey" in post_dictionary and post_dictionary["generateclientkey"]:
                    response[0]["success"]["clientkey"] = "321c0c2ebfa7361e55491095b2f5f9db"
                self._set_end_headers(bytes(json.dumps(response,separators=(',', ':'),ensure_ascii=False), "utf8"))
                logging.info(json.dumps(response, sort_keys=True, indent=4, separators=(',', ': ')))
            else:
                self._set_end_headers(bytes(json.dumps([{"error": {"type": 101, "address": self.path, "description": "link button not pressed" }}], separators=(',', ':'),ensure_ascii=False), "utf8"))
        configManager.bridgeConfig.save_config()

    def do_PUT(self):
        self._set_headers()
        logging.info("in PUT method")
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        put_dictionary = json.loads(self.data_string.decode('utf8'))
        url_pices = self.path.rstrip('/').split('/')
        logging.info(self.path)
        logging.info(self.data_string)
        if url_pices[2] in bridge_config["config"]["whitelist"] or (url_pices[2] == "0" and self.client_address[0] == "127.0.0.1"):
            current_time = datetime.now()
            if len(url_pices) == 4:
                bridge_config[url_pices[3]].update(put_dictionary)
                response_location = "/" + url_pices[3] + "/"
            if len(url_pices) == 5:
                if url_pices[3] == "schedules":
                    if "status" in put_dictionary and put_dictionary["status"] == "enabled" and (bridge_config["schedules"][url_pices[4]]["localtime"].startswith("PT") or bridge_config["schedules"][url_pices[4]]["localtime"].startswith("R/PT")):
                        bridge_config["schedules"][url_pices[4]]["starttime"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                    bridge_config[url_pices[3]][url_pices[4]].update(put_dictionary)
                elif url_pices[3] == "scenes":
                    if "storelightstate" in put_dictionary:
                        if "lights" in bridge_config["scenes"][url_pices[4]]:
                            lights = bridge_config["scenes"][url_pices[4]]["lights"]
                        elif "group" in bridge_config["scenes"][url_pices[4]]:
                            lights = bridge_config["groups"][bridge_config["scenes"][url_pices[4]]["group"]]["lights"]
                        for light in lights:
                            bridge_config["scenes"][url_pices[4]]["lightstates"][light] = {}
                            bridge_config["scenes"][url_pices[4]]["lightstates"][light]["on"] = bridge_config["lights"][light]["state"]["on"]
                            if "bri" in bridge_config["lights"][light]["state"]:
                                bridge_config["scenes"][url_pices[4]]["lightstates"][light]["bri"] = bridge_config["lights"][light]["state"]["bri"]
                            if "colormode" in bridge_config["lights"][light]["state"]:
                                if bridge_config["lights"][light]["state"]["colormode"] in ["ct", "xy"]:
                                    bridge_config["scenes"][url_pices[4]]["lightstates"][light][bridge_config["lights"][light]["state"]["colormode"]] = bridge_config["lights"][light]["state"][bridge_config["lights"][light]["state"]["colormode"]]
                                elif bridge_config["lights"][light]["state"]["colormode"] == "hs" and "hue" in bridge_config["scenes"][url_pices[4]]["lightstates"][light]:
                                    bridge_config["scenes"][url_pices[4]]["lightstates"][light]["hue"] = bridge_config["lights"][light]["state"]["hue"]
                                    bridge_config["scenes"][url_pices[4]]["lightstates"][light]["sat"] = bridge_config["lights"][light]["state"]["sat"]
                elif url_pices[3] == "sensors":
                    current_time = datetime.now()
                    for key, value in put_dictionary.items():
                        if key not in dxState["sensors"][url_pices[4]]:
                            dxState["sensors"][url_pices[4]][key] = {}
                        if type(value) is dict:
                            bridge_config["sensors"][url_pices[4]][key].update(value)
                            for element in value.keys():
                                dxState["sensors"][url_pices[4]][key][element] = current_time
                        else:
                            bridge_config["sensors"][url_pices[4]][key] = value
                            dxState["sensors"][url_pices[4]][key] = current_time
                    dxState["sensors"][url_pices[4]]["state"]["lastupdated"] = current_time
                    bridge_config["sensors"][url_pices[4]]["state"]["lastupdated"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
                    if url_pices[4] == "1" and bridge_config[url_pices[3]][url_pices[4]]["modelid"] == "PHDL00":
                        bridge_config["sensors"]["1"]["config"]["configured"] = True ##mark daylight sensor as configured
                elif url_pices[3] == "groups" and "stream" in put_dictionary:
                    if "active" in put_dictionary["stream"]:
                        if put_dictionary["stream"]["active"]:
                            for light in bridge_config["groups"][url_pices[4]]["lights"]:
                                bridge_config["lights"][light]["state"]["mode"] = "streaming"
                            logging.info("start hue entertainment")
                            Popen(["/opt/hue-emulator/entertain-srv", "server_port=2100", "dtls=1", "psk_list=" + url_pices[2] + ",321c0c2ebfa7361e55491095b2f5f9db"])
                            sleep(0.2)
                            bridge_config["groups"][url_pices[4]]["stream"].update({"active": True, "owner": url_pices[2], "proxymode": "auto", "proxynode": "/bridge"})
                        else:
                            for light in bridge_config["groups"][url_pices[4]]["lights"]:
                                bridge_config["lights"][light]["state"]["mode"] = "homeautomation"
                            logging.info("stop hue entertainent")
                            Popen(["killall", "entertain-srv"])
                            bridge_config["groups"][url_pices[4]]["stream"].update({"active": False, "owner": None})
                    else:
                        bridge_config[url_pices[3]][url_pices[4]].update(put_dictionary)
                elif url_pices[3] == "lights" and "config" in put_dictionary:
                    bridge_config["lights"][url_pices[4]]["config"].update(put_dictionary["config"])
                    if "startup" in put_dictionary["config"] and bridge_config["lights_address"][url_pices[4]]["protocol"] == "native":
                        if put_dictionary["config"]["startup"]["mode"] == "safety":
                            sendRequest("http://" + bridge_config["lights_address"][url_pices[4]]["ip"] + "/", "POST", {"startup": 1})
                        elif put_dictionary["config"]["startup"]["mode"] == "powerfail":
                            sendRequest("http://" + bridge_config["lights_address"][url_pices[4]]["ip"] + "/", "POST", {"startup": 0})

                        #add exception on json output as this dictionary has tree levels
                        response_dictionary = {"success":{"/lights/" + url_pices[4] + "/config/startup": {"mode": put_dictionary["config"]["startup"]["mode"]}}}
                        self._set_end_headers(bytes(json.dumps(response_dictionary,separators=(',', ':'),ensure_ascii=False), "utf8"))
                        logging.info(json.dumps(response_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))
                        return
                else:
                    bridge_config[url_pices[3]][url_pices[4]].update(put_dictionary)
                    if url_pices[3] == "groups" and "lights" in put_dictionary: #need to update scene lightstates
                        for scene in bridge_config["scenes"]: # iterate over scenes
                            for light in put_dictionary["lights"]: # check each scene to make sure it has a lightstate for each new light
                                if "lightstates" in bridge_config["scenes"][scene] and light not in bridge_config["scenes"][scene]["lightstates"]: # copy first light state to new light
                                    if ("lights" in bridge_config["scenes"][scene] and light in bridge_config["scenes"][scene]["lights"]) or \
                                    (bridge_config["scenes"][scene]["type"] == "GroupScene" and light in bridge_config["groups"][bridge_config["scenes"][scene]["group"]]["lights"]):
                                        # Either light is in the scene or part of the group now, add lightscene based on previous scenes
                                        new_state = next(iter(bridge_config["scenes"][scene]["lightstates"]))
                                        new_state = bridge_config["scenes"][scene]["lightstates"][new_state]
                                        bridge_config["scenes"][scene]["lightstates"][light] = new_state

                response_location = "/" + url_pices[3] + "/" + url_pices[4] + "/"
            if len(url_pices) == 6:
                if url_pices[3] == "groups": #state is applied to a group
                    if url_pices[5] == "stream":
                        if "active" in put_dictionary:
                            if put_dictionary["active"]:
                                logging.info("start hue entertainment")
                                Popen(["/opt/hue-emulator/entertain-srv", "server_port=2100", "dtls=1", "psk_list=" + url_pices[2] + ",321c0c2ebfa7361e55491095b2f5f9db"])
                                sleep(0.2)
                                bridge_config["groups"][url_pices[4]]["stream"].update({"active": True, "owner": url_pices[2], "proxymode": "auto", "proxynode": "/bridge"})
                            else:
                                Popen(["killall", "entertain-srv"])
                                bridge_config["groups"][url_pices[4]]["stream"].update({"active": False, "owner": None})
                    elif "scene" in put_dictionary: #scene applied to group
                        if bridge_config["scenes"][put_dictionary["scene"]]["type"] == "GroupScene":
                            splitLightsToDevices(bridge_config["scenes"][put_dictionary["scene"]]["group"], {}, bridge_config["scenes"][put_dictionary["scene"]]["lightstates"])
                        else:
                            splitLightsToDevices(url_pices[4], {}, bridge_config["scenes"][put_dictionary["scene"]]["lightstates"])
                    elif "bri_inc" in put_dictionary or "ct_inc" in put_dictionary or "hue_inc" in put_dictionary:
                        splitLightsToDevices(url_pices[4], put_dictionary)
                    elif "scene_inc" in put_dictionary:
                        switchScene(url_pices[4], put_dictionary["scene_inc"])
                    elif url_pices[4] == "0": #if group is 0 the scene applied to all lights
                        groupZero(put_dictionary)
                    else: # the state is applied to particular group (url_pices[4])
                        if "on" in put_dictionary:
                            bridge_config["groups"][url_pices[4]]["state"]["any_on"] = put_dictionary["on"]
                            bridge_config["groups"][url_pices[4]]["state"]["all_on"] = put_dictionary["on"]
                            dxState["groups"][url_pices[4]]["state"]["any_on"] = current_time
                            dxState["groups"][url_pices[4]]["state"]["all_on"] = current_time
                        bridge_config["groups"][url_pices[4]][url_pices[5]].update(put_dictionary)
                        splitLightsToDevices(url_pices[4], put_dictionary)
                elif url_pices[3] == "lights": #state is applied to a light
                    for key in put_dictionary.keys():
                        if key in ["ct", "xy"]: #colormode must be set by bridge
                            bridge_config["lights"][url_pices[4]]["state"]["colormode"] = key
                        elif key in ["hue", "sat"]:
                            bridge_config["lights"][url_pices[4]]["state"]["colormode"] = "hs"

                    updateGroupStats(url_pices[4], bridge_config["lights"], bridge_config["groups"])
                    sendLightRequest(url_pices[4], put_dictionary, bridge_config["lights"], bridge_config["lights_address"])
                elif url_pices[3] == "sensors":
                    if url_pices[5] == "state":
                        for key in put_dictionary.keys():
                            # track time of state changes in dxState
                            if not key in bridge_config["sensors"][url_pices[4]]["state"] or bridge_config["sensors"][url_pices[4]]["state"][key] != put_dictionary[key]:
                                dxState["sensors"][url_pices[4]]["state"][key] = current_time
                    elif url_pices[4] == "1":
                        bridge_config["sensors"]["1"]["config"]["configured"] = True ##mark daylight sensor as configured
                    dxState["sensors"][url_pices[4]]["state"]["lastupdated"] = current_time
                    bridge_config["sensors"][url_pices[4]]["state"]["lastupdated"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
                if  url_pices[4] != "0" and "scene" not in put_dictionary: #group 0 is virtual, must not be saved in bridge configuration, also the recall scene
                    try:
                        bridge_config[url_pices[3]][url_pices[4]][url_pices[5]].update(put_dictionary)
                    except KeyError:
                        bridge_config[url_pices[3]][url_pices[4]][url_pices[5]] = put_dictionary
                response_location = "/" + url_pices[3] + "/" + url_pices[4] + "/" + url_pices[5] + "/"
            if len(url_pices) == 7:
                try:
                    bridge_config[url_pices[3]][url_pices[4]][url_pices[5]][url_pices[6]].update(put_dictionary)
                except KeyError:
                    bridge_config[url_pices[3]][url_pices[4]][url_pices[5]][url_pices[6]] = put_dictionary
                bridge_config[url_pices[3]][url_pices[4]][url_pices[5]][url_pices[6]] = put_dictionary
                response_location = "/" + url_pices[3] + "/" + url_pices[4] + "/" + url_pices[5] + "/" + url_pices[6] + "/"
            response_dictionary = []
            for key, value in put_dictionary.items():
                response_dictionary.append({"success":{response_location + key: value}})
            sleep(0.3)
            self._set_end_headers(bytes(json.dumps(response_dictionary,separators=(',', ':'),ensure_ascii=False), "utf8"))
            logging.info(json.dumps(response_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))
            if len(url_pices) > 4:
                rulesProcessor([url_pices[3], url_pices[4]], current_time)
            configManager.bridgeConfig.sanitizeBridgeScenes() # in case some lights where removed from group it will need to remove them also from group scenes.
        else:
            self._set_end_headers(bytes(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],separators=(',', ':'),ensure_ascii=False), "utf8"))

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self._set_end_headers(bytes(json.dumps([{"status": "success"}]), "utf8"))


    def do_DELETE(self):
        self._set_headers()
        url_pices = self.path.rstrip('/').split('/')
        if url_pices[2] in bridge_config["config"]["whitelist"]:
            if len(url_pices) == 6:
                del bridge_config[url_pices[3]][url_pices[4]][url_pices[5]]
            else:
                if url_pices[3] == "resourcelinks":
                    configManager.bridgeConfig.resourceRecycle()
                elif url_pices[3] == "sensors":
                    ## delete also related sensors
                    for sensor in list(bridge_config["sensors"]):
                        if sensor != url_pices[4] and "uniqueid" in bridge_config["sensors"][sensor] and bridge_config["sensors"][sensor]["uniqueid"].startswith(bridge_config["sensors"][url_pices[4]]["uniqueid"][:26]):
                            del bridge_config["sensors"][sensor]
                            logging.info('Delete related sensor ' + sensor)
                try:
                    del bridge_config[url_pices[3]][url_pices[4]]
                except:
                    logging.info(str([url_pices[3]]) + ": " + str(url_pices[4]) + " does not exist")
            if url_pices[3] == "lights":
                del_light = url_pices[4]

                # Delete the light address
                del bridge_config["lights_address"][del_light]

                # Remove this light from every group
                for group_id, group in bridge_config["groups"].items():
                    if "lights" in group and del_light in group["lights"]:
                        group["lights"].remove(del_light)

                # Delete the light from the deCONZ config
                for light in list(bridge_config["deconz"]["lights"]):
                    if bridge_config["deconz"]["lights"][light]["bridgeid"] == del_light:
                        del bridge_config["deconz"]["lights"][light]

                # Delete the light from any scenes
                for scene in list(bridge_config["scenes"]):
                    if del_light in bridge_config["scenes"][scene]["lightstates"]:
                        del bridge_config["scenes"][scene]["lightstates"][del_light]
                        if "lights" in bridge_config["scenes"][scene] and del_light in bridge_config["scenes"][scene]["lights"]:
                            bridge_config["scenes"][scene]["lights"].remove(del_light)
                        if ("lights" in bridge_config["scenes"][scene] and len(bridge_config["scenes"][scene]["lights"]) == 0) or len(bridge_config["scenes"][scene]["lightstates"]) == 0:
                            del bridge_config["scenes"][scene]
            elif url_pices[3] == "sensors":
                for sensor in list(bridge_config["deconz"]["sensors"]):
                    if bridge_config["deconz"]["sensors"][sensor]["bridgeid"] == url_pices[4]:
                        del bridge_config["deconz"]["sensors"][sensor]
                for sensor in list(bridge_config["emulator"]["sensors"]):
                    if bridge_config["emulator"]["sensors"][sensor]["bridgeId"] == url_pices[4]:
                        del bridge_config["emulator"]["sensors"][sensor]
            elif url_pices[3] == "groups":
                configManager.bridgeConfig.sanitizeBridgeScenes()
            logging.info(json.dumps([{"success": "/" + url_pices[3] + "/" + url_pices[4] + " deleted."}],separators=(',', ':'),ensure_ascii=False))
            self._set_end_headers(bytes(json.dumps([{"success": "/" + url_pices[3] + "/" + url_pices[4] + " deleted."}],separators=(',', ':'),ensure_ascii=False), "utf8"))



def run(https, server_class=ThreadingSimpleServer, handler_class=S):
    BIND_IP = configManager.runtimeConfig.arg["BIND_IP"]
    HOST_HTTPS_PORT = configManager.runtimeConfig.arg["HTTPS_PORT"]
    if https:
        server_address = (BIND_IP, HOST_HTTPS_PORT)
        httpd = server_class(server_address, handler_class)
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(certfile="/opt/hue-emulator/config/cert.pem") # change to new cert location
        ctx.options |= ssl.OP_NO_TLSv1
        ctx.options |= ssl.OP_NO_TLSv1_1
        ctx.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
        ctx.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256')
        ctx.set_ecdh_curve('prime256v1')
        #ctx.set_alpn_protocols(['h2', 'http/1.1'])
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        logging.info('Starting ssl httpd...')
    else:
        server_address = (BIND_IP, HOST_HTTP_PORT)
        httpd = server_class(server_address, handler_class)
        logging.info('Starting httpd...')
    httpd.serve_forever()
    httpd.server_close()