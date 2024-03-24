from lights.light_types import archetype, lightTypes
from lights.protocols import protocols
from sensors.sensor_types import sensorTypes
from threading import Thread
from datetime import datetime
from pprint import pprint
from copy import deepcopy
from time import sleep
import uuid
import logManager
import random
import weakref

logging = logManager.logger.get_logger(__name__)

eventstream = []

def v1StateToV2(v1State):
    v2State = {}
    if "on" in v1State:
        v2State["on"] = {"on": v1State["on"]}
    if "bri" in v1State:
        v2State["dimming"] = {"brightness": round(v1State["bri"] / 2.54, 2)}
    if "ct" in v1State:
        v2State["color_temperature"] = {"mirek": v1State["ct"], "color_temperature_delta": {}}
    if "xy" in v1State:
        v2State["color"] = {
            "xy": {"x": v1State["xy"][0], "y": v1State["xy"][1]}}
    return v2State


def v2StateToV1(v2State):
    v1State = {}
    if "dimming" in v2State:
        v1State["bri"] = int(v2State["dimming"]["brightness"] * 2.54)
    if "on" in v2State:
        v1State["on"] = v2State["on"]["on"]
    if "color_temperature" in v2State:
        v1State["ct"] = v2State["color_temperature"]["mirek"]
    if "color" in v2State:
        if "xy" in v2State["color"]:
            v1State["xy"] = [v2State["color"]["xy"]
                             ["x"], v2State["color"]["xy"]["y"]]
    if "gradient" in v2State:
        v1State["gradient"] = v2State["gradient"]
    if "transitiontime" in v2State:  # to be replaced once api will be public
        v1State["transitiontime"] = v2State["transitiontime"]
    return v1State

def genV2Uuid():
    return str(uuid.uuid4())

def generate_unique_id():
    rand_bytes = [random.randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0], rand_bytes[1], rand_bytes[2])


def setGroupAction(group, state, scene=None):
    lightsState = {}
    if scene != None:
        sceneStates = list(scene.lightstates.items())
        for light, state in sceneStates:
            lightsState[light.id_v1] = state

    else:
        state = incProcess(group.action, state)
        for light in group.lights:
            if light():
                lightsState[light().id_v1] = state
        if "xy" in state:
            group.action["colormode"] = "xy"
        elif "ct" in state:
            group.action["colormode"] = "ct"
        elif "hue" in state or "sat" in state:
            group.action["colormode"] = "hs"

        if "on" in state:
            group.state["any_on"] = state["on"]
            group.state["all_on"] = state["on"]
        group.action.update(state)

    queueState = {}
    for light in group.lights:
        if light() and light().id_v1 in lightsState:  # apply only if the light belong to this group
            for key, value in lightsState[light().id_v1].items():
                if key in light().state:
                    light().state[key] = value
            light().updateLightState(lightsState[light().id_v1])
            # apply max and min brightness limis
            if "bri" in lightsState[light().id_v1]:
                if "min_bri" in light().protocol_cfg and light().protocol_cfg["min_bri"] > lightsState[light().id_v1]["bri"]:
                    lightsState[light().id_v1]["bri"] = light().protocol_cfg["min_bri"]
                if "max_bri" in light().protocol_cfg and light().protocol_cfg["max_bri"] < lightsState[light().id_v1]["bri"]:
                    lightsState[light().id_v1]["bri"] = light().protocol_cfg["max_bri"]
                if  light().protocol == "mqtt" and not light().state["on"]:
                    continue
            # end limits
            if light().protocol in ["native_multi", "mqtt"]:
                if light().protocol_cfg["ip"] not in queueState:
                    queueState[light().protocol_cfg["ip"]] = {"object": light(), "lights": {}}
                if light().protocol == "native_multi":
                    queueState[light().protocol_cfg["ip"]]["lights"][light().protocol_cfg["light_nr"]] = lightsState[light().id_v1]
                elif light().protocol == "mqtt":
                    queueState[light().protocol_cfg["ip"]]["lights"][light().protocol_cfg["command_topic"]] = lightsState[light().id_v1]
            else:
                light().setV1State(lightsState[light().id_v1])
    for device, state in queueState.items():
        state["object"].setV1State(state)

    group.state = group.update_state()


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
        self.id_v1 = self.id_v2  # used for config save
        self.name = data["metadata"]["name"] if "name" in data["metadata"] else None
        self.configuration = data["configuration"]
        self.enabled = data["enabled"] if "enabled" in data else False
        self.active = data["active"] if "active" in data else False
        self.script_id = data["script_id"] if "script_id" in data else ""

        streamMessage = {
            "creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getV2Api()],
            "id": str(uuid.uuid4()),
            "type": "add"
        }
        eventstream.append(streamMessage)

    def __del__(self):
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.id_v2, "type": "behavior_instance"}],
            "id": str(uuid.uuid4()),
            "type": "delete"
        }
        eventstream.append(streamMessage)
        logging.info(self.name + " behaviour instance was destroyed.")

    def getV2Api(self):
        result = {"configuration": self.configuration,
                  "dependees": [],
                  "enabled": self.enabled,
                  "active": self.active,
                  "id": self.id_v2,
                  "last_error": "",
                  "metadata": {
                      "name": "noname"
                  },
                  "script_id": self.script_id,
                  "status": "running" if self.enabled else "disabled",
                  "type": "behavior_instance"
                  }

        if self.name != None:
            result["metadata"]["name"] = self.name

        for resource in self.configuration["where"]:
            result["dependees"].append({"level": "critical",
                                        "target": {
                                            "rid": resource[list(resource.keys())[0]]["rid"],
                                            "rtype": resource[list(resource.keys())[0]]["rtype"]
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
        streamMessage = {
            "creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getV2Api()],
            "id": str(uuid.uuid4()),
            "type": "update"
        }
        eventstream.append(streamMessage)

    def save(self):
        result = {
            "id": self.id_v2, "metadata": {"name": self.name}, "configuration": self.configuration,
            "enabled": self.enabled, "active": self.active, "script_id": self.script_id
        }
        if self.name != None:
            result["metadata"] = {"name": self.name}

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
        self.state = data["state"] if "state" in data else deepcopy(lightTypes[self.modelid]["state"])
        self.protocol = data["protocol"] if "protocol" in data else "dummy"
        self.config = data["config"] if "config" in data else deepcopy(lightTypes[self.modelid]["config"])
        self.protocol_cfg = data["protocol_cfg"] if "protocol_cfg" in data else {}
        self.streaming = False
        self.dynamics = deepcopy(lightTypes[self.modelid]["dynamics"])
        self.effect = "no_effect"

        # entertainment
        streamMessage = {
            "creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'entertainment')), "type": "entertainent"}],
            "id": str(uuid.uuid4()),
            "type": "add"
        }
        streamMessage["id_v1"] = "/lights/" + self.id_v1
        streamMessage["data"][0].update(self.getV2Entertainment())
        eventstream.append(streamMessage)

        # zigbee_connectivity
        streamMessage = {
            "creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getZigBee()],
            "id": str(uuid.uuid4()),
            "type": "add"
        }
        eventstream.append(streamMessage)

        # light
        streamMessage = {
            "creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getV2Api()],
            "id": str(uuid.uuid4()),
            "type": "add"
        }
        eventstream.append(streamMessage)

        # device
        streamMessage = {
            "creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getDevice()],
            "id": str(uuid.uuid4()),
            "type": "add"
        }
        streamMessage["data"][0].update(self.getDevice())
        eventstream.append(streamMessage)

    def __del__(self):
        ## light ##
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.id_v2, "type": "light"}],
            "id": str(uuid.uuid4()),
            "type": "delete"
        }
        streamMessage["id_v1"] = "/lights/" + self.id_v1
        eventstream.append(streamMessage)

        ## device ##
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.getDevice()["id"], "type": "device"}],
            "id": str(uuid.uuid4()),
            "type": "delete"
        }
        streamMessage["id_v1"] = "/lights/" + self.id_v1
        eventstream.append(streamMessage)

        # Zigbee Connectivity
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.getZigBee()["id"], "type": "zigbee_connectivity"}],
            "id": str(uuid.uuid4()),
            "type": "delete"
        }
        streamMessage["id_v1"] = "/lights/" + self.id_v1
        eventstream.append(streamMessage)

        # Entertainment
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.getV2Entertainment()["id"], "type": "entertainment"}],
            "id": str(uuid.uuid4()),
            "type": "delete"
        }
        streamMessage["id_v1"] = "/lights/" + self.id_v1
        eventstream.append(streamMessage)

        logging.info(self.name + " light was destroyed.")

    def update_attr(self, newdata):
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)
        streamMessage = {
            "creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getDevice()],
            "id": str(uuid.uuid4()),
            "type": "update"
        }
        eventstream.append(streamMessage)

    def getV1Api(self):
        result = lightTypes[self.modelid]["v1_static"]
        result["config"] = self.config
        result["state"] = { "on": self.state["on"] }

        device = lightTypes[self.modelid]
        if ('bri' in self.state) and ('bri' in device['state']):
            result["state"]["bri"] = int(self.state["bri"]) if self.state["bri"] is not None else 1
        if ('ct' in self.state) and ('ct' in device['state']):
            result["state"]["ct"] = self.state["ct"]
            result["state"]["colormode"] = self.state["colormode"]
        if ('xy' in self.state) and ('xy' in device['state']):
            result["state"]["xy"] = self.state["xy"]
            result["state"]["hue"] = self.state["hue"]
            result["state"]["sat"] = self.state["sat"]
            result["state"]["colormode"] = self.state["colormode"]
        result["state"]["alert"] = self.state["alert"]
        if "mode" in self.state:
            result["state"]["mode"] = self.state["mode"]
        result["state"]["reachable"] = self.state["reachable"]
        result["modelid"] = self.modelid
        result["name"] = self.name
        result["uniqueid"] = self.uniqueid
        return result

    def updateLightState(self, state):
        if "xy" in state and "xy" in self.state:
            self.state["colormode"] = "xy"
        elif "ct" in state and "ct" in self.state:
            self.state["colormode"] = "ct"
        elif ("hue" in state or "sat" in state) and "hue" in self.state:
            self.state["colormode"] = "hs"

    def setV1State(self, state, advertise=True):
        if "lights" not in state:
            state = incProcess(self.state, state)
            self.updateLightState(state)
            for key, value in state.items():
                if key in self.state:
                    self.state[key] = value
            if "bri" in state:
                if "min_bri" in self.protocol_cfg and self.protocol_cfg["min_bri"] > state["bri"]:
                    state["bri"] = self.protocol_cfg["min_bri"]
                if "max_bri" in self.protocol_cfg and self.protocol_cfg["max_bri"] < state["bri"]:
                    state["bri"] = self.protocol_cfg["max_bri"]

        for protocol in protocols:
            if "lights.protocols." + self.protocol == protocol.__name__:
                try:
                    protocol.set_light(self, state)
                    self.state["reachable"] = True
                except Exception as e:
                    self.state["reachable"] = False
                    logging.warning(self.name + " light error, details: %s", e)
                return
        if advertise:
            v2State = v1StateToV2(state)
            self.genStreamEvent(v2State)

    def setV2State(self, state):
        v1State = v2StateToV1(state)
        if "effects" in state:
            v1State["effect"] = state["effects"]["effect"]
            self.effect = v1State["effect"]
        if "dynamics" in state and "speed" in state["dynamics"]:
            self.dynamics["speed"] = state["dynamics"]["speed"]
        self.setV1State(v1State, advertise=False)
        self.genStreamEvent(state)

    def genStreamEvent(self, v2State):
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.id_v2, "type": "light"}],
            "id": str(uuid.uuid4()),
            "type": "update"
        }
        streamMessage["id_v1"] = "/lights/" + self.id_v1
        streamMessage["data"][0].update(v2State)
        streamMessage["data"][0].update(
            {"owner": {"rid": self.getDevice()["id"], "rtype": "device"}})
        eventstream.append(streamMessage)

    def getDevice(self):
        result = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'device'))}
        result["id_v1"] = "/lights/" + self.id_v1
        result["identify"] = {}
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
        result["type"] = "device"
        return result

    def getZigBee(self):
        result = {}
        result["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL,self.id_v2 + 'zigbee_connectivity'))
        result["id_v1"] = "/lights/" + self.id_v1
        result["mac_address"] = self.uniqueid[:23]
        result["owner"] = {
            "rid": self.getDevice()["id"],
            "rtype": "device"
        }
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
        result["alert"] = {"action_values": ["breathe"]}

        # gradient lights
        if self.modelid in ["LCX002", "915005987201", "LCX004", "LCX006"]:
            result["gradient"] = {
                "points": self.state["gradient"]["points"],
                "points_capable": self.protocol_cfg["points_capable"]
            }

        # color lights only
        capabilities = lightTypes[self.modelid]["v1_static"]["capabilities"]
        if ("colorgamut" in capabilities["control"]) and ("colorgamuttype" in capabilities["control"]):
            colorgamut = capabilities["control"]["colorgamut"]
            result["color"] = {
                "gamut": {
                    "blue":  {"x": colorgamut[2][0], "y": colorgamut[2][1]},
                    "green": {"x": colorgamut[1][0], "y": colorgamut[1][1]},
                    "red":   {"x": colorgamut[0][0], "y": colorgamut[0][1]}
                },
                "gamut_type": capabilities["control"]["colorgamuttype"],
                "xy": {
                    "x": self.state["xy"][0],
                    "y": self.state["xy"][1]
                }
            }
            result["effects"] = {
                "effect_values": [ "no_effect", "candle", "fire" ],
                "status": "no_effect",
                "status_values": [ "no_effect", "candle", "fire" ]
            }

        if ("ct" in self.state) and ("ct" in capabilities["control"]):
            ct_value = self.state["ct"]
            ct = capabilities["control"]["ct"]
            result["color_temperature"] = {
                "mirek": ct_value if self.state["colormode"] == "ct" else None,
                "mirek_schema": {
                    "mirek_maximum": ct["max"],
                    "mirek_minimum": ct["min"]
                },
                "mirek_valid": (ct_value is not None) and (ct["min"] <= ct_value <= ct["max"])
            }
            result["color_temperature_delta"] = {}

        if "bri" in self.state:
            bri_value = self.state["bri"]
            if bri_value is None or bri_value == "null":
                bri_value = 1
            result["dimming"] = {
                "brightness": round(float(bri_value) / 2.54, 2),
                "min_dim_level": 0.1  # Adjust this value as needed
            }
            result["dimming_delta"] = {}

        result["dynamics"] = self.dynamics
        result["identify"] = {}
        result["id"] = self.id_v2
        result["id_v1"] = "/lights/" + self.id_v1
        result["metadata"] = {
            "name": self.name, "function": "mixed",
            "archetype": archetype[self.config["archetype"]]
        }
        result["mode"] = "normal"
        if "mode" in self.state and self.state["mode"] == "streaming":
            result["mode"] = "streaming"
        result["on"] = {
            "on": self.state["on"]
        }
        result["owner"] = {
            "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'device')),
            "rtype": "device"
        }
        result["product_data"] = { "function": "mixed" }
        result["signaling"] = { "signal_values": [ "no_signal", "on_off" ] }
        result["type"] = "light"
        return result

    def getV2Entertainment(self):
        entertainmenUuid = str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'entertainment'))
        result = {
            "equalizer": True,
            "id": entertainmenUuid,
            "id_v1": "/lights/" + self.id_v1,
            "proxy": lightTypes[self.modelid]["v1_static"]["capabilities"]["streaming"]["proxy"],
            "renderer": lightTypes[self.modelid]["v1_static"]["capabilities"]["streaming"]["renderer"],
            "renderer_reference": {
                "rid": self.id_v2,
                "rtype": "light"
            }
        }
        result["owner"] = { "rid": self.getDevice()["id"], "rtype": "device" }
        result["segments"] = { "configurable": False }
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

    def getObjectPath(self):
        return {"resource": "lights", "id": self.id_v1}

    def dynamicScenePlay(self, palette, index):
        logging.debug("Start Dynamic scene play for " + self.name)
        if "dynamic_palette" in self.dynamics["status_values"]:
            self.dynamics["status"] = "dynamic_palette"
        while self.dynamics["status"] == "dynamic_palette":
            transition = int(30 / self.dynamics["speed"])
            logging.debug("using transistiontime " + str(transition))
            if self.modelid in ["LCT001", "LCT015", "LST002", "LCX002", "915005987201", "LCX004", "LCX006", "LCA005"]:
                if index == len(palette["color"]):
                    index = 0
                points = []
                if self.modelid in ["LCX002", "915005987201", "LCX004", "LCX006"]:
                    # for gradient lights
                    gradientIndex = index
                    for x in range(self.protocol_cfg["points_capable"]):
                        points.append(palette["color"][gradientIndex])
                        gradientIndex += 1
                        if gradientIndex == len(palette["color"]):
                            gradientIndex = 0
                    self.setV2State(
                        {"gradient": {"points": points}, "transitiontime": transition})
                else:
                    lightState = palette["color"][index]
                    # based on youtube videos, the transition is slow
                    lightState["transitiontime"] = transition
                    self.setV2State(lightState)
            elif self.modelid == "LTW001":
                if index == len(palette["color_temperature"]):
                    index = 0
                lightState = palette["color_temperature"][index]
                lightState["transitiontime"] = transition
                self.setV2State(lightState)
            else:
                if index == len(palette["dimming"]):
                    index = 0
                lightState = palette["dimming"][index]
                lightState["transitiontime"] = transition
                self.setV2State(lightState)
            sleep(transition / 10)
            index += 1
            logging.debug("Step forward dynamic scene " + self.name)
        logging.debug("Dynamic Scene " + self.name + " stopped.")

    def save(self):
        result = {"id_v2": self.id_v2, "name": self.name, "modelid": self.modelid, "uniqueid": self.uniqueid,
                  "state": self.state, "config": self.config, "protocol": self.protocol, "protocol_cfg": self.protocol_cfg}
        return result


class EntertainmentConfiguration():
    def __init__(self, data):
        self.name = data["name"] if "name" in data else "Group " + data["id_v1"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.configuration_type = data["configuration_type"] if "configuration_type" in data else "3dspace"
        self.lights = []
        self.action = {
            "on": False, "bri": 100, "hue": 0, "sat": 254, "effect": "none",
            "xy": [0.0, 0.0], "ct": 153, "alert": "none", "colormode": "xy"
        }
        self.sensors = []
        self.type = data["type"] if "type" in data else "Entertainment"
        self.configuration_type = data["configuration_type"] if "configuration_type" in data else "screen"
        self.locations = weakref.WeakKeyDictionary()
        self.stream = {"proxymode": "auto", "proxynode": "/bridge", "active": False, "owner": None}
        self.state = {"all_on": False, "any_on": False}
        self.dxState = {"all_on": None, "any_on": None}

        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getV2Api()],
            "id": str(uuid.uuid4()),
            "type": "add"
        }
        eventstream.append(streamMessage)

    def __del__(self):
        # Groupper light
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.id_v2, "type": "grouped_light"}],
            "id": str(uuid.uuid4()),
            "type": "delete"
        }
        streamMessage["id_v1"] = "/groups/" + self.id_v1
        eventstream.append(streamMessage)

        ### Entertainment area ###
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.getV2Api()["id"], "type": "entertainment_configuration"}],
            "id": str(uuid.uuid4()),
            "type": "delete"
        }
        streamMessage["id_v1"] = "/groups/" + self.id_v1
        eventstream.append(streamMessage)
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
        streamMessage = {
            "creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getV2Api()],
            "id": str(uuid.uuid4()),
            "type": "update"
        }
        eventstream.append(streamMessage)

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
        gradienStripPositions = [
            {"x": -0.4000000059604645, "y": 0.800000011920929, "z": -0.4000000059604645},
            {"x": -0.4000000059604645, "y": 0.800000011920929, "z": 0.0},
            {"x": -0.4000000059604645, "y": 0.800000011920929, "z": 0.4000000059604645},
            {"x": 0.0, "y": 0.800000011920929, "z": 0.4000000059604645},
            {"x": 0.4000000059604645, "y": 0.800000011920929, "z": 0.4000000059604645},
            {"x": 0.4000000059604645, "y": 0.800000011920929, "z": 0.0},
            {"x": 0.4000000059604645, "y": 0.800000011920929, "z": -0.4000000059604645}
        ]

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
                result["light_services"].append({"rtype": "light", "rid": light().id_v2})
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
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.id_v2, "type": "grouped_light"}],
            "id": str(uuid.uuid4()),
            "type": "update"
        }
        streamMessage["id_v1"] = "/groups/" + self.id_v1
        streamMessage.update(v2State)
        eventstream.append(streamMessage)

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


class GeofenceClient():
    def __init__(self, data):
        self.name = data.get('name', f'Geofence {data.get("id_v1")}')
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.is_at_home = data.get('is_at_home', False)

        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getV2GeofenceClient()],
            "id": str(uuid.uuid4()),
            "type": "add"
        }
        eventstream.append(streamMessage)

    def __del__(self):
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.id_v2, "type": "geofence_client"}],
            "id": str(uuid.uuid4()),
            "type": "delete"
        }
        eventstream.append(streamMessage)
        logging.info(self.name + " geofence client was destroyed.")

    def update_attr(self, newdata):
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)

        streamMessage = {
            "creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getV2GeofenceClient()],
            "id": str(uuid.uuid4()),
            "type": "update"
        }
        eventstream.append(streamMessage)

    def getV2GeofenceClient(self):
        return {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'geofence_client')),
            "name": self.name,
            "type": "geofence_client"
        }


class Group():

    def __init__(self, data):
        self.name = data["name"] if "name" in data else "Group " + \
            data["id_v1"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.icon_class = data["class"] if "class" in data else "Other"
        self.lights = []
        self.action = {"on": False, "bri": 100, "hue": 0, "sat": 254, "effect": "none", "xy": [
            0.0, 0.0], "ct": 153, "alert": "none", "colormode": "xy"}
        self.sensors = []
        self.type = data["type"] if "type" in data else "LightGroup"
        self.state = {"all_on": False, "any_on": False}
        self.dxState = {"all_on": None, "any_on": None}

        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getV2Room() if self.type == "Room" else self.getV2Zone()],
            "id": str(uuid.uuid4()),
            "type": "add"
        }
        eventstream.append(streamMessage)

    def groupZeroStream(self, rooms, lights):
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"children": [], "id": str(uuid.uuid5(uuid.NAMESPACE_URL, self.id_v2 + 'bridge_home')),  "id_v1":"/groups/0", "type": "bridge_home"}],
            "id": str(uuid.uuid4()),
            "type": "update"
        }
        for room in rooms:
            streamMessage["data"][0]["children"].append({"rid": room, "rtype": "room"})
        for light in lights:
            streamMessage["data"][0]["children"].append({"rid": light, "rtype": "light"})
        eventstream.append(streamMessage)

    def __del__(self):
        # Groupper light
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.id_v2,  "id_v1": "/groups/" + self.id_v1, "type": "grouped_light"}],
            "id": str(uuid.uuid4()),
            "type": "delete"
        }
        streamMessage["id_v1"] = "/groups/" + self.id_v1
        eventstream.append(streamMessage)

        ### room / zone ####
        elementId = self.getV2Room()["id"] if self.type == "Room" else self.getV2Zone()["id"]
        elementType = "room" if self.type == "Room" else "zone"
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": elementId,  "id_v1": "/groups/" + self.id_v1, "type": elementType}],
            "id": str(uuid.uuid4()),
            "type": "delete"
        }
        eventstream.append(streamMessage)
        logging.info(self.name + " group was destroyed.")

    def add_light(self, light):
        self.lights.append(weakref.ref(light))
        elementId = self.getV2Room()["id"] if self.type == "Room" else self.getV2Zone()["id"]
        elementType = "room" if self.type == "Room" else "zone"
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"alert": {"action_values": ["breathe"]}, "id": self.id_v2, "id_v1": "/groups/" + self.id_v1, "on":{"on": self.action["on"]}, "type": "grouped_light", }],
            "id": str(uuid.uuid4()),
            "type": "add"
        }
        eventstream.append(streamMessage)

        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"grouped_services": [{"rid": self.id_v2, "rtype": "grouped_light"}], "id": elementId, "id_v1": "/groups/" + self.id_v1, "type": elementType}],
            "id": str(uuid.uuid4()),
            "type": "update"
        }

        eventstream.append(streamMessage)
        groupChildrens = []
        groupServices = []
        for light in self.lights:
            if light():
                groupChildrens.append({"rid": light().getDevice()["id"], "rtype": "device"})
                groupServices.append({"rid": light().id_v2, "rtype": "light"})
        groupServices.append({"rid": self.id_v2, "rtype": "grouped_light"})

        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"children": groupChildrens, "id": elementId, "id_v1": "/groups/" + self.id_v1, "services": groupServices, "type": elementType}],
            "id": str(uuid.uuid4()),
            "type": "update"
        }
        eventstream.append(streamMessage)

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

        streamMessage = {
            "creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getV2Room() if self.type == "Room" else self.getV2Zone()],
            "owner": {
                "rid": self.getV2Room()["id"] if self.type == "Room" else self.getV2Zone()["id"],
                "rtype": "room" if self.type == "Room" else "zone"
            },
            "id": str(uuid.uuid4()),
            "type": "update"
        }
        eventstream.append(streamMessage)

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

    def setV2Action(self, state):
        v1State = v2StateToV1(state)
        setGroupAction(self, v1State)
        self.genStreamEvent(state)

    def setV1Action(self, state, scene=None):
        setGroupAction(self, state, scene)
        v2State = v1StateToV2(state)
        self.genStreamEvent(v2State)

    def genStreamEvent(self, v2State):
        for light in self.lights:
            if light():
                streamMessage = {
                    "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "data": [{"id": light().id_v2, "id_v1": "/lights/" + light().id_v1, "owner": {"rid": light().getDevice()["id"], "rtype":"device"}, "type": "light"}],
                    "id": str(uuid.uuid4()),
                    "type": "update"
                }
                streamMessage["data"][0].update(v2State)
                eventstream.append(streamMessage)
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.id_v2, "type": "grouped_light",
                "owner": {
                    "rid": self.getV2Room()["id"] if self.type == "Room" else self.getV2Zone()["id"],
                    "rtype": "room" if self.type == "Room" else "zone"
                }
            }],
            "id": str(uuid.uuid4()),
            "type": "update"
        }
        streamMessage["id_v1"] = "/groups/" + self.id_v1
        streamMessage["data"][0].update(v2State)
        eventstream.append(streamMessage)

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
                "state": {"presence": None, "presence_all": None, "lastupdated": "none"}
            }
            result["lightlevel"] = {
                "state": {"dark": None, "dark_all": None, "daylight": None, "daylight_any": None,
                "lightlevel": None, "lightlevel_min": None, "lightlevel_max": None, "lastupdated": "none"}
            }
        else:
            result["class"] = self.icon_class
        result["action"] = self.action
        return result

    def getV2Room(self):
        result = {"children": [], "grouped_services": [], "services": []}
        for light in self.lights:
            if light():
                result["children"].append({
                    "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, light().id_v2 + 'device')),
                    "rtype": "device"
                })

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

        result["services"].append({
            "rid": self.id_v2,
            "rtype": "grouped_light"
        })

        result["type"] = "room"
        return result

    def getV2Zone(self):
        result = {"children": [], "grouped_services": [], "services": []}
        for light in self.lights:
            if light():
                result["children"].append({
                    "rid": light().id_v2,
                    "rtype": "light"
                })

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
        result["dimming"] = {}
        result["dimming_delta"] = {}
        result["dynamics"] = {}
        result["id"] = self.id_v2
        result["id_v1"] = "/groups/" + self.id_v1
        result["on"] = {"on": self.update_state()["any_on"]}
        result["type"] = "grouped_light"
        return result

    def getObjectPath(self):
        return {"resource": "groups", "id": self.id_v1}

    def save(self):
        result = {
            "id_v2": self.id_v2, "name": self.name, "class": self.icon_class,
            "lights": [], "action": self.action, "type": self.type
        }
        for light in self.lights:
            if light():
                result["lights"].append(light().id_v1)
        return result


class Scene():

    DEFAULT_SPEED = 0.6269841194152832

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
        self.lastupdated = data["lastupdated"] if "lastupdated" in data else datetime.utcnow(
        ).strftime("%Y-%m-%dT%H:%M:%S")
        self.lightstates = weakref.WeakKeyDictionary()
        self.palette = data["palette"] if "palette" in data else {}
        self.speed = data["speed"] if "speed" in data else self.DEFAULT_SPEED
        self.group = data["group"] if "group" in data else None
        self.lights = data["lights"] if "lights" in data else []
        if "group" in data:
            self.storelightstate()
            self.lights = self.group().lights

        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [self.getV2Api()],
            "id": str(uuid.uuid4()),
            "type": "add"
        }
        streamMessage["data"][0].update(self.getV2Api())
        eventstream.append(streamMessage)

    def __del__(self):
        streamMessage = {
            "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": self.id_v2, "type": "scene"}],
            "id": str(uuid.uuid4()),
            "type": "delete"
        }
        streamMessage["id_v1"] = "/scenes/" + self.id_v1
        eventstream.append(streamMessage)
        logging.info(self.name + " scene was destroyed.")

    def add_light(self, light):
        self.lights.append(light)

    def activate(self, data):
        # activate dynamic scene
        if "recall" in data and data["recall"]["action"] == "dynamic_palette":
            lightIndex = 0
            for light in self.lights:
                if light():
                    light().dynamics["speed"] = self.speed
                    Thread(target=light().dynamicScenePlay, args=[
                           self.palette, lightIndex]).start()
                    lightIndex += 1

            return
        queueState = {}
        for light, state in self.lightstates.items():
            logging.debug(state)
            light.state.update(state)
            light.updateLightState(state)
            if light.dynamics["status"] == "dynamic_palette":
                light.dynamics["status"] = "none"
                logging.debug("Stop Dynamic scene play for " + light.name)
            if len(data) > 0:
                transitiontime = 0
                if "seconds" in data:
                    transitiontime += data["seconds"] * 10
                if "minutes" in data:
                    transitiontime += data["minutes"] * 600
                if transitiontime > 0:
                    state["transitiontime"] = transitiontime
                if "recall" in data and "duration" in data["recall"]:
                    state["transitiontime"] = int(data["recall"]["duration"] / 100)

            if light.protocol in ["native_multi", "mqtt"]:
                if light.protocol_cfg["ip"] not in queueState:
                    queueState[light.protocol_cfg["ip"]] = {
                        "object": light, "lights": {}}
                if light.protocol == "native_multi":
                    queueState[light.protocol_cfg["ip"]
                               ]["lights"][light.protocol_cfg["light_nr"]] = state
                elif light.protocol == "mqtt":
                    queueState[light.protocol_cfg["ip"]
                               ]["lights"][light.protocol_cfg["command_topic"]] = state
            else:
                logging.debug(state)
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
            if light.id_v1 in result["lights"] and "gradient" not in state:
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
                bri_value = state["bri"]
                if bri_value is None or bri_value == "null":
                    bri_value = 1
                v2State["dimming"] = {
                    "brightness": round(float(bri_value) / 2.54, 2)
                }
                v2State["dimming_delta"] = {}

            if "xy" in state:
                v2State["color"] = {
                    "xy": {"x": state["xy"][0], "y": state["xy"][1]}}
            if "ct" in state:
                v2State["color_temperature"] = {
                    "mirek": state["ct"]}
            result["actions"].append({
                "action": v2State,
                "target": {
                    "rid": light.id_v2,
                    "rtype": "light",
                }
            })

        if self.type == "GroupScene":
            if self.group():
                result["group"] = {
                    "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.group().id_v2 + self.group().type.lower())),
                    "rtype": self.group().type.lower()
                }
        result["metadata"] = {}
        if self.image != None:
            result["metadata"]["image"] = {"rid": self.image, "rtype": "public_image"}
        result["metadata"]["name"] = self.name
        result["id"] = self.id_v2
        result["id_v1"] = "/scenes/" + self.id_v1
        result["type"] = "scene"
        if self.palette:
            result["palette"] = self.palette
        result["speed"] = self.speed
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
            state["on"] = light().state["on"]
            if "colormode" in light().state:
                if light().state["colormode"] == "xy":
                    state["xy"] = light().state["xy"]
                elif light().state["colormode"] == "ct":
                    state["ct"] = light().state["ct"]
                elif light().state["colormode"] == "hs":
                    state["hue"] = light().state["hue"]
                    state["sat"] = light().state["sat"]
            if "bri" in light().state:
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
        if self.type == "GroupScene":
            if self.group():
                result["group"] = self.group().id_v1
            else:
                return False
        if self.palette != None:
            result["palette"] = self.palette
        result["speed"] = self.speed or self.DEFAULT_SPEED
        for light in self.lights:
            if light():
                result["lights"].append(light().id_v1)
        lightstates = list(self.lightstates.items())
        for light, state in lightstates:
            result["lightstates"][light.id_v1] = state

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
        self.created = data["created"] if "created" in data else datetime.utcnow(
        ).strftime("%Y-%m-%dT%H:%M:%S")
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
        self.links.append("/" + link.getObjectPath()
                          ["resource"] + "/" + link.getObjectPath()["id"])

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
        self.name = data["name"] if "name" in data else "schedule " + data["id_v1"]
        self.id_v1 = data["id_v1"]
        self.description = data["description"] if "description" in data else "none"
        self.command = data["command"] if "command" in data else {}
        self.localtime = data["localtime"] if "localtime" in data else None
        self.created = data["created"] if "created" in data else datetime.utcnow(
        ).strftime("%Y-%m-%dT%H:%M:%S")
        self.status = data["status"] if "status" in data else "disabled"
        self.autodelete = data["autodelete"] if "autodelete" in data else False
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
        self.protocol_cfg = data["protocol_cfg"] if "protocol_cfg" in data else {}
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
            streamMessage = {
                "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "data": [{"id": self.id_v2, "type": "device"}],
                "id": str(uuid.uuid4()),
                "type": "add"
            }
            streamMessage["data"][0].update(self.getDevice())
            eventstream.append(streamMessage)

    def __del__(self):
        if self.modelid in ["SML001", "RWL022"]:
            streamMessage = {
                "creationtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "data": [{"id": self.getDevice()["id"], "type": "device"}],
                "id": str(uuid.uuid4()),
                "type": "delete"
            }
            streamMessage["id_v1"] = "/sensors/" + self.id_v1
            eventstream.append(streamMessage)
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
        return result

    def getMotion(self):
        result = None
        if self.modelid == "SML001" and self.type == "ZLLPresence":
            result = {"enabled": self.config["on"],
                      "id": str(uuid.uuid5(
                          uuid.NAMESPACE_URL, self.id_v2 + 'motion')),
                      "id_v1": "/sensors/" + self.id_v1,
                      "motion": {
                "motion": True if self.state["presence"] else False,
                "motion_valid": True
            },
                "owner": {
                "rid": str(uuid.uuid5(
                    uuid.NAMESPACE_URL, self.id_v2 + 'device')),
                "rtype": "device"
            },
                "type": "motion"}
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
