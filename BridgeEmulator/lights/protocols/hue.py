from lights.light_types import lightTypes
import json
import logManager
import requests

logging = logManager.logger.get_logger(__name__)

def set_light(light, data):
    protocol_cfg = light.protocol_cfg
    url = "http://" + protocol_cfg["ip"] + "/api/" + protocol_cfg["hueUser"] + "/lights/" + protocol_cfg["id"] + "/state"
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
        response = requests.put(url, json=payload, timeout=3)
        logging.debug(response.text)
    if len(color) != 0:
        response = requests.put(url, json=color, timeout=3)
        logging.debug(response.text)

def get_light_state(light):
    protocol_cfg = light.protocol_cfg
    state = requests.get("http://" + protocol_cfg["ip"] + "/api/" + protocol_cfg["hueUser"] + "/lights/" + protocol_cfg["id"], timeout=3)
    return state.json()["state"]

def discover(detectedLights, credentials):
    if "hueUser" in credentials and len(credentials["hueUser"]) > 32:
        logging.debug("hue: <discover> invoked!")
        try:
            ip = credentials['ip']
            user = credentials['hueUser']
            response = requests.get("http://" + ip + "/api/" + user + "/lights", timeout=3)
            if response.status_code == 200:
                logging.debug(response.text)
                lights = json.loads(response.text)
                for id, light in lights.items():
                    if ('modelid' in light) and (light['modelid'] in lightTypes):
                        modelid = light['modelid']
 #                   elif ('productid' in light) : 
 #                       productid = light['productid'] --> Philips-LCG002-3-GU10ECLv2
                    elif light['type'] == 'Extended color light':
                        modelid = 'LCG002'
                    elif light['type'] == 'Color temperature light':
                        modelid = 'LTW001'
                    elif light['type'] == 'Dimmable light':
                        modelid = 'LWB010'
                    elif light['type'] == 'On/Off plug-in unit':
                        modelid = 'LOM001'
                    else:
                        modelid = 'LCT001'
                    detectedLights.append({
                        "protocol": "hue", "name": light["name"], "modelid": modelid,
                        "protocol_cfg": {"ip": ip, "hueUser": user, "modelid": light['modelid'], "id": id, "uniqueid": light["uniqueid"]}
                    })
        except Exception as e:
            logging.info("Error connecting to Hue Bridge: %s", e)
