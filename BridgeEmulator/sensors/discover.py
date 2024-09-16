import logManager
import configManager
from HueObjects import Sensor, Device
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
    motion_sensor = {"name": "Hue motion " + name[:21], "id_v1": motion_sensor_id, "protocol": protocol,
                     "modelid": "SML001", "type": "ZLLPresence", "protocol_cfg": protocol_cfg, "uniqueid": uniqueid + "-02-0406"}
    newMotionObj = Sensor.Sensor(motion_sensor)
    bridgeConfig["sensors"][motion_sensor_id] = newMotionObj
    new_sensor_id = nextFreeId(bridgeConfig, "sensors")
    light_sensor = {"name": "Hue ambient light " + name[:14], "id_v1": new_sensor_id, "protocol": protocol,
                    "modelid": "SML001", "type": "ZLLLightLevel", "protocol_cfg": protocol_cfg, "uniqueid": uniqueid + "-02-0400"}
    newLightObj = Sensor.Sensor(light_sensor)
    bridgeConfig["sensors"][new_sensor_id] = newLightObj
    new_sensor_id = nextFreeId(bridgeConfig, "sensors")
    temp_sensor = {"name": "Hue temperature " + name[:16], "id_v1": new_sensor_id, "protocol": protocol,
                   "modelid": "SML001", "type": "ZLLTemperature", "protocol_cfg": protocol_cfg, "uniqueid": uniqueid + "-02-0402"}
    newTemperatureObj = Sensor.Sensor(temp_sensor)
    bridgeConfig["sensors"][new_sensor_id] = newTemperatureObj
    newDeviceObj = Device.Device(motion_sensor)
    newDeviceObj.add_element("ZLLPresence", newMotionObj)
    newDeviceObj.add_element("ZLLLightLevel", newLightObj)
    newDeviceObj.add_element("ZLLTemperature", newTemperatureObj)
    bridgeConfig["device"][newDeviceObj.id_v2] = newDeviceObj

    return


def addHueSwitch(uniqueid, sensorsType):
    new_sensor_id = nextFreeId(bridgeConfig, "sensors")
    if uniqueid == "":
        uniqueid = "00:17:88:01:02:"
        if len(new_sensor_id) == 1:
            uniqueid += "0" + new_sensor_id + ":4d:c6-02-fc00"
        else:
            uniqueid += new_sensor_id + ":4d:c6-02-fc00"
    deviceData = {"id_v1": new_sensor_id, "state": {"buttonevent": 0, "lastupdated": "none"}, "config": {"on": True, "battery": 100, "reachable": True}, "name": "Dimmer Switch" if sensorsType == "ZLLSwitch" else "Tap Switch",
                  "type": sensorsType, "modelid": "RWL021" if sensorsType == "ZLLSwitch" else "ZGPSWITCH", "manufacturername": "Philips", "swversion": "5.45.1.17846" if sensorsType == "ZLLSwitch" else "", "uniqueid": uniqueid}
    bridgeConfig["sensors"][new_sensor_id] = Sensor.Sensor(deviceData)
    newDeviceObj = Device.Device(deviceData)
    newDeviceObj.add_element(
        deviceData["type"], bridgeConfig["sensors"][new_sensor_id])
    bridgeConfig["device"][newDeviceObj.id_v2] = newDeviceObj
    return (bridgeConfig["sensors"][new_sensor_id])


def addHueRotarySwitch(protocol_cfg):
    uniqueid = generate_unique_id()
    button_id = nextFreeId(bridgeConfig, "sensors")
    button = {"name": "Hue tap dial switch", "id_v1": button_id, "modelid": "RDM002",
              "type": "ZLLSwitch", "protocol_cfg": protocol_cfg, "uniqueid": uniqueid + "-02-0406"}
    bridgeConfig["sensors"][button_id] = Sensor.Sensor(button)
    rotary_id = nextFreeId(bridgeConfig, "sensors")
    rotary = {"name": "Hue tap dial switch", "id_v1": rotary_id, "modelid": "RDM002",
              "type": "ZLLRelativeRotary", "protocol_cfg": protocol_cfg, "uniqueid": uniqueid + "-02-0406"}
    bridgeConfig["sensors"][rotary_id] = Sensor.Sensor(rotary)
    newDeviceObj = Device.Device(button)
    newDeviceObj.add_element("ZLLSwitch", bridgeConfig["sensors"][button_id])
    newDeviceObj.add_element(
        "ZLLRelativeRotary", bridgeConfig["sensors"][rotary_id])
    bridgeConfig["device"][newDeviceObj.id_v2] = newDeviceObj
    return


def addHueSecureContactSensor(name, protocol, protocol_cfg):
    protocol_cfg["invisible_v1"] = True
    uniqueid = generate_unique_id()
    contact_id = nextFreeId(bridgeConfig, "sensors")
    contact = {"name": "Hue contact " + name, "id_v1": contact_id, "protocol": protocol, "modelid": "SOC001",
               "type": "ZLLContact", "protocol_cfg": protocol_cfg, "uniqueid": uniqueid + "-02-0402", "state": {"contact": "contact"}}
    bridgeConfig["sensors"][contact_id] = Sensor.Sensor(contact)
    tamper_id = nextFreeId(bridgeConfig, "sensors")
    tamper = {"name": "Hue tamper " + name, "id_v1": tamper_id, "protocol": protocol, "modelid": "SOC001",
              "type": "ZLLTamper", "protocol_cfg": protocol_cfg, "uniqueid": uniqueid + "-02-0404"}
    bridgeConfig["sensors"][tamper_id] = Sensor.Sensor(tamper)
    newDeviceObj = Device.Device(contact)
    newDeviceObj.add_element("ZLLContact", bridgeConfig["sensors"][contact_id])
    newDeviceObj.add_element("ZLLTamper", bridgeConfig["sensors"][tamper_id])
    bridgeConfig["device"][newDeviceObj.id_v2] = newDeviceObj
    return
