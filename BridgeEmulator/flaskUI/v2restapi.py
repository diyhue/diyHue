import configManager
import logManager
import HueObjects
import uuid
import json
import weakref
from subprocess import Popen
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

v2Resources = {"light": {}, "scene": {}, "grouped_light": {}, "room": {}, "zone": {
}, "entertainment": {}, "entertainment_configuration": {}, "zigbee_connectivity": {}, "device": {}}


def getObject(element, v2uuid):
    if element in ["behavior_instance"]:
        return bridgeConfig[element][v2uuid]
    elif element in v2Resources and v2uuid in v2Resources[element]:
        logging.debug("Cache Hit for " + element)
        return v2Resources[element][v2uuid]()
    elif element in ["light", "scene", "grouped_light"]:
        for v1Element in ["lights", "groups", "scenes"]:
            for key, obj in bridgeConfig[v1Element].items():
                if obj.id_v2 == v2uuid:
                    v2Resources[element][v2uuid] = weakref.ref(obj)
                    logging.debug("Cache Miss " + element)
                    return obj
    elif element in ["entertainment"]:
        for key, obj in bridgeConfig["lights"].items():
            if str(uuid.uuid5(uuid.NAMESPACE_URL, obj.id_v2 + 'entertainment')) == v2uuid:
                v2Resources[element][v2uuid] = weakref.ref(obj)
                return obj
    else:
        for v1Element in ["lights", "groups", "scenes", "sensors"]:
            for key, obj in bridgeConfig[v1Element].items():
                if str(uuid.uuid5(uuid.NAMESPACE_URL, obj.id_v2 + element)) == v2uuid:
                    logging.debug("Cache Miss " + element)
                    v2Resources[element][v2uuid] = weakref.ref(obj)
                    return obj
    logging.info("element not found!")
    return False


def authorizeV2(headers):
    if "hue-application-key" in headers and headers["hue-application-key"] in bridgeConfig["apiUsers"]:
        bridgeConfig["apiUsers"][headers["hue-application-key"]
                                 ].last_use_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
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
    return {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'homekit')),
            "status": "unpaired",
            "status_values": [
                "pairing",
                "paired",
                "unpaired"
            ],
        "type": "homekit"
    }


def v2BridgeZigBee():
    result = {}
    result["id"] = str(uuid.uuid5(
        uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'zigbee_connectivity'))
    result["id_v1"] = ""
    result["status"] = "connected"
    result["type"] = "zigbee_connectivity"
    return result


def v2BridgeHome():
    result = {}
    result["children"] = []
    result["grouped_services"] = []
    if len(bridgeConfig["lights"]) > 0:
        result["grouped_services"].append({
            "rid": bridgeConfig["groups"]["0"].id_v2,
            "rtype": "grouped_light"
        })
    result["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL,
                                  bridgeConfig["groups"]["0"].id_v2 + 'bridge_home'))
    result["id_v1"] = "/groups/0"
    result["services"] = []
    result["type"] = "bridge_home"
    for key, light in bridgeConfig["lights"].items():
        result["services"].append(light.getBridgeHome())
        result["children"].append({"rid": light.getDevice()["id"], "rtype": "device"})
    for key, group in bridgeConfig["groups"].items():
        if group.type == "Room":
            result["children"].append({"rid": group.getV2Room()["id"], "rtype": "room"})
    for key, sensor in bridgeConfig["sensors"].items():
        if sensor.getBridgeHome():
            result["services"].append(sensor.getBridgeHome())
    result["services"].append({"rid": bridgeConfig["groups"]["0"].id_v2 ,"rtype": "grouped_light"})
    return result


def v2Bridge():
    return {
        "bridge_id": bridgeConfig["config"]["bridgeid"].lower(),
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'bridge')),
        "id_v1": "",
        "owner": {
            "rid": str(uuid.uuid5(
                uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'device')),
            "rtype": "device"
        },
        "time_zone": {
            "time_zone": bridgeConfig["config"]["timezone"]
        },

        "type": "bridge"
    }


def geoLocation():
    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'geolocation')),
        "id_v1": "",
        "is_configured": bridgeConfig["sensors"]["1"].config["configured"],
        "type": "geolocation"
    }


def v2BridgeDevice():
    result = {"id": str(uuid.uuid5(
        uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'device')), "type": "device"}
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
        "software_version": bridgeConfig["config"]["apiversion"] + bridgeConfig["config"]["swversion"]
    }
    result["services"] = [
        {
            "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'bridge')),
            "rtype": "bridge"
        },
        {
            "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'zigbee_connectivity')),
            "rtype": "zigbee_connectivity"
        },
        {
            "rid": str(uuid.uuid5(uuid.NAMESPACE_URL, bridgeConfig["config"]["bridgeid"] + 'entertainment')),
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
            logging.debug("Auth 403")
            return '', 403


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
            elif group.type == "Zone":
                data.append(group.getV2Zone())
        # group
        for key, group in bridgeConfig["groups"].items():
            data.append(group.getV2GroupedLight())
        # entertainment_configuration
        for key, group in bridgeConfig["groups"].items():
            if group.type == "Entertainment":
                data.append(group.getV2Api())
        # bridge home
        data.append(v2BridgeHome())
        return {"errors": [], "data": data}


class ClipV2Resource(Resource):
    def get(self, resource):
        # logging.debug(request.headers)
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
                    response["data"].append(group.getV2Zone())
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
            response["data"].append(v2BridgeZigBee())  # the bridge
        elif resource == "entertainment":
            for key, light in bridgeConfig["lights"].items():
                response["data"].append(light.getV2Entertainment())
            response["data"].append(v2BridgeEntertainment())
        elif resource == "entertainment_configuration":
            for key, group in bridgeConfig["groups"].items():
                if group.type == "Entertainment":
                    response["data"].append(group.getV2Api())
        elif resource == "device":
            for key, light in bridgeConfig["lights"].items():
                response["data"].append(light.getDevice())
            for key, sensor in bridgeConfig["sensors"].items():
                device = sensor.getDevice()
                if device != None:
                    response["data"].append(device)
            response["data"].append(v2BridgeDevice())  # the bridge
        elif resource == "bridge":
            response["data"].append(v2Bridge())
        elif resource == "bridge_home":
            response["data"].append(v2BridgeHome())
        elif resource == "homekit":
            response["data"].append(v2HomeKit())
        elif resource == "geolocation":
            response["data"].append(geoLocation())
        elif resource == "behavior_instance":
            for key, instance in bridgeConfig["behavior_instance"].items():
                response["data"].append(instance.getV2Api())
        else:
            response["errors"].append({"description": "Not Found"})
            del response["data"]

        return response

    def post(self, resource):
        # logging.debug(request.headers)
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
                "image": postDict["metadata"]["image"]["rid"] if "image" in postDict["metadata"] else None,
                "owner": bridgeConfig["apiUsers"][request.headers["hue-application-key"]],
            }
            if "group" in postDict:
                objCreation["group"] = weakref.ref(
                    getObject(postDict["group"]["rtype"], postDict["group"]["rid"]))
                objCreation["type"] = "GroupScene"
                del postDict["group"]
            elif "lights" in postDict:
                objCreation["type"] = "LightScene"
                objLights = []
                for light in postDict["lights"]:
                    objLights.append(getObject(light["rtype"], light["rid"]))
                objCreation["lights"] = objLights
            objCreation.update(postDict)
            newObject = HueObjects.Scene(objCreation)
            bridgeConfig["scenes"][new_object_id] = newObject
            if "actions" in postDict:
                for action in postDict["actions"]:
                    if "target" in action:
                        if action["target"]["rtype"] == "light":
                            lightObj = getObject(
                                "light",  action["target"]["rid"])
                            sceneState = {}
                            scene = action["action"]
                            if "on" in scene:
                                sceneState["on"] = scene["on"]["on"]
                            if "dimming" in scene:
                                sceneState["bri"] = int(
                                    scene["dimming"]["brightness"] * 2.54)
                            if "color" in scene:
                                if "xy" in scene["color"]:
                                    sceneState["xy"] = [
                                        scene["color"]["xy"]["x"], scene["color"]["xy"]["y"]]
                            if "color_temperature" in scene:
                                if "mirek" in scene["color_temperature"]:
                                    sceneState["ct"] = scene["color_temperature"]["mirek"]
                            if "gradient" in scene:
                                sceneState["gradient"] = scene["gradient"]
                            newObject.lightstates[lightObj] = sceneState
        elif resource == "behavior_instance":
            newObject = HueObjects.BehaviorInstance(postDict)
            bridgeConfig["behavior_instance"][newObject.id_v2] = newObject
        elif resource == "entertainment_configuration":
            new_object_id = nextFreeId(bridgeConfig, "groups")
            objCreation = {
                "id_v1": new_object_id,
                "name": postDict["metadata"]["name"]
            }
            objCreation.update(postDict)
            newObject = HueObjects.EntertainmentConfiguration(objCreation)
            if "locations" in postDict:
                if "service_locations" in postDict["locations"]:
                    for element in postDict["locations"]["service_locations"]:
                        obj = getObject(
                            element["service"]["rtype"], element["service"]["rid"])
                        newObject.add_light(obj)
                        newObject.locations[obj] = element["positions"]
            bridgeConfig["groups"][new_object_id] = newObject

        # return message
        returnMessage = {"data": [{
            "rid": newObject.id_v2,
            "rtype": resource}
        ], "errors": []}
        if resource == "behavior_instance":
            returnMessage["data"][0]["type"] = "ResourceIdentifier"
            returnMessage["type"] = "ClipMessageBehaviorInstance"

        logging.debug(json.dumps(returnMessage, sort_keys=True, indent=4))
        return returnMessage


class ClipV2ResourceId(Resource):
    def get(self, resource, resourceid):
        # logging.debug(request.headers)
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
            return {"errors": [], "data": [object.getV2Api()]}
        elif resource == "bridge":
            return {"errors": [], "data": [v2Bridge()]}

    def put(self, resource, resourceid):
        logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403
        putDict = request.get_json(force=True)
        logging.debug(putDict)
        object = getObject(resource, resourceid)
        if resource == "light":
            object.setV2State(putDict)
        elif resource == "entertainment_configuration":
            if "action" in putDict:
                if putDict["action"] == "start":
                    logging.info("start hue entertainment")
                    object.stream.update(
                        {"active": True, "owner": authorisation["user"].username, "proxymode": "auto", "proxynode": "/bridge"})
                    Thread(target=entertainmentService, args=[
                           object, authorisation["user"]]).start()
                    for light in object.lights:
                        light().state["mode"] = "streaming"
                    sleep(1)
                elif putDict["action"] == "stop":
                    logging.info("stop entertainment")
                    object.stream["active"] = False
                    for light in object.lights:
                        light().state["mode"] = "homeautomation"
                    Popen(["killall", "openssl"])
        elif resource == "scene":
            if "recall" in putDict:
                object.activate(putDict)
            if "speed" in putDict:
                object.speed = putDict["speed"]
            if "palette" in putDict:
                object.palette = putDict["palette"]
            if "metadata" in putDict:
                object.name = putDict["metadata"]["name"]
        elif resource == "grouped_light":
            object.setV2Action(putDict)
        elif resource == "geolocation":
            bridgeConfig["sensors"]["1"].protocol_cfg = {
                "lat": putDict["latitude"], "long": putDict["longitude"]}
            bridgeConfig["sensors"]["1"].config["configured"] = True
        elif resource == "behavior_instance":
            object.update_attr(putDict)
        response = {"data": [{
            "rid": resourceid,
            "rtype": resource
        }]}

        return response

    def delete(self, resource, resourceid):
        # logging.debug(request.headers)
        authorisation = authorizeV2(request.headers)
        if "user" not in authorisation:
            return "", 403
        object = getObject(resource, resourceid)

        if hasattr(object, 'getObjectPath'):
            del bridgeConfig[object.getObjectPath()["resource"]
                             ][object.getObjectPath()["id"]]
        else:
            del bridgeConfig[resource][resourceid]

        response = {"data": [{
            "rid": resourceid,
            "rtype": resource
        }]}
        return response
