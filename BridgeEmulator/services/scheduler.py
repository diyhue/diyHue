import logManager
import configManager
import json
from time import sleep
from threading import Thread
from datetime import datetime, timedelta
from functions.request import sendRequest
from functions.daylightSensor import daylightSensor

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

        if (datetime.now().strftime("%M:%S") == "00:10"): #auto save configuration every hour
            configManager.bridgeConfig.save_config()
            Thread(target=daylightSensor, args=[bridgeConfig["config"]["timezone"], bridgeConfig["sensors"]["1"]]).start()
            if (datetime.now().strftime("%H") == "23" and datetime.now().strftime("%A") == "Sunday"): #backup config every Sunday at 23:00:10
                configManager.bridgeConfig.save_config(backup=True)
        sleep(1)
