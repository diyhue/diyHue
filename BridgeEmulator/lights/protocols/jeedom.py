import json
import configManager
import requests

bridgeConfig = configManager.bridgeConfig.yaml_config
newLights = configManager.runtimeConfig.newLights

def set_light(address, light, data):
    url = "http://" + address[light]["ip"] + "/core/api/jeeApi.php?apikey=" + address[light]["light_api"] + "&type=cmd&id="
    for key, value in data.items():
        if key == "on":
            if value:
                url += address[light]["light_on"]
            else:
                url += address[light]["light_off"]
        elif key == "bri":
            url += address[light]["light_slider"] + "&slider=" + str(round(float(value)/255*100)) # jeedom range from 0 to 100 (for zwave devices) instead of 0-255 of bridge
    requests.get(url, timeout=3)

def get_light_state(address, light):
    light_data = json.loads(sendRequest("http://" + addresses[light]["ip"] + "/core/api/jeeApi.php?apikey=" + addresses[light]["light_api"] + "&type=cmd&id=" + addresses[light]["light_id"], "GET", "{}"))
    state = {}
    if light_data == 0:
         state["on"] = False
    else:
         state["on"] = True
    state["bri"] = str(round(float(light_data)/100*255))
    return state

def discover():
