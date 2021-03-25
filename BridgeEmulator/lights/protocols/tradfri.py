import json
import configManager
from subprocess import check_output
from functions.colors import convert_rgb_xy, hsv_to_rgb
bridgeConfig = configManager.bridgeConfig.yaml_config
newLights = configManager.runtimeConfig.newLights

def set_light(address, light, data, rgb = None):
    url = "coaps://" + address[light]["ip"] + ":5684/15001/" + str(address[light]["device_id"])
    for key, value in data.items():
        if key == "on":
            payload["5850"] = int(value)
        elif key == "transitiontime":
            payload["5712"] = value
        elif key == "bri":
            if value > 254:
                value = 254
            payload["5851"] = value
        elif key == "ct":
            if value < 270:
                payload["5706"] = "f5faf6"
            elif value < 385:
                payload["5706"] = "f1e0b5"
            else:
                payload["5706"] = "efd275"
        elif key == "xy":
            payload["5709"] = int(value[0] * 65535)
            payload["5710"] = int(value[1] * 65535)
    if "hue" in data or "sat" in data:
        if("hue" in data):
            hue = data["hue"]
        else:
            hue = lights[light]["state"]["hue"]
        if("sat" in data):
            sat = data["sat"]
        else:
            sat = lights[light]["state"]["sat"]
        if("bri" in data):
            bri = data["bri"]
        else:
            bri = lights[light]["state"]["bri"]
        rgbValue = hsv_to_rgb(hue, sat, bri)
        xyValue = convert_rgb_xy(rgbValue[0], rgbValue[1], rgbValue[2])
        payload["5709"] = int(xyValue[0] * 65535)
        payload["5710"] = int(xyValue[1] * 65535)
    if "5850" in payload and payload["5850"] == 0:
        payload.clear() #setting brightnes will turn on the ligh even if there was a request to power off
        payload["5850"] = 0
    elif "5850" in payload and "5851" in payload: #when setting brightness don't send also power on command
        del payload["5850"]

    if "5712" not in payload:
        payload["5712"] = 4 #If no transition add one, might also add check to prevent large transitiontimes
    check_output("./coap-client-linux -m put -u \"" + addresses[light]["identity"] + "\" -k \"" + addresses[light]["preshared_key"] + "\" -e '{ \"3311\": [" + json.dumps(payload) + "] }' \"" + url + "\"", shell=True)

def get_light_state(address, light):
    light_data = json.loads(check_output("./coap-client-linux -m get -u \"" + address[light]["identity"] + "\" -k \"" + address[light]["preshared_key"] + "\" \"coaps://" + address[light]["ip"] + ":5684/15001/" + str(address[light]["device_id"]) +"\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
    state = {}
    state["on"] = bool(light_data["3311"][0]["5850"])
    state["bri"] = light_data["3311"][0]["5851"]
    if "5706" in light_data["3311"][0]:
        if light_data["3311"][0]["5706"] == "f5faf6":
            state["ct"] = 170
        elif light_data["3311"][0]["5706"] == "f1e0b5":
            state["ct"] = 320
        elif light_data["3311"][0]["5706"] == "efd275":
            state["ct"] = 470
    else:
        state["ct"] = 470
    state["reachable"] = True

    return state

def discover():
    return
