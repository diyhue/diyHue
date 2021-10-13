import logManager
import configManager
from threading import Thread
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

def findGroup(id_v2):
    for group, obj in bridgeConfig["groups"].items():
        if obj.getV2Room()["id"] == id_v2:
            return obj
        elif obj.getV2Zone()["id"] == id_v2:
            return obj

def triggerScript(behavior_instance):

    if "when_extended" in behavior_instance.configuration and "randomization" in behavior_instance.configuration["when_extended"]:
        sleep(randrange(behavior_instance.configuration["when_extended"]["randomization"]["minutes"] * 60))

    # Wake Up
    if behavior_instance.script_id == "ff8957e3-2eb9-4699-a0c8-ad2cb3ede704":
        logging.debug("Start Wake Up routine")
        for element in behavior_instance.configuration["where"]:
            if "group" in element:
                group = findGroup(element["group"]["rid"])
                group.setV1Action(state={"ct": 250, "bri": 1})
                sleep(1)
                group.setV1Action(state={"on": True})
                group.setV1Action(state={"bri": 254, "transitiontime": behavior_instance.configuration["fade_in_duration"]["seconds"] * 10})
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
                logging.debug("Finish Go to Sleep")

    # Activate scene
    elif behavior_instance.script_id == "7238c707-8693-4f19-9095-ccdc1444d228":
        logging.debug("Start routine " + behavior_instance.name)
        for element in behavior_instance.configuration["what"]:
            if "group" in element:
                scene = findScene(element)
                if "when_extended" in behavior_instance.configuration and "transition" in behavior_instance.configuration["when_extended"]["start_at"]:
                    scene.activate(behavior_instance.configuration["when_extended"]["start_at"]["transition"])
                else:
                    scene.activate({})
