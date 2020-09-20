import logManager
import configManager
from time import sleep
from threading import Thread
from datetime import datetime, timedelta
from functions.request import sendRequest
from functions.daylightSensor import daylightSensor

bridgeConfig = configManager.bridgeConfig.json_config
logging = logManager.logger.get_logger(__name__)

def runScheduler():
    while True:
        for schedule in bridgeConfig["schedules"].keys():
            try:
                delay = 0
                if bridgeConfig["schedules"][schedule]["status"] == "enabled":
                    if bridgeConfig["schedules"][schedule]["localtime"][-9:-8] == "A":
                        delay = random.randrange(0, int(bridgeConfig["schedules"][schedule]["localtime"][-8:-6]) * 3600 + int(bridgeConfig["schedules"][schedule]["localtime"][-5:-3]) * 60 + int(bridgeConfig["schedules"][schedule]["localtime"][-2:]))
                        schedule_time = bridgeConfig["schedules"][schedule]["localtime"][:-9]
                    else:
                        schedule_time = bridgeConfig["schedules"][schedule]["localtime"]
                    if schedule_time.startswith("W"):
                        pices = schedule_time.split('/T')
                        if int(pices[0][1:]) & (1 << 6 - datetime.today().weekday()):
                            if pices[1] == datetime.now().strftime("%H:%M:%S"):
                                logging.info("execute schedule: " + schedule + " withe delay " + str(delay))
                                sendRequest(bridgeConfig["schedules"][schedule]["command"]["address"], bridgeConfig["schedules"][schedule]["command"]["method"], json.dumps(bridgeConfig["schedules"][schedule]["command"]["body"]), 1, delay)
                    elif schedule_time.startswith("PT"):
                        timmer = schedule_time[2:]
                        (h, m, s) = timmer.split(':')
                        d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                        if bridgeConfig["schedules"][schedule]["starttime"] == (datetime.utcnow() - d).replace(microsecond=0).isoformat():
                            logging.info("execute timmer: " + schedule + " withe delay " + str(delay))
                            sendRequest(bridgeConfig["schedules"][schedule]["command"]["address"], bridgeConfig["schedules"][schedule]["command"]["method"], json.dumps(bridgeConfig["schedules"][schedule]["command"]["body"]), 1, delay)
                            bridgeConfig["schedules"][schedule]["status"] = "disabled"
                    elif schedule_time.startswith("R/PT"):
                        timmer = schedule_time[4:]
                        (h, m, s) = timmer.split(':')
                        d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                        if bridgeConfig["schedules"][schedule]["starttime"] == (datetime.utcnow() - d).replace(microsecond=0).isoformat():
                            logging.info("execute timmer: " + schedule + " withe delay " + str(delay))
                            bridgeConfig["schedules"][schedule]["starttime"] = datetime.utcnow().replace(microsecond=0).isoformat()
                            sendRequest(bridgeConfig["schedules"][schedule]["command"]["address"], bridgeConfig["schedules"][schedule]["command"]["method"], json.dumps(bridgeConfig["schedules"][schedule]["command"]["body"]), 1, delay)
                    else:
                        if schedule_time == datetime.now().strftime("%Y-%m-%dT%H:%M:%S"):
                            logging.info("execute schedule: " + schedule + " withe delay " + str(delay))
                            sendRequest(bridgeConfig["schedules"][schedule]["command"]["address"], bridgeConfig["schedules"][schedule]["command"]["method"], json.dumps(bridgeConfig["schedules"][schedule]["command"]["body"]), 1, delay)
                            if bridgeConfig["schedules"][schedule]["autodelete"]:
                                del bridgeConfig["schedules"][schedule]
            except Exception as e:
                logging.info("Exception while processing the schedule " + schedule + " | " + str(e))

        if (datetime.now().strftime("%M:%S") == "00:10"): #auto save configuration every hour
            configManager.bridgeConfig.save_config()
            Thread(target=daylightSensor).start()
            if (datetime.now().strftime("%H") == "23" and datetime.now().strftime("%A") == "Sunday"): #backup config every Sunday at 23:00:10
                configManager.bridgeConfig.save_config(backup=True)
        sleep(1)
