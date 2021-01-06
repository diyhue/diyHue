import logManager
import configManager
import json
import random
import requests
from datetime import datetime
from time import strftime
from functions.core import addHueMotionSensor, addHueSwitch
from threading import Thread
import traceback

# External
import paho.mqtt.publish as publish

# internal functions
from functions.colors import hsv_to_rgb
from functions.rules import rulesProcessor

logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.json_config
newLights = configManager.runtimeConfig.newLights


def set_light(address, lights, data):
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

    logging.debug("MQTT publish to: " + json.dumps(messages))
    auth = None
    if bridgeConfig["emulator"]["mqtt"]["mqttUser"] != "" and bridgeConfig["emulator"]["mqtt"]["mqttPassword"] != "":
        auth = {'username':bridgeConfig["emulator"]["mqtt"]["mqttUser"], 'password':bridgeConfig["emulator"]["mqtt"]["mqttPassword"]}
    publish.multiple(messages, hostname=bridgeConfig["emulator"]["mqtt"]["mqttServer"], port=bridgeConfig["emulator"]["mqtt"]["mqttPort"], auth=auth)

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
    if bridgeConfig["emulator"]["mqtt"]["enabled"]:
        logging.info("MQTT discovery called")
        auth = None
        if bridgeConfig["emulator"]["mqtt"]["mqttUser"] != "" and bridgeConfig["emulator"]["mqtt"]["mqttPassword"] != "":
            auth = {'username':bridgeConfig["emulator"]["mqtt"]["mqttUser"], 'password':bridgeConfig["emulator"]["mqtt"]["mqttPassword"]}
        publish.single("zigbee2mqtt/bridge/config/devices/get", hostname=bridgeConfig["emulator"]["mqtt"]["mqttServer"], port=bridgeConfig["emulator"]["mqtt"]["mqttPort"], auth=auth)
