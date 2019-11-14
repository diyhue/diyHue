import logging, json
from functions.request import sendRequest
from functions.colors import convert_rgb_xy, convert_xy  
from subprocess import check_output
from protocols import protocols
from datetime import datetime
from time import sleep
from functions.updateGroup import updateGroupStats

def sendLightRequest(light, data, lights, addresses):
    payload = {}
    if light in addresses:
        protocol_name = addresses[light]["protocol"]
        for protocol in protocols:
            if "protocols." + protocol_name == protocol.__name__:
                try:
                    light_state = protocol.set_light(addresses[light], lights[light], data)
                except Exception as e:
                    lights[light]["state"]["reachable"] = False
                    logging.warning(lights[light]["name"] + " light not reachable: %s", e)
                return

        if addresses[light]["protocol"] == "native": #ESP8266 light or strip
            url = "http://" + addresses[light]["ip"] + "/set?light=" + str(addresses[light]["light_nr"])
            method = 'GET'
            for key, value in data.items():
                if key == "xy":
                    url += "&x=" + str(value[0]) + "&y=" + str(value[1])
                else:
                    url += "&" + key + "=" + str(value)
        elif addresses[light]["protocol"] in ["hue","deconz"]: #Original Hue light or Deconz light
            url = "http://" + addresses[light]["ip"] + "/api/" + addresses[light]["username"] + "/lights/" + addresses[light]["light_id"] + "/state"
            method = 'PUT'
            payload.update(data)

        elif addresses[light]["protocol"] == "domoticz": #Domoticz protocol
            url = "http://" + addresses[light]["ip"] + "/json.htm?type=command&idx=" + addresses[light]["light_id"]
            method = 'GET'
            if "on" in data and not "bri" in data and not "ct" in data and not "xy" in data:
                for key, value in data.items():
                    url += "&param=switchlight"
                    if key == "on":
                        if value:
                            url += "&switchcmd=On"
                        else:
                            url += "&switchcmd=Off"
            else:
                url += "&param=setcolbrightnessvalue"
                color_data = {}

                old_light_state = lights[light]["state"]
                colormode = old_light_state["colormode"]
                ct = old_light_state["ct"]
                bri = old_light_state["bri"]
                xy = old_light_state["xy"]

                if "bri" in data:
                    bri = data["bri"]
                if "ct" in data:
                    ct = data["ct"]
                if "xy" in data:
                    xy = data["xy"]
                bri = int(bri)

                color_data["m"] = 1 #0: invalid, 1: white, 2: color temp, 3: rgb, 4: custom
                if colormode == "ct":
                    color_data["m"] = 2
                    ct01 = (ct - 153) / (500 - 153) #map color temperature from 153-500 to 0-1
                    ct255 = ct01 * 255 #map color temperature from 0-1 to 0-255
                    color_data["t"] = ct255
                elif colormode == "xy":
                    color_data["m"] = 3
                    (color_data["r"], color_data["g"], color_data["b"]) = convert_xy(xy[0], xy[1], 255)
                url += "&color="+json.dumps(color_data)
                url += "&brightness=" + str(round(float(bri)/255*100))

            urlObj = {}
            urlObj["url"] = url

        elif addresses[light]["protocol"] == "jeedom": #Jeedom protocol
            url = "http://" + addresses[light]["ip"] + "/core/api/jeeApi.php?apikey=" + addresses[light]["light_api"] + "&type=cmd&id="
            method = 'GET'
            for key, value in data.items():
                if key == "on":
                    if value:
                        url += addresses[light]["light_on"]
                    else:
                        url += addresses[light]["light_off"]
                elif key == "bri":
                    url += addresses[light]["light_slider"] + "&slider=" + str(round(float(value)/255*100)) # jeedom range from 0 to 100 (for zwave devices) instead of 0-255 of bridge

        elif addresses[light]["protocol"] == "milight": #MiLight bulb
            url = "http://" + addresses[light]["ip"] + "/gateways/" + addresses[light]["device_id"] + "/" + addresses[light]["mode"] + "/" + str(addresses[light]["group"])
            method = 'PUT'
            for key, value in data.items():
                if key == "on":
                    payload["status"] = value
                elif key == "bri":
                    payload["brightness"] = value
                elif key == "ct":
                    payload["color_temp"] = int(value / 1.6 + 153)
                elif key == "hue":
                    payload["hue"] = value / 180
                elif key == "sat":
                    payload["saturation"] = value * 100 / 255
                elif key == "xy":
                    payload["color"] = {}
                    (payload["color"]["r"], payload["color"]["g"], payload["color"]["b"]) = convert_xy(value[0], value[1], lights[light]["state"]["bri"])
            logging.info(json.dumps(payload))

        elif addresses[light]["protocol"] == "ikea_tradfri": #IKEA Tradfri bulb
            url = "coaps://" + addresses[light]["ip"] + ":5684/15001/" + str(addresses[light]["device_id"])
            for key, value in data.items():
                if key == "on":
                    payload["5850"] = int(value)
                elif key == "transitiontime":
                    payload["5712"] = value
                elif key == "bri":
                    payload["5851"] = value
                elif key == "ct":
                    if value < 270:
                        payload["5706"] = "f5faf6"
                    elif value < 385:
                        payload["5706"] = "f1e0b5"
                    else:
                        payload["5706"] = "efd275"
                elif key == "xy":
                    payload["5709"] = int(value[0] * 65535)
                    payload["5710"] = int(value[1] * 65535)
            if "hue" in data or "sat" in data:
                if("hue" in data):
                    hue = data["hue"]
                else:
                    hue = lights[light]["state"]["hue"]
                if("sat" in data):
                    sat = data["sat"]
                else:
                    sat = lights[light]["state"]["sat"]
                if("bri" in data):
                    bri = data["bri"]
                else:
                    bri = lights[light]["state"]["bri"]
                rgbValue = hsv_to_rgb(hue, sat, bri)
                xyValue = convert_rgb_xy(rgbValue[0], rgbValue[1], rgbValue[2])
                payload["5709"] = int(xyValue[0] * 65535)
                payload["5710"] = int(xyValue[1] * 65535)
            if "5850" in payload and payload["5850"] == 0:
                payload.clear() #setting brightnes will turn on the ligh even if there was a request to power off
                payload["5850"] = 0
            elif "5850" in payload and "5851" in payload: #when setting brightness don't send also power on command
                del payload["5850"]
        elif addresses[light]["protocol"] == "flex":
            msg = bytearray()
            if "on" in data:
                if data["on"]:
                    msg = bytearray([0x71, 0x23, 0x8a, 0x0f])
                else:
                    msg = bytearray([0x71, 0x24, 0x8a, 0x0f])
                checksum = sum(msg) & 0xFF
                msg.append(checksum)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
                sock.sendto(msg, (addresses[light]["ip"], 48899))
            if ("bri" in data and lights[light]["state"]["colormode"] == "xy") or "xy" in data:
                logging.info(pretty_json(data))
                bri = data["bri"] if "bri" in data else lights[light]["state"]["bri"]
                xy = data["xy"] if "xy" in data else lights[light]["state"]["xy"]
                rgb = convert_xy(xy[0], xy[1], bri)
                msg = bytearray([0x41, rgb[0], rgb[1], rgb[2], 0x00, 0xf0, 0x0f])
                checksum = sum(msg) & 0xFF
                msg.append(checksum)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
                sock.sendto(msg, (addresses[light]["ip"], 48899))
            elif ("bri" in data and lights[light]["state"]["colormode"] == "ct") or "ct" in data:
                bri = data["bri"] if "bri" in data else lights[light]["state"]["bri"]
                msg = bytearray([0x41, 0x00, 0x00, 0x00, bri, 0x0f, 0x0f])
                checksum = sum(msg) & 0xFF
                msg.append(checksum)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
                sock.sendto(msg, (addresses[light]["ip"], 48899))

        try:
            if addresses[light]["protocol"] == "ikea_tradfri":
                if "5712" not in payload:
                    payload["5712"] = 4 #If no transition add one, might also add check to prevent large transitiontimes
                check_output("./coap-client-linux -m put -u \"" + addresses[light]["identity"] + "\" -k \"" + addresses[light]["preshared_key"] + "\" -e '{ \"3311\": [" + json.dumps(payload) + "] }' \"" + url + "\"", shell=True)
            elif addresses[light]["protocol"] in ["hue", "deconz"]:
                color = {}
                if "xy" in payload:
                    color["xy"] = payload["xy"]
                    del(payload["xy"])
                elif "ct" in payload:
                    color["ct"] = payload["ct"]
                    del(payload["ct"])
                elif "hue" in payload:
                    color["hue"] = payload["hue"]
                    del(payload["hue"])
                elif "sat" in payload:
                    color["sat"] = payload["sat"]
                    del(payload["sat"])
                if len(payload) != 0:
                    sendRequest(url, method, json.dumps(payload))
                    if addresses[light]["protocol"] == "deconz":
                        sleep(0.7)
                if len(color) != 0:
                    sendRequest(url, method, json.dumps(color))
            else:
                sendRequest(url, method, json.dumps(payload))
        except:
            lights[light]["state"]["reachable"] = False
            logging.info("request error")
        else:
            lights[light]["state"]["reachable"] = True
            logging.info("LightRequest: " + url)


def syncWithLights(lights, addresses, users, groups, off_if_unreachable): #update Hue Bridge lights states
    while True:
        logging.info("sync with lights")
        for light in addresses:
            try:
                protocol_name = addresses[light]["protocol"]
                for protocol in protocols:
                    if "protocols." + protocol_name == protocol.__name__:
                        try:
                            light_state = protocol.get_light_state(addresses[light], lights[light])
                            lights[light]["state"].update(light_state)
                            lights[light]["state"]["reachable"] = True
                        except Exception as e:
                            lights[light]["state"]["reachable"] = False
                            lights[light]["state"]["on"] = False
                            logging.warning(lights[light]["name"] + " is unreachable: %s", e)

                if addresses[light]["protocol"] == "native":
                    light_data = json.loads(sendRequest("http://" + addresses[light]["ip"] + "/get?light=" + str(addresses[light]["light_nr"]), "GET", "{}"))
                    lights[light]["state"].update(light_data)
                    lights[light]["state"]["reachable"] = True
                elif addresses[light]["protocol"] == "hue":
                    light_data = json.loads(sendRequest("http://" + addresses[light]["ip"] + "/api/" + addresses[light]["username"] + "/lights/" + addresses[light]["light_id"], "GET", "{}"))
                    lights[light]["state"].update(light_data["state"])
                elif addresses[light]["protocol"] == "ikea_tradfri":
                    light_data = json.loads(check_output("./coap-client-linux -m get -u \"" + addresses[light]["identity"] + "\" -k \"" + addresses[light]["preshared_key"] + "\" \"coaps://" + addresses[light]["ip"] + ":5684/15001/" + str(addresses[light]["device_id"]) +"\"", shell=True).decode('utf-8').rstrip('\n').split("\n")[-1])
                    lights[light]["state"]["on"] = bool(light_data["3311"][0]["5850"])
                    lights[light]["state"]["bri"] = light_data["3311"][0]["5851"]
                    if "5706" in light_data["3311"][0]:
                        if light_data["3311"][0]["5706"] == "f5faf6":
                            lights[light]["state"]["ct"] = 170
                        elif light_data["3311"][0]["5706"] == "f1e0b5":
                            lights[light]["state"]["ct"] = 320
                        elif light_data["3311"][0]["5706"] == "efd275":
                            lights[light]["state"]["ct"] = 470
                    else:
                        lights[light]["state"]["ct"] = 470
                    lights[light]["state"]["reachable"] = True
                elif addresses[light]["protocol"] == "milight":
                    light_data = json.loads(sendRequest("http://" + addresses[light]["ip"] + "/gateways/" + addresses[light]["device_id"] + "/" + addresses[light]["mode"] + "/" + str(addresses[light]["group"]), "GET", "{}"))
                    if light_data["state"] == "ON":
                        lights[light]["state"]["on"] = True
                    else:
                        lights[light]["state"]["on"] = False
                    if "brightness" in light_data:
                        lights[light]["state"]["bri"] = light_data["brightness"]
                    if "color_temp" in light_data:
                        lights[light]["state"]["colormode"] = "ct"
                        lights[light]["state"]["ct"] = int(light_data["color_temp"] * 1.6)
                    elif "bulb_mode" in light_data and light_data["bulb_mode"] == "color":
                        lights[light]["state"]["colormode"] = "hs"
                        lights[light]["state"]["hue"] = light_data["hue"] * 180
                        if (not "saturation" in light_data) and addresses[light]["mode"] == "rgbw":
                            lights[light]["state"]["sat"] = 255
                        else:
                            lights[light]["state"]["sat"] = int(light_data["saturation"] * 2.54)
                    lights[light]["state"]["reachable"] = True
                elif addresses[light]["protocol"] == "domoticz": #domoticz protocol
                    light_data = json.loads(sendRequest("http://" + addresses[light]["ip"] + "/json.htm?type=devices&rid=" + addresses[light]["light_id"], "GET", "{}"))
                    if light_data["result"][0]["Status"] == "Off":
                         lights[light]["state"]["on"] = False
                    else:
                         lights[light]["state"]["on"] = True
                    lights[light]["state"]["bri"] = str(round(float(light_data["result"][0]["Level"])/100*255))
                    lights[light]["state"]["reachable"] = True
                elif addresses[light]["protocol"] == "jeedom": #jeedom protocol
                    light_data = json.loads(sendRequest("http://" + addresses[light]["ip"] + "/core/api/jeeApi.php?apikey=" + addresses[light]["light_api"] + "&type=cmd&id=" + addresses[light]["light_id"], "GET", "{}"))
                    if light_data == 0:
                         lights[light]["state"]["on"] = False
                    else:
                         lights[light]["state"]["on"] = True
                    lights[light]["state"]["bri"] = str(round(float(light_data)/100*255))
                    lights[light]["state"]["reachable"] = True

                if off_if_unreachable:
                    if lights[light]["state"]["reachable"] == False:
                        lights[light]["state"]["on"] = False
                updateGroupStats(light, lights, groups)
            except Exception as e:
                lights[light]["state"]["reachable"] = False
                lights[light]["state"]["on"] = False
                logging.warning(lights[light]["name"] + " is unreachable: %s", e)
        sleep(10) #wait at last 10 seconds before next sync
        i = 0
        while i < 300: #sync with lights every 300 seconds or instant if one user is connected
            for user in users.keys():
                if users[user]["last use date"] == datetime.now().strftime("%Y-%m-%dT%H:%M:%S"):
                    i = 300
                    break
            i += 1
            sleep(1)
