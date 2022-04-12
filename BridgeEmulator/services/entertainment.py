from time import sleep
import logManager
import configManager
import requests
import socket, json, uuid
from subprocess import Popen, PIPE
from functions.colors import convert_rgb_xy, convert_xy
import paho.mqtt.publish as publish
logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config

cieTolerance = 0.03 # new frames will be ignored if the color  change is smaller than this values
briTolerange = 16 # new frames will be ignored if the brightness change is smaller than this values
lastAppliedFrame = {}
YeelightConnections = {}

def skipSimilarFrames(light, color, brightness):
    if light not in lastAppliedFrame: # check if light exist in dictionary
        lastAppliedFrame[light] = {"xy": [0,0], "bri": 0}

    if lastAppliedFrame[light]["xy"][0] + cieTolerance < color[0] or color[0] < lastAppliedFrame[light]["xy"][0] - cieTolerance:
        lastAppliedFrame[light]["xy"] = color
        return 2
    if lastAppliedFrame[light]["xy"][1] + cieTolerance < color[1] or color[1] < lastAppliedFrame[light]["xy"][1] - cieTolerance:
        lastAppliedFrame[light]["xy"] = color
        return 2
    if lastAppliedFrame[light]["bri"] + briTolerange < brightness or brightness < lastAppliedFrame[light]["bri"] - briTolerange:
        lastAppliedFrame[light]["bri"] = brightness
        return 1
    return 0

def getObject(v2uuid):
    for key, obj in bridgeConfig["lights"].items():
        if str(uuid.uuid5(uuid.NAMESPACE_URL, obj.id_v2 + 'entertainment')) == v2uuid:
            return obj
    logging.info("element not found!")
    return False

def findGradientStrip(group):
    for light in group.lights:
        if light().modelid in ["LCX001", "LCX002", "LCX003", "915005987201", "LCX004"]:
            return light()
    return "not found"

def get_hue_entertainment_group(light, groupname):
    group = requests.get("http://" + light.protocol_cfg["ip"] + "/api/" + light.protocol_cfg["hueUser"] + "/groups/", timeout=3)
    #logging.debug("Returned Groups: " + group.text)
    groups = json.loads(group.text)
    out = -1
    for i, grp in groups.items():
        #logging.debug("Group "  + i + " has Name " + grp["name"] + " and type " + grp["type"])
        if (grp["name"] == groupname) and (grp["type"] == "Entertainment") and (light.protocol_cfg["id"] in grp["lights"]):
            out = i
            logging.debug("Found Corresponding entertainment group with id " + out + " for light " + light.name)
    return int(out)

YeelightConnections = {}

def entertainmentService(group, user):
    logging.debug("User: " + user.username)
    logging.debug("Key: " + user.client_key)
    lights_v2 = []
    lights_v1 = {}
    hueGroup  = -1
    hueGroupLights = {}
    for light in group.lights:
        lights_v1[int(light().id_v1)] = light()
        if light().protocol == "hue" and get_hue_entertainment_group(light(), group.name) != -1: # If the lights' Hue bridge has an entertainment group with the same name as this current group, we use it to sync the lights.
            hueGroup = get_hue_entertainment_group(light(), group.name)
            hueGroupLights[int(light().protocol_cfg["id"])] = [] # Add light id to list
        bridgeConfig["lights"][light().id_v1].state["mode"] = "streaming"
    v2LightNr = {}
    for channel in group.getV2Api()["channels"]:
        lightObj =  getObject(channel["members"][0]["service"]["rid"])
        if lightObj.id_v1 not in v2LightNr:
            v2LightNr[lightObj.id_v1] = 0
        else:
            v2LightNr[lightObj.id_v1] += 1
        lights_v2.append({"light": lightObj, "lightNr": v2LightNr[lightObj.id_v1]})
    logging.debug(lights_v1)
    logging.debug(lights_v2)
    opensslCmd = ['openssl', 's_server', '-dtls', '-psk', user.client_key, '-psk_identity', user.username, '-nocert', '-accept', '2100', '-quiet']
    p = Popen(opensslCmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    if hueGroup != -1:  # If we have found a hue Brige containing a suitable entertainment group for at least one Lamp, we connect to it
        h = HueConnection(bridgeConfig["config"]["hue"]["ip"])
        h.connect(hueGroup, hueGroupLights)
        if h._connected == False:
            hueGroupLights = {} # on a failed connection, empty the list

    init = False
    frameBites = 10
    fremeID = 1
    host_ip = bridgeConfig["config"]["ipaddress"]
    try:
        while bridgeConfig["groups"][group.id_v1].stream["active"]:
            if not init:
                line = p.stdout.read(200)
                logging.debug(",".join('{:02x}'.format(x) for x in line))
                frameBites = line[1:].find(b'\x48\x75\x65\x53\x74\x72\x65\x61\x6d') + 1
                logging.debug("frameBites: " + str(frameBites))
                if frameBites > 100:
                    p.stdout.read(frameBites - (200 - frameBites)) # sync streaming bytes
                elif frameBites > 67:
                    p.stdout.read(frameBites - (200 - frameBites * 2)) # sync streaming bytes
                else:
                    p.stdout.read(frameBites - (200 - frameBites * 3)) # sync streaming bytes
                init = True

            else:
                data = p.stdout.read(frameBites)
                logging.debug(",".join('{:02x}'.format(x) for x in data))
                nativeLights = {}
                esphomeLights = {}
                mqttLights = []
                wledLights = {}
                if data[:9].decode('utf-8') == "HueStream":
                    i = 0
                    apiVersion = 0
                    counter = 0
                    if data[9] == 1: #api version 1
                        i = 16
                        apiVersion = 1
                        counter = len(data)
                    elif data[9] == 2: #api version 1
                        i = 52
                        apiVersion = 2
                        counter = len(group.getV2Api()["channels"]) * 7 + 52
                    channels = {}
                    while (i < counter):
                        light = None
                        r,g,b = 0,0,0
                        if apiVersion == 1:
                            if (data[i+1] * 256 + data[i+2]) in channels:
                                channels[data[i+1] * 256 + data[i+2]] += 1
                            else:
                                channels[data[i+1] * 256 + data[i+2]] = 0
                            if data[i] == 0:  # Type of device 0x00 = Light
                                if data[i+1] * 256 + data[i+2] == 0:
                                    break
                                light = lights_v1[data[i+1] * 256 + data[i+2]]
                            elif data[i] == 1:  # Type of device Gradient Strip
                                light = findGradientStrip(group)
                            if data[14] == 0: #rgb colorspace
                                r = int((data[i+3] * 256 + data[i+4]) / 256)
                                g = int((data[i+5] * 256 + data[i+6]) / 256)
                                b = int((data[i+7] * 256 + data[i+8]) / 256)
                            elif data[14] == 1: #cie colorspace
                                x = (data[i+3] * 256 + data[i+4]) / 65535
                                y = (data[i+5] * 256 + data[i+6]) / 65535
                                bri = int((data[i+7] * 256 + data[i+8]) / 256)
                                r, g, b = convert_xy(x, y, bri)
                        elif apiVersion == 2:
                            light = lights_v2[data[i]]["light"]
                            if data[14] == 0: #rgb colorspace
                                r = int((data[i+1] * 256 + data[i+2]) / 256)
                                g = int((data[i+3] * 256 + data[i+4]) / 256)
                                b = int((data[i+5] * 256 + data[i+6]) / 256)
                            elif data[14] == 1: #cie colorspace
                                x = (data[i+1] * 256 + data[i+2]) / 65535
                                y = (data[i+3] * 256 + data[i+4]) / 65535
                                bri = int((data[i+5] * 256 + data[i+6]) / 256)
                                r, g, b = convert_xy(x, y, bri)
                        if light == None:
                            logging.info("error in light identification")
                            break
                        logging.debug("Light:" + str(light.name) + " RED: " + str(r) + ", GREEN: " + str(g) + ", BLUE: " + str(b) )
                        proto = light.protocol
                        if r == 0 and  g == 0 and  b == 0:
                            light.state["on"] = False
                        else:
                            light.state.update({"on": True, "bri": int((r + g + b) / 3), "xy": convert_rgb_xy(r, g, b), "colormode": "xy"})
                        if proto in ["native", "native_multi", "native_single"]:
                            if light.protocol_cfg["ip"] not in nativeLights:
                                nativeLights[light.protocol_cfg["ip"]] = {}
                            if apiVersion == 1:
                                if light.modelid in ["LCX001", "LCX002", "LCX003", "915005987201", "LCX004"]:
                                    if data[i] == 1: # individual strip address
                                        nativeLights[light.protocol_cfg["ip"]][data[i+1] * 256 + data[i+2]] = [r, g, b]
                                    elif data[i] == 0: # individual strip address
                                        for x in range(7):
                                            nativeLights[light.protocol_cfg["ip"]][x] = [r, g, b]
                                else:
                                    nativeLights[light.protocol_cfg["ip"]][light.protocol_cfg["light_nr"] - 1] = [r, g, b]

                            elif apiVersion == 2:
                                if light.modelid in ["LCX001", "LCX002", "LCX003", "915005987201", "LCX004"]:
                                    nativeLights[light.protocol_cfg["ip"]][lights_v2[data[i]]["lightNr"]] = [r, g, b]
                                else:
                                    nativeLights[light.protocol_cfg["ip"]][light.protocol_cfg["light_nr"] - 1] = [r, g, b]
                        elif proto == "esphome":
                            if light.protocol_cfg["ip"] not in esphomeLights:
                                esphomeLights[light.protocol_cfg["ip"]] = {}
                            bri = int(max(r,g,b))
                            esphomeLights[light.protocol_cfg["ip"]]["color"] = [r, g, b, bri]
                        elif proto == "mqtt":
                            operation = skipSimilarFrames(light.id_v1, light.state["xy"], light.state["bri"])
                            if operation == 1:
                                mqttLights.append({"topic": light.protocol_cfg["command_topic"], "payload": json.dumps({"brightness": light.state["bri"], "transition": 0.2})})
                            elif operation == 2:
                                mqttLights.append({"topic": light.protocol_cfg["command_topic"], "payload": json.dumps({"color": {"x": light.state["xy"][0], "y": light.state["xy"][1]}, "transition": 0.15})})
                        elif proto == "yeelight":
                            enableMusic(light.protocol_cfg["ip"], host_ip)
                            c = YeelightConnections[light.protocol_cfg["ip"]]
                            operation = skipSimilarFrames(light.id_v1, light.state["xy"], light.state["bri"])
                            if operation == 1:
                                c.command("set_bright", [int(light.state["bri"] / 2.55), "smooth", 200])
                                #c.command("set_bright", [int(bridgeConfig["lights"][str(lightId)]["state"]["bri"] / 2.55), "sudden", 0])

                            elif operation == 2:
                                c.command("set_rgb", [(r * 65536) + (g * 256) + b, "smooth", 200])
                                #c.command("set_rgb", [(r * 65536) + (g * 256) + b, "sudden", 0])
                        elif proto == "wled":
                            if light.protocol_cfg["ip"] not in wledLights:
                                wledLights[light.protocol_cfg["ip"]] = {}
                                wledLights[light.protocol_cfg["ip"]
                                           ]["ledCount"] = light.protocol_cfg["ledCount"]
                            wledLights[light.protocol_cfg["ip"]
                                       ]["color"] = [r, g, b]
                        elif proto == "hue" and int(light.protocol_cfg["id"]) in hueGroupLights:
                            hueGroupLights[int(light.protocol_cfg["id"])] = [r,g,b]
                        else:
                            if fremeID % 4 == 0: # can use 2, 4, 6, 8, 12 => increase in case the destination device is overloaded
                                operation = skipSimilarFrames(light.id_v1, light.state["xy"], light.state["bri"])
                                if operation == 1:
                                    light.setV1State({"bri": light.state["bri"], "transitiontime": 3})
                                elif operation == 2:
                                    light.setV1State({"xy": light.state["xy"], "transitiontime": 3})

                        fremeID += 1
                        if fremeID == 25:
                            fremeID = 1
                        if apiVersion == 1:
                            i = i + 9
                        elif  apiVersion == 2:
                            i = i + 7

                    if len(nativeLights) != 0:
                        for ip in nativeLights.keys():
                            udpmsg = bytearray()
                            for light in nativeLights[ip].keys():
                                udpmsg += bytes([light]) + bytes([nativeLights[ip][light][0]]) + bytes([nativeLights[ip][light][1]]) + bytes([nativeLights[ip][light][2]])
                            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
                            sock.sendto(udpmsg, (ip.split(":")[0], 2100))
                    if len(esphomeLights) != 0:
                        for ip in esphomeLights.keys():
                            udpmsg = bytearray()
                            udpmsg += bytes([0]) + bytes([esphomeLights[ip]["color"][0]]) + bytes([esphomeLights[ip]["color"][1]]) + bytes([esphomeLights[ip]["color"][2]]) + bytes([esphomeLights[ip]["color"][3]])
                            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
                            sock.sendto(udpmsg, (ip.split(":")[0], 2100))
                    if len(mqttLights) != 0:
                        auth = None
                        if bridgeConfig["config"]["mqtt"]["mqttUser"] != "" and bridgeConfig["config"]["mqtt"]["mqttPassword"] != "":
                            auth = {'username':bridgeConfig["config"]["mqtt"]["mqttUser"], 'password':bridgeConfig["config"]["mqtt"]["mqttPassword"]}
                        publish.multiple(mqttLights, hostname=bridgeConfig["config"]["mqtt"]["mqttServer"], port=bridgeConfig["config"]["mqtt"]["mqttPort"], auth=auth)
                    if len(wledLights) != 0:
                        wled_udpmode = 2
                        wled_secstowait = 2
                        for ip in wledLights.keys():
                            udphead = [wled_udpmode, wled_secstowait]
                            color = wledLights[ip]["color"] * int(wledLights[ip]["ledCount"])
                            udpdata = bytes(udphead+color)
                            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                            sock.sendto(udpdata, (ip, 21324))
                    if len(hueGroupLights) != 0:
                        h.send(hueGroupLights, hueGroup)
                else:
                    logging.info("HueStream was missing in the frame")
                    p.kill()
                    try:
                        h.disconnect()
                    except UnboundLocalError:
                        pass
    except Exception as e: #Assuming the only exception is a network timeout, please don't scream at me
        logging.info("Entertainment Service was syncing and has timed out, stopping server and clearing state" + str(e))

    p.kill()
    try:
        h.disconnect()
    except UnboundLocalError:
        pass
    bridgeConfig["groups"][group.id_v1].stream["active"] = False
    for light in group.lights:
         bridgeConfig["lights"][light().id_v1].state["mode"] = "homeautomation"
    logging.info("Entertainment service stopped")

def enableMusic(ip, host_ip):
    if ip in YeelightConnections:
        c = YeelightConnections[ip]
        if not c._music:
            c.enableMusic(host_ip)
    else:
        c = YeelightConnection(ip)
        YeelightConnections[ip] = c
        c.enableMusic(host_ip)

def disableMusic(ip):
    if ip in YeelightConnections: # Else? LOL
        YeelightConnections[ip].disableMusic()

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


class HueConnection(object):
    _connected = False
    _ip = ""
    _entGroup = -1
    _connection = ""
    _hueLights = []

    def __init__(self, ip):
        self._ip = ip

    def connect(self, hueGroup, *lights):
        self._entGroup = hueGroup
        self._hueLights = lights
        self.disconnect()

        url = "HTTP://" + str(self._ip) + "/api/" + bridgeConfig["config"]["hue"]["hueUser"] + "/groups/" + str(self._entGroup)
        r = requests.put(url, json={"stream":{"active":True}})
        logging.debug("Outgoing connection to hue Bridge returned: " + r.text)
        try:
            _opensslCmd = ['openssl', 's_client', '-quiet', '-cipher', 'PSK-AES128-GCM-SHA256', '-dtls', '-psk', bridgeConfig["config"]["hue"]["hueKey"], '-psk_identity', bridgeConfig["config"]["hue"]["hueUser"], '-connect', self._ip + ':2100']
            self._connection = Popen(_opensslCmd, stdin=PIPE, stdout=None, stderr=None) # Open a dtls connection to the Hue bridge
            self._connected = True
            sleep(1) # Wait a bit to catch errors
            err = self._connection.poll()
            if err != None:
                raise ConnectionError(err)
        except Exception as e:
            logging.info("Error connecting to Hue bridge for entertainment. Is a proper hueKey set? openssl connection returned: %s", e)
            self.disconnect()

    def disconnect(self):
        try:
            url = "HTTP://" + str(self._ip) + "/api/" + bridgeConfig["config"]["hue"]["hueUser"] + "/groups/" + str(self._entGroup)
            if self._connected:
                self._connection.kill()
            requests.put(url, data={"stream":{"active":False}})
            self._connected = False
        except:
            pass

    def send(self, lights, hueGroup):
        arr = bytearray("HueStream", 'ascii')
        msg = [
                1, 0,     #Api version
                0,        #Sequence number, not needed
                0, 0,     #Zeroes
                0,        #0: RGB Color space, 1: XY Brightness
                0,        #Zero
              ]
        for id in lights:
            r, g, b = lights[id]
            msg.extend([    0,      #Type: Light
                            0, id,  #Light id (v1-type), 16 Bit
                            r, r,   #Red (or X) as 16 (2 * 8) bit value
                            g, g,   #Green (or Y)
                            b, b,   #Blue (or Brightness)
                            ])
        arr.extend(msg)
        logging.debug("Outgoing data to other Hue Bridge: " + arr.hex(','))
        try:
            self._connection.stdin.write(arr)
            self._connection.stdin.flush()
        except:
            logging.debug("Reconnecting to Hue bridge to sync. This is normal.") #Reconnect if the connection timed out
            self.disconnect()
            self.connect(hueGroup)
