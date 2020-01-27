import json
import logging
import random
import socket
import sys

from functions import light_types, nextFreeId
from functions.colors import convert_rgb_xy, convert_xy, rgbBrightness

Connections = {}

def discover(bridge_config, new_lights):
    group = ("239.255.255.250", 1982)
    message = "\r\n".join([
        'M-SEARCH * HTTP/1.1',
        'HOST: 239.255.255.250:1982',
        'MAN: "ssdp:discover"',
        'ST: wifi_bulb'])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(3)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.sendto(message.encode(), group)
    while True:
        try:
            response = sock.recv(1024).decode('utf-8').split("\r\n")
            properties = {"rgb": False, "ct": False}
            for line in response:
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
            device_exist = False
            for light in bridge_config["lights_address"].keys():
                if bridge_config["lights_address"][light]["protocol"] == "yeelight" and  bridge_config["lights_address"][light]["id"] == properties["id"]:
                    device_exist = True
                    bridge_config["lights_address"][light]["ip"] = properties["ip"]
                    logging.debug("light id " + properties["id"] + " already exist, updating ip...")
                    break
            if (not device_exist):
                #light_name = "YeeLight id " + properties["id"][-8:] if properties["name"] == "" else properties["name"]
                light_name = "Yeelight " + properties["model"] + " " + properties["ip"][-3:] if properties["name"] == "" else properties["name"] #just for me :)
                logging.debug("Add YeeLight: " + properties["id"])
                modelid = "LWB010"
                if properties["model"] == "desklamp":
                    modelid = "LTW001"
                elif properties["rgb"]:
                    modelid = "LCT015"
                elif properties["ct"]:
                    modelid = "LTW001"
                new_light_id = nextFreeId(bridge_config, "lights")
                bridge_config["lights"][new_light_id] = {"state": light_types[modelid]["state"], "type": light_types[modelid]["type"], "name": light_name, "uniqueid": "4a:e0:ad:7f:cf:" + str(random.randrange(0, 99)) + "-1", "modelid": modelid, "manufacturername": "Philips", "swversion": light_types[modelid]["swversion"]}
                new_lights.update({new_light_id: {"name": light_name}})
                bridge_config["lights_address"][new_light_id] = {"ip": properties["ip"], "id": properties["id"], "protocol": "yeelight"}


        except socket.timeout:
            logging.debug('Yeelight search end')
            sock.close()
            break

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

def set_light(address, light, data, rgb = None):
    ip = address["ip"]
    if ip in Connections:
        c = Connections[ip]
    else:
        c = YeelightConnection(ip)
        Connections[ip] = c

    method = 'TCP'
    payload = {}
    transitiontime = 400
    if "transitiontime" in data:
        transitiontime = int(data["transitiontime"] * 100)
    for key, value in data.items():
        if key == "on":
            if value:
                payload["set_power"] = ["on", "smooth", transitiontime]
            else:
                payload["set_power"] = ["off", "smooth", transitiontime]
        elif key == "bri":
            payload["set_bright"] = [int(value / 2.55) + 1, "smooth", transitiontime]
        elif key == "ct":
            #if ip[:-3] == "201" or ip[:-3] == "202":
            if light["name"].find("desklamp") > 0:
                if value > 369: value = 369
            payload["set_ct_abx"] = [int((-4800/347) * value + 2989900/347), "smooth", transitiontime]
        elif key == "hue":
            payload["set_hsv"] = [int(value / 182), int(light["state"]["sat"] / 2.54), "smooth", transitiontime]
        elif key == "sat":
            payload["set_hsv"] = [int(light["state"]["hue"] / 182), int(value / 2.54), "smooth", transitiontime]
        elif key == "xy":
            bri = light["state"]["bri"]
            if rgb:
                color = rgbBrightness(rgb, bri)
            else:
                color = convert_xy(value[0], value[1], bri)
            payload["set_rgb"] = [(color[0] * 65536) + (color[1] * 256) + color[2], "smooth", transitiontime] #according to docs, yeelight needs this to set rgb. its r * 65536 + g * 256 + b
        elif key == "alert" and value != "none":
            payload["start_cf"] = [ 4, 0, "1000, 2, 5500, 100, 1000, 2, 5500, 1, 1000, 2, 5500, 100, 1000, 2, 5500, 1"]

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

def get_light_state(address, light):
    #logging.info("name is: " + light["name"])
    #if light["name"].find("desklamp") > 0: logging.info("is desk lamp")
    state = {}
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.settimeout(5)
    tcp_socket.connect((address["ip"], int(55443)))
    msg=json.dumps({"id": 1, "method": "get_prop", "params":["power","bright"]}) + "\r\n"
    tcp_socket.send(msg.encode())
    data = tcp_socket.recv(16 * 1024)
    light_data = json.loads(data[:-2].decode("utf8"))["result"]
    if light_data[0] == "on": #powerstate
        state['on'] = True
    else:
        state['on'] = False
    state["bri"] = int(int(light_data[1]) * 2.54)
    #if ip[:-3] == "201" or ip[:-3] == "202":
    if light["name"].find("desklamp") > 0:
        msg_ct=json.dumps({"id": 1, "method": "get_prop", "params":["ct"]}) + "\r\n"
        tcp_socket.send(msg_ct.encode())
        data = tcp_socket.recv(16 * 1024)
        tempval = int(-(347/4800) * int(json.loads(data[:-2].decode("utf8"))["result"][0]) +(2989900/4800))
        if tempval > 369: tempval = 369
        state["ct"] = tempval # int(-(347/4800) * int(json.loads(data[:-2].decode("utf8"))["result"][0]) +(2989900/4800))
        state["colormode"] = "ct"
    else:
        msg_mode=json.dumps({"id": 1, "method": "get_prop", "params":["color_mode"]}) + "\r\n"
        tcp_socket.send(msg_mode.encode())
        data = tcp_socket.recv(16 * 1024)
        if json.loads(data[:-2].decode("utf8"))["result"][0] == "1": #rgb mode
            msg_rgb=json.dumps({"id": 1, "method": "get_prop", "params":["rgb"]}) + "\r\n"
            tcp_socket.send(msg_rgb.encode())
            data = tcp_socket.recv(16 * 1024)
            hue_data = json.loads(data[:-2].decode("utf8"))["result"]
            hex_rgb = "%6x" % int(json.loads(data[:-2].decode("utf8"))["result"][0])
            r = hex_rgb[:2]
            if r == "  ":
                r = "00"
            g = hex_rgb[3:4]
            if g == "  ":
                g = "00"
            b = hex_rgb[-2:]
            if b == "  ":
                b = "00"
            state["xy"] = convert_rgb_xy(int(r,16), int(g,16), int(b,16))
            state["colormode"] = "xy"
        elif json.loads(data[:-2].decode("utf8"))["result"][0] == "2": #ct mode
            msg_ct=json.dumps({"id": 1, "method": "get_prop", "params":["ct"]}) + "\r\n"
            tcp_socket.send(msg_ct.encode())
            data = tcp_socket.recv(16 * 1024)
            state["ct"] =  int(-(347/4800) * int(json.loads(data[:-2].decode("utf8"))["result"][0]) +(2989900/4800))
            state["colormode"] = "ct"
        elif json.loads(data[:-2].decode("utf8"))["result"][0] == "3": #hs mode
            msg_hsv=json.dumps({"id": 1, "method": "get_prop", "params":["hue","sat"]}) + "\r\n"
            tcp_socket.send(msg_hsv.encode())
            data = tcp_socket.recv(16 * 1024)
            hue_data = json.loads(data[:-2].decode("utf8"))["result"]
            state["hue"] = int(int(hue_data[0]) * 182)
            state["sat"] = int(int(hue_data[1]) * 2.54)
            state["colormode"] = "hs"
    tcp_socket.close()
    return state

def enableMusic(ip, host_ip):
    if ip in Connections:
        c = Connections[ip]
        if not c._music:
            c.enableMusic(host_ip)
    else:
        c = YeelightConnection(ip)
        Connections[ip] = c
        c.enableMusic(host_ip)

def disableMusic(ip):
    if ip in Connections: # Else? LOL
        Connections[ip].disableMusic()

class YeelightConnection(object):
    _music = False
    _connected = False
    _socket = None
    _host_ip = ""

    def __init__(self, ip):
        self._ip = ip

    def connect(self, simple = False): #Use simple when you don't need to reconnect music mode
        self.disconnect() #To clean old socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.settimeout(5)
        self._socket.connect((self._ip, int(55443)))
        if not simple and self._music:
            self.enableMusic(self._host_ip)
        else:
            self._connected = True

    def disconnect(self):
        self._connected = False
        if self._socket:
            self._socket.close()
        self._socket = None

    def enableMusic(self, host_ip):
        if self._connected and self._music:
            raise AssertionError("Already in music mode!")

        self._host_ip = host_ip

        tempSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Setup listener
        tempSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tempSock.settimeout(5)

        tempSock.bind(("", 0))
        port = tempSock.getsockname()[1] #Get listener port

        tempSock.listen(3)

        if not self._connected:
            self.connect(True) #Basic connect for set_music

        self.command("set_music", [1, host_ip, port]) #MAGIC
        self.disconnect() #Disconnect from basic mode

        while 1:
            try:
                conn, addr = tempSock.accept()
                if addr[0] == self._ip: #Ignore wrong connections
                    tempSock.close() #Close listener
                    self._socket = conn #Replace socket with music one
                    self._connected = True
                    self._music = True
                    break
                else:
                    try:
                        logging.info("Rejecting connection to the music mode listener from %s", self._ip)
                        conn.close()
                    except:
                        pass
            except Exception as e:
                tempSock.close()
                raise ConnectionError("Yeelight with IP {} doesn't want to connect in music mode: {}".format(self._ip, e))
        
        logging.info("Yeelight device with IP %s is now in music mode", self._ip)

    def disableMusic(self):
        if not self._music:
            return

        if self._socket:
            self._socket.close()
            self._socket = None
        self._music = False
        logging.info("Yeelight device with IP %s is no longer using music mode", self._ip)

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