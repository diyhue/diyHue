import logManager
import configManager
import requests
from threading import Thread
from time import sleep
from lights.protocols import protocols


logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.json_config
newLights = configManager.runtimeConfig.newLights

def sendLightRequest(light, data, rgb = None, entertainmentHostIP = None):
    payload = {}
    if light in bridgeConfig["emulator"]["lights"]:
        protocol_name = bridgeConfig["emulator"]["lights"][light]["protocol"]
        for protocol in protocols:
            if "lights.protocols." + protocol_name == protocol.__name__:
                try:
                    if entertainmentHostIP and protocol_name == "yeelight":
                        protocol.enableMusic(bridgeConfig["emulator"]["lights"][light]["ip"], entertainmentHostIP)
                    if protocol_name in ["yeelight", "mi_box", "esphome", "tasmota"]:
                        protocol.set_light(bridgeConfig["emulator"]["lights"][light], bridgeConfig["lights"][light], data, rgb)
                    else:
                        protocol.set_light(bridgeConfig["emulator"]["lights"][light], bridgeConfig["lights"][light], data)
                except Exception as e:
                    bridgeConfig["lights"][light]["state"]["reachable"] = False
                    logging.warning(bridgeConfig["lights"][light]["name"] + " light not reachable: %s", e)
                return

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

    if protocol == "native_multi": # bipass sendLightRequest function and send all light data in one request
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

def updateGroupStats(light, lights, groups): #set group stats based on lights status in that group
    for group in groups:
        if "lights" in groups[group] and light in groups[group]["lights"]:
            for key, value in lights[light]["state"].items():
                if key in ["bri", "xy", "ct", "hue", "sat"]:
                    groups[group]["action"][key] = value
            any_on = False
            all_on = True
            for group_light in groups[group]["lights"]:
                if group_light in lights and lights[group_light]["state"]["on"]:
                    any_on = True
                else:
                    all_on = False
            groups[group]["state"] = {"any_on": any_on, "all_on": all_on,}
            groups[group]["action"]["on"] = any_on