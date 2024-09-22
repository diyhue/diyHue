import json
import logManager
import requests
from functions.colors import hsv_to_rgb, convert_rgb_xy

logging = logManager.logger.get_logger(__name__)

def set_light(light, data):
    url = "http://" + light.protocol_cfg["ip"] + "/api/" + light.protocol_cfg["hueUser"] + "/lights/" + light.protocol_cfg["id"] + "/state"
    payload = {}
    payload.update(data)
    color = {}
    if "strictusexy" in light.protocol_cfg and light.protocol_cfg["strictusexy"] and ("sat" in payload or "hue" in payload):
        if "sat" in payload and "hue" in payload:
            rgb = hsv_to_rgb(payload["hue"], payload["sat"], light.state["bri"])
            del(payload["sat"])
            del(payload["hue"])
        elif "hue" in payload:
            rgb = hsv_to_rgb(payload["hue"], light.state["sat"], light.state["bri"])
            del(payload["hue"])
        elif "sat" in payload:
            rgb = hsv_to_rgb(light.state["hue"], payload["sat"], light.state["bri"])
            del(payload["sat"])
        xy = convert_rgb_xy(rgb[0],rgb[1],rgb[2])
        color["colormode"] = 'xy'
        color["xy"] = [xy[0], xy[1]]
    if "xy" in payload:
        color["xy"] = payload["xy"]
        del(payload["xy"])
    elif "ct" in payload:
        color["ct"] = payload["ct"]
        del(payload["ct"])
    elif "hue" in payload:
        color["hue"] = payload["hue"]
        del(payload["hue"])
    elif "sat" in payload:
        color["sat"] = payload["sat"]
        del(payload["sat"])
    if len(payload) != 0:
        requests.put(url, json=payload, timeout=3)
    if len(color) != 0:
        requests.put(url, json=color, timeout=3)

def get_light_state(light):
    state = requests.get("http://" + light.protocol_cfg["ip"] + "/api/" + light.protocol_cfg["hueUser"] + "/lights/" + light.protocol_cfg["id"], timeout=3)
    return state.json()["state"]

def discover(detectedLights, credentials):
    if "hueUser" in credentials and len(credentials["hueUser"]) > 32:
        logging.debug("hue: <discover> invoked!")
        try:
            response = requests.get("http://" + credentials["ip"] + "/api/" + credentials["hueUser"] + "/lights", timeout=3)
            if response.status_code == 200:
                logging.debug(response.text)
                lights = json.loads(response.text)
                for id, light in lights.items():
                    modelid = "LCT015"
                    if light["type"] == "Dimmable light":
                        modelid = "LWB010"
                    elif light["type"] == "Color temperature light":
                        modelid = "LTW001"
                    elif light["type"] == "On/Off plug-in unit":
                        modelid = "LOM001"
                    detectedLights.append({"protocol": "hue", "name": light["name"], "modelid": modelid, "protocol_cfg": {"ip": credentials["ip"], "hueUser": credentials["hueUser"], "modelid": light["modelid"], "id": id, "uniqueid": light["uniqueid"], "strictusexy": False}})
        except Exception as e:
            logging.info("Error connecting to Hue Bridge: %s", e)
