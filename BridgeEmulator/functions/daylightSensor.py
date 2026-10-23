from astral.sun import sun
from astral import LocationInfo
from functions.rules import rulesProcessor
from datetime import datetime, timezone
from time import sleep
from threading import Thread
from functions.scripts import triggerScript
import logManager
import configManager

bridgeConfig = configManager.bridgeConfig.yaml_config
logging = logManager.logger.get_logger(__name__)

def runBackgroundSleep(instance, seconds):
    sleep(seconds)
    triggerScript(instance)

def scheduleRoutines(deltaSunrise, deltaSunset):
    """Start the v2 sunrise/sunset routines due within the next hour.

    The deltas are seconds until sunrise and sunset without the v1 sensor's
    offsets; each routine applies its own offset.
    """
    for key, instance in bridgeConfig["behavior_instance"].items():
        if "when_extended" in instance.configuration:
            time_point = instance.configuration["when_extended"]["start_at"]["time_point"]
            if time_point["type"] == "sunrise":
                delta = deltaSunrise
            elif time_point["type"] == "sunset":
                delta = deltaSunset
            else:
                continue
            offset = 0
            if "offset" in time_point:
                offset = 60 * time_point["offset"]["minutes"]
            if 0 < delta + offset < 3600:
                Thread(target=runBackgroundSleep, args=[instance, delta + offset]).start()

def daylightSensor(tz, sensor):#tz = timezone
    if sensor.config["configured"]:
        localzone = LocationInfo('localzone', tz.split("/")[-1], tz, sensor.protocol_cfg["lat"], sensor.protocol_cfg["long"])
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        s = sun(localzone.observer, date=now)
        deltaSunset = (s['sunset'].replace(tzinfo=None) - now).total_seconds()
        deltaSunrise = (s['sunrise'].replace(tzinfo=None) - now).total_seconds()
        deltaSunsetOffset = deltaSunset + sensor.config["sunsetoffset"] * 60
        deltaSunriseOffset = deltaSunrise + sensor.config["sunriseoffset"] * 60
        logging.info("deltaSunsetOffset: " + str(deltaSunsetOffset))
        logging.info("deltaSunriseOffset: " + str(deltaSunriseOffset))
        sensor.config["sunset"] = s['sunset'].astimezone().strftime("%H:%M:%S")
        if deltaSunriseOffset < 0 and deltaSunsetOffset > 0:
            sensor.state["daylight"] = True
            logging.info("set daylight sensor to true")
        else:
            sensor.state["daylight"] = False
            logging.info("set daylight sensor to false")
        # v2 api routines: schedule them before the sleeps below, which can last
        # up to an hour and would delay them by as much.
        scheduleRoutines(deltaSunrise, deltaSunset)
        if deltaSunsetOffset > 0 and deltaSunsetOffset < 3600:
            logging.info("will start the sleep for sunset")
            sleep(deltaSunsetOffset)
            current_time = datetime.now(timezone.utc).replace(tzinfo=None)
            logging.debug("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
            sensor.state = {"daylight":False,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
            sensor.dxState["daylight"] = current_time
            rulesProcessor(sensor, current_time)
        elif deltaSunriseOffset > 0 and deltaSunriseOffset < 3600:
            logging.info("will start the sleep for sunrise")
            sleep(deltaSunriseOffset)
            current_time = datetime.now(timezone.utc).replace(tzinfo=None)
            logging.debug("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
            sensor.state = {"daylight":True,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
            sensor.dxState["daylight"] = current_time
            rulesProcessor(sensor, current_time)

    else:
        logging.debug("Daylight Sensor: location is not configured")
