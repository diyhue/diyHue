import configManager
import logManager
import uuid
import json
import weakref
from subprocess import Popen
from lights.manage import sendLightRequest
from flask_restful import Resource
from flask import request
from services.entertainment import entertainmentService
from threading import Thread
from time import sleep
logging = logManager.logger.get_logger(__name__)


bridgeConfig = configManager.bridgeConfig.yaml_config

v2Resources = {"light": {}, "scene": {}, "grouped_light": {}, "room": {}, "entertainment": {}, "entertainment_configuration": {}, "zigbee_connectivity": {}, "device": {}}

def getObject(element, v2uuid):
    if v2uuid in v2Resources[element]:
        logging.debug("Cache Hit for " + element)
        return v2Resources[element][v2uuid]()
    elif element in ["light", "scene", "grouped_light"]:
        for v1Element in ["lights", "groups", "scenes"]:
            for key, obj in bridgeConfig[v1Element].items():
                if obj.id_v2 == v2uuid:
                    v2Resources[element][v2uuid] =  weakref.ref(obj)
                    logging.debug("Cache Miss " + element)
                    return obj
    else:
        for v1Element in ["lights", "groups", "scenes", "sensors"]:
            for key, obj in bridgeConfig[v1Element].items():
                if str(uuid.uuid5(uuid.NAMESPACE_URL, obj.id_v2 + element)) == v2uuid:
                    logging.debug("Cache Miss " + element)
                    v2Resources[element][v2uuid] =  weakref.ref(obj)
                    return obj
    logging.info("element not found!")
    return False

def authorizeV2(headers):
    if "hue-application-key" in headers and headers["hue-application-key"] in bridgeConfig["apiUsers"]:
        return {"user": bridgeConfig["apiUsers"][headers["hue-application-key"]]}
    return []


def buildV2Entertainment():
    result = {}
    result["id"] = "57a9ebc9-406d-4a29-a4ff-42acee9e9be9",
    result["id_v1"] = ""
    result["proxy"] = True
    result["renderer"] = False
    result["type"] = "entertainment"
    return result

def buildV2ZigBee():
    result = {}
    result["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL , bridgeConfig["config"]["bridgeid"] + 'zigbee_connectivity'))
    result["id_v1"] =  ""
    result["mac_address"] = "00:17:88:01:01:59:84:2e"
    result["status"] = "connected"
    result["type"] = "zigbee_connectivity"
    return result


def buildV2Bridge():
    return {
        "bridge_id": bridgeConfig["config"]["bridgeid"].lower(),
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL ,bridgeConfig["config"]["bridgeid"] + 'bridge')),
        "id_v1": "",
        "type": "bridge"
    }

def buildV2Device():
    result = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL , bridgeConfig["config"]["bridgeid"] + 'device')), "type": "device"}
    result["id_v1"] = ""
    result["metadata"] = {
        "archetype": "bridge_v2",
        "name": bridgeConfig["config"]["name"]
    }
    result["product_data"] = {
        "certified": True,
        "manufacturer_name": "Signify Netherlands B.V.",
        "model_id": "BSB002",
        "product_archetype": "bridge_v2",
        "product_name": "Philips hue",
        "software_version": "1.41.1941132080"
    }
    result["services"] = [
        {
          "reference_id": str(uuid.uuid5(uuid.NAMESPACE_URL ,bridgeConfig["config"]["bridgeid"] + 'bridge')),
          "reference_type": "bridge",
          "rid": str(uuid.uuid5(uuid.NAMESPACE_URL ,bridgeConfig["config"]["bridgeid"] + 'bridge')),
          "rtype": "bridge"
        },
        {
          "reference_id": str(uuid.uuid5(uuid.NAMESPACE_URL ,bridgeConfig["config"]["bridgeid"] + 'zigbee_connectivity')),
          "reference_type": "zigbee_connectivity",
          "rid": str(uuid.uuid5(uuid.NAMESPACE_URL ,bridgeConfig["config"]["bridgeid"] + 'zigbee_connectivity')),
          "rtype": "zigbee_connectivity"
        },
        {
          "reference_id": str(uuid.uuid5(uuid.NAMESPACE_URL ,bridgeConfig["config"]["bridgeid"] + 'entertainment')),
          "reference_type": "entertainment",
          "rid": str(uuid.uuid5(uuid.NAMESPACE_URL ,bridgeConfig["config"]["bridgeid"] + 'entertainment')),
          "rtype": "entertainment"
        }
    ]
    return result

class AuthV1(Resource):
    def get(self):
        authorisation = authorizeV2(request.headers)
        if "user" in authorisation:
            logging.debug("Auth 200")
            return {}, 200, {'hue-application-id': '36b1e193-4b74-4763-a054-0578cd927a7b'}

        else:
            logging.debug("Auth 401")
            return "", 401

class ClipV2(Resource):
    def get(self):
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 401
        data = []
        # scenes
        for key, scene in bridgeConfig["scenes"].items():
            data.append(scene.getV2Api())
        # lights
        for key, light in bridgeConfig["lights"].items():
            data.append(light.getV2Api())
        # room
        for key, group in bridgeConfig["groups"].items():
            data.append(group.getV2Room())
        # group
        for key, group in bridgeConfig["groups"].items():
            data.append(group.getV2GroupedLight())
        # zigbee
        for key, light in bridgeConfig["lights"].items():
            data.append(light.getZigBee())
        for key, sensor in bridgeConfig["sensors"].items():
            data.append(sensor.getZigBee())
        data.append(buildV2ZigBee()) # the bridge
        # device
        for key, light in bridgeConfig["lights"].items():
            data.append(light.getDevice())
        for key, sensor in bridgeConfig["sensors"].items():
            data.append(sensor.getDevice())
        data.append(buildV2Device()) # the bridge
        # entertainment
        for key, light in bridgeConfig["lights"].items():
            data.append(light.getV2Entertainment())
            data.append(buildV2Entertainment())
        # entertainment_configuration
        for key, group in bridgeConfig["groups"].items():
            if group.type == "Entertainment":
                data.append(group.getV2EntertainmentConfig())
        data.append(buildV2Bridge())
        return {"errors": [], "data": data}

class ClipV2Resource(Resource):
    def get(self, resource):
        logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 401
        data = []
        if resource == "scene":
            for key, scene in bridgeConfig["scenes"].items():
                data.append(scene.getV2Api())
        elif resource == "light":
            for key, light in bridgeConfig["lights"].items():
                data.append(light.getV2Api())
        elif resource == "room":
            for key, group in bridgeConfig["group"].items():
                data.append(group.getV2Room())
        elif resource == "grouped_light":
            for key, group in bridgeConfig["groups"].items():
                data.append(group.getV2GroupedLight())
        elif resource == "zigbee_connectivity":
            for key, light in bridgeConfig["lights"].items():
                data.append(light.getZigBee())
            for key, sensor in bridgeConfig["sensors"].items():
                zigbee = sensor.getZigBee()
                if zigbee != None:
                    data.append(zigbee)
            data.append(buildV2ZigBee()) # the bridge
        elif resource == "entertainment":
            for key, light in bridgeConfig["lights"].items():
                data.append(light.getV2Entertainment())
                data.append(buildV2Entertainment())
        elif resource == "entertainment_configuration":
            for key, group in bridgeConfig["groups"].items():
                if group.type == "Entertainment":
                    data.append(group.getV2EntertainmentConfig())
        elif resource == "device":
            for key, light in bridgeConfig["lights"].items():
                data.append(light.getDevice())
            for key, sensor in bridgeConfig["sensors"].items():
                device = sensor.getDevice()
                if device != None:
                    data.append(device)
            data.append(buildV2Device()) # the bridge
        elif resource == "bridge":
            data.append(buildV2Bridge())
        return {"errors": [], "data": data}

class ClipV2ResourceId(Resource):
    def get(self, resource, resourceid):
        logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 401
        object = getObject(resource, resourceid)
        if not object:
            return {"errors": [], "data": []}

        if resource in ["scene", "light"]:
            return {"errors": [], "data": [object.getV2Api()]}
        elif resource == "room":
            return {"errors": [], "data": [object.getV2Room()]}
        elif resource == "grouped_light":
            return {"errors": [], "data": [object.getV2GroupedLight()]}
        elif resource == "device":
            return {"errors": [], "data": [object.getDevice()]}
        elif resource == "zigbee_connectivity":
            return {"errors": [], "data": [object.getZigBee()]}
        elif resource == "entertainment":
            return {"errors": [], "data": [object.getV2Entertainment()]}
        elif resource == "entertainment_configuration":
            return {"errors": [], "data": [object.getV2EntertainmentConfig()]}
        elif resource == "bridge":
            return {"errors": [], "data": [buildV2Bridge()]}


    def put(self, resource, resourceid):
        logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 401
        putDict = request.get_json(force=True)
        logging.debug(putDict)
        object = getObject(resource, resourceid)
        if resource == "light":
            v1Request = {}
            if "dimming" in putDict:
                v1Request["bri"] = putDict["dimming"]["brightness"]
            if "on" in putDict:
                v1Request["on"] =  putDict["on"]["on"]
            if "color" in putDict:
                if "xy" in putDict["color"]:
                    v1Request["xy"] = [putDict["color"]["xy"]["x"], putDict["color"]["xy"]["y"]]
                v1Request["on"] =  putDict["on"]["on"]
                if object.modelid in ["LCX001", "LCX002", "LCX003"]:
                    if object.id_v1 not in bridgeConfig["temp"]["gradientStripLights"] or bridgeConfig["temp"]["gradientStripLights"][object.id_v1] > 7:
                        bridgeConfig["temp"]["gradientStripLights"][object.id_v1] = 1
                    object.setV1State(state={"lights": {bridgeConfig["temp"]["gradientStripLights"][object.id_v1]: v1Request}})
                    bridgeConfig["temp"]["gradientStripLights"][object.id_v1] += 1
                else:
                    object.setV1State(state=v1Request)

        elif resource == "entertainment_configuration":
            if "action" in putDict:
                if putDict["action"] == "start":
                    logging.info("start hue entertainment")
                    Thread(target=entertainmentService, args=[object, authorisation["user"]]).start()
                    sleep(3)
                elif putDict["action"] == "stop":
                    logging.info("stop entertainment")
                    Popen(["killall", "entertain-srv"])
        response = {"data": [{
            "reference_id": resourceid,
            "reference_type": resource,
            "rid": resourceid,
            "rtype": resource
            }]}
        return response


    def post(self, resource, resourceid):
        logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 401
        putDict = request.get_json(force=True)
        return {"ok"}
