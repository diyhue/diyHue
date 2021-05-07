import datetime
import requests
import configManager
import logManager
import weakref
import HueObjects
import json
from threading import Thread
from functions.rules import rulesProcessor
from functions.request import sendRequest
from ws4py.client.threadedclient import WebSocketClient
from lights.manage import updateGroupStats

bridgeConfig = configManager.bridgeConfig.yaml_config
logging = logManager.logger.get_logger(__name__)


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

def scanDeconz():
    deconz_ip = configManager.runtimeConfig.arg["DECONZ"]
    if not bridgeConfig["config"]["deconz"]["enabled"]:
        if "username" not in bridgeConfig["config"]["deconz"]:
            try:
                registration = json.loads(sendRequest("http://" + deconz_ip + ":" + str(bridgeConfig["config"]["deconz"]["port"]) + "/api", "POST", "{\"username\": \"283145a4e198cc6535\", \"devicetype\":\"Hue Emulator\"}"))
            except:
                logging.info("registration fail, is the link button pressed?")
                if "websocketport" in bridgeConfig["config"]["deconz"]:
                    del bridgeConfig["config"]["deconz"]["websocketport"]
                return
            if "success" in registration[0]:
                bridgeConfig["config"]["deconz"]["username"] = registration[0]["success"]["username"]
                bridgeConfig["config"]["deconz"]["enabled"] = True
    elif "username" in bridgeConfig["config"]["deconz"]:
        deconz_config = json.loads(sendRequest("http://" + deconz_ip + ":" + str(bridgeConfig["config"]["deconz"]["port"]) + "/api/" + bridgeConfig["config"]["deconz"]["username"] + "/config", "GET", "{}"))
        bridgeConfig["config"]["deconz"]["websocketport"] = deconz_config["websocketport"]

        #lights
        deconz_lights = json.loads(sendRequest("http://" + deconz_ip + ":" + str(bridgeConfig["config"]["deconz"]["port"]) + "/api/" + bridgeConfig["config"]["deconz"]["username"] + "/lights", "GET", "{}"))
        for light in deconz_lights:
            if light not in bridgeConfig["config"]["deconz"]["lights"] and "modelid" in deconz_lights[light]:
                new_light_id = nextFreeId(bridgeConfig, "lights")
                logging.info("register new light " + new_light_id)
                bridgeConfig["lights"][new_light_id] = deconz_lights[light]
                bridgeConfig["lights_address"][new_light_id] = {"username": bridgeConfig["config"]["deconz"]["username"], "light_id": light, "ip": deconz_ip + ":" + str(bridgeConfig["config"]["deconz"]["port"]), "protocol": "deconz"}
                bridgeConfig["config"]["deconz"]["lights"][light] = {"bridgeid": new_light_id, "modelid": deconz_lights[light]["modelid"], "type": deconz_lights[light]["type"]}

        #sensors
        deconz_sensors = json.loads(sendRequest("http://" + deconz_ip + ":" + str(bridgeConfig["config"]["deconz"]["port"]) + "/api/" + bridgeConfig["config"]["deconz"]["username"] + "/sensors", "GET", "{}"))
        for sensor in deconz_sensors:
            if sensor not in bridgeConfig["config"]["deconz"]["sensors"] and "modelid" in deconz_sensors[sensor]:
                new_sensor_id = nextFreeId(bridgeConfig, "sensors")
                if deconz_sensors[sensor]["modelid"] in ["TRADFRI remote control", "TRADFRI wireless dimmer"]:
                    logging.info("register new " + deconz_sensors[sensor]["modelid"])
                    bridgeConfig["sensors"][new_sensor_id] = {"config": deconz_sensors[sensor]["config"], "manufacturername": deconz_sensors[sensor]["manufacturername"], "modelid": deconz_sensors[sensor]["modelid"], "name": deconz_sensors[sensor]["name"], "state": deconz_sensors[sensor]["state"], "type": deconz_sensors[sensor]["type"], "uniqueid": deconz_sensors[sensor]["uniqueid"]}
                    if "swversion" in  deconz_sensors[sensor]:
                        bridgeConfig["sensors"][new_sensor_id]["swversion"] = deconz_sensors[sensor]["swversion"]
                    bridgeConfig["config"]["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                elif deconz_sensors[sensor]["modelid"] == "TRADFRI motion sensor":
                    logging.info("register TRADFRI motion sensor as Philips Motion Sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    bridgeConfig["config"]["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"], "lightsensor": "internal"}
                elif deconz_sensors[sensor]["modelid"] == "lumi.vibration.aq1":
                    logging.info("register Xiaomi Vibration sensor as Philips Motion Sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    bridgeConfig["config"]["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"], "lightsensor": "astral"}
                elif deconz_sensors[sensor]["modelid"] == "lumi.sensor_motion.aq2":
                    if deconz_sensors[sensor]["type"] == "ZHALightLevel":
                        logging.info("register new Xiaomi light sensor")
                        bridgeConfig["sensors"][new_sensor_id] = {"name": "Hue ambient light sensor 1", "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:], "type": "ZLLLightLevel", "swversion": "6.1.0.18912", "state": {"dark": True, "daylight": False, "lightlevel": 6000, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False,"battery": 100, "reachable": True, "alert": "none", "tholddark": 21597, "tholdoffset": 7000, "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
                        bridgeConfig["sensors"][nextFreeId(bridgeConfig, "sensors")] = {"name": "Hue temperature sensor 1", "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:-1] + "2", "type": "ZLLTemperature", "swversion": "6.1.0.18912", "state": {"temperature": None, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False, "battery": 100, "reachable": True, "alert":"none", "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
                        bridgeConfig["config"]["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                    elif deconz_sensors[sensor]["type"] == "ZHAPresence":
                        logging.info("register new Xiaomi motion sensor")
                        bridgeConfig["sensors"][new_sensor_id] = {"name": deconz_sensors[sensor]["name"], "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:], "type": "ZLLPresence", "swversion": "6.1.0.18912", "state": {"lastupdated": "none", "presence": None}, "manufacturername": "Philips", "config": {"on": False,"battery": 100,"reachable": True, "alert": "lselect", "ledindication": False, "usertest": False, "sensitivity": 2, "sensitivitymax": 2,"pending": []}, "modelid": "SML001"}
                        bridgeConfig["config"]["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                elif deconz_sensors[sensor]["modelid"] == "lumi.sensor_motion":
                    logging.info("register Xiaomi Motion sensor w/o light sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    bridgeConfig["config"]["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                else:
                    bridgeConfig["sensors"][new_sensor_id] = deconz_sensors[sensor]
                    bridgeConfig["config"]["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}

            else: #temporary patch for config compatibility with new release
                bridgeConfig["config"]["deconz"]["sensors"][sensor]["modelid"] = deconz_sensors[sensor]["modelid"]
                bridgeConfig["config"]["deconz"]["sensors"][sensor]["type"] = deconz_sensors[sensor]["type"]
        generateDxState()


def websocketClient():
    # initiate deconz connection
    scanDeconz()
    # don't start the websocket if connection was not successful
    if "websocketport" not in bridgeConfig["config"]["deconz"]:
        return

    class EchoClient(WebSocketClient):
        def opened(self):
            self.send("hello")

        def closed(self, code, reason=None):
            logging.info(("deconz websocket disconnected", code, reason))
            del bridgeConfig["config"]["deconz"]["websocketport"]

        def received_message(self, m):
            logging.info(m)
            message = json.loads(str(m))
            try:
                if message["r"] == "sensors":
                    bridge_sensor_id = bridgeConfig["config"]["deconz"]["sensors"][message["id"]]["bridgeid"]
                    if "state" in message and bridgeConfig["sensors"][bridge_sensor_id]["config"]["on"]:

                        #change codes for emulated hue Switches
                        if "hueType" in bridgeConfig["config"]["deconz"]["sensors"][message["id"]]:
                            rewriteDict = {"ZGPSwitch": {1002: 34, 3002: 16, 4002: 17, 5002: 18}, "ZLLSwitch" : {1002 : 1000, 2002: 2000, 2001: 2001, 2003: 2002, 3001: 3001, 3002: 3000, 3003: 3002, 4002: 4000, 5002: 4000} }
                            message["state"]["buttonevent"] = rewriteDict[bridgeConfig["config"]["deconz"]["sensors"][message["id"]]["hueType"]][message["state"]["buttonevent"]]
                        #end change codes for emulated hue Switches

                        #convert tradfri motion sensor notification to look like Hue Motion Sensor
                        if message["state"] and bridgeConfig["config"]["deconz"]["sensors"][message["id"]]["modelid"] == "TRADFRI motion sensor":
                            #find the light sensor id
                            light_sensor = "0"
                            for sensor in bridgeConfig["sensors"].keys():
                                if bridgeConfig["sensors"][sensor]["type"] == "ZLLLightLevel" and bridgeConfig["sensors"][sensor]["uniqueid"] == bridgeConfig["sensors"][bridge_sensor_id]["uniqueid"][:-1] + "0":
                                    light_sensor = sensor
                                    break
                            if bridgeConfig["config"]["deconz"]["sensors"][message["id"]]["lightsensor"] == "none":
                                message["state"].update({"dark": True})
                            elif bridgeConfig["config"]["deconz"]["sensors"][message["id"]]["lightsensor"] == "astral":
                                message["state"]["dark"] = not bridgeConfig["sensors"]["1"]["state"]["daylight"]

                            elif bridgeConfig["config"]["deconz"]["sensors"][message["id"]]["lightsensor"] == "combined":
                                if not bridgeConfig["sensors"]["1"]["state"]["daylight"]:
                                    message["state"]["dark"] = True
                                elif (datetime.strptime(message["state"]["lastupdated"], "%Y-%m-%dT%H:%M:%S") - datetime.strptime(bridgeConfig["sensors"][light_sensor]["state"]["lastupdated"], "%Y-%m-%dT%H:%M:%S")).total_seconds() > 1200:
                                    message["state"]["dark"] = False

                            if  message["state"]["dark"]:
                                bridgeConfig["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                            else:
                                bridgeConfig["sensors"][light_sensor]["state"]["lightlevel"] = 25000
                            bridgeConfig["sensors"][light_sensor]["state"]["dark"] = message["state"]["dark"]
                            bridgeConfig["sensors"][light_sensor]["state"]["daylight"] = not message["state"]["dark"]
                            bridgeConfig["sensors"][light_sensor]["state"]["lastupdated"] = message["state"]["lastupdated"]

                        #Xiaomi motion w/o light level sensor
                        if message["state"] and bridgeConfig["config"]["deconz"]["sensors"][message["id"]]["modelid"] == "lumi.sensor_motion":
                            for sensor in bridgeConfig["sensors"].keys():
                                if bridgeConfig["sensors"][sensor]["type"] == "ZLLLightLevel" and bridgeConfig["sensors"][sensor]["uniqueid"] == bridgeConfig["sensors"][bridge_sensor_id]["uniqueid"][:-1] + "0":
                                    light_sensor = sensor
                                    break

                            if bridgeConfig["sensors"]["1"]["modelid"] == "PHDL00" and bridgeConfig["sensors"]["1"]["state"]["daylight"]:
                                bridgeConfig["sensors"][light_sensor]["state"]["lightlevel"] = 25000
                                bridgeConfig["sensors"][light_sensor]["state"]["dark"] = False
                            else:
                                bridgeConfig["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                                bridgeConfig["sensors"][light_sensor]["state"]["dark"] = True

                        #convert xiaomi motion sensor to hue sensor
                        if message["state"] and bridgeConfig["config"]["deconz"]["sensors"][message["id"]]["modelid"] == "lumi.sensor_motion.aq2" and message["state"] and bridgeConfig["config"]["deconz"]["sensors"][message["id"]]["type"] == "ZHALightLevel":
                            bridgeConfig["sensors"][bridge_sensor_id]["state"].update(message["state"])
                            return
                        ##############

                        ##convert xiaomi vibration sensor states to hue motion sensor
                        if message["state"] and bridgeConfig["config"]["deconz"]["sensors"][message["id"]]["modelid"] == "lumi.vibration.aq1":
                            #find the light sensor id
                            light_sensor = "0"
                            for sensor in bridgeConfig["sensors"].keys():
                                if bridgeConfig["sensors"][sensor]["type"] == "ZLLLightLevel" and bridgeConfig["sensors"][sensor]["uniqueid"] == bridgeConfig["sensors"][bridge_sensor_id]["uniqueid"][:-1] + "0":
                                    light_sensor = sensor
                                    break
                            logging.info("Vibration: emulated light sensor id is  " + light_sensor)
                            if bridgeConfig["config"]["deconz"]["sensors"][message["id"]]["lightsensor"] == "none":
                                message["state"].update({"dark": True})
                                logging.info("Vibration: set light sensor to dark because 'lightsensor' = 'none' ")
                            elif bridgeConfig["config"]["deconz"]["sensors"][message["id"]]["lightsensor"] == "astral":
                                message["state"]["dark"] = not bridgeConfig["sensors"]["1"]["state"]["daylight"]
                                logging.info("Vibration: set light sensor to " + str(not bridgeConfig["sensors"]["1"]["state"]["daylight"]) + " because 'lightsensor' = 'astral' ")

                            if  message["state"]["dark"]:
                                bridgeConfig["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                            else:
                                bridgeConfig["sensors"][light_sensor]["state"]["lightlevel"] = 25000
                            bridgeConfig["sensors"][light_sensor]["state"]["dark"] = message["state"]["dark"]
                            bridgeConfig["sensors"][light_sensor]["state"]["daylight"] = not message["state"]["dark"]
                            bridgeConfig["sensors"][light_sensor]["state"]["lastupdated"] = message["state"]["lastupdated"]
                            message["state"] = {"motion": True, "lastupdated": message["state"]["lastupdated"]} #empty the message state for non Hue motion states (we need to know there was an event only)
                            logging.info("Vibration: set motion = True")
                            Thread(target=motionDetected, args=[bridge_sensor_id]).start()


                        bridgeConfig["sensors"][bridge_sensor_id]["state"].update(message["state"])
                        current_time = datetime.now()
                        for key in message["state"].keys():
                            dxState["sensors"][bridge_sensor_id]["state"][key] = current_time
                        rulesProcessor(["sensors", bridge_sensor_id], current_time)
                        if "buttonevent" in message["state"] and bridgeConfig["config"]["deconz"]["sensors"][message["id"]]["modelid"] in ["TRADFRI remote control","RWL021","TRADFRI on/off switch"]:
                            if message["state"]["buttonevent"] in [1001, 2001, 3001, 4001, 5001]:
                                Thread(target=longPressButton, args=[bridge_sensor_id, message["state"]["buttonevent"]]).start()
                        if "presence" in message["state"] and message["state"]["presence"] and bridgeConfig["config"]["alarm"]["enabled"] and bridgeConfig["config"]["alarm"]["lasttriggered"] + 300 < datetime.now().timestamp():
                            logging.info("Alarm triggered, sending email...")
                            requests.post("https://diyhue.org/cdn/mailNotify.php", json={"to": bridgeConfig["config"]["alarm"]["email"], "sensor": bridgeConfig["sensors"][bridge_sensor_id]["name"]})
                            bridgeConfig["config"]["alarm"]["lasttriggered"] = int(datetime.now().timestamp())
                    elif "config" in message and bridgeConfig["sensors"][bridge_sensor_id]["config"]["on"]:
                        bridgeConfig["sensors"][bridge_sensor_id]["config"].update(message["config"])
                elif message["r"] == "lights":
                    bridge_light_id = bridgeConfig["config"]["deconz"]["lights"][message["id"]]["bridgeid"]
                    if "state" in message and "colormode" not in message["state"]:
                        bridgeConfig["lights"][bridge_light_id]["state"].update(message["state"])
                        updateGroupStats(bridge_light_id, bridgeConfig["lights"], bridgeConfig["groups"])
            except Exception as e:
                logging.info("unable to process the request" + str(e))

    try:
        deconz_ip = configManager.runtimeConfig.arg["DECONZ"]
        ws = EchoClient('ws://' + deconz_ip + ':' + str(bridgeConfig["config"]["deconz"]["websocketport"]))
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()
