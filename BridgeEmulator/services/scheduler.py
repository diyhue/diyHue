import logManager
import configManager
import json
from time import sleep
from threading import Thread
from datetime import datetime, timedelta, time, date
from functions.request import sendRequest
from functions.daylightSensor import daylightSensor
from functions.scripts import triggerScript

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
                        if obj.starttime == (datetime.utcnow() - d).replace(microsecond=0).isoformat():
                            logging.info("execute timmer: " + schedule + " withe delay " + str(delay))
                            sendRequest(obj.command["address"], obj.command["method"], json.dumps(obj.command["body"]), 1, delay)
                            obj.status = "disabled"
                    elif schedule_time.startswith("R/PT"):
                        timmer = schedule_time[4:]
                        (h, m, s) = timmer.split(':')
                        d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                        if obj.starttime == (datetime.utcnow() - d).replace(microsecond=0).isoformat():
                            logging.info("execute timmer: " + schedule + " withe delay " + str(delay))
                            obj.starttime = datetime.utcnow().replace(microsecond=0).isoformat()
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
                            time_object = time(
                                hour = triggerTime["hour"],
                                minute = triggerTime["minute"],
                                second = triggerTime["second"] if "second" in triggerTime else 0)
                            if "fade_in_duration" in obj.configuration:
                                fade_duration = obj.configuration["fade_in_duration"]
                                delta = timedelta(
                                    hours=fade_duration["hours"] if "hours" in fade_duration else 0,
                                    minutes=fade_duration["minutes"] if "minutes" in fade_duration else 0,
                                    seconds=fade_duration["seconds"] if "seconds" in fade_duration else 0)
                                time_object = (datetime.combine(date(1,1,1),time_object) - delta).time()
                            if datetime.now().second == time_object.second and datetime.now().minute == time_object.minute and datetime.now().hour == time_object.hour:
                                Thread(target=triggerScript, args=[obj]).start()

                    elif "when_extended" in obj.configuration:
                        if "recurrence_days" in  obj.configuration["when_extended"]:
                            if datetime.now().strftime("%A").lower() not in obj.configuration["when_extended"]["recurrence_days"]:
                                continue
                            if "start_at" in obj.configuration["when_extended"] and "time_point" in obj.configuration["when_extended"]["start_at"] and obj.configuration["when_extended"]["start_at"]["time_point"]["type"] == "time":
                                triggerTime = obj.configuration["when_extended"]["start_at"]["time_point"]["time"]
                                time_object = time(
                                    hour = triggerTime["hour"],
                                    minute = triggerTime["minute"],
                                    second = triggerTime["second"] if "second" in triggerTime else 0)
                                if datetime.now().second == time_object.second and datetime.now().minute == time_object.minute and datetime.now().hour == time_object.hour:
                                    Thread(target=triggerScript, args=[obj]).start()


            except Exception as e:
                logging.info("Exception while processing the schedule " + obj.name + " | " + str(e))

        if (datetime.now().strftime("%M:%S") == "00:10"): #auto save configuration every hour
            configManager.bridgeConfig.save_config()
            Thread(target=daylightSensor, args=[bridgeConfig["config"]["timezone"], bridgeConfig["sensors"]["1"]]).start()
            if (datetime.now().strftime("%H") == "23" and datetime.now().strftime("%A") == "Sunday"): #backup config every Sunday at 23:00:10
                configManager.bridgeConfig.save_config(backup=True)
        sleep(1)
