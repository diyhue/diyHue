#!/usr/bin/python3
import argparse
import base64
import copy
import json
import logging
import os
import random
import socket
import sys
import requests
import uuid
import WebServer
import Globals
from Config import saveConfig
from collections import defaultdict
from datetime import datetime, timedelta
from subprocess import Popen, check_output, call
from threading import Thread
from time import sleep, strftime
from urllib.parse import parse_qs, urlparse
from functions import light_types, nextFreeId
from functions.colors import convert_rgb_xy, convert_xy, hsv_to_rgb
from functions.ssdp import ssdpBroadcast, ssdpSearch
from functions.network import getIpAddress
from functions.docker import dockerSetup
from functions.entertainment import entertainmentService
from functions.request import sendRequest
from functions.lightRequest import sendLightRequest, syncWithLights
from functions.updateGroup import updateGroupStats
from protocols import protocols, yeelight, tasmota, shelly, native_single, native_multi, esphome, mqtt
from functions.remoteApi import remoteApi
from functions.remoteDiscover import remoteDiscover
from modules import modules, deconz, tradfri


update_lights_on_startup = False # if set to true all lights will be updated with last know state on startup.
off_if_unreachable = False # If set to true all lights that unreachable are marked as off.
protocols = [yeelight, tasmota, shelly, native_single, native_multi, esphome]

ap = argparse.ArgumentParser()

# Arguements can also be passed as Environment Variables.
ap.add_argument("--debug", action='store_true', help="Enables debug output")
ap.add_argument("--bind-ip", help="The IP address to listen on", type=str)
ap.add_argument("--docker", action='store_true', help="Enables setup for use in docker container")
ap.add_argument("--ip", help="The IP address of the host system (Docker)", type=str)
ap.add_argument("--http-port", help="The port to listen on for HTTP (Docker)", type=int)
ap.add_argument("--mac", help="The MAC address of the host system (Docker)", type=str)
ap.add_argument("--no-serve-https", action='store_true', help="Don't listen on port 443 with SSL")
ap.add_argument("--ip-range", help="Set IP range for light discovery. Format: <START_IP>,<STOP_IP>", type=str)
ap.add_argument("--scan-on-host-ip", action='store_true', help="Scan the local IP address when discovering new lights")
ap.add_argument("--deconz", help="Provide the IP address of your Deconz host. 127.0.0.1 by default.", type=str)
ap.add_argument("--no-link-button", action='store_true', help="DANGEROUS! Don't require the link button to be pressed to pair the Hue app, just allow any app to connect")
ap.add_argument("--disable-online-discover", help="Disable Online and Remote API functions")

args = ap.parse_args()

if args.debug or (os.getenv('DEBUG') and (os.getenv('DEBUG') == "true" or os.getenv('DEBUG') == "True")):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)
    
if args.bind_ip:
    Globals.BIND_IP = args.bind_ip
elif os.getenv('BIND_IP'):
    Globals.BIND_IP = os.getenv('BIND_IP')
else:
    Globals.BIND_IP = ''

if args.ip:
    HOST_IP = args.ip
elif os.getenv('IP'):
    HOST_IP = os.getenv('IP')
elif Globals.BIND_IP:
    HOST_IP = Globals.BIND_IP
else:
    HOST_IP = getIpAddress()

if args.http_port:
    Globals.HOST_HTTP_PORT = args.http_port
elif os.getenv('HTTP_PORT'):
    Globals.HOST_HTTP_PORT = os.getenv('HTTP_PORT')
else:
    Globals.HOST_HTTP_PORT = 80
Globals.HOST_HTTPS_PORT = 443 # Hardcoded for now

logging.info("Using Host %s:%s" % (HOST_IP, Globals.HOST_HTTP_PORT))

if args.mac:
    Globals.dockerMAC = args.mac
    Globals.mac = str(args.mac).replace(":","")
    print("Host MAC given as " + mac)
elif os.getenv('MAC'):
    Globals.dockerMAC = os.getenv('MAC')
    Globals.mac = str(Globals.dockerMAC).replace(":","")
    print("Host MAC given as " + mac)
else:
    Globals.dockerMAC = check_output("cat /sys/class/net/$(ip -o addr | grep %s | awk '{print $2}')/address" % HOST_IP, shell=True).decode('utf-8')[:-1]
    Globals.mac = check_output("cat /sys/class/net/$(ip -o addr | grep %s | awk '{print $2}')/address" % HOST_IP, shell=True).decode('utf-8').replace(":","")[:-1]
logging.info(Globals.mac)

if args.docker or (os.getenv('DOCKER') and os.getenv('DOCKER') == "true"):
    print("Docker Setup Initiated")
    Globals.docker = True
    dockerSetup(Globals.dockerMAC)
    print("Docker Setup Complete")
elif os.getenv('MAC'):
    Globals.dockerMAC = os.getenv('MAC')
    Globals.mac = str(Globals.dockerMAC).replace(":","")
    print("Host MAC given as " + mac)
else:
    Globals.docker = False

if args.ip_range:
    ranges = args.ip_range.split(',')
    if ranges[0] and int(ranges[0]) >= 0:
        ip_range_start = int(ranges[0])
    else:
        ip_range_start = 0

    if ranges[1] and int(ranges[1]) > 0:
        ip_range_end = int(ranges[1])
    else:
        ip_range_end = 255
elif os.getenv('IP_RANGE'):
    ranges = os.getenv('IP_RANGE').split(',')
    if ranges[0] and int(ranges[0]) >= 0:
        ip_range_start = int(ranges[0])
    else:
        ip_range_start = 0

    if ranges[1] and int(ranges[1]) > 0:
        ip_range_end = int(ranges[1])
    else:
        ip_range_end = 255
else:
    ip_range_start = os.getenv('IP_RANGE_START', 0)
    ip_range_end = os.getenv('IP_RANGE_END', 255)
logging.info("IP range for light discovery: "+str(ip_range_start)+"-"+str(ip_range_end))

if args.deconz:
  deconz_ip = args.deconz
  print("Deconz IP given as " + deconz_ip)
elif os.getenv('DECONZ'):
  deconz_ip = os.getenv('DECONZ')
  print("Deconz IP given as " + deconz_ip)
else:
  deconz_ip = "127.0.0.1"
logging.info(deconz_ip)

if args.disable_online_discover or ((os.getenv('disable-online-discover') and (os.getenv('disable-online-discover') == "true" or os.getenv('disable-online-discover') == "True"))):
    disableOnlineDiscover = True
    logging.info("Online Discovery/Remote API Disabled!")
else:
    disableOnlineDiscover = False
    logging.info("Online Discovery/Remote API Enabled!")


Globals.cwd = os.path.split(os.path.abspath(__file__))[0]



def pretty_json(data):
    return json.dumps(data, sort_keys=True,                  indent=4, separators=(',', ': '))

run_service = True

def initialize():
    Globals.initialize()
    Globals.new_lights = {}
    Globals.dxState = {"sensors": {}, "lights": {}, "groups": {}}

    try:
        path = Globals.cwd + '/config.json'
        if os.path.exists(path):
            Globals.bridge_config = load_config(path)
            logging.info("Config loaded")
        else:
            logging.info("Config not found, creating new config from default settings")
            Globals.bridge_config = load_config(Globals.cwd + '/default-config.json')
            saveConfig()
    except Exception:
        logging.exception("CRITICAL! Config file was not loaded")
        sys.exit(1)

    ip_pices = HOST_IP.split(".")
    Globals.bridge_config["config"]["ipaddress"] = HOST_IP
    Globals.bridge_config["config"]["gateway"] = ip_pices[0] + "." +  ip_pices[1] + "." + ip_pices[2] + ".1"
    Globals.bridge_config["config"]["mac"] = Globals.mac[0] + Globals.mac[1] + ":" + Globals.mac[2] + Globals.mac[3] + ":" + Globals.mac[4] + Globals.mac[5] + ":" + Globals.mac[6] + Globals.mac[7] + ":" + Globals.mac[8] + Globals.mac[9] + ":" + Globals.mac[10] + Globals.mac[11]
    Globals.bridge_config["config"]["bridgeid"] = (Globals.mac[:6] + 'FFFE' + Globals.mac[6:]).upper()
    generateDxState()
    sanitizeBridgeScenes()
    ## generte security key for Hue Essentials remote access
    if "Hue Essentials key" not in Globals.bridge_config["config"]:
        Globals.bridge_config["config"]["Hue Essentials key"] = str(uuid.uuid1()).replace('-', '')

def sanitizeBridgeScenes():
    for scene in list(Globals.bridge_config["scenes"]):
        if "type" in Globals.bridge_config["scenes"][scene] and Globals.bridge_config["scenes"][scene]["type"] == "GroupScene": # scene has "type" key and "type" is "GroupScene"
            if Globals.bridge_config["scenes"][scene]["group"] not in Globals.bridge_config["groups"]: # the group don't exist
                del Globals.bridge_config["scenes"][scene] # delete the group
                continue # avoid KeyError on next if statement
            else:
                for lightstate in list(Globals.bridge_config["scenes"][scene]["lightstates"]):
                    if lightstate not in Globals.bridge_config["groups"][Globals.bridge_config["scenes"][scene]["group"]]["lights"]: # if the light is no longer member in the group:
                        del Globals.bridge_config["scenes"][scene]["lightstates"][lightstate] # delete the lighstate of the missing light
        else: # must be a lightscene
            for lightstate in list(Globals.bridge_config["scenes"][scene]["lightstates"]):
                if lightstate not in Globals.bridge_config["lights"]: # light is not present anymore on the bridge
                    del (Globals.bridge_config["scenes"][scene]["lightstates"][lightstate]) # delete invalid lightstate

        if "lightstates" in Globals.bridge_config["scenes"][scene] and len(Globals.bridge_config["scenes"][scene]["lightstates"]) == 0: # empty scenes are useless
            del Globals.bridge_config["scenes"][scene]


def updateLight(light, filename):
    firmware = requests.get('https://github.com/diyhue/Lights/raw/master/Arduino/bin/' + filename, allow_redirects=True)
    open('/tmp/' + filename, 'wb').write(firmware.content)
    file = {'update': open('/tmp/' + filename,'rb')}
    update = requests.post('http://' + Globals.bridge_config["lights_address"][light]["ip"] + '/update', files=file)

# Make various updates to the config JSON structure to maintain backwards compatibility with old configs
def updateConfig():

    #### bridge emulator config

    if int(Globals.bridge_config["config"]["swversion"]) < 1937113020:
        Globals.bridge_config["config"]["swversion"] = "1937113020"
        Globals.bridge_config["config"]["apiversion"] = "1.35.0"

    ### end bridge config

    if "emulator" not in Globals.bridge_config:
        Globals.bridge_config["emulator"] = {"lights": {}, "sensors": {}}


    if "alarm" not in Globals.bridge_config["emulator"]:
        Globals.bridge_config["emulator"]["alarm"] = {"on": False, "email": "", "lasttriggered": 100000}
    if "alarm_config" in Globals.bridge_config:
        del Globals.bridge_config["alarm_config"]

    if "mqtt" not in Globals.bridge_config["emulator"]:
        Globals.bridge_config["emulator"]["mqtt"] = { "discoveryPrefix": "homeassistant", "enabled": False, "mqttPassword": "", "mqttPort": 1883, "mqttServer": "mqtt", "mqttUser": ""}

    if "Remote API enabled" not in Globals.bridge_config["config"]:
        Globals.bridge_config["config"]["Remote API enabled"] = False

    # Update deCONZ sensors
    for sensor_id, sensor in Globals.bridge_config["deconz"]["sensors"].items():
        if "modelid" not in sensor:
            sensor["modelid"] = Globals.bridge_config["sensors"][sensor["bridgeid"]]["modelid"]
        if sensor["modelid"] == "TRADFRI motion sensor":
            if "lightsensor" not in sensor:
                sensor["lightsensor"] = "internal"

    # Update scenes
    for scene_id, scene in Globals.bridge_config["scenes"].items():
        if "type" not in scene:
            scene["type"] = "LightGroup"

    # Update sensors
    for sensor_id, sensor in Globals.bridge_config["sensors"].items():
        if sensor["type"] == "CLIPGenericStatus":
            sensor["state"]["status"] = 0
        elif sensor["type"] == "ZLLTemperature" and sensor["modelid"] == "SML001" and sensor["manufacturername"] == "Philips":
            sensor["capabilities"] = {"certified": True, "primary": False}
            sensor["swupdate"] = {"lastinstall": "2019-03-16T21:16:21","state": "noupdates"}
            sensor["swversion"] = "6.1.1.27575"
        elif sensor["type"] == "ZLLPresence" and sensor["modelid"] == "SML001" and sensor["manufacturername"] == "Philips":
            sensor["capabilities"] = {"certified": True, "primary": True}
            sensor["swupdate"] = {"lastinstall": "2019-03-16T21:16:21","state": "noupdates"}
            sensor["swversion"] = "6.1.1.27575"
        elif sensor["type"] == "ZLLLightLevel" and sensor["modelid"] == "SML001" and sensor["manufacturername"] == "Philips":
            sensor["capabilities"] = {"certified": True, "primary": False}
            sensor["swupdate"] = {"lastinstall": "2019-03-16T21:16:21","state": "noupdates"}
            sensor["swversion"] = "6.1.1.27575"

    # Update lights
    for light_id, light_address in Globals.bridge_config["lights_address"].items():
        light = Globals.bridge_config["lights"][light_id]

        if light_address["protocol"] == "native" and "mac" not in light_address:
            light_address["mac"] = light["uniqueid"][:17]
            light["uniqueid"] = generate_unique_id()

        # Update deCONZ protocol lights
        if light_address["protocol"] == "deconz":
            # Delete old keys
            for key in list(light):
                if key in ["hascolor", "ctmax", "ctmin", "etag"]:
                    del light[key]

            if light["modelid"].startswith("TRADFRI"):
                light.update({"manufacturername": "Philips", "swversion": "1.46.13_r26312"})

                light["uniqueid"] = generate_unique_id()

                if light["type"] == "Color temperature light":
                    light["modelid"] = "LTW001"
                elif light["type"] == "Color light":
                    light["modelid"] = "LCT015"
                    light["type"] = "Extended color light"
                elif light["type"] == "Dimmable light":
                    light["modelid"] = "LWB010"

        # Update Philips lights firmware version
        if "manufacturername" in light and light["manufacturername"] == "Philips":
            swversion = "1.46.13_r26312"
            if light["modelid"] in ["LST002", "LCT015", "LTW001", "LWB010"]:
                # Update archetype for various Philips models
                if light["modelid"] in ["LTW001", "LWB010"]:
                    archetype = "classicbulb"
                    light["productname"] = "Hue white lamp"
                    light["productid"] = "Philips-LWB014-1-A19DLv3"
                    light["capabilities"] = {"certified": True,"control": {"ct": {"max": 500,"min": 153},"maxlumen": 840,"mindimlevel": 5000},"streaming": {"proxy": False,"renderer": False}}
                elif light["modelid"] == "LCT015":
                    archetype = "sultanbulb"
                    light["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.6915,0.3083],[0.17,0.7],[0.1532,0.0475]],"colorgamuttype": "C","ct": {"max": 500,"min": 153},"maxlumen": 800,"mindimlevel": 1000},"streaming": {"proxy": True,"renderer": True}}
                    light["productname"] = "Hue color lamp"
                elif light["modelid"] == "LST002":
                    archetype = "huelightstrip"
                    swversion = "5.127.1.26581"
                    light["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.704,0.296],[0.2151,0.7106],[0.138,0.08]],"colorgamuttype": "A","maxlumen": 200,"mindimlevel": 10000},"streaming": {"proxy": False,"renderer": True}}
                    light["productname"] = "Hue lightstrip plus"

                light["config"] = {"archetype": archetype, "function": "mixed", "direction": "omnidirectional"}

                if "mode" in light["state"]:
                    light["state"]["mode"] = "homeautomation"

                # Update startup config
                if "startup" not in light["config"]:
                    light["config"]["startup"] = {"mode": "safety", "configured": False}

            # Finally, update the software version
            light["swversion"] = swversion

    #set entertainment streaming to inactive on start/restart
    for group_id, group in Globals.bridge_config["groups"].items():
        if "type" in group and group["type"] == "Entertainment":
            if "stream" not in group:
                group["stream"] = {}
            group["stream"].update({"active": False, "owner": None})

        group["sensors"] = []

    #fix timezones bug
    if "values" not in Globals.bridge_config["capabilities"]["timezones"]:
        timezones = Globals.bridge_config["capabilities"]["timezones"]
        Globals.bridge_config["capabilities"]["timezones"] = {"values": timezones}

def addHueMotionSensor(uniqueid, name="Hue motion sensor"):
    new_sensor_id = nextFreeId(bridge_config, "sensors")
    if uniqueid == "":
        uniqueid = "00:17:88:01:02:"
        if len(new_sensor_id) == 1:
            uniqueid += "0" + new_sensor_id
        else:
            uniqueid += new_sensor_id
    Globals.bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue temperature sensor 1", "uniqueid": uniqueid + ":d0:5b-02-0402", "type": "ZLLTemperature", "swversion": "6.1.0.18912", "state": {"temperature": None, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False, "battery": 100, "reachable": True, "alert":"none", "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
    motion_sensor = nextFreeId(bridge_config, "sensors")
    Globals.bridge_config["sensors"][motion_sensor] = {"name": name, "uniqueid": uniqueid + ":d0:5b-02-0406", "type": "ZLLPresence", "swversion": "6.1.0.18912", "state": {"lastupdated": "none", "presence": None}, "manufacturername": "Philips", "config": {"on": False,"battery": 100,"reachable": True, "alert": "lselect", "ledindication": False, "usertest": False, "sensitivity": 2, "sensitivitymax": 2,"pending": []}, "modelid": "SML001"}
    Globals.bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue ambient light sensor", "uniqueid": uniqueid + ":d0:5b-02-0400", "type": "ZLLLightLevel", "swversion": "6.1.0.18912", "state": {"dark": True, "daylight": False, "lightlevel": 6000, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False,"battery": 100, "reachable": True, "alert": "none", "tholddark": 21597, "tholdoffset": 7000, "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
    return(motion_sensor)

def addHueSwitch(uniqueid, sensorsType):
    new_sensor_id = nextFreeId(bridge_config, "sensors")
    if uniqueid == "":
        uniqueid = "00:17:88:01:02:"
        if len(new_sensor_id) == 1:
            uniqueid += "0" + new_sensor_id + ":4d:c6-02-fc00"
        else:
            uniqueid += new_sensor_id + ":4d:c6-02-fc00"
    Globals.bridge_config["sensors"][new_sensor_id] = {"state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "name": "Dimmer Switch" if sensorsType == "ZLLSwitch" else "Tap Switch", "type": sensorsType, "modelid": "RWL021" if sensorsType == "ZLLSwitch" else "ZGPSWITCH", "manufacturername": "Philips", "swversion": "5.45.1.17846" if sensorsType == "ZLLSwitch" else "", "uniqueid": uniqueid}
    return(new_sensor_id)

#load config files
def load_config(path):
    with open(path, 'r', encoding="utf-8") as fp:
        return json.load(fp)

def resourceRecycle():
    sleep(5) #give time to application to delete all resources, then start the cleanup
    resourcelinks = {"groups": [],"lights": [], "sensors": [], "rules": [], "scenes": [], "schedules": [], "resourcelinks": []}
    for resourcelink in Globals.bridge_config["resourcelinks"].keys():
        for link in Globals.bridge_config["resourcelinks"][resourcelink]["links"]:
            link_parts = link.split("/")
            resourcelinks[link_parts[1]].append(link_parts[2])

    for resource in resourcelinks.keys():
        for key in list(Globals.bridge_config[resource]):
            if "recycle" in Globals.bridge_config[resource][key] and Globals.bridge_config[resource][key]["recycle"] and key not in resourcelinks[resource]:
                logging.info("delete " + resource + " / " + key)
                del Globals.bridge_config[resource][key]

def generateDxState():
    for sensor in Globals.bridge_config["sensors"]:
        if sensor not in Globals.dxState["sensors"] and "state" in Globals.bridge_config["sensors"][sensor]:
            Globals.dxState["sensors"][sensor] = {"state": {}}
            for key in Globals.bridge_config["sensors"][sensor]["state"].keys():
                if key in ["lastupdated", "presence", "flag", "dark", "daylight", "status"]:
                    Globals.dxState["sensors"][sensor]["state"].update({key: datetime.now()})
    for group in Globals.bridge_config["groups"]:
        if group not in Globals.dxState["groups"] and "state" in Globals.bridge_config["groups"][group]:
            Globals.dxState["groups"][group] = {"state": {}}
            for key in Globals.bridge_config["groups"][group]["state"].keys():
                Globals.dxState["groups"][group]["state"].update({key: datetime.now()})
    for light in Globals.bridge_config["lights"]:
        if light not in Globals.dxState["lights"] and "state" in Globals.bridge_config["lights"][light]:
            Globals.dxState["lights"][light] = {"state": {}}
            for key in Globals.bridge_config["lights"][light]["state"].keys():
                if key in ["on", "bri", "colormode", "reachable"]:
                    Globals.dxState["lights"][light]["state"].update({key: datetime.now()})

def schedulerProcessor():
    while run_service:
        for schedule in Globals.bridge_config["schedules"].keys():
            try:
                delay = 0
                if Globals.bridge_config["schedules"][schedule]["status"] == "enabled":
                    if Globals.bridge_config["schedules"][schedule]["localtime"][-9:-8] == "A":
                        delay = random.randrange(0, int(Globals.bridge_config["schedules"][schedule]["localtime"][-8:-6]) * 3600 + int(Globals.bridge_config["schedules"][schedule]["localtime"][-5:-3]) * 60 + int(Globals.bridge_config["schedules"][schedule]["localtime"][-2:]))
                        schedule_time = Globals.bridge_config["schedules"][schedule]["localtime"][:-9]
                    else:
                        schedule_time = Globals.bridge_config["schedules"][schedule]["localtime"]
                    if schedule_time.startswith("W"):
                        pices = schedule_time.split('/T')
                        if int(pices[0][1:]) & (1 << 6 - datetime.today().weekday()):
                            if pices[1] == datetime.now().strftime("%H:%M:%S"):
                                logging.info("execute schedule: " + schedule + " withe delay " + str(delay))
                                sendRequest(Globals.bridge_config["schedules"][schedule]["command"]["address"], Globals.bridge_config["schedules"][schedule]["command"]["method"], json.dumps(Globals.bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                    elif schedule_time.startswith("PT"):
                        timmer = schedule_time[2:]
                        (h, m, s) = timmer.split(':')
                        d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                        if Globals.bridge_config["schedules"][schedule]["starttime"] == (datetime.utcnow() - d).replace(microsecond=0).isoformat():
                            logging.info("execute timmer: " + schedule + " withe delay " + str(delay))
                            sendRequest(Globals.bridge_config["schedules"][schedule]["command"]["address"], Globals.bridge_config["schedules"][schedule]["command"]["method"], json.dumps(Globals.bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                            Globals.bridge_config["schedules"][schedule]["status"] = "disabled"
                    elif schedule_time.startswith("R/PT"):
                        timmer = schedule_time[4:]
                        (h, m, s) = timmer.split(':')
                        d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                        if Globals.bridge_config["schedules"][schedule]["starttime"] == (datetime.utcnow() - d).replace(microsecond=0).isoformat():
                            logging.info("execute timmer: " + schedule + " withe delay " + str(delay))
                            Globals.bridge_config["schedules"][schedule]["starttime"] = datetime.utcnow().replace(microsecond=0).isoformat()
                            sendRequest(Globals.bridge_config["schedules"][schedule]["command"]["address"], Globals.bridge_config["schedules"][schedule]["command"]["method"], json.dumps(Globals.bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                    else:
                        if schedule_time == datetime.now().strftime("%Y-%m-%dT%H:%M:%S"):
                            logging.info("execute schedule: " + schedule + " withe delay " + str(delay))
                            sendRequest(Globals.bridge_config["schedules"][schedule]["command"]["address"], Globals.bridge_config["schedules"][schedule]["command"]["method"], json.dumps(Globals.bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                            if Globals.bridge_config["schedules"][schedule]["autodelete"]:
                                del Globals.bridge_config["schedules"][schedule]
            except Exception as e:
                logging.info("Exception while processing the schedule " + schedule + " | " + str(e))

        if (datetime.now().strftime("%M:%S") == "00:10"): #auto save configuration every hour
            saveConfig()
            Thread(target=daylightSensor).start()
            if (datetime.now().strftime("%H") == "23" and datetime.now().strftime("%A") == "Sunday"): #backup config every Sunday at 23:00:10
                if docker:
                    saveConfig("export/config-backup-" + datetime.now().strftime("%Y-%m-%d") + ".json")
                else:
                    saveConfig("config-backup-" + datetime.now().strftime("%Y-%m-%d") + ".json")
        sleep(1)

def switchScene(group, direction):
    group_scenes = []
    current_position = -1
    possible_current_position = -1 # used in case the brigtness was changes and will be no perfect match (scene lightstates vs light states)
    break_next = False
    for scene in Globals.bridge_config["scenes"]:
        if Globals.bridge_config["groups"][group]["lights"][0] in Globals.bridge_config["scenes"][scene]["lights"]:
            group_scenes.append(scene)
            if break_next: # don't lose time as this is the scene we need
                break
            is_current_scene = True
            is_possible_current_scene = True
            for light in Globals.bridge_config["scenes"][scene]["lightstates"]:
                for key in Globals.bridge_config["scenes"][scene]["lightstates"][light].keys():
                    if key == "xy":
                        if not Globals.bridge_config["scenes"][scene]["lightstates"][light]["xy"][0] == Globals.bridge_config["lights"][light]["state"]["xy"][0] and not Globals.bridge_config["scenes"][scene]["lightstates"][light]["xy"][1] == Globals.bridge_config["lights"][light]["state"]["xy"][1]:
                            is_current_scene = False
                    else:
                        if not Globals.bridge_config["scenes"][scene]["lightstates"][light][key] == Globals.bridge_config["lights"][light]["state"][key]:
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
    logging.info("matched scene " + Globals.bridge_config["scenes"][matched_scene]["name"])

    for light in Globals.bridge_config["scenes"][matched_scene]["lights"]:
        Globals.bridge_config["lights"][light]["state"].update(Globals.bridge_config["scenes"][matched_scene]["lightstates"][light])
        if "xy" in Globals.bridge_config["scenes"][matched_scene]["lightstates"][light]:
            Globals.bridge_config["lights"][light]["state"]["colormode"] = "xy"
        elif "ct" in Globals.bridge_config["scenes"][matched_scene]["lightstates"][light]:
            Globals.bridge_config["lights"][light]["state"]["colormode"] = "ct"
        elif "hue" or "sat" in Globals.bridge_config["scenes"][matched_scene]["lightstates"][light]:
            Globals.bridge_config["lights"][light]["state"]["colormode"] = "hs"
        sendLightRequest(light, Globals.bridge_config["scenes"][matched_scene]["lightstates"][light], Globals.bridge_config["lights"], Globals.bridge_config["lights_address"])
        updateGroupStats(light, Globals.bridge_config["lights"], Globals.bridge_config["groups"])


def checkRuleConditions(rule, device, current_time, ignore_ddx=False):
    ddx = 0
    device_found = False
    ddx_sensor = []
    for condition in Globals.bridge_config["rules"][rule]["conditions"]:
        try:
            url_pices = condition["address"].split('/')
            if url_pices[1] == device[0] and url_pices[2] == device[1]:
                device_found = True
            if condition["operator"] == "eq":
                if condition["value"] == "true":
                    if not Globals.bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]:
                        return [False, 0]
                elif condition["value"] == "false":
                    if Globals.bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]:
                        return [False, 0]
                else:
                    if not int(Globals.bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]) == int(condition["value"]):
                        return [False, 0]
            elif condition["operator"] == "gt":
                if not int(Globals.bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]) > int(condition["value"]):
                    return [False, 0]
            elif condition["operator"] == "lt":
                if not int(Globals.bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]) < int(condition["value"]):
                    return [False, 0]
            elif condition["operator"] == "dx":
                if not Globals.dxState[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]] == current_time:
                    return [False, 0]
            elif condition["operator"] == "in":
                periods = condition["value"].split('/')
                if condition["value"][0] == "T":
                    timeStart = datetime.strptime(periods[0], "T%H:%M:%S").time()
                    timeEnd = datetime.strptime(periods[1], "T%H:%M:%S").time()
                    now_time = datetime.now().time()
                    if timeStart < timeEnd:
                        if not timeStart <= now_time <= timeEnd:
                            return [False, 0]
                    else:
                        if not (timeStart <= now_time or now_time <= timeEnd):
                            return [False, 0]
            elif condition["operator"] == "ddx" and ignore_ddx is False:
                if not Globals.dxState[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]] == current_time:
                        return [False, 0]
                else:
                    ddx = int(condition["value"][2:4]) * 3600 + int(condition["value"][5:7]) * 60 + int(condition["value"][-2:])
                    ddx_sensor = url_pices
        except Exception as e:
            logging.info("rule " + rule + " failed, reason:" + str(e))


    if device_found:
        return [True, ddx, ddx_sensor]
    else:
        return [False]

def ddxRecheck(rule, device, current_time, ddx_delay, ddx_sensor):
    for x in range(ddx_delay):
        if current_time != Globals.dxState[ddx_sensor[1]][ddx_sensor[2]][ddx_sensor[3]][ddx_sensor[4]]:
            logging.info("ddx rule " + rule + " canceled after " + str(x) + " seconds")
            return # rule not valid anymore because sensor state changed while waiting for ddx delay
        sleep(1)
    current_time = datetime.now()
    rule_state = checkRuleConditions(rule, device, current_time, True)
    if rule_state[0]: #if all conditions are meet again
        logging.info("delayed rule " + rule + " is triggered")
        Globals.bridge_config["rules"][rule]["lasttriggered"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
        Globals.bridge_config["rules"][rule]["timestriggered"] += 1
        for action in Globals.bridge_config["rules"][rule]["actions"]:
            sendRequest("/api/" + Globals.bridge_config["rules"][rule]["owner"] + action["address"], action["method"], json.dumps(action["body"]))

def rulesProcessor(device, current_time):
    Globals.bridge_config["config"]["localtime"] = current_time.strftime("%Y-%m-%dT%H:%M:%S") #required for operator dx to address /config/localtime
    actionsToExecute = []
    for rule in Globals.bridge_config["rules"].keys():
        if Globals.bridge_config["rules"][rule]["status"] == "enabled":
            rule_result = checkRuleConditions(rule, device, current_time)
            if rule_result[0]:
                if rule_result[1] == 0: #is not ddx rule
                    logging.info("rule " + rule + " is triggered")
                    Globals.bridge_config["rules"][rule]["lasttriggered"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
                    Globals.bridge_config["rules"][rule]["timestriggered"] += 1
                    for action in Globals.bridge_config["rules"][rule]["actions"]:
                        actionsToExecute.append(action)
                else: #if ddx rule
                    logging.info("ddx rule " + rule + " will be re validated after " + str(rule_result[1]) + " seconds")
                    Thread(target=ddxRecheck, args=[rule, device, current_time, rule_result[1], rule_result[2]]).start()
    for action in actionsToExecute:
        sendRequest("/api/" +    list(Globals.bridge_config["config"]["whitelist"])[0] + action["address"], action["method"], json.dumps(action["body"]))


def scanHost(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.02) # Very short timeout. If scanning fails this could be increased
    result = sock.connect_ex((host, port))
    sock.close()
    return result

def iter_ips(port):
    host = HOST_IP.split('.')
    if args.scan_on_host_ip:
        yield ('127.0.0.1', port)
        return
    for addr in range(ip_range_start, ip_range_end + 1):
        host[3] = str(addr)
        test_host = '.'.join(host)
        if test_host != HOST_IP:
            yield (test_host, port)

def find_hosts(port):
    validHosts = []
    for host, port in iter_ips(port):
        if scanHost(host, port) == 0:
            hostWithPort = '%s:%s' % (host, port)
            validHosts.append(hostWithPort)

    return validHosts

def find_light_in_config_from_mac_and_nr(bridge_config, mac_address, light_nr):
    for light_id, light_address in Globals.bridge_config["lights_address"].items():
        if (light_address["protocol"] in ["native", "native_single",  "native_multi"]
                and light_address["mac"] == mac_address
                and ('light_nr' not in light_address or
                    light_address['light_nr'] == light_nr)):
            return light_id
    return None

def find_light_in_config_from_uid(bridge_config, unique_id):
    for light in Globals.bridge_config["lights"].keys():
        if Globals.bridge_config["lights"][light]["uniqueid"] == unique_id:
            return light
    return None

def generate_light_name(base_name, light_nr):
    # Light name can only contain 32 characters
    suffix = ' %s' % light_nr
    return '%s%s' % (base_name[:32-len(suffix)], suffix)

def generate_unique_id():
    rand_bytes = [random.randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0],rand_bytes[1],rand_bytes[2])

def scan_for_lights(): #scan for ESP8266 lights and strips
    Thread(target=yeelight.discover, args=[]).start()
    Thread(target=tasmota.discover, args=[]).start()
    Thread(target=shelly.discover, args=[]).start()
    Thread(target=esphome.discover, args=[]).start()
    Thread(target=mqtt.discover, args=[]).start()
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
                                light_address = Globals.bridge_config["lights_address"][light]
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
                            Globals.new_lights[new_light_id] = {"name": light_name}
                            Globals.bridge_config["lights"][new_light_id] = new_light
                            Globals.bridge_config["lights_address"][new_light_id] = {
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
    deconz.scanDeconz()
    tradfri.scanTradfri()
    saveConfig()


def longPressButton(sensor, buttonevent):
    logging.info("long press detected")
    sleep(1)
    while Globals.bridge_config["sensors"][sensor]["state"]["buttonevent"] == buttonevent:
        logging.info("still pressed")
        current_time =  datetime.now()
        Globals.dxState["sensors"][sensor]["state"]["lastupdated"] = current_time
        rulesProcessor(["sensors",sensor], current_time)
        sleep(0.5)
    return


def motionDetected(sensor):
    logging.info("monitoring motion sensor " + sensor)
    while Globals.bridge_config["sensors"][sensor]["state"]["presence"] == True:
        if datetime.utcnow() - datetime.strptime(Globals.bridge_config["sensors"][sensor]["state"]["lastupdated"], "%Y-%m-%dT%H:%M:%S") > timedelta(seconds=30):
            Globals.bridge_config["sensors"][sensor]["state"]["presence"] = False
            Globals.bridge_config["sensors"][sensor]["state"]["lastupdated"] =  datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            current_time =  datetime.now()
            Globals.dxState["sensors"][sensor]["state"]["presence"] = current_time
            rulesProcessor(["sensors",sensor], current_time)
        sleep(1)
    logging.info("set motion sensor " + sensor + " to motion = False")
    return


def websocketClient():
    from ws4py.client.threadedclient import WebSocketClient
    class EchoClient(WebSocketClient):
        def opened(self):
            self.send("hello")

        def closed(self, code, reason=None):
            logging.info(("deconz websocket disconnected", code, reason))
            del Globals.bridge_config["deconz"]["websocketport"]

        def received_message(self, m):
            logging.info(m)
            message = json.loads(str(m))
            try:
                if message["r"] == "sensors":
                    bridge_sensor_id = Globals.bridge_config["deconz"]["sensors"][message["id"]]["bridgeid"]
                    if "state" in message and Globals.bridge_config["sensors"][bridge_sensor_id]["config"]["on"]:

                        #change codes for emulated hue Switches
                        if "hueType" in Globals.bridge_config["deconz"]["sensors"][message["id"]]:
                            rewriteDict = {"ZGPSwitch": {1002: 34, 3002: 16, 4002: 17, 5002: 18}, "ZLLSwitch" : {1002 : 1000, 2002: 2000, 2001: 2001, 2003: 2002, 3001: 3001, 3002: 3000, 3003: 3002, 4002: 4000, 5002: 4000} }
                            message["state"]["buttonevent"] = rewriteDict[Globals.bridge_config["deconz"]["sensors"][message["id"]]["hueType"]][message["state"]["buttonevent"]]
                        #end change codes for emulated hue Switches

                        #convert tradfri motion sensor notification to look like Hue Motion Sensor
                        if message["state"] and Globals.bridge_config["deconz"]["sensors"][message["id"]]["modelid"] == "TRADFRI motion sensor":
                            #find the light sensor id
                            light_sensor = "0"
                            for sensor in Globals.bridge_config["sensors"].keys():
                                if Globals.bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel" and Globals.bridge_config["sensors"][sensor]["uniqueid"] == Globals.bridge_config["sensors"][bridge_sensor_id]["uniqueid"][:-1] + "0":
                                    light_sensor = sensor
                                    break
                            if Globals.bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "none":
                                message["state"].update({"dark": True})
                            elif Globals.bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "astral":
                                message["state"]["dark"] = not Globals.bridge_config["sensors"]["1"]["state"]["daylight"]

                            elif Globals.bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "combined":
                                if not Globals.bridge_config["sensors"]["1"]["state"]["daylight"]:
                                    message["state"]["dark"] = True
                                elif (datetime.strptime(message["state"]["lastupdated"], "%Y-%m-%dT%H:%M:%S") - datetime.strptime(Globals.bridge_config["sensors"][light_sensor]["state"]["lastupdated"], "%Y-%m-%dT%H:%M:%S")).total_seconds() > 1200:
                                    message["state"]["dark"] = False

                            if  message["state"]["dark"]:
                                Globals.bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                            else:
                                Globals.bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 25000
                            Globals.bridge_config["sensors"][light_sensor]["state"]["dark"] = message["state"]["dark"]
                            Globals.bridge_config["sensors"][light_sensor]["state"]["daylight"] = not message["state"]["dark"]
                            Globals.bridge_config["sensors"][light_sensor]["state"]["lastupdated"] = message["state"]["lastupdated"]

                        #Xiaomi motion w/o light level sensor
                        if message["state"] and Globals.bridge_config["deconz"]["sensors"][message["id"]]["modelid"] == "lumi.sensor_motion":
                            for sensor in Globals.bridge_config["sensors"].keys():
                                if Globals.bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel" and Globals.bridge_config["sensors"][sensor]["uniqueid"] == Globals.bridge_config["sensors"][bridge_sensor_id]["uniqueid"][:-1] + "0":
                                    light_sensor = sensor
                                    break

                            if Globals.bridge_config["sensors"]["1"]["modelid"] == "PHDL00" and Globals.bridge_config["sensors"]["1"]["state"]["daylight"]:
                                Globals.bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 25000
                                Globals.bridge_config["sensors"][light_sensor]["state"]["dark"] = False
                            else:
                                Globals.bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                                Globals.bridge_config["sensors"][light_sensor]["state"]["dark"] = True

                        #convert xiaomi motion sensor to hue sensor
                        if message["state"] and Globals.bridge_config["deconz"]["sensors"][message["id"]]["modelid"] == "lumi.sensor_motion.aq2" and message["state"] and Globals.bridge_config["deconz"]["sensors"][message["id"]]["type"] == "ZHALightLevel":
                            Globals.bridge_config["sensors"][bridge_sensor_id]["state"].update(message["state"])
                            return
                        ##############

                        ##convert xiaomi vibration sensor states to hue motion sensor
                        if message["state"] and Globals.bridge_config["deconz"]["sensors"][message["id"]]["modelid"] == "lumi.vibration.aq1":
                            #find the light sensor id
                            light_sensor = "0"
                            for sensor in Globals.bridge_config["sensors"].keys():
                                if Globals.bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel" and Globals.bridge_config["sensors"][sensor]["uniqueid"] == Globals.bridge_config["sensors"][bridge_sensor_id]["uniqueid"][:-1] + "0":
                                    light_sensor = sensor
                                    break
                            logging.info("Vibration: emulated light sensor id is  " + light_sensor)
                            if Globals.bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "none":
                                message["state"].update({"dark": True})
                                logging.info("Vibration: set light sensor to dark because 'lightsensor' = 'none' ")
                            elif Globals.bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "astral":
                                message["state"]["dark"] = not Globals.bridge_config["sensors"]["1"]["state"]["daylight"]
                                logging.info("Vibration: set light sensor to " + str(not Globals.bridge_config["sensors"]["1"]["state"]["daylight"]) + " because 'lightsensor' = 'astral' ")

                            if  message["state"]["dark"]:
                                Globals.bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                            else:
                                Globals.bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 25000
                            Globals.bridge_config["sensors"][light_sensor]["state"]["dark"] = message["state"]["dark"]
                            Globals.bridge_config["sensors"][light_sensor]["state"]["daylight"] = not message["state"]["dark"]
                            Globals.bridge_config["sensors"][light_sensor]["state"]["lastupdated"] = message["state"]["lastupdated"]
                            message["state"] = {"motion": True, "lastupdated": message["state"]["lastupdated"]} #empty the message state for non Hue motion states (we need to know there was an event only)
                            logging.info("Vibration: set motion = True")
                            Thread(target=motionDetected, args=[bridge_sensor_id]).start()


                        Globals.bridge_config["sensors"][bridge_sensor_id]["state"].update(message["state"])
                        current_time = datetime.now()
                        for key in message["state"].keys():
                            Globals.dxState["sensors"][bridge_sensor_id]["state"][key] = current_time
                        rulesProcessor(["sensors", bridge_sensor_id], current_time)
                        if "buttonevent" in message["state"] and Globals.bridge_config["deconz"]["sensors"][message["id"]]["modelid"] in ["TRADFRI remote control","RWL021","TRADFRI on/off switch"]:
                            if message["state"]["buttonevent"] in [1001, 2001, 3001, 4001, 5001]:
                                Thread(target=longPressButton, args=[bridge_sensor_id, message["state"]["buttonevent"]]).start()
                        if "presence" in message["state"] and message["state"]["presence"] and Globals.bridge_config["emulator"]["alarm"]["on"] and Globals.bridge_config["emulator"]["alarm"]["lasttriggered"] + 300 < datetime.now().timestamp():
                            logging.info("Alarm triggered, sending email...")
                            requests.post("https://diyhue.org/cdn/mailNotify.php", json={"to": Globals.bridge_config["emulator"]["alarm"]["email"], "sensor": Globals.bridge_config["sensors"][bridge_sensor_id]["name"]})
                            Globals.bridge_config["emulator"]["alarm"]["lasttriggered"] = int(datetime.now().timestamp())
                    elif "config" in message and Globals.bridge_config["sensors"][bridge_sensor_id]["config"]["on"]:
                        Globals.bridge_config["sensors"][bridge_sensor_id]["config"].update(message["config"])
                elif message["r"] == "lights":
                    bridge_light_id = Globals.bridge_config["deconz"]["lights"][message["id"]]["bridgeid"]
                    if "state" in message and "colormode" not in message["state"]:
                        Globals.bridge_config["lights"][bridge_light_id]["state"].update(message["state"])
                        updateGroupStats(bridge_light_id, Globals.bridge_config["lights"], Globals.bridge_config["groups"])
            except Exception as e:
                logging.info("unable to process the request" + str(e))

    try:
        ws = EchoClient('ws://' + deconz_ip + ':' + str(Globals.bridge_config["deconz"]["websocketport"]))
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()



def updateAllLights():
    ## apply last state on startup to all bulbs, usefull if there was a power outage
    if Globals.bridge_config["deconz"]["enabled"]:
        sleep(60) #give 1 minute for deconz to have ZigBee network ready
    for light in Globals.bridge_config["lights_address"]:
        payload = {}
        payload["on"] = Globals.bridge_config["lights"][light]["state"]["on"]
        if payload["on"] and "bri" in Globals.bridge_config["lights"][light]["state"]:
            payload["bri"] = Globals.bridge_config["lights"][light]["state"]["bri"]
        sendLightRequest(light, payload, Globals.bridge_config["lights"], Globals.bridge_config["lights_address"])
        sleep(0.5)
        logging.info("update status for light " + light)

def manageDeviceLights(lights_state):
    protocol = Globals.bridge_config["lights_address"][list(lights_state.keys())[0]]["protocol"]
    payload = {}
    for light in lights_state.keys():
        if protocol == "native_multi":
            payload[Globals.bridge_config["lights_address"][light]["light_nr"]] = lights_state[light]
        elif protocol in ["native", "native_single", "milight"]:
            sendLightRequest(light, lights_state[light], Globals.bridge_config["lights"], Globals.bridge_config["lights_address"])
            if protocol == "milight": #hotfix to avoid milight hub overload
                sleep(0.05)
        else:
            Thread(target=sendLightRequest, args=[light, lights_state[light], Globals.bridge_config["lights"], Globals.bridge_config["lights_address"]]).start()
            sleep(0.1)
    if protocol == "native_multi":
        requests.put("http://"+Globals.bridge_config["lights_address"][list(lights_state.keys())[0]]["ip"]+"/state", json=payload, timeout=3)



def splitLightsToDevices(group, state, scene={}):
    groups = []
    if group == "0":
        for grp in Globals.bridge_config["groups"].keys():
            groups.append(grp)
    else:
        groups.append(group)

    lightsData = {}
    if len(scene) == 0:
        for grp in groups:
            if "bri_inc" in state:
                Globals.bridge_config["groups"][grp]["action"]["bri"] += int(state["bri_inc"])
                if Globals.bridge_config["groups"][grp]["action"]["bri"] > 254:
                    Globals.bridge_config["groups"][grp]["action"]["bri"] = 254
                elif Globals.bridge_config["groups"][grp]["action"]["bri"] < 1:
                    Globals.bridge_config["groups"][grp]["action"]["bri"] = 1
                del state["bri_inc"]
                state.update({"bri": Globals.bridge_config["groups"][grp]["action"]["bri"]})
            elif "ct_inc" in state:
                Globals.bridge_config["groups"][grp]["action"]["ct"] += int(state["ct_inc"])
                if Globals.bridge_config["groups"][grp]["action"]["ct"] > 500:
                    Globals.bridge_config["groups"][grp]["action"]["ct"] = 500
                elif Globals.bridge_config["groups"][grp]["action"]["ct"] < 153:
                    Globals.bridge_config["groups"][grp]["action"]["ct"] = 153
                del state["ct_inc"]
                state.update({"ct": Globals.bridge_config["groups"][grp]["action"]["ct"]})
            elif "hue_inc" in state:
                Globals.bridge_config["groups"][grp]["action"]["hue"] += int(state["hue_inc"])
                if Globals.bridge_config["groups"][grp]["action"]["hue"] > 65535:
                    Globals.bridge_config["groups"][grp]["action"]["hue"] -= 65535
                elif Globals.bridge_config["groups"][grp]["action"]["hue"] < 0:
                    Globals.bridge_config["groups"][grp]["action"]["hue"] += 65535
                del state["hue_inc"]
                state.update({"hue": Globals.bridge_config["groups"][grp]["action"]["hue"]})
            for light in Globals.bridge_config["groups"][grp]["lights"]:
                lightsData[light] = state
    else:
        lightsData = scene

    # Make sure any lights haven't been deleted
    lightsData = {k: v for k, v in lightsData.items() if k in Globals.bridge_config["lights_address"]}

    deviceIp = {}
    if group != "0": #only set light state if light is part of group
        lightdel=[]
        for light in lightsData.keys():
            if light not in Globals.bridge_config["groups"][group]["lights"]:
                lightdel.append(light)
        for light in lightdel:
            del lightsData[light]

    for light in lightsData.keys():
        if Globals.bridge_config["lights_address"][light]["ip"] not in deviceIp:
            deviceIp[Globals.bridge_config["lights_address"][light]["ip"]] = {}
        deviceIp[Globals.bridge_config["lights_address"][light]["ip"]][light] = lightsData[light]
    for ip in deviceIp:
        Thread(target=manageDeviceLights, args=[deviceIp[ip]]).start()
    ### update light details
    for light in lightsData.keys():
        if "xy" in lightsData[light]:
            Globals.bridge_config["lights"][light]["state"]["colormode"] = "xy"
        elif "ct" in lightsData[light]:
            Globals.bridge_config["lights"][light]["state"]["colormode"] = "ct"
        elif "hue" in lightsData[light]:
            Globals.bridge_config["lights"][light]["state"]["colormode"] = "hs"
        # if "transitiontime" in lightsData[light]:
        #     del lightsData[light]["transitiontime"]
        Globals.bridge_config["lights"][light]["state"].update(lightsData[light])
    updateGroupStats(list(lightsData.keys())[0], Globals.bridge_config["lights"], Globals.bridge_config["groups"])


def groupZero(state):
    lightsData = {}
    for light in Globals.bridge_config["lights"].keys():
        lightsData[light] = state
    Thread(target=splitLightsToDevices, args=["0", {}, lightsData]).start()
    for group in Globals.bridge_config["groups"].keys():
        Globals.bridge_config["groups"][group]["action"].update(state)
        if "on" in state:
            Globals.bridge_config["groups"][group]["state"]["any_on"] = state["on"]
            Globals.bridge_config["groups"][group]["state"]["all_on"] = state["on"]


def daylightSensor():
    if Globals.bridge_config["sensors"]["1"]["modelid"] != "PHDL00" or not Globals.bridge_config["sensors"]["1"]["config"]["configured"]:
        return

    import pytz
    from astral.sun import sun
    from astral import LocationInfo
    localzone = LocationInfo('localzone', Globals.bridge_config["config"]["timezone"].split("/")[1], Globals.bridge_config["config"]["timezone"], float(Globals.bridge_config["sensors"]["1"]["config"]["lat"][:-1]), float(Globals.bridge_config["sensors"]["1"]["config"]["long"][:-1]))
    s = sun(localzone.observer, date=datetime.now())
    deltaSunset = s['sunset'].replace(tzinfo=None) - datetime.now()
    deltaSunrise = s['sunrise'].replace(tzinfo=None) - datetime.now()
    deltaSunsetOffset = deltaSunset.total_seconds() + Globals.bridge_config["sensors"]["1"]["config"]["sunsetoffset"] * 60
    deltaSunriseOffset = deltaSunrise.total_seconds() + Globals.bridge_config["sensors"]["1"]["config"]["sunriseoffset"] * 60
    logging.info("deltaSunsetOffset: " + str(deltaSunsetOffset))
    logging.info("deltaSunriseOffset: " + str(deltaSunriseOffset))
    current_time =  datetime.now()
    if deltaSunriseOffset < 0 and deltaSunsetOffset > 0:
        Globals.bridge_config["sensors"]["1"]["state"] = {"daylight":True,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        logging.info("set daylight sensor to true")
    else:
        Globals.bridge_config["sensors"]["1"]["state"] = {"daylight":False,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        logging.info("set daylight sensor to false")
    if deltaSunsetOffset > 0 and deltaSunsetOffset < 3600:
        logging.info("will start the sleep for sunset")
        sleep(deltaSunsetOffset)
        logging.info("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
        Globals.bridge_config["sensors"]["1"]["state"] = {"daylight":False,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        Globals.dxState["sensors"]["1"]["state"]["daylight"] = current_time
        rulesProcessor(["sensors","1"], current_time)
    if deltaSunriseOffset > 0 and deltaSunriseOffset < 3600:
        logging.info("will start the sleep for sunrise")
        sleep(deltaSunriseOffset)
        logging.info("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
        Globals.bridge_config["sensors"]["1"]["state"] = {"daylight":True,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        Globals.dxState["sensors"]["1"]["state"]["daylight"] = current_time
        rulesProcessor(["sensors","1"], current_time)


if __name__ == "__main__":
    initialize()
    updateConfig()
    saveConfig()
    Thread(target=resourceRecycle).start()
    if Globals.bridge_config["deconz"]["enabled"]:
        deconz.scanDeconz()
    if "emulator" in Globals.bridge_config and "mqtt" in Globals.bridge_config["emulator"] and Globals.bridge_config["emulator"]["mqtt"]["enabled"]:
        mqtt.mqttServer(Globals.bridge_config["emulator"]["mqtt"], Globals.bridge_config["lights"], Globals.bridge_config["lights_address"], Globals.bridge_config["sensors"])
    try:
        if update_lights_on_startup:
            Thread(target=updateAllLights).start()
        Thread(target=ssdpSearch, args=[HOST_IP, Globals.HOST_HTTP_PORT, Globals.mac]).start()
        Thread(target=ssdpBroadcast, args=[HOST_IP, Globals.HOST_HTTPS_PORT, Globals.mac]).start()
        Thread(target=schedulerProcessor).start()
        Thread(target=syncWithLights, args=[Globals.bridge_config["lights"], Globals.bridge_config["lights_address"], Globals.bridge_config["config"]["whitelist"], Globals.bridge_config["groups"], off_if_unreachable]).start()
        Thread(target=entertainmentService, args=[Globals.bridge_config["lights"], Globals.bridge_config["lights_address"], Globals.bridge_config["groups"], HOST_IP]).start()
        Thread(target=WebServer.runHTTP, args=[]).start()
        if not args.no_serve_https:
            Thread(target=WebServer.runHTTPS, args=[]).start()
        Thread(target=daylightSensor).start()
        Thread(target=remoteApi, args=[Globals.BIND_IP, Globals.bridge_config["config"]]).start()
        if disableOnlineDiscover == False:
            Thread(target=remoteDiscover, args=[Globals.bridge_config["config"]]).start()

        while True:
            sleep(10)
    except Exception:
        logging.exception("server stopped ")
    finally:
        run_service = False
        saveConfig()
        logging.info('config saved')
