import json
import configManager
import logManager
from datetime import datetime
from time import sleep
from functions.request import sendRequest
from threading import Thread

bridge_config = configManager.bridgeConfig.json_config
dxState = configManager.runtimeConfig.dxState
logging = logManager.logger.get_logger(__name__)

def generateDxState():
    for sensor in bridge_config["sensors"]:
        if sensor not in dxState["sensors"] and "state" in bridge_config["sensors"][sensor]:
            dxState["sensors"][sensor] = {"state": {}}
            for key in bridge_config["sensors"][sensor]["state"].keys():
                if key in ["lastupdated", "presence", "flag", "dark", "daylight", "status"]:
                    dxState["sensors"][sensor]["state"].update({key: datetime.now()})
    for group in bridge_config["groups"]:
        if group not in dxState["groups"] and "state" in bridge_config["groups"][group]:
            dxState["groups"][group] = {"state": {}}
            for key in bridge_config["groups"][group]["state"].keys():
                dxState["groups"][group]["state"].update({key: datetime.now()})
    for light in bridge_config["lights"]:
        if light not in dxState["lights"] and "state" in bridge_config["lights"][light]:
            dxState["lights"][light] = {"state": {}}
            for key in bridge_config["lights"][light]["state"].keys():
                if key in ["on", "bri", "colormode", "reachable"]:
                    dxState["lights"][light]["state"].update({key: datetime.now()})


def rulesProcessor(device, current_time):
    bridge_config["config"]["localtime"] = current_time.strftime("%Y-%m-%dT%H:%M:%S") #required for operator dx to address /config/localtime
    actionsToExecute = []
    for rule in bridge_config["rules"].keys():
        if bridge_config["rules"][rule]["status"] == "enabled":
            rule_result = checkRuleConditions(rule, device, current_time)
            if rule_result[0]:
                if rule_result[1] == 0: #is not ddx rule
                    logging.info("rule " + rule + " is triggered")
                    bridge_config["rules"][rule]["lasttriggered"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
                    bridge_config["rules"][rule]["timestriggered"] += 1
                    for action in bridge_config["rules"][rule]["actions"]:
                        actionsToExecute.append(action)
                else: #if ddx rule
                    logging.info("ddx rule " + rule + " will be re validated after " + str(rule_result[1]) + " seconds")
                    Thread(target=ddxRecheck, args=[rule, device, current_time, rule_result[1], rule_result[2]]).start()
    for action in actionsToExecute:
        sendRequest("/api/" +    list(bridge_config["config"]["whitelist"])[0] + action["address"], action["method"], json.dumps(action["body"]))



def checkRuleConditions(rule, device, current_time, ignore_ddx=False):
    ddx = 0
    device_found = False
    ddx_sensor = []
    for condition in bridge_config["rules"][rule]["conditions"]:
        try:
            url_pices = condition["address"].split('/')
            if url_pices[1] == device[0] and url_pices[2] == device[1]:
                device_found = True
            if condition["operator"] == "eq":
                if condition["value"] == "true":
                    if not bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]:
                        return [False, 0]
                elif condition["value"] == "false":
                    if bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]:
                        return [False, 0]
                else:
                    if not int(bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]) == int(condition["value"]):
                        return [False, 0]
            elif condition["operator"] == "gt":
                if not int(bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]) > int(condition["value"]):
                    return [False, 0]
            elif condition["operator"] == "lt":
                if not int(bridge_config[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]]) < int(condition["value"]):
                    return [False, 0]
            elif condition["operator"] == "dx":
                if not dxState[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]] == current_time:
                    return [False, 0]
            elif condition["operator"] == "in":
                periods = condition["value"].split('/')
                if condition["value"][0] == "T":
                    timeStart = datetime.strptime(periods[0], "T%H:%M:%S").time()
                    timeEnd = datetime.strptime(periods[1], "T%H:%M:%S").time()
                    now_time = datetime.now().time()
                    if timeStart < timeEnd:
                        if not timeStart <= now_time <= timeEnd:
                            return [False, 0]
                    else:
                        if not (timeStart <= now_time or now_time <= timeEnd):
                            return [False, 0]
            elif condition["operator"] == "ddx" and ignore_ddx is False:
                if not dxState[url_pices[1]][url_pices[2]][url_pices[3]][url_pices[4]] == current_time:
                        return [False, 0]
                else:
                    ddx = int(condition["value"][2:4]) * 3600 + int(condition["value"][5:7]) * 60 + int(condition["value"][-2:])
                    ddx_sensor = url_pices
        except Exception as e:
            logging.info("rule " + rule + " failed, reason:" + str(e))


    if device_found:
        return [True, ddx, ddx_sensor]
    else:
        return [False]


def ddxRecheck(rule, device, current_time, ddx_delay, ddx_sensor):
    for x in range(ddx_delay):
        if current_time != dxState[ddx_sensor[1]][ddx_sensor[2]][ddx_sensor[3]][ddx_sensor[4]]:
            logging.info("ddx rule " + rule + " canceled after " + str(x) + " seconds")
            return # rule not valid anymore because sensor state changed while waiting for ddx delay
        sleep(1)
    current_time = datetime.now()
    rule_state = checkRuleConditions(rule, device, current_time, True)
    if rule_state[0]: #if all conditions are meet again
        logging.info("delayed rule " + rule + " is triggered")
        bridge_config["rules"][rule]["lasttriggered"] = current_time.strftime("%Y-%m-%dT%H:%M:%S")
        bridge_config["rules"][rule]["timestriggered"] += 1
        for action in bridge_config["rules"][rule]["actions"]:
            sendRequest("/api/" + bridge_config["rules"][rule]["owner"] + action["address"], action["method"], json.dumps(action["body"]))
