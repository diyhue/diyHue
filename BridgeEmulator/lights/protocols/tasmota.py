import json
import logManager
import requests
from functions.colors import convert_rgb_xy, convert_xy, rgbBrightness

logging = logManager.logger.get_logger(__name__)

def sendRequest(url, timeout=3):

    head = {"Content-type": "application/json"}
    response = requests.get(url, timeout=timeout, headers=head)
    return response.text


def discover(detectedLights, device_ips):
    logging.debug("tasmota: <discover> invoked!")
    for ip in device_ips:
        try:
            logging.debug ( "tasmota: probing ip " + ip)
            response = requests.get ("http://" + ip + "/cm?cmnd=Status%200", timeout=3)
            if response.status_code == 200:
                device_data = response.json()
                #logging.debug(pretty_json(device_data))
                if ("StatusSTS" in device_data):

                    logging.debug("tasmota: " + ip + " is a Tasmota device ")
                    logging.debug ("tasmota: Hostname: " + device_data["StatusNET"]["Hostname"] )
                    logging.debug ("tasmota: Mac:      " + device_data["StatusNET"]["Mac"] )

                    properties = {"rgb": True, "ct": False, "ip": ip, "name": device_data["StatusNET"]["Hostname"], "id": device_data["StatusNET"]["Mac"], "mac": device_data["StatusNET"]["Mac"]}
                    detectedLights.append({"protocol": "tasmota", "name": device_data["StatusNET"]["Hostname"], "modelid": "LCT015", "protocol_cfg": {"ip": ip, "id": device_data["StatusNET"]["Mac"]}})

        except Exception as e:
            logging.debug("tasmota: ip " + ip + " is unknow device, " + str(e))


def set_light(light, data, rgb = None):
    logging.debug("tasmota: <set_light> invoked! IP=" + light.protocol_cfg["ip"])

    for key, value in data.items():
        logging.debug("tasmota: key " + key)

        if key == "on":
            if value:
                sendRequest ("http://"+light.protocol_cfg["ip"]+"/cm?cmnd=Power%20on")
            else:
                sendRequest ("http://"+light.protocol_cfg["ip"]+"/cm?cmnd=Power%20off")
        elif key == "bri":
            brightness = int(100.0 * (value / 254.0))
            sendRequest ("http://"+light.protocol_cfg["ip"]+"/cm?cmnd=Dimmer%20" + str(brightness))
        elif key == "ct":
            color = {}
        elif key == "xy":
            if rgb:
                color = rgbBrightness(rgb, light["state"]["bri"])
            else:
                color = convert_xy(value[0], value[1], light.state["bri"])
            sendRequest ("http://"+light.protocol_cfg["ip"]+"/cm?cmnd=Color%20" + str(color[0]) + "," + str(color[1]) + "," + str(color[2]))
        elif key == "alert":
                if value == "select":
                    sendRequest ("http://" + light.protocol_cfg["ip"] + "/cm?cmnd=dimmer%20100")


def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    tup = tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    return list(tup)


def rgb_to_hex(rgb):
    return '%02x%02x%02x' % rgb
    #return '#%02x%02x%02x' % rgb

def get_light_state(light):
    logging.debug("tasmota: <get_light_state> invoked!")
    data = sendRequest ("http://" + light.protocol_cfg["ip"] + "/cm?cmnd=Status%2011")
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
        #logging.debug(light_data["Color"])
        if "," in light_data["Color"]:
            # RGB
            rgb = light_data["Color"].split(",")
            state["xy"] = convert_rgb_xy(int(rgb[0],16), int(rgb[1],16), int(rgb[2],16))
        else:
            # HEX
            hex = light_data["Color"]
            rgb = hex_to_rgb(hex)
            state["xy"] = convert_rgb_xy(rgb[0],rgb[1],rgb[2])

        state["bri"] = int(light_data["Dimmer"] / 100.0 * 254.0)
        state["colormode"] = "xy"

    return state
