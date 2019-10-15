import json
import logging
import random
import requests

import socket
import sys

from time import sleep
from subprocess import check_output
from functions import light_types, nextFreeId
from functions.colors import convert_rgb_xy, convert_xy, hsv_to_rgb
from functions.network import getIpAddress

def getRequest(address, request_data, timeout=3):

    head = {"Content-type": "application/json"}
    response = requests.get("http://" + address + request_data, timeout=timeout, headers=head)
    return response.text

def postRequest(address, request_data, timeout=3):
    head = {"Content-type": "application/json"}
    response = requests.post("http://" + address + request_data, timeout=3, headers=head)
    return response.text

def getLightType(light, address, data):
    request_data = ""
    if address["esphome_model"] == "ESPHome-RGBW":
        if "ct" in data:
            request_data = request_data + "/light/white_led"
        elif "xy" in data:
            request_data = request_data + "/light/color_led"
        else:
            if light["state"]["colormode"] == "ct":
                request_data = request_data + "/light/white_led"
            elif light["state"]["colormode"] in ["xy", "hs"]:
                request_data = request_data + "/light/color_led"
    elif address["esphome_model"] == "ESPHome-CT":
        request_data = request_data + "/light/white_led"
    elif address["esphome_model"] == "ESPHome-RGB":
        request_data = request_data + "/light/color_led"
    elif address["esphome_model"] == "ESPHome-Dimmable":
        request_data = request_data + "/light/dimmable_led"
    elif address["esphome_model"] == "ESPHome-Toggle":
        request_data = request_data + "/light/toggle_led"
    
    return request_data

def discover(bridge_config, new_lights):
    logging.debug("ESPHome: <discover> invoked!")

    device_ips = check_output("nmap  " + getIpAddress() + "/24 -p80 --open -n | grep report | cut -d ' ' -f5", shell=True).decode('utf-8').rstrip("\n").split("\n")
    del device_ips[-1] #delete last empty element in list
    for ip in device_ips:
        try:
            logging.debug ( "ESPHome: probing ip " + ip)
            response = requests.get ("http://" + ip + "/text_sensor/light_id", timeout=3)
            device = json.loads(response.text)['state'].split(';') #get device data
            mac = device[1]
            device_name = device[2]
            ct_boost = device[3]
            rgb_boost = device[4]
            if response.status_code == 200 and device[0] == "esphome_diyhue_light":
                logging.debug("ESPHome: Found " + device_name + " at ip " + ip)
                white_response = requests.get ("http://" + ip + "/light/white_led", timeout=3)
                color_response = requests.get ("http://" + ip + "/light/color_led", timeout=3)
                dim_response = requests.get ("http://" + ip + "/light/dimmable_led", timeout=3)
                toggle_response = requests.get ("http://" + ip + "/light/toggle_led", timeout=3)

                if (white_response.status_code != 200 and color_response.status_code != 200 and dim_response != 200 and toggle_response != 200):
                    logging.debug("ESPHome: Device has improper configuration! Exiting.")
                    raise
                elif (white_response.status_code == 200 and color_response.status_code == 200):
                    logging.debug("ESPHome: " + device_name + " is a RGBW ESPHome device")
                    white_device_data = json.loads(white_response.text)
                    color_device_data = json.loads(color_response.text)
                    properties = {"rgb": True, "ct": True, "ip": ip, "name": device_name, "id": mac, "mac": mac, "ct_boost": ct_boost, "rgb_boost": rgb_boost}
                    esphome_model = "ESPHome-RGBW"
                    modelid = "LCT015"
                elif (white_response.status_code == 200):
                    logging.debug("ESPHome: " + device_name + " is a CT ESPHome device")
                    white_device_data = json.loads(white_response.text)
                    properties = {"rgb": False, "ct": True, "ip": ip, "name": device_name, "id": mac, "mac": mac, "ct_boost": ct_boost, "rgb_boost": rgb_boost}
                    esphome_model = "ESPHome-CT"
                    modelid = "LWB010"
                elif (color_response.status_code == 200):
                    logging.debug("ESPHome: " + device_name + " is a RGB ESPHome device")
                    color_device_data = json.loads(color_response.text)
                    properties = {"rgb": True, "ct": False, "ip": ip, "name": device_name, "id": mac, "mac": mac, "ct_boost": ct_boost, "rgb_boost": rgb_boost}
                    esphome_model = "ESPHome-RGB"
                    modelid = "ESPHome-RGB"
                elif (dim_response.status_code == 200):
                    logging.debug("ESPHome: " + device_name + " is a Dimmable ESPHome device")
                    dim_device_data = json.loads(dim_response.text)
                    properties = {"rgb": False, "ct": False, "ip": ip, "name": device_name, "id": mac, "mac": mac, "ct_boost": ct_boost, "rgb_boost": rgb_boost}
                    esphome_model = "ESPHome-Dimmable"
                    modelid = "ESPHome-Dimmable"
                elif (toggle_response.status_code == 200):
                    logging.debug("ESPHome: " + device_name + " is a Toggle ESPHome device")
                    toggle_device_data = json.loads(toggle_response.text)
                    properties = {"rgb": False, "ct": False, "ip": ip, "name": device_name, "id": mac, "mac": mac, "ct_boost": ct_boost, "rgb_boost": rgb_boost}
                    esphome_model = "ESPHome-Toggle"
                    modelid = "ESPHome-Toggle"

                device_exist = False
                for light in bridge_config["lights_address"].keys():
                    if bridge_config["lights_address"][light]["protocol"] == "esphome" and  bridge_config["lights_address"][light]["id"].split('.')[0] == properties["id"].split('.')[0]:
                        device_exist = True
                        bridge_config["lights_address"][light]["ip"] = properties["ip"]
                        bridge_config["lights_address"][light]["ct_boost"] = properties["ct_boost"]
                        bridge_config["lights_address"][light]["rgb_boost"] = properties["rgb_boost"]
                        logging.debug("ESPHome: light id " + properties["id"] + " already exists, updating device data...")
                        break
                if (not device_exist):
                    light_name = "ESPHome id " + properties["id"][-8:] if properties["name"] == "" else properties["name"]
                    logging.debug("ESPHome: Adding ESPHome " + properties["id"])
                    new_light_id = nextFreeId(bridge_config, "lights")
                    bridge_config["lights"][new_light_id] = {"state": light_types[modelid]["state"], "type": light_types[modelid]["type"], "name": light_name, "uniqueid": mac, "modelid": modelid, "manufacturername": "Philips", "swversion": light_types[modelid]["swversion"]}
                    new_lights.update({new_light_id: {"name": light_name}})
                    bridge_config["lights_address"][new_light_id] = {"ip": properties["ip"], "id": properties["id"], "protocol": "esphome", "rgb_boost": rgb_boost, "ct_boost": ct_boost, "esphome_model": esphome_model}

        except Exception as e:
            logging.debug("ESPHome: ip " + ip + " is unknown device, " + str(e))

def set_light(address, light, data):
    logging.debug("ESPHome: <set_light> invoked! IP=" + address["ip"])
    logging.debug(light["modelid"])
    logging.debug(data)

    ct_boost = int(address["ct_boost"])
    rgb_boost = int(address["rgb_boost"])
    request_data = ""
    if address["esphome_model"] == "ESPHome-RGBW":
        if "ct" in data:
            postRequest(address["ip"], "/light/color_led/turn_off")
        if ("xy" in data) or ("hue" in data) or ("sat" in data):
            postRequest(address["ip"], "/light/white_led/turn_off")
    if ("alert" in data) and (data['alert'] == "select"):
            request_data = request_data + "/switch/alert/turn_on"
    else:
        request_data = request_data + getLightType(light, address, data)
        if "on" in data:
            if not(data['on']):
                request_data = request_data + "/turn_off"
            else:
                request_data = request_data + "/turn_on"
        else:
            request_data = request_data + "/turn_on"
        if address["esphome_model"] is not "ESPHome-Toggle":
            if "bri" in data:
                brightness = int(data['bri'])
                if address["esphome_model"] == "ESPHome-RGBW":
                    if light["state"]["colormode"] == "ct":
                        brightness = ct_boost + brightness
                    elif light["state"]["colormode"] == "xy":
                        brightness = rgb_boost + brightness
                elif address["esphome_model"] == "ESPHome-CT":
                    brightness = ct_boost + brightness
                elif address["esphome_model"] == "ESPHome-RGB":
                    brightness = rgb_boost + brightness
                elif address["esphome_model"] == "ESPHome-Dimmable":
                    brightness = ct_boost + brightness
                brightness = str(brightness)
                if ("?" in request_data):
                    request_data = request_data + "&brightness=" + brightness
                else:
                    request_data = request_data + "?brightness=" + brightness
            if address["esphome_model"] in ["ESPHome-RGBW", "ESPHome-CT"]:
                if "ct" in data:
                    if ("?" in request_data):
                        request_data = request_data + "&color_temp=" + str(data['ct'])
                    else:
                        request_data = request_data + "?color_temp=" + str(data['ct'])
            if address["esphome_model"] in ["ESPHome-RGBW", "ESPHome-RGB"]:
                if "xy" in data:
                    color = convert_xy(data['xy'][0], data['xy'][1], 255)
                    red = str(color[0])
                    green = str(color[1])
                    blue = str(color[2])
                    if ("?" in request_data):
                        request_data = request_data + "&r=" + red + "&g=" + green + "&b=" + blue 
                    else:
                        request_data = request_data + "?r=" + red + "&g=" + green + "&b=" + blue
                elif ("hue" in data) and ("sat" in data):
                    if not("bri" in data):
                        bri = light["state"]["bri"]
                    else:
                        bri = data['bri']
                    color = hsv_to_rgb(data['hue'], data['sat'], bri)
                    red = str(color[0])
                    green = str(color[1])
                    blue = str(color[2])
                    if ("?" in request_data):
                        request_data = request_data + "&r=" + red + "&g=" + green + "&b=" + blue 
                    else:
                        request_data = request_data + "?r=" + red + "&g=" + green + "&b=" + blue
            if "transitiontime" in data:
                if ("?" in request_data):
                    request_data = request_data + "&transition=" + str(int(data['transitiontime']/10))
                else:
                    request_data = request_data + "?transition=" + str(int(data['transitiontime']/10))

    postRequest(address["ip"], request_data)




def get_light_state(address, light):
    logging.debug("ESPHome: <get_light_state> invoked!")
    state = {}
    if address["esphome_model"] == "ESPHome-RGBW":
        white_response = requests.get ("http://" + address["ip"] + "/light/white_led", timeout=3)
        color_response = requests.get ("http://" + address["ip"] + "/light/color_led", timeout=3)
        white_device = json.loads(white_response.text) #get white device data
        color_device = json.loads(color_response.text) #get color device data
        if white_device['state'] == 'OFF' and color_device['state'] == 'OFF':
            state['on'] = False
        elif white_device['state'] == 'ON':
            state['on'] = True
            state['ct'] = int(white_device['color_temp'])
            state['bri'] = int(white_device['brightness'])
            state['colormode'] = "ct"
        elif color_device['state'] == 'ON':
            state['on'] = True
            state['xy'] = convert_rgb_xy(int(color_device['color']['r']), int(color_device['color']['g']), int(color_device['color']['b']))
            state['bri'] = int(color_device['brightness'])
            state['colormode'] = "xy"

    elif address["esphome_model"] == "ESPHome-CT":
        white_response = requests.get ("http://" + address["ip"] + "/light/white_led", timeout=3)
        white_device = json.loads(white_response.text) #get white device data
        if white_device['state'] == 'OFF':
            state['on'] = False
        elif white_device['state'] == 'ON':
            state['on'] = True
            state['ct'] = int(white_device['color_temp'])
            state['bri'] = int(white_device['brightness'])
            state['colormode'] = "ct"

    elif address["esphome_model"] == "ESPHome-RGB":
        color_response = requests.get ("http://" + address["ip"] + "/light/color_led", timeout=3)
        color_device = json.loads(color_response.text)
        if color_device['state'] == 'OFF':
            state['on'] = False
        elif color_device['state'] == 'ON':
            state['on'] = True
            state['xy'] = convert_rgb_xy(int(color_device['color']['r']), int(color_device['color']['g']), int(color_device['color']['b']))
            state['bri'] = int(color_device['brightness'])
            state['colormode'] = "xy"

    elif address["esphome_model"] == "ESPHome-Dimmable":
        dimmable_response = requests.get ("http://" + address["ip"] + "/light/dimmable_led", timeout=3)
        dimmable_device = json.loads(dimmable_response.text)
        if dimmable_device['state'] == 'OFF':
            state['on'] = False
        elif dimmable_device['state'] == 'ON':
            state['on'] = True
            state['bri'] = int(dimmable_device['brightness'])

    elif address["esphome_model"] == "ESPHome-Toggle":
        toggle_response = requests.get ("http://" + address["ip"] + "/light/toggle_led", timeout=3)
        toggle_device = json.loads(toggle_response.text)
        if toggle_device['state'] == 'OFF':
            state['on'] = False
        elif toggle_device['state'] == 'ON':
            state['on'] = True

    return state
