import json
import random
from subprocess import check_output

import requests

import logManager
from functions import light_types, nextFreeId
from functions.colors import convert_rgb_xy, convert_xy, rgbBrightness

logging = logManager.logger.get_logger(__name__)

def sendRequest(url, timeout=3):

    head = {"Content-type": "application/json"}
    response = requests.get(url, timeout=timeout, headers=head)
    return response.text


def discover(bridge_config, new_lights):
    logging.debug("tasmota: <discover> invoked!")

    device_ips = check_output("nmap  " + bridge_config["config"]["ipaddress"] + "/24 -p80 --open -n | grep report | cut -d ' ' -f5", shell=True).decode('utf-8').rstrip("\n").split("\n")
    del device_ips[-1] #delete last empty element in list
    for ip in device_ips:
        try:
            logging.debug ( "tasmota: probing ip " + ip)
            response = requests.get ("http://" + ip + "/cm?cmnd=Status%200", timeout=3)
            if response.status_code == 200:
                device_data = json.loads(response.text)
                #logging.debug(pretty_json(device_data))
                if ("StatusSTS" in device_data):

                    logging.debug("tasmota: " + ip + " is a Tasmota device ")
                    logging.debug ("tasmota: Hostname: " + device_data["StatusNET"]["Hostname"] )
                    logging.debug ("tasmota: Mac:      " + device_data["StatusNET"]["Mac"] )

                    properties = {"rgb": True, "ct": False, "ip": ip, "name": device_data["StatusNET"]["Hostname"], "id": device_data["StatusNET"]["Mac"], "mac": device_data["StatusNET"]["Mac"]}
                    device_exist = False
                    for light in bridge_config["lights_address"].keys():
                        if bridge_config["lights_address"][light]["protocol"] == "tasmota" and  bridge_config["lights_address"][light]["id"] == properties["id"]:
                            device_exist = True
                            bridge_config["lights_address"][light]["ip"] = properties["ip"]
                            logging.debug("tasmota: light id " + properties["id"] + " already exist, updating ip...")
                            break
                    if (not device_exist):
                        light_name = "Tasmota id " + properties["id"][-8:] if properties["name"] == "" else properties["name"]
                        logging.debug("tasmota: Add Tasmota: " + properties["id"])
                        modelid = "Tasmota"
                        new_light_id = nextFreeId(bridge_config, "lights")
                        bridge_config["lights"][new_light_id] = {"state": light_types[modelid]["state"], "type": light_types[modelid]["type"], "name": light_name, "uniqueid": "4a:e0:ad:7f:cf:" + str(random.randrange(0, 99)) + "-1", "modelid": modelid, "manufacturername": "Tasmota", "swversion": light_types[modelid]["swversion"]}
                        new_lights.update({new_light_id: {"name": light_name}})
                        bridge_config["lights_address"][new_light_id] = {"ip": properties["ip"], "id": properties["id"], "protocol": "tasmota"}

        except Exception as e:
            logging.debug("tasmota: ip " + ip + " is unknow device, " + str(e))



def set_light(address, light, data, rgb = None):
    logging.debug("tasmota: <set_light> invoked! IP=" + address["ip"])

    for key, value in data.items():
        logging.debug("tasmota: key " + key)

        if key == "on":
            if value:
                sendRequest ("http://"+address["ip"]+"/cm?cmnd=Power%20on")
            else:
                sendRequest ("http://"+address["ip"]+"/cm?cmnd=Power%20off")
        elif key == "bri":
            brightness = int(100.0 * (value / 254.0))
            sendRequest ("http://"+address["ip"]+"/cm?cmnd=Dimmer%20" + str(brightness))
        elif key == "ct":
            color = {}
        elif key == "xy":
            if rgb:
                color = rgbBrightness(rgb, light["state"]["bri"])
            else:
                color = convert_xy(value[0], value[1], light["state"]["bri"])
            sendRequest ("http://"+address["ip"]+"/cm?cmnd=Color%20" + str(color[0]) + "," + str(color[1]) + "," + str(color[2]))
        elif key == "alert":
                if value == "select":
                    sendRequest ("http://" + address["ip"] + "/cm?cmnd=dimmer%20100")


def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    tup = tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    return list(tup)


def rgb_to_hex(rgb):
    return '%02x%02x%02x' % rgb
    #return '#%02x%02x%02x' % rgb

def get_light_state(address, light):
    logging.debug("tasmota: <get_light_state> invoked!")
    data = sendRequest ("http://" + address["ip"] + "/cm?cmnd=Status%2011")
    #logging.debug(data)
    light_data = json.loads(data)["StatusSTS"]
    #logging.debug(light_data)
    state = {}

    if 'POWER'in light_data:
        state['on'] = True if light_data["POWER"] == "ON" else False
        #logging.debug('POWER')
    elif 'POWER1'in light_data:
        state['on'] = True if light_data["POWER1"] == "ON" else False
        #logging.debug('POWER1')

    if 'Color' not in light_data:
       #logging.debug('not Color')
        if state['on'] == True:
            state["xy"] = convert_rgb_xy(255,255,255)
            state["bri"] = int(255)
            state["colormode"] = "xy"
    else:
        #logging.debug('Color')
        hex = light_data["Color"]
        rgb = hex_to_rgb(hex)
        logging.debug(rgb)
        #rgb = light_data["Color"].split(",")
        logging.debug("tasmota: <get_light_state>: red " + str(rgb[0]) + " green " + str(rgb[1]) + " blue " + str(rgb[2]) )
        # state["xy"] = convert_rgb_xy(int(rgb[0],16), int(rgb[1],16), int(rgb[2],16))
        state["xy"] = convert_rgb_xy(rgb[0],rgb[1],rgb[2])
        state["bri"] = (int(light_data["Dimmer"]) / 100.0) * 254.0
        state["colormode"] = "xy"
    return state
