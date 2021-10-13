import logManager
import configManager
import json
import math
import weakref
import HueObjects
import paho.mqtt.client as mqtt
from datetime import datetime
from threading import Thread
from time import sleep
from functions.core import nextFreeId
from sensors.discover import addHueMotionSensor
from sensors.sensor_types import sensorTypes
from lights.discover import addNewLight
from functions.rules import rulesProcessor

logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config
client = mqtt.Client()

devices_ids = {}

# Configuration stuff
discoveryPrefix = "homeassistant"
latestStates = {}
discoveredDevices = {}


motionSensors = ["TRADFRI motion sensor", "lumi.sensor_motion.aq2", "lumi.sensor_motion", "SML001"]
standardSensors = {
            "TRADFRI remote control": {
                "dataConversion": {"rootKey": "action", "toggle": {"buttonevent": 1002}, "arrow_right_click": {"buttonevent": 5002}, "arrow_right_hold": {"buttonevent": 5001}, "arrow_left_click": {"buttonevent": 4002}, "arrow_left_hold": {"buttonevent": 4001}, "brightness_up_click": {"buttonevent": 2002}, "brightness_up_hold": {"buttonevent": 2001}, "brightness_down_click": {"buttonevent": 3002}, "brightness_down_hold": {"buttonevent": 3001}, "brightness_up_release": {"buttonevent": 2003},  "brightness_down_release": {"buttonevent": 3003}, "arrow_left_release": {"buttonevent": 4003}, "arrow_right_release": {"buttonevent": 5003}}},
            "TRADFRI on/off switch": {
                "dataConversion": {"rootKey": "click", "on": {"buttonevent": 1002}, "off": {"buttonevent": 2002}, "brightness_up": {"buttonevent": 1001}, "brightness_down": {"buttonevent": 2001}, "brightness_stop": {"buttonevent": 3001}}},
            "TRADFRI wireless dimmer": {
                "dataConversion": {"rootKey": "action", "rotate_right_quick": {"buttonevent": 1002}, "rotate_right": {"buttonevent": 2002}, "rotate_left": {"buttonevent": 3002}, "rotate_left_quick": {"buttonevent": 4002}, "rotate_stop": {}, "": {}}},
            "RWL021": {
                "dataConversion": {"rootKey": "action", "on_press": {"buttonevent": 1002}, "on_hold": {"buttonevent": 1001}, "on_hold_release": {"buttonevent": 1003}, "up_press": {"buttonevent": 2000}, "up_hold": {"buttonevent": 2001}, "up_hold_release": {"buttonevent": 2002}, "down_press": {"buttonevent": 3000}, "down_hold": {"buttonevent": 3001}, "down_hold_release": {"buttonevent": 3002}, "off_press": {"buttonevent": 4000} }},
            "RWL022": {
                "dataConversion": {"rootKey": "action", "on_press": {"buttonevent": 1002}, "on_hold": {"buttonevent": 1001}, "on_hold_release": {"buttonevent": 1003}, "up_press": {"buttonevent": 2000}, "up_hold": {"buttonevent": 2001}, "up_hold_release": {"buttonevent": 2002}, "down_press": {"buttonevent": 3000}, "down_hold": {"buttonevent": 3001}, "down_hold_release": {"buttonevent": 3002}, "off_press": {"buttonevent": 4000} }}
            }

def getClient():
    return client

def longPressButton(sensor, buttonevent):
    print("running.....")
    logging.info("long press detected")
    sleep(1)
    while sensor.state["buttonevent"] == buttonevent:
        logging.info("still pressed")
        current_time =  datetime.now()
        sensor.dxState["lastupdated"] = current_time
        rulesProcessor(sensor, current_time)
        sleep(0.5)
    return


def getObject(friendly_name):
    if friendly_name in devices_ids:
        logging.debug("Cache Hit for " + friendly_name)
        return devices_ids[friendly_name]()
    else:
        for resource in ["sensors", "lights"]:
            for key, device in bridgeConfig[resource].items():
                if device.protocol == "mqtt":
                    if "friendly_name" in device.protocol_cfg and device.protocol_cfg["friendly_name"] == friendly_name:
                        if device.modelid == "SML001" and device.type != "ZLLPresence":
                            continue
                        devices_ids[friendly_name] = weakref.ref(device)
                        logging.debug("Cache Miss " + friendly_name)
                        return device
                    elif "state_topic" in device.protocol_cfg and device.protocol_cfg["state_topic"] == "zigbee2mqtt/" + friendly_name:
                        devices_ids[friendly_name] = weakref.ref(device)
                        logging.debug("Cache Miss " + friendly_name)
                        return device
        logging.debug("Device not found for " + friendly_name)
        return False

# Will get called zero or more times depending on how many lights are available for autodiscovery
def on_autodiscovery_light(msg):
    data = json.loads(msg.payload)
    logging.info("Auto discovery message on: " + msg.topic)
    #logging.debug(json.dumps(data, indent=4))
    discoveredDevices[data['unique_id']] = data;
    for key, data in discoveredDevices.items():
        device_new = True
        for light, obj in bridgeConfig["lights"].items():
            if obj.protocol == "mqtt" and obj.protocol_cfg["uid"] == key:
                device_new = False
                obj.protocol_cfg["command_topic"] = data["command_topic"]
                obj.protocol_cfg["state_topic"] = data["state_topic"]
                break

        if device_new:
            lightName = data["device"]["name"] if data["device"]["name"] is not None else data["name"]
            logging.debug("MQTT: Adding light " + lightName)

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
            elif light_ct:
                modelid = "LTW001"
            elif light_brightness:
                modelid = "LWB010"
            else:
                modelid = "LOM001"
            protocol_cfg = { "uid": data["unique_id"],
                                    "ip":"mqtt",
                                    "state_topic": data["state_topic"],
                                    "command_topic": data["command_topic"],
                                    "mqtt_server": bridgeConfig["config"]["mqtt"]}

            addNewLight(modelid, lightName, "mqtt", protocol_cfg)



def on_state_update(msg):
    logging.debug("MQTT: got state message on " + msg.topic)
    data = json.loads(msg.payload)
    latestStates[msg.topic] = data
    logging.debug(json.dumps(data, indent=4))

# on_message handler (linked to client below)
def on_message(client, userdata, msg):
    if bridgeConfig["config"]["mqtt"]["enabled"]:
        try:
            current_time =  datetime.now()
            logging.debug("MQTT: got state message on " + msg.topic)
            data = json.loads(msg.payload)
            logging.debug(msg.payload)
            if msg.topic.startswith(discoveryPrefix + "/light/"):
                on_autodiscovery_light(msg)
            elif msg.topic == "zigbee2mqtt/bridge/devices":
                for key in data:
                    if "model_id" in key and (key["model_id"] in standardSensors or key["model_id"] in motionSensors): # Sensor is supported
                        if getObject(key["friendly_name"]) == False: ## Add the new sensor
                            logging.info("MQTT: Add new mqtt sensor " + key["friendly_name"])
                            if key["model_id"] in standardSensors:
                                new_sensor_id = nextFreeId(bridgeConfig, "sensors")
                                sensor_type = list(sensorTypes[key["model_id"]].keys())[0]
                                uniqueid = convertHexToMac(key["ieee_address"]) + "-01-1000"
                                sensorData = {"name": key["friendly_name"], "protocol": "mqtt", "modelid": key["model_id"], "type": sensor_type, "uniqueid": uniqueid,"protocol_cfg": {"friendly_name": key["friendly_name"], "ieeeAddr": key["ieee_address"], "model": key["definition"]["model"]}, "id_v1": new_sensor_id}
                                bridgeConfig["sensors"][new_sensor_id] = HueObjects.Sensor(sensorData)
                            ### TRADFRI Motion Sensor, Xiaomi motion sensor, etc
                            elif key["model_id"] in motionSensors:
                                    logging.info("MQTT: add new motion sensor " + key["model_id"])
                                    addHueMotionSensor(key["friendly_name"], "mqtt", {"modelid": key["model_id"], "lightSensor": "on", "friendly_name": key["friendly_name"]})
                            else:
                                logging.info("MQTT: unsupported sensor " + key["model_id"])
            elif msg.topic == "zigbee2mqtt/bridge/log":
                light = getObject(data["meta"]["friendly_name"])
                if data["type"] == "device_announced":
                    if light.config["startup"]["mode"] == "powerfail":
                        logging.info("set last state for " + light.name)
                        payload = {}
                        payload["state"] = "ON" if light.state["on"] else "OFF"
                        client.publish(light.protocol_cfg['command_topic'], json.dumps(payload))
                elif data["type"] == "zigbee_publish_error":
                    logging.info(light.name + " is unreachable")
                    light.state["reachable"] = False
            else:
                device_friendlyname = msg.topic.split("/")[1]
                device = getObject(device_friendlyname)
                if device != False:
                    if device.getObjectPath()["resource"] == "sensors":
                        if "battery" in data and isinstance(data["battery"], int):
                            device.config["battery"] = data["battery"]
                        if device.config["on"] == False:
                            return
                        convertedPayload = {"lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}
                        if ("action" in data and data["action"] == "") or ("click" in data and data["click"] == ""):
                            return
                        ### If is a motion sensor update the light level and temperature
                        if device.modelid in motionSensors:
                            convertedPayload["presence"] = data["occupancy"]
                            lightPayload = {"lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}
                            lightSensor = findLightSensor(device)
                            if "temperature" in data:
                                tempSensor = findTempSensor(device)
                                tempSensor.state = {"temperature": int(data["temperature"] * 100), "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}
                            if "illuminance_lux" in data:
                                hue_lightlevel = int(10000 * math.log10(data["illuminance_lux"])) if data["illuminance_lux"] != 0 else 0
                                if hue_lightlevel > lightSensor.config["tholddark"]:
                                    lightPayload["dark"] = False
                                else:
                                    lightPayload["dark"] = True
                                lightPayload["lightlevel"] = hue_lightlevel
                            elif lightSensor.protocol_cfg["lightSensor"] == "on":
                                lightPayload["dark"] = not bridgeConfig["sensors"]["1"].state["daylight"]
                                if  lightPayload["dark"]:
                                    lightPayload["lightlevel"] = 6000
                                else:
                                    lightPayload["lightlevel"] = 25000
                            else: # is always dark
                                lightPayload["dark"] = True
                                lightPayload["lightlevel"] = 6000
                            lightPayload["daylight"] = not lightPayload["dark"]
                            if lightPayload["dark"] != lightSensor.state["dark"]:
                                lightSensor.dxState["dark"] = current_time
                            lightSensor.state.update(lightPayload)
                            # send email if alarm is enabled:
                            if data["occupancy"] and bridgeConfig["config"]["alarm"]["enabled"] and bridgeConfig["config"]["alarm"]["lasttriggered"] + 300 < current_time.timestamp():
                                logging.info("Alarm triggered, sending email...")
                                requests.post("https://diyhue.org/cdn/mailNotify.php", json={"to": bridgeConfig["config"]["alarm"]["email"], "sensor": device.name}, timeout=10)
                                bridgeConfig["config"]["alarm"]["lasttriggered"] = int(current_time.timestamp())
                        elif device.modelid in standardSensors:
                            convertedPayload.update(standardSensors[device.modelid]["dataConversion"][data[standardSensors[device.modelid]["dataConversion"]["rootKey"]]])
                        for key in convertedPayload.keys():
                            if device.state[key] != convertedPayload[key]:
                                device.dxState[key] = current_time
                        device.state.update(convertedPayload)
                        logging.debug(convertedPayload)
                        if "buttonevent" in  convertedPayload and convertedPayload["buttonevent"] in [1001, 2001, 3001, 4001, 5001]:
                            Thread(target=longPressButton, args=[device, convertedPayload["buttonevent"]]).start()
                        rulesProcessor(device, current_time)
                    elif device.getObjectPath()["resource"] == "lights":
                        state = {}
                        if "state" in data:
                            if data["state"] == "ON":
                                state["on"] = True
                            else:
                                state["on"] = False
                        if "brightness" in data:
                            state["bri"] = data["brightness"]
                        device.state.update(state)

                on_state_update(msg)
        except Exception as e:
            logging.info("MQTT Exception | " + str(e))

def findLightSensor(sensor):
    lightSensorUID = sensor.uniqueid[:-1] + "0"
    for key, obj in bridgeConfig["sensors"].items():
        if obj.uniqueid == lightSensorUID:
            return obj

def findTempSensor(sensor):
    lightSensorUID = sensor.uniqueid[:-1] + "2"
    for key, obj in bridgeConfig["sensors"].items():
        if obj.uniqueid == lightSensorUID:
            return obj

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
    client.subscribe("zigbee2mqtt/bridge/devices")
    client.subscribe("zigbee2mqtt/bridge/log")

def mqttServer():

    logging.info("Strting MQTT service...")
    # ================= MQTT CLIENT Connection========================
    # Set user/password on client if supplied

    if bridgeConfig["config"]["mqtt"]["mqttUser"] != "" and bridgeConfig["config"]["mqtt"]["mqttPassword"] != "":
        client.username_pw_set(bridgeConfig["config"]["mqtt"]["mqttUser"],bridgeConfig["config"]["mqtt"]["mqttPassword"])

    if bridgeConfig["config"]["mqtt"]['discoveryPrefix'] is not None:
        discoveryPrefix = bridgeConfig["config"]["mqtt"]['discoveryPrefix']
    # Setup handlers
    client.on_connect = on_connect
    client.on_message = on_message
    # Connect to the server
    client.connect(bridgeConfig["config"]["mqtt"]["mqttServer"], bridgeConfig["config"]["mqtt"]["mqttPort"])

    # start the loop to keep receiving data
    client.loop_forever()
