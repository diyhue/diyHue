import logManager
import configManager
from HueObjects import Sensor
import random
from functions.core import nextFreeId

logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config


def generate_unique_id():
    rand_bytes = [random.randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:03:%02x:%02x:%02x" % (rand_bytes[0], rand_bytes[1], rand_bytes[2])

def addHueMotionSensor(name, protocol, protocol_cfg):
    uniqueid = generate_unique_id()
    motion_sensor_id = nextFreeId(bridgeConfig, "sensors")
    motion_sensor = {"name": "Hue motion " + name[:21], "id_v1": motion_sensor_id, "protocol": protocol, "modelid": "SML001", "type": "ZLLPresence", "protocol_cfg": protocol_cfg, "uniqueid": uniqueid + "-02-0406"}
    bridgeConfig["sensors"][motion_sensor_id] = Sensor.Sensor(motion_sensor)
    new_sensor_id = nextFreeId(bridgeConfig, "sensors")
    light_sensor = {"name": "Hue ambient light " + name[:14], "id_v1": new_sensor_id, "protocol": protocol, "modelid": "SML001", "type": "ZLLLightLevel", "protocol_cfg": protocol_cfg, "uniqueid": uniqueid + "-02-0400"}
    bridgeConfig["sensors"][new_sensor_id] = Sensor.Sensor(light_sensor)
    new_sensor_id = nextFreeId(bridgeConfig, "sensors")
    temp_sensor = {"name": "Hue temperature " + name[:16], "id_v1": new_sensor_id, "protocol": protocol, "modelid": "SML001", "type": "ZLLTemperature", "protocol_cfg": protocol_cfg, "uniqueid": uniqueid + "-02-0402"}
    bridgeConfig["sensors"][new_sensor_id] = Sensor.Sensor(temp_sensor)
    return


def addHueSwitch(uniqueid, sensorsType):
    new_sensor_id = nextFreeId(bridgeConfig, "sensors")
    if uniqueid == "":
        uniqueid = "00:17:88:01:02:"
        if len(new_sensor_id) == 1:
            uniqueid += "0" + new_sensor_id + ":4d:c6-02-fc00"
        else:
            uniqueid += new_sensor_id + ":4d:c6-02-fc00"
    deviceData = {"id_v1": new_sensor_id, "state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "name": "Dimmer Switch" if sensorsType == "ZLLSwitch" else "Tap Switch", "type": sensorsType, "modelid": "RWL021" if sensorsType == "ZLLSwitch" else "ZGPSWITCH", "manufacturername": "Philips", "swversion": "5.45.1.17846" if sensorsType == "ZLLSwitch" else "", "uniqueid": uniqueid}
    bridgeConfig["sensors"][new_sensor_id] = Sensor.Sensor(deviceData)
    return(bridgeConfig["sensors"][new_sensor_id])

def addHueRotarySwitch(protocol_cfg):
    uniqueid = generate_unique_id()
    button_id = nextFreeId(bridgeConfig, "sensors")
    button = {"name": "Hue tap dial switch", "id_v1": button_id, "modelid": "RDM002", "type": "ZLLSwitch", "protocol_cfg": protocol_cfg, "uniqueid": uniqueid + "-02-0406"}
    bridgeConfig["sensors"][button_id] = Sensor.Sensor(button)

    rotary_id = nextFreeId(bridgeConfig, "sensors")
    rotary = {"name": "Hue tap dial switch", "id_v1": rotary_id, "modelid": "RDM002", "type": "ZLLRelativeRotary", "protocol_cfg": protocol_cfg, "uniqueid": uniqueid + "-02-0406"}
    bridgeConfig["sensors"][rotary_id] = Sensor.Sensor(rotary)
    return
