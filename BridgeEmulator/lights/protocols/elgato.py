import socket
import json
import logManager
import requests
from time import sleep
from zeroconf import IPVersion, ServiceBrowser, ServiceStateChange, Zeroconf

logging = logManager.logger.get_logger(__name__)

discovered_lights = []

def on_mdns_discover(zeroconf, service_type, name, state_change):
    if "Elgato Key Light" in name and state_change is ServiceStateChange.Added:
        info = zeroconf.get_service_info(service_type, name)
        if info:
            addresses = ["%s" % (socket.inet_ntoa(addr))
                         for addr in info.addresses]
            discovered_lights.append([addresses[0], name])
            logging.debug('<Elgato> mDNS device discovered:'+ addresses[0])


def discover(detectedLights, elgato_ips):
    mdns_string = "_elgo._tcp.local."
    logging.info('<Elgato> mDNS discovery for ' + mdns_string + ' started')
    ip_version = IPVersion.V4Only
    zeroconf = Zeroconf(ip_version=ip_version)
    ServiceBrowser(zeroconf, mdns_string, handlers=[on_mdns_discover])

    sleep(2)

    if len(discovered_lights) == 0:
        # Didn't find anything using mdns, trying elgato_ips
        logging.info("<Elgato> Nothing found using mDNS, trying to find lights by IP")
        for ip in elgato_ips:
            try:
                response = requests.get(
                    "http://"+ ip +":9123/elgato/accessory-info", timeout=3)
                if response.status_code == 200:
                    json_resp = json.loads(response.content)
                    if json_resp['productName'] in ["Elgato Key Light Mini", "Elgato Key Light Air", "Elgato Key Light"]: 
                       discovered_lights.append([ip, json_resp['displayName']])
            except Exception as e:
                logging.warning("<Elgato> ip %s is unknown device", ip)

    lights = []
    for device in discovered_lights:
        try:
            response = requests.get("http://"+ device[0] +":9123/elgato/accessory-info", timeout=3)
            if response.status_code == 200:
                json_accessory_info = json.loads(response.content)

            logging.info("<Elgato> Found device: %s at IP %s" % (device[1], device[0]))

            lights.append({"protocol": "elgato",
                               "name": json_accessory_info["displayName"] ,
                               "modelid": "LTW001",  #Colortemp Bulb
                               "protocol_cfg": {
                                   "ip": device[0],
                                   "mdns_name": device[1],
                                   "mac": json_accessory_info["macAddress"],
                               }
                            })
        except Exception as e:
            logging.warning("<Elgato> EXCEPTION: " + str(e))
            break

    for light in lights:
        detectedLights.append(light)

def translate_range(value, old_min, old_max, new_min, new_max):
    old_range = old_max - old_min
    new_range = new_max - new_min
    scaled_value = (((value - old_min) * new_range) / old_range) + new_min
    new_value = max(min(scaled_value, new_max), new_min)
    return int(new_value)

def set_light(light, data):
    light_state = {}

    if 'on' in data:
        light_state['on'] = 1 if data['on'] else 0

    if 'bri' in data and data['bri'] > 0:
        light_state['brightness'] = round((data['bri'] / 255) * 100)

    if 'ct' in data:
        light_state['temperature'] = translate_range(data['ct'], 153, 500, 143, 344)

    # Ingore unsupported values (xy,hue,sat)

    if light_state:
        json_data = json.dumps({"lights": [light_state]})
        response = requests.put("http://"+light.protocol_cfg["ip"]+":9123/elgato/lights", data = json_data, headers={'Content-type': 'application/json'}, timeout=3)
        return response.text

def get_light_state(light):
    response = requests.get("http://"+light.protocol_cfg["ip"]+":9123/elgato/lights", timeout=3)
    state = response.json()
    light_info  = state['lights'][0]
    if light_info['on'] == 1:
        light_state_on = True
    else:
        light_state_on = False

    converted_state = {
        'bri': round((light_info['brightness']/100)*255),
        'on': light_state_on,
        'ct': translate_range(light_info['temperature'], 143, 344, 153, 500),
        'colormode': 'ct'
    }
    return  converted_state
