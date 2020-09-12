from datetime import datetime
import configManager

bridgeConfig = configManager.bridgeConfig.json_config
dxState = configManager.runtimeConfig.dxState

def nextFreeId(bridgeConfig, element):
    i = 1
    while (str(i)) in bridgeConfig[element]:
        i += 1
    return str(i)

def generateDxState():
    for sensor in bridgeConfig["sensors"]:
        if sensor not in dxState["sensors"] and "state" in bridgeConfig["sensors"][sensor]:
            dxState["sensors"][sensor] = {"state": {}}
            for key in bridgeConfig["sensors"][sensor]["state"].keys():
                if key in ["lastupdated", "presence", "flag", "dark", "daylight", "status"]:
                    dxState["sensors"][sensor]["state"].update({key: datetime.now()})
    for group in bridgeConfig["groups"]:
        if group not in dxState["groups"] and "state" in bridgeConfig["groups"][group]:
            dxState["groups"][group] = {"state": {}}
            for key in bridgeConfig["groups"][group]["state"].keys():
                dxState["groups"][group]["state"].update({key: datetime.now()})
    for light in bridgeConfig["lights"]:
        if light not in dxState["lights"] and "state" in bridgeConfig["lights"][light]:
            dxState["lights"][light] = {"state": {}}
            for key in bridgeConfig["lights"][light]["state"].keys():
                if key in ["on", "bri", "colormode", "reachable"]:
                    dxState["lights"][light]["state"].update({key: datetime.now()})
