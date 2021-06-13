import configManager
import logManager
import HueObjects
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
from functions.core import nextFreeId
from datetime import datetime
from pprint import pprint
logging = logManager.logger.get_logger(__name__)


bridgeConfig = configManager.bridgeConfig.yaml_config

v2Resources = {"light": {}, "scene": {}, "grouped_light": {}, "room": {}, "entertainment": {}, "entertainment_configuration": {}, "zigbee_connectivity": {}, "device": {}}

def getObject(element, v2uuid):
    if element in v2Resources and v2uuid in v2Resources[element]:
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


def v2BridgeEntertainment():
    return {"id": "57a9ebc9-406d-4a29-a4ff-42acee9e9be7",
        "id_v1": "",
        "proxy": True,
        "renderer": False,
        "type": "entertainment"
    }

def v2HomeKit():
    return { "id": str(uuid.uuid5(uuid.NAMESPACE_URL , bridgeConfig["config"]["bridgeid"] + 'homekit')),
      "status": "unpaired",
      "type": "homekit"
    }

def v2BridgeZigBee():
    result = {}
    result["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL , bridgeConfig["config"]["bridgeid"] + 'zigbee_connectivity'))
    result["id_v1"] =  ""
    result["status"] = "connected"
    result["type"] = "zigbee_connectivity"
    return result

def v2BridgeHome():
    result = {}
    #result["grouped_services"] = [{
    #      "rid": bridgeConfig["groups"]["0"].id_v2,
    #      "rtype": "grouped_light"
    #    }]
    result["grouped_services"] = []
    if len(bridgeConfig["lights"]) > 0:
        result["grouped_services"].append({
             "rid": bridgeConfig["groups"]["0"].id_v2,
             "rtype": "grouped_light"
            })
    result["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL , bridgeConfig["config"]["bridgeid"] + 'bridge_home'))
    result["id_v1"] = "/groups/0"
    result["services"] = []
    result["type"] = "bridge_home"
    for key, light in bridgeConfig["lights"].items():
        result["services"].append(light.getBridgeHome())
    for key, sensor in bridgeConfig["sensors"].items():
        if sensor.getBridgeHome():
            result["services"].append(sensor.getBridgeHome())
    return result


def v2Bridge():
    return {
        "bridge_id": bridgeConfig["config"]["bridgeid"].lower(),
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL ,bridgeConfig["config"]["bridgeid"] + 'bridge')),
        "id_v1": "",
        "type": "bridge"
    }

def geoLocation():
    return {
      "id": str(uuid.uuid5(uuid.NAMESPACE_URL ,bridgeConfig["config"]["bridgeid"] + 'geolocation')),
      "id_v1": "",
      "is_configured": bridgeConfig["sensors"]["1"].config["configured"],
      "type": "geolocation"
    }

def v2BridgeDevice():
    result = {"id": str(uuid.uuid5(uuid.NAMESPACE_URL , bridgeConfig["config"]["bridgeid"] + 'device')), "type": "device"}
    result["id_v1"] = ""
    result["metadata"] = {
        "archetype": "bridge_v2",
        "name": "Philips hue" #bridgeConfig["config"]["name"]
    }
    result["product_data"] = {
        "certified": True,
        "manufacturer_name": "Signify Netherlands B.V.",
        "model_id": "BSB002",
        "product_archetype": "bridge_v2",
        "product_name": "Philips hue",
        "software_version": "1.45.1945091050"
    }
    result["services"] = [
        {
          "rid": str(uuid.uuid5(uuid.NAMESPACE_URL ,bridgeConfig["config"]["bridgeid"] + 'bridge')),
          "rtype": "bridge"
        },
        {
          "rid": str(uuid.uuid5(uuid.NAMESPACE_URL ,bridgeConfig["config"]["bridgeid"] + 'zigbee_connectivity')),
          "rtype": "zigbee_connectivity"
        },
        {
          "rid": str(uuid.uuid5(uuid.NAMESPACE_URL ,bridgeConfig["config"]["bridgeid"] + 'entertainment')),
          "rtype": "entertainment"
        }
    ]
    return result

def convertV2StateToV1(state):
    v1State = {}
    if "dimming" in state:
        v1State["bri"] = int(state["dimming"]["brightness"] * 2.54)
    if "on" in state:
        v1State["on"] =  state["on"]["on"]
    if "color_temperature" in state:
        v1State["ct"] =  state["color_temperature"]["mirek"]
    if "color" in state:
        if "xy" in state["color"]:
            v1State["xy"] = [state["color"]["xy"]["x"], state["color"]["xy"]["y"]]
    return v1State

class AuthV1(Resource):
    def get(self):
        authorisation = authorizeV2(request.headers)
        if "user" in authorisation:
            logging.debug("Auth 200")
            return {}, 200, {'hue-application-id': '36b1e193-4b74-4763-a054-0578cd927a7b'}

        else:
            logging.debug("Auth 403")
            return "", 403


class ClipV2(Resource):
    def get(self):
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403
        data = []
        # homekit
        data.append(v2HomeKit())
        # device
        data.append(v2BridgeDevice())
        for key, light in bridgeConfig["lights"].items():
            data.append(light.getDevice())
        for key, sensor in bridgeConfig["sensors"].items():
            if sensor.getDevice() != None:
                data.append(sensor.getDevice())
        # bridge
        data.append(v2Bridge())
        # zigbee
        data.append(v2BridgeZigBee())
        for key, light in bridgeConfig["lights"].items():
            data.append(light.getZigBee())
        for key, sensor in bridgeConfig["sensors"].items():
            if sensor.getZigBee() != None:
                data.append(sensor.getZigBee())
        # entertainment
        data.append(v2BridgeEntertainment())
        for key, light in bridgeConfig["lights"].items():
            data.append(light.getV2Entertainment())
        # scenes
        for key, scene in bridgeConfig["scenes"].items():
            data.append(scene.getV2Api())
        # lights
        for key, light in bridgeConfig["lights"].items():
            data.append(light.getV2Api())
        # room
        for key, group in bridgeConfig["groups"].items():
            if group.type == "Room":
                data.append(group.getV2Room())
        # group
        for key, group in bridgeConfig["groups"].items():
            data.append(group.getV2GroupedLight())
        # entertainment_configuration
        for key, group in bridgeConfig["groups"].items():
            if group.type == "Entertainment":
                data.append(group.getV2EntertainmentConfig())
        # bridge home
        data.append(v2BridgeHome())
        return {"errors": [], "data": data}

class ClipV2Resource(Resource):
    def get(self, resource):
        #logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403
        response = {"data": [], "errors": []}
        if resource == "scene":
            for key, scene in bridgeConfig["scenes"].items():
                response["data"].append(scene.getV2Api())
        elif resource == "light":
            for key, light in bridgeConfig["lights"].items():
                response["data"].append(light.getV2Api())
        elif resource == "room":
            for key, group in bridgeConfig["groups"].items():
                if group.type == "Room":
                    response["data"].append(group.getV2Room())
        elif resource == "zone":
            for key, group in bridgeConfig["groups"].items():
                if group.type == "Zone":
                    print("to be defined")
        elif resource == "grouped_light":
            for key, group in bridgeConfig["groups"].items():
                response["data"].append(group.getV2GroupedLight())
        elif resource == "zigbee_connectivity":
            for key, light in bridgeConfig["lights"].items():
                zigbee = light.getZigBee()
                if zigbee != None:
                    response["data"].append(zigbee)
            for key, sensor in bridgeConfig["sensors"].items():
                zigbee = sensor.getZigBee()
                if zigbee != None:
                    response["data"].append(zigbee)
            response["data"].append(v2BridgeZigBee()) # the bridge
        elif resource == "entertainment":
            for key, light in bridgeConfig["lights"].items():
                response["data"].append(light.getV2Entertainment())
            response["data"].append(v2BridgeEntertainment())
        elif resource == "entertainment_configuration":
            for key, group in bridgeConfig["groups"].items():
                if group.type == "Entertainment":
                    response["data"].append(group.getV2EntertainmentConfig())
        elif resource == "device":
            for key, light in bridgeConfig["lights"].items():
                response["data"].append(light.getDevice())
            for key, sensor in bridgeConfig["sensors"].items():
                device = sensor.getDevice()
                if device != None:
                    response["data"].append(device)
            response["data"].append(v2BridgeDevice()) # the bridge
        elif resource == "bridge":
            response["data"].append(v2Bridge())
        elif resource == "bridge_home":
            response["data"].append(v2BridgeHome())
        elif resource == "geolocation":
            response["data"].append(geoLocation())
            response["type"] = "ClipMessageGeolocation"
        elif resource == "behavior_instance":
            for key, behavior_instance in bridgeConfig["behavior_instances"].items():
                response["data"].append(behavior_instance.getV2Api())
            response["type"] = "ClipMessageBehaviorInstance"
        elif resource == "geofence_client":
            response["type"] = "ClipMessageGeofenceClient"
        else:
            response["errors"].append({"description": "Not Found"})
            del response["data"]

        return response

    def post(self, resource):
        #logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403
        postDict = request.get_json(force=True)
        logging.debug(postDict)
        newObject = None
        if resource == "scene":
            new_object_id = nextFreeId(bridgeConfig, "scenes")
            objCreation = {
                "id_v1": new_object_id,
                "name": postDict["metadata"]["name"],
                "image": postDict["metadata"]["image"]["rid"],
                "owner": bridgeConfig["apiUsers"][request.headers["hue-application-key"]],
            }
            if "group" in postDict:
                objCreation["group"] = weakref.ref(getObject(postDict["group"]["rtype"], postDict["group"]["rid"]))
                objCreation["type"] = "GroupScene"
            elif "lights" in postDict:
                objCreation["type"] = "LightScene"
                objLights = []
                for light in postDict["lights"]:
                    objLights.append(getObject(light["rtype"], light["rid"]))
                objCreation["lights"] = objLights
            newObject = HueObjects.Scene(objCreation)
            bridgeConfig["scenes"][new_object_id] = newObject
        elif resource == "behavior_instance":
            newObject = HueObjects.BehaviorInstance(postDict)
            bridgeConfig["behavior_instances"][newObject.id_v2] = newObject
        # build stream message
        streamMessage = {"creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": newObject.id_v2, "type": resource}],
                "id": str(uuid.uuid4()),
                "type": "add"
                }
        streamMessage["id_v1"] = "/" + newObject.getObjectPath()["resource"] + "/" + newObject.getObjectPath()["id"] if  hasattr(newObject, 'getObjectPath') else ""
        streamMessage["data"][0].update(postDict)
        bridgeConfig["temp"]["eventstream"].append(streamMessage)

        return {"data": [{
                    "rid": newObject.id_v2,
                    "rtype": resource}
                ],"errors": []}



class ClipV2ResourceId(Resource):
    def get(self, resource, resourceid):
        #logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403
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
            return {"errors": [], "data": [v2Bridge()]}


    def put(self, resource, resourceid):
        #logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403
        putDict = request.get_json(force=True)
        logging.debug(putDict)
        object = getObject(resource, resourceid)
        if resource == "light":
            v1Request = convertV2StateToV1(putDict)
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
        elif resource == "scene":
            object.activate(putDict)
        elif resource == "grouped_light":
            v1Request = convertV2StateToV1(putDict)
            object.setV1Action(state=v1Request, scene=None)
        elif resource == "geolocation":
            bridgeConfig["sensors"]["1"].protocol_cfg = {"lat": putDict["latitude"], "long": putDict["longitude"]}
            bridgeConfig["sensors"]["1"].config["configured"] = True
        response = {"data": [{
            "rid": resourceid,
            "rtype": resource
            }]}


        streamMessage = {"creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": resourceid, "type": resource}],
                "id": str(uuid.uuid4()),
                "type": "update"
                }
        streamMessage["id_v1"] = "/" + object.getObjectPath()["resource"] + "/" + object.getObjectPath()["id"] if  hasattr(object, 'getObjectPath') else ""
        streamMessage["data"][0].update(putDict)
        bridgeConfig["temp"]["eventstream"].append(streamMessage)
        return response


    def delete(self, resource, resourceid):
        #logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403
        object = getObject(resource, resourceid)
        del bridgeConfig[object.getObjectPath()["resource"]][object.getObjectPath()["id"]]
        response = {"data": [{
            "rid": resourceid,
            "rtype": resource
            }]}

        bridgeConfig["temp"]["eventstream"].append({"creationtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "data": [{"id": object.id_v2, "id_v1": "/" + object.getObjectPath()["resource"] + "/" + object.getObjectPath()["id"], "type": resource}],
                "id": str(uuid.uuid4()),
                "type": "delete"
                })
        return response
