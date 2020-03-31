import json
import logging
import random
import requests

import socket
import sys

from time import sleep
from subprocess import check_output
from functions import light_types, nextFreeId
from functions.network import getIpAddress


def sendRequest(url, timeout=3):
    head = {"Content-type": "application/json"}
    response = requests.get(url, timeout=timeout, headers=head)
    return response.text


def discover(bridge_config, new_lights):
    logging.debug("shelly: <discover> invoked!")

    device_ips = check_output("nmap  " + getIpAddress() + "/24 -p80 --open -n | grep report | cut -d ' ' -f5",
                              shell=True).decode('utf-8').rstrip("\n").split("\n")
    del device_ips[-1]  # delete last empty element in list
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
                    for light in bridge_config["lights_address"].keys():
                        if bridge_config["lights_address"][light]["protocol"] == "shelly" and \
                                bridge_config["lights_address"][light]["id"] == properties["id"]:
                            device_exist = True
                            bridge_config["lights_address"][light]["ip"] = properties["ip"]
                            logging.debug("shelly: light id " + properties["id"] + " already exist, updating ip...")
                            break
                    if (not device_exist):
                        light_name = "shelly id " + properties["id"][-8:] if properties["name"] == "" else properties[
                            "name"]
                        logging.debug("shelly: Add shelly: " + properties["id"])
                        modelid = "Shelly"
                        new_light_id = nextFreeId(bridge_config, "lights")
                        bridge_config["lights"][new_light_id] = {"state": light_types[modelid]["state"],
                                                                 "type": light_types[modelid]["type"],
                                                                 "name": light_name,
                                                                 "uniqueid": "4a:e0:ad:7f:cf:" + str(
                                                                     random.randrange(0, 99)) + "-1",
                                                                 "modelid": modelid, "manufacturername": "Shelly",
                                                                 "swversion": light_types[modelid]["swversion"]}
                        new_lights.update({new_light_id: {"name": light_name}})
                        bridge_config["lights_address"][new_light_id] = {"ip": properties["ip"], "id": properties["id"],
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
