import logManager
import configManager
import json
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


from pprint import pprint

logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config

devices_ids = {}


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

client = mqtt.Client()

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
                "dataConversion": {"rootKey": "action", "rotate_right_quick": {"buttonevent": 1002}, "rotate_right": {"buttonevent": 2002}, "rotate_left": {"buttonevent": 3002}, "rotate_left_quick": {"buttonevent": 4002}, "rotate_stop": {}, "": {}}}
            }


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
            elif msg.topic == "zigbee2mqtt/bridge/config/devices":
                for key in data:
                    if "modelID" in key and (key["modelID"] in standardSensors or key["modelID"] in motionSensors): # Sensor is supported
                        if getObject(key["friendly_name"]) == False: ## Add the new sensor
                            logging.info("MQTT: Add new mqtt sensor " + key["friendly_name"])
                            if key["modelID"] in standardSensors:
                                new_sensor_id = nextFreeId(bridgeConfig, "sensors")
                                sensor_type = list(sensorTypes[key["modelID"]].keys())[0]
                                uniqueid = convertHexToMac(key["ieeeAddr"]) + "-01-1000"
                                sensorData = {"name": key["friendly_name"], "protocol": "mqtt", "modelid": key["modelID"], "type": sensor_type, "uniqueid": uniqueid,"protocol_cfg": {"friendly_name": key["friendly_name"], "ieeeAddr": key["ieeeAddr"], "model": key["model"]}, "id_v1": new_sensor_id}
                                bridgeConfig["sensors"][new_sensor_id] = HueObjects.Sensor(sensorData)
                            ### TRADFRI Motion Sensor, Xiaomi motion sensor, etc
                            elif key["modelID"] in motionSensors:
                                    logging.info("MQTT: add new motion sensor " + key["modelID"])
                                    addHueMotionSensor(key["friendly_name"], "mqtt", {"modelid": key["modelID"], "lightSensor": "on", "friendly_name": key["friendly_name"]})
                            else:
                                logging.info("MQTT: unsupported sensor " + key["modelID"])
            elif msg.topic == "zigbee2mqtt/bridge/log":
                if data["type"] == "device_announced":
                    light = getObject(data["meta"]["friendly_name"])
                    if light.config["startup"]["mode"] == "powerfail":
                        logging.info("set last state for " + light.name)
                        payload = {}
                        payload["state"] = "ON" if light.state["on"] else "OFF"
                        client.publish(light.protocol_cfg['command_topic'], json.dumps(payload))

            else:
                device = msg.topic.split("/")[1]
                sensor = getObject(device)
                if sensor != False:
                    if "battery" in data:
                        sensor.config["battery"] = int(data["battery"])
                    if sensor.config["on"] == False:
                        return
                    convertedPayload = {"lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}
                    if ("action" in data and data["action"] == "") or ("click" in data and data["click"] == ""):
                        return
                    ### If is a motion sensor update the light level and temperature
                    if sensor.modelid in motionSensors:
                        convertedPayload["presence"] = data["occupancy"]
                        lightPayload = {"lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}
                        lightSensor = findLightSensor(sensor)
                        if "temperature" in data:
                            tempSensor = findTempSensor(sensor)
                            tempSensor.state = {"temperature": int(data["temperature"] * 100), "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}
                        if "illuminance" in data:
                            if data["illuminance"] > 10:
                                lightPayload["dark"] = False
                            else:
                                lightPayload["dark"] = True
                        elif lightSensor.protocol_cfg["lightSensor"] == "on":
                            lightPayload["dark"] = not bridgeConfig["sensors"]["1"].state["daylight"]
                        else: # is always dark
                            lightPayload["dark"] = True

                        if  lightPayload["dark"]:
                            lightPayload["lightlevel"] = 6000
                        else:
                            lightPayload["lightlevel"] = 25000
                        lightPayload["daylight"] = not lightPayload["dark"]
                        if lightPayload["dark"] != lightSensor.state["dark"]:
                            lightSensor.dxState["dark"] = current_time
                        lightSensor.state.update(lightPayload)
                        # send email if alarm is enabled:
                        if data["occupancy"] and bridgeConfig["config"]["alarm"]["enabled"] and bridgeConfig["config"]["alarm"]["lasttriggered"] + 300 < current_time.timestamp():
                            logging.info("Alarm triggered, sending email...")
                            requests.post("https://diyhue.org/cdn/mailNotify.php", json={"to": bridgeConfig["config"]["alarm"]["email"], "sensor": sensor.name}, timeout=10)
                            bridgeConfig["config"]["alarm"]["lasttriggered"] = int(current_time.timestamp())
                    elif sensor.modelid in standardSensors:
                        convertedPayload.update(standardSensors[sensor.modelid]["dataConversion"][data[standardSensors[sensor.modelid]["dataConversion"]["rootKey"]]])
                    for key in convertedPayload.keys():
                        if sensor.state[key] != convertedPayload[key]:
                            sensor.dxState[key] = current_time
                    sensor.state.update(convertedPayload)
                    logging.debug(convertedPayload)
                    if "buttonevent" in  convertedPayload and convertedPayload["buttonevent"] in [1001, 2001, 3001, 4001, 5001]:
                        Thread(target=longPressButton, args=[sensor, convertedPayload["buttonevent"]]).start()
                    rulesProcessor(sensor, current_time)

                on_state_update(msg)
        except:
            traceback.print_exc()
            #quit(0)

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
    client.subscribe("zigbee2mqtt/bridge/config/devices")
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
