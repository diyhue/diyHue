import json
import random
import socket
import requests
import configManager
import logManager
from threading import Thread
from lights import protocols
from time import sleep
from lights.updateGroup import updateGroupStats
from functions.core import nextFreeId

logging = logManager.logger.get_logger(__name__)

def pretty_json(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))

from lights.protocols import protocols, yeelight, tasmota, shelly, native_single, native_multi, esphome, mqtt

bridgeConfig = configManager.bridgeConfig.json_config
newLights = configManager.runtimeConfig.newLights

# Define light defininitions for discovery features and adding device data to config
lightTypes = {}
lightTypes["Tasmota"] = {"type": "Extended color light", "swversion": "1.46.13_r26312"}
lightTypes["Tasmota"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "alert": "none", "effect": "none", "colormode": "xy", "reachable": True}

lightTypes["Shelly"] = {"type": "shelly1", "swversion": "1.46.13_r26312"}
lightTypes["Shelly"]["state"] = {"on": False, "alert": "none", "reachable": True}

lightTypes["ESPHome-RGB"] = {"type": "Extended color light", "swversion": "1.46.13_r26312", "manufacturername": "ESPHome"}
lightTypes["ESPHome-RGB"]["state"] = {"on": False, "bri": 254, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "alert": "none", "effect": "none", "colormode": "xy", "reachable": True}
lightTypes["ESPHome-RGB"]["config"] = {"archetype": "sultanbulb", "function": "mixed", "direction": "omnidirectional"}

lightTypes["ESPHome-Dimmable"] = {"type": "Dimmable light", "swversion": "1.46.13_r26312", "manufacturername": "ESPHome"}
lightTypes["ESPHome-Dimmable"]["state"] = {"on": False, "bri": 254,"alert": "none", "reachable": True}
lightTypes["ESPHome-Dimmable"]["config"] = {"archetype": "classicbulb", "function": "mixed", "direction": "omnidirectional"}

lightTypes["ESPHOME-Toggle"] = {"type": "On/Off plug-in unit", "swversion": "V1.04.12", "manufacturername": "ESPHome"}
lightTypes["ESPHOME-Toggle"]["state"] = {"on": False, "alert": "none", "reachable": True}
lightTypes["ESPHOME-Toggle"]["config"] = {"archetype": "classicbulb", "function": "mixed", "direction": "omnidirectional"}

lightTypes["LCT001"] = {"type":"Extended color light", "manufacturername": "Signify Netherlands B.V.", "swversion": "1.46.13_r26312"}
lightTypes["LCT001"]["state"] = {"alert": "none", "bri":0, "colormode": "xy", "effect": "none","hue": 0, "mode": "homeautomation","on": False,"reachable": True, "sat": 0,"xy": [0.408,0.517]}
lightTypes["LCT001"]["config"] = {"archetype": "sultanbulb","direction": "omnidirectional","function": "mixed","startup": {"configured": True, "mode": "powerfail"}}
lightTypes["LCT001"]["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.675,0.322],[0.409,0.518],[0.167,0.04]],"colorgamuttype": "B","ct": {"max": 500,"min": 153},"maxlumen": 600,"mindimlevel": 5000},"streaming": {"proxy": False,"renderer": True}},

lightTypes["LCT015"] = {"type": "Extended color light", "swversion": "1.46.13_r26312", "manufacturername": "Philips"}
lightTypes["LCT015"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "mode": "homeautomation", "effect": "none", "colormode": "ct", "reachable": True}
lightTypes["LCT015"]["config"] = {"archetype": "sultanbulb", "function": "mixed", "direction": "omnidirectional"}
lightTypes["LCT015"]["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.6915,0.3083],[0.17,0.7],[0.1532,0.0475]],"colorgamuttype": "C","ct": {"max": 500,"min": 153},"maxlumen": 800,"mindimlevel": 1000},"streaming": {"proxy": False,"renderer": True}}

lightTypes["LST002"] = {"type": "Color light", "swversion": "5.127.1.26581"}
lightTypes["LST002"]["state"] = {"on": False, "bri": 200, "hue": 0, "sat": 0, "xy": [0.0, 0.0], "ct": 461, "alert": "none", "mode": "homeautomation", "effect": "none", "colormode": "ct", "reachable": True}
lightTypes["LST002"]["capabilities"] = {"certified": True,"control": {"colorgamut": [[0.704,0.296],[0.2151,0.7106],[0.138,0.08]],"colorgamuttype": "A","maxlumen": 200,"mindimlevel": 10000},"streaming": {"proxy": False,"renderer": True}}

lightTypes["LWB010"] = {"type": "Dimmable light", "swversion": "1.46.13_r26312", "manufacturername": "Philips"}
lightTypes["LWB010"]["state"] = {"on": False, "bri": 254,"alert": "none", "reachable": True}
lightTypes["LWB010"]["config"] = {"archetype": "classicbulb", "function": "mixed", "direction": "omnidirectional"}

lightTypes["LTW001"] = {"type": "Color temperature light", "swversion": "1.46.13_r26312"}
lightTypes["LTW001"]["state"] = {"on": False, "colormode": "ct", "alert": "none", "mode": "homeautomation", "reachable": True, "bri": 254, "ct": 230}
lightTypes["LTW001"]["capabilities"] = {"certified": True,"control": {"mindimlevel": 1000,"maxlumen": 806,"ct": {"min": 153,"max": 454}},"streaming": {"renderer": False,"proxy": False}}

lightTypes["Plug 01"] = {"type": "On/Off plug-in unit", "swversion": "V1.04.12"}
lightTypes["Plug 01"]["state"] = {"on": False, "alert": "none", "reachable": True}

def addNewLight(modelid, name, emulatorConfig):
    newLightID = nextFreeId(bridgeConfig, "lights")
    if modelid in lightTypes:
        bridgeConfig["lights"][newLightID] = lightTypes[modelid]
        bridgeConfig["lights"][newLightID]["name"] = name
        bridgeConfig["lights"][newLightID]["name"] = generate_unique_id()
        bridgeConfig["emulator"]["lights"][newLightID] = emulatorConfig
        return newLightID
    return False


def generate_unique_id():
    rand_bytes = [random.randrange(0, 256) for _ in range(3)]
    return "00:17:88:01:00:%02x:%02x:%02x-0b" % (rand_bytes[0],rand_bytes[1],rand_bytes[2])

def scanHost(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.02) # Very short timeout. If scanning fails this could be increased
    result = sock.connect_ex((host, port))
    sock.close()
    return result

def iter_ips(port):
    argsDict = configManager.runtimeConfig.arg
    HOST_IP = argsDict["HOST_IP"]
    scan_on_host_ip = argsDict["scanOnHostIP"]
    ip_range_start = argsDict["IP_RANGE_START"]
    ip_range_end = argsDict["IP_RANGE_END"]
    host = HOST_IP.split('.')
    if scan_on_host_ip:
        yield ('127.0.0.1', port)
        return
    for addr in range(ip_range_start, ip_range_end + 1):
        host[3] = str(addr)
        test_host = '.'.join(host)
        if test_host != HOST_IP:
            yield (test_host, port)

def find_hosts(port):
    validHosts = []
    for host, port in iter_ips(port):
        if scanHost(host, port) == 0:
            hostWithPort = '%s:%s' % (host, port)
            validHosts.append(hostWithPort)

    return validHosts

def find_light_in_config_from_mac_and_nr(mac_address, light_nr):
    for light_id, light_address in bridgeConfig["emulator"]["lights"].items():
        if (light_address["protocol"] in ["native", "native_single",  "native_multi"]
                and light_address["mac"] == mac_address
                and ('light_nr' not in light_address or
                    light_address['light_nr'] == light_nr)):
            return light_id
    return None


def scanForLights(): #scan for ESP8266 lights and strips
    #return all host that listen on port 80
    device_ips = find_hosts(80)
    logging.info(pretty_json(device_ips))
    Thread(target=mqtt.discover).start()
    Thread(target=yeelight.discover).start()
    Thread(target=native_multi.discover, args=[device_ips]).start() # native_multi probe all esp8266 lights with firmware from diyhue repo
    sleep(0.5) # wait half second to not send http requsts in the same time for the same device during multple protocols probe.
    Thread(target=tasmota.discover, args=[device_ips]).start()
    sleep(0.5)
    Thread(target=shelly.discover, args=[device_ips]).start()
    sleep(0.5)
    Thread(target=esphome.discover, args=[device_ips]).start()
    deconz.scanDeconz()
    tradfri.scanTradfri()
    saveConfig()

def manageDeviceLights(lights_state):
    protocol = bridgeConfig["emulator"]["lights"][list(lights_state.keys())[0]]["protocol"]
    payload = {}
    onStatus = {} #for mqtt
    for light in lights_state.keys():
        if protocol == "native_multi":
            payload[bridgeConfig["emulator"]["lights"][light]["light_nr"]] = lights_state[light]
        elif protocol == "mqtt":
            if bridgeConfig["lights"][light]["state"]["on"] == True or "on" in lights_state[light]: # fix: brightness change turn on the light
                payload[bridgeConfig["emulator"]["lights"][light]["command_topic"]] = lights_state[light]
        else:
            sendLightRequest(light, lights_state[light], bridgeConfig["lights"], bridgeConfig["emulator"]["lights"])
            sleep(0.05)

    if protocol == "native_multi":
        requests.put("http://"+bridgeConfig["emulator"]["lights"][list(lights_state.keys())[0]]["ip"]+"/state", json=payload, timeout=3)
    elif protocol == "mqtt":
        sendLightRequest("1", {"lights": payload, "mqtt": bridgeConfig["emulator"]["mqtt"]}, bridgeConfig["lights"], bridgeConfig["emulator"]["lights"])



def splitLightsToDevices(group, state, scene={}):
    groups = []
    if group == "0":
        for grp in bridgeConfig["groups"].keys():
            groups.append(grp)
    else:
        groups.append(group)

    lightsData = {}
    if len(scene) == 0:
        for grp in groups:
            if "bri_inc" in state:
                bridgeConfig["groups"][grp]["action"]["bri"] += int(state["bri_inc"])
                if bridgeConfig["groups"][grp]["action"]["bri"] > 254:
                    bridgeConfig["groups"][grp]["action"]["bri"] = 254
                elif bridgeConfig["groups"][grp]["action"]["bri"] < 1:
                    bridgeConfig["groups"][grp]["action"]["bri"] = 1
                del state["bri_inc"]
                state.update({"bri": bridgeConfig["groups"][grp]["action"]["bri"]})
            elif "ct_inc" in state:
                bridgeConfig["groups"][grp]["action"]["ct"] += int(state["ct_inc"])
                if bridgeConfig["groups"][grp]["action"]["ct"] > 500:
                    bridgeConfig["groups"][grp]["action"]["ct"] = 500
                elif bridgeConfig["groups"][grp]["action"]["ct"] < 153:
                    bridgeConfig["groups"][grp]["action"]["ct"] = 153
                del state["ct_inc"]
                state.update({"ct": bridgeConfig["groups"][grp]["action"]["ct"]})
            elif "hue_inc" in state:
                bridgeConfig["groups"][grp]["action"]["hue"] += int(state["hue_inc"])
                if bridgeConfig["groups"][grp]["action"]["hue"] > 65535:
                    bridgeConfig["groups"][grp]["action"]["hue"] -= 65535
                elif bridgeConfig["groups"][grp]["action"]["hue"] < 0:
                    bridgeConfig["groups"][grp]["action"]["hue"] += 65535
                del state["hue_inc"]
                state.update({"hue": bridgeConfig["groups"][grp]["action"]["hue"]})
            for light in bridgeConfig["groups"][grp]["lights"]:
                lightsData[light] = state
    else:
        lightsData = scene

    # Make sure any lights haven't been deleted
    lightsData = {k: v for k, v in lightsData.items() if k in bridgeConfig["emulator"]["lights"]}


    deviceIp = {}
    if group != "0": #only set light state if light is part of group
        lightdel=[]
        for light in lightsData.keys():
            if light not in bridgeConfig["groups"][group]["lights"]:
                lightdel.append(light)
        for light in lightdel:
            del lightsData[light]

    for light in lightsData.keys():
        if bridgeConfig["emulator"]["lights"][light]["ip"] not in deviceIp:
            deviceIp[bridgeConfig["emulator"]["lights"][light]["ip"]] = {}
        deviceIp[bridgeConfig["emulator"]["lights"][light]["ip"]][light] = lightsData[light]
    for ip in deviceIp:
        Thread(target=manageDeviceLights, args=[deviceIp[ip]]).start()
    ### update light details
    for light in lightsData.keys():
        if "xy" in lightsData[light]:
            bridgeConfig["lights"][light]["state"]["colormode"] = "xy"
        elif "ct" in lightsData[light]:
            bridgeConfig["lights"][light]["state"]["colormode"] = "ct"
        elif "hue" in lightsData[light]:
            bridgeConfig["lights"][light]["state"]["colormode"] = "hs"
        # if "transitiontime" in lightsData[light]:
        #     del lightsData[light]["transitiontime"]
        bridgeConfig["lights"][light]["state"].update(lightsData[light])
    updateGroupStats(list(lightsData.keys())[0], bridgeConfig["lights"], bridgeConfig["groups"])

def groupZero(state):
    lightsData = {}
    for light in bridgeConfig["lights"].keys():
        lightsData[light] = state
    Thread(target=splitLightsToDevices, args=["0", {}, lightsData]).start()
    for group in bridgeConfig["groups"].keys():
        bridgeConfig["groups"][group]["action"].update(state)
        if "on" in state:
            bridgeConfig["groups"][group]["state"]["any_on"] = state["on"]
            bridgeConfig["groups"][group]["state"]["all_on"] = state["on"]
