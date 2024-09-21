import uuid
import logManager
import weakref
from threading import Thread
from datetime import datetime, timezone
from HueObjects import genV2Uuid, StreamEvent

logging = logManager.logger.get_logger(__name__)

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
        self.lastupdated = data["lastupdated"] if "lastupdated" in data else datetime.now(timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%S")
        self.lightstates = weakref.WeakKeyDictionary()
        self.palette = data["palette"] if "palette" in data else {}
        self.speed = data["speed"] if "speed" in data else self.DEFAULT_SPEED
        self.group = data["group"] if "group" in data else None
        self.lights = data["lights"] if "lights" in data else []
        self.status = data["status"] if "status" in data else "inactive"
        if "group" in data:
            self.storelightstate()
            self.lights = self.group().lights
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [self.getV2Api()],
                         "id": str(uuid.uuid4()),
                         "type": "add"
                         }
        streamMessage["data"][0].update(self.getV2Api())
        StreamEvent(streamMessage)

    def __del__(self):
        streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "data": [{"id": self.id_v2, "type": "scene"}],
                         "id": str(uuid.uuid4()),
                         "type": "delete"
                         }
        streamMessage["id_v1"] = "/scenes/" + self.id_v1
        StreamEvent(streamMessage)
        logging.info(self.name + " scene was destroyed.")

    def add_light(self, light):
        self.lights.append(light)

    def activate(self, data):
        # activate dynamic scene
        if "recall" in data:
            if data["recall"]["action"] == "dynamic_palette":
                self.status = data["recall"]["action"]
                lightIndex = 0
                for light in self.lights:
                    if light():
                        light().dynamics["speed"] = self.speed
                        Thread(target=light().dynamicScenePlay, args=[
                            self.palette, lightIndex]).start()
                        lightIndex += 1
                return
            elif data["recall"]["action"] == "deactivate":
                self.status = "inactive"
                return

        queueState = {}
        self.status = data["recall"]["action"]
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
                    state["transitiontime"] = int(
                        data["recall"]["duration"] / 100)

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

        if self.type == "GroupScene":
            self.group().state["any_on"] = True

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
                #v2State["dimming_delta"] = {}

            if "xy" in state:
                v2State["color"] = {
                    "xy": {"x": state["xy"][0], "y": state["xy"][1]}}
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
                    "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, self.group().id_v2 + self.group().type.lower())),
                    "rtype": self.group().type.lower()
                }
        result["metadata"] = {}
        if self.image != None:
            result["metadata"]["image"] = {"rid": self.image,
                                           "rtype": "public_image"}
        result["metadata"]["name"] = self.name
        result["id"] = self.id_v2
        result["id_v1"] = "/scenes/" + self.id_v1
        result["type"] = "scene"
        if self.palette:
            result["palette"] = self.palette
        result["speed"] = self.speed
        result["auto_dynamic"] = False
        result["status"] = {"active": self.status}
        result["recall"] = {}
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
        self.lastupdated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
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
