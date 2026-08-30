import json
import logManager
import requests
import warnings
from urllib3.exceptions import InsecureRequestWarning

logging = logManager.logger.get_logger(__name__)


def _request(method, config, path, **kwargs):
    scheme = config.get("scheme", "http")
    url = scheme + "://" + config["ip"] + path
    kwargs.setdefault("timeout", 3)

    if scheme == "https":
        kwargs["verify"] = False
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InsecureRequestWarning)
            return requests.request(method, url, **kwargs)

    return requests.request(method, url, **kwargs)


def link_bridge(ip):
    payload = {
        "devicetype": "diyhue#bridge",
        "generateclientkey": True,
    }
    last_error = None

    for scheme in ("https", "http"):
        try:
            response = _request(
                "post",
                {"ip": ip, "scheme": scheme},
                "/api",
                json=payload,
            )

            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and result:
                    return result, scheme
        except (requests.RequestException, ValueError, TypeError) as error:
            last_error = error

    raise ConnectionError("Unable to connect to Hue Bridge") from last_error


def set_light(light, data):
    path = "/api/" + light.protocol_cfg["hueUser"] + "/lights/" + light.protocol_cfg["id"] + "/state"
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
        _request("put", light.protocol_cfg, path, json=payload)
    if len(color) != 0:
        _request("put", light.protocol_cfg, path, json=color)


def get_light_state(light):
    response = _request(
        "get",
        light.protocol_cfg,
        "/api/" + light.protocol_cfg["hueUser"] + "/lights/" + light.protocol_cfg["id"],
    )
    return response.json()["state"]


def discover(detectedLights, credentials):
    if "hueUser" in credentials and len(credentials["hueUser"]) > 32:
        logging.debug("hue: <discover> invoked!")
        try:
            response = _request(
                "get",
                credentials,
                "/api/" + credentials["hueUser"] + "/lights",
            )
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
                    elif light["type"] == "Color light":
                        modelid = "LLC010"
                    detectedLights.append({
                        "protocol": "hue",
                        "name": light["name"],
                        "modelid": modelid,
                        "protocol_cfg": {
                            "ip": credentials["ip"],
                            "scheme": credentials.get("scheme", "http"),
                            "hueUser": credentials["hueUser"],
                            "modelid": light["modelid"],
                            "id": id,
                            "uniqueid": light["uniqueid"],
                        }
                    })
        except Exception as e:
            logging.info("Error connecting to Hue Bridge: %s", e)
