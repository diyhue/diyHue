#!/usr/bin/python3
import json
import logManager
import random
from datetime import datetime, timedelta
from threading import Thread
from time import sleep
from functions.ssdp import ssdpBroadcast, ssdpSearch
from lightManager.core.entertainment import entertainmentService
from functions.request import sendRequest
from lightManager.core.lightRequest import sendLightRequest, syncWithLights
from protocols import mqtt, deconz
import api
import configManager
import webServer # needs lots of work...
from protocols.hue.scheduler import generateDxState, rulesProcessor

logging = logManager.logger.get_logger(__name__)
update_lights_on_startup = False # if set to true all lights will be updated with last know state on startup.
off_if_unreachable = False # If set to true all lights that unreachable are marked as off.
bridge_config = configManager.bridgeConfig.json_config
dxState = configManager.runtimeConfig.dxState
new_lights = configManager.runtimeConfig.newLights


def scheduleProcessor():
    while True:
        for schedule in bridge_config["schedules"].keys():
            try:
                delay = 0
                if bridge_config["schedules"][schedule]["status"] == "enabled":
                    if bridge_config["schedules"][schedule]["localtime"][-9:-8] == "A":
                        delay = random.randrange(0, int(bridge_config["schedules"][schedule]["localtime"][-8:-6]) * 3600 + int(bridge_config["schedules"][schedule]["localtime"][-5:-3]) * 60 + int(bridge_config["schedules"][schedule]["localtime"][-2:]))
                        schedule_time = bridge_config["schedules"][schedule]["localtime"][:-9]
                    else:
                        schedule_time = bridge_config["schedules"][schedule]["localtime"]
                    if schedule_time.startswith("W"):
                        pieces = schedule_time.split('/T')
                        if int(pieces[0][1:]) & (1 << 6 - datetime.today().weekday()):
                            if pieces[1] <= datetime.now().strftime("%H:%M:%S"):
                                logging.info("execute schedule: " + schedule + " withe delay " + str(delay))
                                sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                    elif schedule_time.startswith("PT"):
                        timer = schedule_time[2:]
                        (h, m, s) = timer.split(':')
                        d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                        if bridge_config["schedules"][schedule]["starttime"] <= (datetime.utcnow() - d).replace(microsecond=0).isoformat():
                            logging.info("execute timer: " + schedule + " withe delay " + str(delay))
                            sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                            bridge_config["schedules"][schedule]["status"] = "disabled"
                    elif schedule_time.startswith("R/PT"):
                        timer = schedule_time[4:]
                        (h, m, s) = timer.split(':')
                        d = timedelta(hours=int(h), minutes=int(m), seconds=int(s))
                        if bridge_config["schedules"][schedule]["starttime"] <= (datetime.utcnow() - d).replace(microsecond=0).isoformat():
                            logging.info("execute timer: " + schedule + " withe delay " + str(delay))
                            bridge_config["schedules"][schedule]["starttime"] = datetime.utcnow().replace(microsecond=0).isoformat()
                            sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                    else:
                        if schedule_time <= datetime.now().strftime("%Y-%m-%dT%H:%M:%S"):
                            logging.info("execute schedule: " + schedule + " withe delay " + str(delay))
                            sendRequest(bridge_config["schedules"][schedule]["command"]["address"], bridge_config["schedules"][schedule]["command"]["method"], json.dumps(bridge_config["schedules"][schedule]["command"]["body"]), 1, delay)
                            if bridge_config["schedules"][schedule]["autodelete"]:
                                del bridge_config["schedules"][schedule]
            except Exception as e:
                logging.info("Exception while processing the schedule " + schedule + " | " + str(e))

        if (datetime.now().strftime("%M:%S") == "00:10"): #auto save configuration every hour
            configManager.bridgeConfig.save_config()
            Thread(target=daylightSensor).start()
            if (datetime.now().strftime("%H") == "23" and datetime.now().strftime("%A") == "Sunday"): #backup config every Sunday at 23:00:10
                configManager.bridgeConfig.save_config(True)
        sleep(1)


def updateAllLights():
    ## apply last state on startup to all bulbs, useful if there was a power outage
    if bridge_config["deconz"]["enabled"]:
        sleep(60) #give 1 minute for deconz to have ZigBee network ready
    for light in bridge_config["lights_address"]:
        payload = {}
        payload["on"] = bridge_config["lights"][light]["state"]["on"]
        if payload["on"] and "bri" in bridge_config["lights"][light]["state"]:
            payload["bri"] = bridge_config["lights"][light]["state"]["bri"]
        sendLightRequest(light, payload, bridge_config["lights"], bridge_config["lights_address"])
        sleep(0.5)
        logging.info("update status for light " + light)


def daylightSensor():
    if bridge_config["sensors"]["1"]["modelid"] != "PHDL00" or not bridge_config["sensors"]["1"]["config"]["configured"]:
        return
    from astral.sun import sun
    from astral import LocationInfo
    localzone = LocationInfo('localzone', bridge_config["config"]["timezone"].split("/")[1], bridge_config["config"]["timezone"], float(bridge_config["sensors"]["1"]["config"]["lat"][:-1]), float(bridge_config["sensors"]["1"]["config"]["long"][:-1]))
    s = sun(localzone.observer, date=datetime.now())
    deltaSunset = s['sunset'].replace(tzinfo=None) - datetime.now()
    deltaSunrise = s['sunrise'].replace(tzinfo=None) - datetime.now()
    deltaSunsetOffset = deltaSunset.total_seconds() + bridge_config["sensors"]["1"]["config"]["sunsetoffset"] * 60
    deltaSunriseOffset = deltaSunrise.total_seconds() + bridge_config["sensors"]["1"]["config"]["sunriseoffset"] * 60
    logging.info("deltaSunsetOffset: " + str(deltaSunsetOffset))
    logging.info("deltaSunriseOffset: " + str(deltaSunriseOffset))
    current_time =  datetime.now()
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
        rulesProcessor(["sensors","1"], current_time)
    if deltaSunriseOffset > 0 and deltaSunriseOffset < 3600:
        logging.info("will start the sleep for sunrise")
        sleep(deltaSunriseOffset)
        logging.info("sleep finish at " + current_time.strftime("%Y-%m-%dT%H:%M:%S"))
        bridge_config["sensors"]["1"]["state"] = {"daylight":True,"lastupdated": current_time.strftime("%Y-%m-%dT%H:%M:%S")}
        dxState["sensors"]["1"]["state"]["daylight"] = current_time
        rulesProcessor(["sensors","1"], current_time)


if __name__ == "__main__":
    generateDxState()
    configManager.bridgeConfig.save_config()
    configManager.bridgeConfig.resourceRecycle()
    if bridge_config["deconz"]["enabled"]:
        Thread(target=deconz.scanDeconz).start()
    if "emulator" in bridge_config and "mqtt" in bridge_config["emulator"] and bridge_config["emulator"]["mqtt"]["enabled"]:
        mqtt.mqttServer(bridge_config["emulator"]["mqtt"], bridge_config["lights"], bridge_config["lights_address"], bridge_config["sensors"])
    try:
        BIND_IP = configManager.runtimeConfig.arg["BIND_IP"]
        HOST_IP = configManager.runtimeConfig.arg["HOST_IP"]
        mac = configManager.runtimeConfig.arg["MAC"]
        HOST_HTTP_PORT = configManager.runtimeConfig.arg["HTTP_PORT"]
        if update_lights_on_startup:
            Thread(target=updateAllLights).start()
        Thread(target=ssdpSearch, args=[HOST_IP, HOST_HTTP_PORT, mac]).start()
        Thread(target=ssdpBroadcast, args=[HOST_IP, HOST_HTTP_PORT, mac]).start()
        Thread(target=scheduleProcessor).start()
        Thread(target=syncWithLights, args=[bridge_config["lights"], bridge_config["lights_address"], bridge_config["config"]["whitelist"], bridge_config["groups"], off_if_unreachable]).start()
        Thread(target=entertainmentService, args=[bridge_config["lights"], bridge_config["lights_address"], bridge_config["groups"], HOST_IP]).start()
        Thread(target=webServer.server.run, args=[False]).start()
        if not configManager.runtimeConfig.arg["noServeHttps"]:
            Thread(target=webServer.server.run, args=[True]).start()
        Thread(target=daylightSensor).start()
        Thread(target=api.remote.remoteApi, args=[BIND_IP, bridge_config["config"]]).start()
        if not configManager.runtimeConfig.arg["disableOnlineDiscover"]:
            Thread(target=api.remote.remoteDiscover, args=[bridge_config["config"]]).start()

        while True:
            sleep(10)
    except Exception:
        logging.exception("server stopped ")
    finally:
        run_service = False
        logging.info('gracefully exit')
