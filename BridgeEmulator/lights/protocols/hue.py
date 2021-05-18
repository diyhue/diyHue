import json
import requests

def set_light(light, data):
    url = "http://" + light.protocol_cfg["ip"] + "/api/" + light.protocol_cfg["username"] + "/lights/" + light.protocol_cfg["light_id"] + "/state"
    payload = {}
    payload.update(data)
    color = {}
    if "xy" in payload:
        color["xy"] = payload["xy"]
        del(payload["xy"])
    elif "ct" in payload:
        color["ct"] = payload["ct"]
        del(payload["ct"])
    elif "hue" in payload:
        color["hue"] = payload["hue"]
        del(payload["hue"])
    elif "sat" in payload:
        color["sat"] = payload["sat"]
        del(payload["sat"])
    if len(payload) != 0:
        requests.put(url, json=payload, timeout=3)
    if len(color) != 0:
        equests.put(url, json=color, timeout=3)

def get_light_state(light):
    state = requests.get("http://" + light.protocol_cfg["ip"] + "/api/" + light.protocol_cfg["username"] + "/lights/" + light.protocol_cfg["light_id"]), timeout=3)
    return json.loads(state.text)["state"]

def discover(detectedLights):
    pass
