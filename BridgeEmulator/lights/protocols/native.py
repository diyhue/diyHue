import json
import requests
import configManager

bridgeConfig = configManager.bridgeConfig.yaml_config
newLights = configManager.runtimeConfig.newLights

def set_light(address, light, data):
    url = "http://" + address[light]["ip"] + "/set?light=" + str(address[light]["light_nr"])
    method = 'GET'
    for key, value in data.items():
        if key == "xy":
            url += "&x=" + str(value[0]) + "&y=" + str(value[1])
        else:
            url += "&" + key + "=" + str(value)
    requests.get(url, timeout=3)

def get_light_state(address, light):
    state = requests.get("http://"+address["ip"]+"/get?light=" + str(address["light_nr"]), timeout=3)
    return json.loads(state.text)


def discover():
    return
