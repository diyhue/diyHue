import json
import logManager
import requests
from functions.colors import convert_xy

logging = logManager.logger.get_logger(__name__)

def set_light(light, data):
    
    url = "http://" + light.protocol_cfg["ip"] + "/gateways/" + light.protocol_cfg["miID"] + "/" + light.protocol_cfg["miModes"] + "/" + str(light.protocol_cfg["miGroups"])
    payload={}
    for key, value in data.items():
        if key == "on":
            payload["status"] = value
        elif key == "bri":
            payload["brightness"] = value
        elif key == "ct":
            payload["color_temp"] = int(value / 1.6 + 153)
        elif key == "hue":
            payload["hue"] = value / 180
        elif key == "sat":
            payload["saturation"] = value * 100 / 255
        elif key == "xy":
            payload["color"] = {}
           # 
           # The following if is throwing an error, because rgb does not exist in data. I commented this, becaus I didn't know, if there are any requests with "rgb" when using options that I don't know. 
           # if rgb:
           #     payload["color"]["r"], payload["color"]["g"], payload["color"]["b"] = rgbBrightness(rgb, lights[light]["state"]["bri"])
           # else:
           # payload["color"]["r"], payload["color"]["g"], payload["color"]["b"] = convert_xy(value[0], value[1], lights[light]["state"]["bri"])
            payload["color"]["r"], payload["color"]["g"], payload["color"]["b"] = convert_xy(value[0], value[1], light.state["bri"])
    logging.debug(json.dumps(payload))
    requests.put(url, json=payload, timeout=3)

def get_light_state(light):
    r = requests.get("http://" + light.protocol_cfg["ip"] + "/gateways/" + light.protocol_cfg["miID"] + "/" + light.protocol_cfg["miModes"] + "/" + str(light.protocol_cfg["miGroups"]), timeout=3)
    light_data = json.loads(r.text)
    state ={}
    if light_data["state"] == "ON":
        state["on"] = True
    else:
        state["on"] = False
    if "brightness" in light_data:
        state["bri"] = light_data["brightness"]
    if "color_temp" in light_data:
        state["colormode"] = "ct"
        state["ct"] = int(light_data["color_temp"] * 1.6)
    elif "bulb_mode" in light_data and light_data["bulb_mode"] == "color":
        state["colormode"] = "hs"
        state["hue"] = light_data["hue"] * 180
        if (not "saturation" in light_data) and light.protocol_cfg["miModes"] == "rgbw":
            state["sat"] = 255
        else:
            state["sat"] = int(light_data["saturation"] * 2.54)
    return state

def discover():
    pass
