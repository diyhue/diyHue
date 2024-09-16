import uuid
import logManager
import random

logging = logManager.logger.get_logger(__name__)

eventstream = []
def StreamEvent(message):
    eventstream.append(message)

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
            if "on" in state and state["on"] == True:
                group.state["any_on"] = True

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
                    queueState[light().protocol_cfg["ip"]] = {
                        "object": light(), "lights": {}}
                if light().protocol == "native_multi":
                    queueState[light().protocol_cfg["ip"]]["lights"][light(
                    ).protocol_cfg["light_nr"]] = lightsState[light().id_v1]
                elif light().protocol == "mqtt":
                    queueState[light().protocol_cfg["ip"]]["lights"][light(
                    ).protocol_cfg["command_topic"]] = lightsState[light().id_v1]
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
