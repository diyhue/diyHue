import json
from datetime import datetime
from threading import Thread
from time import sleep

import requests

import configManager
import logManager
from functions import nextFreeId
from functions.request import sendRequest
from lightManager.core.updateGroup import updateGroupStats
from protocols.hue.scheduler import generateDxState, rulesProcessor
from protocols.hue.sensors import addHueMotionSensor, motionDetected

bridge_config = configManager.bridgeConfig.json_config
logging = logManager.logger.get_logger(__name__)
dxState = configManager.runtimeConfig.dxState

def scanDeconz():
    deconz_ip = configManager.runtimeConfig.arg["DECONZ"]
    if not bridge_config["deconz"]["enabled"]:
        if "username" not in bridge_config["deconz"]:
            try:
                registration = json.loads(sendRequest("http://" + deconz_ip + ":" + str(bridge_config["deconz"]["port"]) + "/api", "POST", "{\"username\": \"283145a4e198cc6535\", \"devicetype\":\"Hue Emulator\"}"))
            except:
                logging.info("registration fail, is the link button pressed?")
                return
            if "success" in registration[0]:
                bridge_config["deconz"]["username"] = registration[0]["success"]["username"]
                bridge_config["deconz"]["enabled"] = True
    if "username" in bridge_config["deconz"]:
        deconz_config = json.loads(sendRequest("http://" + deconz_ip + ":" + str(bridge_config["deconz"]["port"]) + "/api/" + bridge_config["deconz"]["username"] + "/config", "GET", "{}"))
        bridge_config["deconz"]["websocketport"] = deconz_config["websocketport"]

        #lights
        deconz_lights = json.loads(sendRequest("http://" + deconz_ip + ":" + str(bridge_config["deconz"]["port"]) + "/api/" + bridge_config["deconz"]["username"] + "/lights", "GET", "{}"))
        for light in deconz_lights:
            if light not in bridge_config["deconz"]["lights"] and "modelid" in deconz_lights[light]:
                new_light_id = nextFreeId(bridge_config, "lights")
                logging.info("register new light " + new_light_id)
                bridge_config["lights"][new_light_id] = deconz_lights[light]
                bridge_config["lights_address"][new_light_id] = {"username": bridge_config["deconz"]["username"], "light_id": light, "ip": deconz_ip + ":" + str(bridge_config["deconz"]["port"]), "protocol": "deconz"}
                bridge_config["deconz"]["lights"][light] = {"bridgeid": new_light_id, "modelid": deconz_lights[light]["modelid"], "type": deconz_lights[light]["type"]}

        #sensors
        deconz_sensors = json.loads(sendRequest("http://" + deconz_ip + ":" + str(bridge_config["deconz"]["port"]) + "/api/" + bridge_config["deconz"]["username"] + "/sensors", "GET", "{}"))
        for sensor in deconz_sensors:
            if sensor not in bridge_config["deconz"]["sensors"] and "modelid" in deconz_sensors[sensor]:
                new_sensor_id = nextFreeId(bridge_config, "sensors")
                if deconz_sensors[sensor]["modelid"] in ["TRADFRI remote control", "TRADFRI wireless dimmer"]:
                    logging.info("register new " + deconz_sensors[sensor]["modelid"])
                    bridge_config["sensors"][new_sensor_id] = {"config": deconz_sensors[sensor]["config"], "manufacturername": deconz_sensors[sensor]["manufacturername"], "modelid": deconz_sensors[sensor]["modelid"], "name": deconz_sensors[sensor]["name"], "state": deconz_sensors[sensor]["state"], "type": deconz_sensors[sensor]["type"], "uniqueid": deconz_sensors[sensor]["uniqueid"]}
                    if "swversion" in  deconz_sensors[sensor]:
                        bridge_config["sensors"][new_sensor_id]["swversion"] = deconz_sensors[sensor]["swversion"]
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                elif deconz_sensors[sensor]["modelid"] == "TRADFRI motion sensor":
                    logging.info("register TRADFRI motion sensor as Philips Motion Sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"], "lightsensor": "internal"}
                elif deconz_sensors[sensor]["modelid"] == "lumi.vibration.aq1":
                    logging.info("register Xiaomi Vibration sensor as Philips Motion Sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"], "lightsensor": "astral"}
                elif deconz_sensors[sensor]["modelid"] == "lumi.sensor_motion.aq2":
                    if deconz_sensors[sensor]["type"] == "ZHALightLevel":
                        logging.info("register new Xiaomi light sensor")
                        bridge_config["sensors"][new_sensor_id] = {"name": "Hue ambient light sensor 1", "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:], "type": "ZLLLightLevel", "swversion": "6.1.0.18912", "state": {"dark": True, "daylight": False, "lightlevel": 6000, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False,"battery": 100, "reachable": True, "alert": "none", "tholddark": 21597, "tholdoffset": 7000, "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
                        bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue temperature sensor 1", "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:-1] + "2", "type": "ZLLTemperature", "swversion": "6.1.0.18912", "state": {"temperature": None, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False, "battery": 100, "reachable": True, "alert":"none", "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
                        bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                    elif deconz_sensors[sensor]["type"] == "ZHAPresence":
                        logging.info("register new Xiaomi motion sensor")
                        bridge_config["sensors"][new_sensor_id] = {"name": deconz_sensors[sensor]["name"], "uniqueid": "00:17:88:01:02:" + deconz_sensors[sensor]["uniqueid"][12:], "type": "ZLLPresence", "swversion": "6.1.0.18912", "state": {"lastupdated": "none", "presence": None}, "manufacturername": "Philips", "config": {"on": False,"battery": 100,"reachable": True, "alert": "lselect", "ledindication": False, "usertest": False, "sensitivity": 2, "sensitivitymax": 2,"pending": []}, "modelid": "SML001"}
                        bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                elif deconz_sensors[sensor]["modelid"] == "lumi.sensor_motion":
                    logging.info("register Xiaomi Motion sensor w/o light sensor")
                    newMotionSensorId = addHueMotionSensor("", deconz_sensors[sensor]["name"])
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": newMotionSensorId, "triggered": False, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}
                else:
                    bridge_config["sensors"][new_sensor_id] = deconz_sensors[sensor]
                    bridge_config["deconz"]["sensors"][sensor] = {"bridgeid": new_sensor_id, "modelid": deconz_sensors[sensor]["modelid"], "type": deconz_sensors[sensor]["type"]}

            else: #temporary patch for config compatibility with new release
                bridge_config["deconz"]["sensors"][sensor]["modelid"] = deconz_sensors[sensor]["modelid"]
                bridge_config["deconz"]["sensors"][sensor]["type"] = deconz_sensors[sensor]["type"]
        generateDxState()

        if "websocketport" in bridge_config["deconz"]:
            logging.info("Starting deconz websocket")
            Thread(target=websocketClient).start()


def websocketClient():
    from ws4py.client.threadedclient import WebSocketClient
    class EchoClient(WebSocketClient):
        def opened(self):
            self.send("hello")

        def closed(self, code, reason=None):
            logging.info(("deconz websocket disconnected", code, reason))
            del bridge_config["deconz"]["websocketport"]

        def received_message(self, m):
            logging.info(m)
            message = json.loads(str(m))
            try:
                if message["r"] == "sensors":
                    bridge_sensor_id = bridge_config["deconz"]["sensors"][message["id"]]["bridgeid"]
                    if "state" in message and bridge_config["sensors"][bridge_sensor_id]["config"]["on"]:

                        #change codes for emulated hue Switches
                        if "hueType" in bridge_config["deconz"]["sensors"][message["id"]]:
                            rewriteDict = {"ZGPSwitch": {1002: 34, 3002: 16, 4002: 17, 5002: 18}, "ZLLSwitch" : {1002 : 1000, 2002: 2000, 2001: 2001, 2003: 2002, 3001: 3001, 3002: 3000, 3003: 3002, 4002: 4000, 5002: 4000} }
                            message["state"]["buttonevent"] = rewriteDict[bridge_config["deconz"]["sensors"][message["id"]]["hueType"]][message["state"]["buttonevent"]]
                        #end change codes for emulated hue Switches

                        #convert tradfri motion sensor notification to look like Hue Motion Sensor
                        if message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["modelid"] == "TRADFRI motion sensor":
                            #find the light sensor id
                            light_sensor = "0"
                            for sensor in bridge_config["sensors"].keys():
                                if bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel" and bridge_config["sensors"][sensor]["uniqueid"] == bridge_config["sensors"][bridge_sensor_id]["uniqueid"][:-1] + "0":
                                    light_sensor = sensor
                                    break
                            if bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "none":
                                message["state"].update({"dark": True})
                            elif bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "astral":
                                message["state"]["dark"] = not bridge_config["sensors"]["1"]["state"]["daylight"]

                            elif bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "combined":
                                if not bridge_config["sensors"]["1"]["state"]["daylight"]:
                                    message["state"]["dark"] = True
                                elif (datetime.strptime(message["state"]["lastupdated"], "%Y-%m-%dT%H:%M:%S") - datetime.strptime(bridge_config["sensors"][light_sensor]["state"]["lastupdated"], "%Y-%m-%dT%H:%M:%S")).total_seconds() > 1200:
                                    message["state"]["dark"] = False

                            if  message["state"]["dark"]:
                                bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                            else:
                                bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 25000
                            bridge_config["sensors"][light_sensor]["state"]["dark"] = message["state"]["dark"]
                            bridge_config["sensors"][light_sensor]["state"]["daylight"] = not message["state"]["dark"]
                            bridge_config["sensors"][light_sensor]["state"]["lastupdated"] = message["state"]["lastupdated"]

                        #Xiaomi motion w/o light level sensor
                        if message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["modelid"] == "lumi.sensor_motion":
                            for sensor in bridge_config["sensors"].keys():
                                if bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel" and bridge_config["sensors"][sensor]["uniqueid"] == bridge_config["sensors"][bridge_sensor_id]["uniqueid"][:-1] + "0":
                                    light_sensor = sensor
                                    break

                            if bridge_config["sensors"]["1"]["modelid"] == "PHDL00" and bridge_config["sensors"]["1"]["state"]["daylight"]:
                                bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 25000
                                bridge_config["sensors"][light_sensor]["state"]["dark"] = False
                            else:
                                bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                                bridge_config["sensors"][light_sensor]["state"]["dark"] = True

                        #convert xiaomi motion sensor to hue sensor
                        if message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["modelid"] == "lumi.sensor_motion.aq2" and message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["type"] == "ZHALightLevel":
                            bridge_config["sensors"][bridge_sensor_id]["state"].update(message["state"])
                            return
                        ##############

                        ##convert xiaomi vibration sensor states to hue motion sensor
                        if message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["modelid"] == "lumi.vibration.aq1":
                            #find the light sensor id
                            light_sensor = "0"
                            for sensor in bridge_config["sensors"].keys():
                                if bridge_config["sensors"][sensor]["type"] == "ZLLLightLevel" and bridge_config["sensors"][sensor]["uniqueid"] == bridge_config["sensors"][bridge_sensor_id]["uniqueid"][:-1] + "0":
                                    light_sensor = sensor
                                    break
                            logging.info("Vibration: emulated light sensor id is  " + light_sensor)
                            if bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "none":
                                message["state"].update({"dark": True})
                                logging.info("Vibration: set light sensor to dark because 'lightsensor' = 'none' ")
                            elif bridge_config["deconz"]["sensors"][message["id"]]["lightsensor"] == "astral":
                                message["state"]["dark"] = not bridge_config["sensors"]["1"]["state"]["daylight"]
                                logging.info("Vibration: set light sensor to " + str(not bridge_config["sensors"]["1"]["state"]["daylight"]) + " because 'lightsensor' = 'astral' ")

                            if  message["state"]["dark"]:
                                bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 6000
                            else:
                                bridge_config["sensors"][light_sensor]["state"]["lightlevel"] = 25000
                            bridge_config["sensors"][light_sensor]["state"]["dark"] = message["state"]["dark"]
                            bridge_config["sensors"][light_sensor]["state"]["daylight"] = not message["state"]["dark"]
                            bridge_config["sensors"][light_sensor]["state"]["lastupdated"] = message["state"]["lastupdated"]
                            message["state"] = {"motion": True, "lastupdated": message["state"]["lastupdated"]} #empty the message state for non Hue motion states (we need to know there was an event only)
                            logging.info("Vibration: set motion = True")
                            Thread(target=motionDetected, args=[bridge_sensor_id]).start()


                        bridge_config["sensors"][bridge_sensor_id]["state"].update(message["state"])
                        current_time = datetime.now()
                        for key in message["state"].keys():
                            dxState["sensors"][bridge_sensor_id]["state"][key] = current_time
                        rulesProcessor(["sensors", bridge_sensor_id], current_time)
                        if "buttonevent" in message["state"] and bridge_config["deconz"]["sensors"][message["id"]]["modelid"] in ["TRADFRI remote control","RWL021","TRADFRI on/off switch"]:
                            if message["state"]["buttonevent"] in [1001, 2001, 3001, 4001, 5001]:
                                Thread(target=longPressButton, args=[bridge_sensor_id, message["state"]["buttonevent"]]).start()
                        if "presence" in message["state"] and message["state"]["presence"] and bridge_config["emulator"]["alarm"]["on"] and bridge_config["emulator"]["alarm"]["lasttriggered"] + 300 < datetime.now().timestamp():
                            logging.info("Alarm triggered, sending email...")
                            requests.post("https://diyhue.org/cdn/mailNotify.php", json={"to": bridge_config["emulator"]["alarm"]["email"], "sensor": bridge_config["sensors"][bridge_sensor_id]["name"]})
                            bridge_config["emulator"]["alarm"]["lasttriggered"] = int(datetime.now().timestamp())
                    elif "config" in message and bridge_config["sensors"][bridge_sensor_id]["config"]["on"]:
                        bridge_config["sensors"][bridge_sensor_id]["config"].update(message["config"])
                elif message["r"] == "lights":
                    bridge_light_id = bridge_config["deconz"]["lights"][message["id"]]["bridgeid"]
                    if "state" in message and "colormode" not in message["state"]:
                        bridge_config["lights"][bridge_light_id]["state"].update(message["state"])
                        updateGroupStats(bridge_light_id, bridge_config["lights"], bridge_config["groups"])
            except Exception as e:
                logging.info("unable to process the request" + str(e))

    try:
        deconz_ip = configManager.runtimeConfig.arg["DECONZ"]
        ws = EchoClient('ws://' + deconz_ip + ':' + str(bridge_config["deconz"]["websocketport"]))
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()


def longPressButton(sensor, buttonevent):
    logging.info("long press detected")
    sleep(1)
    while bridge_config["sensors"][sensor]["state"]["buttonevent"] == buttonevent:
        logging.info("still pressed")
        current_time =  datetime.now()
        dxState["sensors"][sensor]["state"]["lastupdated"] = current_time
        rulesProcessor(["sensors",sensor], current_time)
        sleep(0.5)
    return