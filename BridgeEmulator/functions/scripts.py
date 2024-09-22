import logManager
import configManager
from time import sleep
from random import randrange

logging = logManager.logger.get_logger(__name__)
bridgeConfig = configManager.bridgeConfig.yaml_config

def findScene(element):
    for scene, obj in bridgeConfig["scenes"].items():
        if element["group"]["rtype"] == "room":
            if obj.id_v2 == element["recall"]["rid"] and obj.group().getV2Room()["id"] == element["group"]["rid"]:
                return obj
        elif element["group"]["rtype"] == "zone":
            if obj.id_v2 == element["recall"]["rid"] and obj.group().getV2Zone()["id"] == element["group"]["rid"]:
                return obj
    return False

def findGroup(id_v2):
    for group, obj in bridgeConfig["groups"].items():
        if obj.getV2Room()["id"] == id_v2:
            return obj
        elif obj.getV2Zone()["id"] == id_v2:
            return obj
    return False

def triggerScript(behavior_instance):

    if "when_extended" in behavior_instance.configuration and "randomization" in behavior_instance.configuration["when_extended"]:
        sleep(randrange(behavior_instance.configuration["when_extended"]["randomization"]["minutes"] * 60))

    # Wake Up
    if behavior_instance.script_id == "ff8957e3-2eb9-4699-a0c8-ad2cb3ede704":
        if behavior_instance.active and "turn_lights_off_after" in behavior_instance.configuration:
            logging.debug("End Wake Up routine")
            for element in behavior_instance.configuration["where"]:
                if "group" in element:
                    group = findGroup(element["group"]["rid"])
                    sleep(1)
                    group.setV1Action(state={"on": False})
                    behavior_instance.active = False
                    logging.debug("End Wake Up")

        else:
            logging.debug("Start Wake Up routine")
            for element in behavior_instance.configuration["where"]:
                if "group" in element:
                    group = findGroup(element["group"]["rid"])
                    group.setV1Action(state={"ct": 250, "bri": 1})
                    sleep(1)
                    group.setV1Action(state={"on": True})
                    group.setV1Action(state={"bri": 254, "transitiontime": behavior_instance.configuration["fade_in_duration"]["seconds"] * 10})
                    behavior_instance.active = True if "turn_lights_off_after" in behavior_instance.configuration else False
                    logging.debug("Finish Wake Up")

    # Go to sleep
    elif behavior_instance.script_id == "7e571ac6-f363-42e1-809a-4cbf6523ed72":
        logging.debug("Start Go to Sleep " + behavior_instance.name)
        for element in behavior_instance.configuration["where"]:
            if "group" in element:
                group = findGroup(element["group"]["rid"])
                group.setV1Action(state={"ct": 500})
                sleep(1)
                group.setV1Action(state={"bri": 1, "transitiontime": behavior_instance.configuration["fade_out_duration"]["seconds"] * 10})
                sleep(behavior_instance.configuration["fade_out_duration"]["seconds"])
                if behavior_instance.configuration["end_state"] ==  "turn_off":
                    group.setV1Action(state={"on": False})
                behavior_instance.active = False
                logging.debug("Finish Go to Sleep")

    # Activate scene
    elif behavior_instance.script_id == "7238c707-8693-4f19-9095-ccdc1444d228":
        if behavior_instance.active and "end_at" in behavior_instance.configuration["when_extended"]:
            logging.debug("End routine " + behavior_instance.name)
            for element in behavior_instance.configuration["what"]:
              if "group" in element:
                  scene = findScene(element)
                  if scene:
                      logging.info("Deactivate scene " + scene.name)
                      putDict = {"recall": {"action": "deactivate"}}
                      scene.activate(putDict)
                  group = findGroup(element["group"]["rid"])
                  logging.info("Turn off group " + group.name)
                  group.setV1Action({"on": False})
                  behavior_instance.active = False
        else:
            logging.debug("Start routine " + behavior_instance.name)
            for element in behavior_instance.configuration["what"]:
              if "group" in element:
                  scene = findScene(element)
                  if scene:
                      logging.info("Activate scene " + scene.name)
                      if "when_extended" in behavior_instance.configuration and "transition" in behavior_instance.configuration["when_extended"]["start_at"]:
                          putDict = {"recall": {"action": "active"}, "minutes": behavior_instance.configuration["when_extended"]["start_at"]["transition"]["minutes"]}
                          scene.activate(putDict)
                  else:
                      group = findGroup(element["group"]["rid"])
                      if element["recall"]["rid"] == "732ff1d9-76a7-4630-aad0-c8acc499bb0b": # Bright scene
                          logging.info("Apply Bright scene to group " + group.name)
                          group.setV1Action(state={"ct": 247, "bri": 1})
                          sleep(1)
                          group.setV1Action(state={"on": True})
                          group.setV1Action(state={"bri": 254, "transitiontime": behavior_instance.configuration["when_extended"]["start_at"]["transition"]["minutes"] * 60 * 10})
                          #group.setV1Action({"on": True, "bri": 254, "ct": 247})
                  behavior_instance.active = True if "end_at" in behavior_instance.configuration["when_extended"] else False

    # Countdown Timer
    elif behavior_instance.script_id == "e73bc72d-96b1-46f8-aa57-729861f80c78":
        logging.debug("Start Countdown Timer " + behavior_instance.name)
        secondsToCount = 0
        if "duration" in behavior_instance.configuration:
          if "minutes" in behavior_instance.configuration["duration"]:
              secondsToCount = behavior_instance.configuration["duration"]["minutes"] * 60
          if "seconds" in behavior_instance.configuration["duration"]:
              secondsToCount += behavior_instance.configuration["duration"]["seconds"]
        sleep(secondsToCount)
        for element in behavior_instance.configuration["what"]:
            if "group" in element:
                scene = findScene(element)
                group = findGroup(element["group"]["rid"])
                if scene:
                    logging.info("Activate scene " + scene.name + " to group " + group.name)
                    putDict = {"recall": {"action": "active"}}
                    scene.activate(putDict)
                else:
                  if element["recall"]["rid"] == "732ff1d9-76a7-4630-aad0-c8acc499bb0b": # Bright scene
                      logging.info("Apply Bright scene to group " + group.name)
                      group.setV1Action(state={"on": True, "bri": 254, "ct": 247})
                  else:
                      logging.info("Apply Bright scene to group " + group.name)
                      group.setV1Action(state={"on": True, "bri": 254, "ct": 370})
        behavior_instance.active = False
        behavior_instance.update_attr({"enabled":False})
        logging.debug("Finish Countdown Timer " + behavior_instance.name)


def behaviorScripts():
    return [{
      "configuration_schema": {
        "$ref": "basic_goto_sleep_config.json#"
      },
      "description": "Get ready for nice sleep.",
      "id": "7e571ac6-f363-42e1-809a-4cbf6523ed72",
      "metadata": {
        "category": "automation",
        "name": "Basic go to sleep routine"
      },
      "state_schema": {},
      "supported_features": [],
      "trigger_schema": {
        "$ref": "trigger.json#"
      },
      "type": "behavior_script",
      "version": "0.0.1"
    },
    {
      "configuration_schema": {
        "$ref": "basic_wake_up_config.json#"
      },
      "description": "Get your body in the mood to wake up by fading on the lights in the morning.",
      "id": "ff8957e3-2eb9-4699-a0c8-ad2cb3ede704",
      "metadata": {
        "category": "automation",
        "name": "Basic wake up routine"
      },
      "state_schema": {},
      "supported_features": [
        "style_sunrise"
      ],
      "trigger_schema": {
        "$ref": "trigger.json#"
      },
      "type": "behavior_script",
      "version": "0.0.1"
    },
    {
      "configuration_schema": {
        "$ref": "coming_home_config.json#"
      },
      "description": "Automatically turn your lights to choosen light states, when you arrive at home.",
      "id": "fd60fcd1-4809-4813-b510-4a18856a595c",
      "metadata": {
        "category": "automation",
        "name": "Coming home"
      },
      "state_schema": {},
      "supported_features": [],
      "trigger_schema": {
        "$ref": "trigger.json#"
      },
      "type": "behavior_script",
      "version": "0.0.1"
    },
    {
      "configuration_schema": {
        "$ref": "leaving_home_config.json#"
      },
      "description": "Automatically turn off your lights when you leave",
      "id": "0194752a-2d53-4f92-8209-dfdc52745af3",
      "metadata": {
        "category": "automation",
        "name": "Leaving home"
      },
      "state_schema": {},
      "supported_features": [],
      "trigger_schema": {
        "$ref": "trigger.json#"
      },
      "type": "behavior_script",
      "version": "0.0.1"
    },
    {
      "configuration_schema": {
        "$ref": "schedule_config.json#"
      },
      "description": "Schedule turning on and off lights",
      "id": "7238c707-8693-4f19-9095-ccdc1444d228",
      "metadata": {
        "category": "automation",
        "name": "Schedule"
      },
      "state_schema": {},
      "supported_features": [],
      "trigger_schema": {
        "$ref": "trigger.json#"
      },
      "type": "behavior_script",
      "version": "0.0.1"
    },
    {
      "configuration_schema": {
        "$ref": "timer_config.json#"
      },
      "description": "Countdown Timer",
      "id": "e73bc72d-96b1-46f8-aa57-729861f80c78",
      "metadata": {
        "category": "automation",
        "name": "Timers"
      },
      "state_schema": {
        "$ref": "timer_state.json#"
      },
      "supported_features": [],
      "trigger_schema": {
        "$ref": "trigger.json#"
      },
      "type": "behavior_script",
      "version": "0.0.1"
    },
    {
      "configuration_schema": {
        "$ref": "lights_state_after_streaming_config.json#"
      },
      "description": "State of lights in the entertainment group after streaming ends",
      "id": "7719b841-6b3d-448d-a0e7-601ae9edb6a2",
      "metadata": {
        "category": "entertainment",
        "name": "Light state after streaming"
      },
      "state_schema": {},
      "supported_features": [],
      "trigger_schema": {},
      "type": "behavior_script",
      "version": "0.0.1"
    },
    {
      "configuration_schema": {
        "$ref": "natural_light_config.json#"
      },
      "description": "Natural light during the day",
      "id": "a4260b49-0c69-4926-a29c-417f4a38a352",
      "metadata": {
        "category": "",
        "name": "Natural Light"
      },
      "state_schema": {
        "$ref": "natural_light_state.json#"
      },
      "supported_features": [],
      "trigger_schema": {
        "$ref": "natural_light_trigger.json#"
      },
      "type": "behavior_script",
      "version": "0.0.1"
    }]
