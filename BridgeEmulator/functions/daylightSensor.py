import pytz
import logging
from astral.sun import sun
from astral import LocationInfo
from functions.rules import rulesProcessor
from datetime import datetime
from time import sleep

def daylightSensor(bridge_config, dxState):
    if bridge_config["sensors"]["1"]["modelid"] != "PHDL00" or not bridge_config["sensors"]["1"]["config"]["configured"]:
        return

    localzone = LocationInfo('localzone', bridge_config["config"]["timezone"].split("/")[1], bridge_config["config"]["timezone"], float(bridge_config["sensors"]["1"]["config"]["lat"][:-1]), float(bridge_config["sensors"]["1"]["config"]["long"][:-1]))
    s = sun(localzone.observer, date=datetime.utcnow())
    deltaSunset = s['sunset'].replace(tzinfo=None) - datetime.utcnow()
    deltaSunrise = s['sunrise'].replace(tzinfo=None) - datetime.utcnow()
    deltaSunsetOffset = deltaSunset.total_seconds() + bridge_config["sensors"]["1"]["config"]["sunsetoffset"] * 60
    deltaSunriseOffset = deltaSunrise.total_seconds() + bridge_config["sensors"]["1"]["config"]["sunriseoffset"] * 60
    logging.info("deltaSunsetOffset: " + str(deltaSunsetOffset))
    logging.info("deltaSunriseOffset: " + str(deltaSunriseOffset))
    current_time =  datetime.utcnow()
    if deltaSunriseOffset < 0 and deltaSunsetOffset > 0:
        bridge_config["sensors"]["1"]["state"] = {"daylight":True,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        logging.info("set daylight sensor to true")
    else:
        bridge_config["sensors"]["1"]["state"] = {"daylight":False,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        logging.info("set daylight sensor to false")
    if deltaSunsetOffset > 0 and deltaSunsetOffset < 3600:
        logging.info("will start the sleep for sunset")
        sleep(deltaSunsetOffset)
        logging.info("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
        bridge_config["sensors"]["1"]["state"] = {"daylight":False,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        dxState["sensors"]["1"]["state"]["daylight"] = current_time
        rulesProcessor(["sensors","1"], current_time, bridge_config, dxState)
    if deltaSunriseOffset > 0 and deltaSunriseOffset < 3600:
        logging.info("will start the sleep for sunrise")
        sleep(deltaSunriseOffset)
        logging.info("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
        bridge_config["sensors"]["1"]["state"] = {"daylight":True,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        dxState["sensors"]["1"]["state"]["daylight"] = current_time
        rulesProcessor(["sensors","1"], current_time, bridge_config, dxState)
