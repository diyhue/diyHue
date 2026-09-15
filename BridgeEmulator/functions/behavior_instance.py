import logManager
import configManager
import uuid
import random
from datetime import datetime
from threading import Thread, RLock
from time import sleep
logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config
from pprint import pprint

_motion_area_lock = RLock()
_motion_area_generation = {}

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
    
    
def findLight(rid, rtype):
    for key, obj in bridgeConfig["lights"].items():
        if str(uuid.uuid5(uuid.NAMESPACE_URL, obj.id_v2)) == rid:
            return obj
    logging.info("Light not found!!!!")

def threadDelayAction(actionsToExecute, device, monitoredKey, monitoredValue, groupsAndLights):
    secondsCounter = 0
    storeBriLevel = {}
    if "after" in actionsToExecute:
        if "minutes" in actionsToExecute["after"]:
            secondsCounter = actionsToExecute["after"]["minutes"] * 60
        if "seconds" in actionsToExecute["after"]:
            secondsCounter += actionsToExecute["after"]["seconds"]
    elif "timer" in actionsToExecute:
        if "minutes" in actionsToExecute["timer"]["duration"]:
            secondsCounter =  actionsToExecute["timer"]["duration"]["minutes"] * 60
        if "seconds" in  actionsToExecute["timer"]["duration"]:
            secondsCounter +=  actionsToExecute["timer"]["duration"]["seconds"]
    logging.debug("to wait " + str(secondsCounter))
    while device.state[monitoredKey] == monitoredValue:
        if secondsCounter == 0:
            executeActions(actionsToExecute, groupsAndLights)
            return  
        secondsCounter -= 1
        if secondsCounter == 30:
            print("#### Seconds Counter 30." )
            #try:
            if actionsToExecute["recall_single"][0]["action"] == "all_off":
                for resource in groupsAndLights:
                    if hasattr(resource, 'action'): # it is a group
                        print("#### It is group." )
                        for lightDevice in resource.lights: 
                            storeBriLevel[lightDevice().firstElement()] = lightDevice().firstElement().state["bri"]
                            resource.setV1Action({"bri_inc": -128})
                    else: # it is a light
                        storeBriLevel[resource] = resource.state["bri"]
                        resource.setV1State({"bri_inc": -128})
            #except KeyError:
            #    print("#####ERROR")
            #    pass
        sleep(1)
    logging.info("Motion detected " + device.name + ", cancel the counter..." )
    if storeBriLevel: #lighs dimming was applied
        for light in storeBriLevel.keys():
            logging.info("Restore the light " + light.name + " level to " + str(storeBriLevel[light]))
            light.setV1State({"bri": storeBriLevel[light]})
        
    

def executeActions(actionsToExecute, groupsAndLights):
    recall = "recall"
    if "recall_single" in actionsToExecute: # need to discover the differences between recall and recall_single
        recall = "recall_single"
    logging.info("execute routine action")
    if recall in actionsToExecute:
        for action in actionsToExecute[recall]:
            if action["action"] == "all_off":
                for resource in groupsAndLights:
                    if resource is None:
                        continue
                    resource.setV1Action({"on": False})
                    logging.info("routine turning lights off " + resource.name)
            elif "recall" in action["action"] and action["action"]["recall"]["rtype"] == "scene":
                callScene(action["action"]["recall"]["rid"])


def _motionAreaTargets(configuration):
    """Resolve the Hue behavior `motion.where` targets."""
    motion = configuration.get("motion", {})
    where = motion.get("where", []) if isinstance(motion, dict) else []
    if not where:
        where = configuration.get("where", [])

    targets = []
    for resource in where:
        if not isinstance(resource, dict):
            continue
        if isinstance(resource.get("group"), dict):
            group_ref = resource["group"]
            target = findGroup(group_ref.get("rid"), group_ref.get("rtype"))
        elif isinstance(resource.get("light"), dict):
            light_ref = resource["light"]
            target = findLight(light_ref.get("rid"), light_ref.get("rtype"))
        else:
            target = None
        if target is not None:
            targets.append(target)
    return targets


def _motionAreaSlotActions(configuration, event):
    """Select the current Hue timeslot and return its motion actions."""
    motion = configuration.get("motion", {})
    when = motion.get("when", {}) if isinstance(motion, dict) else {}
    slots = when.get("timeslots", []) if isinstance(when, dict) else []
    if not isinstance(slots, list) or not slots:
        return {}

    normalized = []
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        start_time = slot.get("start_time", {})
        time_value = start_time.get("time", start_time)
        if not isinstance(time_value, dict):
            continue
        try:
            hour = int(time_value["hour"])
            minute = int(time_value["minute"])
        except (KeyError, TypeError, ValueError):
            continue
        normalized.append({
            "hour": hour,
            "minute": minute,
            "actions": slot.get("on_motion" if event else "on_no_motion", {}),
        })

    if not normalized:
        return {}
    return findTriggerTime(normalized)


def _motionAreaDelaySeconds(actions):
    for key in ("after", "timer"):
        value = actions.get(key) if isinstance(actions, dict) else None
        if not isinstance(value, dict):
            continue
        if key == "timer":
            value = value.get("duration", {})
        if not isinstance(value, dict):
            continue
        try:
            return int(value.get("minutes", 0)) * 60 + int(value.get("seconds", 0))
        except (TypeError, ValueError):
            return 0
    return 0


def _motionAreaDelayedNoMotion(area_id, actions, targets, generation):
    delay = _motionAreaDelaySeconds(actions)
    if delay:
        sleep(delay)
    with _motion_area_lock:
        if _motion_area_generation.get(area_id) != generation:
            return
    executeActions(actions, targets)


def checkMotionAwareBehaviorInstances(area_id, motion):
    """Execute Hue-created local behaviors for a MotionAware transition.

    MotionAware is a service source, not a physical sensor device, so the
    existing ``checkBehaviorInstances(device)`` dispatcher cannot reach these
    instances.  This narrow adapter consumes the stock behavior shape and
    reuses the established scene/group executor.
    """
    if not isinstance(area_id, str) or not isinstance(motion, bool):
        return 0

    with _motion_area_lock:
        generation = _motion_area_generation.get(area_id, 0) + 1
        _motion_area_generation[area_id] = generation

    # Editing/recreating an area can leave historical instances in the
    # datastore.  They share the same MotionArea source but may recall stale
    # scenes.  The last persisted matching instance is the current app
    # configuration; dispatch only that one.
    matching = []
    for instance in bridgeConfig.get("behavior_instance", {}).values():
        if not getattr(instance, "enabled", False):
            continue
        configuration = getattr(instance, "configuration", {})
        if not isinstance(configuration, dict):
            continue
        source = configuration.get("source", {})
        if (
            not isinstance(source, dict)
            or source.get("rtype") != "motion_area_configuration"
            or source.get("rid") != area_id
        ):
            continue

        matching.append(instance)

    if not matching:
        return 0

    executed = 0
    for instance in matching[-1:]:
        configuration = getattr(instance, "configuration", {})

        targets = _motionAreaTargets(configuration)
        if not targets:
            logging.warning(
                "MotionAware behavior %s has no resolvable targets",
                getattr(instance, "id_v2", "unknown"),
            )
            continue

        actions = _motionAreaSlotActions(configuration, motion)
        if not isinstance(actions, dict):
            continue

        if motion:
            executeActions(actions, targets)
        else:
            Thread(
                target=_motionAreaDelayedNoMotion,
                args=(area_id, actions, targets, generation),
                daemon=True,
            ).start()
        executed += 1

    return executed


def checkBehaviorInstances(device):
    logging.debug("enter checkBehaviorInstances")
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
        lightsAndGroups = []
        for resource in instance.configuration["where"]:
            if "group" in resource:
                lightsAndGroups.append(findGroup(resource["group"]["rid"], resource["group"]["rtype"]))
            elif "light" in resource:
                lightsAndGroups.append(findLight(resource["light"]["rid"], resource["light"]["rtype"]))
        if device.modelid in ["RWL022", "RWL021", "RWL020"]: #Hue dimmer switch
            button = None
            if device.firstElement().state["buttonevent"] < 2000:
              button = str(uuid.uuid5(uuid.NAMESPACE_URL, device.id_v2  + 'button1'))
            elif device.firstElement().state["buttonevent"] < 3000:
              button = str(uuid.uuid5(uuid.NAMESPACE_URL, device.id_v2  + 'button2'))
            elif device.firstElement().state["buttonevent"] < 4000:
              button = str(uuid.uuid5(uuid.NAMESPACE_URL, device.id_v2  + 'button3'))
            else:
              button = str(uuid.uuid5(uuid.NAMESPACE_URL, device.id_v2  + 'button4'))
            if button in instance.configuration["buttons"]:
                lastDigit = device.firstElement().state["buttonevent"] % 1000
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
                        for resource in lightsAndGroups:
                            if "any_on" in resource.state: # is group
                                if resource.state["any_on"] == True:
                                    any_on = True
                            if "on" in resource.state: # is light
                                if resource.state["on"] == True:
                                    any_on = True
                            resource.setV1Action({"on": False})
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
                        for resource in lightsAndGroups:
                            if instance.configuration["buttons"][button][buttonAction]["action"] == "all_off":
                                resource.setV1Action({"on": False})
                            elif instance.configuration["buttons"][button][buttonAction]["action"] == "dim_up":
                                resource.setV1Action({"bri_inc": +30})
                            elif instance.configuration["buttons"][button][buttonAction]["action"] == "dim_down":
                                resource.setV1Action({"bri_inc": -30})
        elif device.modelid == "SML001": # Motion Sensor
            if "settings" in instance.configuration:
                if "daylight_sensitivity" in instance.configuration["settings"]:
                    if device.elements["ZLLLightLevel"]().protocol_cfg["lightSensor"] == "on":
                        device.elements["ZLLLightLevel"]().state["lightlevel"] = 25000 if bridgeConfig["sensors"]["1"].state["daylight"] else 6000
                    if instance.configuration["settings"]["daylight_sensitivity"]["dark_threshold"] >= device.elements["ZLLLightLevel"]().state["lightlevel"]:
                        logging.debug("Light ok")
                    else:
                        logging.debug("Light ko")
                        return
            motion = device.elements["ZLLPresence"]().state["presence"]
            any_on = False
            for resource in lightsAndGroups:
                if "any_on" in resource.state: # is group
                    if resource.update_state()["any_on"] == True:
                        any_on = True
            
            if "timeslots" in instance.configuration["when"]:
                allSlots = []
                for slot in instance.configuration["when"]["timeslots"]:
                    allSlots.append({"hour": slot["start_time"]["time"]["hour"], "minute": slot["start_time"]["time"]["minute"], "actions": {"on_motion": slot["on_motion"], "on_no_motion": slot["on_no_motion"]}})
                actions = findTriggerTime(allSlots)
                if motion:
                    if any_on == False: # motion triggeredand lights are off
                        logging.info("Trigger motion routine " + instance.name)
                        executeActions(actions["on_motion"],[])
                else:
                    logging.info("no motion " + device.name)
                    if any_on:
                        Thread(target=threadDelayAction, args=[actions["on_no_motion"], device.elements["ZLLPresence"](), "presence", False, lightsAndGroups]).start()
        elif device.modelid == "SOC001": # secure contact sensor
            actions = {}
            if "timeslots" in instance.configuration["when"]:
                allSlots = []
                for slot in instance.configuration["when"]["timeslots"]:
                    allSlots.append({"hour": slot["start_time"]["time"]["hour"], "minute": slot["start_time"]["time"]["minute"], "actions": {"on_open": slot["on_open"], "on_close": slot["on_close"]}})
                actions = findTriggerTime(allSlots)
            elif "always" in instance.configuration["when"]:
                actions = {"on_open": instance.configuration["when"]["always"]["on_open"], "on_close": instance.configuration["when"]["always"]["on_close"]}
            contact = "on_close" if device.elements["ZLLContact"]().state["contact"] == "contact" else "on_open"
            if "timer" in actions[contact]:
                monitoredValue = "contact" if contact == "on_close" else "no_contact"
                logging.info("Trigger timer routine " + instance.name)
                Thread(target=threadDelayAction, args=[actions[contact], device.elements["ZLLContact"](), "contact", monitoredValue, lightsAndGroups]).start()
            else:
                logging.info("Trigger routine " + instance.name)
                executeActions(actions[contact], lightsAndGroups)
        elif device.modelid == "RDM002": # Hue rotary switch
            buttonDevice = device.elements["ZLLSwitch"]()
            rotaryDevice = device.elements["ZLLRelativeRotary"]()
            button = None
            if buttonDevice.state["buttonevent"] < 2000:
              action = 'button1'
            elif buttonDevice.state["buttonevent"] < 3000:
              button = 'button2'
            elif buttonDevice.state["buttonevent"] < 4000:
              button = 'button3'
            else:
              button = 'button4'
            if button in instance.configuration:
                lastDigit = buttonDevice.state["buttonevent"] % 1000
                buttonAction = None
                if lastDigit == 0:
                    buttonAction = "on_short_press"
                elif lastDigit == 1:
                    buttonAction = "on_repeat"
                elif lastDigit == 2:
                    buttonAction = "on_short_release"
                elif lastDigit == 3:
                    buttonAction = "on_long_press"
                if buttonAction in instance.configuration[button]:
                    lightsAndGroups = []
                    for resource in instance.configuration[button]["where"]:
                        if "group" in resource:
                            lightsAndGroups.append(findGroup(resource["group"]["rid"], resource["group"]["rtype"]))
                        elif "light" in resource:
                            lightsAndGroups.append(findLight(resource["light"]["rid"], resource["light"]["rtype"]))
                    if "time_based_extended" in instance.configuration[button][buttonAction]:
                        if "slots" in instance.configuration[button][buttonAction]["time_based_extended"]:
                            allSlots = []
                            for slot in instance.configuration[button][buttonAction]["time_based_extended"]["slots"]:
                                allSlots.append({"hour": slot["start_time"]["hour"], "minute": slot["start_time"]["minute"], "actions": slot["actions"]})
                            actions = findTriggerTime(allSlots)
                            executeActions(actions,lightsAndGroups)
                            
                    elif "time_based" in instance.configuration[button][buttonAction]:
                        if "slots" in instance.configuration[button][buttonAction]["time_based"]:
                            logging.debug("to be done")
