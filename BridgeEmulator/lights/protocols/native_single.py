import logManager
import requests

logging = logManager.logger.get_logger(__name__)

def set_light(light, data):
    state = requests.put("http://"+light.protocol_cfg["ip"]+"/state", json=data, timeout=3)
    return state.text

def get_light_state(light):
    state = requests.get("http://"+light.protocol_cfg["ip"]+"/state", timeout=3)
    return state.json()
