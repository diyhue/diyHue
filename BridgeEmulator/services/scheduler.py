import logManager
import configManager
import json
import random
from time import sleep
from threading import Thread
from datetime import datetime, timedelta, time, timezone
from functions.request import sendRequest
from functions.daylightSensor import daylightSensor
from functions.scripts import findGroup, triggerScript
from services import updateManager
from flaskUI.v2restapi import getObject
from copy import deepcopy

bridgeConfig = configManager.bridgeConfig.yaml_config
logging = logManager.logger.get_logger(__name__)

def runScheduler():
    while True:
        for schedule, obj in bridgeConfig["schedules"].items():
            try:
                delay = 0
                if obj.status == "enabled":
                    if obj.localtime[-9:-8] == "A":
                        delay = random.randrange(0, int(obj.localtime[-8:-6]) * 3600 + int(obj.localtime[-5:-3]) * 60 + int(obj.localtime[-2:]))
                        schedule_time = obj.localtime[:-9]
                    else:
                        schedule_time = obj.localtime
                    if schedule_time.startswith("W"):
                        pices = schedule_time.split('/T')
                        if int(pices[0][1:]) & (1 << 6 - datetime.today().weekday()):
                            if pices[1] == datetime.now().strftime("%H:%M:%S"):
                                logging.info("execute schedule: " + schedule + " withe delay " + str(delay))
                                sendRequest(obj.command["address"], obj.command["method"], json.dumps(obj.command["body"]), 1, delay)
                    elif schedule_time.startswith("PT"):
                        timmer = schedule_time[2:]
                        (h, m, s) = timmer.split(':')
                        d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                        if obj.starttime == (datetime.now(timezone.utc).replace(tzinfo=None) - d).replace(microsecond=0).isoformat():
                            logging.info("execute timmer: " + schedule + " withe delay " + str(delay))
                            sendRequest(obj.command["address"], obj.command["method"], json.dumps(obj.command["body"]), 1, delay)
                            obj.status = "disabled"
                    elif schedule_time.startswith("R/PT"):
                        timmer = schedule_time[4:]
                        (h, m, s) = timmer.split(':')
                        d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                        if obj.starttime == (datetime.now(timezone.utc).replace(tzinfo=None) - d).replace(microsecond=0).isoformat():
                            logging.info("execute timmer: " + schedule + " withe delay " + str(delay))
                            obj.starttime = datetime.now(timezone.utc).replace(tzinfo=None).replace(microsecond=0).isoformat()
                            sendRequest(obj.command["address"], obj.command["method"], json.dumps(obj.command["body"]), 1, delay)
                    else:
                        if schedule_time == datetime.now().strftime("%Y-%m-%dT%H:%M:%S"):
                            logging.info("execute schedule: " + schedule + " withe delay " + str(delay))
                            sendRequest(obj.command["address"], obj.command["method"], json.dumps(obj.command["body"]), 1, delay)
                            if obj.autodelete:
                                del obj

            except Exception as e:
                logging.info("Exception while processing the schedule " + schedule + " | " + str(e))

        for instance, obj in bridgeConfig["behavior_instance"].items():
            try:
                delay = 0
                if obj.enabled:
                    if "when" in obj.configuration:
                        if "recurrence_days" in  obj.configuration["when"]:
                            if datetime.now().strftime("%A").lower() not in obj.configuration["when"]["recurrence_days"]:
                                continue
                        if "time_point" in obj.configuration["when"] and obj.configuration["when"]["time_point"]["type"] == "time":
                            triggerTime = obj.configuration["when"]["time_point"]["time"]
                            time_object = datetime(
                                year = 1,
                                month = 1,
                                day = 1,
                                hour = triggerTime["hour"],
                                minute = triggerTime["minute"],
                                second = triggerTime["second"] if "second" in triggerTime else 0)
                            if "fade_in_duration" in obj.configuration or "turn_lights_off_after" in obj.configuration:
                                fade_duration = obj.configuration["turn_lights_off_after"] if "turn_lights_off_after" in obj.configuration and obj.active else obj.configuration["fade_in_duration"]
                                delta = timedelta(
                                    hours=fade_duration["hours"] if "hours" in fade_duration else 0,
                                    minutes=fade_duration["minutes"] if "minutes" in fade_duration else 0,
                                    seconds=fade_duration["seconds"] if "seconds" in fade_duration else 0)
                                time_object = time_object + delta if "turn_lights_off_after" in obj.configuration and obj.active else time_object - delta
                            if datetime.now().second == time_object.second and datetime.now().minute == time_object.minute and datetime.now().hour == time_object.hour:
                                logging.info("execute timmer: " + obj.name)
                                Thread(target=triggerScript, args=[obj]).start()

                    elif "when_extended" in obj.configuration:
                        if "recurrence_days" in  obj.configuration["when_extended"]:
                            if datetime.now().strftime("%A").lower() not in obj.configuration["when_extended"]["recurrence_days"]:
                                continue
                        if obj.active:
                            if "end_at" in obj.configuration["when_extended"] and "time_point" in obj.configuration["when_extended"]["end_at"] and obj.configuration["when_extended"]["end_at"]["time_point"]["type"] == "time":
                                triggerTime = obj.configuration["when_extended"]["end_at"]["time_point"]["time"]
                                time_object = time(
                                    hour = triggerTime["hour"],
                                    minute = triggerTime["minute"],
                                    second = triggerTime["second"] if "second" in triggerTime else 0)
                                if datetime.now().second == time_object.second and datetime.now().minute == time_object.minute and datetime.now().hour == time_object.hour:
                                    logging.info("end timmer: " + obj.name)
                                    Thread(target=triggerScript, args=[obj]).start()
                        else:
                            if "start_at" in obj.configuration["when_extended"] and "time_point" in obj.configuration["when_extended"]["start_at"] and obj.configuration["when_extended"]["start_at"]["time_point"]["type"] == "time":
                                triggerTime = obj.configuration["when_extended"]["start_at"]["time_point"]["time"]
                                time_object = time(
                                    hour = triggerTime["hour"],
                                    minute = triggerTime["minute"],
                                    second = triggerTime["second"] if "second" in triggerTime else 0)
                                if datetime.now().second == time_object.second and datetime.now().minute == time_object.minute and datetime.now().hour == time_object.hour:
                                    logging.info("execute timmer: " + obj.name)
                                    Thread(target=triggerScript, args=[obj]).start()
                    elif "duration" in obj.configuration:
                        if obj.active == False and obj.enabled == True:
                            logging.info("execute timer: " + obj.name)
                            obj.active = True
                            Thread(target=triggerScript, args=[obj]).start()


            except Exception as e:
                logging.info("Exception while processing the behavior_instance " + obj.name + " | " + str(e))

        for smartscene, obj in bridgeConfig["smart_scene"].items():
            try:
                if hasattr(obj, "timeslots"):
                    sunset_slot = -1
                    sunset = bridgeConfig["sensors"]["1"].config["sunset"] if "lat" in bridgeConfig["sensors"]["1"].protocol_cfg else "21:00:00"
                    slots = deepcopy(obj.timeslots)
                    if hasattr(obj, "recurrence"):
                        if datetime.now().strftime("%A").lower() not in obj.recurrence:
                            continue
                    for instance, slot in enumerate(slots):
                        time_object = ""
                        if slot["start_time"]["kind"] == "time":
                            time_object = datetime(
                                year=1,
                                month=1,
                                day=1,
                                hour=slot["start_time"]["time"]["hour"],
                                minute=slot["start_time"]["time"]["minute"],
                                second=slot["start_time"]["time"]["second"]).strftime("%H:%M:%S")
                        elif slot["start_time"]["kind"] == "sunset":
                            sunset_slot = instance
                            time_object = sunset
                        if sunset_slot > 0 and instance == sunset_slot+1:
                            if sunset > time_object:
                                time_object = (datetime.strptime(sunset, "%H:%M:%S") + timedelta(minutes=30)).strftime("%H:%M:%S")
                        slots[instance]["start_time"]["time"] = time_object
                        slots[instance]["start_time"]["instance"] = instance

                    slots = sorted(slots, key=lambda x: datetime.strptime(x["start_time"]["time"], "%H:%M:%S"))
                    active_timeslot = obj.active_timeslot
                    for slot in slots:
                        if datetime.now().strftime("%H:%M:%S") >= slot["start_time"]["time"]:
                            active_timeslot = slot["start_time"]["instance"]
                    if obj.active_timeslot != active_timeslot:
                        obj.active_timeslot = active_timeslot
                        if obj.state == "active":
                            if active_timeslot == len(obj.timeslots)-1:
                                logging.info("stop smart_scene: " + obj.name)
                                group = findGroup(obj.group["rid"])
                                group.setV1Action(state={"on": False})
                            else:
                                logging.info("execute smart_scene: " + obj.name + " scene: " + str(obj.active_timeslot))
                                putDict = {"recall": {"action": "active", "duration": obj.speed}}
                                target_object = getObject(obj.timeslots[active_timeslot]["target"]["rtype"], obj.timeslots[active_timeslot]["target"]["rid"])
                                target_object.activate(putDict)

            except Exception as e:
                logging.info("Exception while processing the smart_scene " + obj.name + " | " + str(e))

        if ("updatetime" not in bridgeConfig["config"]["swupdate2"]["autoinstall"]):
            bridgeConfig["config"]["swupdate2"]["autoinstall"]["updatetime"] = "T14:00:00"
        if (datetime.now().strftime("T%H:%M:%S") == bridgeConfig["config"]["swupdate2"]["autoinstall"]["updatetime"]): #check for updates every day at updatetime
            updateManager.versionCheck()
            updateManager.githubCheck()
            if (bridgeConfig["config"]["swupdate2"]["autoinstall"]["on"] == True): #install update if available every day at updatetime
                updateManager.githubInstall()
        if (datetime.now().strftime("%M:%S") == "00:10"): #auto save configuration every hour
            configManager.bridgeConfig.save_config()
            Thread(target=daylightSensor, args=[bridgeConfig["config"]["timezone"], bridgeConfig["sensors"]["1"]]).start()
            if (datetime.now().strftime("%H") == "23" and datetime.now().strftime("%A") == "Sunday"): #backup config every Sunday at 23:00:10
                configManager.bridgeConfig.save_config(backup=True)
        sleep(1)
