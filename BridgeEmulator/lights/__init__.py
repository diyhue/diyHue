import json
import random
import socket
import requests


def nextFreeId(bridge_config, element):
    i = 1
    while (str(i)) in bridge_config[element]:
        i += 1
    return str(i)


def generate_unique_id():
    rand_bytes = [random.randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0],rand_bytes[1],rand_bytes[2])


# Define light defininitions for discovery features and adding device data to config
light_types = {}
light_types["Tasmota"] = {"type": "Extended color light", "swversion": "1.46.13_r26312"}
light_types["Tasmota"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "alert": "none", "effect": "none", "colormode": "xy", "reachable": True}

light_types["Shelly"] = {"type": "shelly1", "swversion": "1.46.13_r26312"}
light_types["Shelly"]["state"] = {"on": False, "alert": "none", "reachable": True}

light_types["ESPHome-RGB"] = {"type": "Extended color light", "swversion": "1.46.13_r26312", "manufacturername": "ESPHome"}
light_types["ESPHome-RGB"]["state"] = {"on": False, "bri": 254, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "alert": "none", "effect": "none", "colormode": "xy", "reachable": True}
light_types["ESPHome-RGB"]["config"] = {"archetype": "sultanbulb", "function": "mixed", "direction": "omnidirectional"}

light_types["ESPHome-Dimmable"] = {"type": "Dimmable light", "swversion": "1.46.13_r26312", "manufacturername": "ESPHome"}
light_types["ESPHome-Dimmable"]["state"] = {"on": False, "bri": 254,"alert": "none", "reachable": True}
light_types["ESPHome-Dimmable"]["config"] = {"archetype": "classicbulb", "function": "mixed", "direction": "omnidirectional"}

light_types["ESPHOME-Toggle"] = {"type": "On/Off plug-in unit", "swversion": "V1.04.12", "manufacturername": "ESPHome"}
light_types["ESPHOME-Toggle"]["state"] = {"on": False, "alert": "none", "reachable": True}
light_types["ESPHOME-Toggle"]["config"] = {"archetype": "classicbulb", "function": "mixed", "direction": "omnidirectional"}

light_types["LCT001"] = {"type":"Extended color light", "manufacturername": "Signify Netherlands B.V.", "swversion": "1.46.13_r26312"}
light_types["LCT001"]["state"] = {"alert": "none", "bri":0, "colormode": "xy", "effect": "none","hue": 0, "mode": "homeautomation","on": False,"reachable": True, "sat": 0,"xy": [0.408,0.517]}
light_types["LCT001"]["config"] = {"archetype": "sultanbulb","direction": "omnidirectional","function": "mixed","startup": {"configured": True, "mode": "powerfail"}}
light_types["LCT001"]["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.675,0.322],[0.409,0.518],[0.167,0.04]],"colorgamuttype": "B","ct": {"max": 500,"min": 153},"maxlumen": 600,"mindimlevel": 5000},"streaming": {"proxy": False,"renderer": True}},

light_types["LCT015"] = {"type": "Extended color light", "swversion": "1.46.13_r26312", "manufacturername": "Philips"}
light_types["LCT015"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "mode": "homeautomation", "effect": "none", "colormode": "ct", "reachable": True}
light_types["LCT015"]["config"] = {"archetype": "sultanbulb", "function": "mixed", "direction": "omnidirectional"}
light_types["LCT015"]["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.6915,0.3083],[0.17,0.7],[0.1532,0.0475]],"colorgamuttype": "C","ct": {"max": 500,"min": 153},"maxlumen": 800,"mindimlevel": 1000},"streaming": {"proxy": False,"renderer": True}}

light_types["LST002"] = {"type": "Color light", "swversion": "5.127.1.26581"}
light_types["LST002"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "mode": "homeautomation", "effect": "none", "colormode": "ct", "reachable": True}
light_types["LST002"]["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.704,0.296],[0.2151,0.7106],[0.138,0.08]],"colorgamuttype": "A","maxlumen": 200,"mindimlevel": 10000},"streaming": {"proxy": False,"renderer": True}}

light_types["LWB010"] = {"type": "Dimmable light", "swversion": "1.46.13_r26312", "manufacturername": "Philips"}
light_types["LWB010"]["state"] = {"on": False, "bri": 254,"alert": "none", "reachable": True}
light_types["LWB010"]["config"] = {"archetype": "classicbulb", "function": "mixed", "direction": "omnidirectional"}

light_types["LTW001"] = {"type": "Color temperature light", "swversion": "1.46.13_r26312"}
light_types["LTW001"]["state"] = {"on": False, "colormode": "ct", "alert": "none", "mode": "homeautomation", "reachable": True, "bri": 254, "ct": 230}
light_types["LTW001"]["capabilities"] = {"certified": True,"control": {"mindimlevel": 1000,"maxlumen": 806,"ct": {"min": 153,"max": 454}},"streaming": {"renderer": False,"proxy": False}}

light_types["Plug 01"] = {"type": "On/Off plug-in unit", "swversion": "V1.04.12"}
light_types["Plug 01"]["state"] = {"on": False, "alert": "none", "reachable": True}


def scanHost(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.02) # Very short timeout. If scanning fails this could be increased
    result = sock.connect_ex((host, port))
    sock.close()
    return result

def iter_ips(port):
    argsDict = configManager.runtimeConfig.arg
    HOST_IP = argsDict["HOST_IP"]
    scan_on_host_ip = argsDict["scanOnHostIP"]
    ip_range_start = argsDict["IP_RANGE_START"]
    ip_range_end = argsDict["IP_RANGE_END"]
    host = HOST_IP.split('.')
    if scan_on_host_ip:
        yield ('127.0.0.1', port)
        return
    for addr in range(ip_range_start, ip_range_end + 1):
        host[3] = str(addr)
        test_host = '.'.join(host)
        if test_host != HOST_IP:
            yield (test_host, port)

def find_hosts(port):
    validHosts = []
    for host, port in iter_ips(port):
        if scanHost(host, port) == 0:
            hostWithPort = '%s:%s' % (host, port)
            validHosts.append(hostWithPort)

    return validHosts

def find_light_in_config_from_mac_and_nr(mac_address, light_nr):
    for light_id, light_address in bridgeConfig["emulator"]["lights"].items():
        if (light_address["protocol"] in ["native", "native_single",  "native_multi"]
                and light_address["mac"] == mac_address
                and ('light_nr' not in light_address or
                    light_address['light_nr'] == light_nr)):
            return light_id
    return None

def generate_light_name(base_name, light_nr):
    # Light name can only contain 32 characters
    suffix = ' %s' % light_nr
    return '%s%s' % (base_name[:32-len(suffix)], suffix)


def scan_for_lights(): #scan for ESP8266 lights and strips
    #return all host that listen on port 80
    device_ips = find_hosts(80)
    logging.info(pretty_json(device_ips))
    Thread(target=lights.yeelight.discover).start()
    Thread(target=lights.tasmota.discover).start()
    Thread(target=lights.shelly.discover).start()
    Thread(target=lights.esphome.discover).start()
    Thread(target=lights.mqtt.discover).start()

    for ip in device_ips:
        #try:
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

                    new_light_id = nextFreeId(bridgeConfig, "lights")

                    light_name = generate_light_name(device_data['name'], x)

                    # Construct the configuration for this light from a few sources, in order of precedence
                    # (later sources override earlier ones).
                    # Global defaults
                    new_light = {
                        "manufacturername": "Philips",
                        "uniqueid": generate_unique_id(),
                    }
                    # Defaults for this specific modelid
                    if device_data["modelid"] in light_types:
                        new_light.update(light_types[device_data["modelid"]])
                        # Make sure to make a copy of the state dictionary so we don't share the dictionary
                        new_light['state'] = light_types[device_data["modelid"]]['state'].copy()
                    # Overrides from the response JSON
                    new_light["modelid"] = device_data["modelid"]
                    new_light["name"] = light_name

                    # Add the light to new lights, and to bridge_config (in two places)
                    newLights[new_light_id] = {"name": light_name}
                    bridgeConfig["lights"][new_light_id] = new_light
                    bridgeConfig["emulator"]["lights"][new_light_id] = {
                        "ip": ip,
                        "light_nr": x,
                        "protocol": protocol,
                        "mac": device_data["mac"]
                        }
        #except Exception as e:
        #    logging.info("ip %s is unknown device: %s", ip, e)
            #raise
    deconz.scanDeconz()
    tradfri.scanTradfri()
    saveConfig()
