import uuid
import logManager
import random
import weakref
from lights.light_types import lightTypes
from sensors.sensor_types import sensorTypes
from lights.protocols import protocols
from datetime import datetime
from pprint import pprint

logging = logManager.logger.get_logger(__name__)


def genV2Uuid():
    return str(uuid.uuid4())


def generate_unique_id():
    rand_bytes = [random.randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0], rand_bytes[1], rand_bytes[2])


def incProcess(state, data):
    if "bri_inc" in data:
        state["bri"] += data["bri_inc"]
        if state["bri"] > 254:
            state["bri"] = 254
        elif state["bri"] < 1:
            state["bri"] = 1
        del data["bri_inc"]
        data["bri"] = state["bri"]
    elif "ct_inc" in data:
        state["ct"] += data["ct_inc"]
        if state["ct"] > 500:
            state["ct"] = 500
        elif state["ct"] < 153:
            state["ct"] = 153
        del data["ct_inc"]
        data["ct"] = state["ct"]
    elif "hue_inc" in data:
        state["hue"] += data["hue_inc"]
        if state["hue"] > 65535:
            state["hue"] -= 65535
        elif state["hue"] < 0:
            state["hue"] += 65535
        del data["hue_inc"]
        data["hue"] = state["hue"]
    elif "sat_inc" in data:
        state["sat"] += data["sat_inc"]
        if state["sat"] > 254:
            state["sat"] = 254
        elif state["sat"] < 1:
            state["sat"] = 1
        del data["sat_inc"]
        data["sat"] = state["sat"]

    return data


class BehaviorInstance():
    def __init__(self, data):
        self.id_v2 = data["id"] if "id" in data else genV2Uuid()
        self.id_v1 = self.id_v2 # used for config save
        self.name = data["metadata"]["name"]
        self.configuration = data["configuration"]
        self.enabled = data["enabled"] if "enabled" in data else False
        self.script_id = data["script_id"] if "script_id" in data else ""

    def getV2Api(self):
        result = {"configuration": self.configuration,
          "dependees": [],
          "enabled": self.enabled,
          "id": self.id_v2,
          "id_v1": "",
          "last_error": "",
          "metadata": {
            "name": self.name,
            "type": "InstanceMetadata"
          },
          "migrated_from": "",
          "script_id": self.script_id,
          "status": "running",
          "type": "behavior_instance"
        }

        for resource in self.configuration["where"]:
            result["dependees"].append({"level": "critical",
              "target": {
                "rid": resource[list(resource.keys())[0]]["rid"],
                "rtype": resource[list(resource.keys())[0]]["rtype"],
                "type": "ResourceIdentifier"
              },
              "type": "ResourceDependee"
            })

        return result

    def update_attr(self, newdata):
        for key, value in newdata.items():
            if key == "metadata" and "name" in value:
                self.name = value["name"]
                continue
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)

    def save(self):
        result = {"id": self.id_v2, "metadata": {"name": self.name}, "configuration": self.configuration, "enabled": self.enabled,
                  "script_id": self.script_id}
        return result


class ApiUser():
    def __init__(self, username, name, client_key, create_date=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), last_use_date=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")):
        self.username = username
        self.name = name
        self.client_key = client_key
        self.create_date = create_date
        self.last_use_date = last_use_date

    def getV1Api(self):
        return {"name": self.name, "create date": self.create_date, "last use date": self.last_use_date}

    def save(self):
        return {"name": self.name, "client_key": self.client_key, "create_date": self.create_date, "last_use_date": self.last_use_date}


class Light():
    def __init__(self, data):
        self.name = data["name"]
        self.modelid = data["modelid"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.uniqueid = data["uniqueid"] if "uniqueid" in data else generate_unique_id()
        self.state = data["state"] if "state" in data else lightTypes[self.modelid]["state"].copy()
        self.protocol = data["protocol"] if "protocol" in data else "dummy"
        self.config = data["config"] if "config" in data else lightTypes[self.modelid]["config"].copy()
        self.protocol_cfg = data["protocol_cfg"] if "protocol_cfg" in data else {}
        self.streaming = False

    def __del__(self):
        logging.info(self.name + " light was destroyed.")

    def update_attr(self, newdata):
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)

    def getV1Api(self):
        result = lightTypes[self.modelid]["v1_static"].copy()
        result["config"] = self.config
        result["state"] = self.state
        result["modelid"] = self.modelid
        result["name"] = self.name
        result["uniqueid"] = self.uniqueid
        return result

    def updateLightState(self, state):

        if "xy" in state:
            self.state["colormode"] = "xy"
        elif "ct" in state:
            self.state["colormode"] = "ct"
        elif "hue" in state or "sat" in state:
            self.state["colormode"] = "hs"

    def setV1State(self, state, rgb=None):
        if "lights" not in state:
            state = incProcess(self.state, state)
            self.updateLightState(state)
            self.state.update(state)

        for protocol in protocols:
            if "lights.protocols." + self.protocol == protocol.__name__:
                try:
                    if self.protocol in ["mi_box", "esphome", "tasmota"]:
                        protocol.set_light(self, state, rgb)
                    else:
                        protocol.set_light(self, state)
                    self.state["reachable"] = True
                except Exception as e:
                    self.state["reachable"] = False
                    logging.warning(self.name + " light error, details: %s", e)
                return

    def getDevice(self):
        result = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL,
                                       self.id_v2 + 'device')), "type": "device"}
        result["id_v1"] = self.id_v1
        result["metadata"] = {
            "archetype": lightTypes[self.modelid]["device"]["product_archetype"],
            "name": self.name
        }
        result["product_data"] = lightTypes[self.modelid]["device"]
        result["product_data"]["model_id"] = self.modelid

        result["services"] = [
            {
                "rid": self.id_v2,
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

    def getZigBee(self):
        result = {}
        result["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL,
                                      self.id_v2 + 'zigbee_connectivity'))
        result["id_v1"] = "/lights/" + self.id_v1
        result["mac_address"] = self.uniqueid[:23]
        result["status"] = "connected" if self.state["reachable"] else "connectivity_issue"
        result["type"] = "zigbee_connectivity"
        return result

    def getBridgeHome(self):
        return {
            "rid": self.id_v2,
            "rtype": "light"
        }

    def getV2Api(self):
        result = {}
        if "xy" in self.state:
            colorgamut = lightTypes[self.modelid]["v1_static"]["capabilities"]["control"]["colorgamut"]
            result = {
                "color": {
                    "gamut": {
                        "blue":  {"x": colorgamut[0][0], "y": colorgamut[0][1]},
                        "green": {"x": colorgamut[1][0], "y": colorgamut[1][1]},
                        "red":   {"x": colorgamut[2][0], "y": colorgamut[2][1]}
                    },
                    "gamut_type": lightTypes[self.modelid]["v1_static"]["capabilities"]["control"]["colorgamuttype"],
                    "xy": {
                        "x": self.state["xy"][0],
                        "y": self.state["xy"][1]
                    }
                }
            }
        if "ct" in self.state:
            result["color_temperature"] = {
                "mirek": self.state["ct"]
            }
        if "bri" in self.state:
            result["dimming"] = {
                "brightness": self.state["bri"] / 2.54
            }
        result["dynamics"] = {
            "status": "none",
            "status_values": ["none"]
            }
        result["id"] = self.id_v2
        result["id_v1"] = "/lights/" + self.id_v1
        result["metadata"] = {"name": self.name}
        if "archetype" in self.config:
            result["metadata"]["archetype"] = lightTypes[self.modelid]["device"]["product_archetype"]
        result["mode"] = "normal"
        result["on"] = {
            "on": self.state["on"]
        }
        result["type"] = "light"
        return result

    def getV2Entertainment(self):
        entertainmenUuid = str(uuid.uuid5(
            uuid.NAMESPACE_URL, self.id_v2 + 'entertainment'))
        result = {
            "id": entertainmenUuid,
            "id_v1": "/lights/" + self.id_v1,
            "proxy": lightTypes[self.modelid]["v1_static"]["capabilities"]["streaming"]["proxy"],
            "renderer": lightTypes[self.modelid]["v1_static"]["capabilities"]["streaming"]["renderer"]
        }
        result["segments"] = {
            "configurable": False,
            "max_segments": 1
        }
        if self.modelid in ["LCX001", "LCX002", "LCX003"]:
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
        else:
            result["segments"]["segments"] = [{
                "length": 1,
                "start": 0
            }]
        result["type"] = "entertainment"
        return result

    def getObjectPath(self):
        return {"resource": "lights", "id": self.id_v1}

    def save(self):
        result = {"id_v2": self.id_v2, "name": self.name, "modelid": self.modelid, "uniqueid": self.uniqueid,
                  "state": self.state, "config": self.config, "protocol": self.protocol, "protocol_cfg": self.protocol_cfg}
        return result


class Group():

    def __init__(self, data):
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.icon_class = data["class"] if "class" in data else "Other"
        self.lights = []
        self.action = {"on": False, "bri": 100, "hue": 0, "sat": 254, "effect": "none", "xy": [
            0.0, 0.0], "ct": 153, "alert": "none", "colormode": "xy"}
        self.sensors = []
        self.type = data["type"] if "type" in data else "LightGroup"
        self.locations = weakref.WeakKeyDictionary()
        self.stream = {"proxymode": "auto",
                       "proxynode": "/bridge", "active": False, "owner": None}
        self.state = {"all_on": False, "any_on": False}
        self.dxState = {"all_on": None, "any_on": None}

    def __del__(self):
        logging.info(self.name + " group was destroyed.")

    def add_light(self, light):
        self.lights.append(weakref.ref(light))

    def add_sensor(self, sensor):
        self.sensors.append(weakref.ref(sensor))

    def update_attr(self, newdata):
        if "class" in newdata:
            newdata["icon_class"] = newdata.pop("class")
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)

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

    def setV1Action(self, state, scene=None):
        lightsState = {}
        if scene != None:
            sceneStates = list(scene.lightstates.items())
            for light, state in sceneStates:
                lightsState[light.id_v1] = state

        else:
            state = incProcess(self.action, state)
            for light in self.lights:
                lightsState[light().id_v1] = state
            if "xy" in state:
                self.action["colormode"] = "xy"
            elif "ct" in state:
                self.action["colormode"] = "ct"
            elif "hue" in state or "sat" in state:
                self.action["colormode"] = "hs"

            if "on" in state:
                self.state["any_on"] = state["on"]
                self.state["all_on"] = state["on"]
            self.action.update(state)

        queueState = {}
        for light in self.lights:
            if light() and light().id_v1 in lightsState:  # apply only if the light belong to this group
                light().state.update(lightsState[light().id_v1])
                light().updateLightState(lightsState[light().id_v1])
                if light().protocol in ["native_multi", "mqtt"]:
                    if light().protocol_cfg["ip"] not in queueState:
                        queueState[light().protocol_cfg["ip"]] = {
                            "object": light(), "lights": {}}
                    if light().protocol == "native_multi":
                        queueState[light().protocol_cfg["ip"]]["lights"][light().protocol_cfg["light_nr"]] = lightsState[light().id_v1]
                    elif light().protocol == "mqtt":
                        queueState[light().protocol_cfg["ip"]]["lights"][light().protocol_cfg["command_topic"]] = lightsState[light().id_v1]
                else:
                    light().setV1State(lightsState[light().id_v1])
        for device, state in queueState.items():
            state["object"].setV1State(state)

        self.state = self.update_state()

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
        if self.id_v1 == "0":
            result["presence"] = {
                "state": {"presence": None, "presence_all": None, "lastupdated": "none"}}
            result["lightlevel"] = {"state": {"dark": None, "dark_all": None, "daylight": None, "daylight_any": None,
                                              "lightlevel": None, "lightlevel_min": None, "lightlevel_max": None, "lastupdated": "none"}}
        else:
            result["class"] = self.icon_class
        result["action"] = self.action

        if self.type == "Entertainment":
            result["locations"] = {}
            locations = list(self.locations.items())
            for light, location in locations:
                if light.id_v1 in lights:
                    result["locations"][light.id_v1] = location
            result["stream"] = self.stream
        return result

    def getV2Room(self):
        result = {"grouped_services": [], "services": []}
        result["grouped_services"].append({
            "rid": self.id_v2,
            "rtype": "grouped_light"

        })
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

        result["type"] = "room"
        return result

    def getV2Zone(self):
        result = {"grouped_services": [], "services": []}
        result["grouped_services"].append({
            "rid": self.id_v2,
            "rtype": "grouped_light"

        })
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

        result["type"] = "zone"
        return result

    def getV2GroupedLight(self):
        result = {}
        result["id"] = self.id_v2
        result["id_v1"] = "/groups/" + self.id_v1
        result["on"] = {"on": self.update_state()["any_on"]}
        result["type"] = "grouped_light"
        return result

    def getV2EntertainmentConfig(self):

        gradienStripPositions = [[-0.4000000059604645, 0.800000011920929, -0.4000000059604645],
                                 [-0.4000000059604645, 0.800000011920929, 0.0],
                                 [-0.4000000059604645, 0.800000011920929,
                                     0.4000000059604645],
                                 [0.0, 0.800000011920929, 0.4000000059604645],
                                 [0.4000000059604645, 0.800000011920929,
                                     0.4000000059604645],
                                 [0.4000000059604645, 0.800000011920929, 0.0],
                                 [0.4000000059604645, 0.800000011920929, -0.4000000059604645]]

        result = {
            "channels": [],
            "configuration_type": "screen",
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'entertainment_configuration')),
            "id_v1": "/groups/" + self.id_v1,
            "locations": {
                "service_locations": []
            },
            "name": self.name,
            "status": "active" if self.stream["active"] else "inactive",
            "stream_proxy": {
                "mode": "auto",
                "node": {
                    "rid": "57a9ebc9-406d-4a29-a4ff-42acee9e9be9",
                    "rtype": "entertainment"
                }
            },
            "type": "entertainment_configuration"

        }
        channel_id = 0
        for light in self.lights:
            if light():
                loops = 1
                entertainmentUuid = str(uuid.uuid5(
                    uuid.NAMESPACE_URL, light().id_v2 + 'entertainment'))
                gradientStrip = False
                if light().modelid in ["LCX001", "LCX002", "LCX003"]:
                    loops = 7
                    gradientStrip = True
                for x in range(loops):
                    result["channels"].append({
                        "channel_id": channel_id,
                        "members": [
                            {
                                "index": x,
                                "service": {
                                    "rid": entertainmentUuid,
                                    "rtype": "entertainment"
                                }
                            }
                        ],
                        "position": {
                            "x": gradienStripPositions[x][0] if gradientStrip else self.locations[light()][0],
                            "y": gradienStripPositions[x][1] if gradientStrip else self.locations[light()][1],
                            "z": gradienStripPositions[x][2] if gradientStrip else self.locations[light()][2]
                        }
                    })
                    result["locations"]["service_locations"].append({
                        "position": {
                            "x": gradienStripPositions[x][0] if gradientStrip else self.locations[light()][0],
                            "y": gradienStripPositions[x][1] if gradientStrip else self.locations[light()][1],
                            "z": gradienStripPositions[x][2] if gradientStrip else self.locations[light()][2]
                        },
                        "service": {
                            "rid": entertainmentUuid,
                            "rtype": "entertainment"
                        }

                    })
                channel_id += 1

        return result

    def getObjectPath(self):
        return {"resource": "groups", "id": self.id_v1}

    def save(self):
        result = {"id_v2": self.id_v2, "name": self.name, "class": self.icon_class,
                  "lights": [], "action": self.action, "type": self.type}
        for light in self.lights:
            if light():
                result["lights"].append(light().id_v1)
        if self.type == "Entertainment":
            result["locations"] = {}
            locations = list(self.locations.items())
            for light, location in locations:
                if light.id_v1 in result["lights"]:
                    result["locations"][light.id_v1] = location
        return result


class Scene():

    def __init__(self, data):
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.owner = data["owner"]
        self.appdata = data["appdata"] if "appdata" in data else {}
        self.type = data["type"] if "type" in data else "LightScene"
        self.picture = data["picture"] if "picture" in data else ""
        self.image = data["image"] if "image" in data else None
        self.recycle = data["recycle"] if "recycle" in data else False
        self.lastupdated = data["lastupdated"] if "lastupdated" in data else datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        self.lightstates = weakref.WeakKeyDictionary()
        self.group = data["group"] if "group" in data else None
        self.lights = data["lights"] if "lights" in data else []
        if "group" in data:
            self.storelightstate()
            self.lights = self.group().lights

    def __del__(self):
        logging.info(self.name + " scene was destroyed.")

    def add_light(self, light):
        self.lights.append(light)

    def activate(self, data):
        queueState = {}
        for light, state in self.lightstates.items():
            light.state.update(state)
            light.updateLightState(state)
            if len(data) > 0:
                state["transitiontime"] = 0
                if "seconds" in data:
                    state["transitiontime"] += data["seconds"] * 10
                if "minutes" in data:
                    state["transitiontime"] += data["minutes"] * 600
                if "recall" in data and "duration" in data["recall"]:
                    state["transitiontime"] = int(data["recall"]["duration"] / 100)
            if light.protocol in ["native_multi", "mqtt"]:
                if light.protocol_cfg["ip"] not in queueState:
                    queueState[light.protocol_cfg["ip"]] = {
                        "object": light, "lights": {}}
                if light.protocol == "native_multi":
                    queueState[light.protocol_cfg["ip"]]["lights"][light.protocol_cfg["light_nr"]] = state
                elif light.protocol == "mqtt":
                    queueState[light.protocol_cfg["ip"]]["lights"][light.protocol_cfg["command_topic"]] = state
            else:
                light.setV1State(state)
        for device, state in queueState.items():
            state["object"].setV1State(state)

    def getV1Api(self):
        result = {}
        result["name"] = self.name
        result["type"] = self.type
        result["lights"] = []
        result["lightstates"] = {}
        if self.type == "LightScene":
            for light in self.lights:
                if light():
                    result["lights"].append(light().id_v1)
        elif self.type == "GroupScene":
            result["group"] = self.group().id_v1
            for light in self.group().lights:
                if light():
                    result["lights"].append(light().id_v1)

        lightstates = list(self.lightstates.items())
        for light, state in lightstates:
            if light.id_v1 in result["lights"]:
                result["lightstates"][light.id_v1] = state
        result["owner"] = self.owner.username
        result["recycle"] = self.recycle
        # must be fuction to check the presece in rules or schedules
        result["locked"] = True
        result["appdata"] = self.appdata
        if self.image != None:
            result["image"] = self.image
        result["picture"] = self.picture
        result["lastupdated"] = self.lastupdated
        return result

    def getV2Api(self):
        result = {"actions": []}
        lightstates = list(self.lightstates.items())

        for light, state in lightstates:
            v2State = {}
            if "on" in state:
                v2State["on"] = {"on": state["on"]}
            if "bri" in state:
                v2State["dimming"] = {
                    "brightness": state["bri"] / 2.54}
            if "xy" in state:
                v2State["color"] = {"xy": {"x": state["xy"][0], "y": state["xy"][1]}}
            if "ct" in state:
                v2State["color_temperature"] = {
                    "mirek": state["ct"]}

            result["actions"].append(
                {
                    "action": v2State,
                    "target": {
                        "rid": light.id_v2,
                        "rtype": "light",
                    },
                }
            )

        if self.type == "GroupScene":
            if self.group():
                result["group"] = {
                    "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.group().id_v2 + 'room')),
                    "rtype": "room"
                }
        result["metadata"] = {}
        if self.image != None:
            result["metadata"]["image"] = {"rid": self.image,
                "rtype": "public_image"}
        result["metadata"]["name"] = self.name
        result["id"] = self.id_v2
        result["id_v1"] = "/scenes/" + self.id_v1
        result["type"] = "scene"
        return result

    def storelightstate(self):
        lights = []
        if self.type == "GroupScene":
            for light in self.group().lights:
                if light():
                    lights.append(light)
        else:
            for light in self.lightstates.keys():
                if light():
                    lights.append(light)
        for light in lights:
            state = {}
            if "colormode" in light().state:
                if light().state["colormode"] == "xy":
                    state["xy"] = light().state["xy"]
                elif light().state["colormode"] == "ct":
                    state["ct"] = light().state["ct"]
                elif light().state["colormode"] == "hs":
                    state["hue"] = light().state["hue"]
                    state["sat"] = light().state["sat"]
            state["on"] = light().state["on"]
            state["bri"] = light().state["bri"]
            self.lightstates[light()] = state

    def update_attr(self, newdata):
        self.lastupdated = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        if "storelightstate" in newdata and newdata["storelightstate"]:
            self.storelightstate()
            return
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)

    def getObjectPath(self):
        return {"resource": "scenes", "id": self.id_v1}

    def save(self):
        result = {"id_v2": self.id_v2, "name": self.name, "appdata": self.appdata, "owner": self.owner.username, "type": self.type, "picture": self.picture,
                  "image": self.image, "recycle": self.recycle, "lastupdated": self.lastupdated, "lights": [], "lightstates": {}}
        for light in self.lights:
            if light():
                result["lights"].append(light().id_v1)
        lightstates = list(self.lightstates.items())
        for light,state in lightstates:
            result["lightstates"][light.id_v1] = state
        if self.type == "GroupScene":
            result["group"] = self.group().id_v1
        return result


class Rule():
    def __init__(self, data):
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.actions = data["actions"] if "actions" in data else []
        self.conditions = data["conditions"] if "conditions" in data else []
        self.owner = data["owner"]
        self.status = data["status"] if "status" in data else "enabled"
        self.recycle = data["recycle"] if "recycle" in data else False
        self.created = data["created"] if "created" in data else datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        self.lasttriggered = data["lasttriggered"] if "lasttriggered" in data else "none"
        self.timestriggered = data["timestriggered"] if "timestriggered" in data else 0

    def __del__(self):
        logging.info(self.name + " rule was destroyed.")

    def add_actions(self, action):
        self.actions.append(action)

    def add_conditions(self, condition):
        self.condition.append(condition)

    def getObjectPath(self):
        return {"resource": "rules", "id": self.id_v1}

    def getV1Api(self):
        result = {}
        result["name"] = self.name
        result["owner"] = self.owner.username
        result["created"] = self.created
        result["lasttriggered"] = self.lasttriggered
        result["timestriggered"] = self.timestriggered
        result["status"] = self.status
        result["recycle"] = self.recycle
        result["conditions"] = self.conditions
        result["actions"] = self.actions
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
        return self.getV1Api()



class ResourceLink():
    def __init__(self, data):
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.classid = data["classid"]
        self.description = data["description"] if "description" in data else ""
        self.links = data["links"] if "links" in data else []
        self.owner = data["owner"]
        self.recycle = data["recycle"] if "recycle" in data else False

    def __del__(self):
        logging.info(self.name + " ResourceLink was destroyed.")

    def add_link(self, link):
        self.links.append("/" + link.getObjectPath()["resource"] + "/" + link.getObjectPath()["id"])

    def getObjectPath(self):
        return {"resource": "resourcelinks", "id": self.id_v1}

    def getV1Api(self):
        result = {}
        result["name"] = self.name
        result["description"] = self.description
        result["type"] = "Link"
        result["classid"] = self.classid
        result["owner"] = self.owner.username
        result["recycle"] = self.recycle
        result["links"] = self.links
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
        return self.getV1Api()


class Schedule():
    def __init__(self, data):
        self.name = data["name"] if "name" in data else "schedule " + \
            data["id_v1"]
        self.id_v1 = data["id_v1"]
        self.description = data["description"] if "description" in data else "none"
        self.command = data["command"] if "command" in data else {}
        self.localtime = data["localtime"] if "localtime" in data else None
        self.created = data["created"] if "created" in data else datetime.utcnow(
        ).strftime("%Y-%m-%dT%H:%M:%S")
        self.status = data["status"] if "status" in data else "disabled"
        self.autodelete = data["autodelete"] if "autodelete" in data else None
        starttime = None
        if data["localtime"].startswith("PT") or data["localtime"].startswith("R"):
            starttime = self.created
        self.starttime = data["starttime"] if "starttime" in data else starttime
        self.recycle = data["recycle"] if "recycle" in data else False

    def __del__(self):
        logging.info(self.name + " schedule was destroyed.")

    def getV1Api(self):
        result = {}
        result["name"] = self.name
        result["description"] = self.description
        result["command"] = self.command
        if self.localtime != None:
            result["localtime"] = self.localtime
            result["time"] = self.localtime
        result["created"] = self.created
        result["status"] = self.status
        if not self.localtime.startswith("W"):
            result["autodelete"] = self.autodelete
        if self.starttime != None:
            result["starttime"] = self.starttime
        result["recycle"] = self.recycle
        return result


    def update_attr(self, newdata):
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)
            if key == "status" and value == "enabled":
                logging.debug("enable timer " + self.name)
                self.starttime = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

    def getObjectPath(self):
        return {"resource": "schedules", "id": self.id_v1}

    def save(self):
        return self.getV1Api()


class Sensor():
    def __init__(self, data):
        if data["modelid"] in sensorTypes:
            if "manufacturername" not in data:
                data["manufacturername"] = sensorTypes[data["modelid"]][data["type"]]["static"]["manufacturername"]
            if "config" not in data:
                data["config"] = sensorTypes[data["modelid"]][data["type"]]["config"].copy()
            if "state" not in data:
                data["state"] = sensorTypes[data["modelid"]][data["type"]]["state"].copy()
            if "swversion" not in data:
                data["swversion"] = sensorTypes[data["modelid"]][data["type"]]["static"]["swversion"]
        if "config" not in data:
            data["config"] = {}
        if "reachable" not in data["config"]:
            data["config"]["reachable"] = True
        if "on" not in data["config"]:
            data["config"]["on"] = True
        if "state" not in data:
            data["state"] = {}
        if "lastupdated" not in  data["state"]:
            data["state"]["lastupdated"] = "none"
        self.name = data["name"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.config = data["config"]
        self.modelid = data["modelid"]
        self.manufacturername = data["manufacturername"] if "manufacturername" in data else "Philips"
        self.protocol = data["protocol"] if "protocol" in data else "none"
        self.protocol_cfg = data["protocol_cfg"] if "protocol_cfg" in data else {}
        self.type = data["type"]
        self.state = data["state"]
        dxstate = {}
        for state in data["state"].keys():
            dxstate[state] =  datetime.now()
        self.dxState = dxstate
        self.swversion = data["swversion"] if "swversion" in data else None
        self.recycle = data["recycle"] if "recycle" in data else False
        self.uniqueid = data["uniqueid"] if "uniqueid" in data else None

    def __del__(self):
        logging.info(self.name + " sensor was destroyed.")

    def setV1State(self, state):
        self.state.update(state)

    def getBridgeHome(self):
        if self.modelid == "SML001":
            if self.type == "ZLLPresence":
                rtype = "motion"
            elif self.type == "ZLLLightLevel":
                rtype = "temperature"
            elif self.type == "ZLLTemperature":
                rtype = "light_level"
            return {
                "rid": self.id_v2,
                "rtype": rtype
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
            result = {"id": str(uuid.uuid5(
                uuid.NAMESPACE_URL, self.id_v2 + 'device')), "type": "device"}
            result["metadata"] = {
                "archetype": "unknown_archetype",
                "name": self.name
            }
            result["product_data"] = {
                "certified": True,
                "manufacturer_name": "Signify Netherlands B.V.",
                "model_id": "SML001",
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
                    "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'battery')),
                    "rtype": "battery"
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
                }
            ]
        return result

    def getZigBee(self):
        result = None
        if self.modelid == "SML001" and self.type == "ZLLPresence":
            result = {}
            result["id"] = str(uuid.uuid5(
                uuid.NAMESPACE_URL, self.id_v2 + 'zigbee_connectivity'))
            result["id_v1"] = "/sensors/" + self.id_v1
            result["mac_address"] = self.uniqueid[:23]
            result["status"] = "connected"
            result["type"] = "zigbee_connectivity"
        return result

    def update_attr(self, newdata):
        if self.id_v1 == "1" and "config" in newdata: # manage daylight sensor
            if "long" in newdata["config"] and "lat" in newdata["config"]:
                self.config["configured"] = True
                self.protocol_cfg = {"long": float(newdata["config"]["long"][:-1]), "lat": float(newdata["config"]["lat"][:-1])}
                return
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
        result["id_v1"] = self.id_v1
        result["id_v2"] = self.id_v2
        result["state"] = self.state
        result["config"] = self.config
        result["type"] = self.type
        result["modelid"] = self.modelid
        result["manufacturername"] = self.manufacturername
        result["uniqueid"] = self.uniqueid
        result["swversion"] = self.swversion
        result["protocol"] = self.protocol
        result["protocol_cfg"] = self.protocol_cfg
        return result
