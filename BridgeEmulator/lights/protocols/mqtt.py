import logManager
import json
import random
import requests
from datetime import datetime
from time import strftime
from threading import Thread
import traceback

# External
import paho.mqtt.publish as publish

# internal functions
from functions.colors import hsv_to_rgb

logging = logManager.logger.get_logger(__name__)

def xy_to_hex(x, y):
    z = 1.0 - x - y
    Y = 1.0
    X = (Y / y) * x
    Z = (Y / y) * z
    r = X * 3.240 - Y * 1.537 - Z * 0.499
    g = -X * 0.969 + Y * 1.877 + Z * 0.042
    b = X * 0.056 - Y * 0.204 + Z * 1.057
    r = 12.92 * r if r <= 0.0031308 else (1.0 + 0.055) * (r **(1.0 / 2.4)) - 0.055
    g = 12.92 * g if g <= 0.0031308 else (1.0 + 0.055) * (g **(1.0 / 2.4)) - 0.055
    b = 12.92 * b if b <= 0.0031308 else (1.0 + 0.055) * (b **(1.0 / 2.4)) - 0.055

    maxValue = max(r, g, b)
    r /= maxValue
    g /= maxValue
    b /= maxValue

    r = 0 if r * 255 < 0 else r * 255
    g = 0 if g * 255 < 0 else g * 255
    b = 0 if b * 255 < 0 else b * 255
    r = format(int(round(r)), '02x')
    g = format(int(round(g)), '02x')
    b = format(int(round(b)), '02x')

    return "#" + r + g + b


def set_light(light, data):
    messages = []
    lightsData = {}

    if "lights" not in data:
        lightsData = {light.protocol_cfg["command_topic"]: data}
    else:
        lightsData = data["lights"]

    for topic in lightsData.keys():
        payload = {"transition": 0.3}
        colorFromHsv = False
        for key, value in lightsData[topic].items():
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
            if key == "alert" and value != "none":
                payload['alert'] = value
            if key == "transitiontime":
                payload['transition'] = value / 10
            if key == "gradient":
                gradient = list(map(lambda color: xy_to_hex(color['color']['xy']['x'], color['color']['xy']['y']), value['points']))
                gradient.reverse()
                payload['gradient'] = gradient
        if colorFromHsv:
            color = hsv_to_rgb(data['hue'], data['sat'], light.state["bri"])
            payload['color'] = { 'r': color[0], 'g': color[1], 'b': color[2] }
        messages.append({"topic": topic, "payload": json.dumps(payload)})
    logging.debug("MQTT publish to: " + json.dumps(messages))
    auth = None
    if light.protocol_cfg["mqtt_server"]["mqttUser"] != "" and light.protocol_cfg["mqtt_server"]["mqttPassword"] != "":
        auth = {'username':  light.protocol_cfg["mqtt_server"]["mqttUser"], 'password':  light.protocol_cfg["mqtt_server"]["mqttPassword"]}
    publish.multiple(messages, hostname= light.protocol_cfg["mqtt_server"]["mqttServer"], port= light.protocol_cfg["mqtt_server"]["mqttPort"], auth=auth)

def get_light_state(light):
    return {}

def discover(mqtt_config):
    if mqtt_config["enabled"]:
        logging.info("MQTT discovery called")
        auth = None
        if mqtt_config["mqttUser"] != "" and mqtt_config["mqttPassword"] != "":
            auth = {'username': mqtt_config["mqttUser"], 'password': mqtt_config["mqttPassword"]}
        try:
            publish.single("zigbee2mqtt/bridge/request/permit_join", json.dumps({"value": True, "time": 120}), hostname=mqtt_config["mqttServer"], port=mqtt_config["mqttPort"], auth=auth)
            publish.single("zigbee2mqtt/bridge/config/devices/get", hostname=mqtt_config["mqttServer"], port=mqtt_config["mqttPort"], auth=auth)
        except Exception as e:
            print (str(e))
