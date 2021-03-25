import json
import logging
import random
import requests
import socket
import sys
#import configManager
from time import sleep
from subprocess import check_output
import lights
from functions.network import getIpAddress


#bridgeConfig = configManager.bridgeConfig.yaml_config
#newLights = configManager.runtimeConfig.newLights

def sendRequest(url, timeout=3):
    head = {"Content-type": "application/json"}
    response = requests.get(url, timeout=timeout, headers=head)
    return response.text


def discover(device_ips):
    logging.debug("shelly: <discover> invoked!")
    for ip in device_ips:
        logging.debug("shelly: found ip: " + ip)
        try:
            logging.debug("shelly: probing ip " + ip)
            response = requests.get("http://" + ip + "/shelly", timeout=5)
            if response.status_code == 200:
                device_data = json.loads(response.text)
                if device_data["type"] == "SHSW-1":

                    logging.debug("shelly: " + ip + " is a shelly device ")
                    shelly_response = requests.get("http://" + ip + "/status", timeout=5)
                    shelly_data = json.loads(shelly_response.text)
                    logging.debug("shelly: ip: " + shelly_data["wifi_sta"]["ip"])
                    logging.debug("shelly: Mac:      " + shelly_data["mac"])

                    properties = {"ip": ip, "name": ip, "id": shelly_data["mac"], "mac": shelly_data["mac"]}
                    device_exist = False
                    for light in bridgeConfig["lights_address"].keys():
                        if bridgeConfig["lights_address"][light]["protocol"] == "shelly" and \
                                bridgeConfig["lights_address"][light]["id"] == properties["id"]:
                            device_exist = True
                            bridgeConfig["lights_address"][light]["ip"] = properties["ip"]
                            logging.debug("shelly: light id " + properties["id"] + " already exist, updating ip...")
                            break
                    if (not device_exist):
                        light_name = "shelly id " + properties["id"][-8:] if properties["name"] == "" else properties[
                            "name"]
                        logging.debug("shelly: Add shelly: " + properties["id"])
                        modelid = "Shelly"
                        new_light_id = nextFreeId(bridgeConfig, "lights")
                        bridgeConfig["lights"][new_light_id] = {"state": light_types[modelid]["state"],
                                                                 "type": light_types[modelid]["type"],
                                                                 "name": light_name,
                                                                 "uniqueid": "4a:e0:ad:7f:cf:" + str(
                                                                     random.randrange(0, 99)) + "-1",
                                                                 "modelid": modelid, "manufacturername": "Shelly",
                                                                 "swversion": light_types[modelid]["swversion"]}
                        newLights.update({new_light_id: {"name": light_name}})
                        bridgeConfig["lights_address"][new_light_id] = {"ip": properties["ip"], "id": properties["id"],
                                                                         "protocol": "shelly"}

        except Exception as e:
            logging.debug("shelly: ip " + ip + " is unknow device, " + str(e))


def set_light(address, light, data):
    logging.debug("shelly: <set_light> invoked! IP=" + address["ip"])

    for key, value in data.items():
        if key == "on":
            if value:
                sendRequest("http://" + address["ip"] + "/relay/0/?turn=on")
            else:
                sendRequest("http://" + address["ip"] + "/relay/0/?turn=off")


def get_light_state(address, light):
    logging.debug("shelly: <get_light_state> invoked!")
    data = sendRequest("http://" + address["ip"] + "/relay/0")
    light_data = json.loads(data)
    state = {}

    if 'ison' in light_data:
        state['on'] = True if light_data["ison"] == "true" else False
    return state
