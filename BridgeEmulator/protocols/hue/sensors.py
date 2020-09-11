import logManager
import configManager
from functions import nextFreeId
from protocols.hue.scheduler import rulesProcessor
from time import sleep
from datetime import datetime, timedelta

bridge_config = configManager.bridgeConfig.json_config
dxState = configManager.runtimeConfig.dxState
logging = logManager.logger.get_logger(__name__)

def addHueMotionSensor(uniqueid, name="Hue motion sensor"):
    new_sensor_id = nextFreeId(bridge_config, "sensors")
    if uniqueid == "":
        uniqueid = "00:17:88:01:02:"
        if len(new_sensor_id) == 1:
            uniqueid += "0" + new_sensor_id
        else:
            uniqueid += new_sensor_id
    bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue temperature sensor 1", "uniqueid": uniqueid + ":d0:5b-02-0402", "type": "ZLLTemperature", "swversion": "6.1.0.18912", "state": {"temperature": None, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False, "battery": 100, "reachable": True, "alert":"none", "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
    motion_sensor = nextFreeId(bridge_config, "sensors")
    bridge_config["sensors"][motion_sensor] = {"name": name, "uniqueid": uniqueid + ":d0:5b-02-0406", "type": "ZLLPresence", "swversion": "6.1.0.18912", "state": {"lastupdated": "none", "presence": None}, "manufacturername": "Philips", "config": {"on": False,"battery": 100,"reachable": True, "alert": "lselect", "ledindication": False, "usertest": False, "sensitivity": 2, "sensitivitymax": 2,"pending": []}, "modelid": "SML001"}
    bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue ambient light sensor", "uniqueid": uniqueid + ":d0:5b-02-0400", "type": "ZLLLightLevel", "swversion": "6.1.0.18912", "state": {"dark": True, "daylight": False, "lightlevel": 6000, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False,"battery": 100, "reachable": True, "alert": "none", "tholddark": 21597, "tholdoffset": 7000, "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
    return(motion_sensor)

def addHueSwitch(uniqueid, sensorsType):
    new_sensor_id = nextFreeId(bridge_config, "sensors")
    if uniqueid == "":
        uniqueid = "00:17:88:01:02:"
        if len(new_sensor_id) == 1:
            uniqueid += "0" + new_sensor_id + ":4d:c6-02-fc00"
        else:
            uniqueid += new_sensor_id + ":4d:c6-02-fc00"
    bridge_config["sensors"][new_sensor_id] = {"state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "name": "Dimmer Switch" if sensorsType == "ZLLSwitch" else "Tap Switch", "type": sensorsType, "modelid": "RWL021" if sensorsType == "ZLLSwitch" else "ZGPSWITCH", "manufacturername": "Philips", "swversion": "5.45.1.17846" if sensorsType == "ZLLSwitch" else "", "uniqueid": uniqueid}
    return(new_sensor_id)



def motionDetected(sensor):
    logging.info("monitoring motion sensor " + sensor)
    while bridge_config["sensors"][sensor]["state"]["presence"] == True:
        if datetime.utcnow() - datetime.strptime(bridge_config["sensors"][sensor]["state"]["lastupdated"], "%Y-%m-%dT%H:%M:%S") > timedelta(seconds=30):
            bridge_config["sensors"][sensor]["state"]["presence"] = False
            bridge_config["sensors"][sensor]["state"]["lastupdated"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            current_time =  datetime.now()
            dxState["sensors"][sensor]["state"]["presence"] = current_time
            rulesProcessor(["sensors",sensor], current_time)
        sleep(1)
    logging.info("set motion sensor " + sensor + " to motion = False")
    return