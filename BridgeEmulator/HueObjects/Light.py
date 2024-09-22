import uuid
import logManager
from lights.light_types import lightTypes, archetype
from lights.protocols import protocols
from HueObjects import genV2Uuid, incProcess, v1StateToV2, generate_unique_id, v2StateToV1, StreamEvent, Device
from datetime import datetime, timezone
from copy import deepcopy
from time import sleep

logging = logManager.logger.get_logger(__name__)

class Light():
    def __init__(self, data):
        self.name = data["name"]
        self.modelid = data["modelid"]
        self.id_v1 = data["id_v1"]
        self.id_v2 = data["id_v2"] if "id_v2" in data else genV2Uuid()
        self.uniqueid = data["uniqueid"] if "uniqueid" in data else generate_unique_id(
        )
        self.state = data["state"] if "state" in data else deepcopy(
            lightTypes[self.modelid]["state"])
        self.protocol = data["protocol"] if "protocol" in data else "dummy"
        self.config = data["config"] if "config" in data else deepcopy(
            lightTypes[self.modelid]["config"])
        self.protocol_cfg = data["protocol_cfg"] if "protocol_cfg" in data else {
        }
        self.streaming = False
        self.dynamics = deepcopy(lightTypes[self.modelid]["dynamics"])
        self.effect = "no_effect"
        self.function = data["function"] if "function" in data else "mixed"

        # light
        streamMessage = {"creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [self.getV2Api()],
                         "id": str(uuid.uuid4()),
                         "type": "add"
                         }
        StreamEvent(streamMessage)


    def __del__(self):
        ## light ##
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"id": self.id_v2, "type": "light"}],
                         "id": str(uuid.uuid4()),
                         "type": "delete"
                         }
        streamMessage["id_v1"] = "/lights/" + self.id_v1
        StreamEvent(streamMessage)

        logging.info(self.name + " light was destroyed.")

    def update_attr(self, newdata):
        for key, value in newdata.items():
            updateAttribute = getattr(self, key)
            if isinstance(updateAttribute, dict):
                updateAttribute.update(value)
                setattr(self, key, updateAttribute)
            else:
                setattr(self, key, value)
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [Device.Device.getDevice(self)],
                         "id": str(uuid.uuid4()),
                         "type": "update"
                         }
        StreamEvent(streamMessage)

    def getV1Api(self):
        result = lightTypes[self.modelid]["v1_static"]
        result["config"] = self.config
        result["state"] = {"on": self.state["on"]}
        if "bri" in self.state and self.modelid not in ["LOM001", "LOM004", "LOM010"]:
            result["state"]["bri"] = int(self.state["bri"]) if self.state["bri"] is not None else 1
        if "ct" in self.state and self.modelid not in ["LOM001", "LOM004", "LOM010", "LTW001"]:
            result["state"]["ct"] = self.state["ct"]
            result["state"]["colormode"] = self.state["colormode"]
        if "xy" in self.state and self.modelid not in ["LOM001", "LOM004", "LOM010", "LTW001", "LWB010"]:
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
                if key in self.config:
                    if key == "archetype":
                        self.config[key] = value.replace("_","")
                    else:
                        self.config[key] = value
                if key == "name":
                    self.name = value
                if key == "function":
                    self.function = value
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
        if "metadata" in state:
            if "archetype" in state["metadata"]:
                v1State["archetype"] = state["metadata"]["archetype"]
            if "name" in state["metadata"]:
                v1State["name"] = state["metadata"]["name"]
            if "function" in state["metadata"]:
                v1State["function"] = state["metadata"]["function"]
        self.setV1State(v1State, advertise=False)
        self.genStreamEvent(state)

    def genStreamEvent(self, v2State):
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"id": self.id_v2,"id_v1": "/lights/" + self.id_v1, "type": "light"}],
                         "id": str(uuid.uuid4()),
                         "type": "update"
                         }
        streamMessage["data"][0].update(v2State)
        streamMessage["data"][0].update({"service_id": self.protocol_cfg["light_nr"]-1 if "light_nr" in self.protocol_cfg else 0})
        streamMessage["data"][0].update({"owner": {"rid": Device.Device.getDevice(self)["id"], "rtype": "device"}})
        StreamEvent(streamMessage)
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [Device.Device.getDevice(self)],
                         "id": str(uuid.uuid4()),
                         "type": "update"
                         }
        StreamEvent(streamMessage)


    def getV2Api(self):
        result = {}
        result["alert"] = {"action_values": ["breathe"]}
        # gradient lights
        if self.modelid in ["LCX002", "915005987201", "LCX004", "LCX006"]:
            result["effects"] = {
                "effect_values": [
                    "no_effect",
                    "candle",
                    "fire"
                ],
                "status": self.effect,
                "status_values": [
                    "no_effect",
                    "candle",
                    "fire"
                ]
            }
            result["gradient"] = {"points": self.state["gradient"]["points"],
                                  "points_capable": self.protocol_cfg["points_capable"]}

        # color lights only
        if self.modelid in ["LST002", "LCT001", "LCT015", "LCX002", "915005987201", "LCX004", "LCX006", "LCA005"]:
            colorgamut = lightTypes[self.modelid]["v1_static"]["capabilities"]["control"]["colorgamut"]
            result["color"] = {
                "gamut": {
                    "blue":  {"x": colorgamut[2][0], "y": colorgamut[2][1]},
                    "green": {"x": colorgamut[1][0], "y": colorgamut[1][1]},
                    "red":   {"x": colorgamut[0][0], "y": colorgamut[0][1]}
                },
                "gamut_type": lightTypes[self.modelid]["v1_static"]["capabilities"]["control"]["colorgamuttype"],
                "xy": {
                    "x": self.state["xy"][0],
                    "y": self.state["xy"][1]
                }
            }
        if "ct" in self.state:
            result["color_temperature"] = {
                "mirek": self.state["ct"] if self.state["colormode"] == "ct" else None,
                "mirek_schema": {
                    "mirek_maximum": 500,
                    "mirek_minimum": 153
                }
            }
            result["color_temperature"]["mirek_valid"] = True if self.state[
                "ct"] != None and self.state["ct"] < 500 and self.state["ct"] > 153 else False
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
        result["effects"] = {
            "effect_values": [
                "no_effect",
                "candle",
                "fire"
            ],
            "status": "no_effect",
            "status_values": [
                "no_effect",
                "candle",
                "fire"
            ]
        }
        result["identify"] = {}
        result["id"] = self.id_v2
        result["id_v1"] = "/lights/" + self.id_v1
        result["metadata"] = {"name": self.name, "function": self.function,
                              "archetype": archetype[self.config["archetype"]]}
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
        result["product_data"] = {"function": "mixed"}
        result["signaling"] = {"signal_values": [
            "no_signal",
            "on_off"]}
        result["powerup"] = {"preset": "last_on_state"}
        result["service_id"] = self.protocol_cfg["light_nr"]-1 if "light_nr" in self.protocol_cfg else 0
        result["type"] = "light"
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
        result = {"id_v2": self.id_v2, "name": self.name, "modelid": self.modelid, "uniqueid": self.uniqueid, "function": self.function,
                  "state": self.state, "config": self.config, "protocol": self.protocol, "protocol_cfg": self.protocol_cfg}
        return result
