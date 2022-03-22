import json
import logManager
import requests

logging = logManager.logger.get_logger(__name__)

def set_light(light, data):
    url = "http://" + light.protocol_cfg["ip"] + "/api/" + light.protocol_cfg["hueUser"] + "/lights/" + light.protocol_cfg["id"] + "/state"
    payload = {}
    payload.update(data)
    color = {}
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
                    detectedLights.append({"protocol": "hue", "name": light["name"], "modelid": modelid, "protocol_cfg": {"ip": credentials["ip"], "hueUser": credentials["hueUser"], "modelid": light["modelid"], "id": id, "uniqueid": light["uniqueid"]}})
        except Exception as e:
            logging.info("Error connecting to Hue Bridge: %s", e)
