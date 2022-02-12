import json
import logManager
import requests

logging = logManager.logger.get_logger(__name__)

def set_light(light, data):
    lightsData = {}
    if "lights" not in data:
        lightsData = {light.protocol_cfg["light_nr"]: data}
    else:
        lightsData = data["lights"]
    state = requests.put("http://"+light.protocol_cfg["ip"]+"/state", json=lightsData, timeout=3)
    return state.text

def get_light_state(light):
    state = requests.get("http://"+light.protocol_cfg["ip"]+"/state?light=" + str(light.protocol_cfg["light_nr"]), timeout=3)
    return state.json()


def generate_light_name(base_name, light_nr):
    # Light name can only contain 32 characters
    suffix = ' %s' % light_nr
    return '%s%s' % (base_name[:32-len(suffix)], suffix)


def discover(detectedLights, device_ips):
    logging.debug("native: <discover> invoked!")
    for ip in device_ips:
        try:
            response = requests.get("http://" + ip + "/detect", timeout=3)
            if response.status_code == 200:
                device_data = json.loads(response.text)
                logging.debug(json.dumps(device_data))

                if "modelid" in device_data:
                    logging.info(ip + " is " + device_data['name'])
                    if "protocol" in device_data:
                        protocol = device_data["protocol"]
                    else:
                        protocol = "native"

                    # Get number of lights
                    lights = 1
                    if "lights" in device_data:
                        lights = device_data["lights"]


                    # Add each light to config
                    logging.info("Detected light : " + device_data["name"])
                    for x in range(1, lights + 1):
                        logging.info(device_data['name'])
                        lightName = generate_light_name(device_data['name'], x)
                        protocol_cfg = {"ip": ip, "version": device_data["version"], "type": device_data["type"], "light_nr": x, "mac": device_data["mac"]}
                        if device_data["modelid"] == "LCX002":
                            protocol_cfg["points_capable"] = 5
                        detectedLights.append({"protocol": protocol, "name": lightName, "modelid": device_data["modelid"], "protocol_cfg": protocol_cfg})

        except Exception as e:
            logging.info("ip %s is unknown device: %s", ip, e)

    return detectedLights
