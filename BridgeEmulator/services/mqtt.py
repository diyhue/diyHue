import logManager
import configManager
import json
import random
import paho.mqtt.client as mqtt
from datetime import datetime
from threading import Thread
from functions.core import nextFreeId, addNewLight, addHueMotionSensor, longPressButton, generateDxState
from functions.rules import rulesProcessor


logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.json_config
newLights = configManager.runtimeConfig.newLights
dxState = configManager.runtimeConfig.dxState

client = mqtt.Client()

# Configuration stuff
discoveryPrefix = "homeassistant"
latestStates = {}
discoveredDevices = {}


motionSensors = ["TRADFRI motion sensor", "lumi.sensor_motion.aq2", "lumi.sensor_motion", "SML001"]
standardSensors = ["TRADFRI remote control", "TRADFRI on/off switch", "TRADFRI wireless dimmer"]

standardSensorsData = {"TRADFRI remote control":
                {"structure": {
                    "config": {"alert": "none", "battery": 90, "on": True, "reachable": True}, "manufacturername": "IKEA of Sweden", "name": "Tradfri remote control", "modelid": "TRADFRI remote control",
                    "state": {"buttonevent": 1002, "lastupdated": "none"}, "swversion": "1.2.214", "type": "ZHASwitch", "uniqueid": ""},
                "dataConversion": {"rootKey": "action", "toggle": {"buttonevent": 1002}, "arrow_right_click": {"buttonevent": 5002}, "arrow_right_hold": {"buttonevent": 5001}, "arrow_left_click": {"buttonevent": 4002}, "arrow_left_hold": {"buttonevent": 4001}, "brightness_up_click": {"buttonevent": 2002}, "brightness_up_hold": {"buttonevent": 2001}, "brightness_down_click": {"buttonevent": 3002}, "brightness_down_hold": {"buttonevent": 3001}, "brightness_up_release": {"buttonevent": 2003},  "brightness_down_release": {"buttonevent": 3003}, "arrow_left_release": {"buttonevent": 4003}, "arrow_right_release": {"buttonevent": 5003}}},
            "TRADFRI on/off switch":
                {"structure": {
                    "config": {"alert": "none", "battery": 90, "on": True, "reachable": True}, "manufacturername": "IKEA of Sweden", "name": "TRADFRI on/off switch", "modelid": "TRADFRI on/off switch",
                    "state": {"buttonevent": 1002, "lastupdated": "none"}, "swversion": "2.2.008", "type": "ZHASwitch", "uniqueid": ""},
                "dataConversion": {"rootKey": "click", "on": {"buttonevent": 1002}, "off": {"buttonevent": 2002}, "brightness_up": {"buttonevent": 1001}, "brightness_down": {"buttonevent": 2001}, "brightness_stop": {"buttonevent": 3001}}},
            "TRADFRI wireless dimmer":
                {"structure": {
                    "config": {"alert": "none", "battery": 90, "on": True, "reachable": True}, "manufacturername": "IKEA of Sweden", "name": "TRADFRI wireless dimmer", "modelid": "TRADFRI wireless dimmer",
                    "state": {"buttonevent": 1002, "lastupdated": "none"}, "swversion": "1.2.248", "type": "ZHASwitch", "uniqueid": ""},
                "dataConversion": {"rootKey": "action", "rotate_right_quick": {"buttonevent": 1002}, "rotate_right": {"buttonevent": 2002}, "rotate_left": {"buttonevent": 3002}, "rotate_left_quick": {"buttonevent": 4002}, "rotate_stop": {}, "": {}}}
                }


# Will get called zero or more times depending on how many lights are available for autodiscovery
def on_autodiscovery_light(msg):
    data = json.loads(msg.payload)
    logging.info("Auto discovery message on: " + msg.topic)
    logging.debug(json.dumps(data, indent=4))
    discoveredDevices[data['unique_id']] = data;
    for key, data in discoveredDevices.items():
        device_new = True
        for lightkey in bridgeConfig["emulator"]["lights"].keys():
            if bridgeConfig["emulator"]["lights"][lightkey]["protocol"] == "mqtt" and bridgeConfig["emulator"]["lights"][lightkey]["uid"] == key:
                device_new = False
                bridgeConfig["emulator"]["lights"][lightkey]["command_topic"] = data["command_topic"]
                bridgeConfig["emulator"]["lights"][lightkey]["state_topic"] = data["state_topic"]
                break

        if device_new:
            lightName = data["device"]["name"] if data["device"]["name"] is not None else data["name"]
            logging.debug("MQTT: Adding light " + lightName)
            new_light_id = nextFreeId(bridgeConfig, "lights")

            # Device capabilities
            keys = data.keys()
            light_color = "xy" in keys and data["xy"] == True
            light_brightness = "brightness" in keys and data["brightness"] == True
            light_ct = "color_temp" in keys and data["color_temp"] == True

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

            emulatorLightConfig = { "protocol": "mqtt",
                                    "uid": data["unique_id"],
                                    "ip":"mqtt",
                                    "state_topic": data["state_topic"],
                                    "command_topic": data["command_topic"]}

            addNewLight(modelid, lightName, emulatorLightConfig)
            generateDxState()



def on_state_update(msg):
    #logging.debug("MQTT: got state message on " + msg.topic)
    data = json.loads(msg.payload)
    latestStates[msg.topic] = data
    logging.debug(json.dumps(data, indent=4))

# on_message handler (linked to client below)
def on_message(client, userdata, msg):
    try:
        current_time =  datetime.now()
        logging.debug("MQTT: got state message on " + msg.topic)
        data = json.loads(msg.payload)
        print(msg.payload)
        if msg.topic.startswith(discoveryPrefix + "/light/"):
            on_autodiscovery_light(msg)
        elif msg.topic == "zigbee2mqtt/bridge/config/devices":
            for key in data:
                if "modelID" in key and (key["modelID"] in standardSensors or key["modelID"] in motionSensors): # Sensor is supported
                    if key["friendly_name"] not in bridgeConfig["emulator"]["sensors"]: ## Add the new sensor
                        logging.info("MQTT: Add new mqtt sensor " + key["modelID"])
                        newSensorId = nextFreeId(bridgeConfig, "sensors")
                        if "modelID" in key:
                            if key["modelID"] in standardSensorsData and "structure" in standardSensorsData[key["modelID"]]:
                                sensor = standardSensorsData[key["modelID"]]["structure"]
                                sensor["uniqueid"] = convertHexToMac(key["ieeeAddr"]) + "-01-1000"
                                sensor["name"] = key["friendly_name"]
                                bridgeConfig["sensors"][newSensorId] = sensor.copy()
                                bridgeConfig["emulator"]["sensors"][key["friendly_name"]] = {"bridgeId": newSensorId, "modelid": key["modelID"], "protocol": "mqtt"}
                            ### TRADFRI Motion Sensor, Xiaomi motion sensor, etc
                            elif key["modelID"] in motionSensors:
                                logging.info("MQTT: add new motion sensor " + key["modelID"])
                                newSensorId = addHueMotionSensor("", name=key["friendly_name"])
                                bridgeConfig["emulator"]["sensors"][key["friendly_name"]] = {"bridgeId": newSensorId, "modelid": key["modelID"], "lightSensor": "on", "protocol": "mqtt"}
                            else:
                                pprint(key)
                                logging.info("MQTT: unsupported sensor " + key["modelID"])
                            generateDxState()
        else:
            device = msg.topic.split("/")[1]
            if device in bridgeConfig["emulator"]["sensors"]:
                bridgeId = bridgeConfig["emulator"]["sensors"][device]["bridgeId"]
                if "battery" in data:
                    bridgeConfig["sensors"][bridgeId]["config"]["battery"] = int(data["battery"])
                if bridgeConfig["sensors"][bridgeId]["config"]["on"] == False:
                    return
                convertedPayload = {"lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}
                dxState["sensors"][bridgeId] = {"state": {}}
                if ("action" in data and data["action"] == "") or ("click" in data and data["click"] == ""):
                    return
                ### If is a motion sensor update the light level and temperature
                if bridgeConfig["sensors"][bridgeConfig["emulator"]["sensors"][device]["bridgeId"]]["modelid"] in motionSensors:
                    convertedPayload["presence"] = data["occupancy"]
                    lightPayload = {"lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}
                    lightSensor = findLightSensor(bridgeConfig["sensors"], bridgeConfig["emulator"]["sensors"][device]["bridgeId"])
                    if "temperature" in data:
                        tempSensor = findTempSensor(bridgeConfig["sensors"], bridgeConfig["emulator"]["sensors"][device]["bridgeId"])
                        bridgeConfig["sensors"][tempSensor]["state"] = {"temperature": int(data["temperature"] * 100), "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}
                    if "illuminance" in data:
                        if data["illuminance"] > 10:
                            lightPayload["dark"] = False
                        else:
                            lightPayload["dark"] = True
                    elif bridgeConfig["emulator"]["sensors"][device]["lightSensor"] == "on":
                        lightPayload["dark"] = not bridgeConfig["sensors"]["1"]["state"]["daylight"]
                    else: # is always dark
                        lightPayload["dark"] = True

                    if  lightPayload["dark"]:
                        lightPayload["lightlevel"] = 6000
                    else:
                        lightPayload["lightlevel"] = 25000
                    lightPayload["daylight"] = not lightPayload["dark"]
                    bridgeConfig["sensors"][lightSensor]["state"].update(lightPayload)
                    dxState["sensors"][lightSensor] = {"state": {"dark": current_time}}

                    # send email if alarm is enabled:
                    if data["occupancy"] and bridgeConfig["emulator"]["alarm"]["on"] and bridgeConfig["emulator"]["alarm"]["lasttriggered"] + 300 < current_time.timestamp():
                        logging.info("Alarm triggered, sending email...")
                        requests.post("https://diyhue.org/cdn/mailNotify.php", json={"to": bridgeConfig["emulator"]["alarm"]["email"], "sensor": bridgeConfig["sensors"][bridgeId]["name"]}, timeout=10)
                        bridgeConfig["emulator"]["alarm"]["lasttriggered"] = int(current_time.timestamp())

                elif bridgeConfig["sensors"][bridgeConfig["emulator"]["sensors"][device]["bridgeId"]]["modelid"] in standardSensors:
                    convertedPayload = standardSensorsData[bridgeConfig["emulator"]["sensors"][device]["modelid"]]["dataConversion"][data[standardSensorsData[bridgeConfig["emulator"]["sensors"][device]["modelid"]]["dataConversion"]["rootKey"]]]

                bridgeConfig["sensors"][bridgeId]["state"].update(convertedPayload)
                for key in convertedPayload.keys():
                    dxState["sensors"][bridgeId]["state"][key] = current_time
                if "buttonevent" in  convertedPayload and convertedPayload["buttonevent"] in [1001, 2001, 3001, 4001, 5001]:
                    Thread(target=longPressButton, args=[bridgeConfig["emulator"]["sensors"][device]["bridgeId"], convertedPayload["buttonevent"]]).start()
                rulesProcessor(["sensors", bridgeConfig["emulator"]["sensors"][device]["bridgeId"]], current_time)

            on_state_update(msg)
    except:
        traceback.print_exc()

def findLightSensor(sensors, sensorid):
    lightSensorUID = sensors[sensorid]["uniqueid"][:-1] + "0"
    for sensor in sensors.keys():
        if "uniqueid" in sensors[sensor] and sensors[sensor]["uniqueid"] == lightSensorUID:
            return sensor

def findTempSensor(sensors, sensorid):
    tempSensprUID = sensors[sensorid]["uniqueid"][:-1] + "2"
    for sensor in sensors.keys():
        if "uniqueid" in sensors[sensor] and sensors[sensor]["uniqueid"] == tempSensprUID:
            return sensor
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

def mqttServer():
    logging.info("Strting MQTT service...")
    # ================= MQTT CLIENT Connection========================
    # Set user/password on client if supplied
    if bridgeConfig["emulator"]["mqtt"]["mqttUser"] != "" and bridge_config["emulator"]["mqtt"]["mqttPassword"] != "":
        client.username_pw_set(bridgeConfig["emulator"]["mqtt"]["mqttUser"],bridgeConfig["emulator"]["mqtt"]["mqttPassword"])

    if bridgeConfig["emulator"]["mqtt"]['discoveryPrefix'] is not None:
        discoveryPrefix = bridgeConfig["emulator"]["mqtt"]['discoveryPrefix']
    # Setup handlers
    client.on_connect = on_connect
    client.on_message = on_message
    # Connect to the server
    client.connect(bridgeConfig["emulator"]["mqtt"]["mqttServer"], bridgeConfig["emulator"]["mqtt"]["mqttPort"])

    # start the loop to keep receiving data
    client.loop_forever()
