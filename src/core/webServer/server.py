import base64
import copy
import json
import random
import ssl
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from subprocess import Popen, check_output
from threading import Thread
from time import sleep
from urllib.parse import parse_qs, urlparse

import requests

import configManager
import logManager
import lightManager
from functions import nextFreeId
from functions.json import pretty_json
from lightManager.core.lightRequest import sendLightRequest
from functions.request import sendRequest
from lightManager.core.updateGroup import updateGroupStats
from protocols import deconz, tradfri, native, milight, hue
from protocols.hue.scheduler import generateDxState, rulesProcessor
from protocols.hue.sensors import addHueSwitch, addHueMotionSensor, motionDetected

bridge_config = configManager.bridgeConfig.json_config
logging = logManager.logger.get_logger(__name__)
new_lights = configManager.runtimeConfig.newLights
dxState = configManager.runtimeConfig.dxState
HOST_HTTP_PORT = configManager.runtimeConfig.arg["HTTP_PORT"]


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
                                      format % args))
            else:
                self.logging.debug("%s - %s" %
                                   (self.address_string(),
                                    format % args))
        except:
            self.logging.warning("Could not get return code: %s - %s" %
                                 (self.address_string(),
                                  format % args))
        return

    def _set_headers(self):

        self.send_response(200)

        mimetypes = {"json": "application/json", "map": "application/json", "html": "text/html",
                     "xml": "application/xml", "js": "text/javascript", "css": "text/css", "png": "image/png"}
        if self.path.endswith((".html", ".json", ".css", ".map", ".png", ".js", ".xml")):
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
        # Some older Philips Tv's sent non-standard HTTP GET requests with a Content-Lenght and a
        # body. The HTTP body needs to be consumed and ignored in order to request be handle correctly.
        cwd = configManager.coreConfig.projectDir
        self.read_http_request_body()

        if self.path == '/' or self.path == '/index.html':
            self._set_headers()
            with open(cwd + '/web-ui/index.html') as f:
                self._set_end_headers(bytes(f.read(), "utf8"))
        elif self.path == "/debug/clip.html":
            self._set_headers()
            with open(cwd + '/debug/clip.html', 'rb') as f:
                self._set_end_headers(f.read())
        elif self.path == "/factory-reset":
            self._set_headers()
            previous = configManager.bridgeConfig.reset_config()
            previous = configManager.bridgeConfig.configDir + previous
            self._set_end_headers(bytes(
                json.dumps([{"success": {"configuration": "reset", "backup-filename": previous}}],
                           separators=(',', ':'), ensure_ascii=False), "utf8"))
        elif self.path == '/config.js':
            self._set_headers()
            # create a new user key in case none is available
            # TODO: make more secure...
            if len(bridge_config["config"]["whitelist"]) == 0:
                bridge_config["config"]["whitelist"]["web-ui-" + str(random.randrange(0, 99999))] = {
                    "create date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "last use date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), "name": "WebGui User"}
            self._set_end_headers(
                bytes('window.config = { API_KEY: "' + list(bridge_config["config"]["whitelist"])[0] + '",};', "utf8"))
        elif self.path.endswith((".css", ".map", ".png", ".js", ".webmanifest")):
            # TODO: make web ui under /web to avoid this mess
            self._set_headers()
            with open(cwd + '/web-ui' + self.path, 'rb') as f:
                self._set_end_headers(f.read())
        elif self.path == '/description.xml':
            self._set_headers()
            HOST_HTTP_PORT = configManager.runtimeConfig.arg["HTTP_PORT"]
            mac = configManager.runtimeConfig.arg["MAC"]
            self._set_end_headers(bytes(
                lightManager.core.html.description(bridge_config["config"]["ipaddress"], HOST_HTTP_PORT, mac, bridge_config["config"]["name"]),
                "utf8"))
        elif self.path == "/lights.json":
            self._set_headers()
            self._set_end_headers(
                bytes(json.dumps(native.updater.getLightsVersions(), separators=(',', ':'), ensure_ascii=False), "utf8"))
        elif self.path.startswith("/lights"):
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            if "light" in get_parameters:
                native.updater.updateLight(get_parameters["light"][0], get_parameters["filename"][0])
            self._set_end_headers(bytes(lightManager.core.html.lightsHttp(), "utf8"))

        elif self.path == '/save':
            self._set_headers()
            filename = configManager.bridgeConfig.save_config()
            self._set_end_headers(bytes(
                json.dumps([{"success": {"configuration": "saved", "filename": filename}}],
                           separators=(',', ':'), ensure_ascii=False), "utf8"))
        elif self.path.startswith("/tradfri"):  # setup Tradfri gateway
            # TODO: purge tradfri, milight, hue, deconz, and switch... very messy
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            if "code" in get_parameters:
                # register new identity
                new_identity = "Hue-Emulator-" + str(random.randrange(0, 999))
                registration = json.loads(check_output(
                    "./coap-client-linux -m post -u \"Client_identity\" -k \"" + get_parameters["code"][
                        0] + "\" -e '{\"9090\":\"" + new_identity + "\"}' \"coaps://" + get_parameters["ip"][
                        0] + ":5684/15011/9063\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
                bridge_config["tradfri"] = {"psk": registration["9091"], "ip": get_parameters["ip"][0],
                                            "identity": new_identity}
                lights_found = tradfri.discover.scanTradfri()
                if lights_found == 0:
                    self._set_end_headers(bytes(tradfri.html.webformTradfri() + "<br> No lights where found", "utf8"))
                else:
                    self._set_end_headers(
                        bytes(tradfri.html.webformTradfri() + "<br> " + str(lights_found) + " lights where found", "utf8"))
            else:
                self._set_end_headers(bytes(tradfri.html.webformTradfri(), "utf8"))
        elif self.path.startswith("/milight"):  # setup milight bulb
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            if "device_id" in get_parameters:
                # register new mi-light
                new_light_id = nextFreeId(bridge_config, "lights")
                bridge_config["lights"][new_light_id] = {
                    "state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none",
                              "effect": "none", "colormode": "ct", "reachable": True}, "type": "Extended color light",
                    "name": "MiLight " + get_parameters["mode"][0] + " " + get_parameters["device_id"][0],
                    "uniqueid": "1a2b3c4" + str(random.randrange(0, 99)), "modelid": "LCT015",
                    "swversion": "1.46.13_r26312", "manufacturername": "Philips"}
                new_lights.update({new_light_id: {
                    "name": "MiLight " + get_parameters["mode"][0] + " " + get_parameters["device_id"][0]}})
                bridge_config["lights_address"][new_light_id] = {"device_id": get_parameters["device_id"][0],
                                                                 "mode": get_parameters["mode"][0],
                                                                 "group": int(get_parameters["group"][0]),
                                                                 "ip": get_parameters["ip"][0], "protocol": "milight"}
                self._set_end_headers(bytes(milight.html.webform_milight() + "<br> Light added", "utf8"))
            else:
                self._set_end_headers(bytes(milight.html.webform_milight(), "utf8"))
        elif self.path.startswith("/hue"):  # setup hue bridge
            if "linkbutton" in self.path:  # Hub button emulated
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
                        self._set_end_headers(
                            bytes(
                                lightManager.core.html.webform_linkbutton() + "<br> You have 30 sec to connect your device", "utf8"))
                    elif "action=Exit" in self.path:
                        self._set_AUTHHEAD()
                        self._set_end_headers(bytes('You are succesfully disconnected', "utf8"))
                    elif "action=ChangePassword" in self.path:
                        self._set_headers()
                        tmp_password = str(base64.b64encode(
                            bytes(get_parameters["username"][0] + ":" + get_parameters["password"][0], "utf8"))).split(
                            '\'')
                        bridge_config["linkbutton"]["linkbutton_auth"] = tmp_password[1]
                        configManager.bridgeConfig.save_config()
                        self._set_end_headers(bytes(
                            lightManager.core.html.webform_linkbutton() + '<br> Your credentials are succesfully change. Please logout then login again',
                            "utf8"))
                    else:
                        self._set_headers()
                        self._set_end_headers(bytes(lightManager.core.html.webform_linkbutton(), "utf8"))
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
                    response = json.loads(sendRequest("http://" + get_parameters["ip"][0] + "/api/", "POST",
                                                      "{\"devicetype\":\"Hue Emulator\"}"))
                    if "success" in response[0]:
                        hue_lights = json.loads(sendRequest(
                            "http://" + get_parameters["ip"][0] + "/api/" + response[0]["success"][
                                "username"] + "/lights", "GET", "{}"))
                        logging.debug('Got response from hue bridge: %s', hue_lights)

                        # Look through all lights in the response, and check if we've seen them before
                        lights_found = 0
                        for light_nr, data in hue_lights.items():
                            light_id = lightManager.core.control.find_light_in_config_from_uid(bridge_config, data['uniqueid'])
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
                            self._set_end_headers(bytes(hue.html.webform_hue() + "<br> No lights where found", "utf8"))
                        else:
                            configManager.bridgeConfig.save_config()
                            self._set_end_headers(
                                bytes(hue.html.webform_hue() + "<br> " + str(lights_found) + " lights were found", "utf8"))
                    else:
                        self._set_end_headers(bytes(hue.html.webform_hue() + "<br> unable to connect to hue bridge", "utf8"))
                else:
                    self._set_end_headers(bytes(hue.html.webform_hue(), "utf8"))
        elif self.path.startswith("/deconz"):  # setup imported deconz sensors
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            # clean all rules related to deconz Switches
            if get_parameters:
                emulator_resourcelinkes = []
                for resourcelink in bridge_config["resourcelinks"].keys():  # delete all previews rules of IKEA remotes
                    if bridge_config["resourcelinks"][resourcelink]["classid"] == 15555:
                        emulator_resourcelinkes.append(resourcelink)
                        for link in bridge_config["resourcelinks"][resourcelink]["links"]:
                            pieces = link.split('/')
                            if pieces[1] == "rules":
                                try:
                                    del bridge_config["rules"][pieces[2]]
                                except:
                                    logging.info("unable to delete the rule " + pieces[2])
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
                                bridge_config["deconz"]["sensors"][sensor] = {"hueType": get_parameters[key][0],
                                                                              "bridgeid": hueSwitchId}
                    else:
                        if not key.startswith("mode_"):
                            if bridge_config["sensors"][key]["modelid"] == "TRADFRI remote control":
                                if get_parameters["mode_" + key][0] == "CT":
                                    tradfri.sensors.addTradfriCtRemote(key, get_parameters[key][0])
                                elif get_parameters["mode_" + key][0] == "SCENE":
                                    tradfri.sensors.addTradfriSceneRemote(key, get_parameters[key][0])
                            elif bridge_config["sensors"][key]["modelid"] == "TRADFRI wireless dimmer":
                                tradfri.sensors.addTradfriDimmer(key, get_parameters[key][0])
                            elif bridge_config["sensors"][key]["modelid"] == "TRADFRI on/off switch":
                                tradfri.sensors.addTradfriOnOffSwitch(key, get_parameters[key][0])
                            elif bridge_config["deconz"]["sensors"][key]["modelid"] == "TRADFRI motion sensor":
                                bridge_config["deconz"]["sensors"][key]["lightsensor"] = get_parameters[key][0]
                            # store room id in deconz sensors
                            for sensor in bridge_config["deconz"]["sensors"].keys():
                                if bridge_config["deconz"]["sensors"][sensor]["bridgeid"] == key:
                                    bridge_config["deconz"]["sensors"][sensor]["room"] = get_parameters[key][0]
                                    if bridge_config["sensors"][key]["modelid"] == "TRADFRI remote control":
                                        bridge_config["deconz"]["sensors"][sensor]["opmode"] = \
                                            get_parameters["mode_" + key][0]

            else:
                Thread(target=deconz.deconz.scanDeconz).start()
            self._set_end_headers(bytes(deconz.html.webformDeconz(
                {"deconz": bridge_config["deconz"], "sensors": bridge_config["sensors"],
                 "groups": bridge_config["groups"]}), "utf8"))
        elif self.path.startswith("/switch"):  # request from an ESP8266 switch or sensor
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            logging.info(pretty_json(get_parameters))
            if "devicetype" in get_parameters and get_parameters["mac"][0] not in bridge_config["emulator"][
                "sensors"]:  # register device request
                logging.info("registering new sensor " + get_parameters["devicetype"][0])
                if get_parameters["devicetype"][0] in ["ZLLSwitch", "ZGPSwitch"]:
                    logging.info(get_parameters["devicetype"][0])
                    bridge_config["emulator"]["sensors"][get_parameters["mac"][0]] = {
                        "bridgeId": addHueSwitch("", get_parameters["devicetype"][0])}
                elif get_parameters["devicetype"][0] == "ZLLPresence":
                    logging.info("ZLLPresence")
                    bridge_config["emulator"]["sensors"][get_parameters["mac"][0]] = {
                        "bridgeId": addHueMotionSensor(""), "lightSensorId": "0"}
                    ### detect light sensor id and save it to update directly the lightdata
                    for sensor in bridge_config["sensors"].keys():
                        if bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel" and \
                                bridge_config["sensors"][sensor]["uniqueid"] == bridge_config["sensors"][
                                                                                    bridge_config["emulator"][
                                                                                        "sensors"][
                                                                                        get_parameters["mac"][0]][
                                                                                        "bridgeId"]]["uniqueid"][
                                                                                :-1] + "0":
                            bridge_config["emulator"]["sensors"][get_parameters["mac"][0]]["lightSensorId"] = sensor
                            break
                    generateDxState()
            else:  # switch action request
                if get_parameters["mac"][0] in bridge_config["emulator"]["sensors"]:
                    sensorId = bridge_config["emulator"]["sensors"][get_parameters["mac"][0]]["bridgeId"]
                    logging.info("match sensor " + sensorId)
                    if bridge_config["sensors"][sensorId]["config"]["on"]:  # match senser id based on mac address
                        current_time = datetime.now()
                        if bridge_config["sensors"][sensorId]["type"] in ["ZLLSwitch", "ZGPSwitch"]:
                            bridge_config["sensors"][sensorId]["state"].update(
                                {"buttonevent": int(get_parameters["button"][0]),
                                 "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                            if "battery" in get_parameters:
                                bridge_config["sensors"][sensorId]["config"]["battery"] = int(
                                    get_parameters["battery"][0])
                            dxState["sensors"][sensorId]["state"]["lastupdated"] = current_time
                        elif bridge_config["sensors"][sensorId]["type"] == "ZLLPresence":
                            lightSensorId = bridge_config["emulator"]["sensors"][get_parameters["mac"][0]][
                                "lightSensorId"]
                            if bridge_config["sensors"][sensorId]["state"]["presence"] != True:
                                bridge_config["sensors"][sensorId]["state"]["presence"] = True
                                dxState["sensors"][sensorId]["state"]["presence"] = current_time
                            bridge_config["sensors"][sensorId]["state"]["lastupdated"] = datetime.utcnow().strftime(
                                "%Y-%m-%dT%H:%M:%S")
                            Thread(target=motionDetected, args=[sensorId]).start()

                            if "lightlevel" in get_parameters:
                                bridge_config["sensors"][lightSensorId]["state"].update(
                                    {"lightlevel": int(get_parameters["lightlevel"][0]),
                                     "dark": bool(get_parameters["dark"][0]),
                                     "daylight": bool(get_parameters["daylight"][0]),
                                     "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                            else:
                                if bridge_config["sensors"]["1"]["modelid"] == "PHDL00" and \
                                        bridge_config["sensors"]["1"]["state"]["daylight"]:
                                    bridge_config["sensors"][lightSensorId]["state"].update(
                                        {"lightlevel": 25000, "dark": False, "daylight": True,
                                         "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                                else:
                                    bridge_config["sensors"][lightSensorId]["state"].update(
                                        {"lightlevel": 6000, "dark": True, "daylight": False,
                                         "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})

                            # trigger the alarm if active
                            if bridge_config["emulator"]["alarm"]["on"] and bridge_config["emulator"]["alarm"][
                                "lasttriggered"] + 300 < datetime.now().timestamp():
                                logging.info("Alarm triggered, sending email...")
                                requests.post("https://diyhue.org/cdn/mailNotify.php",
                                              json={"to": bridge_config["emulator"]["alarm"]["email"],
                                                    "sensor": bridge_config["sensors"][sensorId]["name"]})
                                bridge_config["emulator"]["alarm"]["lasttriggered"] = int(datetime.now().timestamp())
                                # triger_horn() need development
                        rulesProcessor(["sensors", sensorId],
                                       current_time)  # process the rules to perform the action configured by application
            self._set_end_headers(bytes("done", "utf8"))
        elif self.path.startswith("/scan"):  # rescan
            self._set_headers()
            lightManager.core.discover.scan_for_lights()
            self._set_end_headers(bytes("done", "utf8"))
        else:
            url_pieces = self.path.rstrip('/').split('/') # last response for getting the config this totally needs to go
            if len(url_pieces) < 3:
                # self._set_headers_error()
                self.send_error(404, 'not found')
                return
            else:
                self._set_headers()
            if url_pieces[2] in bridge_config["config"]["whitelist"]:  # if username is in whitelist
                # TODO: instead of storing time in a config file, dynamically generate return output (think django templates)
                bridge_config["config"]["UTC"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                bridge_config["config"]["localtime"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                bridge_config["config"]["whitelist"][url_pieces[2]]["last use date"] = datetime.now().strftime(
                    "%Y-%m-%dT%H:%M:%S")
                bridge_config["config"]["linkbutton"] = int(
                    bridge_config["linkbutton"]["lastlinkbuttonpushed"]) + 30 >= int(datetime.now().timestamp())
                if len(url_pieces) == 3:  # print entire config
                    # trim off lightstates as per hue api
                    scenelist = {}
                    scenelist["scenes"] = copy.deepcopy(bridge_config["scenes"])
                    for scene in list(scenelist["scenes"]):
                        if "lightstates" in list(scenelist["scenes"][scene]):
                            del scenelist["scenes"][scene]["lightstates"]
                        if ("type" in scenelist["scenes"][scene]) and (
                                "GroupScene" == scenelist["scenes"][scene]["type"]):
                            scenelist["scenes"][scene]["lights"] = {}
                            scenelist["scenes"][scene]["lights"] = \
                                bridge_config["groups"][bridge_config["scenes"][scene]["group"]]["lights"]
                    configManager.bridgeConfig.sanitizeBridgeScenes()
                    self._set_end_headers(bytes(json.dumps(
                        {"lights": bridge_config["lights"], "groups": bridge_config["groups"],
                         "config": bridge_config["config"], "scenes": scenelist["scenes"],
                         "schedules": bridge_config["schedules"], "rules": bridge_config["rules"],
                         "sensors": bridge_config["sensors"], "resourcelinks": bridge_config["resourcelinks"]},
                        separators=(',', ':'), ensure_ascii=False), "utf8"))
                elif len(url_pieces) == 4:  # print specified object config
                    if "scenes" == url_pieces[3]:  # trim lightstates for scenes
                        scenelist = {}
                        scenelist["scenes"] = copy.deepcopy(bridge_config["scenes"])
                        for scene in list(scenelist["scenes"]):
                            if "lightstates" in list(scenelist["scenes"][scene]):
                                del scenelist["scenes"][scene]["lightstates"]
                            if ("type" in scenelist["scenes"][scene]) and (
                                    "GroupScene" == scenelist["scenes"][scene]["type"]):
                                scenelist["scenes"][scene]["lights"] = {}
                                scenelist["scenes"][scene]["lights"] = \
                                    bridge_config["groups"][bridge_config["scenes"][scene]["group"]]["lights"]
                        self._set_end_headers(
                            bytes(json.dumps(scenelist["scenes"], separators=(',', ':'), ensure_ascii=False), "utf8"))
                    else:
                        self._set_end_headers(
                            bytes(json.dumps(bridge_config[url_pieces[3]], separators=(',', ':'), ensure_ascii=False),
                                  "utf8"))
                elif (len(url_pieces) == 5 or (len(url_pieces) == 6 and url_pieces[5] == 'state')):
                    if url_pieces[4] == "new":  # return new lights and sensors only
                        if url_pieces[3] == 'lights':
                            new_lights.update({"lastscan": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")})
                            self._set_end_headers(bytes(json.dumps(new_lights ,separators=(',', ':'),ensure_ascii=False), "utf8"))
                        elif url_pieces[3] == 'sensors':
                            # Return nothing - how should we implement this?
                            self._set_end_headers(bytes(json.dumps({} ,separators=(',', ':'),ensure_ascii=False), "utf8"))
                        new_lights.update({"lastscan": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")})
                        self._set_end_headers(
                            bytes(json.dumps(new_lights, separators=(',', ':'), ensure_ascii=False), "utf8"))
                    elif url_pieces[3] == "groups" and url_pieces[4] == "0":
                        any_on = False
                        all_on = True
                        for group_state in bridge_config["groups"].keys():
                            if bridge_config["groups"][group_state]["state"]["any_on"] == True:
                                any_on = True
                            else:
                                all_on = False
                        self._set_end_headers(bytes(json.dumps(
                            {"name": "Group 0", "lights": [l for l in bridge_config["lights"]],
                             "sensors": [s for s in bridge_config["sensors"]], "type": "LightGroup",
                             "state": {"all_on": all_on, "any_on": any_on}, "recycle": False,
                             "action": {"on": False, "alert": "none"}}, separators=(',', ':'), ensure_ascii=False),
                            "utf8"))
                    elif url_pieces[3] == "info" and url_pieces[4] == "timezones":
                        self._set_end_headers(bytes(
                            json.dumps(bridge_config["capabilities"][url_pieces[4]]["values"], separators=(',', ':'),
                                       ensure_ascii=False), "utf8"))
                    elif "scenes" == url_pieces[3]:  # trim lightstates for scenes
                        scenelist = {}
                        scenelist["scenes"] = copy.deepcopy(bridge_config["scenes"])
                        for scene in list(scenelist["scenes"]):
                            if ("type" in scenelist["scenes"][scene]) and (
                                    "GroupScene" == scenelist["scenes"][scene]["type"]):
                                scenelist["scenes"][scene]["lights"] = {}
                                scenelist["scenes"][scene]["lights"] = \
                                    bridge_config["groups"][bridge_config["scenes"][scene]["group"]]["lights"]
                        self._set_end_headers(bytes(
                            json.dumps(scenelist["scenes"][url_pieces[4]], separators=(',', ':'), ensure_ascii=False),
                            "utf8"))
                    else:
                        if url_pieces[4] in bridge_config[url_pieces[3]]:
                            self._set_end_headers(bytes(
                                json.dumps(bridge_config[url_pieces[3]][url_pieces[4]], separators=(',', ':'),
                                           ensure_ascii=False), "utf8"))
                        else:
                            self._set_end_headers(bytes())
            elif (len(url_pieces) == 4 and url_pieces[3] == "config") or (
                    len(url_pieces) == 3 and url_pieces[2] == "config"):  # used by applications to discover the bridge
                self._set_end_headers(bytes(json.dumps({"name": bridge_config["config"]["name"], "datastoreversion": 70,
                                                        "swversion": bridge_config["config"]["swversion"],
                                                        "apiversion": bridge_config["config"]["apiversion"],
                                                        "mac": bridge_config["config"]["mac"],
                                                        "bridgeid": bridge_config["config"]["bridgeid"],
                                                        "factorynew": False, "replacesbridgeid": None,
                                                        "modelid": bridge_config["config"]["modelid"],
                                                        "starterkitid": ""}, separators=(',', ':'), ensure_ascii=False),
                                            "utf8"))
            else:  # user is not in whitelist
                self._set_end_headers(bytes(
                    json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user"}}],
                               separators=(',', ':'), ensure_ascii=False), "utf8"))

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
            # we no longer update diyhue, only the version number to appear updated, updates are to be done on the container only
            configManager.bridgeConfig.update_swversion()
            self._set_end_headers(bytes(
                json.dumps([{"success": {"/config/swupdate/checkforupdate": True}}], separators=(',', ':'),
                           ensure_ascii=False), "utf8"))
        else:
            raw_json = self.data_string.decode('utf8')
            raw_json = raw_json.replace("\t", "")
            raw_json = raw_json.replace("\n", "")
            post_dictionary = json.loads(raw_json)
            logging.info(self.data_string)
            url_pieces = self.path.rstrip('/').split('/')
            if len(url_pieces) == 4:  # data was posted to a location
                if url_pieces[2] in bridge_config["config"]["whitelist"]:  # check to make sure request is authorized
                    if ((url_pieces[3] == "lights" or url_pieces[3] == "sensors") and not bool(post_dictionary)):
                        # if was a request to scan for lights of sensors
                        new_lights.clear()
                        Thread(target=lightManager.core.discover.scan_for_lights).start() #this needs to be fixed for issue #418
                        sleep(7)  # give no more than 5 seconds for light scanning (otherwise will face app disconnection timeout)
                        self._set_end_headers(bytes(
                            json.dumps([{"success": {"/" + url_pieces[3]: "Searching for new devices"}}],
                                       separators=(',', ':'), ensure_ascii=False), "utf8"))
                    elif url_pieces[3] == "":
                        self._set_end_headers(bytes(
                            json.dumps([{"success": {"clientkey": "321c0c2ebfa7361e55491095b2f5f9db"}}],
                                       separators=(',', ':'), ensure_ascii=False), "utf8"))
                    else:  # create object, appears to be saving resource information e.g. scenes, groups, schedules, rules, sensors, resourcelinks
                        #this is also terrible
                        # find the first unused id for new object
                        new_object_id = nextFreeId(bridge_config, url_pieces[3])
                        if url_pieces[3] == "scenes":  # store scene
                            post_dictionary.update(
                                {"version": 2, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
                                 "owner": url_pieces[2]})
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
                                elif "group" in post_dictionary and post_dictionary["group"] != "0":
                                    lights = bridge_config["groups"][post_dictionary["group"]]["lights"]
                                for light in lights:
                                    post_dictionary["lightstates"][light] = {
                                        "on": bridge_config["lights"][light]["state"]["on"]}
                                    if "bri" in bridge_config["lights"][light]["state"]:
                                        post_dictionary["lightstates"][light]["bri"] = \
                                            bridge_config["lights"][light]["state"]["bri"]
                                    if "colormode" in bridge_config["lights"][light]["state"]:
                                        if bridge_config["lights"][light]["state"]["colormode"] in ["ct", "xy"] and \
                                                bridge_config["lights"][light]["state"]["colormode"] in \
                                                bridge_config["lights"][light]["state"]:
                                            post_dictionary["lightstates"][light][
                                                bridge_config["lights"][light]["state"]["colormode"]] = \
                                                bridge_config["lights"][light]["state"][
                                                    bridge_config["lights"][light]["state"]["colormode"]]
                                        elif bridge_config["lights"][light]["state"]["colormode"] == "hs":
                                            post_dictionary["lightstates"][light]["hue"] = \
                                                bridge_config["lights"][light]["state"]["hue"]
                                            post_dictionary["lightstates"][light]["sat"] = \
                                                bridge_config["lights"][light]["state"]["sat"]

                        elif url_pieces[3] == "groups":
                            if "type" not in post_dictionary:
                                post_dictionary["type"] = "LightGroup"
                            if post_dictionary["type"] in ["Room", "Zone"] and "class" not in post_dictionary:
                                post_dictionary["class"] = "Other"
                            elif post_dictionary["type"] == "Entertainment" and "stream" not in post_dictionary:
                                post_dictionary["stream"] = {"active": False, "owner": url_pieces[2], "proxymode": "auto",
                                                             "proxynode": "/bridge"}
                            post_dictionary.update({"action": {"on": False}, "state": {"any_on": False, "all_on": False}})
                        elif url_pieces[3] == "schedules":
                            try:
                                post_dictionary.update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
                                                        "time": post_dictionary["localtime"]})
                            except KeyError:
                                post_dictionary.update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
                                                        "localtime": post_dictionary["time"]})
                            if post_dictionary["localtime"].startswith("PT") or post_dictionary["localtime"].startswith(
                                    "R/PT"):
                                post_dictionary.update({"starttime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                            if not "status" in post_dictionary:
                                post_dictionary.update({"status": "enabled"})
                        elif url_pieces[3] == "rules":
                            post_dictionary.update({"owner": url_pieces[2], "lasttriggered": "none",
                                                    "created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
                                                    "timestriggered": 0})
                            if not "status" in post_dictionary:
                                post_dictionary.update({"status": "enabled"})
                        elif url_pieces[3] == "sensors":
                            if "state" not in post_dictionary:
                                post_dictionary["state"] = {}
                            if "lastupdated" not in post_dictionary["state"]:
                                post_dictionary["state"]["lastupdated"] = "none"
                            if post_dictionary["modelid"] == "PHWA01":
                                post_dictionary["state"]["status"] = 0
                            elif post_dictionary["modelid"] == "PHA_CTRL_START":
                                post_dictionary.update({"state": {"flag": False, "lastupdated": datetime.utcnow().strftime(
                                    "%Y-%m-%dT%H:%M:%S")}, "config": {"on": True, "reachable": True}})
                        elif url_pieces[3] == "resourcelinks":
                            post_dictionary.update({"owner": url_pieces[2]})
                        generateDxState()
                        bridge_config[url_pieces[3]][new_object_id] = post_dictionary
                        logging.info(json.dumps([{"success": {"id": new_object_id}}], sort_keys=True, indent=4,
                                                separators=(',', ': ')))
                        self._set_end_headers(bytes(
                            json.dumps([{"success": {"id": new_object_id}}], separators=(',', ':'), ensure_ascii=False),
                            "utf8"))
                else:
                    self._set_end_headers(bytes(
                        json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user"}}],
                                   separators=(',', ':'), ensure_ascii=False), "utf8"))
                    logging.info(
                        json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user"}}],
                                   sort_keys=True, indent=4, separators=(',', ': ')))
            elif self.path.startswith("/api") and "devicetype" in post_dictionary:  # new registration by linkbutton
                last_button_press = int(bridge_config["linkbutton"]["lastlinkbuttonpushed"])
                if (configManager.runtimeConfig.arg["noLinkButton"] or last_button_press + 30 >= int(
                        datetime.now().timestamp()) or
                        bridge_config["config"]["linkbutton"]):
                    username = str(uuid.uuid1()).replace('-', '')
                    if post_dictionary["devicetype"].startswith("Hue Essentials"):
                        username = "hueess" + username[-26:]
                    bridge_config["config"]["whitelist"][username] = {
                        "last use date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
                        "create date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
                        "name": post_dictionary["devicetype"]}
                    response = [{"success": {"username": username}}]
                    if "generateclientkey" in post_dictionary and post_dictionary["generateclientkey"]:
                        response[0]["success"]["clientkey"] = "321c0c2ebfa7361e55491095b2f5f9db"
                    self._set_end_headers(bytes(json.dumps(response, separators=(',', ':'), ensure_ascii=False), "utf8"))
                    logging.info(json.dumps(response, sort_keys=True, indent=4, separators=(',', ': ')))
                else:
                    self._set_end_headers(bytes(json.dumps(
                        [{"error": {"type": 101, "address": self.path, "description": "link button not pressed"}}],
                        separators=(',', ':'), ensure_ascii=False), "utf8"))
            configManager.bridgeConfig.save_config()

    def do_PUT(self):
        self._set_headers()
        logging.info("in PUT method")
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        put_dictionary = json.loads(self.data_string.decode('utf8'))
        url_pieces = self.path.rstrip('/').split('/')
        logging.info(self.path)
        logging.info(self.data_string)
        if url_pieces[2] in bridge_config["config"]["whitelist"] or (url_pieces[2] == "0" and self.client_address[0] == "127.0.0.1"):
            current_time = datetime.now()
            if len(url_pieces) == 4:
                bridge_config[url_pieces[3]].update(put_dictionary)
                response_location = "/" + url_pieces[3] + "/"
            if len(url_pieces) == 5: #again appears to be storing lots of random data coming in
                if url_pieces[3] == "schedules":
                    if "status" in put_dictionary and put_dictionary["status"] == "enabled" and (
                            bridge_config["schedules"][url_pieces[4]]["localtime"].startswith("PT") or
                            bridge_config["schedules"][url_pieces[4]]["localtime"].startswith("R/PT")):
                        bridge_config["schedules"][url_pieces[4]]["starttime"] = datetime.utcnow().strftime(
                            "%Y-%m-%dT%H:%M:%S")
                    bridge_config[url_pieces[3]][url_pieces[4]].update(put_dictionary)
                elif url_pieces[3] == "scenes":
                    if "storelightstate" in put_dictionary:
                        if "lights" in bridge_config["scenes"][url_pieces[4]]:
                            lights = bridge_config["scenes"][url_pieces[4]]["lights"]
                        elif "group" in bridge_config["scenes"][url_pieces[4]]:
                            lights = bridge_config["groups"][bridge_config["scenes"][url_pieces[4]]["group"]]["lights"]
                        for light in lights:
                            bridge_config["scenes"][url_pieces[4]]["lightstates"][light] = {}
                            bridge_config["scenes"][url_pieces[4]]["lightstates"][light]["on"] = \
                                bridge_config["lights"][light]["state"]["on"]
                            if "bri" in bridge_config["lights"][light]["state"]:
                                bridge_config["scenes"][url_pieces[4]]["lightstates"][light]["bri"] = \
                                    bridge_config["lights"][light]["state"]["bri"]
                            if "colormode" in bridge_config["lights"][light]["state"]:
                                if bridge_config["lights"][light]["state"]["colormode"] in ["ct", "xy"]:
                                    bridge_config["scenes"][url_pieces[4]]["lightstates"][light][
                                        bridge_config["lights"][light]["state"]["colormode"]] = \
                                        bridge_config["lights"][light]["state"][
                                            bridge_config["lights"][light]["state"]["colormode"]]
                                elif bridge_config["lights"][light]["state"]["colormode"] == "hs" and "hue" in \
                                        bridge_config["scenes"][url_pieces[4]]["lightstates"][light]:
                                    bridge_config["scenes"][url_pieces[4]]["lightstates"][light]["hue"] = \
                                        bridge_config["lights"][light]["state"]["hue"]
                                    bridge_config["scenes"][url_pieces[4]]["lightstates"][light]["sat"] = \
                                        bridge_config["lights"][light]["state"]["sat"]
                elif url_pieces[3] == "sensors":
                    current_time = datetime.now()
                    for key, value in put_dictionary.items():
                        if key not in dxState["sensors"][url_pieces[4]]:
                            dxState["sensors"][url_pieces[4]][key] = {}
                        if type(value) is dict:
                            bridge_config["sensors"][url_pieces[4]][key].update(value)
                            for element in value.keys():
                                dxState["sensors"][url_pieces[4]][key][element] = current_time
                        else:
                            bridge_config["sensors"][url_pieces[4]][key] = value
                            dxState["sensors"][url_pieces[4]][key] = current_time
                    dxState["sensors"][url_pieces[4]]["state"]["lastupdated"] = current_time
                    bridge_config["sensors"][url_pieces[4]]["state"]["lastupdated"] = current_time.strftime(
                        "%Y-%m-%dT%H:%M:%S")
                    if url_pieces[4] == "1" and bridge_config[url_pieces[3]][url_pieces[4]]["modelid"] == "PHDL00":
                        bridge_config["sensors"]["1"]["config"][
                            "configured"] = True  ##mark daylight sensor as configured
                elif url_pieces[3] == "groups" and "stream" in put_dictionary:
                    if "active" in put_dictionary["stream"]:
                        if put_dictionary["stream"]["active"]:
                            for light in bridge_config["groups"][url_pieces[4]]["lights"]:
                                bridge_config["lights"][light]["state"]["mode"] = "streaming"
                            logging.info("start hue entertainment")
                            Popen([configManager.coreConfig.get_path("entertain-srv", project=True), "server_port=2100", "dtls=1",
                                   "psk_list=" + url_pieces[2] + ",321c0c2ebfa7361e55491095b2f5f9db"])
                            sleep(0.2)
                            bridge_config["groups"][url_pieces[4]]["stream"].update(
                                {"active": True, "owner": url_pieces[2], "proxymode": "auto", "proxynode": "/bridge"})
                        else:
                            for light in bridge_config["groups"][url_pieces[4]]["lights"]:
                                bridge_config["lights"][light]["state"]["mode"] = "homeautomation"
                            logging.info("stop hue entertainent")
                            Popen(["killall", "entertain-srv"])
                            bridge_config["groups"][url_pieces[4]]["stream"].update({"active": False, "owner": None})
                    else:
                        bridge_config[url_pieces[3]][url_pieces[4]].update(put_dictionary)
                elif url_pieces[3] == "lights" and "config" in put_dictionary:
                    bridge_config["lights"][url_pieces[4]]["config"].update(put_dictionary["config"])
                    if "startup" in put_dictionary["config"] and bridge_config["lights_address"][url_pieces[4]][
                        "protocol"] == "native":
                        if put_dictionary["config"]["startup"]["mode"] == "safety":
                            sendRequest("http://" + bridge_config["lights_address"][url_pieces[4]]["ip"] + "/", "POST",
                                        {"startup": 1})
                        elif put_dictionary["config"]["startup"]["mode"] == "powerfail":
                            sendRequest("http://" + bridge_config["lights_address"][url_pieces[4]]["ip"] + "/", "POST",
                                        {"startup": 0})

                        # add exception on json output as this dictionary has tree levels
                        response_dictionary = {"success": {"/lights/" + url_pieces[4] + "/config/startup": {
                            "mode": put_dictionary["config"]["startup"]["mode"]}}}
                        self._set_end_headers(
                            bytes(json.dumps(response_dictionary, separators=(',', ':'), ensure_ascii=False), "utf8"))
                        logging.info(json.dumps(response_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))
                        return
                else:
                    bridge_config[url_pieces[3]][url_pieces[4]].update(put_dictionary)
                    if url_pieces[3] == "groups" and "lights" in put_dictionary:  # need to update scene lightstates
                        for scene in bridge_config["scenes"]:  # iterate over scenes
                            for light in put_dictionary[
                                "lights"]:  # check each scene to make sure it has a lightstate for each new light
                                if "lightstates" in bridge_config["scenes"][scene] and light not in \
                                        bridge_config["scenes"][scene][
                                            "lightstates"]:  # copy first light state to new light
                                    if ("lights" in bridge_config["scenes"][scene] and light in
                                        bridge_config["scenes"][scene]["lights"]) or \
                                            (bridge_config["scenes"][scene]["type"] == "GroupScene" and light in
                                             bridge_config["groups"][bridge_config["scenes"][scene]["group"]][
                                                 "lights"]):
                                        # Either light is in the scene or part of the group now, add lightscene based on previous scenes
                                        new_state = next(iter(bridge_config["scenes"][scene]["lightstates"]))
                                        new_state = bridge_config["scenes"][scene]["lightstates"][new_state]
                                        bridge_config["scenes"][scene]["lightstates"][light] = new_state

                response_location = "/" + url_pieces[3] + "/" + url_pieces[4] + "/"
            if len(url_pieces) == 6:
                if url_pieces[3] == "groups":  # state is applied to a group
                    if url_pieces[5] == "stream":
                        if "active" in put_dictionary:
                            if put_dictionary["active"]:
                                logging.info("start hue entertainment")
                                Popen([configManager.coreConfig.get_path("entertain-srv", project=True), "server_port=2100", "dtls=1",
                                       "psk_list=" + url_pieces[2] + ",321c0c2ebfa7361e55491095b2f5f9db"])
                                sleep(0.2)
                                bridge_config["groups"][url_pieces[4]]["stream"].update(
                                    {"active": True, "owner": url_pieces[2], "proxymode": "auto",
                                     "proxynode": "/bridge"})
                            else:
                                Popen(["killall", "entertain-srv"])
                                bridge_config["groups"][url_pieces[4]]["stream"].update({"active": False, "owner": None})
                    elif "scene" in put_dictionary:  # scene applied to group
                        if bridge_config["scenes"][put_dictionary["scene"]]["type"] == "GroupScene":
                            lightManager.core.control.splitLightsToDevices(bridge_config["scenes"][put_dictionary["scene"]]["group"], {},
                                                                      bridge_config["scenes"][put_dictionary["scene"]]["lightstates"])
                        else:
                            lightManager.core.control.splitLightsToDevices(url_pieces[4], {},
                                                                      bridge_config["scenes"][put_dictionary["scene"]]["lightstates"])
                    elif "bri_inc" in put_dictionary or "ct_inc" in put_dictionary or "hue_inc" in put_dictionary:
                        lightManager.core.control.splitLightsToDevices(url_pieces[4], put_dictionary)
                    elif "scene_inc" in put_dictionary:
                        lightManager.core.scene.switchScene(url_pieces[4], put_dictionary["scene_inc"])
                    elif url_pieces[4] == "0":  # if group is 0 the scene applied to all lights
                        lightManager.core.control.groupZero(put_dictionary)
                    else:  # the state is applied to particular group (url_pieces[4])
                        if "on" in put_dictionary:
                            bridge_config["groups"][url_pieces[4]]["state"]["any_on"] = put_dictionary["on"]
                            bridge_config["groups"][url_pieces[4]]["state"]["all_on"] = put_dictionary["on"]
                            dxState["groups"][url_pieces[4]]["state"]["any_on"] = current_time
                            dxState["groups"][url_pieces[4]]["state"]["all_on"] = current_time
                        bridge_config["groups"][url_pieces[4]][url_pieces[5]].update(put_dictionary)
                        lightManager.core.control.splitLightsToDevices(url_pieces[4], put_dictionary)
                elif url_pieces[3] == "lights":  # state is applied to a light
                    for key in put_dictionary.keys():
                        if key in ["ct", "xy"]:  # colormode must be set by bridge
                            bridge_config["lights"][url_pieces[4]]["state"]["colormode"] = key
                        elif key in ["hue", "sat"]:
                            bridge_config["lights"][url_pieces[4]]["state"]["colormode"] = "hs"

                    updateGroupStats(url_pieces[4], bridge_config["lights"], bridge_config["groups"])
                    sendLightRequest(url_pieces[4], put_dictionary, bridge_config["lights"],
                                     bridge_config["lights_address"])
                elif url_pieces[3] == "sensors":
                    if url_pieces[5] == "state":
                        for key in put_dictionary.keys():
                            # track time of state changes in dxState
                            if not key in bridge_config["sensors"][url_pieces[4]]["state"] or \
                                    bridge_config["sensors"][url_pieces[4]]["state"][key] != put_dictionary[key]:
                                dxState["sensors"][url_pieces[4]]["state"][key] = current_time
                    elif url_pieces[4] == "1":
                        bridge_config["sensors"]["1"]["config"][
                            "configured"] = True  ##mark daylight sensor as configured
                    dxState["sensors"][url_pieces[4]]["state"]["lastupdated"] = current_time
                    bridge_config["sensors"][url_pieces[4]]["state"]["lastupdated"] = current_time.strftime(
                        "%Y-%m-%dT%H:%M:%S")
                if url_pieces[
                    4] != "0" and "scene" not in put_dictionary:  # group 0 is virtual, must not be saved in bridge configuration, also the recall scene
                    try:
                        bridge_config[url_pieces[3]][url_pieces[4]][url_pieces[5]].update(put_dictionary)
                    except KeyError:
                        bridge_config[url_pieces[3]][url_pieces[4]][url_pieces[5]] = put_dictionary
                response_location = "/" + url_pieces[3] + "/" + url_pieces[4] + "/" + url_pieces[5] + "/"
            if len(url_pieces) == 7:
                try:
                    bridge_config[url_pieces[3]][url_pieces[4]][url_pieces[5]][url_pieces[6]].update(put_dictionary)
                except KeyError:
                    bridge_config[url_pieces[3]][url_pieces[4]][url_pieces[5]][url_pieces[6]] = put_dictionary
                bridge_config[url_pieces[3]][url_pieces[4]][url_pieces[5]][url_pieces[6]] = put_dictionary
                response_location = "/" + url_pieces[3] + "/" + url_pieces[4] + "/" + url_pieces[5] + "/" + url_pieces[
                    6] + "/"
            response_dictionary = []
            for key, value in put_dictionary.items():
                response_dictionary.append({"success": {response_location + key: value}})
            sleep(0.3)
            self._set_end_headers(
                bytes(json.dumps(response_dictionary, separators=(',', ':'), ensure_ascii=False), "utf8"))
            logging.info(json.dumps(response_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))
            if len(url_pieces) > 4:
                rulesProcessor([url_pieces[3], url_pieces[4]], current_time)
            configManager.bridgeConfig.sanitizeBridgeScenes()  # in case some lights where removed from group it will need to remove them also from group scenes.
        else:
            self._set_end_headers(bytes(
                json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user"}}],
                           separators=(',', ':'), ensure_ascii=False), "utf8"))

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self._set_end_headers(bytes(json.dumps([{"status": "success"}]), "utf8"))

    def do_DELETE(self):
        self._set_headers()
        url_pieces = self.path.rstrip('/').split('/')
        if url_pieces[2] in bridge_config["config"]["whitelist"]:
            if len(url_pieces) == 6:
                del bridge_config[url_pieces[3]][url_pieces[4]][url_pieces[5]]
            else:
                if url_pieces[3] == "resourcelinks":
                    configManager.bridgeConfig.resourceRecycle()
                elif url_pieces[3] == "sensors":
                    ## delete also related sensors
                    for sensor in list(bridge_config["sensors"]):
                        if sensor != url_pieces[4] and "uniqueid" in bridge_config["sensors"][sensor] and \
                                bridge_config["sensors"][sensor]["uniqueid"].startswith(
                                    bridge_config["sensors"][url_pieces[4]]["uniqueid"][:26]):
                            del bridge_config["sensors"][sensor]
                            logging.info('Delete related sensor ' + sensor)
                try:
                    del bridge_config[url_pieces[3]][url_pieces[4]]
                except:
                    logging.info(str([url_pieces[3]]) + ": " + str(url_pieces[4]) + " does not exist")
            if url_pieces[3] == "lights":
                del_light = url_pieces[4]

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
                        if "lights" in bridge_config["scenes"][scene] and del_light in bridge_config["scenes"][scene][
                            "lights"]:
                            bridge_config["scenes"][scene]["lights"].remove(del_light)
                        if ("lights" in bridge_config["scenes"][scene] and len(
                                bridge_config["scenes"][scene]["lights"]) == 0) or len(
                            bridge_config["scenes"][scene]["lightstates"]) == 0:
                            del bridge_config["scenes"][scene]
            elif url_pieces[3] == "sensors":
                for sensor in list(bridge_config["deconz"]["sensors"]):
                    if bridge_config["deconz"]["sensors"][sensor]["bridgeid"] == url_pieces[4]:
                        del bridge_config["deconz"]["sensors"][sensor]
                for sensor in list(bridge_config["emulator"]["sensors"]):
                    if bridge_config["emulator"]["sensors"][sensor]["bridgeId"] == url_pieces[4]:
                        del bridge_config["emulator"]["sensors"][sensor]
            elif url_pieces[3] == "groups":
                configManager.bridgeConfig.sanitizeBridgeScenes()
            logging.info(
                json.dumps([{"success": "/" + url_pieces[3] + "/" + url_pieces[4] + " deleted."}], separators=(',', ':'),
                           ensure_ascii=False))
            self._set_end_headers(bytes(
                json.dumps([{"success": "/" + url_pieces[3] + "/" + url_pieces[4] + " deleted."}], separators=(',', ':'),
                           ensure_ascii=False), "utf8"))


def run(https, server_class=ThreadingSimpleServer, handler_class=S):
    BIND_IP = configManager.runtimeConfig.arg["BIND_IP"]
    HOST_HTTPS_PORT = configManager.runtimeConfig.arg["HTTPS_PORT"]
    if https:
        server_address = (BIND_IP, HOST_HTTPS_PORT)
        httpd = server_class(server_address, handler_class)
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(certfile=configManager.coreConfig.get_path("cert.pem", config=True))  # change to new cert location
        ctx.options |= ssl.OP_NO_TLSv1
        ctx.options |= ssl.OP_NO_TLSv1_1
        ctx.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
        ctx.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256')
        ctx.set_ecdh_curve('prime256v1')
        # ctx.set_alpn_protocols(['h2', 'http/1.1'])
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        logging.info('Starting ssl httpd...')
    else:
        server_address = (BIND_IP, HOST_HTTP_PORT)
        httpd = server_class(server_address, handler_class)
        logging.info('Starting httpd...')
    httpd.serve_forever()
    httpd.server_close()
