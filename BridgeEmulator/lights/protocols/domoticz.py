import json
import requests
import logManager

logging = logManager.logger.get_logger(__name__)

def set_light(light, data):
    url = "http://" + light.protocol_cfg["ip"] + "/json.htm?type=command&idx=" + light.protocol_cfg["light_id"]
    if "on" in data and not "bri" in data and not "ct" in data and not "xy" in data:
        for key, value in data.items():
            url += "&param=switchlight"
            if key == "on":
                if value:
                    url += "&switchcmd=On"
                else:
                    url += "&switchcmd=Off"
    else:
        url += "&param=setcolbrightnessvalue"
        color_data = {}

        old_light_state = light.state
        colormode = old_light_state["colormode"]
        ct = old_light_state["ct"]
        bri = old_light_state["bri"]
        xy = old_light_state["xy"]

        if "bri" in data:
            bri = data["bri"]
        if "ct" in data:
            ct = data["ct"]
        if "xy" in data:
            xy = data["xy"]
        bri = int(bri)

        color_data["m"] = 1 #0: invalid, 1: white, 2: color temp, 3: rgb, 4: custom
        if colormode == "ct":
            color_data["m"] = 2
            ct01 = (ct - 153) / (500 - 153) #map color temperature from 153-500 to 0-1
            ct255 = ct01 * 255 #map color temperature from 0-1 to 0-255
            color_data["t"] = ct255
        elif colormode == "xy":
            color_data["m"] = 3
            if rgb:
                (color_data["r"], color_data["g"], color_data["b"]) = rgbBrightness(rgb, bri)
            else:
                (color_data["r"], color_data["g"], color_data["b"]) = convert_xy(xy[0], xy[1], bri)
        url += "&color="+json.dumps(color_data)
        url += "&brightness=" + str(round(float(bri)/255*100))

    urlObj = {}
    urlObj["url"] = url
    requests.put(url, timeout=3)


def get_light_state(light):
    light_data = requests.get("http://" + light.protocol_cfg["ip"] + "/json.htm?type=devices&rid=" + light.protocol_cfg["light_id"]).json()
    state = {}
    if light_data["result"][0]["Status"] == "Off":
         state["on"] = False
    else:
         state["on"] = True
    state["bri"] = str(round(float(light_data["result"][0]["Level"])/100*255))
    return state

def discover():
    pass
