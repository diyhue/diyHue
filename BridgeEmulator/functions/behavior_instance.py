"""
Behavior instance execution engine.

A *behavior instance* is the Hue v2 API concept for a programmable automation
rule attached to a physical device (switch, dial, motion sensor).  Think of it
as a webhook handler: when the bridge sees a sensor event it calls
``checkBehaviorInstances`` which finds every enabled behavior instance that
references that device and executes the configured action.

Supported action types per button:
  - ``time_based_extended``   — recalls a different scene depending on the time of day
  - ``recall_single_extended``— always recalls the same scene
  - ``scene_cycle_extended``  — cycles through a list of scenes on repeated presses
  - ``action: "all_off"``     — turns all lights in the room off
  - ``action: "dim_up/down"`` — adjusts brightness by a fixed step

The rotary encoder on a tap dial switch always maps to brightness dim up/down
(``ZLLRelativeRotary`` sensor type).

Motion sensors (``ZLLPresence``) trigger a time-slot based scene recall on
motion-start and a countdown-then-off on motion-end.
"""

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
    # Collect all id_v2 values that behavior instances might reference for this device
    device_ids = {device.id_v2}
    if device.parent_id_v2:
        device_ids.add(device.parent_id_v2)
    if device.uniqueid:
        for sensor in bridgeConfig["sensors"].values():
            if sensor.uniqueid == device.uniqueid and sensor.type == device.type:
                device_ids.add(sensor.id_v2)
    matchedInstances = []
    for key, instance in bridgeConfig["behavior_instance"].items():
        if instance.enabled == True:
            try:
                if "source" in instance.configuration:
                    if instance.configuration["source"]["rtype"] == "device" and instance.configuration["source"]["rid"] in device_ids:
                        matchedInstances.append(instance)
                elif "device" in instance.configuration:
                    if instance.configuration["device"]["rtype"] == "device" and instance.configuration["device"]["rid"] in device_ids:
                        matchedInstances.append(instance)
            except KeyError:
                pass

    for instance in matchedInstances:
        if device.type == "ZLLSwitch" and "button1" in instance.configuration: # New per-button format (RDM002 / H56)
            buttonevent = device.state.get("buttonevent")
            if buttonevent is None:
                continue
            if buttonevent < 2000:
                button_key = "button1"
            elif buttonevent < 3000:
                button_key = "button2"
            elif buttonevent < 4000:
                button_key = "button3"
            else:
                button_key = "button4"
            if button_key not in instance.configuration:
                continue
            button_cfg = instance.configuration[button_key]
            lastDigit = buttonevent % 1000
            if lastDigit == 0:
                buttonAction = "on_initial_press"
            elif lastDigit == 1:
                buttonAction = "on_long_press"    # hold — fires while held, before release
            elif lastDigit == 2:
                buttonAction = "on_short_release"
            elif lastDigit == 3:
                buttonAction = "on_long_release"  # hold_release — fires on release after hold
            else:
                continue
            if buttonAction not in button_cfg:
                continue
            action_cfg = button_cfg[buttonAction]
            where = button_cfg.get("where", [])
            for resource in where:
                if "group" not in resource:
                    continue
                group = findGroup(resource["group"]["rid"], resource["group"]["rtype"])
                if group is None:
                    continue
                if "time_based_extended" in action_cfg:
                    any_on = group.update_state()["any_on"]
                    if any_on and action_cfg["time_based_extended"].get("with_off", {}).get("enabled", False):
                        group.setV1Action({"on": False})
                        continue
                    slots = action_cfg["time_based_extended"].get("slots", [])
                    allTimes = [{"hour": s["start_time"]["hour"], "minute": s["start_time"]["minute"], "actions": s["actions"]} for s in slots]
                    actions = findTriggerTime(allTimes)
                    for action in actions:
                        if "recall" in action["action"] and action["action"]["recall"]["rtype"] == "scene":
                            callScene(action["action"]["recall"]["rid"])
                elif "recall_single_extended" in action_cfg:
                    cfg = action_cfg["recall_single_extended"]
                    for action in cfg.get("actions", []):
                        if "recall" in action["action"] and action["action"]["recall"]["rtype"] == "scene":
                            callScene(action["action"]["recall"]["rid"])
                elif "scene_cycle_extended" in action_cfg:
                    cfg = action_cfg["scene_cycle_extended"]
                    slots = cfg.get("slots", [])
                    if slots:
                        callScene(random.choice(slots)[0]["action"]["recall"]["rid"])
                elif "action" in action_cfg:
                    act = action_cfg["action"]
                    if act == "all_off":
                        group.setV1Action({"on": False})
                    elif act == "dim_up":
                        group.setV1Action({"bri_inc": +30})
                    elif act == "dim_down":
                        group.setV1Action({"bri_inc": -30})

        elif device.type == "ZLLSwitch": #Hue dimmer switch (old format)
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

        elif device.type == "ZLLRelativeRotary": # Hue tap dial switch - rotary
            direction = device.state.get("direction", "clock_wise")
            bri_inc = device.state.get("rotary_step_size", 8)
            rotary_cfg = instance.configuration.get("rotary", {})
            where = rotary_cfg.get("where", [])
            for resource in where:
                if "group" not in resource:
                    continue
                group = findGroup(resource["group"]["rid"], resource["group"]["rtype"])
                if group is None:
                    continue
                if direction == "counter_clock_wise":
                    state = group.update_state()
                    # avr_bri is 0-100%; bri_inc is raw 0-254 step — convert to same scale
                    current_bri_pct = state.get("avr_bri", 0) if state.get("any_on") else 0
                    bri_inc_pct = int((bri_inc / 254) * 100)
                    if current_bri_pct <= bri_inc_pct:
                        # brightness would hit 0 — apply on_dim_off action
                        dim_off_action = rotary_cfg.get("on_dim_off", {}).get("action")
                        if dim_off_action == "all_off":
                            group.setV1Action({"on": False})
                    else:
                        group.setV1Action({"bri_inc": -bri_inc, "transitiontime": 4})
                else:
                    if not group.update_state()["any_on"]:
                        # lights off — apply on_dim_on action (turn on at min brightness)
                        group.setV1Action({"on": True, "bri": 1, "transitiontime": 4})
                    else:
                        group.setV1Action({"bri_inc": +bri_inc, "transitiontime": 4})

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
