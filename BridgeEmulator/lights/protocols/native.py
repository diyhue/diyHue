import json
import requests

def set_light(light, data):
    url = "http://" + light.protocol_cfg["ip"] + "/set?light=" + str(light.protocol_cfg["light_nr"])
    method = 'GET'
    for key, value in data.items():
        if key == "xy":
            url += "&x=" + str(value[0]) + "&y=" + str(value[1])
        else:
            url += "&" + key + "=" + str(value)
    requests.get(url, timeout=3)

def get_light_state(light):
    state = requests.get("http://"+light.protocol_cfg["ip"]+"/get?light=" + str(address["light_nr"]), timeout=3)
    return json.loads(state.text)


def discover():
    return
