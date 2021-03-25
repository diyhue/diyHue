import json
import configManager
import requests

bridgeConfig = configManager.bridgeConfig.yaml_config
newLights = configManager.runtimeConfig.newLights

def set_light(address, light, data):
    url = "http://" + address[light]["ip"] + "/api/" + address[light]["username"] + "/lights/" + address[light]["light_id"] + "/state"
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

def get_light_state(address, light):
    state = requests.get("http://" + address[light]["ip"] + "/api/" + address[light]["username"] + "/lights/" + address[light]["light_id"]), timeout=3)
    return json.loads(state.text)["state"]

def discover():
