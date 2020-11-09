import json
import configManager
import logManager
from functions.json import pretty_json
from functions import nextFreeId
from subprocess import check_output

bridge_config = configManager.bridgeConfig.json_config
logging = logManager.logger.get_logger(__name__)
new_lights = configManager.runtimeConfig.newLights

def scanTradfri():
    if "tradfri" in bridge_config:
        tradri_devices = json.loads(check_output("./coap-client-linux -m get -u \"" + bridge_config["tradfri"]["identity"] + "\" -k \"" + bridge_config["tradfri"]["psk"] + "\" \"coaps://" + bridge_config["tradfri"]["ip"] + ":5684/15001\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
        logging.info(pretty_json(tradri_devices))
        lights_found = 0
        for device in tradri_devices:
            device_parameters = json.loads(check_output("./coap-client-linux -m get -u \"" + bridge_config["tradfri"]["identity"] + "\" -k \"" + bridge_config["tradfri"]["psk"] + "\" \"coaps://" + bridge_config["tradfri"]["ip"] + ":5684/15001/" + str(device) +"\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
            if "3311" in device_parameters:
                new_light = True
                for light in bridge_config["lights_address"]:
                    if bridge_config["lights_address"][light]["protocol"] == "ikea_tradfri" and bridge_config["lights_address"][light]["device_id"] == device:
                        new_light = False
                        break
                if new_light:
                    lights_found += 1
                    #register new tradfri lightdevice_id
                    logging.info("register tradfi light " + device_parameters["9001"])
                    new_light_id = nextFreeId(bridge_config, "lights")
                    bridge_config["lights"][new_light_id] = {"state": {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "effect": "none", "colormode": "ct", "reachable": True}, "type": "Extended color light", "name": device_parameters["9001"], "uniqueid": "1234567" + str(device), "modelid": "LLM010", "swversion": "66009461", "manufacturername": "Philips"}
                    new_lights.update({new_light_id: {"name": device_parameters["9001"]}})
                    bridge_config["lights_address"][new_light_id] = {"device_id": device, "preshared_key": bridge_config["tradfri"]["psk"], "identity": bridge_config["tradfri"]["identity"], "ip": bridge_config["tradfri"]["ip"], "protocol": "ikea_tradfri"}
        return lights_found
    else:
        return 0