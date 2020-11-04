import json
import random
import socket
from threading import Thread

import requests

import configManager
import logManager
from functions import light_types, nextFreeId
from functions.json import pretty_json
from protocols import tradfri, yeelight, tasmota, shelly, esphome, mqtt, hyperion, deconz

bridge_config = configManager.bridgeConfig.json_config
logging = logManager.logger.get_logger(__name__)
new_lights = configManager.runtimeConfig.newLights
dxState = configManager.runtimeConfig.dxState
HOST_HTTP_PORT = configManager.runtimeConfig.arg["HTTP_PORT"]

def find_light_in_config_from_mac_and_nr(bridge_config, mac_address, light_nr):
    for light_id, light_address in bridge_config["lights_address"].items():
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
def scanHost(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.02) # Very short timeout. If scanning fails this could be increased
    result = sock.connect_ex((host, port))
    sock.close()
    return result
def find_hosts(port):
    validHosts = []
    for host, port in iter_ips(port):
        if scanHost(host, port) == 0:
            hostWithPort = '%s:%s' % (host, port)
            validHosts.append(hostWithPort)

    return validHosts

def generate_unique_id():
    rand_bytes = [random.randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0],rand_bytes[1],rand_bytes[2])

def scan_for_lights(): #scan for ESP8266 lights and strips
    Thread(target=yeelight.discover, args=[bridge_config, new_lights]).start()
    Thread(target=tasmota.discover, args=[bridge_config, new_lights]).start()
    Thread(target=shelly.discover, args=[bridge_config, new_lights]).start()
    Thread(target=esphome.discover, args=[bridge_config, new_lights]).start()
    Thread(target=mqtt.discover, args=[bridge_config, new_lights]).start()
    Thread(target=hyperion.discover, args=[bridge_config, new_lights]).start()
    Thread(target=deconz.deconz.scanDeconz).start()
    #return all host that listen on port 80
    device_ips = find_hosts(80)
    logging.info(pretty_json(device_ips))
    #logging.debug('devs', device_ips)
    for ip in device_ips:
        try:
            response = requests.get("http://" + ip + "/detect", timeout=3)
            if response.status_code == 200:
                # XXX JSON validation
                try:
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
                            light = find_light_in_config_from_mac_and_nr(bridge_config,
                                    device_data['mac'], x)

                            # Try to find light in existing config
                            if light:
                                logging.info("Updating old light: " + device_data["name"])
                                # Light found, update config
                                light_address = bridge_config["lights_address"][light]
                                light_address["ip"] = ip
                                light_address["protocol"] = protocol
                                if "version" in device_data:
                                    light_address.update({
                                        "version": device_data["version"],
                                        "type": device_data["type"],
                                        "name": device_data["name"]
                                    })
                                continue

                            new_light_id = nextFreeId(bridge_config, "lights")

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
                            new_lights[new_light_id] = {"name": light_name}
                            bridge_config["lights"][new_light_id] = new_light
                            bridge_config["lights_address"][new_light_id] = {
                                "ip": ip,
                                "light_nr": x,
                                "protocol": protocol,
                                "mac": device_data["mac"]
                            }
                except ValueError:
                    logging.info('Decoding JSON from %s has failed', ip)
        except Exception as e:
            logging.info("ip %s is unknown device: %s", ip, e)
            #raise
    tradfri.discover.scanTradfri()
    configManager.bridgeConfig.save_config()