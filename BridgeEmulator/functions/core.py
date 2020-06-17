import logging
from datetime import datetime
import Globals
from threading import Thread
import requests
from functions.updateGroup import updateGroupStats
from functions.lightRequest import sendLightRequest
from time import sleep

def generateDxState():
    for sensor in Globals.bridge_config["sensors"]:
        if sensor not in Globals.dxState["sensors"] and "state" in Globals.bridge_config["sensors"][sensor]:
            Globals.dxState["sensors"][sensor] = {"state": {}}
            for key in Globals.bridge_config["sensors"][sensor]["state"].keys():
                if key in ["lastupdated", "presence", "flag", "dark", "daylight", "status"]:
                    Globals.dxState["sensors"][sensor]["state"].update({key: datetime.now()})
    for group in Globals.bridge_config["groups"]:
        if group not in Globals.dxState["groups"] and "state" in Globals.bridge_config["groups"][group]:
            Globals.dxState["groups"][group] = {"state": {}}
            for key in Globals.bridge_config["groups"][group]["state"].keys():
                Globals.dxState["groups"][group]["state"].update({key: datetime.now()})
    for light in Globals.bridge_config["lights"]:
        if light not in Globals.dxState["lights"] and "state" in Globals.bridge_config["lights"][light]:
            Globals.dxState["lights"][light] = {"state": {}}
            for key in Globals.bridge_config["lights"][light]["state"].keys():
                if key in ["on", "bri", "colormode", "reachable"]:
                    Globals.dxState["lights"][light]["state"].update({key: datetime.now()})


def manageDeviceLights(lights_state):
    protocol = Globals.bridge_config["emulator"]["lights"][list(lights_state.keys())[0]]["protocol"]
    payload = {}
    onStatus = {} #for mqtt
    for light in lights_state.keys():
        if protocol == "native_multi":
            payload[Globals.bridge_config["emulator"]["lights"][light]["light_nr"]] = lights_state[light]
        elif protocol == "mqtt":
            if Globals.bridge_config["lights"][light]["state"]["on"] == True or "on" in lights_state[light]: # fix: brightness change turn on the light
                payload[Globals.bridge_config["emulator"]["lights"][light]["command_topic"]] = lights_state[light]
        else:
            sendLightRequest(light, lights_state[light], Globals.bridge_config["lights"], Globals.bridge_config["emulator"]["lights"])
            sleep(0.05)

    if protocol == "native_multi":
        requests.put("http://"+Globals.bridge_config["emulator"]["lights"][list(lights_state.keys())[0]]["ip"]+"/state", json=payload, timeout=3)
    elif protocol == "mqtt":
        sendLightRequest("1", {"lights": payload, "mqtt": Globals.bridge_config["emulator"]["mqtt"]}, Globals.bridge_config["lights"], Globals.bridge_config["emulator"]["lights"])



def splitLightsToDevices(group, state, scene={}):
    groups = []
    if group == "0":
        for grp in Globals.bridge_config["groups"].keys():
            groups.append(grp)
    else:
        groups.append(group)

    lightsData = {}
    if len(scene) == 0:
        for grp in groups:
            if "bri_inc" in state:
                Globals.bridge_config["groups"][grp]["action"]["bri"] += int(state["bri_inc"])
                if Globals.bridge_config["groups"][grp]["action"]["bri"] > 254:
                    Globals.bridge_config["groups"][grp]["action"]["bri"] = 254
                elif Globals.bridge_config["groups"][grp]["action"]["bri"] < 1:
                    Globals.bridge_config["groups"][grp]["action"]["bri"] = 1
                del state["bri_inc"]
                state.update({"bri": Globals.bridge_config["groups"][grp]["action"]["bri"]})
            elif "ct_inc" in state:
                Globals.bridge_config["groups"][grp]["action"]["ct"] += int(state["ct_inc"])
                if Globals.bridge_config["groups"][grp]["action"]["ct"] > 500:
                    Globals.bridge_config["groups"][grp]["action"]["ct"] = 500
                elif Globals.bridge_config["groups"][grp]["action"]["ct"] < 153:
                    Globals.bridge_config["groups"][grp]["action"]["ct"] = 153
                del state["ct_inc"]
                state.update({"ct": Globals.bridge_config["groups"][grp]["action"]["ct"]})
            elif "hue_inc" in state:
                Globals.bridge_config["groups"][grp]["action"]["hue"] += int(state["hue_inc"])
                if Globals.bridge_config["groups"][grp]["action"]["hue"] > 65535:
                    Globals.bridge_config["groups"][grp]["action"]["hue"] -= 65535
                elif Globals.bridge_config["groups"][grp]["action"]["hue"] < 0:
                    Globals.bridge_config["groups"][grp]["action"]["hue"] += 65535
                del state["hue_inc"]
                state.update({"hue": Globals.bridge_config["groups"][grp]["action"]["hue"]})
            for light in Globals.bridge_config["groups"][grp]["lights"]:
                lightsData[light] = state
    else:
        lightsData = scene

    # Make sure any lights haven't been deleted
    lightsData = {k: v for k, v in lightsData.items() if k in Globals.bridge_config["emulator"]["lights"]}


    deviceIp = {}
    if group != "0": #only set light state if light is part of group
        lightdel=[]
        for light in lightsData.keys():
            if light not in Globals.bridge_config["groups"][group]["lights"]:
                lightdel.append(light)
        for light in lightdel:
            del lightsData[light]

    for light in lightsData.keys():
        if Globals.bridge_config["emulator"]["lights"][light]["ip"] not in deviceIp:
            deviceIp[Globals.bridge_config["emulator"]["lights"][light]["ip"]] = {}
        deviceIp[Globals.bridge_config["emulator"]["lights"][light]["ip"]][light] = lightsData[light]
    for ip in deviceIp:
        Thread(target=manageDeviceLights, args=[deviceIp[ip]]).start()
    ### update light details
    for light in lightsData.keys():
        if "xy" in lightsData[light]:
            Globals.bridge_config["lights"][light]["state"]["colormode"] = "xy"
        elif "ct" in lightsData[light]:
            Globals.bridge_config["lights"][light]["state"]["colormode"] = "ct"
        elif "hue" in lightsData[light]:
            Globals.bridge_config["lights"][light]["state"]["colormode"] = "hs"
        # if "transitiontime" in lightsData[light]:
        #     del lightsData[light]["transitiontime"]
        Globals.bridge_config["lights"][light]["state"].update(lightsData[light])
    updateGroupStats(list(lightsData.keys())[0], Globals.bridge_config["lights"], Globals.bridge_config["groups"])

def groupZero(state):
    lightsData = {}
    for light in Globals.bridge_config["lights"].keys():
        lightsData[light] = state
    Thread(target=splitLightsToDevices, args=["0", {}, lightsData]).start()
    for group in Globals.bridge_config["groups"].keys():
        Globals.bridge_config["groups"][group]["action"].update(state)
        if "on" in state:
            Globals.bridge_config["groups"][group]["state"]["any_on"] = state["on"]
            Globals.bridge_config["groups"][group]["state"]["all_on"] = state["on"]
