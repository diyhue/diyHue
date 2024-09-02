import configManager
import logManager
from flask_restful import Resource
from flask import request
from functions.rules import rulesProcessor
from sensors.discover import addHueMotionSensor, addHueSwitch, addHueRotarySwitch
from datetime import datetime, timezone
from threading import Thread
from time import sleep

logging = logManager.logger.get_logger(__name__)

bridgeConfig = configManager.bridgeConfig.yaml_config


def noMotion(sensor):
    bridgeConfig["sensors"][sensor].protocol_cfg["threaded"] = True
    logging.info("Monitor the sensor for no motion")

    while (datetime.now() - bridgeConfig["sensors"][sensor].dxState["presence"]).total_seconds() < 60:
        sleep(1)
    bridgeConfig["sensors"][sensor].state["presence"] = False
    current_time = datetime.now()
    bridgeConfig["sensors"][sensor].dxState["presence"] = current_time
    rulesProcessor(bridgeConfig["sensors"][sensor], current_time)
    bridgeConfig["sensors"][sensor].protocol_cfg["threaded"] = False


class Switch(Resource):
    def get(self):
        args = request.args
        if "mac" in args:
            current_time = datetime.now()
            mac = args["mac"]
            if "devicetype" in args:  # device registration if is new
                deviceIsNew = True
                for device, obj in bridgeConfig["sensors"].items():
                    if "mac" in obj.protocol_cfg and obj.protocol_cfg["mac"] == mac:
                        deviceIsNew = False
                        break
                if deviceIsNew:
                    if args["devicetype"] in ["ZLLSwitch", "ZGPSwitch"]:
                        sensor = addHueSwitch("", args["devicetype"])
                        sensor.protocol_cfg["mac"] = mac
                        return {"success": "device registered"}
                    elif args["devicetype"] == "ZLLPresence":
                        sensor = addHueMotionSensor("Hue Motion Sensor", "native", {
                                                    "mac": mac, "threaded": False})
                        return {"success": "device registered"}
                    elif args["devicetype"] == "ZLLRelativeRotary":
                        sensor = addHueRotarySwitch({"mac": mac})
                        return {"success": "device registered"}
                    else:
                        return {"fail": "unknown device"}
                else:
                    return {"fail": "device already registerd"}
            else:
                result = {""}
                for device, obj in bridgeConfig["sensors"].items():
                    if "mac" in obj.protocol_cfg:
                        if obj.protocol_cfg["mac"] == mac:
                            if obj.type == "ZLLLightLevel":
                                if "lightlevel" in args:
                                    obj.state["lightlevel"] = int(args["lightlevel"])
                                    obj.dxState["lightlevel"] = current_time
                                if "dark" in args:
                                    dark = True if args["dark"] == "true" else False
                                    if obj.state["dark"] != dark:
                                        obj.dxState["dark"] = current_time
                                        obj.state["dark"] = dark
                                if "daylight" in args:
                                    daylight = True if args["daylight"] == "true" else False
                                    if obj.state["daylight"] != daylight:
                                        obj.dxState["daylight"] = current_time
                                        obj.state["daylight"] = daylight
                            elif obj.type == "ZLLPresence":
                                if "battery" in args:
                                    obj.config["battery"] = int(args["battery"])
                                if "presence" in args:
                                    presence = True if args["presence"] == "true" else False
                                    if obj.state["presence"] != presence:
                                        obj.state["presence"] = presence
                                        obj.dxState["presence"] = current_time
                                        if obj.protocol_cfg["threaded"] == False:
                                            Thread(target=noMotion, args=[device]).start()
                            elif obj.type == "ZLLTemperature":
                                if "temperature" in args:
                                    obj.state["temperature"] = int(args["temperature"])
                                    obj.dxState["temperature"] = current_time
                            elif obj.type in ["ZLLSwitch", "ZGPSwitch"]:
                                if "button" in args:
                                    obj.state["buttonevent"] = int(args["button"])
                                    obj.dxState["buttonevent"] = current_time
                                if "battery" in args:
                                    obj.config["battery"] = int(args["battery"])
                            elif obj.type == "ZLLRelativeRotary":
                                if "rotary" in args:
                                    obj.state["rotaryevent"] = int(args["rotary"])
                                    obj.state["expectedrotation"] = int(args["rotation"])
                                    obj.state["expectedeventduration"] = int(args["duration"])
                                    obj.dxState["rotaryevent"] = current_time
                                if "battery" in args:
                                    obj.config["battery"] = int(args["battery"])
                            else:
                                result = {"fail": "unknown device"}
                            obj.dxState["lastupdated"] = current_time
                            obj.state["lastupdated"] = datetime.now(timezone.utc).strftime(
                                "%Y-%m-%dT%H:%M:%S.000Z")
                            rulesProcessor(obj, current_time)
                            result = {"success": "command applied"}
                        else:
                            if result == {""} or result == {"fail": "no mac in list"}:
                                result = {"fail": "device not found"}
                    else:
                        if result == {""}:
                            result = {"fail": "no mac in list"}
                return result
        else:
            return {"fail": "missing mac address"}
