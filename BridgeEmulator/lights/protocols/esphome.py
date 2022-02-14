import json
import requests
import logManager
from functions.colors import convert_rgb_xy, convert_xy, hsv_to_rgb, rgbBrightness

logging = logManager.logger.get_logger(__name__)


def postRequest(address, request_data, timeout=3):
    head = {"Content-type": "application/json"}
    response = requests.post("http://" + address + request_data, timeout=3, headers=head)
    return response.text

def addRequest(request_data, data_type, new_data):
    if ("?" in request_data):
        request_data = request_data + "&" + str(data_type) + "=" + str(new_data)
    else:
        request_data = request_data + "?" + str(data_type) + "=" + str(new_data)
    return request_data

def getLightType(light, data):
    request_data = ""
    if light.protocol_cfg["esphome_model"] == "ESPHome-RGBW":
        if "xy" in data: #revised according to hue api docs
            request_data = request_data + "/light/color_led"
        elif "ct" in data:
            request_data = request_data + "/light/white_led"
        elif ("hue" in data) or ("sat" in data):
            request_data = request_data + "/light/color_led"
        else:
            if light["state"]["colormode"] == "xy":
                request_data = request_data + "/light/color_led"
            elif light["state"]["colormode"] == "ct":
                request_data = request_data + "/light/white_led"
            elif light["state"]["colormode"] == "hs":
                request_data = request_data + "/light/color_led"
    elif light.protocol_cfg["esphome_model"] == "ESPHome-CT":
        request_data = request_data + "/light/white_led"
    elif light.protocol_cfg["esphome_model"] == "ESPHome-RGB":
        request_data = request_data + "/light/color_led"
    elif light.protocol_cfg["esphome_model"] == "ESPHome-Dimmable":
        request_data = request_data + "/light/dimmable_led"
    elif light.protocol_cfg["esphome_model"] == "ESPHome-Toggle":
        request_data = request_data + "/light/toggle_led"

    return request_data

def discover(detectedLights, device_ips):
    logging.debug("ESPHome: <discover> invoked!")

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
                properties = {}
                modelid = ""
                if (white_response.status_code != 200 and color_response.status_code != 200 and dim_response.status_code != 200 and toggle_response.status_code != 200):
                    logging.debug("ESPHome: Device has improper configuration! Exiting.")
                    raise
                elif (white_response.status_code == 200 and color_response.status_code == 200):
                    logging.debug("ESPHome: " + device_name + " is a RGBW ESPHome device")
                    properties = {"rgb": True, "ct": True, "ip": ip, "name": device_name,  "mac": mac, "ct_boost": ct_boost, "rgb_boost": rgb_boost, "esphome_model": "ESPHome-RGBW"}
                    modelid = "LCT015"
                elif (white_response.status_code == 200):
                    logging.debug("ESPHome: " + device_name + " is a CT ESPHome device")
                    properties = {"rgb": False, "ct": True, "ip": ip, "name": device_name, "mac": mac, "ct_boost": ct_boost, "rgb_boost": rgb_boost, "esphome_model": "ESPHome-CT"}
                    modelid = "LTW001"
                elif (color_response.status_code == 200):
                    logging.debug("ESPHome: " + device_name + " is a RGB ESPHome device")
                    properties = {"rgb": True, "ct": False, "ip": ip, "name": device_name, "mac": mac, "ct_boost": ct_boost, "rgb_boost": rgb_boost, "esphome_model": "ESPHome-RGB"}
                    modelid = "LCT015"
                elif (dim_response.status_code == 200):
                    logging.debug("ESPHome: " + device_name + " is a Dimmable ESPHome device")
                    properties = {"rgb": False, "ct": False, "ip": ip, "name": device_name,  "mac": mac, "ct_boost": ct_boost, "rgb_boost": rgb_boost, "esphome_model": "ESPHome-Dimmable"}
                    modelid = "LWB010"
                elif (toggle_response.status_code == 200):
                    logging.debug("ESPHome: " + device_name + " is a Toggle ESPHome device")
                    properties = {"rgb": False, "ct": False, "ip": ip, "name": device_name, "id": mac, "mac": mac, "ct_boost": ct_boost, "rgb_boost": rgb_boost, "esphome_model": "ESPHome-Toggle"}
                    modelid = "LOM001"
                else:
                    logging.debug("ESPHome: ip " + ip + " is unknown device")
                    raise
                detectedLights.append({"protocol": "esphome", "name": device_name, "modelid": modelid, "protocol_cfg": properties})

        except Exception as e:
            logging.debug("ESPHome: ip " + ip + " is unknown device, " + str(e))

def set_light(light, data, rgb = None):
    logging.debug("ESPHome: <set_light> invoked! IP=" + light.protocol_cfg["ip"])

    ct_boost = int(light.protocol_cfg["ct_boost"])
    rgb_boost = int(light.protocol_cfg["rgb_boost"])
    request_data = ""
    if ("alert" in data) and (data['alert'] == "select"): #one breath cycle, temporary for now until breath implemented in esphome firmware
        request_data = request_data + "/switch/alert/turn_on"
    # elif ("alert" in data) and (data['alert'] == "lselect"): #15 second breath cycle
    #     request_data = request_data + "/switch/alert/turn_on"
    # elif ("alert" in data) and (data['alert'] == "none"):
    #     request_data = request_data + "/switch/alert/turn_off"
    else:
        request_data = request_data + getLightType(light, data)
        if "white_led" in request_data:
            postRequest(light.protocol_cfg["ip"], "/light/color_led/turn_off")
        else:
            postRequest(light.protocol_cfg["ip"], "/light/white_led/turn_off")
        if "on" in data:
            if not(data['on']):
                request_data = request_data + "/turn_off"
            else:
                request_data = request_data + "/turn_on"
        else:
            request_data = request_data + "/turn_on"
        if light.protocol_cfg["esphome_model"] != "ESPHome-Toggle":
            if "bri" in data:
                brightness = int(data['bri'])
                if light.protocol_cfg["esphome_model"] == "ESPHome-RGBW":
                    if light.state["colormode"] == "ct":
                        brightness = ct_boost + brightness
                    elif light.state["colormode"] == "xy":
                        brightness = rgb_boost + brightness
                elif light.protocol_cfg["esphome_model"] == "ESPHome-CT":
                    brightness = ct_boost + brightness
                elif light.protocol_cfg["esphome_model"] == "ESPHome-RGB":
                    brightness = rgb_boost + brightness
                elif light.protocol_cfg["esphome_model"] == "ESPHome-Dimmable":
                    brightness = ct_boost + brightness
                if brightness > 255: # do not send brightness values over 255
                    brightness = 255
                request_data = addRequest(request_data, "brightness", brightness)
            if light.protocol_cfg["esphome_model"] in ["ESPHome-RGBW", "ESPHome-RGB", "ESPHome-CT"]:
                if ("xy" in data) and (light.protocol_cfg["esphome_model"] in ["ESPHome-RGBW", "ESPHome-RGB"]):
                    if rgb:
                        color = rgbBrightness(rgb, light.state["bri"])
                    else:
                        color = convert_xy(data['xy'][0], data['xy'][1], light.state["bri"])
                    request_data = addRequest(request_data, "r", color[0])
                    request_data = addRequest(request_data, "g", color[1])
                    request_data = addRequest(request_data, "b", color[2])
                elif "ct" in data and (light.protocol_cfg["esphome_model"] in ["ESPHome-RGBW", "ESPHome-CT"]):
                    request_data = addRequest(request_data, "color_temp", data['ct'])
                elif (("hue" in data) or ("sat" in data)) and (light.protocol_cfg["esphome_model"] in ["ESPHome-RGBW", "ESPHome-RGB"]):
                    if (("hue" in data) and ("sat" in data)):
                        hue = data['hue']
                        sat = data['sat']
                    elif "hue" in data:
                        hue = data['hue']
                        sat = light.state["sat"]
                    elif "sat" in data:
                        hue = light.state["hue"]
                        sat = data['sat']
                    if "bri" not in data:
                        bri = light.state["bri"]
                    else:
                        bri = data['bri']
                    color = hsv_to_rgb(hue, sat, bri)
                    request_data = addRequest(request_data, "r", color[0])
                    request_data = addRequest(request_data, "g", color[1])
                    request_data = addRequest(request_data, "b", color[2])
            if "transitiontime" in data:
                request_data = addRequest(request_data, "transition", data['transitiontime']/10)
            else: #Utilize default interval of 0.4
                request_data = addRequest(request_data, "transition", 0.4)

    postRequest(light.protocol_cfg["ip"], request_data)




def get_light_state(light):
    logging.debug("ESPHome: <get_light_state> invoked!")
    state = {}
    if light.protocol_cfg["esphome_model"] == "ESPHome-RGBW":
        white_response = requests.get ("http://" + light.protocol_cfg["ip"] + "/light/white_led", timeout=3)
        color_response = requests.get ("http://" + light.protocol_cfg["ip"] + "/light/color_led", timeout=3)
        white_device = white_response.json() #get white device data
        color_device = color_response.json() #get color device data
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

    elif light.protocol_cfg["esphome_model"] == "ESPHome-CT":
        white_response = requests.get ("http://" + light.protocol_cfg["ip"] + "/light/white_led", timeout=3)
        white_device = white_response.json() #get white device data
        if white_device['state'] == 'OFF':
            state['on'] = False
        elif white_device['state'] == 'ON':
            state['on'] = True
            state['ct'] = int(white_device['color_temp'])
            state['bri'] = int(white_device['brightness'])
            state['colormode'] = "ct"

    elif light.protocol_cfg["esphome_model"] == "ESPHome-RGB":
        color_response = requests.get ("http://" + light.protocol_cfg["ip"] + "/light/color_led", timeout=3)
        color_device = color_response.json()
        if color_device['state'] == 'OFF':
            state['on'] = False
        elif color_device['state'] == 'ON':
            state['on'] = True
            state['xy'] = convert_rgb_xy(int(color_device['color']['r']), int(color_device['color']['g']), int(color_device['color']['b']))
            state['bri'] = int(color_device['brightness'])
            state['colormode'] = "xy"

    elif light.protocol_cfg["esphome_model"] == "ESPHome-Dimmable":
        dimmable_response = requests.get ("http://" + light.protocol_cfg["ip"] + "/light/dimmable_led", timeout=3)
        dimmable_device = dimmable_response.json()
        if dimmable_device['state'] == 'OFF':
            state['on'] = False
        elif dimmable_device['state'] == 'ON':
            state['on'] = True
            state['bri'] = int(dimmable_device['brightness'])

    elif light.protocol_cfg["esphome_model"] == "ESPHome-Toggle":
        toggle_response = requests.get ("http://" + light.protocol_cfg["ip"] + "/light/toggle_led", timeout=3)
        toggle_device = toggle_response.json()
        if toggle_device['state'] == 'OFF':
            state['on'] = False
        elif toggle_device['state'] == 'ON':
            state['on'] = True
    return state
