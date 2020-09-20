import json
import logManager
import requests
import configManager
from lights.discover import addNewLight


bridgeConfig = configManager.bridgeConfig.json_config
logging = logManager.logger.get_logger(__name__)

def set_light(address, light, data):
    state = requests.put("http://"+address["ip"]+"/state", json={address["light_nr"]: data}, timeout=3)
    return state.text

def get_light_state(address, light):
    state = requests.get("http://"+address["ip"]+"/state?light=" + str(address["light_nr"]), timeout=3)
    return json.loads(state.text)


def generate_light_name(base_name, light_nr):
    # Light name can only contain 32 characters
    suffix = ' %s' % light_nr
    return '%s%s' % (base_name[:32-len(suffix)], suffix)

def find_light_in_config_from_mac_and_nr(mac_address, light_nr):
    for light_id, light_address in bridgeConfig["emulator"]["lights"].items():
        if (light_address["protocol"] in ["native", "native_single",  "native_multi"]
                and light_address["mac"] == mac_address
                and ('light_nr' not in light_address or
                    light_address['light_nr'] == light_nr)):
            return light_id
    return None

def discover(device_ips):
    logging.debug("native: <discover> invoked!")
    for ip in device_ips:
        try:
            response = requests.get("http://" + ip + "/detect", timeout=3)
            if response.status_code == 200:
                device_data = json.loads(response.text)
                logging.info(json.dumps(device_data))

                if "modelid" in device_data:
                    logging.info(ip + " is " + device_data['name'])
                    if "protocol" in device_data:
                        protocol = device_data["protocol"]
                    else:
                        protocol = "native"

                    # Get number of lights
                    light = 1
                    if "lights" in device_data:
                        light = device_data["lights"]

                    # Add each light to config
                    logging.info("Add new light: " + device_data["name"])
                    for x in range(1, light + 1):
                        light = find_light_in_config_from_mac_and_nr(device_data['mac'], x)
                        lightName = generate_light_name(device_data['name'], x)

                        # Try to find light in existing config
                        if light:
                            logging.info("Updating old light: " + lightName)
                            # Light found, update config
                            bridgeConfig["emulator"]["lights"][light].update({"ip": ip, "protocol": protocol})
                            if "version" in device_data:
                                bridgeConfig["emulator"]["lights"][light].update({
                                    "version": device_data["version"],
                                    "type": device_data["type"],
                                    "name": device_data["name"]
                                })
                            continue

                        emulatorLightConfig = {
                            "ip": ip,
                            "light_nr": x,
                            "protocol": protocol,
                            "mac": device_data["mac"]
                            }
    
                        addNewLight(device_data["modelid"], lightName, emulatorLightConfig)



        except Exception as e:
            logging.info("ip %s is unknown device: %s", ip, e)
