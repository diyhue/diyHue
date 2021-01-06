import logManager
import configManager
import socket, json
from subprocess import Popen
from functions.colors import convert_rgb_xy, convert_xy
from lights.manage import sendLightRequest
import paho.mqtt.publish as publish

logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.json_config

cieTolerance = 0.03 # new frames will be ignored if the color  change is smaller than this values
briTolerange = 16 # new frames will be ignored if the brightness change is smaller than this values
lastAppliedFrame = {}

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

Connections = {}

def entertainmentService():
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSocket.settimeout(3) #Set a packet timeout that we catch later
    serverSocket.bind(('127.0.0.1', 2101))
    fremeID = 1
    lightStatus = {}
    syncing = False #Flag to check whether or not we had been syncing when a timeout occurs
    while True:
        try:
            data = serverSocket.recvfrom(106)[0]
            nativeLights = {}
            esphomeLights = {}
            mqttLights = []
            if data[:9].decode('utf-8') == "HueStream":
                syncing = True #Set sync flag when receiving valid data
                i = 0
                apiVersion = 0
                entertainmentGroup = 0
                if data[9] == 1: #api version 1
                    i = 16
                    apiVersion = 1
                elif data[9] == 2: #api version 1
                    i = 52
                    apiVersion = 2
                    entertainmentGroup = bridgeConfig["emulator"]["links"]["v2"]["entertainment_configuration"][data[16:52].decode('utf-8')]["id_v1"]
                if data[14] == 0: #rgb colorspace
                    while (apiVersion == 1 and i < len(data)) or (apiVersion == 2 and len(bridgeConfig["groups"][entertainmentGroup]["lights"]) * 7 + 52 > i):
                        #if True: # data[i] == 0: #Type of device 0x00 = Light
                        lightId = 0
                        if apiVersion == 1:
                            lightId = data[i+1] * 256 + data[i+2]
                            if lightId != 0:
                                r = int((data[i+3] * 256 + data[i+4]) / 256)
                                g = int((data[i+5] * 256 + data[i+6]) / 256)
                                b = int((data[i+7] * 256 + data[i+8]) / 256)
                        elif apiVersion == 2:
                            lightId = bridgeConfig["groups"][entertainmentGroup]["lights"][data[i]]
                            r = int((data[i+1] * 256 + data[i+2]) / 256)
                            g = int((data[i+3] * 256 + data[i+4]) / 256)
                            b = int((data[i+5] * 256 + data[i+6]) / 256)
                        if lightId != 0:
                            #print("Light:" + str(lightId) + " RED: " + str(r) + ", GREEN: " + str(g) + "BLUE: " + str(b) )
                            proto = bridgeConfig["emulator"]["lights"][str(lightId)]["protocol"]
                            if lightId not in lightStatus:
                                lightStatus[lightId] = {"on": False, "bri": 1}
                            if r == 0 and  g == 0 and  b == 0:
                                bridgeConfig["lights"][str(lightId)]["state"]["on"] = False
                            else:
                                bridgeConfig["lights"][str(lightId)]["state"].update({"on": True, "bri": int((r + g + b) / 3), "xy": convert_rgb_xy(r, g, b), "colormode": "xy"})
                            if proto in ["native", "native_multi", "native_single"]:
                                if bridgeConfig["emulator"]["lights"][str(lightId)]["ip"] not in nativeLights:
                                    nativeLights[bridgeConfig["emulator"]["lights"][str(lightId)]["ip"]] = {}
                                nativeLights[bridgeConfig["emulator"]["lights"][str(lightId)]["ip"]][bridgeConfig["emulator"]["lights"][str(lightId)]["light_nr"] - 1] = [r, g, b]
                            elif proto == "esphome":
                                if bridgeConfig["emulator"]["lights"][str(lightId)]["ip"] not in esphomeLights:
                                    esphomeLights[bridgeConfig["emulator"]["lights"][str(lightId)]["ip"]] = {}
                                bri = int(max(r,g,b))
                                esphomeLights[bridgeConfig["emulator"]["lights"][str(lightId)]["ip"]]["color"] = [r, g, b, bri]
                            elif proto == "mqtt":
                                operation = skipSimilarFrames(lightId, bridgeConfig["lights"][str(lightId)]["state"]["xy"], bridgeConfig["lights"][str(lightId)]["state"]["bri"])
                                if operation == 1:
                                    mqttLights.append({"topic": bridgeConfig["emulator"]["lights"][str(lightId)]["command_topic"], "payload": json.dumps({"brightness": bridgeConfig["lights"][str(lightId)]["state"]["bri"], "transition": 0.2})})
                                elif operation == 2:
                                    mqttLights.append({"topic": bridgeConfig["emulator"]["lights"][str(lightId)]["command_topic"], "payload": json.dumps({"color": {"x": bridgeConfig["lights"][str(lightId)]["state"]["xy"][0], "y": bridgeConfig["lights"][str(lightId)]["state"]["xy"][1]}, "transition": 0.15})})
                            elif proto == "yeelight":
                                operation = skipSimilarFrames(lightId, bridgeConfig["lights"][str(lightId)]["state"]["xy"], bridgeConfig["lights"][str(lightId)]["state"]["bri"])
                                if operation != 0:
                                    sendLightRequest(str(lightId), {"xy": bridgeConfig["lights"][str(lightId)]["state"]["xy"], "transitiontime": 3}, [r, g, b])

                            else:
                                if fremeID % 4 == 0: # can use 2, 4, 6, 8, 12 => increase in case the destination device is overloaded
                                    if r == 0 and  g == 0 and  b == 0:
                                        if lightStatus[lightId]["on"]:
                                            sendLightRequest(str(lightId), {"on": False, "transitiontime": 3}, bridgeConfig["lights"], bridgeConfig["emulator"]["lights"], None, host_ip)
                                            lightStatus[lightId]["on"] = False
                                    elif lightStatus[lightId]["on"] == False:
                                        sendLightRequest(str(lightId), {"on": True, "transitiontime": 3}, bridgeConfig["lights"], bridgeConfig["emulator"]["lights"], None, host_ip)
                                        lightStatus[lightId]["on"] = True
                                    operation = skipSimilarFrames(lightId, bridgeConfig["lights"][str(lightId)]["state"]["xy"], bridgeConfig["lights"][str(lightId)]["state"]["bri"])
                                    if operation == 1:
                                        sendLightRequest(str(lightId), {"bri": bridgeConfig["lights"][str(lightId)]["state"]["bri"], "transitiontime": 3}, bridgeConfig["lights"], bridgeConfig["emulator"]["lights"], None, host_ip)
                                    elif operation == 2:
                                        sendLightRequest(str(lightId), {"xy": bridgeConfig["lights"][str(lightId)]["state"]["xy"], "transitiontime": 3}, bridgeConfig["lights"], bridgeConfig["emulator"]["lights"])

                            fremeID += 1
                            if fremeID == 25:
                                fremeID = 1
                        if apiVersion == 1:
                            i = i + 9
                        elif  apiVersion == 2:
                            i = i + 7
                elif data[14] == 1: #cie colorspace
                    i = 16
                    while i < len(data):
                        if data[i] == 0: #Type of device 0x00 = Light
                            lightId = data[i+1] * 256 + data[i+2]
                            if lightId != 0:
                                x = (data[i+3] * 256 + data[i+4]) / 65535
                                y = (data[i+5] * 256 + data[i+6]) / 65535
                                bri = int((data[i+7] * 256 + data[i+8]) / 256)
                                if bri == 0:
                                    bridgeConfig["lights"][str(lightId)]["state"]["on"] = False
                                else:
                                    bridgeConfig["lights"][str(lightId)]["state"].update({"on": True, "bri": bri, "xy": [x,y], "colormode": "xy"})
                                if bridgeConfig["emulator"]["lights"][str(lightId)]["protocol"] in ["native", "native_multi", "native_single"]:
                                    if bridgeConfig["emulator"]["lights"][str(lightId)]["ip"] not in nativeLights:
                                        nativeLights[bridgeConfig["emulator"]["lights"][str(lightId)]["ip"]] = {}
                                    nativeLights[bridgeConfig["emulator"]["lights"][str(lightId)]["ip"]][bridgeConfig["emulator"]["lights"][str(lightId)]["light_nr"] - 1] = convert_xy(x, y, bri)
                                elif bridgeConfig["emulator"]["lights"][str(lightId)]["protocol"] == "esphome":
                                    if bridgeConfig["emulator"]["lights"][str(lightId)]["ip"] not in esphomeLights:
                                        esphomeLights[bridgeConfig["emulator"]["lights"][str(lightId)]["ip"]] = {}
                                    r, g, b = convert_xy(x, y, bri)
                                    esphomeLights[bridgeConfig["emulator"]["lights"][str(lightId)]["ip"]]["color"] = [r, g, b, bri]
                                elif bridgeConfig["emulator"]["lights"][str(lightId)]["protocol"] == "mqtt":
                                    operation = skipSimilarFrames(lightId, [x,y], bri)
                                    if operation == 1:
                                        mqttLights.append({"topic": bridgeConfig["emulator"]["lights"][str(lightId)]["command_topic"], "payload": json.dumps({"brightness": bri, "transition": 0.2})})
                                    elif operation == 2:
                                        mqttLights.append({"topic": bridgeConfig["emulator"]["lights"][str(lightId)]["command_topic"], "payload": json.dumps({"color": {"x": x, "y": y}, "transition": 0.15})})
                                else:
                                    fremeID += 1
                                    if fremeID % 4 == 0: # can use 2, 4, 6, 8, 12 => increase in case the destination device is overloaded
                                        operation = skipSimilarFrames(lightId, [x,y], bri)
                                        if operation == 1:
                                            sendLightRequest(str(lightId), {"bri": bri, "transitiontime": 3}, bridgeConfig["lights"], bridgeConfig["emulator"]["lights"])
                                        elif operation == 2:
                                            sendLightRequest(str(lightId), {"xy": [x,y], "transitiontime": 3}, bridgeConfig["lights"], bridgeConfig["emulator"]["lights"])
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
                if bridgeConfig["emulator"]["mqtt"]["mqttUser"] != "" and bridgeConfig["emulator"]["mqtt"]["mqttPassword"] != "":
                    auth = {'username':bridgeConfig["emulator"]["mqtt"]["mqttUser"], 'password':bridgeConfig["emulator"]["mqtt"]["mqttPassword"]}
                publish.multiple(mqttLights, hostname=bridgeConfig["emulator"]["mqtt"]["mqttServer"], port=bridgeConfig["emulator"]["mqtt"]["mqttPort"], auth=auth)
        except Exception as e: #Assuming the only exception is a network timeout, please don't scream at me
            if syncing: #Reset sync status and kill relay service
                logging.info("Entertainment Service was syncing and has timed out, stopping server and clearing state" + str(e))
                #Popen(["killall", "entertain-srv"])
                #for group in bridgeConfig["groups"].keys():
                #    if "type" in bridgeConfig["groups"][group] and bridgeConfig["groups"][group]["type"] == "Entertainment":
                #        bridgeConfig["groups"][group]["stream"].update({"active": False, "owner": None})
                syncing = False



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
