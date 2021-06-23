import json
import logManager
from subprocess import check_output
from functions.colors import convert_rgb_xy, hsv_to_rgb

logging = logManager.logger.get_logger(__name__)

def set_light(light, data):
    payload = {}
    url = "coaps://" + light.protocol_cfg["ip"] + ":5684/15001/" + str(light.protocol_cfg["id"])
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
    check_output("./coap-client-linux -B 2 -m put -u \"" + light.protocol_cfg["identity"] + "\" -k \"" + light.protocol_cfg["psk"] + "\" -e '{ \"3311\": [" + json.dumps(payload) + "] }' \"" + url + "\"", shell=True)

def get_light_state(light):
    state ={}
    light_data = json.loads(check_output("./coap-client-linux -B 5 -m get -u \"" + light.protocol_cfg["identity"] + "\" -k \"" + light.protocol_cfg["psk"] + "\" \"coaps://" + light.protocol_cfg["ip"] + ":5684/15001/" + str(light.protocol_cfg["id"]) +"\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
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

    return state

def discover(detectedLights, tradfriConfig):
    if "psk" in tradfriConfig:
        logging.debug("tradfri: <discover> invoked!")
        try:
            tradriDevices = json.loads(check_output("./coap-client-linux -B 5 -m get -u \"" + tradfriConfig["identity"] + "\" -k \"" + tradfriConfig["psk"] + "\" \"coaps://" + tradfriConfig["tradfriGwIp"] + ":5684/15001\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
            logging.debug(tradriDevices)
            for device in tradriDevices:
                deviceParameters = json.loads(check_output("./coap-client-linux -B 5 -m get -u \"" + tradfriConfig["identity"] + "\" -k \"" + tradfriConfig["psk"] + "\" \"coaps://" + tradfriConfig["tradfriGwIp"] + ":5684/15001/" + str(device) +"\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
                if "3311" in deviceParameters:
                    logging.debug("found tradfi light " + deviceParameters["9001"])
                    detectedLights.append({"protocol": "tradfri", "name": deviceParameters["9001"], "modelid": "LCT015", "protocol_cfg": {"ip": tradfriConfig["tradfriGwIp"], "id": device, "identity": tradfriConfig["identity"], "psk":  tradfriConfig["psk"]}})
        except Exception as e:
            logging.warning(e)
    return detectedLights
