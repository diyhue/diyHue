#!/usr/bin/python3
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from time import strftime, sleep
from datetime import datetime, timedelta
from pprint import pprint
from subprocess import check_output
import json, socket, hashlib, struct, random, sys
import requests
import urllib.request, urllib.parse
import base64
from threading import Thread
from collections import defaultdict
from uuid import getnode as get_mac
from urllib.parse import urlparse, parse_qs

update_lights_on_startup = True # if set to true all lights will be updated with last know state on startup.

mac = '%012x' % get_mac()

run_service = True

bridge_config = defaultdict(lambda:defaultdict(str))
new_lights = {}
sensors_state = {}

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
        print("successfully sent the mail")
        return True
    except:
        print("failed to send mail")
        return False

#load config files
try:
    with open('/opt/hue-emulator/config.json', 'r') as fp:
        bridge_config = json.load(fp)
        print("Config loaded")
except Exception:
    print("CRITICAL! Config file was not loaded")
    sys.exit(1)


def nextFreeId(element):
    i = 1
    while (str(i)) in bridge_config[element]:
        i += 1
    return str(i)

#load and configure alarm virtual light
if bridge_config["alarm_config"]["mail_username"] != "":
    print("E-mail account configured")
    if "virtual_light" not in bridge_config["alarm_config"]:
        print("Send test email")
        if sendEmail("dummy test"):
            print("Mail succesfully sent\nCreate alarm virtual light")
            new_light_id = nextFreeId("lights")
            bridge_config["lights"][new_light_id] = {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.690456, 0.295907], "ct": 461, "alert": "none", "effect": "none", "colormode": "xy", "reachable": True}, "type": "Extended color light", "name": "Alarm", "uniqueid": "1234567ffffff", "modelid": "LLC012", "swversion": "66009461"}
            bridge_config["alarm_config"]["virtual_light"] = new_light_id
        else:
            print("Mail test failed")


def generateSensorsState():
    for sensor in bridge_config["sensors"]:
        if sensor not in sensors_state and "state" in bridge_config["sensors"][sensor]:
            sensors_state[sensor] = {"state": {}}
            for key in bridge_config["sensors"][sensor]["state"].keys():
                if key in ["lastupdated", "presence", "flag", "dark", "status"]:
                    sensors_state[sensor]["state"].update({key: "2017-01-01T00:00:00"})

generateSensorsState() #comment this line if you don't want to restore last known state to all lights on startup

def getIpAddress():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


bridge_config["config"]["ipaddress"] = getIpAddress()
bridge_config["config"]["gateway"] = getIpAddress()
bridge_config["config"]["mac"] = mac[0] + mac[1] + ":" + mac[2] + mac[3] + ":" + mac[4] + mac[5] + ":" + mac[6] + mac[7] + ":" + mac[8] + mac[9] + ":" + mac[10] + mac[11]
bridge_config["config"]["bridgeid"] = (mac[:6] + 'FFFE' + mac[6:]).upper()

def saveConfig(filename='/opt/hue-emulator/config.json'):
    with open(filename, 'w') as fp:
        json.dump(bridge_config, fp, sort_keys=True, indent=4, separators=(',', ': '))

def ssdpSearch():
    SSDP_ADDR = '239.255.255.250'
    SSDP_PORT = 1900
    MSEARCH_Interval = 2
    multicast_group_c = SSDP_ADDR
    multicast_group_s = (SSDP_ADDR, SSDP_PORT)
    server_address = ('', SSDP_PORT)
    Response_message = 'HTTP/1.1 200 OK\r\nHOST: 239.255.255.250:1900\r\nEXT:\r\nCACHE-CONTROL: max-age=100\r\nLOCATION: http://' + getIpAddress() + ':80/description.xml\r\nSERVER: Linux/3.14.0 UPnP/1.0 IpBridge/1.20.0\r\nhue-bridgeid: ' + (mac[:6] + 'FFFE' + mac[6:]).upper() + '\r\n'
    custom_response_message = {0: {"st": "upnp:rootdevice", "usn": "uuid:2f402f80-da50-11e1-9b23-" + mac + "::upnp:rootdevice"}, 1: {"st": "uuid:2f402f80-da50-11e1-9b23-" + mac, "usn": "uuid:2f402f80-da50-11e1-9b23-" + mac}, 2: {"st": "urn:schemas-upnp-org:device:basic:1", "usn": "uuid:2f402f80-da50-11e1-9b23-" + mac}}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(server_address)

    group = socket.inet_aton(multicast_group_c)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print("starting ssdp...")

    while run_service:
        data, address = sock.recvfrom(1024)
        data = data.decode('utf-8')
        if data[0:19]== 'M-SEARCH * HTTP/1.1':
           if data.find("ssdp:discover") != -1:
               sleep(random.randrange(0, 3))
               print("Sending M-Search response to " + address[0])
               for x in range(3):
                  sock.sendto(bytes(Response_message + "ST: " + custom_response_message[x]["st"] + "\r\nUSN: " + custom_response_message[x]["usn"] + "\r\n\r\n", "utf8"), address)
        sleep(1)

def ssdpBroadcast():
    print("start ssdp broadcast")
    SSDP_ADDR = '239.255.255.250'
    SSDP_PORT = 1900
    MSEARCH_Interval = 2
    multicast_group_s = (SSDP_ADDR, SSDP_PORT)
    message = 'NOTIFY * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nCACHE-CONTROL: max-age=100\r\nLOCATION: http://' + getIpAddress() + ':80/description.xml\r\nSERVER: Linux/3.14.0 UPnP/1.0 IpBridge/1.20.0\r\nNTS: ssdp:alive\r\nhue-bridgeid: ' + (mac[:6] + 'FFFE' + mac[6:]).upper() + '\r\n'
    custom_message = {0: {"nt": "upnp:rootdevice", "usn": "uuid:2f402f80-da50-11e1-9b23-" + mac + "::upnp:rootdevice"}, 1: {"nt": "uuid:2f402f80-da50-11e1-9b23-" + mac, "usn": "uuid:2f402f80-da50-11e1-9b23-" + mac}, 2: {"nt": "urn:schemas-upnp-org:device:basic:1", "usn": "uuid:2f402f80-da50-11e1-9b23-" + mac}}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(MSEARCH_Interval+0.5)
    ttl = struct.pack('b', 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    while True:
        for x in range(3):
            sent = sock.sendto(bytes(message + "NT: " + custom_message[x]["nt"] + "\r\nUSN: " + custom_message[x]["usn"] + "\r\n\r\n", "utf8"),multicast_group_s)
            sent = sock.sendto(bytes(message + "NT: " + custom_message[x]["nt"] + "\r\nUSN: " + custom_message[x]["usn"] + "\r\n\r\n", "utf8"),multicast_group_s)
        sleep(60)

def schedulerProcessor():
    while run_service:
        for schedule in bridge_config["schedules"].keys():
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
                            print("execute schedule: " + schedule + " withe delay " + str(delay))
                            sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                elif schedule_time.startswith("PT"):
                    timmer = schedule_time[2:]
                    (h, m, s) = timmer.split(':')
                    d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                    if bridge_config["schedules"][schedule]["starttime"] == (datetime.utcnow() - d).strftime("%Y-%m-%dT%H:%M:%S"):
                        print("execute timmer: " + schedule + " withe delay " + str(delay))
                        sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                        bridge_config["schedules"][schedule]["status"] = "disabled"
                else:
                    if schedule_time == datetime.now().strftime("%Y-%m-%dT%H:%M:%S"):
                        print("execute schedule: " + schedule + " withe delay " + str(delay))
                        sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                        if bridge_config["schedules"][schedule]["autodelete"]:
                            del bridge_config["schedules"][schedule]
        if (datetime.now().strftime("%M:%S") == "00:10"): #auto save configuration every hour
            saveConfig()
            if (datetime.now().strftime("%H") == "23" and datetime.now().strftime("%A") == "Sunday"): #backup config every Sunday at 23:00:10
                saveConfig("config-backup-" + datetime.now().strftime("%Y-%m-%d") + ".json")
        sleep(1)

def addTradfriDimmer(sensor_id, group_id):
    rules = [{ "actions":[{"address": "/groups/" + group_id + "/action", "body":{ "on":True, "bri":1 }, "method": "PUT" }], "conditions":[{ "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}, { "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2002" }, { "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "false" }], "name": "Remote " + sensor_id + " turn on" },{"actions":[{"address":"/groups/" + group_id + "/action", "body":{ "on": False}, "method":"PUT"}], "conditions":[{ "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }, { "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4002" }, { "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "true" }, { "address": "/groups/" + group_id + "/action/bri", "operator": "eq", "value": "1"}], "name":"Dimmer Switch " + sensor_id + " off"}, { "actions":[{ "address": "/groups/" + group_id + "/action", "body":{ "on":False }, "method": "PUT" }], "conditions":[{ "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }, { "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3002" }, { "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "true" }, { "address": "/groups/" + group_id + "/action/bri", "operator": "eq", "value": "1"}], "name": "Remote " + sensor_id + " turn off" }, { "actions": [{"address": "/groups/" + group_id + "/action", "body":{"bri_inc": 32, "transitiontime": 9}, "method": "PUT" }], "conditions": [{ "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "true" },{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2002" }, {"address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}], "name": "Dimmer Switch " + sensor_id + " rotate right"}, { "actions": [{"address": "/groups/" + group_id + "/action", "body":{"bri_inc": 56, "transitiontime": 9}, "method": "PUT" }], "conditions": [{ "address": "/groups/" + group_id + "/state/any_on", "operator": "eq", "value": "true" },{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "1002" }, {"address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}], "name": "Dimmer Switch " + sensor_id + " rotate fast right"}, {"actions": [{"address": "/groups/" + group_id + "/action", "body": {"bri_inc": -32, "transitiontime": 9}, "method": "PUT"}], "conditions": [{ "address": "/groups/" + group_id + "/action/bri", "operator": "gt", "value": "1"},{"address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3002"}, {"address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}], "name": "Dimmer Switch " + sensor_id + " rotate left"}, {"actions": [{"address": "/groups/" + group_id + "/action", "body": {"bri_inc": -56, "transitiontime": 9}, "method": "PUT"}], "conditions": [{ "address": "/groups/" + group_id + "/action/bri", "operator": "gt", "value": "1"},{"address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4002"}, {"address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx"}], "name": "Dimmer Switch " + sensor_id + " rotate left"}]
    resourcelinkId = nextFreeId("resourcelinks")
    bridge_config["resourcelinks"][resourcelinkId] = {"classid": 15555,"description": "Rules for sensor " + sensor_id, "links": ["/sensors/" + sensor_id], "name": "Emulator rules " + sensor_id,"owner": list(bridge_config["config"]["whitelist"])[0]}
    for rule in rules:
        ruleId = nextFreeId("rules")
        bridge_config["rules"][ruleId] = rule
        bridge_config["rules"][ruleId].update({"creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "lasttriggered": None, "owner": list(bridge_config["config"]["whitelist"])[0], "recycle": True, "status": "enabled", "timestriggered": 0})
        bridge_config["resourcelinks"][resourcelinkId]["links"].append("/rules/" + ruleId);

def addTradfriCtRemote(sensor_id, group_id):
    rules = [{"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": True},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "1002"},{"address": "/groups/" + group_id + "/state/any_on","operator": "eq","value": "false"}],"name": "Remote " + sensor_id + " button on"}, {"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": False},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "1002"},{"address": "/groups/" + group_id + "/state/any_on","operator": "eq","value": "true"}],"name": "Remote " + sensor_id + " button off"},{ "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": 30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " up-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": 56, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " up-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": -30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " dn-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": -56, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " dn-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "ct_inc": 50, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ctl-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "ct_inc": 100, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ctl-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "ct_inc": -50, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "5002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ct-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "ct_inc": -100, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "5001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ct-long" }]
    resourcelinkId = nextFreeId("resourcelinks")
    bridge_config["resourcelinks"][resourcelinkId] = {"classid": 15555,"description": "Rules for sensor " + sensor_id, "links": ["/sensors/" + sensor_id], "name": "Emulator rules " + sensor_id,"owner": list(bridge_config["config"]["whitelist"])[0]}
    for rule in rules:
        ruleId = nextFreeId("rules")
        bridge_config["rules"][ruleId] = rule
        bridge_config["rules"][ruleId].update({"creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "lasttriggered": None, "owner": list(bridge_config["config"]["whitelist"])[0], "recycle": True, "status": "enabled", "timestriggered": 0})
        bridge_config["resourcelinks"][resourcelinkId]["links"].append("/rules/" + ruleId);

def addTradfriSceneRemote(sensor_id, group_id):
    rules = [{"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": True},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "1002"},{"address": "/groups/" + group_id + "/state/any_on","operator": "eq","value": "false"}],"name": "Remote " + sensor_id + " button on"}, {"actions": [{"address": "/groups/" + group_id + "/action","body": {"on": False},"method": "PUT"}],"conditions": [{"address": "/sensors/" + sensor_id + "/state/lastupdated","operator": "dx"},{"address": "/sensors/" + sensor_id + "/state/buttonevent","operator": "eq","value": "1002"},{"address": "/groups/" + group_id + "/state/any_on","operator": "eq","value": "true"}],"name": "Remote " + sensor_id + " button off"},{ "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": 30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " up-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": 56, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "2001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " up-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": -30, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " dn-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "bri_inc": -56, "transitiontime": 9 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "3001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " dn-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "scene_inc": -1 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ctl-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "scene_inc": -1 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "4001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ctl-long" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "scene_inc": 1 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "5002" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ct-press" }, { "actions": [{ "address": "/groups/" + group_id + "/action", "body": { "scene_inc": 1 }, "method": "PUT" }], "conditions": [{ "address": "/sensors/" + sensor_id + "/state/buttonevent", "operator": "eq", "value": "5001" }, { "address": "/sensors/" + sensor_id + "/state/lastupdated", "operator": "dx" }], "name": "Dimmer Switch " + sensor_id + " ct-long" }]
    resourcelinkId = nextFreeId("resourcelinks")
    bridge_config["resourcelinks"][resourcelinkId] = {"classid": 15555,"description": "Rules for sensor " + sensor_id, "links": ["/sensors/" + sensor_id], "name": "Emulator rules " + sensor_id,"owner": list(bridge_config["config"]["whitelist"])[0]}
    for rule in rules:
        ruleId = nextFreeId("rules")
        bridge_config["rules"][ruleId] = rule
        bridge_config["rules"][ruleId].update({"creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "lasttriggered": None, "owner": list(bridge_config["config"]["whitelist"])[0], "recycle": True, "status": "enabled", "timestriggered": 0})
        bridge_config["resourcelinks"][resourcelinkId]["links"].append("/rules/" + ruleId);

def addHueMotionSensor(uniqueid):
    new_sensor_id = nextFreeId("sensors")
    if uniqueid == "":
        if len(new_sensor_id) == 1:
            uniqueid = "0" + new_sensor_id + ":0f:12:23:34:45"
        else:
            uniqueid = new_sensor_id + ":0f:12:23:34:45"
    bridge_config["sensors"][new_sensor_id] = {"name": "Hue temperature sensor 1", "uniqueid": uniqueid + ":56:d0:5b-02-0402", "type": "ZLLTemperature", "swversion": "6.1.0.18912", "state": {"temperature": None, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False, "battery": 100, "reachable": True, "alert":"none", "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
    bridge_config["sensors"][str(int(new_sensor_id) + 1)] = {"name": "Entrance Lights sensor", "uniqueid": uniqueid + ":56:d0:5b-02-0406", "type": "ZLLPresence", "swversion": "6.1.0.18912", "state": {"lastupdated": "none", "presence": None}, "manufacturername": "Philips", "config": {"on": False,"battery": 100,"reachable": True, "alert": "lselect", "ledindication": False, "usertest": False, "sensitivity": 2, "sensitivitymax": 2,"pending": []}, "modelid": "SML001"}
    bridge_config["sensors"][str(int(new_sensor_id) + 2)] = {"name": "Hue ambient light sensor 1", "uniqueid": uniqueid + ":56:d0:5b-02-0400", "type": "ZLLLightLevel", "swversion": "6.1.0.18912", "state": {"dark": True, "daylight": False, "lightlevel": 6000, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False,"battery": 100, "reachable": True, "alert": "none", "tholddark": 21597, "tholdoffset": 7000, "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
    return(str(int(new_sensor_id) + 1))

def addHueSwitch(uniqueid, sensorsType):
    new_sensor_id = nextFreeId("sensors")
    if uniqueid == "":
        uniqueid = "00:00:00:00:00:40:" + new_sensor_id + ":83-f2"
    bridge_config["sensors"][new_sensor_id] = {"state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "name": "Dimmer Switch" if sensorsType == "ZLLSwitch" else "Tap Switch", "type": sensorsType, "modelid": "RWL021" if sensorsType == "ZLLSwitch" else "ZGPSWITCH", "manufacturername": "Philips", "swversion": "5.45.1.17846" if sensorsType == "ZLLSwitch" else "", "uniqueid": uniqueid}
    return(new_sensor_id)

def switchScene(group, direction):
    print("group " + group)
    group_scenes = []
    current_position = -1
    possible_current_position = -1 # used in case the brigtness was changes and will be no perfect match (scene lightstates vs light states)
    break_next = False
    for scene in bridge_config["scenes"]:
        if bridge_config["groups"][group]["lights"][0] in bridge_config["scenes"][scene]["lights"]:
            group_scenes.append(scene)
            if break_next: # don't lose time as this is the chene we need
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
                if direction == -1:
                    break
                else:
                    break_next = True
            elif  is_possible_current_scene:
                possible_current_position = len(group_scenes) -1

    matched_scene = ""
    if current_position + possible_current_position == -2:
        print("current scene not found, reset to zero")
        if len(group_scenes) != 0:
            matched_scene = group_scenes[0]
        else:
            print("error, no scenes found")
            return
    elif current_position != -1:
        if len(group_scenes) -1 < current_position + direction:
            return
        matched_scene = group_scenes[current_position + direction]
    elif possible_current_position != -1:
        if len(group_scenes) -1 < possible_current_position + direction:
            return
        matched_scene = group_scenes[possible_current_position + direction]
    print("matched scene " + bridge_config["scenes"][matched_scene]["name"])

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


    if sensor_found:
        return [True, ddx, ddx_sensor]
    else:
        return [False]

def ddxRecheck(rule, sensor, current_time, ddx_delay, ddx_sensor):
    for x in range(ddx_delay):
        if current_time != sensors_state[ddx_sensor[2]][ddx_sensor[3]][ddx_sensor[4]]:
            print("ddx rule " + rule + " canceled after " + str(x) + " seconds")
            return # rule not valid anymore because sensor state changed while waiting for ddx delay
        sleep(1)
    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    rule_state = checkRuleConditions(rule, sensor, current_time, True)
    if rule_state[0]: #if all conditions are meet again
        print("delayed rule " + rule + " is triggered")
        bridge_config["rules"][rule]["lasttriggered"] = current_time
        bridge_config["rules"][rule]["timestriggered"] += 1
        for action in bridge_config["rules"][rule]["actions"]:
            sendRequest("/api/" + bridge_config["rules"][rule]["owner"] + action["address"], action["method"], json.dumps(action["body"]))

def rulesProcessor(sensor, current_time=datetime.now().strftime("%Y-%m-%dT%H:%M:%S")):
    bridge_config["config"]["localtime"] = current_time #required for operator dx to address /config/localtime
    actionsToExecute = []
    for rule in bridge_config["rules"].keys():
        if bridge_config["rules"][rule]["status"] == "enabled":
            rule_result = checkRuleConditions(rule, sensor, current_time)
            if rule_result[0]:
                if rule_result[1] == 0: #is not ddx rule
                    print("rule " + rule + " is triggered")
                    bridge_config["rules"][rule]["lasttriggered"] = current_time
                    bridge_config["rules"][rule]["timestriggered"] += 1
                    for action in bridge_config["rules"][rule]["actions"]:
                        actionsToExecute.append(action)
                else: #if ddx rule
                    print("ddx rule " + rule + " will be re validated after " + str(rule_result[1]) + " seconds")
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

def convert_rgb_xy(red,green,blue):
    red = pow((red + 0.055) / (1.0 + 0.055), 2.4) if red > 0.04045 else red / 12.92
    green = pow((green + 0.055) / (1.0 + 0.055), 2.4) if green > 0.04045 else green / 12.92
    blue = pow((blue + 0.055) / (1.0 + 0.055), 2.4) if blue > 0.04045 else blue / 12.92

#Convert the RGB values to XYZ using the Wide RGB D65 conversion formula The formulas used:
    X = red * 0.664511 + green * 0.154324 + blue * 0.162028
    Y = red * 0.283881 + green * 0.668433 + blue * 0.047685
    Z = red * 0.000088 + green * 0.072310 + blue * 0.986039

#Calculate the xy values from the XYZ values
    x = X / (X + Y + Z)
    y = Y / (X + Y + Z)
    return [x, y]

def convert_xy(x, y, bri): #needed for milight hub that don't work with xy values
    X = x
    Y = y
    Z = 1.0 - x - y

  # sRGB D65 conversion
    r =  X * 3.2406 - Y * 1.5372 - Z * 0.4986
    g = -X * 0.9689 + Y * 1.8758 + Z * 0.0415
    b =  X * 0.0557 - Y * 0.2040 + Z * 1.0570


    r = 12.92 * r if r <= 0.0031308 else (1.0 + 0.055) * pow(r, (1.0 / 2.4)) - 0.055
    g = 12.92 * g if g <= 0.0031308 else (1.0 + 0.055) * pow(g, (1.0 / 2.4)) - 0.055
    b = 12.92 * b if b <= 0.0031308 else (1.0 + 0.055) * pow(b, (1.0 / 2.4)) - 0.055

    if r > b and r > g:
    # red is biggest
        if r > 1:
            g = g / r
            b = b / r
            r = 1
    elif g > b and g > r:
    # green is biggest
        if g > 1:
            r = r / g
            b = b / g
            g = 1

    elif b > r and b > g:
    # blue is biggest
        if b > 1:
            r = r / b
            g = g / b
            b = 1

    r = 0 if r < 0 else r
    g = 0 if g < 0 else g
    b = 0 if b < 0 else b

    return [int(r * bri), int(g * bri), int(b * bri)]

def sendLightRequest(light, data):
    payload = {}
    if light in bridge_config["lights_address"]:
        if bridge_config["lights_address"][light]["protocol"] == "native": #ESP8266 light or strip
            url = "http://" + bridge_config["lights_address"][light]["ip"] + "/set?light=" + str(bridge_config["lights_address"][light]["light_nr"]);
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
            url = "http://" + bridge_config["lights_address"][light]["ip"] + "/json.htm?type=command&param=switchlight&idx=" + bridge_config["lights_address"][light]["light_id"];
            method = 'GET'
            for key, value in data.items():
                if key == "on":
                    if value:
                        url += "&switchcmd=On"
                    else:
                        url += "&switchcmd=Off"
                elif key == "bri":
                    url += "&switchcmd=Set%20Level&level=" + str(round(float(value)/255*100)) # domoticz range from 0 to 100 (for zwave devices) instead of 0-255 of bridge

        elif bridge_config["lights_address"][light]["protocol"] == "milight": #MiLight bulb
            url = "http://" + bridge_config["lights_address"][light]["ip"] + "/gateways/" + bridge_config["lights_address"][light]["device_id"] + "/" + bridge_config["lights_address"][light]["mode"] + "/" + str(bridge_config["lights_address"][light]["group"]);
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
            print(json.dumps(payload))
        elif bridge_config["lights_address"][light]["protocol"] == "ikea_tradfri": #IKEA Tradfri bulb
            url = "coaps://" + bridge_config["lights_address"][light]["ip"] + ":5684/15001/" + str(bridge_config["lights_address"][light]["device_id"])
            for key, value in data.items():
                if key == "on":
                    payload["5850"] = int(value)
                elif key == "transitiontime":
                    payload["transitiontime"] = value
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
            if "5850" in payload and payload["5850"] == 0:
                payload.clear() #setting brightnes will turn on the ligh even if there was a request to power off
                payload["5850"] = 0
            elif "5850" in payload and "5851" in payload: #when setting brightness don't send also power on command
                del payload["5850"]
                pprint(payload)

        try:
            if bridge_config["lights_address"][light]["protocol"] == "ikea_tradfri":
                if "transitiontime" in payload:
                    transitiontime = payload["transitiontime"]
                else:
                    transitiontime = 4
                    for key, value in payload.items(): #ikea bulbs don't accept all arguments at once
                        print(check_output("./coap-client-linux -m put -u \"" + bridge_config["lights_address"][light]["identity"] + "\" -k \"" + bridge_config["lights_address"][light]["preshared_key"] + "\" -e '{ \"3311\": [" + json.dumps({key : value, "5712": transitiontime}) + "] }' \"" + url + "\"", shell=True).split("\n")[3])
                        sleep(0.5)
            elif bridge_config["lights_address"][light]["protocol"] in ["hue", "deconz"]:
                if "xy" in payload:
                    sendRequest(url, method, json.dumps({"on": True, "xy": payload["xy"]}))
                    del(payload["xy"])
                    sleep(0.6)
                elif "ct" in payload:
                    sendRequest(url, method, json.dumps({"on": True, "ct": payload["ct"]}))
                    del(payload["ct"])
                    sleep(0.6)
                sendRequest(url, method, json.dumps(payload))
            else:
                sendRequest(url, method, json.dumps(payload))
        except:
            bridge_config["lights"][light]["state"]["reachable"] = False
            print("request error")
        else:
            bridge_config["lights"][light]["state"]["reachable"] = True
            print("LightRequest: " + url)

def updateGroupStats(light): #set group stats based on lights status in that group
    for group in bridge_config["groups"]:
        if light in bridge_config["groups"][group]["lights"]:
            for key, value in bridge_config["lights"][light]["state"].items():
                if key not in ["on", "reachable"]:
                    bridge_config["groups"][group]["action"][key] = value
            any_on = False
            all_on = True
            for group_light in bridge_config["groups"][group]["lights"]:
                if bridge_config["lights"][light]["state"]["on"] == True:
                    any_on = True
                else:
                    all_on = False
            bridge_config["groups"][group]["state"] = {"any_on": any_on, "all_on": all_on,}
            bridge_config["groups"][group]["action"]["on"] = any_on

def scanForLights(): #scan for ESP8266 lights and strips
    print(json.dumps([{"success": {"/lights": "Searching for new devices"}}], sort_keys=True, indent=4, separators=(',', ': ')))
    #return all host that listen on port 80
    device_ips = check_output("nmap  " + getIpAddress() + "/24 -p80 --open -n | grep report | cut -d ' ' -f5", shell=True).decode('utf-8').split("\n")
    pprint(device_ips)
    del device_ips[-1] #delete last empty element in list
    for ip in device_ips:
        try:
            if ip != getIpAddress():
                response = requests.get("http://" + ip + "/detect", timeout=3)
                if response.status_code == 200:
                    device_data = json.loads(response.text)
                    pprint(device_data)
                    if "hue" in device_data:
                        print(ip + " is a hue " + device_data['hue'])
                        device_exist = False
                        for light in bridge_config["lights"].keys():
                            if bridge_config["lights"][light]["uniqueid"].startswith( device_data["mac"] ):
                                device_exist = True
                                bridge_config["lights_address"][light]["ip"] = ip
                        if not device_exist:
                            print("is a new device")
                            for x in range(1, int(device_data["lights"]) + 1):
                                new_light_id = nextFreeId("lights")
                                light_types = {"LCT001": {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}, "type": "Extended color light", "swversion": "66009461"}, "LCT015": {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}, "type": "Extended color light", "swversion": "1.29.0_r21169"}, "LST001": {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}, "type": "Color light", "swversion": "66010400"}, "LWB010": {"state": {"on": False, "bri": 254,"alert": "none", "reachable": True}, "type": "Dimmable light", "swversion": "1.15.0_r18729"}, "LTW001": {"state": {"on": False, "colormode": "ct", "alert": "none", "reachable": True, "bri": 254, "ct": 230}, "type": "Color temperature light", "swversion": "5.50.1.19085"}, "Plug 01": {"state": {"on": False, "alert": "none", "reachable": True}, "type": "On/Off plug-in unit", "swversion": "V1.04.12"}}
                                bridge_config["lights"][new_light_id] = {"state": light_types[device_data["modelid"]]["state"], "type": light_types[device_data["modelid"]]["type"], "name": "Hue " + device_data["hue"] + " " + device_data["modelid"] + " " + str(x), "uniqueid": device_data["mac"] + "-" + str(x), "modelid": device_data["modelid"], "swversion": light_types[device_data["modelid"]]["swversion"]}
                                new_lights.update({new_light_id: {"name": "Hue " + device_data["hue"] + " " + device_data["modelid"] + " " + str(x)}})
                                bridge_config["lights_address"][new_light_id] = {"ip": ip, "light_nr": x, "protocol": "native"}
        except:
            print("ip " + ip + " is unknow device")
    scanDeconz()
    scanTradfri()
    saveConfig()


def syncWithLights(): #update Hue Bridge lights states
    while True:
        print("sync with lights")
        for light in bridge_config["lights_address"]:
            try:
                if bridge_config["lights_address"][light]["protocol"] == "native":
                    light_data = json.loads(sendRequest("http://" + bridge_config["lights_address"][light]["ip"] + "/get?light=" + str(bridge_config["lights_address"][light]["light_nr"]), "GET", "{}"))
                    bridge_config["lights"][light]["state"].update(light_data)
                elif bridge_config["lights_address"][light]["protocol"] == "hue":
                    light_data = json.loads(sendRequest("http://" + bridge_config["lights_address"][light]["ip"] + "/api/" + bridge_config["lights_address"][light]["username"] + "/lights/" + bridge_config["lights_address"][light]["light_id"], "GET", "{}"))
                    bridge_config["lights"][light]["state"].update(light_data["state"])
                elif bridge_config["lights_address"][light]["protocol"] == "ikea_tradfri":
                    light_data = json.loads(check_output("./coap-client-linux -m get -u \"Client_identity\" -k \"" + bridge_config["lights_address"][light]["security_code"] + "\" \"coaps://" + bridge_config["lights_address"][light]["ip"] + ":5684/15001/" + str(bridge_config["lights_address"][light]["device_id"]) +"\"", shell=True).decode('utf-8').split("\n")[3])
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
                        bridge_config["lights"][light]["state"]["colormode"] = "xy"
                        bridge_config["lights"][light]["state"]["xy"] = convert_rgb_xy(light_data["color"]["r"], light_data["color"]["g"], light_data["color"]["b"])

                elif bridge_config["lights_address"][light]["protocol"] == "domoticz": #domoticz protocol
                    light_data = json.loads(sendRequest("http://" + bridge_config["lights_address"][light]["ip"] + "/json.htm?type=devices&rid=" + bridge_config["lights_address"][light]["light_id"], "GET", "{}"))
                    if light_data["result"][0]["Status"] == "Off":
                         bridge_config["lights"][light]["state"]["on"] = False
                    else:
                         bridge_config["lights"][light]["state"]["on"] = True
                    bridge_config["lights"][light]["state"]["bri"] = str(round(float(light_data["result"][0]["Level"])/100*255))

                bridge_config["lights"][light]["state"]["reachable"] = True
                updateGroupStats(light)
            except:
                bridge_config["lights"][light]["state"]["reachable"] = False
                bridge_config["lights"][light]["state"]["on"] = False
                print("light " + light + " is unreachable")
        sleep(10) #wait at last 10 seconds before next sync
        i = 0
        while i < 300: #sync with lights every 300 seconds or instant if one user is connected
            for user in bridge_config["config"]["whitelist"].keys():
                if bridge_config["config"]["whitelist"][user]["last use date"] == datetime.now().strftime("%Y-%m-%dT%H:%M:%S"):
                    i = 300
                    break
            sleep(1)



def longPressButton(sensor, buttonevent):
    print("long press detected")
    sleep(1)
    while bridge_config["sensors"][sensor]["state"]["buttonevent"] == buttonevent:
        print("still pressed")
        current_time =  datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        sensors_state[sensor]["state"]["lastupdated"] = current_time
        rulesProcessor(sensor, current_time)
        sleep(0.9)
    return


def scanTradfri():
    if "tradfri" in bridge_config:
        tradri_devices = json.loads(check_output("./coap-client-linux -m get -u \"" + bridge_config["tradfri"]["identity"] + "\" -k \"" + bridge_config["tradfri"]["psk"] + "\" \"coaps://" + bridge_config["tradfri"]["ip"] + ":5684/15001\"", shell=True).decode('utf-8').split("\n")[3])
        pprint(tradri_devices)
        lights_found = 0
        for device in tradri_devices:
            device_parameters = json.loads(check_output("./coap-client-linux -m get -u \"" + bridge_config["tradfri"]["identity"] + "\" -k \"" + bridge_config["tradfri"]["psk"] + "\" \"coaps://" + bridge_config["tradfri"]["ip"] + ":5684/15001/" + str(device) +"\"", shell=True).decode('utf-8').split("\n")[3])
            if "3311" in device_parameters:
                new_light = True
                for light in bridge_config["lights_address"]:
                    if bridge_config["lights_address"][light]["protocol"] == "ikea_tradfri" and bridge_config["lights_address"][light]["device_id"] == device:
                        new_light = False
                        break
                if new_light:
                    lights_found += 1
                    #register new tradfri lightdevice_id
                    print("register tradfi light " + device_parameters["9001"])
                    new_light_id = nextFreeId("lights")
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
            print(("deconz websocket disconnected", code, reason))
            del bridge_config["deconz"]["websocketport"]

        def received_message(self, m):
            print(m)
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
                            if message["state"]["dark"]:
                                bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                            else:
                                bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 25000
                            if message["state"]["dark"] and not sensors_state[bridge_sensor_id]["state"]["dark"]:
                                sensors_state[bridge_sensor_id]["state"]["dark"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                            bridge_config["sensors"][light_sensor]["state"]["dark"] = message["state"]["dark"]
                            bridge_config["sensors"][light_sensor]["state"]["daylight"] = not message["state"]["dark"]
                            bridge_config["sensors"][light_sensor]["state"]["lastupdated"] = message["state"]["lastupdated"]

                        #convert xiaomi motion sensor to hue sensor
                        if message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["modelid"] == "lumi.sensor_motion.aq2" and message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["type"] == "ZHALightLevel":
                            bridge_config["sensors"][bridge_sensor_id]["state"].update(message["state"])
                            return
                        ##############

                        bridge_config["sensors"][bridge_sensor_id]["state"].update(message["state"])
                        current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                        for key in message["state"].keys():
                            sensors_state[bridge_sensor_id]["state"][key] = current_time
                        rulesProcessor(bridge_sensor_id, current_time)
                        if "buttonevent" in message["state"] and bridge_config["sensors"][bridge_sensor_id]["modelid"] in ["TRADFRI remote control","RWL021"]:
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
                print("unable to process the request" + str(e))

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
                print("registration fail, is the link button pressed?")
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
            if light not in bridge_config["deconz"]["lights"]:
                new_light_id = nextFreeId("lights")
                print("register new light " + new_light_id)
                bridge_config["lights"][new_light_id] = deconz_lights[light]
                bridge_config["lights_address"][new_light_id] = {"username": bridge_config["deconz"]["username"], "light_id": light, "ip": "127.0.0.1:" + str(bridge_config["deconz"]["port"]), "protocol": "deconz"}
                bridge_config["deconz"]["lights"][light] = {"bridgeid": new_light_id}
            else: #temporary patch for config compatibility with new release
                bridge_config["deconz"]["lights"][light]["modelid"] = deconz_lights[light]["modelid"]
                bridge_config["deconz"]["lights"][light]["type"] = deconz_lights[light]["type"]



        #sensors
        deconz_sensors = json.loads(sendRequest("http://127.0.0.1:" + str(bridge_config["deconz"]["port"]) + "/api/" + bridge_config["deconz"]["username"] + "/sensors", "GET", "{}"))
        for sensor in deconz_sensors:
            if sensor not in bridge_config["deconz"]["sensors"]:
                new_sensor_id = nextFreeId("sensors")
                if deconz_sensors[sensor]["modelid"] in ["TRADFRI remote control", "TRADFRI wireless dimmer"]:
                    print("register new " + deconz_sensors[sensor]["modelid"])
                    bridge_config["sensors"][new_sensor_id] = {"config": deconz_sensors[sensor]["config"], "manufacturername": deconz_sensors[sensor]["manufacturername"], "modelid": deconz_sensors[sensor]["modelid"], "name": deconz_sensors[sensor]["name"], "state": deconz_sensors[sensor]["state"], "swversion": deconz_sensors[sensor]["swversion"], "type": deconz_sensors[sensor]["type"], "uniqueid": deconz_sensors[sensor]["uniqueid"]}
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"]}
                elif deconz_sensors[sensor]["modelid"] == "TRADFRI motion sensor":
                    print("register TRADFRI motion sensor as Philips Motion Sensor")
                    newMotionSensorId = addHueMotionSensor("")
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"]}

                elif deconz_sensors[sensor]["modelid"] == "lumi.sensor_motion.aq2":
                    if deconz_sensors[sensor]["type"] == "ZHALightLevel":
                        print("register new Xiaomi light sensor")
                        bridge_config["sensors"][new_sensor_id] = {"name": "Hue ambient light sensor 1", "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:], "type": "ZLLLightLevel", "swversion": "6.1.0.18912", "state": {"dark": True, "daylight": False, "lightlevel": 6000, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False,"battery": 100, "reachable": True, "alert": "none", "tholddark": 21597, "tholdoffset": 7000, "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
                        bridge_config["sensors"][str(int(new_sensor_id) + 1)] = {"name": "Hue temperature sensor 1", "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:-1] + "2", "type": "ZLLTemperature", "swversion": "6.1.0.18912", "state": {"temperature": None, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False, "battery": 100, "reachable": True, "alert":"none", "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
                        bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id}
                    elif deconz_sensors[sensor]["type"] == "ZHAPresence":
                        print("register new Xiaomi motion sensor")
                        bridge_config["sensors"][new_sensor_id] = {"name": "Entrance Lights sensor", "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:], "type": "ZLLPresence", "swversion": "6.1.0.18912", "state": {"lastupdated": "none", "presence": None}, "manufacturername": "Philips", "config": {"on": False,"battery": 100,"reachable": True, "alert": "lselect", "ledindication": False, "usertest": False, "sensitivity": 2, "sensitivitymax": 2,"pending": []}, "modelid": "SML001"}
                        bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id}
                else:
                    bridge_config["sensors"][new_sensor_id] = deconz_sensors[sensor]
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id}
            else: #temporary patch for config compatibility with new release
                bridge_config["deconz"]["sensors"][sensor]["modelid"] = deconz_sensors[sensor]["modelid"]
                bridge_config["deconz"]["sensors"][sensor]["type"] = deconz_sensors[sensor]["type"]
        generateSensorsState()

        if "websocketport" in bridge_config["deconz"]:
            print("Starting deconz websocket")
            Thread(target=websocketClient).start()




def description():
    return """<?xml version="1.0" encoding="UTF-8" ?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
<specVersion>
<major>1</major>
<minor>0</minor>
</specVersion>
<URLBase>http://""" + getIpAddress() + """:80/</URLBase>
<device>
<deviceType>urn:schemas-upnp-org:device:Basic:1</deviceType>
<friendlyName>Philips hue (""" + getIpAddress() + """)</friendlyName>
<manufacturer>Royal Philips Electronics</manufacturer>
<manufacturerURL>http://www.philips.com</manufacturerURL>
<modelDescription>Philips hue Personal Wireless Lighting</modelDescription>
<modelName>Philips hue bridge 2015</modelName>
<modelNumber>BSB002</modelNumber>
<modelURL>http://www.meethue.com</modelURL>
<serialNumber>""" + mac + """</serialNumber>
<UDN>uuid:2f402f80-da50-11e1-9b23-""" + mac + """</UDN>
<presentationURL>index.html</presentationURL>
<iconList>
<icon>
<mimetype>image/png</mimetype>
<height>48</height>
<width>48</width>
<depth>24</depth>
<url>hue_logo_0.png</url>
</icon>
</iconList>
</device>
</root>
"""

def webformTradfri():
    return """<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>Tradfri Setup</title>
<link rel=\"stylesheet\" href=\"https://unpkg.com/purecss@0.6.2/build/pure-min.css\">
</head>
<body>
<form class=\"pure-form pure-form-aligned\" action=\"\" method=\"get\">
<fieldset>
<legend>Tradfri Setup</legend>
<div class=\"pure-control-group\"><label for=\"ip\">Bridge IP</label><input id=\"ip\" name=\"ip\" type=\"text\" placeholder=\"168.168.xxx.xxx\"></div>
<div class=\"pure-control-group\"><label for=\"code\">Security Code</label><input id=\"code\" name=\"code\" type=\"text\" placeholder=\"1a2b3c4d5e6f7g8h\"></div>
<div class=\"pure-controls\"><label for=\"cb\" class=\"pure-checkbox\"></label><button type=\"submit\" class=\"pure-button pure-button-primary\">Save</button></div>
</fieldset>
</form>
</body>
</html>"""

def webformDeconz():
    content = """<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>Deconz Setup</title>
<link rel=\"stylesheet\" href=\"https://unpkg.com/purecss@0.6.2/build/pure-min.css\">
</head>
<body>
<form class=\"pure-form pure-form-aligned\" action=\"\" method=\"get\">
<fieldset>
<legend>Deconz Switches Setup</legend>\n"""
    for deconzSensor in bridge_config["deconz"]["sensors"].keys():
        if bridge_config["sensors"][bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"]]["modelid"] in ["TRADFRI remote control", "TRADFRI wireless dimmer"]:
            content += "<div class=\"pure-control-group\">\n"
            content += "<label for=\"" + deconzSensor + "\">" + bridge_config["sensors"][bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"]]["name"] + "</label>\n"
            content += "<select id=\"" + deconzSensor + "\" name=\"" + bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"] + "\">\n"
            if bridge_config["sensors"][bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"]]["modelid"] == "TRADFRI remote control":
                content += "<option value=\"ZGPSwitch\">Hue Tap Switch</option>\n"
                content += "<option value=\"ZLLSwitch\">Hue Dimmer Switch</option>\n"
            for group in bridge_config["groups"].keys():
                if "room" in bridge_config["deconz"]["sensors"][deconzSensor] and bridge_config["deconz"]["sensors"][deconzSensor]["room"] == group:
                    content += "<option value=\"" + group + "\" selected>" + bridge_config["groups"][group]["name"] + "</option>\n"
                else:
                    content += "<option value=\"" + group + "\">" + bridge_config["groups"][group]["name"] + "</option>\n"
            content += "</select>\n"
            if bridge_config["sensors"][bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"]]["modelid"] == "TRADFRI remote control":
                content += "<select id=\"" + deconzSensor + "\" name=\"mode_" + bridge_config["deconz"]["sensors"][deconzSensor]["bridgeid"] + "\">\n"
                content += "<option value=\"CT\">CCT Switch</option>\n"
                content += "<option value=\"SCENE\" " + ("selected" if "opmode" in bridge_config["deconz"]["sensors"][deconzSensor] and bridge_config["deconz"]["sensors"][deconzSensor]["opmode"] == "SCENE" else "") +  ">Scene Switch</option>\n"
                content += "</select>\n"
            content += "</div>\n"
    content += """<div class="pure-controls">
<button type=\"submit\" class=\"pure-button pure-button-primary\">Save</button></div>
</div>
</fieldset>
</form>
</body>
</html>"""
    return content


def webform_milight():
    return """<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>Milight Setup</title>
<link rel=\"stylesheet\" href=\"https://unpkg.com/purecss@0.6.2/build/pure-min.css\">
</head>
<body>
<form class=\"pure-form pure-form-aligned\" action=\"\" method=\"get\">
<fieldset>
<legend>Milight Setup</legend>
<div class=\"pure-control-group\"><label for=\"ip\">Hub ip</label><input id=\"ip\" name=\"ip\" type=\"text\" placeholder=\"168.168.xxx.xxx\"></div>
<div class=\"pure-control-group\"><label for=\"device_id\">Device id</label><input id=\"device_id\" name=\"device_id\" type=\"text\" placeholder=\"0x1234\"></div>
<div class=\"pure-control-group\">
<label for=\"mode\">Mode</label>
<select id=\"mode\" name=\"mode\">
<option value=\"rgbw\">RGBW</option>
<option value=\"cct\">CCT</option>
<option value=\"rgb_cct\">RGB+CCT</option>
<option value=\"rgb\">RGB</option>
</select>
</div>
<div class=\"pure-control-group\">
<label for=\"group\">Group</label>
<select id=\"group\" name=\"group\">
<option value=\"1\">1</option>
<option value=\"2\">2</option>
<option value=\"3\">3</option>
<option value=\"4\">4</option>
</select>
</div>
<div class=\"pure-controls\"><button type=\"submit\" class=\"pure-button pure-button-primary\">Save</button></div>
</fieldset>
</form>
</body>
</html>"""

def webform_hue():
    return """<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>Hue Bridge Setup</title>
<link rel=\"stylesheet\" href=\"https://unpkg.com/purecss@0.6.2/build/pure-min.css\">
</head>
<body>
<form class=\"pure-form pure-form-aligned\" action=\"\" method=\"get\">
<fieldset>
<legend>Hue Bridge Setup</legend>
<div class=\"pure-control-group\"><label for=\"ip\">Hub ip</label><input id=\"ip\" name=\"ip\" type=\"text\" placeholder=\"168.168.xxx.xxx\"></div>
<div class=\"pure-controls\">
<label class="pure-checkbox">
First press the link button on Hue Bridge
</label>
<button type=\"submit\" class=\"pure-button pure-button-primary\">Save</button></div>
</fieldset>
</form>
</body>
</html>"""

def webform_linkbutton():
    return """<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>Hue LinkButton</title>
<link rel=\"stylesheet\" href=\"https://unpkg.com/purecss@0.6.2/build/pure-min.css\">
</head>
<body>
<form class=\"pure-form pure-form-aligned\" action=\"\" method=\"get\">
<fieldset>
<legend>Hue LinkButton</legend>

<div class="pure-control-group">
<label for="username">Username</label><input id="username" name="username" type="text" placeholder="Hue" data-cip-id="username">
</div>
<div class="pure-control-group">
<label for="password">Password</label><input id="password" name="password" type="password" placeholder="HuePassword" data-cip-id="password">
</div>

<div class=\"pure-controls\">
<label class="pure-checkbox">
Click on Activate button to allow association for 30 sec.
</label>
<input class=\"pure-button pure-button-primary\" type=\"submit\" name=\"action\" value=\"Activate\">
<input class=\"pure-button pure-button-primary\" type=\"submit\" name=\"action\" value=\"ChangePassword\">
<input class=\"pure-button pure-button-primary\" type=\"submit\" name=\"action\" value=\"Exit\"></div>
</fieldset>
</form>
</body>
</html>"""

def updateAllLights():
    ## apply last state on startup to all bulbs, usefull if there was a power outage
    for light in bridge_config["lights_address"]:
        payload = {}
        payload["on"] = bridge_config["lights"][light]["state"]["on"]
        if payload["on"] and "bri" in bridge_config["lights"][light]["state"]:
            payload["bri"] = bridge_config["lights"][light]["state"]["bri"]
        sendLightRequest(light, payload)
        sleep(0.5)
        print("update status for light " + light)

class S(BaseHTTPRequestHandler):

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def _set_headers_html(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def _set_headers_xml(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/xml')
        self.end_headers()

    def _set_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Hue\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        if self.path == '/description.xml':
            self._set_headers_xml()
            self.wfile.write(bytes(description(), "utf8"))
        elif self.path == '/save':
            saveConfig()
            self.wfile.write(bytes("config saved", "utf8"))
        elif self.path.startswith("/tradfri"): #setup Tradfri gateway
            self._set_headers_html()
            get_parameters = parse_qs(urlparse(self.path).query)
            if "code" in get_parameters:
                #register new identity
                new_identity = "Hue-Emulator-" + str(random.randrange(0, 999))
                registration = json.loads(check_output("./coap-client-linux -m post -u \"Client_identity\" -k \"" + get_parameters["code"][0] + "\" -e '{\"9090\":\"" + new_identity + "\"}' \"coaps://" + get_parameters["ip"][0] + ":5684/15011/9063\"", shell=True).decode('utf-8').split("\n")[3])
                bridge_config["tradfri"] = {"psk": registration["9091"], "ip": get_parameters["ip"][0], "identity": new_identity}
                lights_found = scanTradfri()
                if lights_found == 0:
                    self.wfile.write(bytes(webformTradfri() + "<br> No lights where found", "utf8"))
                else:
                    self.wfile.write(bytes(webformTradfri() + "<br> " + str(lights_found) + " lights where found", "utf8"))
            else:
                self.wfile.write(bytes(webformTradfri(), "utf8"))
        elif self.path.startswith("/milight"): #setup milight bulb
            self._set_headers_html()
            get_parameters = parse_qs(urlparse(self.path).query)
            if "device_id" in get_parameters:
                #register new mi-light
                new_light_id = nextFreeId("lights")
                bridge_config["lights"][new_light_id] = {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}, "type": "Extended color light", "name": "MiLight " + get_parameters["mode"][0] + " " + get_parameters["device_id"][0], "uniqueid": "1a2b3c4" + str(random.randrange(0, 99)), "modelid": "LCT001", "swversion": "66009461"}
                new_lights.update({new_light_id: {"name": "MiLight " + get_parameters["mode"][0] + " " + get_parameters["device_id"][0]}})
                bridge_config["lights_address"][new_light_id] = {"device_id": get_parameters["device_id"][0], "mode": get_parameters["mode"][0], "group": int(get_parameters["group"][0]), "ip": get_parameters["ip"][0], "protocol": "milight"}
                self.wfile.write(bytes(webform_milight() + "<br> Light added", "utf8"))
            else:
                self.wfile.write(bytes(webform_milight(), "utf8"))
        elif self.path.startswith("/hue"): #setup hue bridge
            if "linkbutton" in self.path: #Hub button emulated
                if self.headers['Authorization'] == None:
                    self._set_AUTHHEAD()
                    self.wfile.write(bytes('You are not authenticated', "utf8"))
                    pass
                elif self.headers['Authorization'] == 'Basic ' + bridge_config["linkbutton"]["linkbutton_auth"]:
                    get_parameters = parse_qs(urlparse(self.path).query)
                    if "action=Activate" in self.path:
                        self._set_headers_html()
                        bridge_config["config"]["linkbutton"] = False
                        bridge_config["linkbutton"]["lastlinkbuttonpushed"] = datetime.now().strftime("%s")
                        saveConfig()
                        self.wfile.write(bytes(webform_linkbutton() + "<br> You have 30 sec to connect your device", "utf8"))
                    elif "action=Exit" in self.path:
                        self._set_AUTHHEAD()
                        self.wfile.write(bytes('You are succesfully disconnected', "utf8"))
                    elif "action=ChangePassword" in self.path:
                        self._set_headers_html()
                        tmp_password = str(base64.b64encode(bytes(get_parameters["username"][0] + ":" + get_parameters["password"][0], "utf8"))).split('\'')
                        bridge_config["linkbutton"]["linkbutton_auth"] = tmp_password[1]
                        saveConfig()
                        self.wfile.write(bytes(webform_linkbutton() + '<br> Your credentials are succesfully change. Please logout then login again', "utf8"))
                    else:
                        self._set_headers_html()
                        self.wfile.write(bytes(webform_linkbutton(), "utf8"))
                    pass
                else:
                    self._set_AUTHHEAD()
                    self.wfile.write(bytes(self.headers.headers['Authorization'], "utf8"))
                    self.wfile.write(bytes('not authenticated', "utf8"))
                    pass
            else:
                self._set_headers_html()
                get_parameters = parse_qs(urlparse(self.path).query)
                if "ip" in get_parameters:
                    response = json.loads(sendRequest("http://" + get_parameters["ip"][0] + "/api/", "POST", "{\"devicetype\":\"Hue Emulator\"}"))
                    if "success" in response[0]:
                        hue_lights = json.loads(sendRequest("http://" + get_parameters["ip"][0] + "/api/" + response[0]["success"]["username"] + "/lights", "GET", "{}"))
                        lights_found = 0
                        for hue_light in hue_lights:
                            new_light_id = nextFreeId("lights")
                            bridge_config["lights"][new_light_id] = hue_lights[hue_light]
                            bridge_config["lights_address"][new_light_id] = {"username": response[0]["success"]["username"], "light_id": hue_light, "ip": get_parameters["ip"][0], "protocol": "hue"}
                            lights_found += 1
                        if lights_found == 0:
                            self.wfile.write(bytes(webform_hue() + "<br> No lights where found", "utf8"))
                        else:
                            self.wfile.write(bytes(webform_hue() + "<br> " + str(lights_found) + " lights where found", "utf8"))
                    else:
                        self.wfile.write(bytes(webform_hue() + "<br> unable to connect to hue bridge", "utf8"))
                else:
                    self.wfile.write(bytes(webform_hue(), "utf8"))
        elif self.path.startswith("/deconz"): #setup imported deconz sensors
            self._set_headers_html()
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
                                    print("unable to delete the rule " + pices[2])
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
                            #store room id in deconz sensors
                            for sensor in bridge_config["deconz"]["sensors"].keys():
                                if bridge_config["deconz"]["sensors"][sensor]["bridgeid"] == key:
                                    bridge_config["deconz"]["sensors"][sensor]["room"] = get_parameters[key][0]
                                    if bridge_config["sensors"][key]["modelid"] == "TRADFRI remote control":
                                        bridge_config["deconz"]["sensors"][sensor]["opmode"] = get_parameters["mode_" + key][0]

            else:
                scanDeconz()
            self.wfile.write(bytes(webformDeconz(), "utf8"))
        elif self.path.startswith("/switch"): #request from an ESP8266 switch or sensor
            self._set_headers_html()
            get_parameters = parse_qs(urlparse(self.path).query)
            pprint(get_parameters)
            if "devicetype" in get_parameters: #register device request
                sensor_is_new = True
                for sensor in bridge_config["sensors"]:
                    if bridge_config["sensors"][sensor]["uniqueid"].startswith(get_parameters["mac"][0]): # if sensor is already present
                        sensor_is_new = False
                if sensor_is_new:
                    print("registering new sensor " + get_parameters["devicetype"][0])
                    new_sensor_id = nextFreeId("sensors")
                    if get_parameters["devicetype"][0] in ["ZLLSwitch","ZGPSwitch"]:
                        print(get_parameters["devicetype"][0])
                        addHueSwitch(get_parameters["mac"][0], get_parameters["devicetype"][0])
                    elif get_parameters["devicetype"][0] == "ZLLPresence":
                        print("ZLLPresence")
                        addHueMotionSensor(get_parameters["mac"][0])
                    generateSensorsState()
            else: #switch action request
                for sensor in bridge_config["sensors"]:
                    if bridge_config["sensors"][sensor]["uniqueid"].startswith(get_parameters["mac"][0]) and bridge_config["sensors"][sensor]["config"]["on"]: #match senser id based on mac address
                        print("match sensor " + str(sensor))
                        if bridge_config["sensors"][sensor]["type"] == "ZLLSwitch" or bridge_config["sensors"][sensor]["type"] == "ZGPSwitch":
                            bridge_config["sensors"][sensor]["state"].update({"buttonevent": get_parameters["button"][0], "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                            current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                            sensors_state[sensor]["state"]["lastupdated"] = current_time
                            rulesProcessor(sensor, current_time)
                        elif bridge_config["sensors"][sensor]["type"] == "ZLLPresence" and "presence" in get_parameters:
                            if str(bridge_config["sensors"][sensor]["state"]["presence"]).lower() != get_parameters["presence"][0]:
                                sensors_state[sensor]["state"]["presence"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                            bridge_config["sensors"][sensor]["state"].update({"presence": True if get_parameters["presence"][0] == "true" else False, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                            rulesProcessor(sensor)
                            #if alarm is activ trigger the alarm
                            if "virtual_light" in bridge_config["alarm_config"] and bridge_config["lights"][bridge_config["alarm_config"]["virtual_light"]]["state"]["on"] and bridge_config["sensors"][sensor]["state"]["presence"] == True:
                                sendEmail(bridge_config["sensors"][sensor]["name"])
                                #triger_horn() need development
                        elif bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel" and "lightlevel" in get_parameters:
                            if str(bridge_config["sensors"][sensor]["state"]["dark"]).lower() != get_parameters["dark"][0]:
                                sensors_state[sensor]["state"]["dark"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                            bridge_config["sensors"][sensor]["state"].update({"lightlevel":int(get_parameters["lightlevel"][0]), "dark":True if get_parameters["dark"][0] == "true" else False, "daylight":True if get_parameters["daylight"][0] == "true" else False, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
                            rulesProcessor(sensor) #process the rules to perform the action configured by application
        else:
            url_pices = self.path.split('/')
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
                if len(url_pices) == 3 or (len(url_pices) == 4 and url_pices[3] == ""): #print entire config
                    self.wfile.write(bytes(json.dumps({"lights": bridge_config["lights"], "groups": bridge_config["groups"], "config": bridge_config["config"], "scenes": bridge_config["scenes"], "schedules": bridge_config["schedules"], "rules": bridge_config["rules"], "sensors": bridge_config["sensors"], "resourcelinks": bridge_config["resourcelinks"]}), "utf8"))
                elif len(url_pices) == 4 or (len(url_pices) == 5 and url_pices[4] == ""): #print specified object config
                    self.wfile.write(bytes(json.dumps(bridge_config[url_pices[3]]), "utf8"))
                elif len(url_pices) == 5 or (len(url_pices) == 6 and url_pices[5] == ""):
                    if url_pices[4] == "new": #return new lights and sensors only
                        new_lights.update({"lastscan": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")})
                        self.wfile.write(bytes(json.dumps(new_lights), "utf8"))
                        new_lights.clear()
                    elif url_pices[3] == "groups" and url_pices[4] == "0":
                        any_on = False
                        all_on = True
                        for group_state in bridge_config["groups"].keys():
                            if bridge_config["groups"][group_state]["state"]["any_on"] == True:
                                any_on = True
                            else:
                                all_on = False
                        self.wfile.write(bytes(json.dumps({"name":"Group 0","lights": [l for l in bridge_config["lights"]],"type":"LightGroup","state":{"all_on":all_on,"any_on":any_on},"recycle":False,"action":{"on":True,"bri":254,"hue":47258,"sat":253,"effect":"none","xy":[0.1424,0.0824],"ct":153,"alert":"none","colormode":"xy"}}), "utf8"))
                    elif url_pices[3] == "info":
                        self.wfile.write(bytes(json.dumps(bridge_config["capabilities"][url_pices[4]]), "utf8"))
                    else:
                        self.wfile.write(bytes(json.dumps(bridge_config[url_pices[3]][url_pices[4]]), "utf8"))
                elif len(url_pices) == 6 or (len(url_pices) == 7 and url_pices[6] == ""):
                    self.wfile.write(bytes(json.dumps(bridge_config[url_pices[3]][url_pices[4]][url_pices[5]]), "utf8"))
            elif (url_pices[2] == "nouser" or url_pices[2] == "none" or url_pices[2] == "config"): #used by applications to discover the bridge
                self.wfile.write(bytes(json.dumps({"name": bridge_config["config"]["name"],"datastoreversion": 59, "swversion": bridge_config["config"]["swversion"], "apiversion": bridge_config["config"]["apiversion"], "mac": bridge_config["config"]["mac"], "bridgeid": bridge_config["config"]["bridgeid"], "factorynew": False, "modelid": bridge_config["config"]["modelid"]}), "utf8"))
            else: #user is not in whitelist
                self.wfile.write(bytes(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}]), "utf8"))


    def do_POST(self):
        self._set_headers()
        print ("in post method")
        print(self.path)
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        if self.path == "/updater":
            print("check for updates")
            update_data = json.loads(sendRequest("http://raw.githubusercontent.com/mariusmotea/diyHue/master/BridgeEmulator/updater", "GET", "{}"))
            for category in update_data.keys():
                for key in update_data[category].keys():
                    print("patch " + category + " -> " + key )
                    bridge_config[category][key] = update_data[category][key]
            self.wfile.write(bytes(json.dumps([{"success": {"/config/swupdate/checkforupdate": True}}]), "utf8"))
        else:
            post_dictionary = json.loads(self.data_string.decode('utf8'))
            print(self.data_string)
        url_pices = self.path.split('/')
        if len(url_pices) == 4: #data was posted to a location
            if url_pices[2] in bridge_config["config"]["whitelist"]:
                if ((url_pices[3] == "lights" or url_pices[3] == "sensors") and not bool(post_dictionary)):
                    #if was a request to scan for lights of sensors
                    Thread(target=scanForLights).start()
                    sleep(7) #give no more than 5 seconds for light scanning (otherwise will face app disconnection timeout)
                    self.wfile.write(bytes(json.dumps([{"success": {"/" + url_pices[3]: "Searching for new devices"}}]), "utf8"))
                elif url_pices[3] == "":
                    self.wfile.write(bytes(json.dumps([{"success": {"clientkey": "E3B550C65F78022EFD9E52E28378583"}}]), "utf8"))
                else: #create object
                    # find the first unused id for new object
                    new_object_id = nextFreeId(url_pices[3])
                    if url_pices[3] == "scenes":
                        post_dictionary.update({"lightstates": {}, "version": 2, "picture": "", "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "owner" :url_pices[2]})
                        if "locked" not in post_dictionary:
                            post_dictionary["locked"] = False
                    elif url_pices[3] == "groups":
                        post_dictionary.update({"action": {"on": False}, "state": {"any_on": False, "all_on": False}})
                    elif url_pices[3] == "schedules":
                        post_dictionary.update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "time": post_dictionary["localtime"]})
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
                    print(json.dumps([{"success": {"id": new_object_id}}], sort_keys=True, indent=4, separators=(',', ': ')))
                    self.wfile.write(bytes(json.dumps([{"success": {"id": new_object_id}}], sort_keys=True, indent=4, separators=(',', ': ')), "utf8"))
            else:
                self.wfile.write(bytes(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],sort_keys=True, indent=4, separators=(',', ': ')), "utf8"))
                print(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],sort_keys=True, indent=4, separators=(',', ': ')))
        elif self.path.startswith("/api") and "devicetype" in post_dictionary and bridge_config["config"]["linkbutton"]: #this must be a new device registration
                #create new user hash
                username = hashlib.new('ripemd160', post_dictionary["devicetype"][0].encode('utf-8')).hexdigest()[:32]
                bridge_config["config"]["whitelist"][username] = {"last use date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"create date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"name": post_dictionary["devicetype"]}
                response = [{"success": {"username": username}}]
                if "generateclientkey" in post_dictionary and post_dictionary["generateclientkey"]:
                    response[0]["success"]["clientkey"] = "E3B550C65F78022EFD9E52E28378583"
                self.wfile.write(bytes(json.dumps(response), "utf8"))
                print(json.dumps(response, sort_keys=True, indent=4, separators=(',', ': ')))
        elif self.path.startswith("/api") and "devicetype" in post_dictionary and not bridge_config["config"]["linkbutton"]: #new registration by linkbutton
                if int(bridge_config["linkbutton"]["lastlinkbuttonpushed"])+30 >= int(datetime.now().strftime("%s")):
                    username = hashlib.new('ripemd160', post_dictionary["devicetype"][0].encode('utf-8')).hexdigest()[:32]
                    bridge_config["config"]["whitelist"][username] = {"last use date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"create date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"name": post_dictionary["devicetype"]}
                    response = [{"success": {"username": username}}]
                    if "generateclientkey" in post_dictionary and post_dictionary["generateclientkey"]:
                        response[0]["success"]["clientkey"] = "E3B550C65F78022EFD9E52E28378583"
                    self.wfile.write(bytes(json.dumps(response), "utf8"))
                    print(json.dumps(response, sort_keys=True, indent=4, separators=(',', ': ')))
                else:
                    self.wfile.write(bytes(json.dumps([{"error": {"type": 101, "address": self.path, "description": "link button not pressed" }}],sort_keys=True, indent=4, separators=(',', ': ')), "utf8"))
        self.end_headers()
        saveConfig()

    def do_PUT(self):
        self._set_headers()
        print ("in PUT method")
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        put_dictionary = json.loads(self.data_string.decode('utf8'))
        url_pices = self.path.split('/')
        print(self.path)
        print(self.data_string)
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
                            bridge_config["scenes"][url_pices[4]]["lightstates"][light]["on"] = bridge_config["lights"][light]["state"]["on"]
                            bridge_config["scenes"][url_pices[4]]["lightstates"][light]["bri"] = bridge_config["lights"][light]["state"]["bri"]
                            if "xy" in bridge_config["scenes"][url_pices[4]]["lightstates"][light]:
                                del bridge_config["scenes"][url_pices[4]]["lightstates"][light]["xy"]
                            elif "ct" in bridge_config["scenes"][url_pices[4]]["lightstates"][light]:
                                del bridge_config["scenes"][url_pices[4]]["lightstates"][light]["ct"]
                            elif "hue" in bridge_config["scenes"][url_pices[4]]["lightstates"][light]:
                                del bridge_config["scenes"][url_pices[4]]["lightstates"][light]["hue"]
                                del bridge_config["scenes"][url_pices[4]]["lightstates"][light]["sat"]
                            if bridge_config["lights"][light]["state"]["colormode"] in ["ct", "xy"]:
                                bridge_config["scenes"][url_pices[4]]["lightstates"][light][bridge_config["lights"][light]["state"]["colormode"]] = bridge_config["lights"][light]["state"][bridge_config["lights"][light]["state"]["colormode"]]
                            elif bridge_config["lights"][light]["state"]["colormode"] == "hs" and "hue" in bridge_config["scenes"][url_pices[4]]["lightstates"][light]:
                                bridge_config["scenes"][url_pices[4]]["lightstates"][light]["hue"] = bridge_config["lights"][light]["state"]["hue"]
                                bridge_config["scenes"][url_pices[4]]["lightstates"][light]["sat"] = bridge_config["lights"][light]["state"]["sat"]

                if url_pices[3] == "sensors":
                    pprint(put_dictionary)
                    for key, value in put_dictionary.items():
                        if type(value) is dict:
                            bridge_config[url_pices[3]][url_pices[4]][key].update(value)
                        else:
                            bridge_config[url_pices[3]][url_pices[4]][key] = value
                    rulesProcessor(url_pices[4])
                else:
                    bridge_config[url_pices[3]][url_pices[4]].update(put_dictionary)
                response_location = "/" + url_pices[3] + "/" + url_pices[4] + "/"
            if len(url_pices) == 6:
                if url_pices[3] == "groups": #state is applied to a group
                    if "scene" in put_dictionary: #scene applied to group
                        for light in bridge_config["scenes"][put_dictionary["scene"]]["lights"]:
                            bridge_config["lights"][light]["state"].update(bridge_config["scenes"][put_dictionary["scene"]]["lightstates"][light])
                            if "xy" in bridge_config["scenes"][put_dictionary["scene"]]["lightstates"][light]:
                                bridge_config["lights"][light]["state"]["colormode"] = "xy"
                            elif "ct" in bridge_config["scenes"][put_dictionary["scene"]]["lightstates"][light]:
                                bridge_config["lights"][light]["state"]["colormode"] = "ct"
                            elif "hue" or "sat" in bridge_config["scenes"][put_dictionary["scene"]]["lightstates"][light]:
                                bridge_config["lights"][light]["state"]["colormode"] = "hs"
                            sendLightRequest(light, bridge_config["scenes"][put_dictionary["scene"]]["lightstates"][light])
                            updateGroupStats(light)
                    elif "bri_inc" in put_dictionary:
                        bridge_config["groups"][url_pices[4]]["action"]["bri"] += int(put_dictionary["bri_inc"])
                        if bridge_config["groups"][url_pices[4]]["action"]["bri"] > 254:
                            bridge_config["groups"][url_pices[4]]["action"]["bri"] = 254
                        elif bridge_config["groups"][url_pices[4]]["action"]["bri"] < 1:
                            bridge_config["groups"][url_pices[4]]["action"]["bri"] = 1
                        bridge_config["groups"][url_pices[4]]["state"]["bri"] = bridge_config["groups"][url_pices[4]]["action"]["bri"]
                        del put_dictionary["bri_inc"]
                        put_dictionary.update({"bri": bridge_config["groups"][url_pices[4]]["action"]["bri"]})
                        for light in bridge_config["groups"][url_pices[4]]["lights"]:
                            bridge_config["lights"][light]["state"].update(put_dictionary)
                            sendLightRequest(light, put_dictionary)
                    elif "ct_inc" in put_dictionary:
                        bridge_config["groups"][url_pices[4]]["action"]["ct"] += int(put_dictionary["ct_inc"])
                        if bridge_config["groups"][url_pices[4]]["action"]["ct"] > 500:
                            bridge_config["groups"][url_pices[4]]["action"]["ct"] = 500
                        elif bridge_config["groups"][url_pices[4]]["action"]["ct"] < 153:
                            bridge_config["groups"][url_pices[4]]["action"]["ct"] = 153
                        bridge_config["groups"][url_pices[4]]["state"]["ct"] = bridge_config["groups"][url_pices[4]]["action"]["ct"]
                        del put_dictionary["ct_inc"]
                        put_dictionary.update({"ct": bridge_config["groups"][url_pices[4]]["action"]["ct"]})
                        for light in bridge_config["groups"][url_pices[4]]["lights"]:
                            bridge_config["lights"][light]["state"].update(put_dictionary)
                            sendLightRequest(light, put_dictionary)
                    elif "scene_inc" in put_dictionary:
                        switchScene(url_pices[4], put_dictionary["scene_inc"])
                    elif url_pices[4] == "0": #if group is 0 the scene applied to all lights
                        for light in bridge_config["lights"].keys():
                            if "virtual_light" not in bridge_config["alarm_config"] or light != bridge_config["alarm_config"]["virtual_light"]:
                                bridge_config["lights"][light]["state"].update(put_dictionary)
                                sendLightRequest(light, put_dictionary)
                        for group in bridge_config["groups"].keys():
                            bridge_config["groups"][group][url_pices[5]].update(put_dictionary)
                            if "on" in put_dictionary:
                                bridge_config["groups"][group]["state"]["any_on"] = put_dictionary["on"]
                                bridge_config["groups"][group]["state"]["all_on"] = put_dictionary["on"]
                    else: # the state is applied to particular group (url_pices[4])
                        if "on" in put_dictionary:
                            bridge_config["groups"][url_pices[4]]["state"]["any_on"] = put_dictionary["on"]
                            bridge_config["groups"][url_pices[4]]["state"]["all_on"] = put_dictionary["on"]
                        bridge_config["groups"][url_pices[4]]["action"].update(put_dictionary)
                        for light in bridge_config["groups"][url_pices[4]]["lights"]:
                            bridge_config["lights"][light]["state"].update(put_dictionary)
                            sendLightRequest(light, put_dictionary)
                elif url_pices[3] == "lights": #state is applied to a light
                    sendLightRequest(url_pices[4], put_dictionary)
                    for key in put_dictionary.keys():
                        if key in ["ct", "xy"]: #colormode must be set by bridge
                            bridge_config["lights"][url_pices[4]]["state"]["colormode"] = key
                        elif key in ["hue", "sat"]:
                            bridge_config["lights"][url_pices[4]]["state"]["colormode"] = "hs"
                    updateGroupStats(url_pices[4])
                if not url_pices[4] == "0": #group 0 is virtual, must not be saved in bridge configuration
                    try:
                        bridge_config[url_pices[3]][url_pices[4]][url_pices[5]].update(put_dictionary)
                    except KeyError:
                        bridge_config[url_pices[3]][url_pices[4]][url_pices[5]] = put_dictionary
                if url_pices[3] == "sensors" and url_pices[5] == "state":
                    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
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
            self.wfile.write(bytes(json.dumps(response_dictionary,sort_keys=True, indent=4, separators=(',', ': ')), "utf8"))
            print(json.dumps(response_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))
        else:
            self.wfile.write(bytes(json.dumps([{"error": {"type": 1, "address": self.path, "description": "unauthorized user" }}],sort_keys=True, indent=4, separators=(',', ': ')), "utf8"))

    def do_DELETE(self):
        self._set_headers()
        url_pices = self.path.split('/')
        if url_pices[2] in bridge_config["config"]["whitelist"]:
            if len(url_pices) == 6:
                del bridge_config[url_pices[3]][url_pices[4]][url_pices[5]]
            else:
                del bridge_config[url_pices[3]][url_pices[4]]
            if url_pices[3] == "lights":
                del bridge_config["lights_address"][url_pices[4]]
                for light in bridge_config["deconz"]["lights"].keys():
                    if bridge_config["deconz"]["lights"][light]["bridgeid"] == url_pices[4]:
                        del bridge_config["deconz"]["lights"][light]
            if url_pices[3] == "sensors":
                for sensor in bridge_config["deconz"]["sensors"].keys():
                    if bridge_config["deconz"]["sensors"][sensor]["bridgeid"] == url_pices[4]:
                        del bridge_config["deconz"]["sensors"][sensor]
            self.wfile.write(bytes(json.dumps([{"success": "/" + url_pices[3] + "/" + url_pices[4] + " deleted."}]), "utf8"))

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

def run(server_class=ThreadingSimpleServer, handler_class=S):
    server_address = ('', 80)
    httpd = server_class(server_address, handler_class)
    print ('Starting httpd...')
    httpd.serve_forever()

if __name__ == "__main__":
    if bridge_config["deconz"]["enabled"]:
        scanDeconz()
    try:
        if update_lights_on_startup:
            updateAllLights()
        Thread(target=ssdpSearch).start()
        Thread(target=ssdpBroadcast).start()
        Thread(target=schedulerProcessor).start()
        Thread(target=syncWithLights).start()
        run()
    except Exception as e:
        print("server stopped " + str(e))
    finally:
        run_service = False
        saveConfig()
        print ('config saved')
