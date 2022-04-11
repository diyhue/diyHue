import json
import requests
import logManager
from functions.colors import convert_xy, rgbBrightness

logging = logManager.logger.get_logger(__name__)

def set_light(light, data, rgb = None):
    url = "http://" + light.protocol_cfg["ip"] + "/json.htm?type=command&idx=" + light.protocol_cfg["domoticzID"]

    if "on" in data:
        onUrl = url + "&param=switchlight&switchcmd="
        if data["on"]:
            onUrl += "On"
        else:
            onUrl += "Off"
        logging.debug(onUrl)
        requests.put(onUrl, timeout=3)
    if "ct" in data or "xy" in data or "bri" in data:
        url += "&param=setcolbrightnessvalue"
        color_data = {}
        if "ct" in data or ("colormode" in light.state and light.state["colormode"] == "ct"):
            ct = data["ct"] if "ct" in data else light.state["ct"]
            color_data["m"] = 2
            ct01 = (ct - 153) / (500 - 153) #map color temperature from 153-500 to 0-1
            ct255 = ct01 * 255 #map color temperature from 0-1 to 0-255
            color_data["t"] = ct255
        if "xy" in data or ("colormode" in light.state and light.state["colormode"] == "xy"):
            xy = data["xy"] if "xy" in data else light.state["xy"]
            bri = data["bri"] if "bri" in data else light.state["bri"]
            color_data["m"] = 3
            if rgb:
                (color_data["r"], color_data["g"], color_data["b"]) = rgbBrightness(rgb, bri)
            else:
                (color_data["r"], color_data["g"], color_data["b"]) = convert_xy(xy[0], xy[1], bri)

            url += "&color="+json.dumps(color_data)
        if "bri" in data:
            url += "&brightness=" + str(round(float(data["bri"])/255*100))
        logging.debug(url)
        requests.put(url, timeout=3)


def get_light_state(light):
    light_data = requests.get("http://" + light.protocol_cfg["ip"] + "/json.htm?type=devices&rid=" + light.protocol_cfg["domoticzID"]).json()
    state = {}
    if light_data["result"][0]["Status"] == "Off":
         state["on"] = False
    else:
         state["on"] = True
    state["bri"] = int(round(float(light_data["result"][0]["Level"])/100*255))
    return state

def discover():
    pass
