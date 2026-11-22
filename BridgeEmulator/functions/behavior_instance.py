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


def _motionAreaServiceReference(configuration):
    """Return the explicit MotionAware service used by a Hue behavior."""
    if not isinstance(configuration, dict):
        return None

    motion = configuration.get("motion", {})
    if not isinstance(motion, dict):
        return None

    service = motion.get("motion_service")
    if not isinstance(service, dict):
        return None

    rid = service.get("rid")
    rtype = service.get("rtype")

    if (
        not isinstance(rid, str)
        or not rid
        or rtype not in (
            "convenience_area_motion",
            "security_area_motion",
        )
    ):
        return None

    return {
        "rid": rid,
        "rtype": rtype,
    }


def _motionAreaServiceIsEnabled(area_id, configuration):
    """Check the current persisted enable state of a behavior's service."""
    service = _motionAreaServiceReference(configuration)
    if service is None:
        return True

    config = bridgeConfig.get("config", {})
    if not isinstance(config, dict):
        return True

    motion_aware = config.get("motion_aware", {})
    if not isinstance(motion_aware, dict):
        return True

    areas = motion_aware.get("areas", {})
    if not isinstance(areas, dict):
        return True

    area = areas.get(area_id)
    if not isinstance(area, dict):
        return True

    if area.get("enabled") is False:
        return False

    service_state = area.get(service["rtype"], {})
    if not isinstance(service_state, dict):
        return True

    return service_state.get("enabled") is not False


def _motionAreaDelayedNoMotion(
    area_id,
    configuration,
    actions,
    targets,
    generation,
):
    delay = _motionAreaDelaySeconds(actions)
    if delay:
        sleep(delay)
    with _motion_area_lock:
        if _motion_area_generation.get(area_id) != generation:
            return

    # The service may have been disabled while the no-motion timer slept.
    # Do not execute an action belonging to a service that no longer reports.
    if not _motionAreaServiceIsEnabled(area_id, configuration):
        return

    # ``after``/``timer`` describes scheduling, not an action list.  Passing
    # it to the legacy action executor makes it iterate a duration dictionary
    # and prevents the actual no-motion action from running.
    executable = {
        key: value
        for key, value in actions.items()
        if key not in ("after", "timer")
    }
    executeActions(executable, targets)


def cancelMotionAwareBehaviorInstances(area_id):
    """Invalidate pending delayed actions for a MotionAware area."""
    if not isinstance(area_id, str) or not area_id:
        return False

    with _motion_area_lock:
        _motion_area_generation[area_id] = (
            _motion_area_generation.get(area_id, 0) + 1
        )

    return True


def checkMotionAwareBehaviorInstances(
    area_id,
    motion,
    active_service_ids=None,
):
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

        service = _motionAreaServiceReference(configuration)

        # Runtime dispatch provides the exact service IDs whose V2 state
        # actually transitioned. A behavior explicitly bound to another
        # MotionAware service must not execute.
        if (
            active_service_ids is not None
            and service is not None
            and service["rid"] not in active_service_ids
        ):
            continue

        if not _motionAreaServiceIsEnabled(area_id, configuration):
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
                args=(
                    area_id,
                    configuration,
                    actions,
                    targets,
                    generation,
                ),
                daemon=True,
            ).start()
        executed += 1

    return executed


def _resolveDevice(obj):
    """Return (device, element) for a Device or for one of its v1 elements."""
    if hasattr(obj, "elements"):
        return obj, None
    for device in bridgeConfig.get("device", {}).values():
        for element in device.elements.values():
            if element() is obj:
                return device, obj
    return None, obj


def _switchElement(device, element):
    if element is not None and element.type != "ZLLRelativeRotary":
        return element
    for key in ("ZLLSwitch", "ZHASwitch", "ZGPSwitch"):
        if key in device.elements and device.elements[key]():
            return device.elements[key]()
    return device.firstElement()


def _buttonKey(buttonevent):
    if buttonevent < 2000:
        return 1
    elif buttonevent < 3000:
        return 2
    elif buttonevent < 4000:
        return 3
    return 4


def _resolveTargets(where):
    """Groups and lights referenced by a behavior instance "where" list."""
    targets = []
    for resource in where or []:
        target = None
        if "group" in resource:
            target = findGroup(resource["group"]["rid"], resource["group"]["rtype"])
        elif "light" in resource:
            target = findLight(resource["light"]["rid"], resource["light"]["rtype"])
        if target is not None:
            targets.append(target)
    return targets


def _anyOn(targets):
    any_on = False
    for resource in targets:
        if hasattr(resource, "update_state"):  # is group
            if resource.update_state()["any_on"]:
                any_on = True
        elif resource.state.get("on"):  # is light
            any_on = True
    return any_on


def _runButtonAction(action_cfg, targets):
    """Execute one configured button action (old and *_extended formats)."""
    if "time_based" in action_cfg or "time_based_extended" in action_cfg:
        if "time_based" in action_cfg:
            turn_off = True
            slots = action_cfg["time_based"]
            if isinstance(slots, dict):
                slots = slots.get("slots", [])
        else:
            turn_off = action_cfg["time_based_extended"].get("with_off", {}).get("enabled", False)
            slots = action_cfg["time_based_extended"].get("slots", [])
        if turn_off and _anyOn(targets):
            for resource in targets:
                resource.setV1Action({"on": False})
            return
        allTimes = []
        for slot in slots:
            allTimes.append({"hour": slot["start_time"]["hour"], "minute": slot["start_time"]["minute"], "actions": slot["actions"]})
        for action in findTriggerTime(allTimes):
            if "recall" in action["action"] and action["action"]["recall"]["rtype"] == "scene":
                callScene(action["action"]["recall"]["rid"])
    elif "scene_cycle" in action_cfg:
        callScene(random.choice(action_cfg["scene_cycle"])[0]["action"]["recall"]["rid"])
    elif "scene_cycle_extended" in action_cfg:
        slots = action_cfg["scene_cycle_extended"].get("slots", [])
        if slots:
            callScene(random.choice(slots)[0]["action"]["recall"]["rid"])
    elif "recall_single_extended" in action_cfg:
        for action in action_cfg["recall_single_extended"].get("actions", []):
            if "recall" in action["action"] and action["action"]["recall"]["rtype"] == "scene":
                callScene(action["action"]["recall"]["rid"])
    elif "action" in action_cfg:
        for resource in targets:
            if action_cfg["action"] == "all_off":
                resource.setV1Action({"on": False})
            elif action_cfg["action"] == "dim_up":
                resource.setV1Action({"bri_inc": +30})
            elif action_cfg["action"] == "dim_down":
                resource.setV1Action({"bri_inc": -30})


def _handleSwitch(device, switch, instance):
    buttonevent = switch.state.get("buttonevent")
    if buttonevent is None:
        return
    number = _buttonKey(buttonevent)
    lastDigit = buttonevent % 1000
    configuration = instance.configuration
    if "button" + str(number) in configuration or "button1" in configuration:
        # Per-button format (tap dial, newer Hue app): button1..button4
        button_cfg = configuration.get("button" + str(number))
        if button_cfg is None:
            return
        buttonAction = {0: "on_initial_press", 1: "on_long_press", 2: "on_short_release", 3: "on_long_release"}.get(lastDigit)
        if buttonAction is None or buttonAction not in button_cfg:
            return
        _runButtonAction(button_cfg[buttonAction], _resolveTargets(button_cfg.get("where", configuration.get("where", []))))
    elif "buttons" in configuration:
        # Dimmer switch format: buttons keyed by button service id
        button = str(uuid.uuid5(uuid.NAMESPACE_URL, device.id_v2 + 'button' + str(number)))
        if button not in configuration["buttons"]:
            return
        button_cfg = configuration["buttons"][button]
        buttonAction = {0: "on_short_press", 1: "on_repeat", 2: "on_short_release", 3: "on_long_press"}.get(lastDigit)
        if buttonAction is None or buttonAction not in button_cfg:
            return
        # The Hue app stores "where" on each button; older configs have it once at the top level.
        targets = _resolveTargets(button_cfg.get("where", configuration.get("where", [])))
        _runButtonAction(button_cfg[buttonAction], targets)


def _handleRotary(rotary, instance):
    """Tap dial rotary: dim the configured groups, switching them on/off at the ends."""
    direction = rotary.state.get("direction", "clock_wise")
    bri_inc = rotary.state.get("rotary_step_size", 8)
    rotary_cfg = instance.configuration.get("rotary", {})
    for group in _resolveTargets(rotary_cfg.get("where", [])):
        if not hasattr(group, "update_state"):
            continue
        if direction in ("counter_clock_wise", "left"):
            state = group.update_state()
            # avr_bri is 0-100%; bri_inc is raw 0-254 step — convert to same scale
            current_bri_pct = state.get("avr_bri", 0) if state.get("any_on") else 0
            bri_inc_pct = int((bri_inc / 254) * 100)
            if current_bri_pct <= bri_inc_pct:
                # brightness would hit 0 — apply on_dim_off action
                if rotary_cfg.get("on_dim_off", {}).get("action") == "all_off":
                    group.setV1Action({"on": False})
            else:
                group.setV1Action({"bri_inc": -bri_inc, "transitiontime": 4})
        else:
            if not group.update_state()["any_on"]:
                # lights off — apply on_dim_on action (turn on at min brightness)
                group.setV1Action({"on": True, "bri": 1, "transitiontime": 4})
            else:
                group.setV1Action({"bri_inc": +bri_inc, "transitiontime": 4})


def checkBehaviorInstances(device, element=None):
    """Run the behavior instances of a device.

    ``device`` is a v2 Device, or one of its v1 elements (sensor); ``element``
    is the v1 element that changed, when known.
    """
    logging.debug("enter checkBehaviorInstances")
    resolved, trigger = _resolveDevice(device)
    if resolved is None:
        return
    device = resolved
    element = element or trigger
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
        lightsAndGroups = _resolveTargets(instance.configuration.get("where", []))
        if device.modelid in ["RWL022", "RWL021", "RWL020", "RDM002"] or (element is not None and element.type in ["ZLLSwitch", "ZLLRelativeRotary"]):
            if element is not None and element.type == "ZLLRelativeRotary":
                _handleRotary(element, instance)
            else:
                _handleSwitch(device, _switchElement(device, element), instance)
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
