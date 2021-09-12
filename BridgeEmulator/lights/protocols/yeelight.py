import json
import random
import socket
import logManager
#import configManager
from functions.colors import convert_rgb_xy, convert_xy, rgbBrightness


logging = logManager.logger.get_logger(__name__)
Connections = {}


def discover(detectedLights):
    group = ("239.255.255.250", 1982)
    message = "\r\n".join([
        'M-SEARCH * HTTP/1.1',
        'HOST: 239.255.255.250:1982',
        'MAN: "ssdp:discover"',
        'ST: wifi_bulb'])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(5)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.sendto(message.encode(), group)
    while True:
        try:
            response = sock.recv(1024).decode('utf-8').split("\r\n")
            logging.debug(response)
            properties = {"rgb": False, "ct": False}
            for line in response:
                logging.info(line)
                #logging.info("line check: " + line)
                if line[:2] == "id":
                    properties["id"] = line[4:]
                elif line[:3] == "rgb":
                    properties["rgb"] = True
                elif line[:2] == "ct":
                    properties["ct"] = True
                elif line[:8] == "Location":
                    properties["ip"] = line.split(":")[2][2:]
                elif line[:4] == "name":
                    properties["name"] = line[6:]
                elif line[:5] == "model":
                    properties["model"] = line.split(": ",1)[1]

            lightName = "Yeelight " + properties["model"] + " " + properties["ip"][-3:] if properties["name"] == "" else properties["name"] #just for me :)
            logging.info("Found YeeLight: " + properties["id"])
            modelid = "LWB010"
            if properties["model"] == "desklamp":
                modelid = "LTW001"
            elif properties["model"] in ["ceiling10", "ceiling20", "ceiling4"]:
                detectedLights.append({"protocol": "yeelight", "name": lightName + '-bg', "modelid": "LCT015", "protocol_cfg": {"ip": properties["ip"], "id": properties["id"] + "bg", "backlight": True, "model": properties["model"]}})
                modelid = "LWB010" # second light must be CT only
            elif properties["rgb"]:
                modelid = "LCT015"
            elif properties["ct"]:
                modelid = "LTW001"
            detectedLights.append({"protocol": "yeelight", "name": lightName, "modelid": modelid, "protocol_cfg": {"ip": properties["ip"], "id": properties["id"], "backlight": False, "model": properties["model"]}})

        except socket.timeout:
            logging.debug('Yeelight search end')
            sock.close()
            break

    return detectedLights

def command(ip, light, api_method, param):
    if ip in Connections:
        c = Connections[ip]
    else:
        c = YeelightConnection(ip)
        Connections[ip] = c
    try:
        c.command(api_method, param)
    finally:
        if not c._music and c._connected:
            c.disconnect()

def set_light(light, data):
    ip = light.protocol_cfg["ip"]
    if ip in Connections:
        c = Connections[ip]
    else:
        c = YeelightConnection(ip)
        Connections[ip] = c

    method = 'TCP'
    payload = {}
    transitiontime = 400
    cmdPrefix = ''
    if "backlight" in light.protocol_cfg and light.protocol_cfg["backlight"]:
        cmdPrefix = "bg_"
    if "transitiontime" in data:
        transitiontime = int(data["transitiontime"] * 100)
    for key, value in data.items():
        if key == "on":
            if value:
                payload[cmdPrefix + "set_power"] = ["on", "smooth", transitiontime]
            else:
                payload[cmdPrefix + "set_power"] = ["off", "smooth", transitiontime]
        elif key == "bri":
            payload[cmdPrefix + "set_bright"] = [int(value / 2.55) + 1, "smooth", transitiontime]
        elif key == "ct":
            #if ip[:-3] == "201" or ip[:-3] == "202":
            if light.name.find("desklamp") > 0:
                if value > 369: value = 369
            payload[cmdPrefix + "set_ct_abx"] = [int((-4800/347) * value + 2989900/347), "smooth", transitiontime]
        elif key == "hue":
            payload[cmdPrefix + "set_hsv"] = [int(value / 182), int(light.state["sat"] / 2.54), "smooth", transitiontime]
        elif key == "sat":
            payload[cmdPrefix + "set_hsv"] = [int(light.state["hue"] / 182), int(value / 2.54), "smooth", transitiontime]
        elif key == "xy":
            color = convert_xy(value[0], value[1], light.state["bri"])
            payload[cmdPrefix + "set_rgb"] = [(color[0] * 65536) + (color[1] * 256) + color[2], "smooth", transitiontime] #according to docs, yeelight needs this to set rgb. its r * 65536 + g * 256 + b
        elif key == "alert" and value != "none":
            payload[cmdPrefix + "start_cf"] = [ 4, 0, "1000, 2, 5500, 100, 1000, 2, 5500, 1, 1000, 2, 5500, 100, 1000, 2, 5500, 1"]

    # yeelight uses different functions for each action, so it has to check for each function
    # see page 9 http://www.yeelight.com/download/Yeelight_Inter-Operation_Spec.pdf
    # check if hue wants to change brightness
    for key, value in payload.items():
        try:
            c.command(key, value)
        except Exception as e:
            if not c._music and c._connected:
                c.disconnect()
            raise e
    if not c._music and c._connected:
        c.disconnect()

def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    tup = tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    return list(tup)

def data_to_result(data):
    return json.loads(data[:-2].decode("utf8"))["result"]

def get_prop_data(tcp_socket, params):
    params = list(params)
    msg_dict = {"id": 1, "method": "get_prop", "params": params}
    msg=json.dumps(msg_dict) + "\r\n"
    tcp_socket.send(msg.encode())
    data = tcp_socket.recv(16 * 1024)
    return data

def calculate_color_temp(value):
    return int(-(347/4800) * int(value) +(2989900/4800))

def get_light_state(light):
    state = {}
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.settimeout(5)
    tcp_socket.connect((light.protocol_cfg["ip"], int(55443)))
    data = get_prop_data(tcp_socket, ["power", "bright"])
    light_data = data_to_result(data)
    if light_data[0] == "on": #powerstate
        state['on'] = True
    else:
        state['on'] = False
    state["bri"] = int(int(light_data[1]) * 2.54)
    #if ip[:-3] == "201" or ip[:-3] == "202":
    if light.name.find("desklamp") > 0:
        data = get_prop_data(tcp_socket, ["ct"])
        tempval = calculate_color_temp(data_to_result(data)[0])
        state["ct"] = min(tempval, 369)
        state["colormode"] = "ct"
    else:
        data = get_prop_data(tcp_socket, ["color_mode"])
        light_mode = data_to_result(data)[0]
        if light_mode == "1": #rgb mode
            data = get_prop_data(tcp_socket, ["rgb"])
            hue_data = data_to_result(data)
            hex_rgb = "%06x" % int(data_to_result(data)[0])
            rgb=hex_to_rgb(hex_rgb)
            state["xy"] = convert_rgb_xy(rgb[0],rgb[1],rgb[2])
            state["colormode"] = "xy"
        elif light_mode == "2": #ct mode
            data = get_prop_data(tcp_socket, ["ct"])
            state["ct"] =  calculate_color_temp(data_to_result(data)[0])
            state["colormode"] = "ct"
        elif light_mode == "3": #hs mode
            data = get_prop_data(tcp_socket, ["hue", "sat"])
            hue_data = data_to_result(data)
            state["hue"] = int(int(hue_data[0]) * 182)
            state["sat"] = int(int(hue_data[1]) * 2.54)
            state["colormode"] = "hs"
    tcp_socket.close()
    return state


class YeelightConnection(object):
    _music = False
    _connected = False
    _socket = None
    _host_ip = ""

    def __init__(self, ip):
        self._ip = ip

    def connect(self, simple = True): #Use simple when you don't need to reconnect music mode
        self.disconnect() #To clean old socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(5)
        self._socket.connect((self._ip, int(55443)))
        self._connected = True

    def disconnect(self):
        self._connected = False
        if self._socket:
            self._socket.close()
        self._socket = None


    def send(self, data: bytes, flags: int = 0):
        try:
            if not self._connected:
                self.connect()
            self._socket.send(data, flags)
        except Exception as e:
            self._connected = False
            raise e

    def recv(self, bufsize: int, flags: int = 0) -> bytes:
        try:
            if not self._connected:
                self.connect()
            return self._socket.recv(bufsize, flags)
        except Exception as e:
            self._connected = False
            raise e

    def command(self, api_method, param):
        try:
            msg = json.dumps({"id": 1, "method": api_method, "params": param}) + "\r\n"
            self.send(msg.encode())
        except Exception as e:
            logging.warning("Yeelight command error: %s", e)
