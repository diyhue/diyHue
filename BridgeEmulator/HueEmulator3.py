#!/usr/bin/python3
import base64
import hashlib
import json
import logging
import os
import random
import socket
import ssl
import sys
import requests
from collections import defaultdict
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from subprocess import Popen, check_output
from threading import Thread
from time import sleep, strftime
from urllib.parse import parse_qs, urlparse
from functions import light_types, nextFreeId
from functions.colors import convert_rgb_xy, convert_xy, hsv_to_rgb
from functions.html import (description, webform_hue, webform_linkbutton,
                            webform_milight, webformDeconz, webformTradfri)
from functions.ssdp import ssdpBroadcast, ssdpSearch
from functions.network import getIpAddress
from protocols import yeelight
from protocols import tasmota

debug = False # set this to True in order to see all script actions.

if debug: 
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)

protocols = [yeelight, tasmota]

cwd = os.path.split(os.path.abspath(__file__))[0]
docker = False # Set only to true if using script in Docker container

update_lights_on_startup = False # if set to true all lights will be updated with last know state on startup.

def pretty_json(data):
    return json.dumps(data, sort_keys=True,                  indent=4, separators=(',', ': '))

if len(sys.argv) == 3:
    mac = str(sys.argv[1]).replace(":","")
else:
    mac = check_output("cat /sys/class/net/$(ip -o addr | grep " + getIpAddress() + " | awk '{print $2}')/address", shell=True).decode('utf-8').replace(":","")[:-1]
logging.debug(mac)

run_service = True

bridge_config = defaultdict(lambda:defaultdict(str))
new_lights = {}
sensors_state = {}


def updateConfig():
    for sensor in bridge_config["deconz"]["sensors"].keys():
        if "modelid" not in bridge_config["deconz"]["sensors"][sensor]:
            bridge_config["deconz"]["sensors"]["modelid"] = bridge_config["sensors"][bridge_config["deconz"]["sensors"][sensor]["bridgeid"]]["modelid"]
        if bridge_config["deconz"]["sensors"][sensor]["modelid"] == "TRADFRI motion sensor":
            if "lightsensor" not in bridge_config["deconz"]["sensors"][sensor]:
                bridge_config["deconz"]["sensors"][sensor]["lightsensor"] = "internal"
    for sensor in bridge_config["sensors"].keys():
        if bridge_config["sensors"][sensor]["type"] == "CLIPGenericStatus":
            bridge_config["sensors"][sensor]["state"]["status"] = 0
    for light in bridge_config["lights_address"].keys():
        if bridge_config["lights_address"][light]["protocol"] =="native" and "mac" not in bridge_config["lights_address"][light]:
            bridge_config["lights_address"][light]["mac"] = bridge_config["lights"][light]["uniqueid"][:17]
            bridge_config["lights"][light]["uniqueid"] = "00:17:88:01:00:" + hex(random.randrange(0,255))[2:] + ":" + hex(random.randrange(0,255))[2:] + ":" + hex(random.randrange(0,255))[2:] + "-0b"
        if bridge_config["lights_address"][light]["protocol"] =="deconz":
            for key in list(bridge_config["lights"][light]):
                if key in ["hascolor", "ctmax", "ctmin", "etag"]:
                    del bridge_config["lights"][light][key]
            if bridge_config["lights"][light]["modelid"].startswith("TRADFRI"):
                if bridge_config["lights"][light]["type"] == "Color temperature light":
                    bridge_config["lights"][light].update({"manufacturername": "Philips", "modelid": "LTW001", "uniqueid": "00:17:88:01:00:" + hex(random.randrange(0,255))[2:] + ":" + hex(random.randrange(0,255))[2:] + ":" + hex(random.randrange(0,255))[2:] + "-0b","swversion": "5.50.1.19085"})
                elif bridge_config["lights"][light]["type"] == "Color light":
                    bridge_config["lights"][light].update({"type": "Extended color light", "manufacturername": "Philips", "modelid": "LCT015", "uniqueid": "00:17:88:01:00:" + hex(random.randrange(0,255))[2:] + ":" + hex(random.randrange(0,255))[2:] + ":" + hex(random.randrange(0,255))[2:] + "-0b", "swversion": "1.29.0_r21169"})
                elif bridge_config["lights"][light]["type"] == "Dimmable light":
                    bridge_config["lights"][light].update({"manufacturername": "Philips", "modelid": "LWB010", "uniqueid": "00:17:88:01:00:" + hex(random.randrange(0,255))[2:] + ":" + hex(random.randrange(0,255))[2:] + ":" + hex(random.randrange(0,255))[2:] + "-0b", "swversion": "1.15.0_r18729"})
    #fix timezones bug
    if "values" not in bridge_config["capabilities"]["timezones"]:
        timezones = bridge_config["capabilities"]["timezones"]
        del bridge_config["capabilities"]["timezones"]
        bridge_config["capabilities"]["timezones"] = {"values": timezones}

def entertainmentService():
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSocket.bind(('127.0.0.1', 2101))
    fremeID = 0
    lightStatus = {}
    while True:
        data = serverSocket.recvfrom(106)[0]
        nativeLights = {}
        if data[:9].decode('utf-8') == "HueStream":
            if data[14] == 0: #rgb colorspace
                i = 16
                while i < len(data):
                    if data[i] == 0: #Type of device 0x00 = Light
                        lightId = data[i+1] * 256 + data[i+2]
                        if lightId != 0:
                            r = int((data[i+3] * 256 + data[i+4]) / 256)
                            g = int((data[i+5] * 256 + data[i+6]) / 256)
                            b = int((data[i+7] * 256 + data[i+7]) / 256)
                            if lightId not in lightStatus:
                                lightStatus[lightId] = {"on": False, "bri": 1}
                            if r == 0 and  g == 0 and  b == 0:
                                bridge_config["lights"][str(lightId)]["state"]["on"] = False
                            else:
                                bridge_config["lights"][str(lightId)]["state"].update({"on": True, "bri": int((r + g + b) / 3), "xy": convert_rgb_xy(r, g, b), "colormode": "xy"})
                            if bridge_config["lights_address"][str(lightId)]["protocol"] == "native":
                                if bridge_config["lights_address"][str(lightId)]["ip"] not in nativeLights:
                                    nativeLights[bridge_config["lights_address"][str(lightId)]["ip"]] = {}
                                nativeLights[bridge_config["lights_address"][str(lightId)]["ip"]][bridge_config["lights_address"][str(lightId)]["light_nr"] - 1] = [r, g, b]
                            else:
                                if fremeID == 24: # => every seconds, increase in case the destination device is overloaded
                                    if r == 0 and  g == 0 and  b == 0:
                                        if lightStatus[lightId]["on"]:
                                            sendLightRequest(str(lightId), {"on": False, "transitiontime": 3})
                                            lightStatus[lightId]["on"] = False
                                    elif lightStatus[lightId]["on"] == False:
                                        sendLightRequest(str(lightId), {"on": True, "transitiontime": 3})
                                        lightStatus[lightId]["on"] = True
                                    elif abs(int((r + b + g) / 3) - lightStatus[lightId]["bri"]) > 50: # to optimize, send brightness  only of difference is bigger than this value
                                        sendLightRequest(str(lightId), {"bri": int((r + b + g) / 3), "transitiontime": 3})
                                        lightStatus[lightId]["bri"] = int((r + b + g) / 3)
                                    else:
                                        sendLightRequest(str(lightId), {"xy": convert_rgb_xy(r, g, b), "transitiontime": 3})
                            fremeID += 1
                            if fremeID == 25:
                                fremeID = 0
                            updateGroupStats(lightId)
                        i = i + 9
            elif data[14] == 1: #cie colorspace
                i = 16
                while i < len(data):
                    if data[i] == 0: #Type of device 0x00 = Light
                        lightId = data[i+1] * 256 + data[i+2]
                        if lightId != 0:
                            x = (data[i+3] * 256 + data[i+4]) / 65535
                            y = (data[i+5] * 256 + data[i+6]) / 65535
                            bri = int((data[i+7] * 256 + data[i+7]) / 256)
                            if bri == 0:
                                bridge_config["lights"][str(lightId)]["state"]["on"] = False
                            else:
                                bridge_config["lights"][str(lightId)]["state"].update({"on": True, "bri": bri, "xy": [x,y], "colormode": "xy"})
                            if bridge_config["lights_address"][str(lightId)]["protocol"] == "native":
                                if bridge_config["lights_address"][str(lightId)]["ip"] not in nativeLights:
                                    nativeLights[bridge_config["lights_address"][str(lightId)]["ip"]] = {}
                                nativeLights[bridge_config["lights_address"][str(lightId)]["ip"]][bridge_config["lights_address"][str(lightId)]["light_nr"] - 1] = convert_xy(x, y, bri)
                            else:
                                fremeID += 1
                                if fremeID == 24 : #24 = every seconds, increase in case the destination device is overloaded
                                    sendLightRequest(str(lightId), {"xy": [x,y]})
                                    fremeID = 0
                            updateGroupStats(lightId)
        if len(nativeLights) is not 0:
            for ip in nativeLights.keys():
                udpmsg = bytearray()
                for light in nativeLights[ip].keys():
                    udpmsg += bytes([light]) + bytes([nativeLights[ip][light][0]]) + bytes([nativeLights[ip][light][1]]) + bytes([nativeLights[ip][light][2]])
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
                sock.sendto(udpmsg, (ip, 2100))



def addTradfriDimmer(sensor_id, group_id):
    rules = [{ "actions":[{"address": "/groups/" + group_id + "/action", "body":{ "on":True, "bri":1 }, "method": "PUT" }], "conditions":[{ "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}, { "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2002" }, { "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "false" }], "name": "Remote " + sensor_id + " turn on" },{"actions":[{"address":"/groups/" + group_id + "/action", "body":{ "on": False}, "method":"PUT"}], "conditions":[{ "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }, { "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4002" }, { "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "true" }, { "address": "/groups/" + group_id + "/action/bri", "operator": "eq", "value": "1"}], "name":"Dimmer Switch " + sensor_id + " off"}, { "actions":[{ "address": "/groups/" + group_id + "/action", "body":{ "on":False }, "method": "PUT" }], "conditions":[{ "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }, { "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3002" }, { "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "true" }, { "address": "/groups/" + group_id + "/action/bri", "operator": "eq", "value": "1"}], "name": "Remote " + sensor_id + " turn off" }, { "actions": [{"address": "/groups/" + group_id + "/action", "body":{"bri_inc": 32, "transitiontime": 9}, "method": "PUT" }], "conditions": [{ "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "true" },{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2002" }, {"address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}], "name": "Dimmer Switch " + sensor_id + " rotate right"}, { "actions": [{"address": "/groups/" + group_id + "/action", "body":{"bri_inc": 56, "transitiontime": 9}, "method": "PUT" }], "conditions": [{ "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "true" },{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "1002" }, {"address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}], "name": "Dimmer Switch " + sensor_id + " rotate fast right"}, {"actions": [{"address": "/groups/" + group_id + "/action", "body": {"bri_inc": -32, "transitiontime": 9}, "method": "PUT"}], "conditions": [{ "address": "/groups/" + group_id + "/action/bri", "operator": "gt", "value": "1"},{"address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3002"}, {"address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}], "name": "Dimmer Switch " + sensor_id + " rotate left"}, {"actions": [{"address": "/groups/" + group_id + "/action", "body": {"bri_inc": -56, "transitiontime": 9}, "method": "PUT"}], "conditions": [{ "address": "/groups/" + group_id + "/action/bri", "operator": "gt", "value": "1"},{"address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4002"}, {"address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}], "name": "Dimmer Switch " + sensor_id + " rotate left"}]
    resourcelinkId = nextFreeId(bridge_config, "resourcelinks")
    bridge_config["resourcelinks"][resourcelinkId] = {"classid": 15555,"description": "Rules for sensor " + sensor_id, "links": ["/sensors/" + sensor_id], "name": "Emulator rules " + sensor_id,"owner": list(bridge_config["config"]["whitelist"])[0]}
    for rule in rules:
        ruleId = nextFreeId(bridge_config, "rules")
        bridge_config["rules"][ruleId] = rule
        bridge_config["rules"][ruleId].update({"creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "lasttriggered": None, "owner": list(bridge_config["config"]["whitelist"])[0], "recycle": True, "status": "enabled", "timestriggered": 0})
        bridge_config["resourcelinks"][resourcelinkId]["links"].append("/rules/" + ruleId)

def addTradfriCtRemote(sensor_id, group_id):
    rules = [{"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": True},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "1002"},{"address": "/groups/" + group_id + "/state/any_on","operator": "eq","value": "false"}],"name": "Remote " + sensor_id + " button on"}, {"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": False},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "1002"},{"address": "/groups/" + group_id + "/state/any_on","operator": "eq","value": "true"}],"name": "Remote " + sensor_id + " button off"},{ "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": 30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " up-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": 56, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " up-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": -30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " dn-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": -56, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " dn-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "ct_inc": 50, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ctl-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "ct_inc": 100, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ctl-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "ct_inc": -50, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "5002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ct-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "ct_inc": -100, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "5001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ct-long" }]
    resourcelinkId = nextFreeId(bridge_config, "resourcelinks")
    bridge_config["resourcelinks"][resourcelinkId] = {"classid": 15555,"description": "Rules for sensor " + sensor_id, "links": ["/sensors/" + sensor_id], "name": "Emulator rules " + sensor_id,"owner": list(bridge_config["config"]["whitelist"])[0]}
    for rule in rules:
        ruleId = nextFreeId(bridge_config, "rules")
        bridge_config["rules"][ruleId] = rule
        bridge_config["rules"][ruleId].update({"creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "lasttriggered": None, "owner": list(bridge_config["config"]["whitelist"])[0], "recycle": True, "status": "enabled", "timestriggered": 0})
        bridge_config["resourcelinks"][resourcelinkId]["links"].append("/rules/" + ruleId)

def addTradfriSceneRemote(sensor_id, group_id):
    rules = [{"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": True},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "1002"},{"address": "/groups/" + group_id + "/state/any_on","operator": "eq","value": "false"}],"name": "Remote " + sensor_id + " button on"}, {"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": False},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "1002"},{"address": "/groups/" + group_id + "/state/any_on","operator": "eq","value": "true"}],"name": "Remote " + sensor_id + " button off"},{ "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": 30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " up-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": 56, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " up-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": -30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " dn-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": -56, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " dn-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "scene_inc": -1 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ctl-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "scene_inc": -1 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ctl-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "scene_inc": 1 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "5002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ct-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "scene_inc": 1 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "5001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ct-long" }]
    resourcelinkId = nextFreeId(bridge_config, "resourcelinks")
    bridge_config["resourcelinks"][resourcelinkId] = {"classid": 15555,"description": "Rules for sensor " + sensor_id, "links": ["/sensors/" + sensor_id], "name": "Emulator rules " + sensor_id,"owner": list(bridge_config["config"]["whitelist"])[0]}
    for rule in rules:
        ruleId = nextFreeId(bridge_config, "rules")
        bridge_config["rules"][ruleId] = rule
        bridge_config["rules"][ruleId].update({"creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "lasttriggered": None, "owner": list(bridge_config["config"]["whitelist"])[0], "recycle": True, "status": "enabled", "timestriggered": 0})
        bridge_config["resourcelinks"][resourcelinkId]["links"].append("/rules/" + ruleId)

def addHueMotionSensor(uniqueid, name="Entrance Lights sensor"):
    new_sensor_id = nextFreeId(bridge_config, "sensors")
    if uniqueid == "":
        if len(new_sensor_id) == 1:
            uniqueid = "0" + new_sensor_id + ":0f:12:23:34:45"
        else:
            uniqueid = new_sensor_id + ":0f:12:23:34:45"
    bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue temperature sensor 1", "uniqueid": uniqueid + ":56:d0:5b-02-0402", "type": "ZLLTemperature", "swversion": "6.1.0.18912", "state": {"temperature": None, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False, "battery": 100, "reachable": True, "alert":"none", "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
    motion_sensor = nextFreeId(bridge_config, "sensors")
    bridge_config["sensors"][motion_sensor] = {"name": name, "uniqueid": uniqueid + ":56:d0:5b-02-0406", "type": "ZLLPresence", "swversion": "6.1.0.18912", "state": {"lastupdated": "none", "presence": None}, "manufacturername": "Philips", "config": {"on": False,"battery": 100,"reachable": True, "alert": "lselect", "ledindication": False, "usertest": False, "sensitivity": 2, "sensitivitymax": 2,"pending": []}, "modelid": "SML001"}
    bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue ambient light sensor", "uniqueid": uniqueid + ":56:d0:5b-02-0400", "type": "ZLLLightLevel", "swversion": "6.1.0.18912", "state": {"dark": True, "daylight": False, "lightlevel": 6000, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False,"battery": 100, "reachable": True, "alert": "none", "tholddark": 21597, "tholdoffset": 7000, "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
    return(motion_sensor)

def addHueSwitch(uniqueid, sensorsType):
    new_sensor_id = nextFreeId(bridge_config, "sensors")
    if uniqueid == "":
        uniqueid = "00:00:00:00:00:40:" + new_sensor_id + ":83-f2"
    bridge_config["sensors"][new_sensor_id] = {"state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "name": "Dimmer Switch" if sensorsType == "ZLLSwitch" else "Tap Switch", "type": sensorsType, "modelid": "RWL021" if sensorsType == "ZLLSwitch" else "ZGPSWITCH", "manufacturername": "Philips", "swversion": "5.45.1.17846" if sensorsType == "ZLLSwitch" else "", "uniqueid": uniqueid}
    return(new_sensor_id)

def sendEmail(triggered_sensor):
    import smtplib

    TEXT = "Sensor " + triggered_sensor + " was triggered while the alarm is active"
    # Prepare actual message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (bridge_config["alarm_config"]["mail_from"], ", ".join(bridge_config["alarm_config"]["mail_recipients"]), bridge_config["alarm_config"]["mail_subject"], TEXT)
    try:
        server_ssl = smtplib.SMTP_SSL(bridge_config["alarm_config"]["smtp_server"], bridge_config["alarm_config"]["smtp_port"])
        server_ssl.ehlo() # optional, called by login()
        server_ssl.login(bridge_config["alarm_config"]["mail_username"], bridge_config["alarm_config"]["mail_password"])
        server_ssl.sendmail(bridge_config["alarm_config"]["mail_from"], bridge_config["alarm_config"]["mail_recipients"], message)
        server_ssl.close()
        logging.debug("successfully sent the mail")

        return True
    except:
        logging.exception("failed to send mail")
        return False
#load config files
try:
    with open(cwd +'/config.json', 'r') as fp:
        bridge_config = json.load(fp)
        logging.debug("Config loaded")
except Exception:
    logging.exception("CRITICAL! Config file was not loaded")
    sys.exit(1)

def resourceRecycle():
    sleep(5) #give time to application to delete all resources, then start the cleanup
    resourcelinks = {"groups": [],"lights": [], "sensors": [], "rules": [], "scenes": [], "schedules": []}
    for resourcelink in bridge_config["resourcelinks"].keys():
        for link in bridge_config["resourcelinks"][resourcelink]["links"]:
            link_parts = link.split("/")
            resourcelinks[link_parts[1]].append(link_parts[2])

    for resource in resourcelinks.keys():
        for key in list(bridge_config[resource]):
            if "recycle" in bridge_config[resource][key] and bridge_config[resource][key]["recycle"] and key not in resourcelinks[resource]:
                logging.debug("delete " + resource + " / " + key)
                del bridge_config[resource][key]


def loadConfig():  #load and configure alarm virtual light
    if bridge_config["alarm_config"]["mail_username"] != "":
        logging.debug("E-mail account configured")
        if "virtual_light" not in bridge_config["alarm_config"]:
            logging.debug("Send test email")
            if sendEmail("dummy test"):
                logging.debug("Mail succesfully sent\nCreate alarm virtual light")
                new_light_id = nextFreeId(bridge_config, "lights")
                bridge_config["lights"][new_light_id] = {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.690456, 0.295907], "ct": 461, "alert": "none", "effect": "none", "colormode": "xy", "reachable": True}, "type": "Extended color light", "name": "Alarm", "uniqueid": "1234567ffffff", "modelid": "LLC012", "swversion": "66009461"}
                bridge_config["alarm_config"]["virtual_light"] = new_light_id
            else:
                logging.debug("Mail test failed")
loadConfig()

def saveConfig(filename='config.json'):
    with open(cwd + '/' + filename, 'w') as fp:
        json.dump(bridge_config, fp, sort_keys=True, indent=4, separators=(',', ': '))
    if docker:
        Popen(["cp", cwd + '/' + filename, cwd + '/' + 'export/'])

def generateSensorsState():
    for sensor in bridge_config["sensors"]:
        if sensor not in sensors_state and "state" in bridge_config["sensors"][sensor]:
            sensors_state[sensor] = {"state": {}}
            for key in bridge_config["sensors"][sensor]["state"].keys():
                if key in ["lastupdated", "presence", "flag", "dark", "daylight", "status"]:
                    sensors_state[sensor]["state"].update({key: datetime.now()})

generateSensorsState()

ip_pices = getIpAddress().split(".")
bridge_config["config"]["ipaddress"] = getIpAddress()
bridge_config["config"]["gateway"] = ip_pices[0] + "." +  ip_pices[1] + "." + ip_pices[2] + ".1"
bridge_config["config"]["mac"] = mac[0] + mac[1] + ":" + mac[2] + mac[3] + ":" + mac[4] + mac[5] + ":" + mac[6] + mac[7] + ":" + mac[8] + mac[9] + ":" + mac[10] + mac[11]
bridge_config["config"]["bridgeid"] = (mac[:6] + 'FFFE' + mac[6:]).upper()


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
                        pices = schedule_time.split('/T')
                        if int(pices[0][1:]) & (1 << 6 - datetime.today().weekday()):
                            if pices[1] == datetime.now().strftime("%H:%M:%S"):
                                logging.debug("execute schedule: " + schedule + " withe delay " + str(delay))
                                sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                    elif schedule_time.startswith("PT"):
                        timmer = schedule_time[2:]
                        (h, m, s) = timmer.split(':')
                        d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                        if bridge_config["schedules"][schedule]["starttime"] == (datetime.utcnow() - d).strftime("%Y-%m-%dT%H:%M:%S"):
                            logging.debug("execute timmer: " + schedule + " withe delay " + str(delay))
                            sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                            bridge_config["schedules"][schedule]["status"] = "disabled"
                    else:
                        if schedule_time == datetime.now().strftime("%Y-%m-%dT%H:%M:%S"):
                            logging.debug("execute schedule: " + schedule + " withe delay " + str(delay))
                            sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                            if bridge_config["schedules"][schedule]["autodelete"]:
                                del bridge_config["schedules"][schedule]
            except Exception as e:
                logging.debug("Exception while processing the schedule " + schedule + " | " + str(e))

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
        logging.debug("current scene not found, reset to zero")
        if len(group_scenes) != 0:
            matched_scene = group_scenes[0]
        else:
            logging.debug("error, no scenes found")
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
    logging.debug("matched scene " + bridge_config["scenes"][matched_scene]["name"])

    for light in bridge_config["scenes"][matched_scene]["lights"]:
        bridge_config["lights"][light]["state"].update(bridge_config["scenes"][matched_scene]["lightstates"][light])
        if "xy" in bridge_config["scenes"][matched_scene]["lightstates"][light]:
            bridge_config["lights"][light]["state"]["colormode"] = "xy"
        elif "ct" in bridge_config["scenes"][matched_scene]["lightstates"][light]:
            bridge_config["lights"][light]["state"]["colormode"] = "ct"
        elif "hue" or "sat" in bridge_config["scenes"][matched_scene]["lightstates"][light]:
            bridge_config["lights"][light]["state"]["colormode"] = "hs"
        sendLightRequest(light, bridge_config["scenes"][matched_scene]["lightstates"][light])
        updateGroupStats(light)


def checkRuleConditions(rule, sensor, current_time, ignore_ddx=False):
    ddx = 0
    sensor_found = False
    ddx_sensor = []
    for condition in bridge_config["rules"][rule]["conditions"]:
        try:
            url_pices = condition["address"].split('/')
            if url_pices[1] == "sensors" and sensor == url_pices[2]:
                sensor_found = True
            if condition["operator"] == "eq":
                if condition["value"] == "true":
                    if not bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]:
                        return [False, 0]
                elif condition["value"] == "false":
                    if bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]:
                        return [False, 0]
                else:
                    if not int(bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]) == int(condition["value"]):
                        return [False, 0]
            elif condition["operator"] == "gt":
                if not int(bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]) > int(condition["value"]):
                    return [False, 0]
            elif condition["operator"] == "lt":
                if not int(bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]) < int(condition["value"]):
                    return [False, 0]
            elif condition["operator"] == "dx":
                if not sensors_state[url_pices[2]][url_pices[3]][url_pices[4]] == current_time:
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
                if not sensors_state[url_pices[2]][url_pices[3]][url_pices[4]] == current_time:
                        return [False, 0]
                else:
                    ddx = int(condition["value"][2:4]) * 3600 + int(condition["value"][5:7]) * 60 + int(condition["value"][-2:])
                    ddx_sensor = url_pices
        except Exception as e:
            logging.debug("rule " + rule + " failed, reason:" + str(e))


    if sensor_found:
        return [True, ddx, ddx_sensor]
    else:
        return [False]

def ddxRecheck(rule, sensor, current_time, ddx_delay, ddx_sensor):
    for x in range(ddx_delay):
        if current_time != sensors_state[ddx_sensor[2]][ddx_sensor[3]][ddx_sensor[4]]:
            logging.debug("ddx rule " + rule + " canceled after " + str(x) + " seconds")
            return # rule not valid anymore because sensor state changed while waiting for ddx delay
        sleep(1)
    current_time = datetime.now()
    rule_state = checkRuleConditions(rule, sensor, current_time, True)
    if rule_state[0]: #if all conditions are meet again
        logging.debug("delayed rule " + rule + " is triggered")
        bridge_config["rules"][rule]["lasttriggered"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
        bridge_config["rules"][rule]["timestriggered"] += 1
        for action in bridge_config["rules"][rule]["actions"]:
            sendRequest("/api/" + bridge_config["rules"][rule]["owner"] + action["address"], action["method"], json.dumps(action["body"]))

def rulesProcessor(sensor, current_time):
    bridge_config["config"]["localtime"] = current_time.strftime("%Y-%m-%dT%H:%M:%S") #required for operator dx to address /config/localtime
    actionsToExecute = []
    for rule in bridge_config["rules"].keys():
        if bridge_config["rules"][rule]["status"] == "enabled":
            rule_result = checkRuleConditions(rule, sensor, current_time)
            if rule_result[0]:
                if rule_result[1] == 0: #is not ddx rule
                    logging.debug("rule " + rule + " is triggered")
                    bridge_config["rules"][rule]["lasttriggered"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
                    bridge_config["rules"][rule]["timestriggered"] += 1
                    for action in bridge_config["rules"][rule]["actions"]:
                        actionsToExecute.append(action)
                else: #if ddx rule
                    logging.debug("ddx rule " + rule + " will be re validated after " + str(rule_result[1]) + " seconds")
                    Thread(target=ddxRecheck, args=[rule, sensor, current_time, rule_result[1], rule_result[2]]).start()
    for action in actionsToExecute:
        sendRequest("/api/" +    list(bridge_config["config"]["whitelist"])[0] + action["address"], action["method"], json.dumps(action["body"]))

def sendRequest(url, method, data, timeout=3, delay=0):
    if delay != 0:
        sleep(delay)
    if not url.startswith( 'http://' ):
        url = "http://127.0.0.1" + url
    head = {"Content-type": "application/json"}
    if method == "POST":
        response = requests.post(url, data=bytes(data, "utf8"), timeout=timeout, headers=head)
        return response.text
    elif method == "PUT":
        response = requests.put(url, data=bytes(data, "utf8"), timeout=timeout, headers=head)
        return response.text
    elif method == "GET":
        response = requests.get(url, timeout=timeout, headers=head)
        return response.text



def sendLightRequest(light, data):
    payload = {}
    if light in bridge_config["lights_address"]:
        protocol_name = bridge_config["lights_address"][light]["protocol"]
        for protocol in protocols:
            if "protocols." + protocol_name == protocol.__name__:
                try:
                    light_state = protocol.set_light(bridge_config["lights_address"][light]["ip"], bridge_config["lights"][light], data)
                except:
                    bridge_config["lights"][light]["state"]["reachable"] = False
                    logging.exception("request error")
                return

        if bridge_config["lights_address"][light]["protocol"] == "native": #ESP8266 light or strip
            url = "http://" + bridge_config["lights_address"][light]["ip"] + "/set?light=" + str(bridge_config["lights_address"][light]["light_nr"])
            method = 'GET'
            for key, value in data.items():
                if key == "xy":
                    url += "&x=" + str(value[0]) + "&y=" + str(value[1])
                else:
                    url += "&" + key + "=" + str(value)
        elif bridge_config["lights_address"][light]["protocol"] in ["hue","deconz"]: #Original Hue light or Deconz light
            url = "http://" + bridge_config["lights_address"][light]["ip"] + "/api/" + bridge_config["lights_address"][light]["username"] + "/lights/" + bridge_config["lights_address"][light]["light_id"] + "/state"
            method = 'PUT'
            payload.update(data)

        elif bridge_config["lights_address"][light]["protocol"] == "domoticz": #Domoticz protocol
            url = "http://" + bridge_config["lights_address"][light]["ip"] + "/json.htm?type=command&param=switchlight&idx=" + bridge_config["lights_address"][light]["light_id"]
            method = 'GET'
            for key, value in data.items():
                if key == "on":
                    if value:
                        url += "&switchcmd=On"
                    else:
                        url += "&switchcmd=Off"
                elif key == "bri":
                    url += "&switchcmd=Set%20Level&level=" + str(round(float(value)/255*100)) # domoticz range from 0 to 100 (for zwave devices) instead of 0-255 of bridge

        elif bridge_config["lights_address"][light]["protocol"] == "jeedom": #Jeedom protocol
            url = "http://" + bridge_config["lights_address"][light]["ip"] + "/core/api/jeeApi.php?apikey=" + bridge_config["lights_address"][light]["light_api"] + "&type=cmd&id="
            method = 'GET'
            for key, value in data.items():
                if key == "on":
                    if value:
                        url += bridge_config["lights_address"][light]["light_on"]
                    else:
                        url += bridge_config["lights_address"][light]["light_off"]
                elif key == "bri":
                    url += bridge_config["lights_address"][light]["light_slider"] + "&slider=" + str(round(float(value)/255*100)) # jeedom range from 0 to 100 (for zwave devices) instead of 0-255 of bridge

        elif bridge_config["lights_address"][light]["protocol"] == "milight": #MiLight bulb
            url = "http://" + bridge_config["lights_address"][light]["ip"] + "/gateways/" + bridge_config["lights_address"][light]["device_id"] + "/" + bridge_config["lights_address"][light]["mode"] + "/" + str(bridge_config["lights_address"][light]["group"])
            method = 'PUT'
            for key, value in data.items():
                if key == "on":
                    payload["status"] = value
                elif key == "bri":
                    payload["brightness"] = value
                elif key == "ct":
                    payload["color_temp"] = int(value / 1.6 + 153)
                elif key == "hue":
                    payload["hue"] = value / 180
                elif key == "sat":
                    payload["saturation"] = value * 100 / 255
                elif key == "xy":
                    payload["color"] = {}
                    (payload["color"]["r"], payload["color"]["g"], payload["color"]["b"]) = convert_xy(value[0], value[1], bridge_config["lights"][light]["state"]["bri"])
            logging.debug(json.dumps(payload))

        elif bridge_config["lights_address"][light]["protocol"] == "ikea_tradfri": #IKEA Tradfri bulb
            url = "coaps://" + bridge_config["lights_address"][light]["ip"] + ":5684/15001/" + str(bridge_config["lights_address"][light]["device_id"])
            for key, value in data.items():
                if key == "on":
                    payload["5850"] = int(value)
                elif key == "transitiontime":
                    payload["5712"] = value
                elif key == "bri":
                    payload["5851"] = value
                elif key == "ct":
                    if value < 270:
                        payload["5706"] = "f5faf6"
                    elif value < 385:
                        payload["5706"] = "f1e0b5"
                    else:
                        payload["5706"] = "efd275"
                elif key == "xy":
                    payload["5709"] = int(value[0] * 65535)
                    payload["5710"] = int(value[1] * 65535)
            if "hue" in data or "sat" in data:
                if("hue" in data):
                    hue = data["hue"]
                else:
                    hue = bridge_config["lights"][light]["state"]["hue"]
                if("sat" in data):
                    sat = data["sat"]
                else:
                    sat = bridge_config["lights"][light]["state"]["sat"]
                if("bri" in data):
                    bri = data["bri"]
                else:
                    bri = bridge_config["lights"][light]["state"]["bri"]
                rgbValue = hsv_to_rgb(hue, sat, bri)
                xyValue = convert_rgb_xy(rgbValue[0], rgbValue[1], rgbValue[2])
                payload["5709"] = int(xyValue[0] * 65535)
                payload["5710"] = int(xyValue[1] * 65535)
            if "5850" in payload and payload["5850"] == 0:
                payload.clear() #setting brightnes will turn on the ligh even if there was a request to power off
                payload["5850"] = 0
            elif "5850" in payload and "5851" in payload: #when setting brightness don't send also power on command
                del payload["5850"]
        elif bridge_config["lights_address"][light]["protocol"] == "flex":
            msg = bytearray()
            if "on" in data:
                if data["on"]:
                    msg = bytearray([0x71, 0x23, 0x8a, 0x0f])
                else:
                    msg = bytearray([0x71, 0x24, 0x8a, 0x0f])
                checksum = sum(msg) & 0xFF
                msg.append(checksum)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
                sock.sendto(msg, (bridge_config["lights_address"][light]["ip"], 48899))
            if ("bri" in data and bridge_config["lights"][light]["state"]["colormode"] == "xy") or "xy" in data:
                logging.debug(pretty_json(data))
                bri = data["bri"] if "bri" in data else bridge_config["lights"][light]["state"]["bri"]
                xy = data["xy"] if "xy" in data else bridge_config["lights"][light]["state"]["xy"]
                rgb = convert_xy(xy[0], xy[1], bri)
                msg = bytearray([0x41, rgb[0], rgb[1], rgb[2], 0x00, 0xf0, 0x0f])
                checksum = sum(msg) & 0xFF
                msg.append(checksum)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
                sock.sendto(msg, (bridge_config["lights_address"][light]["ip"], 48899))
            elif ("bri" in data and bridge_config["lights"][light]["state"]["colormode"] == "ct") or "ct" in data:
                bri = data["bri"] if "bri" in data else bridge_config["lights"][light]["state"]["bri"]
                msg = bytearray([0x41, 0x00, 0x00, 0x00, bri, 0x0f, 0x0f])
                checksum = sum(msg) & 0xFF
                msg.append(checksum)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
                sock.sendto(msg, (bridge_config["lights_address"][light]["ip"], 48899))

        try:
            if bridge_config["lights_address"][light]["protocol"] == "ikea_tradfri":
                if "5712" not in payload:
                    payload["5712"] = 4 #If no transition add one, might also add check to prevent large transitiontimes
                    check_output("./coap-client-linux -m put -u \"" + bridge_config["lights_address"][light]["identity"] + "\" -k \"" + bridge_config["lights_address"][light]["preshared_key"] + "\" -e '{ \"3311\": [" + json.dumps(payload) + "] }' \"" + url + "\"", shell=True)
            elif bridge_config["lights_address"][light]["protocol"] in ["hue", "deconz"]:
                color = {}
                if "xy" in payload:
                    color["xy"] = payload["xy"]
                    del(payload["xy"])
                elif "ct" in payload:
                    color["ct"] = payload["ct"]
                    del(payload["ct"])
                elif "hue" in payload:
                    color["hue"] = payload["hue"]
                    del(payload["hue"])
                elif "sat" in payload:
                    color["sat"] = payload["sat"]
                    del(payload["sat"])
                if len(payload) != 0:
                    sendRequest(url, method, json.dumps(payload))
                    if bridge_config["lights_address"][light]["protocol"] == "deconz":
                        sleep(0.7)
                if len(color) != 0:
                    sendRequest(url, method, json.dumps(color))
            else:
                sendRequest(url, method, json.dumps(payload))
        except:
            bridge_config["lights"][light]["state"]["reachable"] = False
            logging.debug("request error")
        else:
            bridge_config["lights"][light]["state"]["reachable"] = True
            logging.debug("LightRequest: " + url)

def updateGroupStats(light): #set group stats based on lights status in that group
    for group in bridge_config["groups"]:
        if "lights" in bridge_config["groups"][group] and light in bridge_config["groups"][group]["lights"]:
            for key, value in bridge_config["lights"][light]["state"].items():
                if key in ["bri", "xy", "ct", "hue", "sat"]:
                    bridge_config["groups"][group]["action"][key] = value
            any_on = False
            all_on = True
            for group_light in bridge_config["groups"][group]["lights"]:
                if bridge_config["lights"][group_light]["state"]["on"]:
                    any_on = True
                else:
                    all_on = False
            bridge_config["groups"][group]["state"] = {"any_on": any_on, "all_on": all_on,}
            bridge_config["groups"][group]["action"]["on"] = any_on


def scanForLights(): #scan for ESP8266 lights and strips
    Thread(target=yeelight.discover, args=[bridge_config, new_lights]).start()
    Thread(target=tasmota.discover, args=[bridge_config, new_lights]).start()
    #return all host that listen on port 80
    device_ips = check_output("nmap  " + getIpAddress() + "/24 -p80 --open -n | grep report | cut -d ' ' -f5", shell=True).decode('utf-8').rstrip("\n").split("\n")
    logging.debug(pretty_json(device_ips))
    del device_ips[-1] #delete last empty element in list
    for ip in device_ips:
        try:
            if ip != getIpAddress():
                response = requests.get("http://" + ip + "/detect", timeout=3)
                if response.status_code == 200:
                    device_data = json.loads(response.text)
                    logging.debug(pretty_json(device_data))
                    if "hue" in device_data:
                        logging.debug(ip + " is a hue " + device_data['hue'])
                        device_exist = False
                        for light in bridge_config["lights_address"].keys():
                            if bridge_config["lights_address"][light]["protocol"] == "native" and bridge_config["lights_address"][light]["mac"] == device_data["mac"]:
                                device_exist = True
                                bridge_config["lights_address"][light]["ip"] = ip
                        if not device_exist:
                            light_name = "Hue " + device_data["hue"] + " " + device_data["modelid"]
                            if "name" in device_data:
                                light_name = device_data["name"]
                            logging.debug("Add new light: " + light_name)
                            for x in range(1, int(device_data["lights"]) + 1):
                                new_light_id = nextFreeId(bridge_config, "lights")
                                bridge_config["lights"][new_light_id] = {"state": light_types[device_data["modelid"]]["state"], "type": light_types[device_data["modelid"]]["type"], "name": light_name if x == 1 else light_name + " " + str(x), "uniqueid": "00:17:88:01:00:" + hex(random.randrange(0,255))[2:] + ":" + hex(random.randrange(0,255))[2:] + ":" + hex(random.randrange(0,255))[2:] + "-0b", "modelid": device_data["modelid"], "manufacturername": "Philips", "swversion": light_types[device_data["modelid"]]["swversion"]}
                                new_lights.update({new_light_id: {"name": light_name if x == 1 else light_name + " " + str(x)}})
                                bridge_config["lights_address"][new_light_id] = {"ip": ip, "light_nr": x, "protocol": "native", "mac": device_data["mac"]}
        except Exception as e:
            logging.debug("ip " + ip + " is unknow device, " + str(e))
    scanDeconz()
    scanTradfri()
    saveConfig()


def syncWithLights(): #update Hue Bridge lights states
    while True:
        logging.debug("sync with lights")
        for light in bridge_config["lights_address"]:
            try:
                protocol_name = bridge_config["lights_address"][light]["protocol"]
                for protocol in protocols:
                    if "protocols." + protocol_name == protocol.__name__:
                        light_state = protocol.get_light_state(bridge_config["lights_address"][light]["ip"], bridge_config["lights"][light])
                        bridge_config["lights"][light]["state"].update(light_state)
                if bridge_config["lights_address"][light]["protocol"] == "native":
                    light_data = json.loads(sendRequest("http://" + bridge_config["lights_address"][light]["ip"] + "/get?light=" + str(bridge_config["lights_address"][light]["light_nr"]), "GET", "{}"))
                    bridge_config["lights"][light]["state"].update(light_data)
                elif bridge_config["lights_address"][light]["protocol"] == "hue":
                    light_data = json.loads(sendRequest("http://" + bridge_config["lights_address"][light]["ip"] + "/api/" + bridge_config["lights_address"][light]["username"] + "/lights/" + bridge_config["lights_address"][light]["light_id"], "GET", "{}"))
                    bridge_config["lights"][light]["state"].update(light_data["state"])
                elif bridge_config["lights_address"][light]["protocol"] == "ikea_tradfri":
                    light_data = json.loads(check_output("./coap-client-linux -m get -u \"" + bridge_config["lights_address"][light]["identity"] + "\" -k \"" + bridge_config["lights_address"][light]["preshared_key"] + "\" \"coaps://" + bridge_config["lights_address"][light]["ip"] + ":5684/15001/" + str(bridge_config["lights_address"][light]["device_id"]) +"\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
                    bridge_config["lights"][light]["state"]["on"] = bool(light_data["3311"][0]["5850"])
                    bridge_config["lights"][light]["state"]["bri"] = light_data["3311"][0]["5851"]
                    if "5706" in light_data["3311"][0]:
                        if light_data["3311"][0]["5706"] == "f5faf6":
                            bridge_config["lights"][light]["state"]["ct"] = 170
                        elif light_data["3311"][0]["5706"] == "f1e0b5":
                            bridge_config["lights"][light]["state"]["ct"] = 320
                        elif light_data["3311"][0]["5706"] == "efd275":
                            bridge_config["lights"][light]["state"]["ct"] = 470
                    else:
                        bridge_config["lights"][light]["state"]["ct"] = 470
                elif bridge_config["lights_address"][light]["protocol"] == "milight":
                    light_data = json.loads(sendRequest("http://" + bridge_config["lights_address"][light]["ip"] + "/gateways/" + bridge_config["lights_address"][light]["device_id"] + "/" + bridge_config["lights_address"][light]["mode"] + "/" + str(bridge_config["lights_address"][light]["group"]), "GET", "{}"))
                    if light_data["state"] == "ON":
                        bridge_config["lights"][light]["state"]["on"] = True
                    else:
                        bridge_config["lights"][light]["state"]["on"] = False
                    if "brightness" in light_data:
                        bridge_config["lights"][light]["state"]["bri"] = light_data["brightness"]
                    if "color_temp" in light_data:
                        bridge_config["lights"][light]["state"]["colormode"] = "ct"
                        bridge_config["lights"][light]["state"]["ct"] = light_data["color_temp"] * 1.6
                    elif "bulb_mode" in light_data and light_data["bulb_mode"] == "color":
                        bridge_config["lights"][light]["state"]["colormode"] = "hs"
                        bridge_config["lights"][light]["state"]["hue"] = light_data["hue"] * 180
                        bridge_config["lights"][light]["state"]["sat"] = int(light_data["saturation"] * 2.54)
                elif bridge_config["lights_address"][light]["protocol"] == "domoticz": #domoticz protocol
                    light_data = json.loads(sendRequest("http://" + bridge_config["lights_address"][light]["ip"] + "/json.htm?type=devices&rid=" + bridge_config["lights_address"][light]["light_id"], "GET", "{}"))
                    if light_data["result"][0]["Status"] == "Off":
                         bridge_config["lights"][light]["state"]["on"] = False
                    else:
                         bridge_config["lights"][light]["state"]["on"] = True
                    bridge_config["lights"][light]["state"]["bri"] = str(round(float(light_data["result"][0]["Level"])/100*255))
                elif bridge_config["lights_address"][light]["protocol"] == "jeedom": #jeedom protocol
                    light_data = json.loads(sendRequest("http://" + bridge_config["lights_address"][light]["ip"] + "/core/api/jeeApi.php?apikey=" + bridge_config["lights_address"][light]["light_api"] + "&type=cmd&id=" + bridge_config["lights_address"][light]["light_id"], "GET", "{}"))
                    if light_data == 0:
                         bridge_config["lights"][light]["state"]["on"] = False
                    else:
                         bridge_config["lights"][light]["state"]["on"] = True
                    bridge_config["lights"][light]["state"]["bri"] = str(round(float(light_data)/100*255))

                bridge_config["lights"][light]["state"]["reachable"] = True
                updateGroupStats(light)
            except:
                bridge_config["lights"][light]["state"]["reachable"] = False
                bridge_config["lights"][light]["state"]["on"] = False
                logging.exception("light " + light + " is unreachable")
        sleep(10) #wait at last 10 seconds before next sync
        i = 0
        while i < 300: #sync with lights every 300 seconds or instant if one user is connected
            for user in bridge_config["config"]["whitelist"].keys():
                if bridge_config["config"]["whitelist"][user]["last use date"] == datetime.now().strftime("%Y-%m-%dT%H:%M:%S"):
                    i = 300
                    break
            sleep(1)



def longPressButton(sensor, buttonevent):
    logging.debug("long press detected")
    sleep(1)
    while bridge_config["sensors"][sensor]["state"]["buttonevent"] == buttonevent:
        logging.debug("still pressed")
        current_time =  datetime.now()
        sensors_state[sensor]["state"]["lastupdated"] = current_time
        rulesProcessor(sensor, current_time)
        sleep(0.5)
    return


def motionDetected(sensor):
    logging.debug("monitoring esp8266 motion sensor")
    while bridge_config["sensors"][sensor]["state"]["presence"] == True:
        if datetime.utcnow() - datetime.strptime(bridge_config["sensors"][sensor]["state"]["lastupdated"], "%Y-%m-%dT%H:%M:%S") > timedelta(seconds=30):
            bridge_config["sensors"][sensor]["state"]["presence"] = False
            bridge_config["sensors"][sensor]["state"]["lastupdated"] =  datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            current_time =  datetime.now()
            sensors_state[sensor]["state"]["presence"] = current_time
            rulesProcessor(sensor, current_time)
        sleep(1)
    return


def scanTradfri():
    if "tradfri" in bridge_config:
        tradri_devices = json.loads(check_output("./coap-client-linux -m get -u \"" + bridge_config["tradfri"]["identity"] + "\" -k \"" + bridge_config["tradfri"]["psk"] + "\" \"coaps://" + bridge_config["tradfri"]["ip"] + ":5684/15001\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
        logging.debug(pretty_json(tradri_devices))
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
                    logging.debug("register tradfi light " + device_parameters["9001"])
                    new_light_id = nextFreeId(bridge_config, "lights")
                    bridge_config["lights"][new_light_id] = {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}, "type": "Extended color light", "name": device_parameters["9001"], "uniqueid": "1234567" + str(device), "modelid": "LLM010", "swversion": "66009461"}
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
            logging.debug(("deconz websocket disconnected", code, reason))
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

                            if bridge_config["sensors"]["1"]["modelid"] == "PHDL00" and bridge_config["sensors"]["1"]["state"]["daylight"]:
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

                        bridge_config["sensors"][bridge_sensor_id]["state"].update(message["state"])
                        current_time = datetime.now()
                        for key in message["state"].keys():
                            sensors_state[bridge_sensor_id]["state"][key] = current_time
                        rulesProcessor(bridge_sensor_id, current_time)
                        if "buttonevent" in message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["modelid"] in ["TRADFRI remote control","RWL021"]:
                            if message["state"]["buttonevent"] in [2001, 3001, 4001, 5001]:
                                Thread(target=longPressButton, args=[bridge_sensor_id, message["state"]["buttonevent"]]).start()
                        if "presence" in message["state"] and message["state"]["presence"] and "virtual_light" in bridge_config["alarm_config"] and bridge_config["lights"][bridge_config["alarm_config"]["virtual_light"]]["state"]["on"]:
                            sendEmail(bridge_config["sensors"][bridge_sensor_id]["name"])
                            bridge_config["alarm_config"]["virtual_light"]
                    elif "config" in message and bridge_config["sensors"][bridge_sensor_id]["config"]["on"]:
                        bridge_config["sensors"][bridge_sensor_id]["config"].update(message["config"])
                elif message["r"] == "lights":
                    bridge_light_id = bridge_config["deconz"]["lights"][message["id"]]["bridgeid"]
                    if "state" in message:
                        bridge_config["lights"][bridge_light_id]["state"].update(message["state"])
                        updateGroupStats(bridge_light_id)
            except Exception as e:
                logging.debug("unable to process the request" + str(e))

    try:
        ws = EchoClient('ws://127.0.0.1:' + str(bridge_config["deconz"]["websocketport"]))
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()

def scanDeconz():
    if not bridge_config["deconz"]["enabled"]:
        if "username" not in bridge_config["deconz"]:
            try:
                registration = json.loads(sendRequest("http://127.0.0.1:" + str(bridge_config["deconz"]["port"]) + "/api", "POST", "{\"username\": \"283145a4e198cc6535\", \"devicetype\":\"Hue Emulator\"}"))
            except:
                logging.debug("registration fail, is the link button pressed?")
                return
            if "success" in registration[0]:
                bridge_config["deconz"]["username"] = registration[0]["success"]["username"]
                bridge_config["deconz"]["enabled"] = True
    if "username" in bridge_config["deconz"]:
        deconz_config = json.loads(sendRequest("http://127.0.0.1:" + str(bridge_config["deconz"]["port"]) + "/api/" + bridge_config["deconz"]["username"] + "/config", "GET", "{}"))
        bridge_config["deconz"]["websocketport"] = deconz_config["websocketport"]

        #lights
        deconz_lights = json.loads(sendRequest("http://127.0.0.1:" + str(bridge_config["deconz"]["port"]) + "/api/" + bridge_config["deconz"]["username"] + "/lights", "GET", "{}"))
        for light in deconz_lights:
            if light not in bridge_config["deconz"]["lights"] and "modelid" in deconz_lights[light]:
                new_light_id = nextFreeId(bridge_config, "lights")
                logging.debug("register new light " + new_light_id)
                bridge_config["lights"][new_light_id] = deconz_lights[light]
                bridge_config["lights_address"][new_light_id] = {"username": bridge_config["deconz"]["username"], "light_id": light, "ip": "127.0.0.1:" + str(bridge_config["deconz"]["port"]), "protocol": "deconz"}
                bridge_config["deconz"]["lights"][light] = {"bridgeid": new_light_id, "modelid": deconz_lights[light]["modelid"], "type": deconz_lights[light]["type"]}



        #sensors
        deconz_sensors = json.loads(sendRequest("http://127.0.0.1:" + str(bridge_config["deconz"]["port"]) + "/api/" + bridge_config["deconz"]["username"] + "/sensors", "GET", "{}"))
        for sensor in deconz_sensors:
            if sensor not in bridge_config["deconz"]["sensors"] and "modelid" in deconz_sensors[sensor]:
                new_sensor_id = nextFreeId(bridge_config, "sensors")
                if deconz_sensors[sensor]["modelid"] in ["TRADFRI remote control", "TRADFRI wireless dimmer"]:
                    logging.debug("register new " + deconz_sensors[sensor]["modelid"])
                    bridge_config["sensors"][new_sensor_id] = {"config": deconz_sensors[sensor]["config"], "manufacturername": deconz_sensors[sensor]["manufacturername"], "modelid": deconz_sensors[sensor]["modelid"], "name": deconz_sensors[sensor]["name"], "state": deconz_sensors[sensor]["state"], "type": deconz_sensors[sensor]["type"], "uniqueid": deconz_sensors[sensor]["uniqueid"]}
                    if "swversion" in  deconz_sensors[sensor]:
                        bridge_config["sensors"][new_sensor_id]["swversion"] = deconz_sensors[sensor]["swversion"]
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                elif deconz_sensors[sensor]["modelid"] == "TRADFRI motion sensor":
                    logging.debug("register TRADFRI motion sensor as Philips Motion Sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"], "lightsensor": "internal"}

                elif deconz_sensors[sensor]["modelid"] == "lumi.sensor_motion.aq2":
                    if deconz_sensors[sensor]["type"] == "ZHALightLevel":
                        logging.debug("register new Xiaomi light sensor")
                        bridge_config["sensors"][new_sensor_id] = {"name": "Hue ambient light sensor 1", "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:], "type": "ZLLLightLevel", "swversion": "6.1.0.18912", "state": {"dark": True, "daylight": False, "lightlevel": 6000, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False,"battery": 100, "reachable": True, "alert": "none", "tholddark": 21597, "tholdoffset": 7000, "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
                        bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue temperature sensor 1", "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:-1] + "2", "type": "ZLLTemperature", "swversion": "6.1.0.18912", "state": {"temperature": None, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False, "battery": 100, "reachable": True, "alert":"none", "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
                        bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                    elif deconz_sensors[sensor]["type"] == "ZHAPresence":
                        logging.debug("register new Xiaomi motion sensor")
                        bridge_config["sensors"][new_sensor_id] = {"name": deconz_sensors[sensor]["name"], "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:], "type": "ZLLPresence", "swversion": "6.1.0.18912", "state": {"lastupdated": "none", "presence": None}, "manufacturername": "Philips", "config": {"on": False,"battery": 100,"reachable": True, "alert": "lselect", "ledindication": False, "usertest": False, "sensitivity": 2, "sensitivitymax": 2,"pending": []}, "modelid": "SML001"}
                        bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                elif deconz_sensors[sensor]["modelid"] == "lumi.sensor_motion":
                    logging.debug("register Xiaomi Motion sensor w/o light sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                else:
                    bridge_config["sensors"][new_sensor_id] = deconz_sensors[sensor]
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}

            else: #temporary patch for config compatibility with new release
                bridge_config["deconz"]["sensors"][sensor]["modelid"] = deconz_sensors[sensor]["modelid"]
                bridge_config["deconz"]["sensors"][sensor]["type"] = deconz_sensors[sensor]["type"]
        generateSensorsState()

        if "websocketport" in bridge_config["deconz"]:
            logging.debug("Starting deconz websocket")
            Thread(target=websocketClient).start()


def updateAllLights():
    ## apply last state on startup to all bulbs, usefull if there was a power outage
    for light in bridge_config["lights_address"]:
        payload = {}
        payload["on"] = bridge_config["lights"][light]["state"]["on"]
        if payload["on"] and "bri" in bridge_config["lights"][light]["state"]:
            payload["bri"] = bridge_config["lights"][light]["state"]["bri"]
        sendLightRequest(light, payload)
        sleep(0.5)
        logging.debug("update status for light " + light)

def manageDeviceLights(lights_state):
    protocol = bridge_config["lights_address"][list(lights_state.keys())[0]]["protocol"]
    for light in lights_state.keys():
        if protocol in ["native","milight"]:
            sendLightRequest(light, lights_state[light])
            if protocol == "milight": #hotfix to avoid milight hub overload
                sleep(0.05)
        else:
            Thread(target=sendLightRequest, args=[light, lights_state[light]]).start()
            sleep(0.1)



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
                bridge_config["groups"][grp]["state"]["bri"] = bridge_config["groups"][grp]["action"]["bri"]
                del state["bri_inc"]
                state.update({"bri": bridge_config["groups"][grp]["action"]["bri"]})
            elif "ct_inc" in state:
                bridge_config["groups"][grp]["action"]["ct"] += int(state["ct_inc"])
                if bridge_config["groups"][grp]["action"]["ct"] > 500:
                    bridge_config["groups"][grp]["action"]["ct"] = 500
                elif bridge_config["groups"][grp]["action"]["ct"] < 153:
                    bridge_config["groups"][grp]["action"]["ct"] = 153
                bridge_config["groups"][grp]["state"]["ct"] = bridge_config["groups"][grp]["action"]["ct"]
                del state["ct_inc"]
                state.update({"ct": bridge_config["groups"][grp]["action"]["ct"]})
            for light in bridge_config["groups"][grp]["lights"]:
                lightsData[light] = state
    else:
        lightsData = scene
    deviceIp = {}
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
        if "transitiontime" in lightsData[light]:
            del lightsData[light]["transitiontime"]
        bridge_config["lights"][light]["state"].update(lightsData[light])
    updateGroupStats(list(lightsData.keys())[0])


def groupZero(state):
    lightsData = {}
    for light in bridge_config["lights"].keys():
        if "virtual_light" not in bridge_config["alarm_config"] or light != bridge_config["alarm_config"]["virtual_light"]:
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

    import pytz, astral
    from astral import Astral, Location
    a = Astral()
    a.solar_depression = 'civil'
    loc = Location(('Current', bridge_config["config"]["timezone"].split("/")[1], float(bridge_config["sensors"]["1"]["config"]["lat"][:-1]), float(bridge_config["sensors"]["1"]["config"]["long"][:-1]), bridge_config["config"]["timezone"], 0))
    sun = loc.sun(date=datetime.now(), local=True)
    deltaSunset = sun['sunset'].replace(tzinfo=None) - datetime.now()
    deltaSunrise = sun['sunrise'].replace(tzinfo=None) - datetime.now()
    deltaSunsetOffset = deltaSunset.total_seconds() + bridge_config["sensors"]["1"]["config"]["sunsetoffset"] * 60
    deltaSunriseOffset = deltaSunrise.total_seconds() + bridge_config["sensors"]["1"]["config"]["sunriseoffset"] * 60
    logging.debug("deltaSunsetOffset: " + str(deltaSunsetOffset))
    logging.debug("deltaSunriseOffset: " + str(deltaSunriseOffset))
    current_time =  datetime.now()
    if deltaSunriseOffset < 0 and deltaSunsetOffset > 0:
        bridge_config["sensors"]["1"]["state"] = {"daylight":True,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        logging.debug("set daylight sensor to true")
    else:
        bridge_config["sensors"]["1"]["state"] = {"daylight":False,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        logging.debug("set daylight sensor to false")
    if deltaSunsetOffset > 0 and deltaSunsetOffset < 3600:
        logging.debug("will start the sleep for sunset")
        sleep(deltaSunsetOffset)
        logging.debug("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
        bridge_config["sensors"]["1"]["state"] = {"daylight":False,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        sensors_state["1"]["state"]["daylight"] = current_time
        rulesProcessor("1", current_time)
    if deltaSunriseOffset > 0 and deltaSunriseOffset < 3600:
        logging.debug("will start the sleep for sunrise")
        sleep(deltaSunriseOffset)
        logging.debug("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
        bridge_config["sensors"]["1"]["state"] = {"daylight":True,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        sensors_state["1"]["state"]["daylight"] = current_time
        rulesProcessor("1", current_time)


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
        self.end_headers()

    def _set_end_headers(self, data):
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        #Some older Philips Tv's sent non-standard HTTP GET requests with a Content-Lenght and a
        # body. The HTTP body needs to be consumed and ignored in order to request be handle correctly.
        self.read_http_request_body()

        if self.path == '/' or self.path == '/index.html':
            self._set_headers()
            f = open(cwd + '/web-ui/index.html')
            self._set_end_headers(bytes(f.read(), "utf8"))
        elif self.path == "/debug/clip.html":
            self._set_headers()
            f = open(cwd + '/clip.html', 'rb')
            self._set_end_headers(f.read())
        elif self.path == '/config.js':
            self._set_headers()
            #create a new user key in case none is available
            if len(bridge_config["config"]["whitelist"]) == 0:
                bridge_config["config"]["whitelist"]["web-ui-" + str(random.randrange(0, 99999))] = {"create date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),"last use date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),"name": "WegGui User"}
            self._set_end_headers(bytes('window.config = { API_KEY: "' + list(bridge_config["config"]["whitelist"])[0] + '",};', "utf8"))
        elif self.path.endswith((".css",".map",".png",".js")):
            self._set_headers()
            f = open(cwd + '/web-ui' + self.path, 'rb')
            self._set_end_headers(f.read())
        elif self.path == '/description.xml':
            self._set_headers()
            self._set_end_headers(bytes(description(bridge_config["config"]["ipaddress"], mac), "utf8"))
        elif self.path == '/save':
            self._set_headers()
            saveConfig()
            self._set_end_headers(bytes(json.dumps([{"success":{"configuration":"saved","filename":"/opt/hue-emulator/config.json"}}] ,separators=(',', ':')), "utf8"))
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
                bridge_config["lights"][new_light_id] = {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}, "type": "Extended color light", "name": "MiLight " + get_parameters["mode"][0] + " " + get_parameters["device_id"][0], "uniqueid": "1a2b3c4" + str(random.randrange(0, 99)), "modelid": "LCT001", "swversion": "66009461"}
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
                        bridge_config["linkbutton"]["lastlinkbuttonpushed"] = datetime.now().strftime("%s")
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
                    self._set_end_headers(bytes(self.headers.headers['Authorization'], "utf8"))
                    self._set_end_headers(bytes('not authenticated', "utf8"))
                    pass
            else:
                self._set_headers()
                get_parameters = parse_qs(urlparse(self.path).query)
                if "ip" in get_parameters:
                    response = json.loads(sendRequest("http://" + get_parameters["ip"][0] + "/api/", "POST", "{\"devicetype\":\"Hue Emulator\"}"))
                    if "success" in response[0]:
                        hue_lights = json.loads(sendRequest("http://" + get_parameters["ip"][0] + "/api/" + response[0]["success"]["username"] + "/lights", "GET", "{}"))
                        lights_found = 0
                        for hue_light in hue_lights:
                            new_light_id = nextFreeId(bridge_config, "lights")
                            bridge_config["lights"][new_light_id] = hue_lights[hue_light]
                            bridge_config["lights_address"][new_light_id] = {"username": response[0]["success"]["username"], "light_id": hue_light, "ip": get_parameters["ip"][0], "protocol": "hue"}
                            lights_found += 1
                        if lights_found == 0:
                            self._set_end_headers(bytes(webform_hue() + "<br> No lights where found", "utf8"))
                        else:
                            self._set_end_headers(bytes(webform_hue() + "<br> " + str(lights_found) + " lights where found", "utf8"))
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
                                    logging.debug("unable to delete the rule " + pices[2])
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
                            elif bridge_config["deconz"]["sensors"][key]["modelid"] == "TRADFRI motion sensor":
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
            logging.debug(pretty_json(get_parameters))
            if "devicetype" in get_parameters: #register device request
                sensor_is_new = True
                for sensor in bridge_config["sensors"]:
                    if "uniqueid" in bridge_config["sensors"][sensor] and bridge_config["sensors"][sensor]["uniqueid"].startswith(get_parameters["mac"][0]): # if sensor is already present
                        sensor_is_new = False
                if sensor_is_new:
                    logging.debug("registering new sensor " + get_parameters["devicetype"][0])
                    new_sensor_id = nextFreeId(bridge_config, "sensors")
                    if get_parameters["devicetype"][0] in ["ZLLSwitch","ZGPSwitch"]:
                        logging.debug(get_parameters["devicetype"][0])
                        addHueSwitch(get_parameters["mac"][0], get_parameters["devicetype"][0])
                    elif get_parameters["devicetype"][0] == "ZLLPresence":
                        logging.debug("ZLLPresence")
                        addHueMotionSensor(get_parameters["mac"][0])
                    generateSensorsState()
            else: #switch action request
                for sensor in bridge_config["sensors"]:
                    if "uniqueid" in bridge_config["sensors"][sensor] and bridge_config["sensors"][sensor]["uniqueid"].startswith(get_parameters["mac"][0]) and bridge_config["sensors"][sensor]["config"]["on"]: #match senser id based on mac address
                        logging.debug("match sensor " + str(sensor))
                        current_time = datetime.now()
                        if bridge_config["sensors"][sensor]["type"] == "ZLLSwitch" or bridge_config["sensors"][sensor]["type"] == "ZGPSwitch":
                            bridge_config["sensors"][sensor]["state"].update({"buttonevent": get_parameters["button"][0], "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                            sensors_state[sensor]["state"]["lastupdated"] = current_time
                        elif bridge_config["sensors"][sensor]["type"] == "ZLLPresence":
                            if bridge_config["sensors"][sensor]["state"]["presence"] != True:
                                bridge_config["sensors"][sensor]["state"]["presence"] = True
                                sensors_state[sensor]["state"]["presence"] = current_time
                                Thread(target=motionDetected, args=[sensor]).start()
                            bridge_config["sensors"][sensor]["state"]["lastupdated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

                        elif bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel":
                            if bridge_config["sensors"]["1"]["modelid"] == "PHDL00" and bridge_config["sensors"]["1"]["state"]["daylight"]:
                                bridge_config["sensors"][sensor]["state"]["lightlevel"] = 25000
                                bridge_config["sensors"][sensor]["state"]["dark"] = False
                            else:
                                bridge_config["sensors"][sensor]["state"]["lightlevel"] = 6000
                                bridge_config["sensors"][sensor]["state"]["dark"] = True

                            #if alarm is activ trigger the alarm
                            if "virtual_light" in bridge_config["alarm_config"] and bridge_config["lights"][bridge_config["alarm_config"]["virtual_light"]]["state"]["on"] and bridge_config["sensors"][sensor]["state"]["presence"] == True:
                                sendEmail(bridge_config["sensors"][sensor]["name"])
                                #triger_horn() need development
                        rulesProcessor(sensor, current_time) #process the rules to perform the action configured by application
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
                bridge_config["config"]["linkbutton"] = int(bridge_config["linkbutton"]["lastlinkbuttonpushed"]) + 30 >= int(datetime.now().strftime("%s"))
                if len(url_pices) == 3: #print entire config
                    self._set_end_headers(bytes(json.dumps({"lights": bridge_config["lights"], "groups": bridge_config["groups"], "config": bridge_config["config"], "scenes": bridge_config["scenes"], "schedules": bridge_config["schedules"], "rules": bridge_config["rules"], "sensors": bridge_config["sensors"], "resourcelinks": bridge_config["resourcelinks"]},separators=(',', ':')), "utf8"))
                elif len(url_pices) == 4: #print specified object config
                    self._set_end_headers(bytes(json.dumps(bridge_config[url_pices[3]],separators=(',', ':')), "utf8"))
                elif len(url_pices) == 5:
                    if url_pices[4] == "new": #return new lights and sensors only
                        new_lights.update({"lastscan": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")})
                        self._set_end_headers(bytes(json.dumps(new_lights ,separators=(',', ':')), "utf8"))
                        new_lights.clear()
                    elif url_pices[3] == "groups" and url_pices[4] == "0":
                        any_on = False
                        all_on = True
                        for group_state in bridge_config["groups"].keys():
                            if bridge_config["groups"][group_state]["state"]["any_on"] == True:
                                any_on = True
                            else:
                                all_on = False
                        self._set_end_headers(bytes(json.dumps({"name":"Group 0","lights": [l for l in bridge_config["lights"]],"sensors": [s for s in bridge_config["sensors"]],"type":"LightGroup","state":{"all_on":all_on,"any_on":any_on},"recycle":false,"action":{"on":false,"alert":"none"}},separators=(',', ':')), "utf8"))
                    elif url_pices[3] == "info":
                        self._set_end_headers(bytes(json.dumps(bridge_config["capabilities"][url_pices[4]],separators=(',', ':')), "utf8"))
                    else:
                        self._set_end_headers(bytes(json.dumps(bridge_config[url_pices[3]][url_pices[4]],separators=(',', ':')), "utf8"))
            elif (url_pices[2] == "nouser" or url_pices[2] == "none" or url_pices[2] == "config"): #used by applications to discover the bridge
                self._set_end_headers(bytes(json.dumps({"name": bridge_config["config"]["name"],"datastoreversion": 70, "swversion": bridge_config["config"]["swversion"], "apiversion": bridge_config["config"]["apiversion"], "mac": bridge_config["config"]["mac"], "bridgeid": bridge_config["config"]["bridgeid"], "factorynew": False, "replacesbridgeid": None, "modelid": bridge_config["config"]["modelid"],"starterkitid":""},separators=(',', ':')), "utf8"))
            else: #user is not in whitelist
                self._set_end_headers(bytes(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],separators=(',', ':')), "utf8"))

    def read_http_request_body(self):
        return b"{}" if self.headers['Content-Length'] is None or self.headers[
            'Content-Length'] == '0' else self.rfile.read(int(self.headers['Content-Length']))

    def do_POST(self):
        self._set_headers()
        logging.debug("in post method")
        logging.debug(self.path)
        self.data_string = self.read_http_request_body()
        if self.path == "/updater":
            logging.debug("check for updates")
            update_data = json.loads(sendRequest("http://raw.githubusercontent.com/mariusmotea/diyHue/master/BridgeEmulator/updater", "GET", "{}"))
            for category in update_data.keys():
                for key in update_data[category].keys():
                    logging.debug("patch " + category + " -> " + key )
                    bridge_config[category][key] = update_data[category][key]
            self._set_end_headers(bytes(json.dumps([{"success": {"/config/swupdate/checkforupdate": True}}],separators=(',', ':')), "utf8"))
        else:
            raw_json = self.data_string.decode('utf8')
            raw_json = raw_json.replace("\t","")
            raw_json = raw_json.replace("\n","")
            post_dictionary = json.loads(raw_json)
            logging.debug(self.data_string)
        url_pices = self.path.rstrip('/').split('/')
        if len(url_pices) == 4: #data was posted to a location
            if url_pices[2] in bridge_config["config"]["whitelist"]:
                if ((url_pices[3] == "lights" or url_pices[3] == "sensors") and not bool(post_dictionary)):
                    #if was a request to scan for lights of sensors
                    Thread(target=scanForLights).start()
                    sleep(7) #give no more than 5 seconds for light scanning (otherwise will face app disconnection timeout)
                    self._set_end_headers(bytes(json.dumps([{"success": {"/" + url_pices[3]: "Searching for new devices"}}],separators=(',', ':')), "utf8"))
                elif url_pices[3] == "":
                    self._set_end_headers(bytes(json.dumps([{"success": {"clientkey": "321c0c2ebfa7361e55491095b2f5f9db"}}],separators=(',', ':')), "utf8"))
                else: #create object
                    # find the first unused id for new object
                    new_object_id = nextFreeId(bridge_config, url_pices[3])
                    if url_pices[3] == "scenes":
                        post_dictionary.update({"lightstates": {}, "version": 2, "picture": "", "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "owner" :url_pices[2]})
                        if "locked" not in post_dictionary:
                            post_dictionary["locked"] = False
                    elif url_pices[3] == "groups":
                        post_dictionary.update({"action": {"on": False}, "state": {"any_on": False, "all_on": False}})
                    elif url_pices[3] == "schedules":
                        try:
                            post_dictionary.update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "time": post_dictionary["localtime"]})
                        except KeyError:
                            post_dictionary.update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "localtime": post_dictionary["time"]})
                        if post_dictionary["localtime"].startswith("PT"):
                            post_dictionary.update({"starttime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                        if not "status" in post_dictionary:
                            post_dictionary.update({"status": "enabled"})
                    elif url_pices[3] == "rules":
                        post_dictionary.update({"owner": url_pices[2], "lasttriggered" : "none", "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "timestriggered": 0})
                        if not "status" in post_dictionary:
                            post_dictionary.update({"status": "enabled"})
                    elif url_pices[3] == "sensors":
                        if "state" not in post_dictionary:
                            post_dictionary["state"] = {}
                        if post_dictionary["modelid"] == "PHWA01":
                            post_dictionary.update({"state": {"status": 0}})
                    elif url_pices[3] == "resourcelinks":
                        post_dictionary.update({"owner" :url_pices[2]})
                    generateSensorsState()
                    bridge_config[url_pices[3]][new_object_id] = post_dictionary
                    logging.debug(json.dumps([{"success": {"id": new_object_id}}], sort_keys=True, indent=4, separators=(',', ': ')))
                    self._set_end_headers(bytes(json.dumps([{"success": {"id": new_object_id}}], separators=(',', ':')), "utf8"))
            else:
                self._set_end_headers(bytes(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}], separators=(',', ':')), "utf8"))
                logging.debug(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],sort_keys=True, indent=4, separators=(',', ': ')))
        elif self.path.startswith("/api") and "devicetype" in post_dictionary: #new registration by linkbutton
            if int(bridge_config["linkbutton"]["lastlinkbuttonpushed"])+30 >= int(datetime.now().strftime("%s")) or bridge_config["config"]["linkbutton"]:
                username = hashlib.new('ripemd160', post_dictionary["devicetype"][0].encode('utf-8')).hexdigest()[:32]
                bridge_config["config"]["whitelist"][username] = {"last use date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"create date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"name": post_dictionary["devicetype"]}
                response = [{"success": {"username": username}}]
                if "generateclientkey" in post_dictionary and post_dictionary["generateclientkey"]:
                    response[0]["success"]["clientkey"] = "321c0c2ebfa7361e55491095b2f5f9db"
                self._set_end_headers(bytes(json.dumps(response,separators=(',', ':')), "utf8"))
                logging.debug(json.dumps(response, sort_keys=True, indent=4, separators=(',', ': ')))
            else:
                self._set_end_headers(bytes(json.dumps([{"error": {"type": 101, "address": self.path, "description": "link button not pressed" }}], separators=(',', ':')), "utf8"))
        saveConfig()

    def do_PUT(self):
        self._set_headers()
        logging.debug("in PUT method")
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        put_dictionary = json.loads(self.data_string.decode('utf8'))
        url_pices = self.path.rstrip('/').split('/')
        logging.debug(self.path)
        logging.debug(self.data_string)
        if url_pices[2] in bridge_config["config"]["whitelist"]:
            if len(url_pices) == 4:
                bridge_config[url_pices[3]].update(put_dictionary)
                response_location = "/" + url_pices[3] + "/"
            if len(url_pices) == 5:
                if url_pices[3] == "schedules":
                    if "status" in put_dictionary and put_dictionary["status"] == "enabled" and bridge_config["schedules"][url_pices[4]]["localtime"].startswith("PT"):
                        put_dictionary.update({"starttime": (datetime.utcnow()).strftime("%Y-%m-%dT%H:%M:%S")})
                elif url_pices[3] == "scenes":
                    if "storelightstate" in put_dictionary:
                        for light in bridge_config["scenes"][url_pices[4]]["lightstates"]:
                            bridge_config["scenes"][url_pices[4]]["lightstates"][light] = {}
                            bridge_config["scenes"][url_pices[4]]["lightstates"][light]["on"] = bridge_config["lights"][light]["state"]["on"]
                            bridge_config["scenes"][url_pices[4]]["lightstates"][light]["bri"] = bridge_config["lights"][light]["state"]["bri"]
                            if "colormode" in bridge_config["lights"][light]["state"]:
                                if bridge_config["lights"][light]["state"]["colormode"] in ["ct", "xy"]:
                                    bridge_config["scenes"][url_pices[4]]["lightstates"][light][bridge_config["lights"][light]["state"]["colormode"]] = bridge_config["lights"][light]["state"][bridge_config["lights"][light]["state"]["colormode"]]
                                elif bridge_config["lights"][light]["state"]["colormode"] == "hs" and "hue" in bridge_config["scenes"][url_pices[4]]["lightstates"][light]:
                                    bridge_config["scenes"][url_pices[4]]["lightstates"][light]["hue"] = bridge_config["lights"][light]["state"]["hue"]
                                    bridge_config["scenes"][url_pices[4]]["lightstates"][light]["sat"] = bridge_config["lights"][light]["state"]["sat"]
                if url_pices[3] == "sensors":
                    current_time = datetime.now()
                    for key, value in put_dictionary.items():
                        if key not in sensors_state[url_pices[4]]:
                            sensors_state[url_pices[4]][key] = {}
                        if type(value) is dict:
                            bridge_config["sensors"][url_pices[4]][key].update(value)
                            for element in value.keys():
                                sensors_state[url_pices[4]][key][element] = current_time
                        else:
                            bridge_config["sensors"][url_pices[4]][key] = value
                            sensors_state[url_pices[3]][url_pices[4]][key] = current_time
                    rulesProcessor(url_pices[4], current_time)
                    if url_pices[4] == "1" and bridge_config[url_pices[3]][url_pices[4]]["modelid"] == "PHDL00":
                        bridge_config["sensors"]["1"]["config"]["configured"] = True ##mark daylight sensor as configured
                elif url_pices[3] == "groups" and "stream" in put_dictionary:
                    if "active" in put_dictionary["stream"]:
                        if put_dictionary["stream"]["active"]:
                            logging.debug("start hue entertainment")
                            Popen(["/opt/hue-emulator/entertainment-srv", "server_port=2100", "dtls=1", "psk_list=" + url_pices[2] + ",321c0c2ebfa7361e55491095b2f5f9db"])
                            sleep(0.2)
                            bridge_config["groups"][url_pices[4]]["stream"].update({"active": True, "owner": url_pices[2], "proxymode": "auto", "proxynode": "/bridge"})
                        else:
                            Popen(["killall", "entertainment-srv"])
                            bridge_config["groups"][url_pices[4]]["stream"].update({"active": False, "owner": None})
                    else:
                        bridge_config[url_pices[3]][url_pices[4]].update(put_dictionary)
                else:
                    bridge_config[url_pices[3]][url_pices[4]].update(put_dictionary)
                response_location = "/" + url_pices[3] + "/" + url_pices[4] + "/"
            if len(url_pices) == 6:
                if url_pices[3] == "groups": #state is applied to a group
                    if url_pices[5] == "stream":
                        if "active" in put_dictionary:
                            if put_dictionary["active"]:
                                logging.debug("start hue entertainment")
                                Popen(["/opt/hue-emulator/entertainment-srv", "server_port=2100", "dtls=1", "psk_list=" + url_pices[2] + ",321c0c2ebfa7361e55491095b2f5f9db"])
                                sleep(0.2)
                                bridge_config["groups"][url_pices[4]]["stream"].update({"active": True, "owner": url_pices[2], "proxymode": "auto", "proxynode": "/bridge"})
                            else:
                                Popen(["killall", "entertainment-srv"])
                                bridge_config["groups"][url_pices[4]]["stream"].update({"active": False, "owner": None})
                    elif "scene" in put_dictionary: #scene applied to group
                        splitLightsToDevices(url_pices[4], {}, bridge_config["scenes"][put_dictionary["scene"]]["lightstates"])

                    elif "bri_inc" in put_dictionary or "ct_inc" in put_dictionary:
                        splitLightsToDevices(url_pices[4], put_dictionary)
                    elif "scene_inc" in put_dictionary:
                        switchScene(url_pices[4], put_dictionary["scene_inc"])
                    elif url_pices[4] == "0": #if group is 0 the scene applied to all lights
                        groupZero(put_dictionary)
                    else: # the state is applied to particular group (url_pices[4])
                        if "on" in put_dictionary:
                            bridge_config["groups"][url_pices[4]]["state"]["any_on"] = put_dictionary["on"]
                            bridge_config["groups"][url_pices[4]]["state"]["all_on"] = put_dictionary["on"]
                        bridge_config["groups"][url_pices[4]][url_pices[5]].update(put_dictionary)
                        splitLightsToDevices(url_pices[4], put_dictionary)
                elif url_pices[3] == "lights": #state is applied to a light
                    for key in put_dictionary.keys():
                        if key in ["ct", "xy"]: #colormode must be set by bridge
                            bridge_config["lights"][url_pices[4]]["state"]["colormode"] = key
                        elif key in ["hue", "sat"]:
                            bridge_config["lights"][url_pices[4]]["state"]["colormode"] = "hs"
                    updateGroupStats(url_pices[4])
                    sendLightRequest(url_pices[4], put_dictionary)
                if not url_pices[4] == "0": #group 0 is virtual, must not be saved in bridge configuration
                    try:
                        bridge_config[url_pices[3]][url_pices[4]][url_pices[5]].update(put_dictionary)
                    except KeyError:
                        bridge_config[url_pices[3]][url_pices[4]][url_pices[5]] = put_dictionary
                if url_pices[3] == "sensors" and url_pices[5] == "state":
                    current_time = datetime.now()
                    for key in put_dictionary.keys():
                        sensors_state[url_pices[4]]["state"].update({key: current_time})
                    rulesProcessor(url_pices[4], current_time)
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
            self._set_end_headers(bytes(json.dumps(response_dictionary,separators=(',', ':')), "utf8"))
            logging.debug(json.dumps(response_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))
        else:
            self._set_end_headers(bytes(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],separators=(',', ':')), "utf8"))

    def do_DELETE(self):
        self._set_headers()
        url_pices = self.path.rstrip('/').split('/')
        if url_pices[2] in bridge_config["config"]["whitelist"]:
            if len(url_pices) == 6:
                del bridge_config[url_pices[3]][url_pices[4]][url_pices[5]]
            else:
                del bridge_config[url_pices[3]][url_pices[4]]
                if url_pices[3] == "resourcelinks":
                    Thread(target=resourceRecycle).start()
            if url_pices[3] == "lights":
                del bridge_config["lights_address"][url_pices[4]]
                for light in list(bridge_config["deconz"]["lights"]):
                    if bridge_config["deconz"]["lights"][light]["bridgeid"] == url_pices[4]:
                        del bridge_config["deconz"]["lights"][light]
            elif url_pices[3] == "sensors":
                for sensor in list(bridge_config["deconz"]["sensors"]):
                    if bridge_config["deconz"]["sensors"][sensor]["bridgeid"] == url_pices[4]:
                        del bridge_config["deconz"]["sensors"][sensor]
            self._set_end_headers(bytes(json.dumps([{"success": "/" + url_pices[3] + "/" + url_pices[4] + " deleted."}],separators=(',', ':')), "utf8"))

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

def run(https, server_class=ThreadingSimpleServer, handler_class=S):
    if https:
        server_address = ('', 443)
        httpd = server_class(server_address, handler_class)
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(certfile="./cert.pem")
        ctx.options |= ssl.OP_NO_TLSv1
        ctx.options |= ssl.OP_NO_TLSv1_1
        ctx.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
        ctx.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256')
        ctx.set_ecdh_curve('prime256v1')
        #ctx.set_alpn_protocols(['h2', 'http/1.1'])
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        logging.debug('Starting ssl httpd...')
    else:
        server_address = ('', 80)
        httpd = server_class(server_address, handler_class)
        logging.debug('Starting httpd...')
    httpd.serve_forever()
    httpd.server_close()

if __name__ == "__main__":
    updateConfig()
    Thread(target=resourceRecycle).start()
    if bridge_config["deconz"]["enabled"]:
        scanDeconz()
    try:
        if update_lights_on_startup:
            updateAllLights()
        Thread(target=ssdpSearch, args=[getIpAddress(), mac]).start()
        Thread(target=ssdpBroadcast, args=[getIpAddress(), mac]).start()
        Thread(target=schedulerProcessor).start()
        Thread(target=syncWithLights).start()
        Thread(target=entertainmentService).start()
        Thread(target=run, args=[False]).start()
        Thread(target=run, args=[True]).start()
        Thread(target=daylightSensor).start()
        while True:
            sleep(10)
    except Exception:
        logging.exception("server stopped ")
    finally:
        run_service = False
        saveConfig()
        logging.debug('config saved')
