import datetime
import requests
import configManager
import logManager
import weakref
from HueObjects import Sensor
import json
from threading import Thread
from functions.rules import rulesProcessor
from ws4py.client.threadedclient import WebSocketClient
from sensors.discover import addHueMotionSensor
from functions.core import nextFreeId
from datetime import datetime, timezone
from time import sleep

bridgeConfig = configManager.bridgeConfig.yaml_config
logging = logManager.logger.get_logger(__name__)
devicesIds = {"sensors": {}, "lights": {}}
motionSensors = ["TRADFRI motion sensor", "lumi.sensor_motion", "lumi.vibration.aq1"]

def getObject(resource, id):
    if id in devicesIds[resource]:
        logging.debug("Cache Hit for " + resource + " " + id)
        return devicesIds[resource][id]()
    else:
        for key, device in bridgeConfig[resource].items():
            if device.protocol == "deconz" and device.protocol_cfg["deconzId"] == id:
                devicesIds[resource][id] = weakref.ref(device)
                logging.debug("Cache Miss for " + resource + " " + id)
                return device
        logging.debug("Device not found for " + resource + " " + id)
        return False

def longPressButton(sensor, buttonevent):
    logging.info("long press detected")
    sleep(1)
    while sensor.state["buttonevent"] == buttonevent:
        logging.info("still pressed")
        current_time =  datetime.now()
        sensor.dxState["lastupdated"] = current_time
        rulesProcessor(sensor, current_time)
        sleep(0.5)
    return

def scanDeconz():
    deconzConf = bridgeConfig["config"]["deconz"]
    deconz_config = requests.get("http://" + deconzConf["deconzHost"] + ":" + str(deconzConf["deconzPort"]) + "/api/" + deconzConf["deconzUser"] + "/config").json()
    deconzConf["websocketport"] = deconz_config["websocketport"]

    #sensors
    deconz_sensors = requests.get("http://" + deconzConf["deconzHost"] + ":" + str(deconzConf["deconzPort"]) + "/api/" + deconzConf["deconzUser"] + "/sensors").json()
    for id, sensor in deconz_sensors.items():
        if not getObject("sensors", id):
            new_sensor_id = nextFreeId(bridgeConfig, "sensors")
            if sensor["modelid"] in motionSensors:
                logging.info("register motion sensor as Philips Motion Sensor")
                addHueMotionSensor(sensor["name"], "deconz", {"lightSensor": "on", "deconzId": id, "modelid": sensor["modelid"]})
            elif sensor["modelid"] == "lumi.sensor_motion.aq2":
                if sensor["type"] == "ZHALightLevel":
                    logging.info("register new Xiaomi light sensor")
                    lightSensor = {"name": "Hue ambient light " + sensor["name"][:14], "id_v1": new_sensor_id, "protocol": "deconz", "modelid": "SML001", "type": "ZLLLightLevel", "protocol_cfg": {"deconzId": id}, "uniqueid": "00:17:88:01:02:" + sensor["uniqueid"][12:]}
                    bridgeConfig["sensors"][new_sensor_id] = Sensor.Sensor(lightSensor)
                elif sensor["type"] == "ZHAPresence":
                    logging.info("register new Xiaomi motion sensor")
                    motion_sensor = {"name": "Hue motion " + sensor["name"][:21], "id_v1": new_sensor_id, "protocol": "deconz", "modelid": "SML001", "type": "ZLLPresence", "protocol_cfg": {"deconzId": id}, "uniqueid": "00:17:88:01:02:" + sensor["uniqueid"][12:]}
                    bridgeConfig["sensors"][new_sensor_id] = Sensor.Sensor(motion_sensor)
                    new_sensor_id = nextFreeId(bridgeConfig, "sensors")
                    temp_sensor = {"name": "Hue temperature " + sensor["name"][:16], "id_v1": new_sensor_id, "protocol": "deconz", "modelid": "SML001", "type": "ZLLTemperature", "protocol_cfg": {"deconzId": "none", "id_v1": new_sensor_id}, "uniqueid": "00:17:88:01:02:" + sensor["uniqueid"][12:-1] + "2"}
                    bridgeConfig["sensors"][new_sensor_id] = Sensor.Sensor(temp_sensor)
            elif sensor["modelid"] not in ["PHDL00"]:
                logging.info("register new sensor " + sensor["name"])
                sensor.update({"protocol": "deconz", "protocol_cfg": {"deconzId": id}, "id_v1": new_sensor_id})
                bridgeConfig["sensors"][new_sensor_id] = Sensor.Sensor(sensor)

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
                    bridgeSensor = getObject("sensors", message["id"])
                    if "config" in message and bridgeSensor.config["on"]:
                        bridgeSensor.config.update(message["config"])
                    elif "state" in message and message["state"] and bridgeSensor.config["on"]:
                        #convert tradfri motion sensor notification to look like Hue Motion Sensor
                        if bridgeSensor.modelid == "SML001" and "lightSensor" in bridgeSensor.protocol_cfg:
                            #find the light sensor id
                            lightSensor = None
                            for key, sensor in bridgeConfig["sensors"].items():
                                if sensor.type == "ZLLLightLevel" and sensor.uniqueid == bridgeSensor.uniqueid[:-1] + "0":
                                    lightSensor = sensor
                                    break

                            if lightSensor.protocol_cfg["lightSensor"] == "no":
                                lightSensor.state["dark"] = True
                            else:
                                lightSensor.state["dark"] = not bridgeConfig["sensors"]["1"].state["daylight"]
                            if  lightSensor.state["dark"]:
                                lightSensor.state["lightlevel"] = 6000
                            else:
                                lightSensor.state["lightlevel"] = 25000
                            lightSensor.state["daylight"] = not lightSensor.state["dark"]
                            lightSensor.state["lastupdated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                            if "dark" in message["state"]:
                                del message["state"]["dark"]

                        if bridgeSensor.modelid == "SML001" and "lightlevel" in message["state"]:
                            if message["state"]["lightlevel"] > bridgeSensor.config["tholddark"]:
                                message["state"]["dark"] = False
                            else:
                                message["state"]["dark"] = True

                        bridgeSensor.state.update(message["state"])
                        current_time = datetime.now()
                        for key in message["state"].keys():
                            bridgeSensor.dxState[key] = current_time
                        rulesProcessor(bridgeSensor, current_time)

                        if "buttonevent" in message["state"] and bridgeSensor.modelid in ["TRADFRI remote control","RWL021","TRADFRI on/off switch"]:
                            if message["state"]["buttonevent"] in [1001, 2001, 3001, 4001, 5001]:
                                Thread(target=longPressButton, args=[bridgeSensor, message["state"]["buttonevent"]]).start()
                        if "presence" in message["state"] and message["state"]["presence"] and bridgeConfig["config"]["alarm"]["enabled"] and bridgeConfig["config"]["alarm"]["lasttriggered"] + 300 < datetime.now().timestamp():
                            logging.info("Alarm triggered, sending email...")
                            requests.post("https://diyhue.org/cdn/mailNotify.php", json={"to": bridgeConfig["config"]["alarm"]["email"], "sensor": bridgeSensor.name})
                            bridgeConfig["config"]["alarm"]["lasttriggered"] = int(datetime.now().timestamp())
                elif message["r"] == "lights":
                    bridgeLightId = getObject("lights", message["id"])
                    if "state" in message and "colormode" not in message["state"]:
                        bridgeLightId.state.update(message["state"])
            except Exception as e:
                logging.info("unable to process the request" + str(e))

    try:
        ws = EchoClient('ws://' + bridgeConfig["config"]["deconz"]["deconzHost"] + ':' + str(bridgeConfig["config"]["deconz"]["websocketport"]))
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()
