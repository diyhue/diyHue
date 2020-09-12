import json
import logging
import requests


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

def discover(device_ips):
    logging.debug("tasmota: <discover> invoked!")
    for ip in device_ips:
        try:
            response = requests.get("http://" + ip + "/detect", timeout=3)
            if response.status_code == 200:
                device_data = json.loads(response.text)
                logging.info(pretty_json(device_data))

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
                    logging.info("Add new light: " + device_data["name"])
                    for x in range(1, lights + 1):
                        light = find_light_in_config_from_mac_and_nr(device_data['mac'], x)

                        # Try to find light in existing config
                        if light:
                            logging.info("Updating old light: " + device_data["name"])
                            # Light found, update config
                            bridgeConfig["emulator"]["lights"][light].update({"ip": ip, "protocol": protocol})
                            if "version" in device_data:
                                bridgeConfig["emulator"]["lights"][light].update({
                                    "version": device_data["version"],
                                    "type": device_data["type"],
                                    "name": device_data["name"]
                                })
                            continue

                        lightName = generate_light_name(device_data['name'], x)

                        emulatorLightConfig = {
                            "ip": ip,
                            "light_nr": x,
                            "protocol": protocol,
                            "mac": device_data["mac"]
                            }

                        addNewLight(device_data["modelid"], lightName, emulatorLightConfig)



        except Exception as e:
            logging.info("ip %s is unknown device: %s", ip, e)
