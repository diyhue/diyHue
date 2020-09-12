import json
import logging
import random
import requests
from datetime import datetime
from time import strftime
from functions.devicesRules import addHueMotionSensor, addHueSwitch
from threading import Thread
import configManager

import traceback

# External
import paho.mqtt.publish as publish

# internal functions
from functions.colors import hsv_to_rgb
from functions.rules import rulesProcessor

bridgeConfig = configManager.bridgeConfig.json_config
newLights = configManager.runtimeConfig.newLights


def set_light(address, light, data):
    messages = []
    lightsData = {}

    if "lights" not in data:
        lightsData = {address["command_topic"]: data}
    else:
        lightsData = data["lights"]

    for light in lightsData.keys():
        payload = {"transition": 0.3}
        colorFromHsv = False
        for key, value in lightsData[light].items():
            if key == "on":
                payload['state'] = "ON" if value == True else "OFF"
            if key == "bri":
                payload['brightness'] = value
            if key == "xy":
                payload['color'] = {'x': value[0], 'y': value[1]}
            if key == "ct":
                payload["color_temp"] = value
            if key == "hue" or key == "sat":
                colorFromHsv = True
            if key == "alert":
                payload['alert'] = value
            if key == "transitiontime":
                payload['transition'] = value / 10

        if colorFromHsv:
            color = hsv_to_rgb(data['hue'], data['sat'], light["state"]["bri"])
            payload['color'] = { 'r': color[0], 'g': color[1], 'b': color[2] }
        messages.append({"topic": light, "payload": json.dumps(payload)})

    if "mqtt" in data:
        logging.debug("MQTT publish to multiple: " + json.dumps(messages))
        auth = None
        if data["mqtt"]["mqttUser"] != "" and data["mqtt"]["mqttPassword"] != "":
            auth = {'username':data["mqtt"]["mqttUser"], 'password':data["mqtt"]["mqttPassword"]}
        publish.multiple(messages, hostname=data["mqtt"]["mqttServer"], port=data["mqtt"]["mqttPort"], auth=auth)
    else:
        logging.debug("MQTT publish to " + messages[0]["topic"] + " " + messages[0]["payload"])
        publish.single(messages[0]["topic"], payload=messages[0]["payload"], hostname=data["mqtt"]["mqttServer"], port=data["mqtt"]["mqttPort"], auth=auth)

def get_light_state(address, light):
    if latestStates[address['state_topic']] is None:
        return { 'reachable': False }
    state = { 'reachable': True }
    mqttState = latestStates[address['state_topic']]
    for key, value in mqttState.items():
        if key == "state":
            state['on'] = (value == 'ON')
        if key == "brightness":
            state['bri'] = value
        if key == "color":
            state["colormode"] = "xy"
            state['xy'] = [value['x'], value['y']]

    return state

def discover():
    logging.info("MQTT discovery called")
    auth = None
    if bridgeConfig["emulator"]["mqtt"]["mqttUser"] != "" and bridgeConfig["emulator"]["mqtt"]["mqttPassword"] != "":
        auth = {'username':bridgeConfig["emulator"]["mqtt"]["mqttUser"], 'password':bridgeConfig["emulator"]["mqtt"]["mqttPassword"]}
    publish.single("zigbee2mqtt/bridge/config/devices/get", hostname=bridgeConfig["emulator"]["mqtt"]["mqttServer"], port=bridgeConfig["emulator"]["mqtt"]["mqttPort"], auth=auth)


    for key, data in discoveredDevices.items():
        device_new = True
        for lightkey in bridgeConfig["emulator"]["lights"].keys():
            if bridgeConfig["emulator"]["lights"][lightkey]["protocol"] == "mqtt" and bridgeConfig["emulator"]["lights"][lightkey]["uid"] == key:
                device_new = False
                bridgeConfig["emulator"]["lights"][lightkey]["command_topic"] = data["command_topic"]
                bridgeConfig["emulator"]["lights"][lightkey]["state_topic"] = data["state_topic"]
                break

        if device_new:
            light_name = data["device"]["name"] if data["device"]["name"] is not None else data["name"]
            logging.debug("MQTT: Adding light " + light_name)
            new_light_id = nextFreeId(bridgeConfig, "lights")

            # Device capabilities
            keys = data.keys()
            light_color = "xy" in keys and data["xy"] == True
            light_brightness = "brightness" in keys and data["brightness"] == True
            light_ct = "ct" in keys and data["ct"] == True

            modelid = None
            if light_color and light_ct:
                modelid = "LCT015"
            elif light_color: # Every light as LCT001? Or also support other lights
                modelid = "LCT001"
            elif light_brightness:
                modelid = "LWB010"
            elif light_ct:
                modelid = "LTW001"
            else:
                modelid = "Plug 01"

            bridgeConfig["lights"][new_light_id] = {"state": light_types[modelid]["state"], "type": light_types[modelid]["type"], "name": light_name, "uniqueid": generate_unique_id(), "modelid": modelid, "manufacturername": "Philips", "swversion": light_types[modelid]["swversion"]}
            newLights.update({new_light_id: {"name": light_name}})

            # Add the lights to new lights, so it shows up in the search screen
            newLights.update({new_light_id: {"name": light_name}})

            # Save the mqtt parameters
            bridgeConfig["emulator"]["lights"][new_light_id] = { "protocol": "mqtt", "uid": data["unique_id"], "ip":"mqtt", "state_topic": data["state_topic"], "command_topic": data["command_topic"]}
