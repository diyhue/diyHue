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

def daylightSensor(tz, sensor):#tz = timezone
    if sensor.config["configured"]:
        localzone = LocationInfo('localzone', tz.split("/")[1], tz, sensor.protocol_cfg["lat"], sensor.protocol_cfg["long"])
        s = sun(localzone.observer, date=datetime.now(timezone.utc).replace(tzinfo=None))
        deltaSunset = s['sunset'].replace(tzinfo=None) - datetime.now(timezone.utc).replace(tzinfo=None)
        deltaSunrise = s['sunrise'].replace(tzinfo=None) - datetime.now(timezone.utc).replace(tzinfo=None)
        deltaSunsetOffset = deltaSunset.total_seconds() + sensor.config["sunsetoffset"] * 60
        deltaSunriseOffset = deltaSunrise.total_seconds() + sensor.config["sunriseoffset"] * 60
        logging.info("deltaSunsetOffset: " + str(deltaSunsetOffset))
        logging.info("deltaSunriseOffset: " + str(deltaSunriseOffset))
        sensor.config["sunset"] = s['sunset'].astimezone().strftime("%H:%M:%S")
        current_time =  datetime.now(timezone.utc).replace(tzinfo=None)
        if deltaSunriseOffset < 0 and deltaSunsetOffset > 0:
            sensor.state["daylight"] = True
            logging.info("set daylight sensor to true")
        else:
            sensor.state["daylight"] = False
            logging.info("set daylight sensor to false")
        if deltaSunsetOffset > 0 and deltaSunsetOffset < 3600:
            logging.info("will start the sleep for sunset")
            sleep(deltaSunsetOffset)
            logging.debug("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
            sensor.state = {"daylight":False,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
            sensor.dxState["daylight"] = current_time
            rulesProcessor(sensor, current_time)
        elif deltaSunriseOffset > 0 and deltaSunriseOffset < 3600:
            logging.info("will start the sleep for sunrise")
            sleep(deltaSunriseOffset)
            logging.debug("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
            sensor.state = {"daylight":True,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
            sensor.dxState["daylight"] = current_time
            rulesProcessor(sensor, current_time)
        # v2 api routines
        for key, instance in bridgeConfig["behavior_instance"].items():
            if "when_extended" in instance.configuration:
                offset = 0
                if instance.configuration["when_extended"]["start_at"]["time_point"]["type"] == "sunrise":
                    if "offset" in instance.configuration["when_extended"]["start_at"]["time_point"]:
                        offset = 60 * instance.configuration["when_extended"]["start_at"]["time_point"]["offset"]["minutes"]
                    if deltaSunriseOffset + offset > 0 and deltaSunriseOffset + offset < 3600:
                        Thread(target=runBackgroundSleep, args=[instance, deltaSunriseOffset + offset]).start()
                elif instance.configuration["when_extended"]["start_at"]["time_point"]["type"] == "sunset":
                    if "offset" in instance.configuration["when_extended"]["start_at"]["time_point"]:
                        offset = 60 * instance.configuration["when_extended"]["start_at"]["time_point"]["offset"]["minutes"]
                    if deltaSunsetOffset + offset > 0 and deltaSunsetOffset + offset < 3600:
                        Thread(target=runBackgroundSleep, args=[instance, deltaSunsetOffset + offset]).start()

    else:
        logging.debug("Daylight Sensor: location is not configured")
