import json
import logging
import random
from datetime import datetime
from time import strftime
from functions.config import loadConfig, saveConfig, addHueMotionSensor, addHueSwitch
from threading import Thread
from time import sleep

import traceback

# External libraries
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

# internal functions
from functions import light_types, nextFreeId, generate_unique_id
from functions.colors import hsv_to_rgb
from functions.rules import rulesProcessor

client = mqtt.Client()
dxState = {"sensors": {}}

#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Configuration stuff
discoveryPrefix = "homeassistant"
latestStates = {}
discoveredDevices = {}

motionSensors = ["TRADFRI motion sensor", "lumi.sensor_motion.aq2", "lumi.sensor_motion", "SML001"]
standardSensors = ["TRADFRI remote control", "TRADFRI on/off switch"]

standardSensorsData = {"TRADFRI remote control":
                {"structure": {
                    "config": {"alert": "none", "battery": 90, "on": True, "reachable": True}, "manufacturername": "IKEA of Sweden", "name": "Tradfri remote control", "modelid": "TRADFRI remote control",
                    "state": {"buttonevent": 1002, "lastupdated": "2020-02-27T20:32:00"}, "swversion": "1.2.214", "type": "ZHASwitch", "uniqueid": ""},
                "dataConversion": {"rootKey": "action", "toggle": {"buttonevent": 1002}, "arrow_right_click": {"buttonevent": 5002}, "arrow_right_hold": {"buttonevent": 5001}, "arrow_left_click": {"buttonevent": 4002}, "arrow_left_hold": {"buttonevent": 4001}, "brightness_up_click": {"buttonevent": 2002}, "brightness_up_hold": {"buttonevent": 2001}, "brightness_down_click": {"buttonevent": 3002}, "brightness_down_hold": {"buttonevent": 3001}, "brightness_up_release": {"buttonevent": 2003},  "brightness_down_release": {"buttonevent": 3003}, "arrow_left_release": {"buttonevent": 4003}, "arrow_right_release": {"buttonevent": 5003}}},
            "TRADFRI on/off switch":
                {"structure": {
                    "config": {"alert": "none", "battery": 90, "on": True, "reachable": True}, "manufacturername": "IKEA of Sweden", "name": "TRADFRI on/off switch", "modelid": "TRADFRI on/off switch",
                    "state": {"buttonevent": 1002, "lastupdated": "2020-02-27T20:32:00"}, "swversion": "2.2.008", "type": "ZHASwitch", "uniqueid": ""},
                "dataConversion": {"rootKey": "click", "on": {"buttonevent": 1002}, "off": {"buttonevent": 2002}, "brightness_up": {"buttonevent": 1001}, "brightness_down": {"buttonevent": 2001}, "brightness_stop": {"buttonevent": 3001}}}
                }


def findLightSensors(sensors, sensorid):
    lightSensorUID = sensors[sensorid]["uniqueid"][:-1] + "0"
    for sensor in sensors.keys():
        if "uniqueid" in sensors[sensor] and sensors[sensor]["uniqueid"] == lightSensorUID:
            return sensor



# Will get called zero or more times depending on how many lights are available for autodiscovery
def on_autodiscovery_light(msg):
    data = json.loads(msg.payload)
    logging.info("Auto discovery message on: " + msg.topic)
    logging.debug(json.dumps(data, indent=4))
    discoveredDevices[data['unique_id']] = data;

def longPressButton(sensor, buttonevent, bridge_config):
    logging.info("long press detected")
    sleep(1)
    while bridge_config["sensors"][sensor]["state"]["buttonevent"] == buttonevent:
        logging.info("still pressed")
        current_time =  datetime.now()
        dxState["sensors"][sensor] = {"state": {"lastupdated": current_time}}
        rulesProcessor(["sensors",sensor], current_time, bridge_config, dxState)
        sleep(0.5)
    return

# on_message handler (linked to client below)
def on_message(client, userdata, msg):
    try:
        logging.debug("MQTT: got state message on " + msg.topic)
        data = json.loads(msg.payload)
        if msg.topic.startswith(discoveryPrefix + "/light/"):
            on_autodiscovery_light(msg)
        elif msg.topic == "zigbee2mqtt/bridge/config/devices":
            logging.info("MQTT: got state message on " + msg.topic)
            for key in data:
                if "modelID" in key and (key["modelID"] in standardSensors or key["modelID"] in motionSensors): # Sensor is supported
                    if key["friendly_name"] not in userdata["emulator"]["sensors"]: ## Add the new sensor
                        print("Add new mqtt sensor" + key["modelID"])
                        newSensorId = nextFreeId(userdata, "sensors")
                        if key["modelID"] in standardSensorsData and "structure" in standardSensorsData[key["modelID"]]:
                            userdata["sensors"][newSensorId] = standardSensorsData[key["modelID"]]["structure"]
                            userdata["sensors"][newSensorId]["uniqueid"] = convertHexToMac(key["ieeeAddr"]) + "-01-1000"
                            userdata["sensors"][newSensorId]["name"] = key["friendly_name"]
                            userdata["emulator"]["sensors"][key["friendly_name"]] = {"bridgeId": newSensorId, "modelid": key["modelID"]}
                        ### TRADFRI Motion Sensor, Xiaomi motion sensor, etc
                        elif key["modelID"] in motionSensors:
                            logging.info("MQTT: add new motion sensor " + key["modelID"])
                            newSensorId = addHueMotionSensor("", userdata, name=key["friendly_name"])
                            userdata["emulator"]["sensors"][key["ieeeAddr"]] = {"bridgeId": newSensorId, "modelid": key["modelID"], "lightSensor": "on"}
        else:
            device = msg.topic.split("/")[1]
            if device in userdata["emulator"]["sensors"]:
                bridgeId = userdata["emulator"]["sensors"][device]["bridgeId"]
                if userdata["sensors"][bridgeId]["config"]["on"] == False:
                    return
                current_time =  datetime.now()
                convertedPayload = {"lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}
                dxState["sensors"][bridgeId] = {"state": {}}
                if ("action" in data and data["action"] == "") or ("click" in data and data["click"] == ""):
                    return
                ### If is a motion sensor update the light level
                if userdata["sensors"][userdata["emulator"]["sensors"][device]["bridgeId"]]["modelid"] in motionSensors:
                    convertedPayload["presence"] = data["occupancy"]
                    lightPayload = {"lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}
                    lightSensor = findLightSensors(userdata["sensors"], userdata["emulator"]["sensors"][device]["bridgeId"])
                    if userdata["emulator"]["sensors"][device]["lightSensor"] == "on": # use build it light senor or the daylight logical sensor
                        if "illuminance_lux" in data:
                            if data["illuminance_lux"] > 10:
                                lightPayload["dark"] = False
                            else:
                                lightPayload["dark"] = True
                        else:
                            lightPayload["dark"] = not userdata["sensors"]["1"]["state"]["daylight"]
                    else: # is always dark
                        lightPayload["dark"] = True
                    if  lightPayload["dark"]:
                        lightPayload["lightlevel"] = 6000
                    else:
                        lightPayload["lightlevel"] = 25000
                    lightPayload["daylight"] = not lightPayload["dark"]
                    userdata["sensors"][lightSensor]["state"].update(lightPayload)
                    dxState["sensors"][lightSensor] = {"state": {"dark": current_time}}
                elif userdata["sensors"][userdata["emulator"]["sensors"][device]["bridgeId"]]["modelid"] in standardSensors:
                    convertedPayload = standardSensorsData[userdata["emulator"]["sensors"][device]["modelid"]]["dataConversion"][data[standardSensorsData[userdata["emulator"]["sensors"][device]["modelid"]]["dataConversion"]["rootKey"]]]

                userdata["sensors"][bridgeId]["state"].update(convertedPayload)
                for key in convertedPayload.keys():
                    dxState["sensors"][bridgeId]["state"][key] = current_time
                if "buttonevent" in  convertedPayload and convertedPayload["buttonevent"] in [1001, 2001, 3001, 4001, 5001]:
                    Thread(target=longPressButton, args=[userdata["emulator"]["sensors"][device]["bridgeId"], convertedPayload["buttonevent"], userdata]).start()
                rulesProcessor(["sensors", userdata["emulator"]["sensors"][device]["bridgeId"]], current_time, userdata, dxState)
            on_state_update(msg)
    except:
        traceback.print_exc()

def on_state_update(msg):
    logging.debug("MQTT: got state message on " + msg.topic)
    data = json.loads(msg.payload)
    latestStates[msg.topic] = data
    logging.debug(json.dumps(data, indent=4))


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
        client.publish(messages[0]["topic"], messages[0]["payload"])

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

def discover(bridge_config, new_lights):
    logging.info("MQTT discovery called")
    for key, data in discoveredDevices.items():
        device_new = True
        for lightkey in bridge_config["lights_address"].keys():
            if bridge_config["lights_address"][lightkey]["protocol"] == "mqtt" and bridge_config["lights_address"][lightkey]["uid"] == key:
                device_new = False
                bridge_config["lights_address"][lightkey]["command_topic"] = data["command_topic"]
                bridge_config["lights_address"][lightkey]["state_topic"] = data["state_topic"]
                break

        if device_new:
            light_name = data["device"]["name"] if data["device"]["name"] is not None else data["name"]
            logging.debug("MQTT: Adding light " + light_name)
            new_light_id = nextFreeId(bridge_config, "lights")

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

            bridge_config["lights"][new_light_id] = {"state": light_types[modelid]["state"], "type": light_types[modelid]["type"], "name": light_name, "uniqueid": generate_unique_id(), "modelid": modelid, "manufacturername": "Philips", "swversion": light_types[modelid]["swversion"]}
            new_lights.update({new_light_id: {"name": light_name}})

            # Add the lights to new lights, so it shows up in the search screen
            new_lights.update({new_light_id: {"name": light_name}})

            # Save the mqtt parameters
            bridge_config["lights_address"][new_light_id] = { "protocol": "mqtt", "uid": data["unique_id"], "ip":"mqtt", "state_topic": data["state_topic"], "command_topic": data["command_topic"]}

    ### Discover Sensors

    client.publish("zigbee2mqtt/bridge/config/devices/get", "")

def convertHexToMac(hexValue):
    s = '{0:016x}'.format(int(hexValue,16))
    s = ':'.join(s[i:i + 2] for i in range(0, 16, 2))
    return s

# on_connect handler (linked to client below)
def on_connect(client, userdata, flags, rc):
    logging.debug("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # Start autodetection on lights
    autodiscoveryTopic = discoveryPrefix + "/light/+/light/config" # + in topic is wildcard
    client.subscribe(autodiscoveryTopic)
    client.subscribe("zigbee2mqtt/+")
    client.subscribe("zigbee2mqtt/bridge/config/devices")

def mqttServer(bridge_config):
    # ================= MQTT CLIENT Connection========================
    # Set user/password on client if supplied
    if bridge_config["emulator"]["mqtt"]["mqttUser"] != "" and bridge_config["emulator"]["mqtt"]["mqttPassword"] != "":
        client.username_pw_set(bridge_config["emulator"]["mqtt"]["mqttUser"],bridge_config["emulator"]["mqtt"]["mqttPassword"])

    if bridge_config["emulator"]["mqtt"]['discoveryPrefix'] is not None:
        discoveryPrefix = bridge_config["emulator"]["mqtt"]['discoveryPrefix']

    # Setup handlers
    client.on_connect = on_connect
    client.on_message = on_message
    # Connect to the server
    client.connect(bridge_config["emulator"]["mqtt"]["mqttServer"], bridge_config["emulator"]["mqtt"]["mqttPort"])

    client.user_data_set(bridge_config)


    # start the loop to keep receiving data
    client.loop_forever()
