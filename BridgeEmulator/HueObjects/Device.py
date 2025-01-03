import uuid
import logManager
import weakref
from sensors.sensor_types import sensorTypes
from lights.light_types import lightTypes, archetype
from HueObjects import genV2Uuid, StreamEvent
from datetime import datetime, timezone

logging = logManager.logger.get_logger(__name__)


class Device():
    def __init__(self, data):
        self.id_v2 = data["id"] if "id" in data else genV2Uuid()
        self.id_v1 = self.id_v2  # used for config save
        self.name = data["name"]
        self.type = data["type"] if "type" in data else "ZLLLight"
        self.elements = {}
        self.modelid = data["modelid"]
        self.group_v1 = data["group_v1"] if "group_v1" in data else "sensors"
        self.protocol = data["protocol"] if "protocol" in data else "none"
        self.protocol_cfg = data["protocol_cfg"] if "protocol_cfg" in data else {
        }

    def __del__(self):
        logging.info(self.name + " device was destroyed.")
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"id": self.getDevice()["id"], "type": "device"}],
                         "id": str(uuid.uuid4()),
                         "type": "delete"
                         }
        StreamEvent(streamMessage)
        for element, obj in self.elements.items():
            del obj

    def add_element(self, type, element):
        self.elements[type] = weakref.ref(element)
        self.id_v2 = str(uuid.uuid5(
            uuid.NAMESPACE_URL, element.id_v2 + 'device'))
        # device
        streamMessage = {"creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [self.getDevice()],
                         "id": str(uuid.uuid4()),
                         "type": "add"
                         }
        StreamEvent(streamMessage)
        # zigbee_connectivity
        streamMessage = {"creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [self.getZigBee()],
                         "id": str(uuid.uuid4()),
                         "type": "add"
                         }
        StreamEvent(streamMessage)

        if self.group_v1 == "lights":
            # entertainment
            streamMessage = {"creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "data": [{"id": str(uuid.uuid5(
                                 uuid.NAMESPACE_URL, self.id_v2 + 'entertainment')), "type": "entertainent"}],
                             "id": str(uuid.uuid4()),
                             "type": "add"
                             }
            streamMessage["id_v1"] = "/lights/" + self.id_v1
            streamMessage["data"][0].update(self.getV2Entertainment())
            StreamEvent(streamMessage)

    def firstElement(self):
        rootKey = list(self.elements.keys())[0]
        return self.elements[rootKey]()

    def getSML001data(self):
        result = {}
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
        return result

    def setDevice(self, type, data):
        obj = None
        if type == "device":
            obj = self
        else:
            obj = self.elements[type]()
        if "metadata" in data and "name" in data["metadata"]:
            obj.name = data["metadata"]["name"]
            if type == "device":
                self.firstElement().name = data["metadata"]["name"]
        if "enabled" in data:
            obj.config["on"] = data["enabled"]

        streamMessage = {"creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [data],
                         "id": str(uuid.uuid4()),
                         "type": "update"
                         }
        streamMessage["data"][0].update(
            {"id_v1": "/sensors/" + obj.id_v1, "owner": {"rid": self.id_v2, "rtype": "device"}})
        StreamEvent(streamMessage)

    def getButtons(self):
        result = []
        start, buttonsCount = 0, 0
        if self.modelid in ["RWL022", "RWL021", "RWL020", "RDM002"]:
            buttonsCount = 4

        for button in range(start, buttonsCount):
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

    def getRWL02xData(self):
        result = {}
        result["product_data"] = {"model_id": self.modelid,
                                  "manufacturer_name": "Signify Netherlands B.V.",
                                  "product_name": "Hue dimmer switch",
                                  "product_archetype": "unknown_archetype",
                                  "certified": True,
                                  "software_version": "2.44.0",
                                  "hardware_platform_type": "100b-119"
                                  }
        result["services"] = []
        for button in self.getButtons():
            result["services"].append(
                {
                    "rid": button["id"],
                    "rtype": "button"
                }
            )

        result["services"].extend([{
            "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'device_power')),
            "rtype": "device_power"
        }, {
            "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'zigbee_connectivity')),
            "rtype": "zigbee_connectivity"
        }])
        return result

    def getRDM002Data(self):
        result = {}
        result["product_data"] = {"model_id": self.modelid,
                                  "manufacturer_name": "Signify Netherlands B.V.",
                                  "product_name": "Hue tap dial switch",
                                  "product_archetype": "unknown_archetype",
                                  "certified": True,
                                  "software_version": "2.59.25",
                                  "hardware_platform_type": "100b-119"
                                  }

        result["services"] = []
        for button in self.getButtons:
            result["services"].append(
                {
                    "rid": button["id"],
                    "rtype": "button"
                }
            )

        result["services"].extend([{
            "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'device_power')),
            "rtype": "device_power"
        }, {
            "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'zigbee_connectivity')),
            "rtype": "zigbee_connectivity"
        }])
        return result

    def getContactData(self):
        result = {}
        result["product_data"] = {"model_id": self.modelid,
                                  "product_name": "Hue secure contact sensor",
                                  "manufacturer_name": "Signify Netherlands B.V.",
                                  "product_archetype": "unknown_archetype",
                                  "certified": True,
                                  "software_version": "2.67.9",
                                  "hardware_platform_type": "100b-125"
                                  }
        result["services"] = [
            {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'device_power')),
                "rtype": "device_power"
            }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'zigbee_connectivity')),
                "rtype": "zigbee_connectivity"
            }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'contact')),
                "rtype": "contact"
            }, {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'tamper')),
                "rtype": "tamper"
            }
        ]
        return result

    def getLightData(self):
        result = {}
        result["product_data"] = lightTypes[self.modelid]["device"]
        result["product_data"]["model_id"] = self.modelid
        result["services"] = [
            {
                "rid": self.firstElement().id_v2,
                "rtype": "light"
            },
            {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'zigbee_connectivity')),
                "rtype": "zigbee_connectivity"
            },
            {
                "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'entertainment')),
                "rtype": "entertainment"
            }
        ]
        return result
    
    def getGenericDevice(self):
        result = {}
        result["product_data"] = {"model_id": self.modelid,
                                  "product_name": "Hue secure contact sensor",
                                  "manufacturer_name": sensorTypes[self.modelid]["ZHASwitch"]["static"]["manufacturername"],
                                  "product_archetype": "unknown_archetype",
                                  "certified": False,
                                  "software_version": sensorTypes[self.modelid]["ZHASwitch"]["static"]["swversion"],
                                  }
        result["services"] = []
        return result

    def getDevice(self):
        result = {}
        if self.modelid == "SML001":
            result = self.getSML001data()
        elif self.modelid in ["RWL022", "RWL021", "RWL020"]:
            result = self.getRWL02xData()
        elif self.modelid == "RDM002":
            result = self.getRDM002Data()
        elif self.modelid == "SOC001":
            result = self.getContactData()
        elif self.group_v1 == "lights":
            result = self.getLightData()
        else:
            result = self.getGenericDevice()
        result["metadata"] = {"name": self.name,
                              "archetype": "unknown_archetype"}  # for sensors
        if self.group_v1 == "lights":
            result["metadata"]["archetype"] = archetype[self.firstElement(
            ).config["archetype"]]
            result["metadata"]["function"] = "mixed"
        result["id"] = self.id_v2
        if "invisible_v1" not in self.firstElement().protocol_cfg:
            result["id_v1"] = "/" + self.type + "/" + self.firstElement().id_v1
        result["identify"] = {}
        result["type"] = "device"
        return result

    def getMotion(self):
        result = None
        if self.modelid == "SML001":
            result = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'motion')),
                      "id_v1": "/sensors/" + self.elements["ZLLPresence"]().id_v1,
                      "owner": {
                "rid": self.id_v2,
                "rtype": "device"
            },
                "enabled": self.elements["ZLLPresence"]().config["on"],
                "motion": {
                    "motion": self.elements["ZLLPresence"]().state["presence"],
                    "motion_valid": True,
                    "motion_report": {
                        "changed": self.elements["ZLLPresence"]().state["lastupdated"],
                        "motion": self.elements["ZLLPresence"]().state["presence"]
                    }
            },
                "sensitivity": {
                    "status": "set",
                    "sensitivity": 2,
                    "sensitivity_max": 2
            },
                "type": "motion"
            }

        return result

    def getTemperature(self):
        result = None
        if self.modelid == "SML001":
            temperature = self.elements["ZLLTemperature"](
            ).state["temperature"]
            result = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'temperature')),
                      "id_v1": "/sensors/" + self.elements["ZLLTemperature"]().id_v1,
                      "owner": {
                "rid": self.id_v2,
                "rtype": "device"
            },
                "enabled": self.elements["ZLLTemperature"]().config["on"],
                "temperature": {
                "temperature": temperature,
                "temperature_valid": True,
                "temperature_report": {
                    "changed": self.elements["ZLLTemperature"]().state["lastupdated"],
                    "temperature": temperature
                }
            },
                "type": "temperature"
            }
        return result

    def getContact(self):
        result = None
        if self.modelid == "SOC001":
            result = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'contact')),
                      "owner": {
                "rid": self.id_v2,
                "rtype": "device"
            },
            "enabled": self.elements["ZLLContact"]().config["on"],
            "contact_report": {
                "changed": self.elements["ZLLContact"]().state["lastupdated"],
                "state": "contact" if self.elements["ZLLContact"]().state["contact"] else "no_contact"
            },
            "type": "contact"
            }
        return result
    
    def getTamper(self):
        result = None
        if self.modelid == "SOC001":
            result = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'tamper')),
                      "owner": {
                "rid": self.id_v2,
                "rtype": "device"
            },
            "enabled": self.elements["ZLLTamper"]().config["on"],
            "tamper_reports": [{
                "changed": "2024-09-06T21:16:17.512Z",
                    "source": "battery_door",
                    "state": "not_tampered"
            }],
            "type": "tamper"
            }
        return result

    def getLightLevel(self):
        result = None
        if self.modelid == "SML001":
            result = {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'light_level')),
                "id_v1": "/sensors/" + self.elements["ZLLLightLevel"]().id_v1,
                "owner": {
                    "rid": self.id_v2,
                    "rtype": "device"
                },
                "enabled": self.elements["ZLLLightLevel"]().config["on"],
                "light": {
                    "light_level": self.elements["ZLLLightLevel"]().state["lightlevel"],
                    "light_level_valid": True,
                    "light_level_report": {
                        "changed": self.elements["ZLLLightLevel"]().state["lastupdated"],
                        "light_level": self.elements["ZLLLightLevel"]().state["lightlevel"]
                    }
                },
                "type": "light_level"
            }
        return result

    def getZigBee(self):
        result = {}
        result["id"] = str(uuid.uuid5(
            uuid.NAMESPACE_URL, self.id_v2 + 'zigbee_connectivity'))
        result["id_v1"] = "/" + self.type + "/" + self.firstElement().id_v1
        result["owner"] = {
            "rid": self.id_v2,
            "rtype": "device"
        }
        result["type"] = "zigbee_connectivity"
        result["mac_address"] = self.firstElement().uniqueid[:23]
        result["status"] = "connected"
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
                        "direction": "right",  # self.state["direction"],
                        "steps": self.state["expectedrotation"],
                        "duration": self.state["expectedeventduration"]
                    }
                },
                "type": "relative_rotary"
            })
        return result

    def getDevicePower(self):
        result = None
        if "battery" in self.firstElement().config:
            result = {
                "id": str(uuid.uuid5(
                    uuid.NAMESPACE_URL, self.id_v2 + 'device_power')),
                "id_v1": "/" + self.firstElement().getObjectPath()["resource"] + "/" + self.firstElement().getObjectPath()["id"],
                "owner": {
                    "rid": self.id_v2,
                    "rtype": "device"
                },
                "power_state": {},
                "type": "device_power"
            }
            if self.firstElement().config["battery"]:
                result["power_state"].update({"battery_level": self.firstElement().config["battery"],
                                              "battery_state": "normal"
                                              })
        return result

    def getV2Entertainment(self):
        if self.group_v1 != "lights":
            return None
        entertainmenUuid = str(uuid.uuid5(
            uuid.NAMESPACE_URL, self.id_v2 + 'entertainment'))
        result = {
            "equalizer": True,
            "id": entertainmenUuid,
            "id_v1": "/lights/" + self.firstElement().id_v1,
            "proxy": lightTypes[self.modelid]["v1_static"]["capabilities"]["streaming"]["proxy"],
            "renderer": lightTypes[self.modelid]["v1_static"]["capabilities"]["streaming"]["renderer"],
            "renderer_reference": {
                "rid": self.firstElement().id_v2,
                "rtype": "light"
            }
        }
        result["owner"] = {
            "rid": self.id_v2, "rtype": "device"}
        result["segments"] = {
            "configurable": False
        }
        if self.modelid == "LCX002":
            result["segments"]["max_segments"] = 7
            result["segments"]["segments"] = [
                {
                    "length": 2,
                    "start": 0
                },
                {
                    "length": 2,
                    "start": 2
                },
                {
                    "length": 4,
                    "start": 4
                },
                {
                    "length": 4,
                    "start": 8
                },
                {
                    "length": 4,
                    "start": 12
                },
                {
                    "length": 2,
                    "start": 16
                },
                {
                    "length": 2,
                    "start": 18
                }]
        elif self.modelid in ["915005987201", "LCX004", "LCX006"]:
            result["segments"]["max_segments"] = 10
            result["segments"]["segments"] = [
                {
                    "length": 3,
                    "start": 0
                },
                {
                    "length": 4,
                    "start": 3
                },
                {
                    "length": 3,
                    "start": 7
                }
            ]
        else:
            result["segments"]["max_segments"] = 1
            result["segments"]["segments"] = [{
                "length": 1,
                "start": 0
            }]
        result["type"] = "entertainment"
        return result

    def update_attr(self, newdata):
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)

    def save(self):
        result = {}
        result["name"] = self.name
        result["id"] = self.id_v2  # for config save compatibility
        result["elements"] = []
        result["type"] = self.type
        result["group_v1"] = self.group_v1
        result["modelid"] = self.modelid
        result["protocol"] = self.protocol
        result["protocol_cfg"] = self.protocol_cfg
        for key, element in self.elements.items():
            if element():
                result["elements"].append(element().id_v1)
            else:
                return None
        return result
