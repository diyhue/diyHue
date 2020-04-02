import json
import sys
import logging
import os
from pprint import pprint
from subprocess import Popen
from functions import nextFreeId

cwd = os.path.split(os.path.abspath(__file__))[0]

#load config files
def load_config(path):
    with open(path, 'r', encoding="utf-8") as fp:
        return json.load(fp)

def saveConfig(bridge_config, docker=False,  filename='config.json'):
    with open(cwd + '/../' + filename, 'w', encoding="utf-8") as fp:
        json.dump(bridge_config, fp, sort_keys=True, indent=4, separators=(',', ': '))
    if docker:
        Popen(["cp", cwd + '/../' + filename, cwd + '/' + 'export/'])

def loadConfig():
    try:
        path = cwd + '/../config.json'
        if os.path.exists(path):
            bridge_config = load_config(path)
            logging.info("Config loaded")
            return bridge_config
        else:
            logging.info("Config not found, creating new config from default settings")
            bridge_config = load_config(cwd + '/default-config.json')
            saveConfig(bridge_config)
            return bridge_config
    except Exception:
        logging.exception("CRITICAL! Config file was not loaded")
        sys.exit(1)

def addHueMotionSensor(uniqueid, bridge_config, name="Hue motion sensor"):
    new_sensor_id = nextFreeId(bridge_config, "sensors")
    if uniqueid == "":
        uniqueid = "00:17:88:01:02:"
        if len(new_sensor_id) == 1:
            uniqueid += "0" + new_sensor_id
        else:
            uniqueid += new_sensor_id
    bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue temperature sensor "  + new_sensor_id, "uniqueid": uniqueid + ":d0:5b-02-0402", "type": "ZLLTemperature", "swversion": "6.1.0.18912", "state": {"temperature": None, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False, "battery": 100, "reachable": True, "alert":"none", "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
    motion_sensor = nextFreeId(bridge_config, "sensors")
    bridge_config["sensors"][motion_sensor] = {"name": name, "uniqueid": uniqueid + ":d0:5b-02-0406", "type": "ZLLPresence", "swversion": "6.1.0.18912", "state": {"lastupdated": "none", "presence": None}, "manufacturername": "Philips", "config": {"on": False,"battery": 100,"reachable": True, "alert": "lselect", "ledindication": False, "usertest": False, "sensitivity": 2, "sensitivitymax": 2,"pending": []}, "modelid": "SML001"}
    bridge_config["sensors"][nextFreeId(bridge_config, "sensors")] = {"name": "Hue ambient light sensor " + new_sensor_id, "uniqueid": uniqueid + ":d0:5b-02-0400", "type": "ZLLLightLevel", "swversion": "6.1.0.18912", "state": {"dark": True, "daylight": False, "lightlevel": 6000, "lastupdated": "none"}, "manufacturername": "Philips", "config": {"on": False,"battery": 100, "reachable": True, "alert": "none", "tholddark": 21597, "tholdoffset": 7000, "ledindication": False, "usertest": False, "pending": []}, "modelid": "SML001"}
    return(motion_sensor)

def addHueSwitch(uniqueid, sensorsType, bridge_config):
    new_sensor_id = nextFreeId(bridge_config, "sensors")
    if uniqueid == "":
        uniqueid = "00:17:88:01:02:"
        if len(new_sensor_id) == 1:
            uniqueid += "0" + new_sensor_id + ":4d:c6-02-fc00"
        else:
            uniqueid += new_sensor_id + ":4d:c6-02-fc00"
    bridge_config["sensors"][new_sensor_id] = {"state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "name": "Dimmer Switch" if sensorsType == "ZLLSwitch" else "Tap Switch", "type": sensorsType, "modelid": "RWL021" if sensorsType == "ZLLSwitch" else "ZGPSWITCH", "manufacturername": "Philips", "swversion": "5.45.1.17846" if sensorsType == "ZLLSwitch" else "", "uniqueid": uniqueid}
    return(new_sensor_id)
