from threading import Thread
from time import sleep

import requests

import configManager
from functions.lightRequest import sendLightRequest
from functions.updateGroup import updateGroupStats

bridge_config = configManager.bridgeConfig.json_config

def manageDeviceLights(lights_state):
    protocol = bridge_config["lights_address"][list(lights_state.keys())[0]]["protocol"]
    payload = {}
    for light in lights_state.keys():
        if protocol == "native_multi":  # whyyy
            payload[bridge_config["lights_address"][light]["light_nr"]] = lights_state[light]
        elif protocol in ["native", "native_single", "milight"]:
            sendLightRequest(light, lights_state[light], bridge_config["lights"], bridge_config["lights_address"])
            if protocol == "milight":  # hotfix to avoid milight hub overload
                sleep(0.05)
        else:
            Thread(target=sendLightRequest,
                   args=[light, lights_state[light], bridge_config["lights"], bridge_config["lights_address"]]).start()
            sleep(0.1)
    if protocol == "native_multi":
        requests.put("http://" + bridge_config["lights_address"][list(lights_state.keys())[0]]["ip"] + "/state",
                     json=payload, timeout=3)


def splitLightsToDevices(group, state,
                         scene={}):  # appears to take in a request to change light mode -> sending light packet to device
    groups = []
    if group == "0":
        for grp in bridge_config["groups"].keys():
            groups.append(grp)
    else:
        groups.append(group)

    lightsData = {}
    if len(scene) == 0:  # convert relative inc/dec to light commands
        for grp in groups:  # part of the groups api inc/dec bri
            if "bri_inc" in state:
                bridge_config["groups"][grp]["action"]["bri"] += int(state["bri_inc"])
                if bridge_config["groups"][grp]["action"]["bri"] > 254:
                    bridge_config["groups"][grp]["action"]["bri"] = 254
                elif bridge_config["groups"][grp]["action"]["bri"] < 1:
                    bridge_config["groups"][grp]["action"]["bri"] = 1
                del state["bri_inc"]
                state.update({"bri": bridge_config["groups"][grp]["action"]["bri"]})
            elif "ct_inc" in state:
                bridge_config["groups"][grp]["action"]["ct"] += int(state["ct_inc"])
                if bridge_config["groups"][grp]["action"]["ct"] > 500:
                    bridge_config["groups"][grp]["action"]["ct"] = 500
                elif bridge_config["groups"][grp]["action"]["ct"] < 153:
                    bridge_config["groups"][grp]["action"]["ct"] = 153
                del state["ct_inc"]
                state.update({"ct": bridge_config["groups"][grp]["action"]["ct"]})
            elif "hue_inc" in state:
                bridge_config["groups"][grp]["action"]["hue"] += int(state["hue_inc"])
                if bridge_config["groups"][grp]["action"]["hue"] > 65535:
                    bridge_config["groups"][grp]["action"]["hue"] -= 65535
                elif bridge_config["groups"][grp]["action"]["hue"] < 0:
                    bridge_config["groups"][grp]["action"]["hue"] += 65535
                del state["hue_inc"]
                state.update({"hue": bridge_config["groups"][grp]["action"]["hue"]})
            for light in bridge_config["groups"][grp]["lights"]:
                lightsData[light] = state
    else:
        lightsData = scene

    # Make sure any lights haven't been deleted
    lightsData = {k: v for k, v in lightsData.items() if k in bridge_config["lights_address"]}

    if group != "0":  # only set light state if light is part of group
        lightdel = []  # if light is not in a group, delete it from the intermediate scene
        for light in lightsData.keys():
            if light not in bridge_config["groups"][group]["lights"]:
                lightdel.append(light)
        for light in lightdel:
            del lightsData[light]

    # deviceIp = {}
    # for light in lightsData.keys(): #this appears to be legacy code as the ip is not used anywhere
    #     if bridge_config["lights_address"][light]["ip"] not in deviceIp:
    #         deviceIp[bridge_config["lights_address"][light]["ip"]] = {}
    #     deviceIp[bridge_config["lights_address"][light]["ip"]][light] = lightsData[light]
    # for ip in deviceIp:
    for lightid, state in lightsData.items():  # this janky thing replaces the previous more janky thing
        Thread(target=manageDeviceLights, args=[{lightid: state}]).start()
    ### update light details
    for light in lightsData.keys():
        if "xy" in lightsData[light]:
            bridge_config["lights"][light]["state"]["colormode"] = "xy"
        elif "ct" in lightsData[light]:
            bridge_config["lights"][light]["state"]["colormode"] = "ct"
        elif "hue" in lightsData[light]:
            bridge_config["lights"][light]["state"]["colormode"] = "hs"
        # if "transitiontime" in lightsData[light]:
        #     del lightsData[light]["transitiontime"]
        bridge_config["lights"][light]["state"].update(lightsData[light])
    if lightsData:
        updateGroupStats(list(lightsData.keys())[0], bridge_config["lights"], bridge_config["groups"])



def groupZero(state):
    lightsData = {}
    for light in bridge_config["lights"].keys():
        lightsData[light] = state
    Thread(target=splitLightsToDevices, args=["0", {}, lightsData]).start()
    for group in bridge_config["groups"].keys():
        bridge_config["groups"][group]["action"].update(state)
        if "on" in state:
            bridge_config["groups"][group]["state"]["any_on"] = state["on"]
            bridge_config["groups"][group]["state"]["all_on"] = state["on"]


def find_light_in_config_from_uid(bridge_config, unique_id):
    for light in bridge_config["lights"].keys():
        if bridge_config["lights"][light]["uniqueid"] == unique_id:
            return light
    return None
