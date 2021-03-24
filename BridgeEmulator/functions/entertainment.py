import socket
import logging
from subprocess import Popen
from functions.colors import convert_rgb_xy, convert_xy
from functions.lightRequest import sendLightRequest


def entertainmentService(lights, addresses, groups, host_ip):
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverSocket.settimeout(3)  # Set a packet timeout that we catch later
    serverSocket.bind(('127.0.0.1', 2101))
    frameID = 0
    lightStatus = {}
    syncing = False  # Flag to check whether or not we had been syncing when a timeout occurs
    while True:
        try:
            data = serverSocket.recvfrom(106)[0]
            nativeLights = {}
            esphomeLights = {}
            if data[:9].decode('utf-8') == "HueStream":
                syncing = True  # Set sync flag when receiving valid data
                if data[14] == 0:  # rgb colorspace
                    i = 16
                    while i < len(data):
                        if data[i] == 0:  # Type of device 0x00 = Light
                            lightId = data[i+1] * 256 + data[i+2]
                            if lightId != 0:
                                r = int((data[i+3] * 256 + data[i+4]) / 256)
                                g = int((data[i+5] * 256 + data[i+6]) / 256)
                                b = int((data[i+7] * 256 + data[i+8]) / 256)
                                proto = addresses[str(lightId)]["protocol"]
                                if lightId not in lightStatus:
                                    lightStatus[lightId] = {
                                        "on": False, "bri": 1}
                                if r == 0 and g == 0 and b == 0:
                                    lights[str(lightId)]["state"]["on"] = False
                                else:
                                    lights[str(lightId)]["state"].update({"on": True, "bri": int(
                                        (r + g + b) / 3), "xy": convert_rgb_xy(r, g, b), "colormode": "xy"})
                                if proto in ["native", "native_multi", "native_single"]:
                                    if addresses[str(lightId)]["ip"] not in nativeLights:
                                        nativeLights[addresses[str(lightId)]["ip"]] = {
                                        }
                                    nativeLights[addresses[str(lightId)]["ip"]][addresses[str(
                                        lightId)]["light_nr"] - 1] = [r, g, b]
                                elif proto == "esphome":
                                    if addresses[str(lightId)]["ip"] not in esphomeLights:
                                        esphomeLights[addresses[str(lightId)]["ip"]] = {
                                        }
                                    bri = int(max(r, g, b))
                                    esphomeLights[addresses[str(lightId)]["ip"]]["color"] = [
                                        r, g, b, bri]
                                else:
                                    if frameID == 24:  # => every seconds, increase in case the destination device is overloaded
                                        gottaSend = False
                                        yee = proto == "yeelight"
                                        brABS = abs(
                                            int((r + b + g) / 3) - lightStatus[lightId]["bri"])
                                        if r == 0 and g == 0 and b == 0:  # Turn off if color is black
                                            if lightStatus[lightId]["on"]:
                                                sendLightRequest(str(lightId), {
                                                                 "on": False, "transitiontime": 3}, lights, addresses, None, host_ip)
                                                lightStatus[lightId]["on"] = False
                                        else:
                                            # Turn on if color is not black
                                            if lightStatus[lightId]["on"] == False:
                                                sendLightRequest(str(lightId), {
                                                                 "on": True, "transitiontime": 3}, lights, addresses, None, host_ip)
                                                lightStatus[lightId]["on"] = True
                                            elif brABS > 50:  # to optimize, send brightness only if difference is bigger than this value
                                                sendLightRequest(str(lightId), {"bri": int(
                                                    (r + b + g) / 3), "transitiontime": 150 / brABS}, lights, addresses, None, host_ip)
                                                lightStatus[lightId]["bri"] = int(
                                                    (r + b + g) / 3)
                                            else:
                                                gottaSend = True
                                            if gottaSend or yee:
                                                sendLightRequest(str(lightId), {"xy": convert_rgb_xy(
                                                    r, g, b), "transitiontime": 3}, lights, addresses, [r, g, b], host_ip)
                                frameID += 1
                                if frameID == 25:
                                    frameID = 0
                        i = i + 9
                elif data[14] == 1:  # cie colorspace
                    i = 16
                    while i < len(data):
                        if data[i] == 0:  # Type of device 0x00 = Light
                            lightId = data[i+1] * 256 + data[i+2]
                            if lightId != 0:
                                x = (data[i+3] * 256 + data[i+4]) / 65535
                                y = (data[i+5] * 256 + data[i+6]) / 65535
                                bri = int((data[i+7] * 256 + data[i+8]) / 256)
                                if bri == 0:
                                    lights[str(lightId)]["state"]["on"] = False
                                else:
                                    lights[str(lightId)]["state"].update(
                                        {"on": True, "bri": bri, "xy": [x, y], "colormode": "xy"})
                                if addresses[str(lightId)]["protocol"] in ["native", "native_multi", "native_single"]:
                                    if addresses[str(lightId)]["ip"] not in nativeLights:
                                        nativeLights[addresses[str(lightId)]["ip"]] = {
                                        }
                                    nativeLights[addresses[str(lightId)]["ip"]][addresses[str(
                                        lightId)]["light_nr"] - 1] = convert_xy(x, y, bri)
                                elif addresses[str(lightId)]["protocol"] == "esphome":
                                    if addresses[str(lightId)]["ip"] not in esphomeLights:
                                        esphomeLights[addresses[str(lightId)]["ip"]] = {
                                        }
                                    r, g, b = convert_xy(x, y, bri)
                                    esphomeLights[addresses[str(lightId)]["ip"]]["color"] = [
                                        r, g, b, bri]
                                else:
                                    frameID += 1
                                    if frameID == 24:  # 24 = every seconds, increase in case the destination device is overloaded
                                        sendLightRequest(
                                            str(lightId), {"xy": [x, y]}, lights, addresses, None, host_ip)
                                        frameID = 0
                        i = i + 9
            if len(nativeLights) != 0:
                for ip in nativeLights.keys():
                    udpmsg = bytearray()
                    for light in nativeLights[ip].keys():
                        udpmsg += bytes([light]) + bytes([nativeLights[ip][light][0]]) + bytes(
                            [nativeLights[ip][light][1]]) + bytes([nativeLights[ip][light][2]])
                    sock = socket.socket(
                        socket.AF_INET, socket.SOCK_DGRAM)  # UDP
                    sock.sendto(udpmsg, (ip.split(":")[0], 2100))
            if len(esphomeLights) != 0:
                for ip in esphomeLights.keys():
                    udpmsg = bytearray()
                    udpmsg += bytes([0]) + bytes([esphomeLights[ip]["color"][0]]) + bytes([esphomeLights[ip]["color"][1]]
                                                                                          ) + bytes([esphomeLights[ip]["color"][2]]) + bytes([esphomeLights[ip]["color"][3]])
                    sock = socket.socket(
                        socket.AF_INET, socket.SOCK_DGRAM)  # UDP
                    sock.sendto(udpmsg, (ip.split(":")[0], 2100))
        except Exception:  # Assuming the only exception is a network timeout, please don't scream at me
            if syncing:  # Reset sync status and kill relay service
                logging.info(
                    "Entertainment Service was syncing and has timed out, stopping server and clearing state")
                Popen(["killall", "entertain-srv"])
                for group in groups.keys():
                    if "type" in groups[group] and groups[group]["type"] == "Entertainment":
                        groups[group]["stream"].update(
                            {"active": False, "owner": None})
                syncing = False
