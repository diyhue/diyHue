import uuid
import logManager
from sensors.sensor_types import sensorTypes
from HueObjects import genV2Uuid, StreamEvent
from datetime import datetime, timezone
from copy import deepcopy

logging = logManager.logger.get_logger(__name__)

class Sensor():
    def __init__(self, data):
        if data["modelid"] in sensorTypes:
            if "manufacturername" not in data:
                data["manufacturername"] = sensorTypes[data["modelid"]
                                                       ][data["type"]]["static"]["manufacturername"]
            if "config" not in data:
                data["config"] = deepcopy(
                    sensorTypes[data["modelid"]][data["type"]]["config"])
            if "state" not in data:
                data["state"] = deepcopy(
                    sensorTypes[data["modelid"]][data["type"]]["state"])
            if "swversion" not in data:
                data["swversion"] = sensorTypes[data["modelid"]
                                                ][data["type"]]["static"]["swversion"]
        if "config" not in data:
            data["config"] = {}
        if "reachable" not in data["config"]:
            data["config"]["reachable"] = True
        if "on" not in data["config"]:
            data["config"]["on"] = True
        if "state" not in data:
            data["state"] = {}
        if "lastupdated" not in data["state"]:
            data["state"]["lastupdated"] = "none"
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.config = data["config"]
        self.modelid = data["modelid"]
        self.manufacturername = data["manufacturername"] if "manufacturername" in data else "Philips"
        self.protocol = data["protocol"] if "protocol" in data else "none"
        self.protocol_cfg = data["protocol_cfg"] if "protocol_cfg" in data else {
        }
        self.type = data["type"]
        self.state = data["state"]
        dxstate = {}
        for state in data["state"].keys():
            dxstate[state] = datetime.now()
        self.dxState = dxstate
        self.swversion = data["swversion"] if "swversion" in data else None
        self.recycle = data["recycle"] if "recycle" in data else False
        self.uniqueid = data["uniqueid"] if "uniqueid" in data else None
        if self.getDevice() != None:
            streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "data": [{"id": self.id_v2, "type": "device"}],
                             "id": str(uuid.uuid4()),
                             "type": "add"
                             }
            streamMessage["data"][0].update(self.getDevice())
            StreamEvent(streamMessage)

    def __del__(self):
        if self.modelid in ["SML001", "RWL022"]:
            streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"id": self.getDevice()["id"], "type": "device"}],
                         "id": str(uuid.uuid4()),
                         "type": "delete"
                         }
            streamMessage["id_v1"] = "/sensors/" + self.id_v1
            StreamEvent(streamMessage)
        logging.info(self.name + " sensor was destroyed.")

    def setV1State(self, state):
        self.state.update(state)

    def getBridgeHome(self):
        if self.modelid == "SML001":
            if self.type == "ZLLPresence":
                rtype = "motion"
            elif self.type == "ZLLLightLevel":
                rtype = "light_level"
            elif self.type == "ZLLTemperature":
                rtype = "temperature"
            return {
                "rid": self.id_v2,
                "rtype": rtype
            }
        else:
            return {
                "rid": self.id_v2,
                "rtype": 'device'
            }
        return False

    def getV1Api(self):
        result = {}
        if self.modelid in sensorTypes:
            result = sensorTypes[self.modelid][self.type]["static"]
        result["state"] = self.state
        if self.config != None:
            result["config"] = self.config
        result["name"] = self.name
        result["type"] = self.type
        result["modelid"] = self.modelid
        result["manufacturername"] = self.manufacturername
        if self.swversion != None:
            result["swversion"] = self.swversion
        if self.uniqueid != None:
            result["uniqueid"] = self.uniqueid
        if self.recycle == True:
            result["recycle"] = self.recycle
        return result

    def getObjectPath(self):
        return {"resource": "sensors", "id": self.id_v1}

    def getDevice(self):
        result = None
        if self.modelid == "SML001" and self.type == "ZLLPresence":
            result = {"id": self.id_v2, "id_v1": "/sensors/" + self.id_v1, "type": "device"}
            result["identify"] = {}
            result["metadata"] = {
                "archetype": "unknown_archetype",
                "name": self.name
            }
            result["product_data"] = {
                "certified": True,
                "manufacturer_name": "Signify Netherlands B.V.",
                "model_id": self.modelid,
                "product_archetype": "unknown_archetype",
                "product_name": "Hue motion sensor",
                "software_version": "1.1.27575"
            }
            result["services"] = [
                {
                    "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'motion')),
                    "rtype": "motion"
                },
                {
                    "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'device_power')),
                    "rtype": "device_power"
                },
                {
                    "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'zigbee_connectivity')),
                    "rtype": "zigbee_connectivity"
                },
                {
                    "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'light_level')),
                    "rtype": "light_level"
                },
                {
                    "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'temperature')),
                    "rtype": "temperature"
                }]
            result["type"] = "device"
        elif self.modelid == "RWL022" or self.modelid == "RWL021" or self.modelid == "RWL020":
            result = {"id": self.id_v2, "id_v1": "/sensors/" + self.id_v1, "type": "device"}
            result["identify"] = {}
            result["product_data"] = {"model_id": self.modelid,
                "manufacturer_name": "Signify Netherlands B.V.",
                "product_name": "Hue dimmer switch",
                "product_archetype": "unknown_archetype",
                "certified": True,
                "software_version": "2.44.0",
                "hardware_platform_type": "100b-119"
            }
            result["metadata"] = {
                "archetype": "unknown_archetype",
                "name": self.name
            }
            result["services"] = [{
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'button1')),
                "rtype": "button"
                }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'button2')),
                "rtype": "button"
                }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'button3')),
                "rtype": "button"
                }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'button4')),
                "rtype": "button"
                }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'device_power')),
                "rtype": "device_power"
                }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'zigbee_connectivity')),
                "rtype": "zigbee_connectivity"
                }]
            result["type"] = "device"
        elif self.modelid == "RDM002" and self.type != "ZLLRelativeRotary":
            result = {"id": self.id_v2, "id_v1": "/sensors/" + self.id_v1, "type": "device"}
            result["identify"] = {}
            result["product_data"] = {"model_id": self.modelid,
                "manufacturer_name": "Signify Netherlands B.V.",
                "product_name": "Hue tap dial switch",
                "product_archetype": "unknown_archetype",
                "certified": True,
                "software_version": "2.59.25",
                "hardware_platform_type": "100b-119"
            }
            result["metadata"] = {
                "archetype": "unknown_archetype",
                "name": self.name
            }
            result["services"] = [{
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'button1')),
                "rtype": "button"
                }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'button2')),
                "rtype": "button"
                }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'button3')),
                "rtype": "button"
                }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'button4')),
                "rtype": "button"
                }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'device_power')),
                "rtype": "device_power"
                }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'zigbee_connectivity')),
                "rtype": "zigbee_connectivity"
                }]
            result["type"] = "device"
        elif self.modelid == "RDM002" and self.type == "ZLLRelativeRotary":
            result = {"id": self.id_v2, "id_v1": "/sensors/" + self.id_v1, "type": "device"}
            result["identify"] = {}
            result["product_data"] = {"model_id": self.modelid,
                "manufacturer_name": "Signify Netherlands B.V.",
                "product_name": "Hue tap dial switch",
                "product_archetype": "unknown_archetype",
                "certified": True,
                "software_version": "2.59.25",
                "hardware_platform_type": "100b-119"
            }
            result["metadata"] = {
                "archetype": "unknown_archetype",
                "name": self.name
            }
            result["services"] = [{
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'relative_rotary')),
                "rtype": "relative_rotary"
                }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'device_power')),
                "rtype": "device_power"
                }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'zigbee_connectivity')),
                "rtype": "zigbee_connectivity"
                }]
            result["type"] = "device"
        return result

    def getMotion(self):
        result = None
        if self.modelid == "SML001" and self.type == "ZLLPresence":
            result = {
                "enabled": self.config["on"],
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'motion')),
                "id_v1": "/sensors/" + self.id_v1,
                "motion": {
                    "motion_report": {
                        "changed": self.state["lastupdated"],
                        "motion": True if self.state["presence"] else False,
                    }
                },
                "sensitivity": {
                    "status": "set",
                    "sensitivity": 2,
                    "sensitivity_max": 2
                },
                "owner": {
                    "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'device')),
                    "rtype": "device"
                },
                "type": "motion"}
        return result
    
    def getTemperature(self):
        result = None
        if self.modelid == "SML001" and self.type == "ZLLTemperature":
            result = {
                "enabled": self.config["on"],
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'temperature')),
                "id_v1": "/sensors/" + self.id_v1,
                "temperature": {
                    "temperature_report":{
                        "changed": self.state["lastupdated"],
                        "temperature": self.state["temperature"]/100
                    }
                },
                "owner": {
                    "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'device')),
                    "rtype": "device"
                },
                "type": "temperature"}
        return result
    
    def getLightlevel(self):
        result = None
        if self.modelid == "SML001" and self.type == "ZLLLightLevel":
            result = {
                "enabled": self.config["on"],
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'light_level')),
                "id_v1": "/sensors/" + self.id_v1,
                "light": {
                    "light_level_report":{
                        "changed": self.state["lastupdated"],
                        "light_level": self.state["lightlevel"]
                    }
                },
                "owner": {
                    "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'device')),
                    "rtype": "device"
                },
                "type": "light_level"}
        return result

    def getZigBee(self):
        result = None
        if self.modelid == "SML001" and self.type != "ZLLPresence":
            return None
        if not self.uniqueid:
            return None
        result = {}
        result["id"] = str(uuid.uuid5(
            uuid.NAMESPACE_URL, self.id_v2 + 'zigbee_connectivity'))
        result["id_v1"] = "/sensors/" + self.id_v1
        result["owner"] = {
            "rid": self.id_v2,
            "rtype": "device"
            }
        result["type"] = "zigbee_connectivity"
        result["mac_address"] = self.uniqueid[:23]
        result["status"] = "connected"
        return result
    
    def getButtons(self):
        result = []
        if self.modelid == "RWL022" or self.modelid == "RWL021" or self.modelid == "RWL020" or self.modelid == "RDM002" and self.type != "ZLLRelativeRotary":
            for button in range(4):
                result.append({
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'button' + str(button + 1))),
                "id_v1": "/sensors/" + self.id_v1,
                "owner": {
                  "rid": self.id_v2,
                  "rtype": "device"
                },
                "metadata": {
                  "control_id": button + 1
                },
                "button": {
                        "last_event": "short_release",
                        "button_report": {
                            "updated": self.state["lastupdated"],
                            "event": "initial_press"
                        },
                        "repeat_interval": 800,
                        "event_values": [
                            "initial_press",
                            "repeat",
                            "short_release",
                            "long_release",
                            "long_press"
                        ]
                    },
                "type": "button"
              })
        return result
    
    def getRotary(self):
        result = []
        if self.modelid == "RDM002" and self.type == "ZLLRelativeRotary":
            result.append({
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'relative_rotary')),
                "id_v1": "/sensors/" + self.id_v1,
                "owner": {
                  "rid": self.id_v2,
                  "rtype": "device"
                },
                "rotary_report": {
                    "updated": self.state["lastupdated"],
                    "action": "start" if self.state["rotaryevent"] == 1 else "repeat",
                    "rotation": {
                        "direction": "right",#self.state["direction"],
                        "steps": self.state["expectedrotation"],
                        "duration": self.state["expectedeventduration"]
                    }
                },
                "type": "relative_rotary"
            })
        return result

    def getDevicePower(self):
        result = None
        if "battery" in self.config:
            result = {
                "id": str(uuid.uuid5(
                    uuid.NAMESPACE_URL, self.id_v2 + 'device_power')),
                "id_v1": "/sensors/" + self.id_v1,
                "owner": {
                    "rid": self.id_v2,
                    "rtype": "device"
                },
                "power_state": {},
                "type": "device_power"
            }
            if self.config["battery"]:
                result["power_state"].update({"battery_level": self.config["battery"],
                    "battery_state": "normal"
                    })
        return result

    def update_attr(self, newdata):
        if self.id_v1 == "1" and "config" in newdata:  # manage daylight sensor
            if "long" in newdata["config"] and "lat" in newdata["config"]:
                self.config["configured"]=True
                self.protocol_cfg={"long": float(
                    newdata["config"]["long"][:-1]), "lat": float(newdata["config"]["lat"][:-1])}
                return
        for key, value in newdata.items():
            updateAttribute=getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)

    def save(self):
        result={}
        result["name"]=self.name
        result["id_v1"]=self.id_v1
        result["id_v2"]=self.id_v2
        result["state"]=self.state
        result["config"]=self.config
        result["type"]=self.type
        result["modelid"]=self.modelid
        result["manufacturername"]=self.manufacturername
        result["uniqueid"]=self.uniqueid
        result["swversion"]=self.swversion
        result["protocol"]=self.protocol
        result["protocol_cfg"]=self.protocol_cfg
        return result
