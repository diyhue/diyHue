import uuid
import logManager
import weakref
from datetime import datetime, timezone
from HueObjects import genV2Uuid, v1StateToV2, v2StateToV1, setGroupAction, StreamEvent

logging = logManager.logger.get_logger(__name__)

class Group():

    def __init__(self, data):
        self.name = data["name"] if "name" in data else "Group " + \
            data["id_v1"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        if "owner" in data:
            self.owner = data["owner"]
        self.icon_class = data["class"] if "class" in data else "Other"
        self.lights = []
        self.action = {"on": False, "bri": 100, "hue": 0, "sat": 254, "effect": "none", "xy": [
            0.0, 0.0], "ct": 153, "alert": "none", "colormode": "xy"}
        self.sensors = []
        self.type = data["type"] if "type" in data else "LightGroup"
        self.state = {"all_on": False, "any_on": False}
        self.dxState = {"all_on": None, "any_on": None}

        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [self.getV2Room() if self.type == "Room" else self.getV2Zone()],
                         "id": str(uuid.uuid4()),
                         "type": "add"
                         }
        StreamEvent(streamMessage)

    def groupZeroStream(self, rooms, lights):
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"children": [], "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'bridge_home')),  "id_v1":"/groups/0", "type": "bridge_home"}],
                         "id": str(uuid.uuid4()),
                         "type": "update"
                         }
        for room in rooms:
            streamMessage["data"][0]["children"].append(
                {"rid": room, "rtype": "room"})
        for light in lights:
            streamMessage["data"][0]["children"].append(
                {"rid": light, "rtype": "light"})
        StreamEvent(streamMessage)

    def __del__(self):
        # Groupper light
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"id": self.id_v2,  "id_v1": "/groups/" + self.id_v1, "type": "grouped_light"}],
                         "id": str(uuid.uuid4()),
                         "type": "delete"
                         }
        streamMessage["id_v1"] = "/groups/" + self.id_v1
        StreamEvent(streamMessage)
        ### room / zone ####
        elementId = self.getV2Room(
        )["id"] if self.type == "Room" else self.getV2Zone()["id"]
        elementType = "room" if self.type == "Room" else "zone"
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"id": elementId,  "id_v1": "/groups/" + self.id_v1, "type": elementType}],
                         "id": str(uuid.uuid4()),
                         "type": "delete"
                         }
        StreamEvent(streamMessage)
        logging.info(self.name + " group was destroyed.")

    def add_light(self, light):
        self.lights.append(weakref.ref(light))
        elementId = self.getV2Room(
        )["id"] if self.type == "Room" else self.getV2Zone()["id"]
        elementType = "room" if self.type == "Room" else "zone"
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"alert": {"action_values": ["breathe"]}, "id": self.id_v2, "id_v1": "/groups/" + self.id_v1, "on":{"on": self.action["on"]}, "type": "grouped_light", }],
                         "id": str(uuid.uuid4()),
                         "type": "add"
                         }
        StreamEvent(streamMessage)
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"grouped_services": [{"rid": self.id_v2, "rtype": "grouped_light"}], "id": elementId, "id_v1": "/groups/" + self.id_v1, "type": elementType}],
                         "id": str(uuid.uuid4()),
                         "type": "update"
                         }

        StreamEvent(streamMessage)
        groupChildrens = []
        groupServices = []
        for light in self.lights:
            if light():
                groupChildrens.append(
                    {"rid": light().getDevice()["id"], "rtype": "device"})
                groupServices.append({"rid": light().id_v2, "rtype": "light"})
        groupServices.append({"rid": self.id_v2, "rtype": "grouped_light"})
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"children": groupChildrens, "id": elementId, "id_v1": "/groups/" + self.id_v1, "services": groupServices, "type": elementType}],
                         "id": str(uuid.uuid4()),
                         "type": "update"
                         }
        StreamEvent(streamMessage)

    def add_sensor(self, sensor):
        self.sensors.append(weakref.ref(sensor))

    def update_attr(self, newdata):
        if "lights" in newdata:  # update of the lights must be done using add_light function
            del newdata["lights"]
        if "class" in newdata:
            newdata["icon_class"] = newdata.pop("class")
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)

        streamMessage = {"creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [self.getV2Room() if self.type == "Room" else self.getV2Zone()],
                         "id": str(uuid.uuid4()),
                         "type": "update"
                         }
        StreamEvent(streamMessage)

    def update_state(self):
        all_on = True
        any_on = False
        bri = 0
        lights_on = 0
        if len(self.lights) == 0:
            all_on = False
        for light in self.lights:
            if light():
                if light().state["on"]:
                    any_on = True
                    if "bri" in light().state:
                        bri = bri + light().state["bri"]
                        lights_on = lights_on + 1
                else:
                    all_on = False
        if any_on:
            bri = (((bri/lights_on)/254)*100) if bri > 0 else 0
        return {"all_on": all_on, "any_on": any_on, "avr_bri": int(bri)}

    def setV2Action(self, state):
        v1State = v2StateToV1(state)
        setGroupAction(self, v1State)
        self.genStreamEvent(state)

    def setV1Action(self, state, scene=None):
        setGroupAction(self, state, scene)
        v2State = v1StateToV2(state)
        self.genStreamEvent(v2State)

    def genStreamEvent(self, v2State):
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                               "data": [],
                                 "id": str(uuid.uuid4()),
                                 "type": "update"
                                 }
        for num, light in enumerate(self.lights):
            if light():
                streamMessage["data"].insert(num,{
                    "id": light().id_v2,
                    "id_v1": "/lights/" + light().id_v1,
                    "owner": {
                        "rid": light().getDevice()["id"],
                        "rtype":"device"
                    },
                    "service_id": light().protocol_cfg["light_nr"]-1 if "light_nr" in light().protocol_cfg else 0,
                    "type": "light"
                })
                streamMessage["data"][num].update(v2State)
        StreamEvent(streamMessage)

        if "on" in v2State:
            v2State["dimming"] = {"brightness": self.update_state()["avr_bri"]}
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"id": self.id_v2,"id_v1": "/groups/" + self.id_v1, "type": "grouped_light",
                                   "owner": {
                                       "rid": self.getV2Room()["id"] if self.type == "Room" else self.getV2Zone()["id"],
                                       "rtype": "room" if self.type == "Room" else "zone"
                                   }
                                   }],
                         "id": str(uuid.uuid4()),
                         "type": "update"
                         }
        streamMessage["data"][0].update(v2State)
        StreamEvent(streamMessage)

    def getV1Api(self):
        result = {}
        result["name"] = self.name
        if hasattr(self, "owner"):
            result["owner"] = self.owner.username
        lights = []
        for light in self.lights:
            if light():
                lights.append(light().id_v1)
        sensors = []
        for sensor in self.sensors:
            if sensor():
                sensors.append(sensor().id_v1)
        result["lights"] = lights
        result["sensors"] = sensors
        result["type"] = self.type.capitalize()
        result["state"] = self.update_state()
        result["recycle"] = False
        if self.id_v1 == "0":
            result["presence"] = {
                "state": {"presence": None, "presence_all": None, "lastupdated": "none"}}
            result["lightlevel"] = {"state": {"dark": None, "dark_all": None, "daylight": None, "daylight_any": None,
                                              "lightlevel": None, "lightlevel_min": None, "lightlevel_max": None, "lastupdated": "none"}}
        else:
            result["class"] = self.icon_class.capitalize() if len(self.icon_class) > 2 else self.icon_class.upper()
        result["action"] = self.action
        return result

    def getV2Room(self):
        result = {"children": [], "services": []}
        for light in self.lights:
            if light():
                result["children"].append({
                    "rid": str(uuid.uuid5(
                        uuid.NAMESPACE_URL, light().id_v2 + 'device')),
                    "rtype": "device"
                })

        #result["grouped_services"].append({
        #    "rid": self.id_v2,
        #    "rtype": "grouped_light"
        #})
        result["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'room'))
        result["id_v1"] = "/groups/" + self.id_v1
        result["metadata"] = {
            "archetype": self.icon_class.replace(" ", "_").replace("'", "").lower(),
            "name": self.name
        }
        for light in self.lights:
            if light():
                result["services"].append({
                    "rid": light().id_v2,
                    "rtype": "light"
                })

        result["services"].append({
            "rid": self.id_v2,
            "rtype": "grouped_light"
        })

        result["type"] = "room"
        return result

    def getV2Zone(self):
        result = {"children": [], "services": []}
        for light in self.lights:
            if light():
                result["children"].append({
                    "rid": light().id_v2,
                    "rtype": "light"
                })

        #result["grouped_services"].append({
        #    "rid": self.id_v2,
        #    "rtype": "grouped_light"
        #})
        result["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'zone'))
        result["id_v1"] = "/groups/" + self.id_v1
        result["metadata"] = {
            "archetype": self.icon_class.replace(" ", "_").replace("'", "").lower(),
            "name": self.name
        }
        for light in self.lights:
            if light():
                result["services"].append({
                    "rid": light().id_v2,
                    "rtype": "light"
                })

        result["services"].append({
            "rid": self.id_v2,
            "rtype": "grouped_light"
        })

        result["type"] = "zone"
        return result

    def getV2GroupedLight(self):
        result = {}
        result["alert"] = {
            "action_values": [
                "breathe"
            ]
        }
        result["color"] = {}
        result["dimming"] = {"brightness": self.update_state()["avr_bri"]}
        result["dimming_delta"] = {}
        result["dynamics"] = {}
        result["id"] = self.id_v2
        result["id_v1"] = "/groups/" + self.id_v1
        result["on"] = {"on": self.update_state()["any_on"]}
        result["type"] = "grouped_light"
        if hasattr(self, "owner"):
            result["owner"] = {"rid": self.owner.username, "rtype": "device"}
        else:
            result["owner"] = {"rid": self.id_v2, "rtype": "device"}
        result["signaling"] = {"signal_values": [
            "no_signal",
            "on_off"]}

        return result

    def getObjectPath(self):
        return {"resource": "groups", "id": self.id_v1}

    def save(self):
        result = {"id_v2": self.id_v2, "name": self.name, "class": self.icon_class,
                  "lights": [], "action": self.action, "type": self.type}
        if hasattr(self, "owner"):
            result["owner"] = self.owner.username
        for light in self.lights:
            if light():
                result["lights"].append(light().id_v1)
        return result
