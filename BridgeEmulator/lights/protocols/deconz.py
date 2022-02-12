import json
import logManager
import requests
from time import sleep
logging = logManager.logger.get_logger(__name__)

def set_light(light, data):
    url = "http://" + light.protocol_cfg["ip"] + "/api/" + light.protocol_cfg["deconzUser"] + "/lights/" + light.protocol_cfg["deconzId"] + "/state"
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
        sleep(0.7)
    if len(color) != 0:
        requests.put(url, json=color, timeout=3)

def get_light_state(light):
    state = requests.get("http://" + light.protocol_cfg["ip"] + "/api/" + light.protocol_cfg["deconzUser"] + "/lights/" + light.protocol_cfg["deconzId"], timeout=3)
    return state.json()["state"]

def discover(detectedLights, credentials):
    if "deconzUser" in credentials and credentials["deconzUser"] != "":
        logging.debug("deconz: <discover> invoked!")
        try:
            response = requests.get("http://" + credentials["deconzHost"] + ":" + str(credentials["deconzPort"]) + "/api/" + credentials["deconzUser"] + "/lights", timeout=3)
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
                    detectedLights.append({"protocol": "deconz", "name": light["name"], "modelid": modelid, "protocol_cfg": {"ip": credentials["deconzHost"] + ":" + str(credentials["deconzPort"]), "deconzUser": credentials["deconzUser"], "modelid": light["modelid"], "deconzId": id, "uniqueid": light["uniqueid"]}})
        except Exception as e:
            logging.info("Error connecting to Deconz: %s", e)
