import logManager
import configManager
import json
import math
import weakref
import ssl
from HueObjects import Sensor
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
from threading import Thread
from time import sleep
from functions.core import nextFreeId
from sensors.discover import addHueMotionSensor
from sensors.sensor_types import sensorTypes
from lights.discover import addNewLight
from functions.rules import rulesProcessor
from functions.behavior_instance import checkBehaviorInstances
import requests

logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config
client = mqtt.Client()

devices_ids = {}

# Configuration stuff
discoveryPrefix = "homeassistant"
latestStates = {}
discoveredDevices = {}


motionSensors = ["TRADFRI motion sensor", "lumi.sensor_motion.aq2", "lumi.sensor_motion", "lumi.motion.ac02", "SML001"]
standardSensors = {
    "TRADFRI remote control": {
        "dataConversion": {
            "rootKey": "action",
            "toggle": {"buttonevent": 1002},
            "arrow_right_click": {"buttonevent": 5002},
            "arrow_right_hold": {"buttonevent": 5001},
            "arrow_left_click": {"buttonevent": 4002},
            "arrow_left_hold": {"buttonevent": 4001},
            "brightness_up_click": {"buttonevent": 2002},
            "brightness_up_hold": {"buttonevent": 2001},
            "brightness_down_click": {"buttonevent": 3002},
            "brightness_down_hold": {"buttonevent": 3001},
            "brightness_up_release": {"buttonevent": 2003},
            "brightness_down_release": {"buttonevent": 3003},
            "arrow_left_release": {"buttonevent": 4003},
            "arrow_right_release": {"buttonevent": 5003},
        }
    },
    "TRADFRI on/off switch": {
        "dataConversion": {
            "rootKey": "action",
            "on": {"buttonevent": 1002},
            "off": {"buttonevent": 2002},
            "brightness_up": {"buttonevent": 1001},
            "brightness_down": {"buttonevent": 2001},
            "brightness_stop": {"buttonevent": 3001},
        }
    },
    "TRADFRI wireless dimmer": {
        "dataConversion": {
            "rootKey": "action",
            "rotate_right_quick": {"buttonevent": 1002},
            "rotate_right": {"buttonevent": 2002},
            "rotate_left": {"buttonevent": 3002},
            "rotate_left_quick": {"buttonevent": 4002},
            "rotate_stop": {},
            "": {},
        }
    },
    "RWL021": {
        "dataConversion": {
            "rootKey": "action",
            "on_press": {"buttonevent": 1000},
            "on-press": {"buttonevent": 1000},
            "on_hold": {"buttonevent": 1001},
            "on-hold": {"buttonevent": 1001},
            "on_press_release": {"buttonevent": 1002},
            "on-press-release": {"buttonevent": 1002},
            "on_hold_release": {"buttonevent": 1003},
            "on-hold-release": {"buttonevent": 1003},
            "up_press": {"buttonevent": 2000},
            "up-press": {"buttonevent": 2000},
            "up_hold": {"buttonevent": 2001},
            "up-hold": {"buttonevent": 2001},
            "up_press_release": {"buttonevent": 2002},
            "up-press-release": {"buttonevent": 2002},
            "up_hold_release": {"buttonevent": 2003},
            "up-hold-release": {"buttonevent": 2003},
            "down_press": {"buttonevent": 3000},
            "down-press": {"buttonevent": 3000},
            "down_hold": {"buttonevent": 3001},
            "down-hold": {"buttonevent": 3001},
            "down_press_release": {"buttonevent": 3002},
            "down-press-release": {"buttonevent": 3002},
            "down_hold_release": {"buttonevent": 3003},
            "down-hold-release": {"buttonevent": 3003},
            "off_press": {"buttonevent": 4000},
            "off-press": {"buttonevent": 4000},
            "off_hold": {"buttonevent": 4001},
            "off-hold": {"buttonevent": 4001},
            "off_press_release": {"buttonevent": 4002},
            "off-press-release": {"buttonevent": 4002},
            "off_hold_release": {"buttonevent": 4003},
            "off-hold-release": {"buttonevent": 4003},
        }
    },
    "WXKG01LM": {
        "dataConversion": {
            "rootKey": "action",
            "single": {"buttonevent": 1001},
            "double": {"buttonevent": 1002},
            "triple": {"buttonevent": 1003},
            "quadruple": {"buttonevent": 1004},
            "hold": {"buttonevent": 2001},
            "release": {"buttonevent": 2002},
            "release": {"many": 2003},
        }
    },
    "Remote Control N2": {
        "dataConversion": {
            "rootKey": "action",
            "on": {"buttonevent": 1001},
            "off": {"buttonevent": 2001},
            "brightness_move_up": {"buttonevent": 1002},
            "brightness_stop": {"buttonevent": 1003},
            "brightness_move_down": {"buttonevent": 2002},
            "arrow_left_click": {"buttonevent": 3002},
            "arrow_right_click": {"many": 4002},
        }
    },
    "RDM002": {
        "dataConversion": {
            "rootKey": "action",
            "dirKey": "action_direction",
            "typeKey": "action_type",
            "timeKey": "action_time",
            "button_1_press": {"buttonevent": 1000},
            "button_1_hold": {"buttonevent": 1001},
            "button_1_press_release": {"buttonevent": 1002},
            "button_1_hold_release": {"buttonevent": 1003},
            "button_2_press": {"buttonevent": 2000},
            "button_2_hold": {"buttonevent": 2001},
            "button_2_press_release": {"buttonevent": 2002},
            "button_2_hold_release": {"buttonevent": 2003},
            "button_3_press": {"buttonevent": 3000},
            "button_3_hold": {"buttonevent": 3001},
            "button_3_press_release": {"buttonevent": 3002},
            "button_3_hold_release": {"buttonevent": 3003},
            "button_4_press": {"buttonevent": 4000},
            "button_4_hold": {"buttonevent": 4001},
            "button_4_press_release": {"buttonevent": 4002},
            "button_4_hold_release": {"buttonevent": 4003},
            "dial_rotate_left_step": {"rotaryevent": 1},
            "dial_rotate_left_slow": {"rotaryevent": 2},
            "dial_rotate_left_fast": {"rotaryevent": 2},
            "dial_rotate_right_step": {"rotaryevent": 1},
            "dial_rotate_right_slow": {"rotaryevent": 2},
            "dial_rotate_right_fast": {"rotaryevent": 2},
            "expectedrotation":90,
            "expectedeventduration":400
        }
    },
    "PTM 215Z": {
        "dataConversion": {
            "rootKey": "action",
            "press_1": {"buttonevent": 1000},
            "release_1": {"buttonevent": 1002},
            "press_2": {"buttonevent": 2000},
            "release_2": {"buttonevent": 2002},
            "press_3": {"buttonevent": 3000},
            "release_3": {"buttonevent": 3002},
            "press_4": {"buttonevent": 4000},
            "release_4": {"buttonevent": 4002},
            "press_1_and_3": {"buttonevent": 1010},
            "release_1_and_3": {"buttonevent": 1003},
            "press_2_and_4": {"buttonevent": 2010},
            "release_2_and_4": {"buttonevent": 2003},
            "press_energy_bar": {"buttonevent": 5000},
        }
    },
}



# WXKG01LM MiJia wireless switch https://www.zigbee2mqtt.io/devices/WXKG01LM.html

standardSensors["RWL020"] = standardSensors["RWL021"]
standardSensors["RWL022"] = standardSensors["RWL021"]
standardSensors["8719514440937"] = standardSensors["RDM002"]
standardSensors["8719514440999"] = standardSensors["RDM002"]
standardSensors["9290035001"] = standardSensors["RDM002"]
standardSensors["9290035003"] = standardSensors["RDM002"]


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
        checkBehaviorInstances(sensor)
        sleep(0.5)
    return

def streamGroupEvent(device, state):
    for id, group in bridgeConfig["groups"].items():
        if id != "0":
            for light in group.lights:
                if light().id_v1 == device.id_v1:
                    group.genStreamEvent(state)


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
    discoveredDevices[data['unique_id']] = data
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
                                for sensor_type in sensorTypes[key["model_id"]].keys():
                                    new_sensor_id = nextFreeId(bridgeConfig, "sensors")
                                    #sensor_type = sensorTypes[key["model_id"]][sensor]
                                    uniqueid = convertHexToMac(key["ieee_address"]) + "-01-1000"
                                    sensorData = {"name": key["friendly_name"], "protocol": "mqtt", "modelid": key["model_id"], "type": sensor_type, "uniqueid": uniqueid,"protocol_cfg": {"friendly_name": key["friendly_name"], "ieeeAddr": key["ieee_address"], "model": key["definition"]["model"]}, "id_v1": new_sensor_id}
                                    bridgeConfig["sensors"][new_sensor_id] = Sensor.Sensor(sensorData)
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
                device_friendlyname = msg.topic[msg.topic.index("/") + 1:]
                device = getObject(device_friendlyname)
                if device != False:
                    if device.getObjectPath()["resource"] == "sensors":
                        if "battery" in data and isinstance(data["battery"], int):
                            device.config["battery"] = data["battery"]
                        if device.config["on"] == False:
                            return
                        convertedPayload = {"lastupdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")}
                        if ("action" in data and data["action"] == "") or ("click" in data and data["click"] == ""):
                            return
                        ### If is a motion sensor update the light level and temperature
                        if device.modelid in motionSensors:
                            convertedPayload["presence"] = data["occupancy"]
                            lightPayload = {"lastupdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")}
                            lightSensor = findLightSensor(device)
                            if "temperature" in data:
                                tempSensor = findTempSensor(device)
                                tempSensor.state = {"temperature": int(data["temperature"] * 100), "lastupdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")}
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
                        checkBehaviorInstances(device)
                    elif device.getObjectPath()["resource"] == "lights":
                        state = {"reachable": True}
                        v2State = {}
                        if "state" in data:
                            if data["state"] == "ON":
                                state["on"] = True
                            else:
                                state["on"] = False
                            v2State.update({"on":{"on": state["on"]}})
                            device.genStreamEvent(v2State)
                        if "brightness" in data:
                            state["bri"] = data["brightness"]
                            v2State.update({"dimming": {"brightness": round(state["bri"] / 2.54, 2)}})
                            device.genStreamEvent(v2State)
                        device.state.update(state)
                        streamGroupEvent(device, v2State)

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

    # defaults for TLS and certs
    if 'mqttCaCerts' not in bridgeConfig["config"]["mqtt"]:
        bridgeConfig["config"]["mqtt"]["mqttCaCerts"] = None
    if 'mqttCertfile' not in bridgeConfig["config"]["mqtt"]:
        bridgeConfig["config"]["mqtt"]["mqttCertfile"] = None
    if 'mqttKeyfile' not in bridgeConfig["config"]["mqtt"]:
        bridgeConfig["config"]["mqtt"]["mqttKeyfile"] = None
    if 'mqttTls' not in bridgeConfig["config"]["mqtt"]:
        bridgeConfig["config"]["mqtt"]["mqttTls"] = False
    if 'mqttTlsInsecure' not in bridgeConfig["config"]["mqtt"]:
        bridgeConfig["config"]["mqtt"]["mqttTlsInsecure"] = False
    # TLS set?
    if bridgeConfig["config"]["mqtt"]["mqttTls"]:
        mqttTlsVersion = ssl.PROTOCOL_TLS
        client.tls_set(ca_certs=bridgeConfig["config"]["mqtt"]["mqttCaCerts"], certfile=bridgeConfig["config"]["mqtt"]["mqttCertfile"], keyfile=bridgeConfig["config"]["mqtt"]["mqttKeyfile"], tls_version=mqttTlsVersion)
        # allow insecure
        if bridgeConfig["config"]["mqtt"]["mqttTlsInsecure"]:
            client.tls_insecure_set(bridgeConfig["config"]["mqtt"]["mqttTlsInsecure"])
    # Setup handlers
    client.on_connect = on_connect
    client.on_message = on_message
    # Connect to the server
    client.connect(bridgeConfig["config"]["mqtt"]["mqttServer"], bridgeConfig["config"]["mqtt"]["mqttPort"])

    # start the loop to keep receiving data
    client.loop_forever()
