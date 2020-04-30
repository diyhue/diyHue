import logging
import ssl
import os
import random
import json
import uuid
import copy
import Globals

from Config import saveConfig
from HueEmulator3 import sanitizeBridgeScenes, scan_for_lights
from threading import Thread
from time import sleep, strftime
from subprocess import Popen, check_output, call
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse
from modules import modules, deconz, tradfri
from functions.html import (description, webform_hue, webform_linkbutton,
                            webform_milight, webformDeconz, webformTradfri, lightsHttp)


cwd = os.path.split(os.path.abspath(__file__))[0]

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


def getLightsVersions():
    lights = {}
    githubCatalog = json.loads(requests.get('https://raw.githubusercontent.com/diyhue/Lights/master/catalog.json').text)
    for light in Globals.bridge_config["lights_address"].keys():
        if Globals.bridge_config["lights_address"][light]["protocol"] in ["native_single", "native_multi"]:
            if "light_nr" not in Globals.bridge_config["lights_address"][light] or Globals.bridge_config["lights_address"][light]["light_nr"] == 1:
                currentData = json.loads(requests.get('http://' + Globals.bridge_config["lights_address"][light]["ip"] + '/detect', timeout=3).text)
                lights[light] = {"name": currentData["name"], "currentVersion": currentData["version"], "lastVersion": githubCatalog[currentData["type"]]["version"], "firmware": githubCatalog[currentData["type"]]["filename"]}
    return lights


class HTTPHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'nginx'
    sys_version = ''

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
        global bridge_config
        self.read_http_request_body()

        if self.path == '/' or self.path == '/index.html':
            self._set_headers()
            f = open(cwd + '/web-ui/index.html')
            self._set_end_headers(bytes(f.read(), "utf8"))
        elif self.path == "/debug/clip.html":
            self._set_headers()
            f = open(cwd + '/clip.html', 'rb')
            self._set_end_headers(f.read())
        elif self.path == "/factory-reset":
            self._set_headers()
            saveConfig('before-reset.json')
            bridge_config = load_config(cwd + '/default-config.json')
            saveConfig()
            self._set_end_headers(bytes(json.dumps([{"success":{"configuration":"reset","backup-filename":"/opt/hue-emulator/before-reset.json"}}] ,separators=(',', ':'),ensure_ascii=False), "utf8"))
        elif self.path == '/config.js':
            self._set_headers()
            #create a new user key in case none is available
            if len(Globals.bridge_config["config"]["whitelist"]) == 0:
                Globals.bridge_config["config"]["whitelist"]["web-ui-" + str(random.randrange(0, 99999))] = {"create date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),"last use date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),"name": "WebGui User"}
            self._set_end_headers(bytes('window.config = { API_KEY: "' + list(Globals.bridge_config["config"]["whitelist"])[0] + '",};', "utf8"))
        elif self.path.endswith((".css",".map",".png",".js")):
            self._set_headers()
            f = open(cwd + '/web-ui' + self.path, 'rb')
            self._set_end_headers(f.read())
        elif self.path == '/description.xml':
            self._set_headers()
            self._set_end_headers(bytes(description(Globals.bridge_config["config"]["ipaddress"], Globals.HOST_HTTP_PORT, Globals.mac, Globals.bridge_config["config"]["name"]), "utf8"))
        elif self.path == "/lights.json":
            self._set_headers()
            self._set_end_headers(bytes(json.dumps(getLightsVersions(bridge_config) ,separators=(',', ':'),ensure_ascii=False), "utf8"))
        elif self.path.startswith("/lights"):
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            if "light" in get_parameters:
                updateLight(get_parameters["light"][0], get_parameters["filename"][0])
            self._set_end_headers(bytes(lightsHttp(), "utf8"))

        elif self.path == '/save':
            self._set_headers()
            saveConfig()
            self._set_end_headers(bytes(json.dumps([{"success":{"configuration":"saved","filename":"/opt/hue-emulator/config.json"}}] ,separators=(',', ':'),ensure_ascii=False), "utf8"))
        elif self.path.startswith("/tradfri"): #setup Tradfri gateway
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            if "code" in get_parameters:
                #register new identity
                new_identity = "Hue-Emulator-" + str(random.randrange(0, 999))
                registration = json.loads(check_output("./coap-client-linux -m post -u \"Client_identity\" -k \"" + get_parameters["code"][0] + "\" -e '{\"9090\":\"" + new_identity + "\"}' \"coaps://" + get_parameters["ip"][0] + ":5684/15011/9063\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
                Globals.bridge_config["tradfri"] = {"psk": registration["9091"], "ip": get_parameters["ip"][0], "identity": new_identity}
                lights_found = tradfri.scanTradfri(bridge_config)
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
                Globals.bridge_config["lights"][new_light_id] = {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}, "type": "Extended color light", "name": "MiLight " + get_parameters["mode"][0] + " " + get_parameters["device_id"][0], "uniqueid": "1a2b3c4" + str(random.randrange(0, 99)), "modelid": "LCT015", "swversion": "1.46.13_r26312", "manufacturername": "Philips"}
                Globals.new_lights.update({new_light_id: {"name": "MiLight " + get_parameters["mode"][0] + " " + get_parameters["device_id"][0]}})
                Globals.bridge_config["lights_address"][new_light_id] = {"device_id": get_parameters["device_id"][0], "mode": get_parameters["mode"][0], "group": int(get_parameters["group"][0]), "ip": get_parameters["ip"][0], "protocol": "milight"}
                self._set_end_headers(bytes(webform_milight() + "<br> Light added", "utf8"))
            else:
                self._set_end_headers(bytes(webform_milight(), "utf8"))
        elif self.path.startswith("/hue"): #setup hue bridge
            if "linkbutton" in self.path: #Hub button emulated
                if self.headers['Authorization'] == None:
                    self._set_AUTHHEAD()
                    self._set_end_headers(bytes('You are not authenticated', "utf8"))
                    pass
                elif self.headers['Authorization'] == 'Basic ' + Globals.bridge_config["linkbutton"]["linkbutton_auth"]:
                    get_parameters = parse_qs(urlparse(self.path).query)
                    if "action=Activate" in self.path:
                        self._set_headers()
                        Globals.bridge_config["config"]["linkbutton"] = False
                        Globals.bridge_config["linkbutton"]["lastlinkbuttonpushed"] = str(int(datetime.now().timestamp()))
                        saveConfig()
                        self._set_end_headers(bytes(webform_linkbutton() + "<br> You have 30 sec to connect your device", "utf8"))
                    elif "action=Exit" in self.path:
                        self._set_AUTHHEAD()
                        self._set_end_headers(bytes('You are succesfully disconnected', "utf8"))
                    elif "action=ChangePassword" in self.path:
                        self._set_headers()
                        tmp_password = str(base64.b64encode(bytes(get_parameters["username"][0] + ":" + get_parameters["password"][0], "utf8"))).split('\'')
                        Globals.bridge_config["linkbutton"]["linkbutton_auth"] = tmp_password[1]
                        saveConfig()
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
                                Globals.bridge_config["lights_address"][light_id] = {
                                    "username": response[0]["success"]["username"],
                                    "light_id": light_nr,
                                    "ip": get_parameters["ip"][0],
                                    "protocol": "hue"
                                }
                            else:
                                logging.info('Found duplicate light: %s %s', light_id, data)
                            Globals.bridge_config["lights"][light_id] = data

                        if lights_found == 0:
                            self._set_end_headers(bytes(webform_hue() + "<br> No lights where found", "utf8"))
                        else:
                            saveConfig()
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
                for resourcelink in Globals.bridge_config["resourcelinks"].keys(): # delete all previews rules of IKEA remotes
                    if Globals.bridge_config["resourcelinks"][resourcelink]["classid"] == 15555:
                        emulator_resourcelinkes.append(resourcelink)
                        for link in Globals.bridge_config["resourcelinks"][resourcelink]["links"]:
                            pices = link.split('/')
                            if pices[1] == "rules":
                                try:
                                    del Globals.bridge_config["rules"][pices[2]]
                                except:
                                    logging.info("unable to delete the rule " + pices[2])
                for resourcelink in emulator_resourcelinkes:
                    del Globals.bridge_config["resourcelinks"][resourcelink]
                for key in get_parameters.keys():
                    if get_parameters[key][0] in ["ZLLSwitch", "ZGPSwitch"]:
                        try:
                            del Globals.bridge_config["sensors"][key]
                        except:
                            pass
                        hueSwitchId = addHueSwitch("", get_parameters[key][0])
                        for sensor in Globals.bridge_config["deconz"]["sensors"].keys():
                            if Globals.bridge_config["deconz"]["sensors"][sensor]["bridgeid"] == key:
                                Globals.bridge_config["deconz"]["sensors"][sensor] = {"hueType": get_parameters[key][0], "bridgeid": hueSwitchId}
                    else:
                        if not key.startswith("mode_"):
                            if Globals.bridge_config["sensors"][key]["modelid"] == "TRADFRI remote control":
                                if get_parameters["mode_" + key][0]  == "CT":
                                    tradfri.addTradfriCtRemote(key, get_parameters[key][0])
                                elif get_parameters["mode_" + key][0]  == "SCENE":
                                    addTradfriSceneRemote(key, get_parameters[key][0])
                            elif Globals.bridge_config["sensors"][key]["modelid"] == "TRADFRI wireless dimmer":
                                tradfri.addTradfriDimmer(key, get_parameters[key][0])
                            elif Globals.bridge_config["sensors"][key]["modelid"] == "TRADFRI on/off switch":
                                tradfri.addTradfriOnOffSwitch(key, get_parameters[key][0])
                            elif Globals.bridge_config["deconz"]["sensors"][key]["modelid"] == "TRADFRI motion sensor":
                                Globals.bridge_config["deconz"]["sensors"][key]["lightsensor"] = get_parameters[key][0]
                            #store room id in deconz sensors
                            for sensor in Globals.bridge_config["deconz"]["sensors"].keys():
                                if Globals.bridge_config["deconz"]["sensors"][sensor]["bridgeid"] == key:
                                    Globals.bridge_config["deconz"]["sensors"][sensor]["room"] = get_parameters[key][0]
                                    if Globals.bridge_config["sensors"][key]["modelid"] == "TRADFRI remote control":
                                        Globals.bridge_config["deconz"]["sensors"][sensor]["opmode"] = get_parameters["mode_" + key][0]

            else:
                deconz.scanDeconz()
            self._set_end_headers(bytes(webformDeconz({"deconz": Globals.bridge_config["deconz"], "sensors": Globals.bridge_config["sensors"], "groups": Globals.bridge_config["groups"]}), "utf8"))
        elif self.path.startswith("/switch"): #request from an ESP8266 switch or sensor
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            logging.info(pretty_json(get_parameters))
            if "devicetype" in get_parameters and get_parameters["mac"][0] not in Globals.bridge_config["emulator"]["sensors"]: #register device request
                logging.info("registering new sensor " + get_parameters["devicetype"][0])
                if get_parameters["devicetype"][0] in ["ZLLSwitch","ZGPSwitch"]:
                    logging.info(get_parameters["devicetype"][0])
                    Globals.bridge_config["emulator"]["sensors"][get_parameters["mac"][0]] = {"bridgeId": addHueSwitch("", get_parameters["devicetype"][0])}
                elif get_parameters["devicetype"][0] == "ZLLPresence":
                    logging.info("ZLLPresence")
                    Globals.bridge_config["emulator"]["sensors"][get_parameters["mac"][0]] = {"bridgeId": addHueMotionSensor(""), "lightSensorId": "0"}
                    ### detect light sensor id and save it to update directly the lightdata
                    for sensor in Globals.bridge_config["sensors"].keys():
                        if Globals.bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel" and Globals.bridge_config["sensors"][sensor]["uniqueid"] == Globals.bridge_config["sensors"][Globals.bridge_config["emulator"]["sensors"][get_parameters["mac"][0]]["bridgeId"]]["uniqueid"][:-1] + "0":
                            Globals.bridge_config["emulator"]["sensors"][get_parameters["mac"][0]]["lightSensorId"] = sensor
                            break
                    generateDxState()
            else: #switch action request
                if get_parameters["mac"][0] in Globals.bridge_config["emulator"]["sensors"]:
                    sensorId = Globals.bridge_config["emulator"]["sensors"][get_parameters["mac"][0]]["bridgeId"]
                    logging.info("match sensor " + sensorId)
                    if Globals.bridge_config["sensors"][sensorId]["config"]["on"]: #match senser id based on mac address
                        current_time = datetime.now()
                        if Globals.bridge_config["sensors"][sensorId]["type"] in ["ZLLSwitch","ZGPSwitch"]:
                            Globals.bridge_config["sensors"][sensorId]["state"].update({"buttonevent": int(get_parameters["button"][0]), "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                            dxState["sensors"][sensorId]["state"]["lastupdated"] = current_time
                        elif Globals.bridge_config["sensors"][sensorId]["type"] == "ZLLPresence":
                            lightSensorId = Globals.bridge_config["emulator"]["sensors"][get_parameters["mac"][0]]["lightSensorId"]
                            if Globals.bridge_config["sensors"][sensorId]["state"]["presence"] != True:
                                Globals.bridge_config["sensors"][sensorId]["state"]["presence"] = True
                                dxState["sensors"][sensorId]["state"]["presence"] = current_time
                            Globals.bridge_config["sensors"][sensorId]["state"]["lastupdated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                            Thread(target=motionDetected, args=[sensorId]).start()

                            if "lightlevel" in get_parameters:
                                Globals.bridge_config["sensors"][lightSensorId]["state"].update({"lightlevel": int(get_parameters["lightlevel"][0]), "dark": bool(get_parameters["dark"][0]), "daylight": bool(get_parameters["daylight"][0]), "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                            else:
                                if Globals.bridge_config["sensors"]["1"]["modelid"] == "PHDL00" and Globals.bridge_config["sensors"]["1"]["state"]["daylight"]:
                                    Globals.bridge_config["sensors"][lightSensorId]["state"].update({"lightlevel": 25000, "dark": False, "daylight": True, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") })
                                else:
                                    Globals.bridge_config["sensors"][lightSensorId]["state"].update({"lightlevel": 6000, "dark": True, "daylight": False, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S") })

                            #trigger the alarm if active
                            if Globals.bridge_config["emulator"]["alarm"]["on"] and Globals.bridge_config["emulator"]["alarm"]["lasttriggered"] + 300 < datetime.now().timestamp():
                                logging.info("Alarm triggered, sending email...")
                                requests.post("https://diyhue.org/cdn/mailNotify.php", json={"to": Globals.bridge_config["emulator"]["alarm"]["email"], "sensor": Globals.bridge_config["sensors"][sensorId]["name"]})
                                Globals.bridge_config["emulator"]["alarm"]["lasttriggered"] = int(datetime.now().timestamp())
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
            if url_pices[2] in Globals.bridge_config["config"]["whitelist"]: #if username is in whitelist
                Globals.bridge_config["config"]["UTC"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                Globals.bridge_config["config"]["localtime"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                Globals.bridge_config["config"]["whitelist"][url_pices[2]]["last use date"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                Globals.bridge_config["config"]["linkbutton"] = int(Globals.bridge_config["linkbutton"]["lastlinkbuttonpushed"]) + 30 >= int(datetime.now().timestamp())
                if len(url_pices) == 3: #print entire config
                    #trim off lightstates as per hue api
                    scenelist = {}
                    scenelist["scenes"] = copy.deepcopy(Globals.bridge_config["scenes"])
                    for scene in list(scenelist["scenes"]):
                        if "lightstates" in list(scenelist["scenes"][scene]):
                            del scenelist["scenes"][scene]["lightstates"]
                        if ("type" in scenelist["scenes"][scene]) and ("GroupScene" == scenelist["scenes"][scene]["type"]):
                            scenelist["scenes"][scene]["lights"] = {}
                            scenelist["scenes"][scene]["lights"] = Globals.bridge_config["groups"][Globals.bridge_config["scenes"][scene]["group"]]["lights"]
                    sanitizeBridgeScenes()
                    self._set_end_headers(bytes(json.dumps({"lights": Globals.bridge_config["lights"], "groups": Globals.bridge_config["groups"], "config": Globals.bridge_config["config"], "scenes": scenelist["scenes"], "schedules": Globals.bridge_config["schedules"], "rules": Globals.bridge_config["rules"], "sensors": Globals.bridge_config["sensors"], "resourcelinks": Globals.bridge_config["resourcelinks"]},separators=(',', ':'),ensure_ascii=False), "utf8"))
                elif len(url_pices) == 4: #print specified object config
                    if "scenes" == url_pices[3]: #trim lightstates for scenes
                        scenelist = {}
                        scenelist["scenes"] = copy.deepcopy(Globals.bridge_config["scenes"])
                        for scene in list(scenelist["scenes"]):
                            if "lightstates" in list(scenelist["scenes"][scene]):
                                del scenelist["scenes"][scene]["lightstates"]
                            if ("type" in scenelist["scenes"][scene]) and ("GroupScene" == scenelist["scenes"][scene]["type"]):
                                scenelist["scenes"][scene]["lights"] = {}
                                scenelist["scenes"][scene]["lights"] = Globals.bridge_config["groups"][Globals.bridge_config["scenes"][scene]["group"]]["lights"]
                        self._set_end_headers(bytes(json.dumps(scenelist["scenes"],separators=(',', ':'),ensure_ascii=False), "utf8"))
                    else:
                        self._set_end_headers(bytes(json.dumps(Globals.bridge_config[url_pices[3]],separators=(',', ':'),ensure_ascii=False), "utf8"))
                elif (len(url_pices) == 5 or (len(url_pices) == 6 and url_pices[5] == 'state')):
                    if url_pices[4] == "new": #return new lights and sensors only
                        Globals.new_lights.update({"lastscan": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")})
                        self._set_end_headers(bytes(json.dumps(Globals.new_lights ,separators=(',', ':'),ensure_ascii=False), "utf8"))
                    elif url_pices[3] == "groups" and url_pices[4] == "0":
                        any_on = False
                        all_on = True
                        for group_state in Globals.bridge_config["groups"].keys():
                            if Globals.bridge_config["groups"][group_state]["state"]["any_on"] == True:
                                any_on = True
                            else:
                                all_on = False
                        self._set_end_headers(bytes(json.dumps({"name":"Group 0","lights": [l for l in Globals.bridge_config["lights"]],"sensors": [s for s in Globals.bridge_config["sensors"]],"type":"LightGroup","state":{"all_on":all_on,"any_on":any_on},"recycle":False,"action":{"on":False,"alert":"none"}},separators=(',', ':'),ensure_ascii=False), "utf8"))
                    elif url_pices[3] == "info" and url_pices[4] == "timezones":
                        self._set_end_headers(bytes(json.dumps(Globals.bridge_config["capabilities"][url_pices[4]]["values"],separators=(',', ':'),ensure_ascii=False), "utf8"))
                    elif "scenes" == url_pices[3]: #trim lightstates for scenes
                        scenelist = {}
                        scenelist["scenes"] = copy.deepcopy(Globals.bridge_config["scenes"])
                        for scene in list(scenelist["scenes"]):
                            if ("type" in scenelist["scenes"][scene]) and ("GroupScene" == scenelist["scenes"][scene]["type"]):
                                scenelist["scenes"][scene]["lights"] = {}
                                scenelist["scenes"][scene]["lights"] = Globals.bridge_config["groups"][Globals.bridge_config["scenes"][scene]["group"]]["lights"]
                        self._set_end_headers(bytes(json.dumps(scenelist["scenes"][url_pices[4]],separators=(',', ':'),ensure_ascii=False), "utf8"))
                    else:
                        self._set_end_headers(bytes(json.dumps(Globals.bridge_config[url_pices[3]][url_pices[4]],separators=(',', ':'),ensure_ascii=False), "utf8"))
            elif (len(url_pices) == 4 and url_pices[3] == "config") or (len(url_pices) == 3 and url_pices[2] == "config"): #used by applications to discover the bridge
                self._set_end_headers(bytes(json.dumps({"name": Globals.bridge_config["config"]["name"],"datastoreversion": 70, "swversion": Globals.bridge_config["config"]["swversion"], "apiversion": Globals.bridge_config["config"]["apiversion"], "mac": Globals.bridge_config["config"]["mac"], "bridgeid": Globals.bridge_config["config"]["bridgeid"], "factorynew": False, "replacesbridgeid": None, "modelid": Globals.bridge_config["config"]["modelid"],"starterkitid":""},separators=(',', ':'),ensure_ascii=False), "utf8"))
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
                    Globals.bridge_config[category][key] = update_data[category][key]
            self._set_end_headers(bytes(json.dumps([{"success": {"/config/swupdate/checkforupdate": True}}],separators=(',', ':'),ensure_ascii=False), "utf8"))
        else:
            raw_json = self.data_string.decode('utf8')
            raw_json = raw_json.replace("\t","")
            raw_json = raw_json.replace("\n","")
            post_dictionary = json.loads(raw_json)
            logging.info(self.data_string)
        url_pices = self.path.rstrip('/').split('/')
        if len(url_pices) == 4: #data was posted to a location
            if url_pices[2] in Globals.bridge_config["config"]["whitelist"]: #check to make sure request is authorized
                if ((url_pices[3] == "lights" or url_pices[3] == "sensors") and not bool(post_dictionary)):
                    #if was a request to scan for lights of sensors
                    Globals.new_lights.clear()
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
                                lights = Globals.bridge_config["groups"][post_dictionary["group"]]["lights"]
                            for light in lights:
                                post_dictionary["lightstates"][light] = {"on": Globals.bridge_config["lights"][light]["state"]["on"]}
                                if "bri" in Globals.bridge_config["lights"][light]["state"]:
                                    post_dictionary["lightstates"][light]["bri"] = Globals.bridge_config["lights"][light]["state"]["bri"]
                                if "colormode" in Globals.bridge_config["lights"][light]["state"]:
                                    if Globals.bridge_config["lights"][light]["state"]["colormode"] in ["ct", "xy"] and Globals.bridge_config["lights"][light]["state"]["colormode"] in Globals.bridge_config["lights"][light]["state"]:
                                        post_dictionary["lightstates"][light][Globals.bridge_config["lights"][light]["state"]["colormode"]] = Globals.bridge_config["lights"][light]["state"][Globals.bridge_config["lights"][light]["state"]["colormode"]]
                                    elif Globals.bridge_config["lights"][light]["state"]["colormode"] == "hs":
                                        post_dictionary["lightstates"][light]["hue"] = Globals.bridge_config["lights"][light]["state"]["hue"]
                                        post_dictionary["lightstates"][light]["sat"] = Globals.bridge_config["lights"][light]["state"]["sat"]

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
                    Globals.bridge_config[url_pices[3]][new_object_id] = post_dictionary
                    logging.info(json.dumps([{"success": {"id": new_object_id}}], sort_keys=True, indent=4, separators=(',', ': ')))
                    self._set_end_headers(bytes(json.dumps([{"success": {"id": new_object_id}}], separators=(',', ':'),ensure_ascii=False), "utf8"))
            else:
                self._set_end_headers(bytes(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}], separators=(',', ':'),ensure_ascii=False), "utf8"))
                logging.info(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],sort_keys=True, indent=4, separators=(',', ': ')))
        elif self.path.startswith("/api") and "devicetype" in post_dictionary: #new registration by linkbutton
            last_button_press = int(Globals.bridge_config["linkbutton"]["lastlinkbuttonpushed"])
            if (Globals.args.no_link_button or last_button_press+30 >= int(datetime.now().timestamp()) or
                    Globals.bridge_config["config"]["linkbutton"]):
                username = str(uuid.uuid1()).replace('-', '')
                if post_dictionary["devicetype"].startswith("Hue Essentials"):
                    username = "hueess" + username[-26:]
                Globals.bridge_config["config"]["whitelist"][username] = {"last use date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"create date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"name": post_dictionary["devicetype"]}
                response = [{"success": {"username": username}}]
                if "generateclientkey" in post_dictionary and post_dictionary["generateclientkey"]:
                    response[0]["success"]["clientkey"] = "321c0c2ebfa7361e55491095b2f5f9db"
                self._set_end_headers(bytes(json.dumps(response,separators=(',', ':'),ensure_ascii=False), "utf8"))
                logging.info(json.dumps(response, sort_keys=True, indent=4, separators=(',', ': ')))
            else:
                self._set_end_headers(bytes(json.dumps([{"error": {"type": 101, "address": self.path, "description": "link button not pressed" }}], separators=(',', ':'),ensure_ascii=False), "utf8"))
        saveConfig()

    def do_PUT(self):
        self._set_headers()
        logging.info("in PUT method")
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        put_dictionary = json.loads(self.data_string.decode('utf8'))
        url_pices = self.path.rstrip('/').split('/')
        logging.info(self.path)
        logging.info(self.data_string)
        if url_pices[2] in Globals.bridge_config["config"]["whitelist"] or (url_pices[2] == "0" and self.client_address[0] == "127.0.0.1"):
            current_time = datetime.now()
            if len(url_pices) == 4:
                Globals.bridge_config[url_pices[3]].update(put_dictionary)
                response_location = "/" + url_pices[3] + "/"
            if len(url_pices) == 5:
                if url_pices[3] == "schedules":
                    if "status" in put_dictionary and put_dictionary["status"] == "enabled" and (Globals.bridge_config["schedules"][url_pices[4]]["localtime"].startswith("PT") or Globals.bridge_config["schedules"][url_pices[4]]["localtime"].startswith("R/PT")):
                        Globals.bridge_config["schedules"][url_pices[4]]["starttime"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                    Globals.bridge_config[url_pices[3]][url_pices[4]].update(put_dictionary)
                elif url_pices[3] == "scenes":
                    if "storelightstate" in put_dictionary:
                        if "lights" in Globals.bridge_config["scenes"][url_pices[4]]:
                            lights = Globals.bridge_config["scenes"][url_pices[4]]["lights"]
                        elif "group" in Globals.bridge_config["scenes"][url_pices[4]]:
                            lights = Globals.bridge_config["groups"][Globals.bridge_config["scenes"][url_pices[4]]["group"]]["lights"]
                        for light in lights:
                            Globals.bridge_config["scenes"][url_pices[4]]["lightstates"][light] = {}
                            Globals.bridge_config["scenes"][url_pices[4]]["lightstates"][light]["on"] = Globals.bridge_config["lights"][light]["state"]["on"]
                            if "bri" in Globals.bridge_config["lights"][light]["state"]:
                                Globals.bridge_config["scenes"][url_pices[4]]["lightstates"][light]["bri"] = Globals.bridge_config["lights"][light]["state"]["bri"]
                            if "colormode" in Globals.bridge_config["lights"][light]["state"]:
                                if Globals.bridge_config["lights"][light]["state"]["colormode"] in ["ct", "xy"]:
                                    Globals.bridge_config["scenes"][url_pices[4]]["lightstates"][light][Globals.bridge_config["lights"][light]["state"]["colormode"]] = Globals.bridge_config["lights"][light]["state"][Globals.bridge_config["lights"][light]["state"]["colormode"]]
                                elif Globals.bridge_config["lights"][light]["state"]["colormode"] == "hs" and "hue" in Globals.bridge_config["scenes"][url_pices[4]]["lightstates"][light]:
                                    Globals.bridge_config["scenes"][url_pices[4]]["lightstates"][light]["hue"] = Globals.bridge_config["lights"][light]["state"]["hue"]
                                    Globals.bridge_config["scenes"][url_pices[4]]["lightstates"][light]["sat"] = Globals.bridge_config["lights"][light]["state"]["sat"]
                elif url_pices[3] == "sensors":
                    current_time = datetime.now()
                    for key, value in put_dictionary.items():
                        if key not in dxState["sensors"][url_pices[4]]:
                            dxState["sensors"][url_pices[4]][key] = {}
                        if type(value) is dict:
                            Globals.bridge_config["sensors"][url_pices[4]][key].update(value)
                            for element in value.keys():
                                dxState["sensors"][url_pices[4]][key][element] = current_time
                        else:
                            Globals.bridge_config["sensors"][url_pices[4]][key] = value
                            dxState["sensors"][url_pices[4]][key] = current_time
                    dxState["sensors"][url_pices[4]]["state"]["lastupdated"] = current_time
                    Globals.bridge_config["sensors"][url_pices[4]]["state"]["lastupdated"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
                    if url_pices[4] == "1" and Globals.bridge_config[url_pices[3]][url_pices[4]]["modelid"] == "PHDL00":
                        Globals.bridge_config["sensors"]["1"]["config"]["configured"] = True ##mark daylight sensor as configured
                elif url_pices[3] == "groups" and "stream" in put_dictionary:
                    if "active" in put_dictionary["stream"]:
                        if put_dictionary["stream"]["active"]:
                            for light in Globals.bridge_config["groups"][url_pices[4]]["lights"]:
                                Globals.bridge_config["lights"][light]["state"]["mode"] = "streaming"
                            logging.info("start hue entertainment")
                            Popen(["/opt/hue-emulator/entertain-srv", "server_port=2100", "dtls=1", "psk_list=" + url_pices[2] + ",321c0c2ebfa7361e55491095b2f5f9db"])
                            sleep(0.2)
                            Globals.bridge_config["groups"][url_pices[4]]["stream"].update({"active": True, "owner": url_pices[2], "proxymode": "auto", "proxynode": "/bridge"})
                        else:
                            for light in Globals.bridge_config["groups"][url_pices[4]]["lights"]:
                                Globals.bridge_config["lights"][light]["state"]["mode"] = "homeautomation"
                            logging.info("stop hue entertainent")
                            Popen(["killall", "entertain-srv"])
                            Globals.bridge_config["groups"][url_pices[4]]["stream"].update({"active": False, "owner": None})
                    else:
                        Globals.bridge_config[url_pices[3]][url_pices[4]].update(put_dictionary)
                elif url_pices[3] == "lights" and "config" in put_dictionary:
                    Globals.bridge_config["lights"][url_pices[4]]["config"].update(put_dictionary["config"])
                    if "startup" in put_dictionary["config"] and Globals.bridge_config["lights_address"][url_pices[4]]["protocol"] == "native":
                        if put_dictionary["config"]["startup"]["mode"] == "safety":
                            sendRequest("http://" + Globals.bridge_config["lights_address"][url_pices[4]]["ip"] + "/", "POST", {"startup": 1})
                        elif put_dictionary["config"]["startup"]["mode"] == "powerfail":
                            sendRequest("http://" + Globals.bridge_config["lights_address"][url_pices[4]]["ip"] + "/", "POST", {"startup": 0})

                        #add exception on json output as this dictionary has tree levels
                        response_dictionary = {"success":{"/lights/" + url_pices[4] + "/config/startup": {"mode": put_dictionary["config"]["startup"]["mode"]}}}
                        self._set_end_headers(bytes(json.dumps(response_dictionary,separators=(',', ':'),ensure_ascii=False), "utf8"))
                        logging.info(json.dumps(response_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))
                        return
                else:
                    Globals.bridge_config[url_pices[3]][url_pices[4]].update(put_dictionary)
                    if url_pices[3] == "groups" and "lights" in put_dictionary: #need to update scene lightstates
                        for scene in Globals.bridge_config["scenes"]: # iterate over scenes
                            for light in put_dictionary["lights"]: # check each scene to make sure it has a lightstate for each new light
                                if "lightstates" in Globals.bridge_config["scenes"][scene] and light not in Globals.bridge_config["scenes"][scene]["lightstates"]: # copy first light state to new light
                                    if ("lights" in Globals.bridge_config["scenes"][scene] and light in Globals.bridge_config["scenes"][scene]["lights"]) or \
                                    (Globals.bridge_config["scenes"][scene]["type"] == "GroupScene" and light in Globals.bridge_config["groups"][Globals.bridge_config["scenes"][scene]["group"]]["lights"]):
                                        # Either light is in the scene or part of the group now, add lightscene based on previous scenes
                                        new_state = next(iter(Globals.bridge_config["scenes"][scene]["lightstates"]))
                                        new_state = Globals.bridge_config["scenes"][scene]["lightstates"][new_state]
                                        Globals.bridge_config["scenes"][scene]["lightstates"][light] = new_state

                response_location = "/" + url_pices[3] + "/" + url_pices[4] + "/"
            if len(url_pices) == 6:
                if url_pices[3] == "groups": #state is applied to a group
                    if url_pices[5] == "stream":
                        if "active" in put_dictionary:
                            if put_dictionary["active"]:
                                logging.info("start hue entertainment")
                                Popen(["/opt/hue-emulator/entertain-srv", "server_port=2100", "dtls=1", "psk_list=" + url_pices[2] + ",321c0c2ebfa7361e55491095b2f5f9db"])
                                sleep(0.2)
                                Globals.bridge_config["groups"][url_pices[4]]["stream"].update({"active": True, "owner": url_pices[2], "proxymode": "auto", "proxynode": "/bridge"})
                            else:
                                Popen(["killall", "entertain-srv"])
                                Globals.bridge_config["groups"][url_pices[4]]["stream"].update({"active": False, "owner": None})
                    elif "scene" in put_dictionary: #scene applied to group
                        if Globals.bridge_config["scenes"][put_dictionary["scene"]]["type"] == "GroupScene":
                            splitLightsToDevices(Globals.bridge_config["scenes"][put_dictionary["scene"]]["group"], {}, Globals.bridge_config["scenes"][put_dictionary["scene"]]["lightstates"])
                        else:
                            splitLightsToDevices(url_pices[4], {}, Globals.bridge_config["scenes"][put_dictionary["scene"]]["lightstates"])
                    elif "bri_inc" in put_dictionary or "ct_inc" in put_dictionary or "hue_inc" in put_dictionary:
                        splitLightsToDevices(url_pices[4], put_dictionary)
                    elif "scene_inc" in put_dictionary:
                        switchScene(url_pices[4], put_dictionary["scene_inc"])
                    elif url_pices[4] == "0": #if group is 0 the scene applied to all lights
                        groupZero(put_dictionary)
                    else: # the state is applied to particular group (url_pices[4])
                        if "on" in put_dictionary:
                            Globals.bridge_config["groups"][url_pices[4]]["state"]["any_on"] = put_dictionary["on"]
                            Globals.bridge_config["groups"][url_pices[4]]["state"]["all_on"] = put_dictionary["on"]
                            dxState["groups"][url_pices[4]]["state"]["any_on"] = current_time
                            dxState["groups"][url_pices[4]]["state"]["all_on"] = current_time
                        Globals.bridge_config["groups"][url_pices[4]][url_pices[5]].update(put_dictionary)
                        splitLightsToDevices(url_pices[4], put_dictionary)
                elif url_pices[3] == "lights": #state is applied to a light
                    for key in put_dictionary.keys():
                        if key in ["ct", "xy"]: #colormode must be set by bridge
                            Globals.bridge_config["lights"][url_pices[4]]["state"]["colormode"] = key
                        elif key in ["hue", "sat"]:
                            Globals.bridge_config["lights"][url_pices[4]]["state"]["colormode"] = "hs"

                    updateGroupStats(url_pices[4], Globals.bridge_config["lights"], Globals.bridge_config["groups"])
                    sendLightRequest(url_pices[4], put_dictionary, Globals.bridge_config["lights"], Globals.bridge_config["lights_address"])
                elif url_pices[3] == "sensors":
                    if url_pices[5] == "state":
                        for key in put_dictionary.keys():
                            # track time of state changes in dxState
                            if not key in Globals.bridge_config["sensors"][url_pices[4]]["state"] or Globals.bridge_config["sensors"][url_pices[4]]["state"][key] != put_dictionary[key]:
                                dxState["sensors"][url_pices[4]]["state"][key] = current_time
                    elif url_pices[4] == "1":
                        Globals.bridge_config["sensors"]["1"]["config"]["configured"] = True ##mark daylight sensor as configured
                    dxState["sensors"][url_pices[4]]["state"]["lastupdated"] = current_time
                    Globals.bridge_config["sensors"][url_pices[4]]["state"]["lastupdated"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
                if  url_pices[4] != "0" and "scene" not in put_dictionary: #group 0 is virtual, must not be saved in bridge configuration, also the recall scene
                    try:
                        Globals.bridge_config[url_pices[3]][url_pices[4]][url_pices[5]].update(put_dictionary)
                    except KeyError:
                        Globals.bridge_config[url_pices[3]][url_pices[4]][url_pices[5]] = put_dictionary
                response_location = "/" + url_pices[3] + "/" + url_pices[4] + "/" + url_pices[5] + "/"
            if len(url_pices) == 7:
                try:
                    Globals.bridge_config[url_pices[3]][url_pices[4]][url_pices[5]][url_pices[6]].update(put_dictionary)
                except KeyError:
                    Globals.bridge_config[url_pices[3]][url_pices[4]][url_pices[5]][url_pices[6]] = put_dictionary
                Globals.bridge_config[url_pices[3]][url_pices[4]][url_pices[5]][url_pices[6]] = put_dictionary
                response_location = "/" + url_pices[3] + "/" + url_pices[4] + "/" + url_pices[5] + "/" + url_pices[6] + "/"
            response_dictionary = []
            for key, value in put_dictionary.items():
                response_dictionary.append({"success":{response_location + key: value}})
            sleep(0.3)
            self._set_end_headers(bytes(json.dumps(response_dictionary,separators=(',', ':'),ensure_ascii=False), "utf8"))
            logging.info(json.dumps(response_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))
            if len(url_pices) > 4:
                rulesProcessor([url_pices[3], url_pices[4]], current_time)
            sanitizeBridgeScenes() # in case some lights where removed from group it will need to remove them also from group scenes.
        else:
            self._set_end_headers(bytes(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],separators=(',', ':'),ensure_ascii=False), "utf8"))

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self._set_end_headers(bytes(json.dumps([{"status": "success"}]), "utf8"))


    def do_DELETE(self):
        self._set_headers()
        url_pices = self.path.rstrip('/').split('/')
        if url_pices[2] in Globals.bridge_config["config"]["whitelist"]:
            if len(url_pices) == 6:
                del Globals.bridge_config[url_pices[3]][url_pices[4]][url_pices[5]]
            else:
                if url_pices[3] == "resourcelinks":
                    Thread(target=resourceRecycle).start()
                elif url_pices[3] == "sensors":
                    ## delete also related sensors
                    for sensor in list(Globals.bridge_config["sensors"]):
                        if sensor != url_pices[4] and "uniqueid" in Globals.bridge_config["sensors"][sensor] and Globals.bridge_config["sensors"][sensor]["uniqueid"].startswith(Globals.bridge_config["sensors"][url_pices[4]]["uniqueid"][:26]):
                            del Globals.bridge_config["sensors"][sensor]
                            logging.info('Delete related sensor ' + sensor)
                try:
                    del Globals.bridge_config[url_pices[3]][url_pices[4]]
                except:
                    logging.info(str([url_pices[3]]) + ": " + str(url_pices[4]) + " does not exist")
            if url_pices[3] == "lights":
                del_light = url_pices[4]

                # Delete the light address
                del Globals.bridge_config["lights_address"][del_light]

                # Remove this light from every group
                for group_id, group in Globals.bridge_config["groups"].items():
                    if "lights" in group and del_light in group["lights"]:
                        group["lights"].remove(del_light)

                # Delete the light from the deCONZ config
                for light in list(Globals.bridge_config["deconz"]["lights"]):
                    if Globals.bridge_config["deconz"]["lights"][light]["bridgeid"] == del_light:
                        del Globals.bridge_config["deconz"]["lights"][light]

                # Delete the light from any scenes
                for scene in list(Globals.bridge_config["scenes"]):
                    if del_light in Globals.bridge_config["scenes"][scene]["lightstates"]:
                        del Globals.bridge_config["scenes"][scene]["lightstates"][del_light]
                        if "lights" in Globals.bridge_config["scenes"][scene] and del_light in Globals.bridge_config["scenes"][scene]["lights"]:
                            Globals.bridge_config["scenes"][scene]["lights"].remove(del_light)
                        if ("lights" in Globals.bridge_config["scenes"][scene] and len(Globals.bridge_config["scenes"][scene]["lights"]) == 0) or len(Globals.bridge_config["scenes"][scene]["lightstates"]) == 0:
                            del Globals.bridge_config["scenes"][scene]
            elif url_pices[3] == "sensors":
                for sensor in list(Globals.bridge_config["deconz"]["sensors"]):
                    if Globals.bridge_config["deconz"]["sensors"][sensor]["bridgeid"] == url_pices[4]:
                        del Globals.bridge_config["deconz"]["sensors"][sensor]
                for sensor in list(Globals.bridge_config["emulator"]["sensors"]):
                    if Globals.bridge_config["emulator"]["sensors"][sensor]["bridgeId"] == url_pices[4]:
                        del Globals.bridge_config["emulator"]["sensors"][sensor]
            elif url_pices[3] == "groups":
                sanitizeBridgeScenes()
            logging.info(json.dumps([{"success": "/" + url_pices[3] + "/" + url_pices[4] + " deleted."}],separators=(',', ':'),ensure_ascii=False))
            self._set_end_headers(bytes(json.dumps([{"success": "/" + url_pices[3] + "/" + url_pices[4] + " deleted."}],separators=(',', ':'),ensure_ascii=False), "utf8"))


def runHTTP(server_class=ThreadingSimpleServer, handler_class=HTTPHandler):
    server_address = (Globals.BIND_IP, Globals.HOST_HTTP_PORT)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...')
    httpd.serve_forever()
    httpd.server_close()

def runHTTPS(server_class=ThreadingSimpleServer, handler_class=HTTPHandler):
    server_address = (Globals.BIND_IP, Globals.HOST_HTTPS_PORT)
    httpd = server_class(server_address, handler_class)
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(certfile="/opt/hue-emulator/cert.pem")
    ctx.options |= ssl.OP_NO_TLSv1
    ctx.options |= ssl.OP_NO_TLSv1_1
    ctx.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
    ctx.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256')
    ctx.set_ecdh_curve('prime256v1')
    #ctx.set_alpn_protocols(['h2', 'http/1.1'])
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    logging.info('Starting ssl httpd...')
    httpd.serve_forever()
    httpd.server_close()