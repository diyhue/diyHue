import json
import logging
import requests


def set_light(address, light, data):
    state = requests.put("http://"+address["ip"]+"/state", json=data, timeout=3)
    return state.text

def get_light_state(address, light):
    state = requests.get("http://"+address["ip"]+"/state", timeout=3)
    return json.loads(state.text)
