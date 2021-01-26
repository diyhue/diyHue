#!/usr/bin/python3
import argparse
import base64
import copy
import json
import logging
import os
import random
import socket
import ssl
import sys
import requests
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from subprocess import Popen, check_output, call
from threading import Thread
from time import sleep, strftime
from urllib.parse import parse_qs, urlparse
from functions import light_types, nextFreeId
from functions.colors import convert_rgb_xy, convert_xy, hsv_to_rgb
from functions.html import (description, webform_hue, webform_linkbutton,
                            webform_milight, webformDeconz, webformTradfri, lightsHttp)
from functions.ssdp import ssdpBroadcast, ssdpSearch
from functions.network import getIpAddress
from functions.docker import dockerSetup
from functions.entertainment import entertainmentService
from functions.request import sendRequest
from functions.lightRequest import sendLightRequest, syncWithLights
from functions.updateGroup import updateGroupStats
from protocols import protocols, yeelight, tasmota, shelly, homeassistant_ws, native_single, native_multi, esphome, mqtt, hyperion, wled
from functions.remoteApi import remoteApi
from functions.remoteDiscover import remoteDiscover

update_lights_on_startup = False # if set to true all lights will be updated with last know state on startup.
off_if_unreachable = False # If set to true all lights that unreachable are marked as off.
protocols = [yeelight, tasmota, shelly, homeassistant_ws, native_single, native_multi, esphome, hyperion, wled]

ap = argparse.ArgumentParser()

# Arguements can also be passed as Environment Variables.
ap.add_argument("--debug", action='store_true', help="Enables debug output")
ap.add_argument("--bind-ip", help="The IP address to listen on", type=str)
ap.add_argument("--docker", action='store_true', help="Enables setup for use in docker container")
ap.add_argument("--ip", help="The IP address of the host system (Docker)", type=str)
ap.add_argument("--config-path", help="specify config.json file location", type=str)
ap.add_argument("--http-port", help="The port to listen on for HTTP (Docker)", type=int)
ap.add_argument("--mac", help="The MAC address of the host system (Docker)", type=str)
ap.add_argument("--no-serve-https", action='store_true', help="Don't listen on port 443 with SSL")
ap.add_argument("--ip-range", help="Set IP range for light discovery. Format: <START_IP>,<STOP_IP>", type=str)
ap.add_argument("--scan-on-host-ip", action='store_true', help="Scan the local IP address when discovering new lights")
ap.add_argument("--deconz", help="Provide the IP address of your Deconz host. 127.0.0.1 by default.", type=str)
ap.add_argument("--no-link-button", action='store_true', help="DANGEROUS! Don't require the link button to be pressed to pair the Hue app, just allow any app to connect")
ap.add_argument("--disable-online-discover", help="Disable Online and Remote API functions")

args = ap.parse_args()

cwd = os.path.split(os.path.abspath(__file__))[0]

if args.debug or (os.getenv('DEBUG') and (os.getenv('DEBUG') == "true" or os.getenv('DEBUG') == "True")):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)

if args.bind_ip:
    BIND_IP = args.bind_ip
elif os.getenv('BIND_IP'):
    BIND_IP = os.getenv('BIND_IP')
else:
    BIND_IP = ''

if args.ip:
    HOST_IP = args.ip
elif os.getenv('IP'):
    HOST_IP = os.getenv('IP')
elif BIND_IP:
    HOST_IP = BIND_IP
else:
    HOST_IP = getIpAddress()

if args.http_port:
    HOST_HTTP_PORT = args.http_port
elif os.getenv('HTTP_PORT'):
    HOST_HTTP_PORT = int(os.getenv('HTTP_PORT'))
else:
    HOST_HTTP_PORT = 80
HOST_HTTPS_PORT = 443 # Hardcoded for now


if args.config_path:
    CONFIG_PATH = args.config_path
elif os.getenv('CONFIG_PATH'):
    CONFIG_PATH = os.getenv('CONFIG_PATH')
elif args.docker or (os.getenv('DOCKER') and os.getenv('DOCKER') == "true"):
    CONFIG_PATH = cwd + "/export"
else:
    CONFIG_PATH = cwd

logging.info("Using Host %s:%s" % (HOST_IP, HOST_HTTP_PORT))

if args.mac:
    dockerMAC = args.mac
    mac = str(args.mac).replace(":","")
    print("Host MAC given as " + mac)
elif os.getenv('MAC'):
    dockerMAC = os.getenv('MAC')
    mac = str(dockerMAC).replace(":","")
    print("Host MAC given as " + mac)
else:
    dockerMAC = check_output("cat /sys/class/net/$(ip -o addr | grep %s | awk '{print $2}')/address" % HOST_IP, shell=True).decode('utf-8')[:-1]
    mac = check_output("cat /sys/class/net/$(ip -o addr | grep %s | awk '{print $2}')/address" % HOST_IP, shell=True).decode('utf-8').replace(":","")[:-1]
logging.info(mac)

if args.docker or (os.getenv('DOCKER') and os.getenv('DOCKER') == "true"):
    print("Docker Setup Initiated")
    docker = True
    dockerSetup(mac, CONFIG_PATH)
    print("Docker Setup Complete")
elif os.getenv('MAC'):
    dockerMAC = os.getenv('MAC')
    mac = str(dockerMAC).replace(":","")
    print("Host MAC given as " + mac)
else:
    docker = False

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

if args.disable_online_discover or ((os.getenv('disableonlinediscover') and (os.getenv('disableonlinediscover') == "true" or os.getenv('disableonlinediscover') == "True"))):
    disableOnlineDiscover = True
    logging.info("Online Discovery/Remote API Disabled!")
else:
    disableOnlineDiscover = False
    logging.info("Online Discovery/Remote API Enabled!")



def pretty_json(data):
    return json.dumps(data, sort_keys=True,                  indent=4, separators=(',', ': '))

run_service = True

def initialize():
    global bridge_config, new_lights, dxState
    new_lights = {}
    dxState = {"sensors": {}, "lights": {}, "groups": {}}

    try:
        path = CONFIG_PATH + '/config.json'
        if os.path.exists(path):
            bridge_config = load_config(path)
            logging.info("Config loaded")
        else:
            logging.info("Config not found, creating new config from default settings")
            bridge_config = load_config(CONFIG_PATH + '/default-config.json')
            saveConfig()
    except Exception:
        logging.exception("CRITICAL! Config file was not loaded")
        sys.exit(1)

    ip_pieces = HOST_IP.split(".")
    bridge_config["config"]["ipaddress"] = HOST_IP
    bridge_config["config"]["gateway"] = ip_pieces[0] + "." +  ip_pieces[1] + "." + ip_pieces[2] + ".1"
    bridge_config["config"]["mac"] = mac[0] + mac[1] + ":" + mac[2] + mac[3] + ":" + mac[4] + mac[5] + ":" + mac[6] + mac[7] + ":" + mac[8] + mac[9] + ":" + mac[10] + mac[11]
    bridge_config["config"]["bridgeid"] = (mac[:6] + 'FFFE' + mac[6:]).upper()
    generateDxState()
    sanitizeBridgeScenes()
    ## generte security key for Hue Essentials remote access
    if "Hue Essentials key" not in bridge_config["config"]:
        bridge_config["config"]["Hue Essentials key"] = str(uuid.uuid1()).replace('-', '')

def sanitizeBridgeScenes():
    for scene in list(bridge_config["scenes"]):
        if "type" in bridge_config["scenes"][scene] and bridge_config["scenes"][scene]["type"] == "GroupScene": # scene has "type" key and "type" is "GroupScene"
            if bridge_config["scenes"][scene]["group"] not in bridge_config["groups"]: # the group don't exist
                del bridge_config["scenes"][scene] # delete the group
                continue # avoid KeyError on next if statement
            else:
                for lightstate in list(bridge_config["scenes"][scene]["lightstates"]):
                    if lightstate not in bridge_config["groups"][bridge_config["scenes"][scene]["group"]]["lights"]: # if the light is no longer member in the group:
                        del bridge_config["scenes"][scene]["lightstates"][lightstate] # delete the lighstate of the missing light
        else: # must be a lightscene
            for lightstate in list(bridge_config["scenes"][scene]["lightstates"]):
                if lightstate not in bridge_config["lights"]: # light is not present anymore on the bridge
                    del (bridge_config["scenes"][scene]["lightstates"][lightstate]) # delete invalid lightstate

        if "lightstates" in bridge_config["scenes"][scene] and len(bridge_config["scenes"][scene]["lightstates"]) == 0: # empty scenes are useless
            del bridge_config["scenes"][scene]

def getLightsVersions():
    lights = {}
    githubCatalog = json.loads(requests.get('https://raw.githubusercontent.com/diyhue/Lights/master/catalog.json').text)
    for light in bridge_config["lights_address"].keys():
        if bridge_config["lights_address"][light]["protocol"] in ["native_single", "native_multi"]:
            if "light_nr" not in bridge_config["lights_address"][light] or bridge_config["lights_address"][light]["light_nr"] == 1:
                currentData = json.loads(requests.get('http://' + bridge_config["lights_address"][light]["ip"] + '/detect', timeout=3).text)
                lights[light] = {"name": currentData["name"], "currentVersion": currentData["version"], "lastVersion": githubCatalog[currentData["type"]]["version"], "firmware": githubCatalog[currentData["type"]]["filename"]}
    return lights

def updateLight(light, filename):
    firmware = requests.get('https://github.com/diyhue/Lights/raw/master/Arduino/bin/' + filename, allow_redirects=True)
    open('/tmp/' + filename, 'wb').write(firmware.content)
    file = {'update': open('/tmp/' + filename,'rb')}
    update = requests.post('http://' + bridge_config["lights_address"][light]["ip"] + '/update', files=file)

# Make various updates to the config JSON structure to maintain backwards compatibility with old configs
def updateConfig():

    #### bridge emulator config

    if int(bridge_config["config"]["swversion"]) < 1941132080:
        bridge_config["config"]["swversion"] = "1941132080"
        bridge_config["config"]["apiversion"] = "1.39.0"

    ### end bridge config

    if "emulator" not in bridge_config:
        bridge_config["emulator"] = {"lights": {}, "sensors": {}}


    if "alarm" not in bridge_config["emulator"]:
        bridge_config["emulator"]["alarm"] = {"on": False, "email": "", "lasttriggered": 100000}
    if "alarm_config" in bridge_config:
        del bridge_config["alarm_config"]

    if "mqtt" not in bridge_config["emulator"]:
        bridge_config["emulator"]["mqtt"] = { "discoveryPrefix": "homeassistant", "enabled": False, "mqttPassword": "", "mqttPort": 1883, "mqttServer": "mqtt", "mqttUser": ""}

    if "homeassistant" not in bridge_config["emulator"]:
        bridge_config["emulator"]["homeassistant"] = { "enabled": False, "homeAssistantIp": "127.0.0.1", "homeAssistantPort": 8123, "homeAssistantToken": "", "homeAssistantIncludeByDefault": False}

    if "yeelight" not in bridge_config["emulator"]:
        bridge_config["emulator"]["yeelight"] = { "enabled": True}
    if "tasmota" not in bridge_config["emulator"]:
        bridge_config["emulator"]["tasmota"] = { "enabled": True}
    if "shelly" not in bridge_config["emulator"]:
        bridge_config["emulator"]["shelly"] = { "enabled": True}
    if "esphome" not in bridge_config["emulator"]:
        bridge_config["emulator"]["esphome"] = { "enabled": True}
    if "hyperion" not in bridge_config["emulator"]:
        bridge_config["emulator"]["hyperion"] = { "enabled": True}
    if "wled" not in bridge_config["emulator"]:
        bridge_config["emulator"]["wled"] = { "enabled": True}
    if "network_scan" not in bridge_config["emulator"]:
        bridge_config["emulator"]["network_scan"] = { "enabled": True}

    if "Remote API enabled" not in bridge_config["config"]:
        bridge_config["config"]["Remote API enabled"] = False

    # Update deCONZ sensors
    for sensor_id, sensor in bridge_config["deconz"]["sensors"].items():
        if "modelid" not in sensor:
            sensor["modelid"] = bridge_config["sensors"][sensor["bridgeid"]]["modelid"]
        if sensor["modelid"] in ["TRADFRI motion sensor", "lumi.sensor_motion"]:
            if "lightsensor" not in sensor:
                sensor["lightsensor"] = "astral"

    # Update scenes
    for scene_id, scene in bridge_config["scenes"].items():
        if "type" not in scene:
            scene["type"] = "LightGroup"

    # Update sensors
    for sensor_id, sensor in bridge_config["sensors"].items():
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
    for light_id, light_address in bridge_config["lights_address"].items():
        light = bridge_config["lights"][light_id]

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
    for group_id, group in bridge_config["groups"].items():
        if "type" in group and group["type"] == "Entertainment":
            if "stream" not in group:
                group["stream"] = {}
            group["stream"].update({"active": False, "owner": None})

        group["sensors"] = []

    #fix timezones bug
    if "values" not in bridge_config["capabilities"]["timezones"]:
        timezones = bridge_config["capabilities"]["timezones"]
        bridge_config["capabilities"]["timezones"] = {"values": timezones}

def addTradfriDimmer(sensor_id, group_id):
    rules = [{ "actions":[{"address": "/groups/" + group_id + "/action", "body":{ "on":True, "bri":1 }, "method": "PUT" }], "conditions":[{ "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}, { "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2002" }, { "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "false" }], "name": "Remote " + sensor_id + " turn on" },{"actions":[{"address":"/groups/" + group_id + "/action", "body":{ "on": False}, "method":"PUT"}], "conditions":[{ "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }, { "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4002" }, { "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "true" }, { "address": "/groups/" + group_id + "/action/bri", "operator": "eq", "value": "1"}], "name":"Dimmer Switch " + sensor_id + " off"}, { "actions":[{ "address": "/groups/" + group_id + "/action", "body":{ "on":False }, "method": "PUT" }], "conditions":[{ "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }, { "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3002" }, { "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "true" }, { "address": "/groups/" + group_id + "/action/bri", "operator": "eq", "value": "1"}], "name": "Remote " + sensor_id + " turn off" }, { "actions": [{"address": "/groups/" + group_id + "/action", "body":{"bri_inc": 32, "transitiontime": 9}, "method": "PUT" }], "conditions": [{ "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "true" },{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2002" }, {"address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}], "name": "Dimmer Switch " + sensor_id + " rotate right"}, { "actions": [{"address": "/groups/" + group_id + "/action", "body":{"bri_inc": 56, "transitiontime": 9}, "method": "PUT" }], "conditions": [{ "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "true" },{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "1002" }, {"address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}], "name": "Dimmer Switch " + sensor_id + " rotate fast right"}, {"actions": [{"address": "/groups/" + group_id + "/action", "body": {"bri_inc": -32, "transitiontime": 9}, "method": "PUT"}], "conditions": [{ "address": "/groups/" + group_id + "/action/bri", "operator": "gt", "value": "1"},{"address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3002"}, {"address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}], "name": "Dimmer Switch " + sensor_id + " rotate left"}, {"actions": [{"address": "/groups/" + group_id + "/action", "body": {"bri_inc": -56, "transitiontime": 9}, "method": "PUT"}], "conditions": [{ "address": "/groups/" + group_id + "/action/bri", "operator": "gt", "value": "1"},{"address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4002"}, {"address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}], "name": "Dimmer Switch " + sensor_id + " rotate left"}]
    resourcelinkId = nextFreeId(bridge_config, "resourcelinks")
    bridge_config["resourcelinks"][resourcelinkId] = {"classid": 15555,"description": "Rules for sensor " + sensor_id, "links": ["/sensors/" + sensor_id], "name": "Emulator rules " + sensor_id,"owner": list(bridge_config["config"]["whitelist"])[0]}
    for rule in rules:
        ruleId = nextFreeId(bridge_config, "rules")
        bridge_config["rules"][ruleId] = rule
        bridge_config["rules"][ruleId].update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "lasttriggered": None, "owner": list(bridge_config["config"]["whitelist"])[0], "recycle": True, "status": "enabled", "timestriggered": 0})
        bridge_config["resourcelinks"][resourcelinkId]["links"].append("/rules/" + ruleId)

def addTradfriCtRemote(sensor_id, group_id):
    rules = [{"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": True},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "1002"},{"address": "/groups/" + group_id + "/state/any_on","operator": "eq","value": "false"}],"name": "Remote " + sensor_id + " button on"}, {"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": False},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "1002"},{"address": "/groups/" + group_id + "/state/any_on","operator": "eq","value": "true"}],"name": "Remote " + sensor_id + " button off"},{ "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": 30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " up-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": 56, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " up-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": -30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " dn-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": -56, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " dn-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "ct_inc": 50, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ctl-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "ct_inc": 100, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ctl-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "ct_inc": -50, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "5002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ct-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "ct_inc": -100, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "5001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ct-long" }]
    resourcelinkId = nextFreeId(bridge_config, "resourcelinks")
    bridge_config["resourcelinks"][resourcelinkId] = {"classid": 15555,"description": "Rules for sensor " + sensor_id, "links": ["/sensors/" + sensor_id], "name": "Emulator rules " + sensor_id,"owner": list(bridge_config["config"]["whitelist"])[0]}
    for rule in rules:
        ruleId = nextFreeId(bridge_config, "rules")
        bridge_config["rules"][ruleId] = rule
        bridge_config["rules"][ruleId].update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "lasttriggered": None, "owner": list(bridge_config["config"]["whitelist"])[0], "recycle": True, "status": "enabled", "timestriggered": 0})
        bridge_config["resourcelinks"][resourcelinkId]["links"].append("/rules/" + ruleId)

def addTradfriOnOffSwitch(sensor_id, group_id):
    rules = [{"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": True},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "1002"}],"name": "Remote " + sensor_id + " button on"}, {"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": False},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "2002"}],"name": "Remote " + sensor_id + " button off"},{ "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": 30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "1001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " up-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": -30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " dn-press" }]
    resourcelinkId = nextFreeId(bridge_config, "resourcelinks")
    bridge_config["resourcelinks"][resourcelinkId] = {"classid": 15555,"description": "Rules for sensor " + sensor_id, "links": ["/sensors/" + sensor_id], "name": "Emulator rules " + sensor_id,"owner": list(bridge_config["config"]["whitelist"])[0]}
    for rule in rules:
        ruleId = nextFreeId(bridge_config, "rules")
        bridge_config["rules"][ruleId] = rule
        bridge_config["rules"][ruleId].update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "lasttriggered": None, "owner": list(bridge_config["config"]["whitelist"])[0], "recycle": True, "status": "enabled", "timestriggered": 0})
        bridge_config["resourcelinks"][resourcelinkId]["links"].append("/rules/" + ruleId)

def addTradfriSceneRemote(sensor_id, group_id):
    rules = [{"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": True},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "1002"},{"address": "/groups/" + group_id + "/state/any_on","operator": "eq","value": "false"}],"name": "Remote " + sensor_id + " button on"}, {"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": False},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "1002"},{"address": "/groups/" + group_id + "/state/any_on","operator": "eq","value": "true"}],"name": "Remote " + sensor_id + " button off"},{ "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": 30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " up-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": 56, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " up-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": -30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " dn-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": -56, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " dn-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "scene_inc": -1 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ctl-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "scene_inc": -1 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ctl-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "scene_inc": 1 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "5002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ct-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "scene_inc": 1 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "5001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ct-long" }]
    resourcelinkId = nextFreeId(bridge_config, "resourcelinks")
    bridge_config["resourcelinks"][resourcelinkId] = {"classid": 15555,"description": "Rules for sensor " + sensor_id, "links": ["/sensors/" + sensor_id], "name": "Emulator rules " + sensor_id,"owner": list(bridge_config["config"]["whitelist"])[0]}
    for rule in rules:
        ruleId = nextFreeId(bridge_config, "rules")
        bridge_config["rules"][ruleId] = rule
        bridge_config["rules"][ruleId].update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "lasttriggered": None, "owner": list(bridge_config["config"]["whitelist"])[0], "recycle": True, "status": "enabled", "timestriggered": 0})
        bridge_config["resourcelinks"][resourcelinkId]["links"].append("/rules/" + ruleId)

def addHueMotionSensor(uniqueid, name="Hue motion sensor"):
    new_sensor_id = nextFreeId(bridge_config, "sensors")
    if uniqueid == "":
        uniqueid = "00:17:88:01:02:"
        if len(new_sensor_id) == 1:
            uniqueid += "0" + new_sensor_id
        else:
            uniqueid += new_sensor_id
    bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue temperature sensor 1", "uniqueid": uniqueid + ":d0:5b-02-0402", "type": "ZLLTemperature", "swversion": "6.1.0.18912", "state": {"temperature": None, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False, "battery": 100, "reachable": True, "alert":"none", "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
    motion_sensor = nextFreeId(bridge_config, "sensors")
    bridge_config["sensors"][motion_sensor] = {"name": name, "uniqueid": uniqueid + ":d0:5b-02-0406", "type": "ZLLPresence", "swversion": "6.1.0.18912", "state": {"lastupdated": "none", "presence": None}, "manufacturername": "Philips", "config": {"on": False,"battery": 100,"reachable": True, "alert": "lselect", "ledindication": False, "usertest": False, "sensitivity": 2, "sensitivitymax": 2,"pending": []}, "modelid": "SML001"}
    bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue ambient light sensor", "uniqueid": uniqueid + ":d0:5b-02-0400", "type": "ZLLLightLevel", "swversion": "6.1.0.18912", "state": {"dark": True, "daylight": False, "lightlevel": 6000, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False,"battery": 100, "reachable": True, "alert": "none", "tholddark": 21597, "tholdoffset": 7000, "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
    return(motion_sensor)

def addHueSwitch(uniqueid, sensorsType):
    new_sensor_id = nextFreeId(bridge_config, "sensors")
    if uniqueid == "":
        uniqueid = "00:17:88:01:02:"
        if len(new_sensor_id) == 1:
            uniqueid += "0" + new_sensor_id + ":4d:c6-02-fc00"
        else:
            uniqueid += new_sensor_id + ":4d:c6-02-fc00"
    bridge_config["sensors"][new_sensor_id] = {"state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "name": "Dimmer Switch" if sensorsType == "ZLLSwitch" else "Tap Switch", "type": sensorsType, "modelid": "RWL021" if sensorsType == "ZLLSwitch" else "ZGPSWITCH", "manufacturername": "Philips", "swversion": "5.45.1.17846" if sensorsType == "ZLLSwitch" else "", "uniqueid": uniqueid}
    return(new_sensor_id)

#load config files
def load_config(path):
    with open(path, 'r', encoding="utf-8") as fp:
        return json.load(fp)

def resourceRecycle():
    sleep(5) #give time to application to delete all resources, then start the cleanup
    resourcelinks = {"groups": [],"lights": [], "sensors": [], "rules": [], "scenes": [], "schedules": [], "resourcelinks": []}
    for resourcelink in bridge_config["resourcelinks"].keys():
        for link in bridge_config["resourcelinks"][resourcelink]["links"]:
            link_parts = link.split("/")
            resourcelinks[link_parts[1]].append(link_parts[2])

    for resource in resourcelinks.keys():
        for key in list(bridge_config[resource]):
            if "recycle" in bridge_config[resource][key] and bridge_config[resource][key]["recycle"] and key not in resourcelinks[resource]:
                logging.info("delete " + resource + " / " + key)
                del bridge_config[resource][key]

def saveConfig(filename='config.json'):
    with open(CONFIG_PATH + '/' + filename, 'w', encoding="utf-8") as fp:
        json.dump(bridge_config, fp, sort_keys=True, indent=4, separators=(',', ': '))

def generateDxState():
    for sensor in bridge_config["sensors"]:
        if sensor not in dxState["sensors"] and "state" in bridge_config["sensors"][sensor]:
            dxState["sensors"][sensor] = {"state": {}}
            for key in bridge_config["sensors"][sensor]["state"].keys():
                if key in ["lastupdated", "presence", "flag", "dark", "daylight", "status"]:
                    dxState["sensors"][sensor]["state"].update({key: datetime.now()})
    for group in bridge_config["groups"]:
        if group not in dxState["groups"] and "state" in bridge_config["groups"][group]:
            dxState["groups"][group] = {"state": {}}
            for key in bridge_config["groups"][group]["state"].keys():
                dxState["groups"][group]["state"].update({key: datetime.now()})
    for light in bridge_config["lights"]:
        if light not in dxState["lights"] and "state" in bridge_config["lights"][light]:
            dxState["lights"][light] = {"state": {}}
            for key in bridge_config["lights"][light]["state"].keys():
                if key in ["on", "bri", "colormode", "reachable"]:
                    dxState["lights"][light]["state"].update({key: datetime.now()})

def schedulerProcessor():
    while run_service:
        for schedule in bridge_config["schedules"].keys():
            try:
                delay = 0
                if bridge_config["schedules"][schedule]["status"] == "enabled":
                    if bridge_config["schedules"][schedule]["localtime"][-9:-8] == "A":
                        delay = random.randrange(0, int(bridge_config["schedules"][schedule]["localtime"][-8:-6]) * 3600 + int(bridge_config["schedules"][schedule]["localtime"][-5:-3]) * 60 + int(bridge_config["schedules"][schedule]["localtime"][-2:]))
                        schedule_time = bridge_config["schedules"][schedule]["localtime"][:-9]
                    else:
                        schedule_time = bridge_config["schedules"][schedule]["localtime"]
                    if schedule_time.startswith("W"):
                        pieces = schedule_time.split('/T')
                        if int(pieces[0][1:]) & (1 << 6 - datetime.today().weekday()):
                            if pieces[1] == datetime.now().strftime("%H:%M:%S"):
                                logging.info("execute schedule: " + schedule + " withe delay " + str(delay))
                                sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                    elif schedule_time.startswith("PT"):
                        timmer = schedule_time[2:]
                        (h, m, s) = timmer.split(':')
                        d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                        if bridge_config["schedules"][schedule]["starttime"] == (datetime.utcnow() - d).replace(microsecond=0).isoformat():
                            logging.info("execute timmer: " + schedule + " withe delay " + str(delay))
                            sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                            bridge_config["schedules"][schedule]["status"] = "disabled"
                    elif schedule_time.startswith("R/PT"):
                        timmer = schedule_time[4:]
                        (h, m, s) = timmer.split(':')
                        d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                        if bridge_config["schedules"][schedule]["starttime"] == (datetime.utcnow() - d).replace(microsecond=0).isoformat():
                            logging.info("execute timmer: " + schedule + " withe delay " + str(delay))
                            bridge_config["schedules"][schedule]["starttime"] = datetime.utcnow().replace(microsecond=0).isoformat()
                            sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                    else:
                        if schedule_time == datetime.now().strftime("%Y-%m-%dT%H:%M:%S"):
                            logging.info("execute schedule: " + schedule + " withe delay " + str(delay))
                            sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                            if bridge_config["schedules"][schedule]["autodelete"]:
                                del bridge_config["schedules"][schedule]
                            else:
                                bridge_config["schedules"][schedule]["status"] = "disabled"
            except Exception as e:
                logging.info("Exception while processing the schedule " + schedule + " | " + str(e))

        if (datetime.now().strftime("%M:%S") == "00:10"): #auto save configuration every hour
            saveConfig()
            Thread(target=daylightSensor).start()
            if (datetime.now().strftime("%H") == "23" and datetime.now().strftime("%A") == "Sunday"): #backup config every Sunday at 23:00:10
                saveConfig("config-backup-" + datetime.now().strftime("%Y-%m-%d") + ".json")
        sleep(1)

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


def checkRuleConditions(rule, device, current_time, ignore_ddx=False):
    ddx = 0
    device_found = False
    ddx_sensor = []
    for condition in bridge_config["rules"][rule]["conditions"]:
        try:
            url_pieces = condition["address"].split('/')
            if url_pieces[1] == device[0] and url_pieces[2] == device[1]:
                device_found = True
            if condition["operator"] == "eq":
                if condition["value"] == "true":
                    if not bridge_config[url_pieces[1]][url_pieces[2]][url_pieces[3]][url_pieces[4]]:
                        return [False, 0]
                elif condition["value"] == "false":
                    if bridge_config[url_pieces[1]][url_pieces[2]][url_pieces[3]][url_pieces[4]]:
                        return [False, 0]
                else:
                    if not int(bridge_config[url_pieces[1]][url_pieces[2]][url_pieces[3]][url_pieces[4]]) == int(condition["value"]):
                        return [False, 0]
            elif condition["operator"] == "gt":
                if not int(bridge_config[url_pieces[1]][url_pieces[2]][url_pieces[3]][url_pieces[4]]) > int(condition["value"]):
                    return [False, 0]
            elif condition["operator"] == "lt":
                if not int(bridge_config[url_pieces[1]][url_pieces[2]][url_pieces[3]][url_pieces[4]]) < int(condition["value"]):
                    return [False, 0]
            elif condition["operator"] == "dx":
                if not dxState[url_pieces[1]][url_pieces[2]][url_pieces[3]][url_pieces[4]] == current_time:
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
                if not dxState[url_pieces[1]][url_pieces[2]][url_pieces[3]][url_pieces[4]] == current_time:
                        return [False, 0]
                else:
                    ddx = int(condition["value"][2:4]) * 3600 + int(condition["value"][5:7]) * 60 + int(condition["value"][-2:])
                    ddx_sensor = url_pieces
        except Exception as e:
            logging.info("rule " + rule + " failed, reason:" + str(e))


    if device_found:
        return [True, ddx, ddx_sensor]
    else:
        return [False]

def ddxRecheck(rule, device, current_time, ddx_delay, ddx_sensor):
    for x in range(ddx_delay):
        if current_time != dxState[ddx_sensor[1]][ddx_sensor[2]][ddx_sensor[3]][ddx_sensor[4]]:
            logging.info("ddx rule " + rule + " canceled after " + str(x) + " seconds")
            return # rule not valid anymore because sensor state changed while waiting for ddx delay
        sleep(1)
    current_time = datetime.now()
    rule_state = checkRuleConditions(rule, device, current_time, True)
    if rule_state[0]: #if all conditions are meet again
        logging.info("delayed rule " + rule + " is triggered")
        bridge_config["rules"][rule]["lasttriggered"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
        bridge_config["rules"][rule]["timestriggered"] += 1
        for action in bridge_config["rules"][rule]["actions"]:
            sendRequest("/api/" + bridge_config["rules"][rule]["owner"] + action["address"], action["method"], json.dumps(action["body"]))

def rulesProcessor(device, current_time):
    bridge_config["config"]["localtime"] = current_time.strftime("%Y-%m-%dT%H:%M:%S") #required for operator dx to address /config/localtime
    actionsToExecute = []
    for rule in bridge_config["rules"].keys():
        if bridge_config["rules"][rule]["status"] == "enabled":
            rule_result = checkRuleConditions(rule, device, current_time)
            if rule_result[0]:
                if rule_result[1] == 0: #is not ddx rule
                    logging.info("rule " + rule + " is triggered")
                    bridge_config["rules"][rule]["lasttriggered"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
                    bridge_config["rules"][rule]["timestriggered"] += 1
                    for action in bridge_config["rules"][rule]["actions"]:
                        actionsToExecute.append(action)
                else: #if ddx rule
                    logging.info("ddx rule " + rule + " will be re validated after " + str(rule_result[1]) + " seconds")
                    Thread(target=ddxRecheck, args=[rule, device, current_time, rule_result[1], rule_result[2]]).start()
    for action in actionsToExecute:
        sendRequest("/api/" +    list(bridge_config["config"]["whitelist"])[0] + action["address"], action["method"], json.dumps(action["body"]))


def scanHost(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
    for light_id, light_address in bridge_config["lights_address"].items():
        if (light_address["protocol"] in ["native", "native_single",  "native_multi"]
                and light_address["mac"] == mac_address
                and ('light_nr' not in light_address or
                    light_address['light_nr'] == light_nr)):
            return light_id
    return None

def find_light_in_config_from_uid(bridge_config, unique_id):
    for light in bridge_config["lights"].keys():
        if bridge_config["lights"][light]["uniqueid"] == unique_id:
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
    if bridge_config["emulator"]["yeelight"]["enabled"]:
        Thread(target=yeelight.discover, args=[bridge_config, new_lights]).start()
    if bridge_config["emulator"]["tasmota"]["enabled"]:
        Thread(target=tasmota.discover, args=[bridge_config, new_lights]).start()
    if bridge_config["emulator"]["shelly"]["enabled"]:
        Thread(target=shelly.discover, args=[bridge_config, new_lights]).start()
    if bridge_config["emulator"]["homeassistant"]["enabled"]:
        Thread(target=scanHomeAssistant, args=[bridge_config, new_lights]).start()
    if bridge_config["emulator"]["esphome"]["enabled"]:
        Thread(target=esphome.discover, args=[bridge_config, new_lights]).start()
    if bridge_config["emulator"]["mqtt"]["enabled"]:
        Thread(target=mqtt.discover, args=[bridge_config, new_lights]).start()
    if bridge_config["emulator"]["hyperion"]["enabled"]:
        Thread(target=hyperion.discover, args=[bridge_config, new_lights]).start()
    if bridge_config["emulator"]["wled"]["enabled"]:
        Thread(target=wled.discover, args=[bridge_config, new_lights]).start()
    #return all host that listen on port 80
    if bridge_config["emulator"]["network_scan"]["enabled"]:
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
    scanDeconz()
    scanTradfri()
    saveConfig()


def longPressButton(sensor, buttonevent):
    logging.info("long press detected")
    sleep(1)
    while bridge_config["sensors"][sensor]["state"]["buttonevent"] == buttonevent:
        logging.info("still pressed")
        current_time =  datetime.now()
        dxState["sensors"][sensor]["state"]["lastupdated"] = current_time
        rulesProcessor(["sensors",sensor], current_time)
        sleep(0.5)
    return


def motionDetected(sensor):
    logging.info("monitoring motion sensor " + sensor)
    while bridge_config["sensors"][sensor]["state"]["presence"] == True:
        if datetime.utcnow() - datetime.strptime(bridge_config["sensors"][sensor]["state"]["lastupdated"], "%Y-%m-%dT%H:%M:%S") > timedelta(seconds=30):
            bridge_config["sensors"][sensor]["state"]["presence"] = False
            bridge_config["sensors"][sensor]["state"]["lastupdated"] =  datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            current_time =  datetime.now()
            dxState["sensors"][sensor]["state"]["presence"] = current_time
            rulesProcessor(["sensors",sensor], current_time)
        sleep(1)
    logging.info("set motion sensor " + sensor + " to motion = False")
    return

def scanHomeAssistant(bridge_config, new_lights):
    homeassistant_ws.discover(bridge_config, new_lights)
    # We have to regenerate the DX state as we may have added groups (/rooms/zones)
    generateDxState()

def scanTradfri():
    if "tradfri" in bridge_config:
        tradri_devices = json.loads(check_output("./coap-client-linux -m get -u \"" + bridge_config["tradfri"]["identity"] + "\" -k \"" + bridge_config["tradfri"]["psk"] + "\" \"coaps://" + bridge_config["tradfri"]["ip"] + ":5684/15001\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
        logging.info(pretty_json(tradri_devices))
        lights_found = 0
        for device in tradri_devices:
            device_parameters = json.loads(check_output("./coap-client-linux -m get -u \"" + bridge_config["tradfri"]["identity"] + "\" -k \"" + bridge_config["tradfri"]["psk"] + "\" \"coaps://" + bridge_config["tradfri"]["ip"] + ":5684/15001/" + str(device) +"\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
            if "3311" in device_parameters:
                new_light = True
                for light in bridge_config["lights_address"]:
                    if bridge_config["lights_address"][light]["protocol"] == "ikea_tradfri" and bridge_config["lights_address"][light]["device_id"] == device:
                        new_light = False
                        break
                if new_light:
                    lights_found += 1
                    #register new tradfri lightdevice_id
                    logging.info("register tradfi light " + device_parameters["9001"])
                    new_light_id = nextFreeId(bridge_config, "lights")
                    bridge_config["lights"][new_light_id] = {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}, "type": "Extended color light", "name": device_parameters["9001"], "uniqueid": "1234567" + str(device), "modelid": "LLM010", "swversion": "66009461", "manufacturername": "Philips"}
                    new_lights.update({new_light_id: {"name": device_parameters["9001"]}})
                    bridge_config["lights_address"][new_light_id] = {"device_id": device, "preshared_key": bridge_config["tradfri"]["psk"], "identity": bridge_config["tradfri"]["identity"], "ip": bridge_config["tradfri"]["ip"], "protocol": "ikea_tradfri"}
        return lights_found
    else:
        return 0

def websocketClient():
    from ws4py.client.threadedclient import WebSocketClient
    class EchoClient(WebSocketClient):
        def opened(self):
            self.send("hello")

        def closed(self, code, reason=None):
            logging.info(("deconz websocket disconnected", code, reason))
            del bridge_config["deconz"]["websocketport"]

        def received_message(self, m):
            logging.debug(m)
            message = json.loads(str(m))
            try:
                if message["r"] == "sensors":
                    bridge_sensor_id = bridge_config["deconz"]["sensors"][message["id"]]["bridgeid"]
                    if "state" in message and bridge_config["sensors"][bridge_sensor_id]["config"]["on"]:

                        #change codes for emulated hue Switches
                        if "hueType" in bridge_config["deconz"]["sensors"][message["id"]]:
                            rewriteDict = {"ZGPSwitch": {1002: 34, 3002: 16, 4002: 17, 5002: 18}, "ZLLSwitch" : {1002 : 1000, 2002: 2000, 2001: 2001, 2003: 2002, 3001: 3001, 3002: 3000, 3003: 3002, 4002: 4000, 5002: 4000} }
                            message["state"]["buttonevent"] = rewriteDict[bridge_config["deconz"]["sensors"][message["id"]]["hueType"]][message["state"]["buttonevent"]]
                        #end change codes for emulated hue Switches

                        #convert tradfri motion sensor notification to look like Hue Motion Sensor
                        if message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["modelid"] == "TRADFRI motion sensor":
                            #find the light sensor id
                            light_sensor = "0"
                            for sensor in bridge_config["sensors"].keys():
                                if bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel" and bridge_config["sensors"][sensor]["uniqueid"] == bridge_config["sensors"][bridge_sensor_id]["uniqueid"][:-1] + "0":
                                    light_sensor = sensor
                                    break
                            if bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "none":
                                message["state"].update({"dark": True})
                            elif bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "astral":
                                message["state"]["dark"] = not bridge_config["sensors"]["1"]["state"]["daylight"]


                            if  message["state"]["dark"]:
                                bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                            else:
                                bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 25000
                            bridge_config["sensors"][light_sensor]["state"]["dark"] = message["state"]["dark"]
                            bridge_config["sensors"][light_sensor]["state"]["daylight"] = not message["state"]["dark"]
                            bridge_config["sensors"][light_sensor]["state"]["lastupdated"] = message["state"]["lastupdated"]

                        #Xiaomi motion w/o light level sensor
                        if message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["modelid"] == "lumi.sensor_motion":
                            for sensor in bridge_config["sensors"].keys():
                                if bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel" and bridge_config["sensors"][sensor]["uniqueid"] == bridge_config["sensors"][bridge_sensor_id]["uniqueid"][:-1] + "0":
                                    light_sensor = sensor
                                    break
                            if bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "none":
                                bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                                bridge_config["sensors"][light_sensor]["state"]["dark"] = True
                            elif bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "astral":
                                if bridge_config["sensors"]["1"]["state"]["daylight"]:
                                    bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 25000
                                    bridge_config["sensors"][light_sensor]["state"]["dark"] = False
                                else:
                                    bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                                    bridge_config["sensors"][light_sensor]["state"]["dark"] = True

                        #convert xiaomi motion sensor to hue sensor
                        if message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["modelid"] == "lumi.sensor_motion.aq2" and message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["type"] == "ZHALightLevel":
                            bridge_config["sensors"][bridge_sensor_id]["state"].update(message["state"])
                            return
                        ##############

                        ##convert xiaomi vibration sensor states to hue motion sensor
                        if message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["modelid"] == "lumi.vibration.aq1":
                            #find the light sensor id
                            light_sensor = "0"
                            for sensor in bridge_config["sensors"].keys():
                                if bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel" and bridge_config["sensors"][sensor]["uniqueid"] == bridge_config["sensors"][bridge_sensor_id]["uniqueid"][:-1] + "0":
                                    light_sensor = sensor
                                    break
                            logging.info("Vibration: emulated light sensor id is  " + light_sensor)
                            if bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "none":
                                message["state"].update({"dark": True})
                                logging.info("Vibration: set light sensor to dark because 'lightsensor' = 'none' ")
                            elif bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "astral":
                                message["state"]["dark"] = not bridge_config["sensors"]["1"]["state"]["daylight"]
                                logging.info("Vibration: set light sensor to " + str(not bridge_config["sensors"]["1"]["state"]["daylight"]) + " because 'lightsensor' = 'astral' ")

                            if  message["state"]["dark"]:
                                bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                            else:
                                bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 25000
                            bridge_config["sensors"][light_sensor]["state"]["dark"] = message["state"]["dark"]
                            bridge_config["sensors"][light_sensor]["state"]["daylight"] = not message["state"]["dark"]
                            bridge_config["sensors"][light_sensor]["state"]["lastupdated"] = message["state"]["lastupdated"]
                            message["state"] = {"motion": True, "lastupdated": message["state"]["lastupdated"]} #empty the message state for non Hue motion states (we need to know there was an event only)
                            logging.info("Vibration: set motion = True")
                            Thread(target=motionDetected, args=[bridge_sensor_id]).start()


                        bridge_config["sensors"][bridge_sensor_id]["state"].update(message["state"])
                        current_time = datetime.now()
                        for key in message["state"].keys():
                            dxState["sensors"][bridge_sensor_id]["state"][key] = current_time
                        rulesProcessor(["sensors", bridge_sensor_id], current_time)
                        if "buttonevent" in message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["modelid"] in ["TRADFRI remote control","RWL021","TRADFRI on/off switch"]:
                            if message["state"]["buttonevent"] in [1001, 2001, 3001, 4001, 5001]:
                                Thread(target=longPressButton, args=[bridge_sensor_id, message["state"]["buttonevent"]]).start()
                        if "presence" in message["state"] and message["state"]["presence"] and bridge_config["emulator"]["alarm"]["on"] and bridge_config["emulator"]["alarm"]["lasttriggered"] + 300 < datetime.now().timestamp():
                            logging.info("Alarm triggered, sending email...")
                            requests.post("https://diyhue.org/cdn/mailNotify.php", json={"to": bridge_config["emulator"]["alarm"]["email"], "sensor": bridge_config["sensors"][bridge_sensor_id]["name"]})
                            bridge_config["emulator"]["alarm"]["lasttriggered"] = int(datetime.now().timestamp())
                    elif "config" in message and bridge_config["sensors"][bridge_sensor_id]["config"]["on"]:
                        bridge_config["sensors"][bridge_sensor_id]["config"].update(message["config"])
                elif message["r"] == "lights":
                    bridge_light_id = bridge_config["deconz"]["lights"][message["id"]]["bridgeid"]
                    if "state" in message and "colormode" not in message["state"]:
                        bridge_config["lights"][bridge_light_id]["state"].update(message["state"])
                        updateGroupStats(bridge_light_id, bridge_config["lights"], bridge_config["groups"])
            except Exception as e:
                logging.info("unable to process the request" + str(e))

    try:
        ws = EchoClient('ws://' + deconz_ip + ':' + str(bridge_config["deconz"]["websocketport"]))
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()

def scanDeconz():
    if not bridge_config["deconz"]["enabled"]:
        if "username" not in bridge_config["deconz"]:
            try:
                registration = json.loads(sendRequest("http://" + deconz_ip + ":" + str(bridge_config["deconz"]["port"]) + "/api", "POST", "{\"username\": \"283145a4e198cc6535\", \"devicetype\":\"Hue Emulator\"}"))
            except:
                logging.info("registration fail, is the link button pressed?")
                return
            if "success" in registration[0]:
                bridge_config["deconz"]["username"] = registration[0]["success"]["username"]
                bridge_config["deconz"]["enabled"] = True
    if "username" in bridge_config["deconz"]:
        deconz_config = json.loads(sendRequest("http://" + deconz_ip + ":" + str(bridge_config["deconz"]["port"]) + "/api/" + bridge_config["deconz"]["username"] + "/config", "GET", "{}"))
        bridge_config["deconz"]["websocketport"] = deconz_config["websocketport"]

        #lights
        deconz_lights = json.loads(sendRequest("http://" + deconz_ip + ":" + str(bridge_config["deconz"]["port"]) + "/api/" + bridge_config["deconz"]["username"] + "/lights", "GET", "{}"))
        for light in deconz_lights:
            if light not in bridge_config["deconz"]["lights"] and "modelid" in deconz_lights[light]:
                new_light_id = nextFreeId(bridge_config, "lights")
                logging.info("register new light " + new_light_id)
                bridge_config["lights"][new_light_id] = deconz_lights[light]
                bridge_config["lights_address"][new_light_id] = {"username": bridge_config["deconz"]["username"], "light_id": light, "ip": deconz_ip + ":" + str(bridge_config["deconz"]["port"]), "protocol": "deconz"}
                bridge_config["deconz"]["lights"][light] = {"bridgeid": new_light_id, "modelid": deconz_lights[light]["modelid"], "type": deconz_lights[light]["type"]}

        #sensors
        deconz_sensors = json.loads(sendRequest("http://" + deconz_ip + ":" + str(bridge_config["deconz"]["port"]) + "/api/" + bridge_config["deconz"]["username"] + "/sensors", "GET", "{}"))
        for sensor in deconz_sensors:
            if sensor not in bridge_config["deconz"]["sensors"] and "modelid" in deconz_sensors[sensor]:
                new_sensor_id = nextFreeId(bridge_config, "sensors")
                if deconz_sensors[sensor]["modelid"] in ["TRADFRI remote control", "TRADFRI wireless dimmer"]:
                    logging.info("register new " + deconz_sensors[sensor]["modelid"])
                    bridge_config["sensors"][new_sensor_id] = {"config": deconz_sensors[sensor]["config"], "manufacturername": deconz_sensors[sensor]["manufacturername"], "modelid": deconz_sensors[sensor]["modelid"], "name": deconz_sensors[sensor]["name"], "state": deconz_sensors[sensor]["state"], "type": deconz_sensors[sensor]["type"], "uniqueid": deconz_sensors[sensor]["uniqueid"]}
                    if "swversion" in  deconz_sensors[sensor]:
                        bridge_config["sensors"][new_sensor_id]["swversion"] = deconz_sensors[sensor]["swversion"]
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                elif deconz_sensors[sensor]["modelid"] == "TRADFRI motion sensor":
                    logging.info("register TRADFRI motion sensor as Philips Motion Sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"], "lightsensor": "astral"}
                elif deconz_sensors[sensor]["modelid"] == "lumi.vibration.aq1":
                    logging.info("register Xiaomi Vibration sensor as Philips Motion Sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"], "lightsensor": "astral"}
                elif deconz_sensors[sensor]["modelid"] == "lumi.sensor_motion.aq2":
                    if deconz_sensors[sensor]["type"] == "ZHALightLevel":
                        logging.info("register new Xiaomi light sensor")
                        bridge_config["sensors"][new_sensor_id] = {"name": "Hue ambient light sensor 1", "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:], "type": "ZLLLightLevel", "swversion": "6.1.0.18912", "state": {"dark": True, "daylight": False, "lightlevel": 6000, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False,"battery": 100, "reachable": True, "alert": "none", "tholddark": 21597, "tholdoffset": 7000, "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
                        bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue temperature sensor 1", "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:-1] + "2", "type": "ZLLTemperature", "swversion": "6.1.0.18912", "state": {"temperature": None, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False, "battery": 100, "reachable": True, "alert":"none", "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
                        bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                    elif deconz_sensors[sensor]["type"] == "ZHAPresence":
                        logging.info("register new Xiaomi motion sensor")
                        bridge_config["sensors"][new_sensor_id] = {"name": deconz_sensors[sensor]["name"], "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:], "type": "ZLLPresence", "swversion": "6.1.0.18912", "state": {"lastupdated": "none", "presence": None}, "manufacturername": "Philips", "config": {"on": False,"battery": 100,"reachable": True, "alert": "lselect", "ledindication": False, "usertest": False, "sensitivity": 2, "sensitivitymax": 2,"pending": []}, "modelid": "SML001"}
                        bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                elif deconz_sensors[sensor]["modelid"] == "lumi.sensor_motion":
                    logging.info("register Xiaomi Motion sensor w/o light sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"], "lightsensor": "astral"}
                else:
                    bridge_config["sensors"][new_sensor_id] = deconz_sensors[sensor]
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}

            else: #temporary patch for config compatibility with new release
                bridge_config["deconz"]["sensors"][sensor]["modelid"] = deconz_sensors[sensor]["modelid"]
                bridge_config["deconz"]["sensors"][sensor]["type"] = deconz_sensors[sensor]["type"]
        generateDxState()

        if "websocketport" in bridge_config["deconz"]:
            logging.info("Starting deconz websocket")
            Thread(target=websocketClient).start()


def updateAllLights():
    ## apply last state on startup to all bulbs, usefull if there was a power outage
    if bridge_config["deconz"]["enabled"]:
        sleep(60) #give 1 minute for deconz to have ZigBee network ready
    for light in bridge_config["lights_address"]:
        payload = {}
        payload["on"] = bridge_config["lights"][light]["state"]["on"]
        if payload["on"] and "bri" in bridge_config["lights"][light]["state"]:
            payload["bri"] = bridge_config["lights"][light]["state"]["bri"]
        sendLightRequest(light, payload, bridge_config["lights"], bridge_config["lights_address"])
        sleep(0.5)
        logging.info("update status for light " + light)

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


def daylightSensor():
    if bridge_config["sensors"]["1"]["modelid"] != "PHDL00" or not bridge_config["sensors"]["1"]["config"]["configured"]:
        return

    import pytz
    from astral.sun import sun
    from astral import LocationInfo
    localzone = LocationInfo('localzone', bridge_config["config"]["timezone"].split("/")[1], bridge_config["config"]["timezone"], float(bridge_config["sensors"]["1"]["config"]["lat"][:-1]), float(bridge_config["sensors"]["1"]["config"]["long"][:-1]))
    s = sun(localzone.observer, date=datetime.now())
    deltaSunset = s['sunset'].replace(tzinfo=None) - datetime.now()
    deltaSunrise = s['sunrise'].replace(tzinfo=None) - datetime.now()
    deltaSunsetOffset = deltaSunset.total_seconds() + bridge_config["sensors"]["1"]["config"]["sunsetoffset"] * 60
    deltaSunriseOffset = deltaSunrise.total_seconds() + bridge_config["sensors"]["1"]["config"]["sunriseoffset"] * 60
    logging.info("deltaSunsetOffset: " + str(deltaSunsetOffset))
    logging.info("deltaSunriseOffset: " + str(deltaSunriseOffset))
    current_time =  datetime.now()
    if deltaSunriseOffset < 0 and deltaSunsetOffset > 0:
        bridge_config["sensors"]["1"]["state"] = {"daylight":True,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        logging.info("set daylight sensor to true")
    else:
        bridge_config["sensors"]["1"]["state"] = {"daylight":False,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        logging.info("set daylight sensor to false")
    if deltaSunsetOffset > 0 and deltaSunsetOffset < 3600:
        logging.info("will start the sleep for sunset")
        sleep(deltaSunsetOffset)
        logging.info("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
        bridge_config["sensors"]["1"]["state"] = {"daylight":False,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        dxState["sensors"]["1"]["state"]["daylight"] = current_time
        rulesProcessor(["sensors","1"], current_time)
    if deltaSunriseOffset > 0 and deltaSunriseOffset < 3600:
        logging.info("will start the sleep for sunrise")
        sleep(deltaSunriseOffset)
        logging.info("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
        bridge_config["sensors"]["1"]["state"] = {"daylight":True,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        dxState["sensors"]["1"]["state"]["daylight"] = current_time
        rulesProcessor(["sensors","1"], current_time)


class S(BaseHTTPRequestHandler):
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
            f = open(cwd + '/debug/clip.html', 'rb')
            self._set_end_headers(f.read())
        elif self.path == "/factory-reset":
            self._set_headers()
            saveConfig('before-reset.json')
            bridge_config = load_config(cwd + '/default-config.json')
            saveConfig()
            self._set_end_headers(bytes(json.dumps([{"success":{"configuration":"reset","backup-filename": CONFIG_PATH + "/before-reset.json"}}] ,separators=(',', ':'),ensure_ascii=False), "utf8"))
        elif self.path == '/config.js':
            self._set_headers()
            #create a new user key in case none is available
            if len(bridge_config["config"]["whitelist"]) == 0:
                bridge_config["config"]["whitelist"]["web-ui-" + str(random.randrange(0, 99999))] = {"create date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),"last use date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),"name": "WebGui User"}
            self._set_end_headers(bytes('window.config = { API_KEY: "' + list(bridge_config["config"]["whitelist"])[0] + '",};', "utf8"))
        elif self.path.endswith((".css",".map",".png",".js")):
            self._set_headers()
            f = open(cwd + '/web-ui' + self.path, 'rb')
            self._set_end_headers(f.read())
        elif self.path == '/description.xml':
            self._set_headers()
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
            saveConfig()
            self._set_end_headers(bytes(json.dumps([{"success":{"configuration":"saved","filename": CONFIG_PATH + "/config.json"}}] ,separators=(',', ':'),ensure_ascii=False), "utf8"))
        elif self.path.startswith("/tradfri"): #setup Tradfri gateway
            self._set_headers()
            get_parameters = parse_qs(urlparse(self.path).query)
            if "code" in get_parameters:
                #register new identity
                new_identity = "Hue-Emulator-" + str(random.randrange(0, 999))
                registration = json.loads(check_output("./coap-client-linux -m post -u \"Client_identity\" -k \"" + get_parameters["code"][0] + "\" -e '{\"9090\":\"" + new_identity + "\"}' \"coaps://" + get_parameters["ip"][0] + ":5684/15011/9063\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
                bridge_config["tradfri"] = {"psk": registration["9091"], "ip": get_parameters["ip"][0], "identity": new_identity}
                lights_found = scanTradfri()
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
                        saveConfig()
                        self._set_end_headers(bytes(webform_linkbutton() + "<br> You have 30 sec to connect your device", "utf8"))
                    elif "action=Exit" in self.path:
                        self._set_AUTHHEAD()
                        self._set_end_headers(bytes('You are succesfully disconnected', "utf8"))
                    elif "action=ChangePassword" in self.path:
                        self._set_headers()
                        tmp_password = str(base64.b64encode(bytes(get_parameters["username"][0] + ":" + get_parameters["password"][0], "utf8"))).split('\'')
                        bridge_config["linkbutton"]["linkbutton_auth"] = tmp_password[1]
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
                for resourcelink in bridge_config["resourcelinks"].keys(): # delete all previews rules of IKEA remotes
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
                                bridge_config["deconz"]["sensors"][sensor] = {"hueType": get_parameters[key][0], "bridgeid": hueSwitchId}
                    else:
                        if not key.startswith("mode_"):
                            if bridge_config["sensors"][key]["modelid"] == "TRADFRI remote control":
                                if get_parameters["mode_" + key][0]  == "CT":
                                    addTradfriCtRemote(key, get_parameters[key][0])
                                elif get_parameters["mode_" + key][0]  == "SCENE":
                                    addTradfriSceneRemote(key, get_parameters[key][0])
                            elif bridge_config["sensors"][key]["modelid"] == "TRADFRI wireless dimmer":
                                addTradfriDimmer(key, get_parameters[key][0])
                            elif bridge_config["sensors"][key]["modelid"] == "TRADFRI on/off switch":
                                addTradfriOnOffSwitch(key, get_parameters[key][0])
                            elif bridge_config["deconz"]["sensors"][key]["modelid"] in ["TRADFRI motion sensor", "lumi.sensor_motion"]:
                                bridge_config["deconz"]["sensors"][key]["lightsensor"] = get_parameters[key][0]
                            #store room id in deconz sensors
                            for sensor in bridge_config["deconz"]["sensors"].keys():
                                if bridge_config["deconz"]["sensors"][sensor]["bridgeid"] == key:
                                    bridge_config["deconz"]["sensors"][sensor]["room"] = get_parameters[key][0]
                                    if bridge_config["sensors"][key]["modelid"] == "TRADFRI remote control":
                                        bridge_config["deconz"]["sensors"][sensor]["opmode"] = get_parameters["mode_" + key][0]

            else:
                scanDeconz()
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
            url_pieces = self.path.rstrip('/').split('/')
            if len(url_pieces) < 3:
                #self._set_headers_error()
                self.send_error(404, 'not found')
                return
            else:
                self._set_headers()
            if url_pieces[2] in bridge_config["config"]["whitelist"]: #if username is in whitelist
                bridge_config["config"]["UTC"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                bridge_config["config"]["localtime"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                bridge_config["config"]["whitelist"][url_pieces[2]]["last use date"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                bridge_config["config"]["linkbutton"] = int(bridge_config["linkbutton"]["lastlinkbuttonpushed"]) + 30 >= int(datetime.now().timestamp())
                if len(url_pieces) == 3: #print entire config
                    #trim off lightstates as per hue api
                    scenelist = {}
                    scenelist["scenes"] = copy.deepcopy(bridge_config["scenes"])
                    for scene in list(scenelist["scenes"]):
                        if "lightstates" in list(scenelist["scenes"][scene]):
                            del scenelist["scenes"][scene]["lightstates"]
                        if ("type" in scenelist["scenes"][scene]) and ("GroupScene" == scenelist["scenes"][scene]["type"]):
                            scenelist["scenes"][scene]["lights"] = {}
                            scenelist["scenes"][scene]["lights"] = bridge_config["groups"][bridge_config["scenes"][scene]["group"]]["lights"]
                    sanitizeBridgeScenes()
                    self._set_end_headers(bytes(json.dumps({"lights": bridge_config["lights"], "groups": bridge_config["groups"], "config": bridge_config["config"], "scenes": scenelist["scenes"], "schedules": bridge_config["schedules"], "rules": bridge_config["rules"], "sensors": bridge_config["sensors"], "resourcelinks": bridge_config["resourcelinks"]},separators=(',', ':'),ensure_ascii=False), "utf8"))
                elif len(url_pieces) == 4: #print specified object config
                    if "scenes" == url_pieces[3]: #trim lightstates for scenes
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
                        self._set_end_headers(bytes(json.dumps(bridge_config[url_pieces[3]],separators=(',', ':'),ensure_ascii=False), "utf8"))
                elif (len(url_pieces) == 5 or (len(url_pieces) == 6 and url_pieces[5] == 'state')):
                    if url_pieces[4] == "new": #return new lights and sensors only
                        if url_pieces[3] == 'lights':
                            new_lights.update({"lastscan": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")})
                            self._set_end_headers(bytes(json.dumps(new_lights ,separators=(',', ':'),ensure_ascii=False), "utf8"))
                        elif url_pieces[3] == 'sensors':
                            # Temporarilty return nothing
                            self._set_end_headers(bytes(json.dumps({} ,separators=(',', ':'),ensure_ascii=False), "utf8"))
                    elif url_pieces[3] == "groups" and url_pieces[4] == "0":
                        any_on = False
                        all_on = True
                        for group_state in bridge_config["groups"].keys():
                            if bridge_config["groups"][group_state]["state"]["any_on"] == True:
                                any_on = True
                            else:
                                all_on = False
                        self._set_end_headers(bytes(json.dumps({"name":"Group 0","lights": [l for l in bridge_config["lights"]],"sensors": [s for s in bridge_config["sensors"]],"type":"LightGroup","state":{"all_on":all_on,"any_on":any_on},"recycle":False,"action":{"on":False,"alert":"none"}},separators=(',', ':'),ensure_ascii=False), "utf8"))
                    elif url_pieces[3] == "info" and url_pieces[4] == "timezones":
                        self._set_end_headers(bytes(json.dumps(bridge_config["capabilities"][url_pieces[4]]["values"],separators=(',', ':'),ensure_ascii=False), "utf8"))
                    elif "scenes" == url_pieces[3]: #trim lightstates for scenes
                        scenelist = {}
                        scenelist["scenes"] = copy.deepcopy(bridge_config["scenes"])
                        for scene in list(scenelist["scenes"]):
                            if ("type" in scenelist["scenes"][scene]) and ("GroupScene" == scenelist["scenes"][scene]["type"]):
                                scenelist["scenes"][scene]["lights"] = {}
                                scenelist["scenes"][scene]["lights"] = bridge_config["groups"][bridge_config["scenes"][scene]["group"]]["lights"]
                        self._set_end_headers(bytes(json.dumps(scenelist["scenes"][url_pieces[4]],separators=(',', ':'),ensure_ascii=False), "utf8"))
                    else:
                        self._set_end_headers(bytes(json.dumps(bridge_config[url_pieces[3]][url_pieces[4]],separators=(',', ':'),ensure_ascii=False), "utf8"))
            elif (len(url_pieces) == 4 and url_pieces[3] == "config") or (len(url_pieces) == 3 and url_pieces[2] == "config"): #used by applications to discover the bridge
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
        url_pieces = self.path.rstrip('/').split('/')
        if len(url_pieces) == 4: #data was posted to a location
            if url_pieces[2] in bridge_config["config"]["whitelist"]: #check to make sure request is authorized
                if ((url_pieces[3] == "lights" or url_pieces[3] == "sensors") and not bool(post_dictionary)):
                    #if was a request to scan for lights of sensors
                    new_lights.clear()
                    Thread(target=scan_for_lights).start()
                    sleep(7) #give no more than 5 seconds for light scanning (otherwise will face app disconnection timeout)
                    self._set_end_headers(bytes(json.dumps([{"success": {"/" + url_pieces[3]: "Searching for new devices"}}],separators=(',', ':'),ensure_ascii=False), "utf8"))
                elif url_pieces[3] == "":
                    self._set_end_headers(bytes(json.dumps([{"success": {"clientkey": "321c0c2ebfa7361e55491095b2f5f9db"}}],separators=(',', ':'),ensure_ascii=False), "utf8"))
                else: #create object
                    # find the first unused id for new object
                    new_object_id = nextFreeId(bridge_config, url_pieces[3])
                    if url_pieces[3] == "scenes": # store scene
                        post_dictionary.update({"version": 2, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "owner" :url_pieces[2]})
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

                    elif url_pieces[3] == "groups":
                        if "type" not in post_dictionary:
                            post_dictionary["type"] = "LightGroup"
                        if post_dictionary["type"] in ["Room", "Zone"] and "class" not in post_dictionary:
                            post_dictionary["class"] = "Other"
                        elif post_dictionary["type"] == "Entertainment" and "stream" not in post_dictionary:
                            post_dictionary["stream"] = {"active": False, "owner": url_pieces[2], "proxymode": "auto", "proxynode": "/bridge"}
                        post_dictionary.update({"action": {"on": False}, "state": {"any_on": False, "all_on": False}})
                    elif url_pieces[3] == "schedules":
                        try:
                            post_dictionary.update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "time": post_dictionary["localtime"]})
                        except KeyError:
                            post_dictionary.update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "localtime": post_dictionary["time"]})
                        if post_dictionary["localtime"].startswith("PT") or post_dictionary["localtime"].startswith("R/PT"):
                            post_dictionary.update({"starttime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                        if not "status" in post_dictionary:
                            post_dictionary.update({"status": "enabled"})
                    elif url_pieces[3] == "rules":
                        post_dictionary.update({"owner": url_pieces[2], "lasttriggered" : "none", "created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "timestriggered": 0})
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
                            post_dictionary.update({"state": {"flag": False, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}, "config": {"on": True,"reachable": True}})
                    elif url_pieces[3] == "resourcelinks":
                        post_dictionary.update({"owner" :url_pieces[2]})
                    generateDxState()
                    bridge_config[url_pieces[3]][new_object_id] = post_dictionary
                    logging.info(json.dumps([{"success": {"id": new_object_id}}], sort_keys=True, indent=4, separators=(',', ': ')))
                    self._set_end_headers(bytes(json.dumps([{"success": {"id": new_object_id}}], separators=(',', ':'),ensure_ascii=False), "utf8"))
            else:
                self._set_end_headers(bytes(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}], separators=(',', ':'),ensure_ascii=False), "utf8"))
                logging.info(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],sort_keys=True, indent=4, separators=(',', ': ')))
        elif self.path.startswith("/api") and "devicetype" in post_dictionary: #new registration by linkbutton
            last_button_press = int(bridge_config["linkbutton"]["lastlinkbuttonpushed"])
            if (args.no_link_button or last_button_press+30 >= int(datetime.now().timestamp()) or
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
        saveConfig()

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
            if len(url_pieces) == 5:
                if url_pieces[3] == "schedules":
                    if "status" in put_dictionary and put_dictionary["status"] == "enabled" and (bridge_config["schedules"][url_pieces[4]]["localtime"].startswith("PT") or bridge_config["schedules"][url_pieces[4]]["localtime"].startswith("R/PT")):
                        bridge_config["schedules"][url_pieces[4]]["starttime"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
                    bridge_config[url_pieces[3]][url_pieces[4]].update(put_dictionary)
                elif url_pieces[3] == "scenes":
                    if "storelightstate" in put_dictionary:
                        if "lights" in bridge_config["scenes"][url_pieces[4]]:
                            lights = bridge_config["scenes"][url_pieces[4]]["lights"]
                        elif "group" in bridge_config["scenes"][url_pieces[4]]:
                            lights = bridge_config["groups"][bridge_config["scenes"][url_pieces[4]]["group"]]["lights"]
                        for light in lights:
                            bridge_config["scenes"][url_pieces[4]]["lightstates"][light] = {}
                            bridge_config["scenes"][url_pieces[4]]["lightstates"][light]["on"] = bridge_config["lights"][light]["state"]["on"]
                            if "bri" in bridge_config["lights"][light]["state"]:
                                bridge_config["scenes"][url_pieces[4]]["lightstates"][light]["bri"] = bridge_config["lights"][light]["state"]["bri"]
                            if "colormode" in bridge_config["lights"][light]["state"]:
                                if bridge_config["lights"][light]["state"]["colormode"] in ["ct", "xy"]:
                                    bridge_config["scenes"][url_pieces[4]]["lightstates"][light][bridge_config["lights"][light]["state"]["colormode"]] = bridge_config["lights"][light]["state"][bridge_config["lights"][light]["state"]["colormode"]]
                                elif bridge_config["lights"][light]["state"]["colormode"] == "hs" and "hue" in bridge_config["scenes"][url_pieces[4]]["lightstates"][light]:
                                    bridge_config["scenes"][url_pieces[4]]["lightstates"][light]["hue"] = bridge_config["lights"][light]["state"]["hue"]
                                    bridge_config["scenes"][url_pieces[4]]["lightstates"][light]["sat"] = bridge_config["lights"][light]["state"]["sat"]
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
                    bridge_config["sensors"][url_pieces[4]]["state"]["lastupdated"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
                    if url_pieces[4] == "1" and bridge_config[url_pieces[3]][url_pieces[4]]["modelid"] == "PHDL00":
                        bridge_config["sensors"]["1"]["config"]["configured"] = True ##mark daylight sensor as configured
                elif url_pieces[3] == "groups" and "stream" in put_dictionary:
                    if "active" in put_dictionary["stream"]:
                        if put_dictionary["stream"]["active"]:
                            for light in bridge_config["groups"][url_pieces[4]]["lights"]:
                                bridge_config["lights"][light]["state"]["mode"] = "streaming"
                            logging.info("start hue entertainment")
                            Popen(["/opt/hue-emulator/entertain-srv", "server_port=2100", "dtls=1", "psk_list=" + url_pieces[2] + ",321c0c2ebfa7361e55491095b2f5f9db"])
                            sleep(0.2)
                            bridge_config["groups"][url_pieces[4]]["stream"].update({"active": True, "owner": url_pieces[2], "proxymode": "auto", "proxynode": "/bridge"})
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
                    if "startup" in put_dictionary["config"] and bridge_config["lights_address"][url_pieces[4]]["protocol"] == "native":
                        if put_dictionary["config"]["startup"]["mode"] == "safety":
                            sendRequest("http://" + bridge_config["lights_address"][url_pieces[4]]["ip"] + "/", "POST", {"startup": 1})
                        elif put_dictionary["config"]["startup"]["mode"] == "powerfail":
                            sendRequest("http://" + bridge_config["lights_address"][url_pieces[4]]["ip"] + "/", "POST", {"startup": 0})

                        #add exception on json output as this dictionary has tree levels
                        response_dictionary = {"success":{"/lights/" + url_pieces[4] + "/config/startup": {"mode": put_dictionary["config"]["startup"]["mode"]}}}
                        self._set_end_headers(bytes(json.dumps(response_dictionary,separators=(',', ':'),ensure_ascii=False), "utf8"))
                        logging.info(json.dumps(response_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))
                        return
                else:
                    bridge_config[url_pieces[3]][url_pieces[4]].update(put_dictionary)
                    if url_pieces[3] == "groups" and "lights" in put_dictionary: #need to update scene lightstates
                        for scene in bridge_config["scenes"]: # iterate over scenes
                            for light in put_dictionary["lights"]: # check each scene to make sure it has a lightstate for each new light
                                if "lightstates" in bridge_config["scenes"][scene] and light not in bridge_config["scenes"][scene]["lightstates"]: # copy first light state to new light
                                    if ("lights" in bridge_config["scenes"][scene] and light in bridge_config["scenes"][scene]["lights"]) or \
                                    (bridge_config["scenes"][scene]["type"] == "GroupScene" and light in bridge_config["groups"][bridge_config["scenes"][scene]["group"]]["lights"]):
                                        # Either light is in the scene or part of the group now, add lightscene based on previous scenes
                                        new_state = next(iter(bridge_config["scenes"][scene]["lightstates"]))
                                        new_state = bridge_config["scenes"][scene]["lightstates"][new_state]
                                        bridge_config["scenes"][scene]["lightstates"][light] = new_state

                response_location = "/" + url_pieces[3] + "/" + url_pieces[4] + "/"
            if len(url_pieces) == 6:
                if url_pieces[3] == "groups": #state is applied to a group
                    if url_pieces[5] == "stream":
                        if "active" in put_dictionary:
                            if put_dictionary["active"]:
                                logging.info("start hue entertainment")
                                Popen(["/opt/hue-emulator/entertain-srv", "server_port=2100", "dtls=1", "psk_list=" + url_pieces[2] + ",321c0c2ebfa7361e55491095b2f5f9db"])
                                sleep(0.2)
                                bridge_config["groups"][url_pieces[4]]["stream"].update({"active": True, "owner": url_pieces[2], "proxymode": "auto", "proxynode": "/bridge"})
                            else:
                                Popen(["killall", "entertain-srv"])
                                bridge_config["groups"][url_pieces[4]]["stream"].update({"active": False, "owner": None})
                    elif "scene" in put_dictionary: #scene applied to group
                        if bridge_config["scenes"][put_dictionary["scene"]]["type"] == "GroupScene":
                            splitLightsToDevices(bridge_config["scenes"][put_dictionary["scene"]]["group"], {}, bridge_config["scenes"][put_dictionary["scene"]]["lightstates"])
                        else:
                            splitLightsToDevices(url_pieces[4], {}, bridge_config["scenes"][put_dictionary["scene"]]["lightstates"])
                    elif "bri_inc" in put_dictionary or "ct_inc" in put_dictionary or "hue_inc" in put_dictionary:
                        splitLightsToDevices(url_pieces[4], put_dictionary)
                    elif "scene_inc" in put_dictionary:
                        switchScene(url_pieces[4], put_dictionary["scene_inc"])
                    elif url_pieces[4] == "0": #if group is 0 the scene applied to all lights
                        groupZero(put_dictionary)
                    else: # the state is applied to particular group (url_pieces[4])
                        if "on" in put_dictionary:
                            bridge_config["groups"][url_pieces[4]]["state"]["any_on"] = put_dictionary["on"]
                            bridge_config["groups"][url_pieces[4]]["state"]["all_on"] = put_dictionary["on"]
                            dxState["groups"][url_pieces[4]]["state"]["any_on"] = current_time
                            dxState["groups"][url_pieces[4]]["state"]["all_on"] = current_time
                        bridge_config["groups"][url_pieces[4]][url_pieces[5]].update(put_dictionary)
                        splitLightsToDevices(url_pieces[4], put_dictionary)
                elif url_pieces[3] == "lights": #state is applied to a light
                    for key in put_dictionary.keys():
                        if key in ["ct", "xy"]: #colormode must be set by bridge
                            bridge_config["lights"][url_pieces[4]]["state"]["colormode"] = key
                        elif key in ["hue", "sat"]:
                            bridge_config["lights"][url_pieces[4]]["state"]["colormode"] = "hs"

                    updateGroupStats(url_pieces[4], bridge_config["lights"], bridge_config["groups"])
                    sendLightRequest(url_pieces[4], put_dictionary, bridge_config["lights"], bridge_config["lights_address"])
                elif url_pieces[3] == "sensors":
                    if url_pieces[5] == "state":
                        for key in put_dictionary.keys():
                            # track time of state changes in dxState
                            if not key in bridge_config["sensors"][url_pieces[4]]["state"] or bridge_config["sensors"][url_pieces[4]]["state"][key] != put_dictionary[key]:
                                dxState["sensors"][url_pieces[4]]["state"][key] = current_time
                    elif url_pieces[4] == "1":
                        bridge_config["sensors"]["1"]["config"]["configured"] = True ##mark daylight sensor as configured
                    dxState["sensors"][url_pieces[4]]["state"]["lastupdated"] = current_time
                    bridge_config["sensors"][url_pieces[4]]["state"]["lastupdated"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
                if  url_pieces[4] != "0" and "scene" not in put_dictionary: #group 0 is virtual, must not be saved in bridge configuration, also the recall scene
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
                response_location = "/" + url_pieces[3] + "/" + url_pieces[4] + "/" + url_pieces[5] + "/" + url_pieces[6] + "/"
            response_dictionary = []
            for key, value in put_dictionary.items():
                response_dictionary.append({"success":{response_location + key: value}})
            sleep(0.3)
            self._set_end_headers(bytes(json.dumps(response_dictionary,separators=(',', ':'),ensure_ascii=False), "utf8"))
            logging.info(json.dumps(response_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))
            if len(url_pieces) > 4:
                rulesProcessor([url_pieces[3], url_pieces[4]], current_time)
            sanitizeBridgeScenes() # in case some lights where removed from group it will need to remove them also from group scenes.
        else:
            self._set_end_headers(bytes(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],separators=(',', ':'),ensure_ascii=False), "utf8"))

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
                    Thread(target=resourceRecycle).start()
                elif url_pieces[3] == "sensors":
                    ## delete also related sensors
                    for sensor in list(bridge_config["sensors"]):
                        if sensor != url_pieces[4] and "uniqueid" in bridge_config["sensors"][sensor] and bridge_config["sensors"][sensor]["uniqueid"].startswith(bridge_config["sensors"][url_pieces[4]]["uniqueid"][:26]):
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
                        if "lights" in bridge_config["scenes"][scene] and del_light in bridge_config["scenes"][scene]["lights"]:
                            bridge_config["scenes"][scene]["lights"].remove(del_light)
                        if ("lights" in bridge_config["scenes"][scene] and len(bridge_config["scenes"][scene]["lights"]) == 0) or len(bridge_config["scenes"][scene]["lightstates"]) == 0:
                            del bridge_config["scenes"][scene]
            elif url_pieces[3] == "sensors":
                for sensor in list(bridge_config["deconz"]["sensors"]):
                    if bridge_config["deconz"]["sensors"][sensor]["bridgeid"] == url_pieces[4]:
                        del bridge_config["deconz"]["sensors"][sensor]
                for sensor in list(bridge_config["emulator"]["sensors"]):
                    if bridge_config["emulator"]["sensors"][sensor]["bridgeId"] == url_pieces[4]:
                        del bridge_config["emulator"]["sensors"][sensor]
            elif url_pieces[3] == "groups":
                sanitizeBridgeScenes()
            logging.info(json.dumps([{"success": "/" + url_pieces[3] + "/" + url_pieces[4] + " deleted."}],separators=(',', ':'),ensure_ascii=False))
            self._set_end_headers(bytes(json.dumps([{"success": "/" + url_pieces[3] + "/" + url_pieces[4] + " deleted."}],separators=(',', ':'),ensure_ascii=False), "utf8"))

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

def run(https, server_class=ThreadingSimpleServer, handler_class=S):
    if https:
        server_address = (BIND_IP, HOST_HTTPS_PORT)
        httpd = server_class(server_address, handler_class)
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(certfile=CONFIG_PATH + "/cert.pem")
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

if __name__ == "__main__":
    initialize()
    updateConfig()
    saveConfig()
    Thread(target=resourceRecycle).start()
    if bridge_config["deconz"]["enabled"]:
        scanDeconz()
    if "emulator" in bridge_config and "mqtt" in bridge_config["emulator"] and bridge_config["emulator"]["mqtt"]["enabled"]:
        mqtt.mqttServer(bridge_config["emulator"]["mqtt"], bridge_config["lights"], bridge_config["lights_address"], bridge_config["sensors"])
    if "emulator" in bridge_config and "homeassistant" in bridge_config["emulator"] and bridge_config["emulator"]["homeassistant"]["enabled"]:
        homeassistant_ws.create_ws_client(bridge_config["emulator"]["homeassistant"], bridge_config["lights"], bridge_config["lights_address"], bridge_config["sensors"])

    try:
        if update_lights_on_startup:
            Thread(target=updateAllLights).start()
        Thread(target=ssdpSearch, args=[HOST_IP, HOST_HTTP_PORT, mac]).start()
        Thread(target=ssdpBroadcast, args=[HOST_IP, HOST_HTTP_PORT, mac]).start()
        Thread(target=schedulerProcessor).start()
        Thread(target=syncWithLights, args=[bridge_config["lights"], bridge_config["lights_address"], bridge_config["config"]["whitelist"], bridge_config["groups"], off_if_unreachable]).start()
        Thread(target=entertainmentService, args=[bridge_config["lights"], bridge_config["lights_address"], bridge_config["groups"], HOST_IP]).start()
        Thread(target=run, args=[False]).start()
        if not args.no_serve_https:
            Thread(target=run, args=[True]).start()
        Thread(target=daylightSensor).start()
        Thread(target=remoteApi, args=[BIND_IP, bridge_config["config"]]).start()
        if disableOnlineDiscover == False:
            Thread(target=remoteDiscover, args=[bridge_config["config"]]).start()

        while True:
            sleep(10)
            sys.exit()
    except Exception:
        logging.exception("server stopped ")
    finally:
        run_service = False
        logging.info('gracefully exit')
