import logManager
import configManager

from datetime import datetime
from threading import Thread
from time import sleep
import requests

logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config

def in_time_interval(value, now):
    """Whether `now` falls in a Hue time interval.

    The value is "T08:00:00/T10:00:00", optionally prefixed with a weekday
    bitmask, "W124/T08:00:00/T10:00:00" (bit 6 is Monday, bit 0 Sunday). An
    interval whose start is after its end runs past midnight; the weekday is
    the one it starts on.
    """
    parts = value.split('/')
    weekdays = 127
    if parts[0].startswith("W"):
        weekdays = int(parts[0][1:])
        parts = parts[1:]
    timeStart = datetime.strptime(parts[0], "T%H:%M:%S").time()
    timeEnd = datetime.strptime(parts[1], "T%H:%M:%S").time()
    now_time = now.time()
    day = now.weekday()  # Monday is 0
    if timeStart <= timeEnd:
        inside = timeStart <= now_time <= timeEnd
    elif timeStart <= now_time:
        inside = True
    elif now_time <= timeEnd:
        inside = True
        day = (day - 1) % 7  # still the interval that started yesterday
    else:
        inside = False
    return inside and bool(weekdays & (1 << (6 - day)))


def checkRuleConditions(rule, device, current_time, ignore_ddx=False):
    #logging.debug("Check " + rule.id_v1)
    ddx = 0
    device_found = False
    ddx_sensor = []
    for condition in rule.conditions:
        try:
            url_pices = condition["address"].split('/')
            if url_pices[1] == device.getObjectPath()["resource"] and url_pices[2] == device.getObjectPath()["id"]:
                device_found = True
                #logging.debug("device found")
            if condition["operator"] == "eq":
                if condition["value"] == "true":
                    if not bridgeConfig[url_pices[1]][url_pices[2]].state[url_pices[4]]:
                        return [False, 0]
                elif condition["value"] == "false":
                    if bridgeConfig[url_pices[1]][url_pices[2]].state[url_pices[4]]:
                        return [False, 0]
                else:
                    if not int(bridgeConfig[url_pices[1]][url_pices[2]].state[url_pices[4]]) == int(condition["value"]):
                        return [False, 0]
            elif condition["operator"] == "gt":
                if not int(bridgeConfig[url_pices[1]][url_pices[2]].state[url_pices[4]]) > int(condition["value"]):
                    return [False, 0]
            elif condition["operator"] == "lt":
                if not int(bridgeConfig[url_pices[1]][url_pices[2]].state[url_pices[4]]) < int(condition["value"]):
                    return [False, 0]
            elif condition["operator"] == "dx":
                if device_found == False or not bridgeConfig[url_pices[1]][url_pices[2]].dxState[url_pices[4]] == current_time:
                    return [False, 0]
            elif condition["operator"] in ("in", "not in"):
                inside = in_time_interval(condition["value"], datetime.now())
                if inside != (condition["operator"] == "in"):
                    return [False, 0]
            elif condition["operator"] == "ddx" and ignore_ddx is False:
                if not bridgeConfig[url_pices[1]][url_pices[2]].dxState[url_pices[4]] == current_time:
                    return [False, 0]
                else:
                    ddx = int(condition["value"][2:4]) * 3600 + int(condition["value"][5:7]) * 60 + int(condition["value"][-2:])
                    ddx_sensor = url_pices
        except Exception as e:
            logging.exception("rule " + rule.name + " failed, reason: " + str(type(e).__name__) + " " + str(e))


    if device_found:
        return [True, ddx, ddx_sensor]
    else:
        return [False]

def ddxRecheck(rule, device, current_time, ddx_delay, ddx_sensor):
    for x in range(ddx_delay):
        if current_time != bridgeConfig[ddx_sensor[1]][ddx_sensor[2]].dxState[ddx_sensor[4]]:
            logging.info("ddx rule " + rule.id_v1 + ", name: " + rule.name + " canceled after " + str(x) + " seconds")
            return # rule not valid anymore because sensor state changed while waiting for ddx delay
        sleep(1)
    current_time = datetime.now()
    rule_state = checkRuleConditions(rule, device, current_time, True)
    if rule_state[0]: #if all conditions are meet again
        logging.info("delayed rule " + rule.id_v1 + ", name: " + rule.name + " is triggered")
        rule.lasttriggered = current_time.strftime("%Y-%m-%dT%H:%M:%S")
        rule.timestriggered += 1
        for action in rule.actions:
            if action["method"] == "POST":
                requests.post("http://localhost/api/local" + action["address"], json=action["body"], timeout=5)
            elif action["method"] == "PUT":
                requests.put("http://localhost/api/local" + action["address"], json=action["body"], timeout=5)

def threadActions(actionsToExecute):
    sleep(0.2)
    for action in actionsToExecute:
        urlPrefix = "http://localhost/api/local"
        if action["address"].startswith("http"):
            urlPrefix = ""
        if action["method"] == "POST":
            requests.post( urlPrefix + action["address"], json=action["body"], timeout=5)
        elif action["method"] == "PUT":
            requests.put( urlPrefix + action["address"], json=action["body"], timeout=5)


def rulesProcessor(device, current_time):
    logging.debug("Processing rules for " + device.name)
    bridgeConfig["config"]["localtime"] = current_time.strftime("%Y-%m-%dT%H:%M:%S") #required for operator dx to address /config/localtime
    actionsToExecute = []
    for key, rule in bridgeConfig["rules"].items():
        if rule.status == "enabled":
            rule_result = checkRuleConditions(rule, device, current_time)
            if rule_result[0]:
                if rule_result[1] == 0: #is not ddx rule
                    logging.info("rule " + rule.id_v1 + ", name: " + rule.name + " is triggered")
                    rule.lasttriggered = current_time.strftime("%Y-%m-%dT%H:%M:%S")
                    rule.timestriggered += 1
                    for action in rule.actions:
                        actionsToExecute.append(action)
                else: #if ddx rule
                    logging.info("ddx rule " + rule.id_v1 + ", name: " + rule.name + " will be re validated after " + str(rule_result[1]) + " seconds")
                    Thread(target=ddxRecheck, args=[rule, device, current_time, rule_result[1], rule_result[2]]).start()

    Thread(target=threadActions, args=[actionsToExecute]).start()
