import socket, logging, json
from subprocess import Popen
from functions.colors import convert_rgb_xy, convert_xy
from functions.lightRequest import sendLightRequest
import paho.mqtt.publish as publish
import Globals


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


def entertainmentService(lights, addresses, groups, emulator):
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
                if data[14] == 0: #rgb colorspace
                    i = 16
                    while i < len(data):
                        if data[i] == 0: #Type of device 0x00 = Light
                            lightId = data[i+1] * 256 + data[i+2]
                            if lightId != 0:
                                r = int((data[i+3] * 256 + data[i+4]) / 256)
                                g = int((data[i+5] * 256 + data[i+6]) / 256)
                                b = int((data[i+7] * 256 + data[i+8]) / 256)
                                proto = addresses[str(lightId)]["protocol"]
                                if lightId not in lightStatus:
                                    lightStatus[lightId] = {"on": False, "bri": 1}
                                if r == 0 and  g == 0 and  b == 0:
                                    lights[str(lightId)]["state"]["on"] = False
                                else:
                                    lights[str(lightId)]["state"].update({"on": True, "bri": int((r + g + b) / 3), "xy": convert_rgb_xy(r, g, b), "colormode": "xy"})
                                if proto in ["native", "native_multi", "native_single"]:
                                    if addresses[str(lightId)]["ip"] not in nativeLights:
                                        nativeLights[addresses[str(lightId)]["ip"]] = {}
                                    nativeLights[addresses[str(lightId)]["ip"]][addresses[str(lightId)]["light_nr"] - 1] = [r, g, b]
                                elif proto == "esphome":
                                    if addresses[str(lightId)]["ip"] not in esphomeLights:
                                        esphomeLights[addresses[str(lightId)]["ip"]] = {}
                                    bri = int(max(r,g,b))
                                    esphomeLights[addresses[str(lightId)]["ip"]]["color"] = [r, g, b, bri]
                                elif proto == "mqtt":
                                    operation = skipSimilarFrames(lightId, lights[str(lightId)]["state"]["xy"], lights[str(lightId)]["state"]["bri"])
                                    if operation == 1:
                                        mqttLights.append({"topic": addresses[str(lightId)]["command_topic"], "payload": json.dumps({"brightness": lights[str(lightId)]["state"]["bri"], "transition": 0.2})})
                                    elif operation == 2:
                                        mqttLights.append({"topic": addresses[str(lightId)]["command_topic"], "payload": json.dumps({"color": {"x": lights[str(lightId)]["state"]["xy"][0], "y": lights[str(lightId)]["state"]["xy"][1]}, "transition": 0.15})})
                                elif proto == "yeelight":
                                    operation = skipSimilarFrames(lightId, lights[str(lightId)]["state"]["xy"], lights[str(lightId)]["state"]["bri"])
                                    if operation == 1:
                                        sendLightRequest(str(lightId), {"bri": lights[str(lightId)]["state"]["bri"], "transitiontime": 150 / lights[str(lightId)]["state"]["bri"]}, lights, addresses, None, host_ip)
                                    elif operation == 2:
                                        sendLightRequest(str(lightId), {"xy": lights[str(lightId)]["state"]["xy"], "transitiontime": 3}, lights, addresses, [r, g, b], host_ip)

                                else:
                                    if fremeID % 4 == 0: # can use 2, 4, 6, 8, 12 => increase in case the destination device is overloaded
                                        if r == 0 and  g == 0 and  b == 0:
                                            if lightStatus[lightId]["on"]:
                                                sendLightRequest(str(lightId), {"on": False, "transitiontime": 3}, lights, addresses, None, host_ip)
                                                lightStatus[lightId]["on"] = False
                                        elif lightStatus[lightId]["on"] == False:
                                            sendLightRequest(str(lightId), {"on": True, "transitiontime": 3}, lights, addresses, None, host_ip)
                                            lightStatus[lightId]["on"] = True
                                        operation = skipSimilarFrames(lightId, lights[str(lightId)]["state"]["xy"], lights[str(lightId)]["state"]["bri"])
                                        if operation == 1:
                                            sendLightRequest(str(lightId), {"bri": lights[str(lightId)]["state"]["bri"], "transitiontime": 3}, lights, addresses, None, host_ip)
                                        elif operation == 2:
                                            sendLightRequest(str(lightId), {"xy": lights[str(lightId)]["state"]["xy"], "transitiontime": 3}, lights, addresses)

                                fremeID += 1
                                if fremeID == 25:
                                    fremeID = 1
                        i = i + 9
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
                                    lights[str(lightId)]["state"]["on"] = False
                                else:
                                    lights[str(lightId)]["state"].update({"on": True, "bri": bri, "xy": [x,y], "colormode": "xy"})
                                if addresses[str(lightId)]["protocol"] in ["native", "native_multi", "native_single"]:
                                    if addresses[str(lightId)]["ip"] not in nativeLights:
                                        nativeLights[addresses[str(lightId)]["ip"]] = {}
                                    nativeLights[addresses[str(lightId)]["ip"]][addresses[str(lightId)]["light_nr"] - 1] = convert_xy(x, y, bri)
                                elif addresses[str(lightId)]["protocol"] == "esphome":
                                    if addresses[str(lightId)]["ip"] not in esphomeLights:
                                        esphomeLights[addresses[str(lightId)]["ip"]] = {}
                                    r, g, b = convert_xy(x, y, bri)
                                    esphomeLights[addresses[str(lightId)]["ip"]]["color"] = [r, g, b, bri]
                                elif addresses[str(lightId)]["protocol"] == "mqtt":
                                    operation = skipSimilarFrames(lightId, [x,y], bri)
                                    if operation == 1:
                                        mqttLights.append({"topic": addresses[str(lightId)]["command_topic"], "payload": json.dumps({"brightness": bri, "transition": 0.2})})
                                    elif operation == 2:
                                        mqttLights.append({"topic": addresses[str(lightId)]["command_topic"], "payload": json.dumps({"color": {"x": x, "y": y}, "transition": 0.15})})
                                else:
                                    fremeID += 1
                                    if fremeID % 4 == 0: # can use 2, 4, 6, 8, 12 => increase in case the destination device is overloaded
                                        operation = skipSimilarFrames(lightId, [x,y], bri)
                                        if operation == 1:
                                            sendLightRequest(str(lightId), {"bri": bri, "transitiontime": 3}, lights, addresses)
                                        elif operation == 2:
                                            sendLightRequest(str(lightId), {"xy": [x,y], "transitiontime": 3}, lights, addresses)
                                fremeID += 1
                                if fremeID == 25:
                                    fremeID = 1

                        i = i + 9
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
                if emulator["mqtt"]["mqttUser"] != "" and emulator["mqtt"]["mqttPassword"] != "":
                    auth = {'username':emulator["mqtt"]["mqttUser"], 'password':emulator["mqtt"]["mqttPassword"]}
                publish.multiple(mqttLights, hostname=emulator["mqtt"]["mqttServer"], port=emulator["mqtt"]["mqttPort"], auth=auth)
        except Exception as e: #Assuming the only exception is a network timeout, please don't scream at me
            if syncing: #Reset sync status and kill relay service
                logging.info("Entertainment Service was syncing and has timed out, stopping server and clearing state" + str(e))
                Popen(["killall", "entertain-srv"])
                for group in groups.keys():
                    if "type" in groups[group] and groups[group]["type"] == "Entertainment":
                        groups[group]["stream"].update({"active": False, "owner": None})
                syncing = False
