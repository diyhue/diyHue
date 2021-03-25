import json
import logging
import requests

def set_light(light, data):
    state = requests.put("http://"+light.protocol_cfg["ip"]+"/state", json=data, timeout=3)
    return state.text

def get_light_state(light):
    state = requests.get("http://"+config["ip"]+"/state", timeout=3)
    return json.loads(state.text)
