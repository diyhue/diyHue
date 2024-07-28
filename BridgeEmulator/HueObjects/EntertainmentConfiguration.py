import uuid
import logManager
import weakref
from datetime import datetime, timezone
from HueObjects import genV2Uuid, v1StateToV2, v2StateToV1, setGroupAction, StreamEvent

logging = logManager.logger.get_logger(__name__)

class EntertainmentConfiguration():
    def __init__(self, data):
        self.name = data["name"] if "name" in data else "Group " + \
            data["id_v1"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.configuration_type = data["configuration_type"] if "configuration_type" in data else "3dspace"
        self.lights = []
        self.action = {"on": False, "bri": 100, "hue": 0, "sat": 254, "effect": "none", "xy": [
            0.0, 0.0], "ct": 153, "alert": "none", "colormode": "xy"}
        self.sensors = []
        self.type = data["type"] if "type" in data else "Entertainment"
        self.configuration_type = data["configuration_type"] if "configuration_type" in data else "screen"
        self.locations = weakref.WeakKeyDictionary()
        self.stream = {"proxymode": "auto",
                       "proxynode": "/bridge", "active": False, "owner": None}
        self.state = {"all_on": False, "any_on": False}
        self.dxState = {"all_on": None, "any_on": None}

        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [self.getV2Api()],
                         "id": str(uuid.uuid4()),
                         "type": "add"
                         }
        StreamEvent(streamMessage)

    def __del__(self):
        # Groupper light
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"id": self.id_v2, "type": "grouped_light"}],
                         "id": str(uuid.uuid4()),
                         "type": "delete"
                         }
        streamMessage["id_v1"] = "/groups/" + self.id_v1
        StreamEvent(streamMessage)
        ### Entertainment area ###
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"id": self.getV2Api()["id"], "type": "entertainment_configuration"}],
                         "id": str(uuid.uuid4()),
                         "type": "delete"
                         }
        streamMessage["id_v1"] = "/groups/" + self.id_v1
        StreamEvent(streamMessage)
        logging.info(self.name + " entertainment area was destroyed.")

    def add_light(self, light):
        self.lights.append(weakref.ref(light))
        self.locations[light] = [{"x": 0, "y": 0, "z": 0}]

    def update_attr(self, newdata):
        if "lights" in newdata:  # update of the lights must be done using add_light function
            del newdata["lights"]
        if "locations" in newdata:  # update of the locations must be done directly from restful
            del newdata["locations"]
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)
        streamMessage = {"creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [self.getV2Api()],
                         "id": str(uuid.uuid4()),
                         "type": "update"
                         }
        StreamEvent(streamMessage)

    def update_state(self):
        all_on = True
        any_on = False
        if len(self.lights) == 0:
            all_on = False
        for light in self.lights:
            if light():
                if light().state["on"]:
                    any_on = True
                else:
                    all_on = False
        return {"all_on": all_on, "any_on": any_on}

    def getV2GroupedLight(self):
        result = {}
        result["alert"] = {
            "action_values": [
                "breathe"
            ]
        }
        result["id"] = self.id_v2
        result["id_v1"] = "/groups/" + self.id_v1
        result["on"] = {"on": self.update_state()["any_on"]}
        result["type"] = "grouped_light"
        return result

    def getV1Api(self):
        result = {}
        result["name"] = self.name
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
        result["type"] = self.type
        result["state"] = self.update_state()
        result["recycle"] = False
        class_type = "TV"
        if self.configuration_type == "3dspace":
            class_type == "Free"
        result["class"] = class_type
        result["action"] = self.action

        result["locations"] = {}
        locations = list(self.locations.items())
        for light, location in locations:
            if light.id_v1 in lights:
                result["locations"][light.id_v1] = [
                    location[0]["x"], location[0]["y"], location[0]["z"]]
        result["stream"] = self.stream
        return result

    def getV2Api(self):

        gradienStripPositions = [{"x": -0.4000000059604645, "y": 0.800000011920929, "z": -0.4000000059604645},
                                 {"x": -0.4000000059604645,
                                     "y": 0.800000011920929, "z": 0.0},
                                 {"x": -0.4000000059604645, "y": 0.800000011920929,
                                     "z": 0.4000000059604645},
                                 {"x": 0.0, "y": 0.800000011920929,
                                     "z": 0.4000000059604645},
                                 {"x": 0.4000000059604645, "y": 0.800000011920929,
                                     "z": 0.4000000059604645},
                                 {"x": 0.4000000059604645,
                                     "y": 0.800000011920929, "z": 0.0},
                                 {"x": 0.4000000059604645, "y": 0.800000011920929, "z": -0.4000000059604645}]

        result = {
            "configuration_type": self.configuration_type,
            "locations": {
                "service_locations": []
            },
            "metadata": {
                "name": self.name
            },
            "id_v1": "/groups/" + self.id_v1,
            "stream_proxy": {
                "mode": "auto",
                "node": {
                    "rid": str(uuid.uuid5(
                        uuid.NAMESPACE_URL, self.lights[0]().id_v2 + 'entertainment')) if len(self.lights) > 0 else None,
                    "rtype": "entertainment"
                }
            },
            "light_services": [],
            "channels": [],
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'entertainment_configuration')),
            "type": "entertainment_configuration",
            "name": self.name,
            "status": "active" if self.stream["active"] else "inactive"
        }
        if self.stream["active"]:
            result["active_streamer"] = {"rid": self.stream["owner"], "rtype": "auth_v1"}
        channel_id = 0
        for light in self.lights:
            if light():
                result["light_services"].append(
                    {"rtype": "light", "rid": light().id_v2})
                entertainmentUuid = str(uuid.uuid5(
                    uuid.NAMESPACE_URL, light().id_v2 + 'entertainment'))
                result["locations"]["service_locations"].append({"equalization_factor": 1, "positions": self.locations[light()],
                                                                 "service": {"rid": entertainmentUuid, "rtype": "entertainment"}, "position": self.locations[light()][0]})

                loops = 1
                gradientStrip = False
                if light().modelid in ["LCX001", "LCX002", "LCX003"]:
                    loops = len(gradienStripPositions)
                elif light().modelid in ["915005987201", "LCX004", "LCX006"]:
                    loops = len(self.locations[light()])
                for x in range(loops):
                    print("x:", x)
                    channel = {
                        "channel_id": channel_id,
                        "members": [
                            {
                                "index": x,
                                "service": {
                                    "rid": entertainmentUuid,
                                    "rtype": "entertainment"
                                }
                            }
                        ]
                    }
                    if light().modelid in ["LCX001", "LCX002", "LCX003"]:
                        channel["position"] = {"x": gradienStripPositions[x]["x"],
                                               "y": gradienStripPositions[x]["y"], "z": gradienStripPositions[x]["z"]}
                    elif light().modelid in ["915005987201", "LCX004", "LCX006"]:
                        if x == 0:
                            channel["position"] = {"x": self.locations[light(
                            )][0]["x"], "y": self.locations[light()][0]["y"], "z": self.locations[light()][0]["z"]}
                        elif x == 2:
                            channel["position"] = {"x": self.locations[light(
                            )][1]["x"], "y": self.locations[light()][1]["y"], "z": self.locations[light()][1]["z"]}
                        else:
                            channel["position"] = {"x": (self.locations[light()][0]["x"] + self.locations[light()][1]["x"]) / 2, "y": (self.locations[light(
                            )][0]["y"] + self.locations[light()][1]["y"]) / 2, "z": (self.locations[light()][0]["z"] + self.locations[light()][1]["z"]) / 2}
                    else:
                        channel["position"] = {"x": self.locations[light(
                        )][0]["x"], "y": self.locations[light()][0]["y"], "z": self.locations[light()][0]["z"]}

                    result["channels"].append(channel)
                    channel_id += 1

        return result

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
                         "data": [{"id": self.id_v2, "type": "grouped_light"}],
                         "id": str(uuid.uuid4()),
                         "type": "update"
                         }
        streamMessage["id_v1"] = "/groups/" + self.id_v1
        streamMessage.update(v2State)
        StreamEvent(streamMessage)

    def getObjectPath(self):
        return {"resource": "groups", "id": self.id_v1}

    def save(self):
        result = {"id_v2": self.id_v2, "name": self.name, "configuration_type": self.configuration_type,
                  "lights": [], "action": self.action, "type": self.type, "configuration_type": self.configuration_type}
        for light in self.lights:
            if light():
                result["lights"].append(light().id_v1)
        result["locations"] = {}
        locations = list(self.locations.items())
        for light, location in locations:
            if light.id_v1 in result["lights"]:
                result["locations"][light.id_v1] = location
        return result
