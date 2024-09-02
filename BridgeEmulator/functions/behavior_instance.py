import logManager
import configManager
import uuid
import random
from datetime import datetime
from threading import Thread
from time import sleep
logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config


def findTriggerTime(times):
    numberOfIntervals = len(times)
    now = datetime.now()
    for i in range(numberOfIntervals - 1):
        start = now.replace(hour=times[i]["hour"], minute=times[i]["minute"], second=0)
        end = now.replace(hour=times[i + 1]["hour"], minute=times[i + 1]["minute"], second=0)
        if start <= now <= end:
            return times[i]["actions"]
    return times[-1]["actions"]

        

def callScene(scene):
   logging.info("callling scene " + scene)
   for key, obj in bridgeConfig["scenes"].items():
        if obj.id_v2 == scene:
            obj.activate({"seconds": 1, "minutes": 0})

def findGroup(rid, rtype):
    for key, obj in bridgeConfig["groups"].items():
        if str(uuid.uuid5(uuid.NAMESPACE_URL, obj.id_v2 + rtype)) == rid:
            return obj
    logging.info("Group not found!!!!")

def threadNoMotion(actionsToExecute, device, group):
    secondsCounter = 0
    if "after" in actionsToExecute:
        if "minutes" in actionsToExecute["after"]:
            secondsCounter = actionsToExecute["after"]["minutes"] * 60
        if "seconds" in actionsToExecute["after"]:
            secondsCounter += actionsToExecute["after"]["seconds"]
    while device.state["presence"] == False:
        if secondsCounter == 0:
            if "recall_single" in actionsToExecute:
                for action in actionsToExecute["recall_single"]:
                    if action["action"] == "all_off":
                        group.setV1Action({"on": False, "transistiontime": 100})
                        logging.info("No motion, turning lights off" )
                        return       
        secondsCounter -= 1
        sleep(1)
    logging.info("Motion detected, cancel the counter..." )
    

def checkBehaviorInstances(device):
    deviceUuid = device.id_v2 
    matchedInstances = []
    for key, instance in bridgeConfig["behavior_instance"].items():
        if instance.enabled == True:
            try:
                if "source" in instance.configuration:
                    if instance.configuration["source"]["rtype"] == "device" and instance.configuration["source"]["rid"] == deviceUuid:
                        matchedInstances.append(instance)
                elif "device" in instance.configuration:
                    if instance.configuration["device"]["rtype"] == "device" and instance.configuration["device"]["rid"] == deviceUuid:
                        matchedInstances.append(instance)
            except KeyError:
                pass

    for instance in matchedInstances:
        if device.type == "ZLLSwitch": #Hue dimmer switch
            button = None
            if device.state["buttonevent"] < 2000:
              button = str(uuid.uuid5(uuid.NAMESPACE_URL, device.id_v2  + 'button1'))
            elif device.state["buttonevent"] < 3000:
              button = str(uuid.uuid5(uuid.NAMESPACE_URL, device.id_v2  + 'button2'))
            elif device.state["buttonevent"] < 4000:
              button = str(uuid.uuid5(uuid.NAMESPACE_URL, device.id_v2  + 'button3'))
            else:
              button = str(uuid.uuid5(uuid.NAMESPACE_URL, device.id_v2  + 'button4'))
            if button in instance.configuration["buttons"]:
                lastDigit = device.state["buttonevent"] % 1000
                buttonAction = None
                if lastDigit == 0:
                    buttonAction = "on_short_press"
                elif lastDigit == 1:
                    buttonAction = "on_repeat"
                elif lastDigit == 2:
                    buttonAction = "on_short_release"
                elif lastDigit == 3:
                    buttonAction = "on_long_press"
                if buttonAction in instance.configuration["buttons"][button]:
                    if "time_based" in instance.configuration["buttons"][button][buttonAction]:
                        any_on = False
                        for resource in instance.configuration["where"]:
                            if "group" in resource:
                                group = findGroup(resource["group"]["rid"], resource["group"]["rtype"])
                                if group.update_state()["any_on"] == True:
                                    any_on = True
                                    group.setV1Action({"on": False})
                        if any_on == True:
                            return
                        allTimes = []
                        for time in instance.configuration["buttons"][button][buttonAction]["time_based"]:
                            allTimes.append({"hour": time["start_time"]["hour"], "minute": time["start_time"]["minute"], "actions": time["actions"]})
                        actions = findTriggerTime(allTimes)
                        for action in actions:
                            if "recall" in action["action"] and action["action"]["recall"]["rtype"] == "scene":
                                callScene(action["action"]["recall"]["rid"])
                    elif "scene_cycle" in instance.configuration["buttons"][button][buttonAction]:
                        callScene(random.choice(instance.configuration["buttons"][button][buttonAction]["scene_cycle"])[0]["action"]["recall"]["rid"])
                    elif "action" in instance.configuration["buttons"][button][buttonAction]:
                        for resource in instance.configuration["where"]:
                            if "group" in resource:
                                group = findGroup(resource["group"]["rid"], resource["group"]["rtype"])
                                if instance.configuration["buttons"][button][buttonAction]["action"] == "all_off":
                                    group.setV1Action({"on": False})
                                elif instance.configuration["buttons"][button][buttonAction]["action"] == "dim_up":
                                    group.setV1Action({"bri_inc": +30})
                                elif instance.configuration["buttons"][button][buttonAction]["action"] == "dim_down":
                                    group.setV1Action({"bri_inc": -30})

        elif device.type == "ZLLPresence": # Motion Sensor
            #if "settings" in instance.configuration:
            #    if "daylight_sensitivity" in instance.configuration["settings"]:
            #        if instance.configuration["settings"]["daylight_sensitivity"]["dark_threshold"] < device.state["lightlevel"]:
            #            print("Light ok")
            #        else:
            #            print("Light ko")
            #            return
            motion = device.state["presence"]
            any_on = False
            for resource in instance.configuration["where"]:
                if "group" in resource:
                    group = findGroup(resource["group"]["rid"], resource["group"]["rtype"])
                    if group.update_state()["any_on"] == True:
                        any_on = True
            
            if "timeslots" in instance.configuration["when"]:
                allSlots = []
                for slot in instance.configuration["when"]["timeslots"]:
                    allSlots.append({"hour": slot["start_time"]["time"]["hour"], "minute": slot["start_time"]["time"]["minute"], "actions": {"on_motion": slot["on_motion"], "on_no_motion": slot["on_no_motion"]}})
                actions = findTriggerTime(allSlots)
                if motion:
                    if any_on == False: # motion triggeredand lights are off
                        if "recall_single" in actions["on_motion"]:
                            for action in actions["on_motion"]["recall_single"]:
                                if "recall" in action["action"]:
                                    if action["action"]["recall"]["rtype"] == "scene":
                                        callScene(action["action"]["recall"]["rid"])
                else:
                    logging.info("no motion")
                    if any_on:
                        Thread(target=threadNoMotion, args=[actions["on_no_motion"], device, group]).start()
