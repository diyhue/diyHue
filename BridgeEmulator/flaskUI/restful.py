import configManager
import logManager
from HueObjects import ApiUser, Group, EntertainmentConfiguration, Scene, Rule, ResourceLink, Sensor, Schedule
import weakref
import uuid
import json
import os
from subprocess import Popen
from threading import Thread
from datetime import datetime, timezone
from lights.discover import scanForLights, manualAddLight
from functions.core import capabilities, staticConfig, nextFreeId
from flask_restful import Resource
from flask import request
from functions.rules import rulesProcessor
from services.entertainment import entertainmentService
from services.updateManager import githubCheck, versionCheck, githubInstall
from werkzeug.security import generate_password_hash

try:
    from time import tzset
except ImportError:
    tzset = None

logging = logManager.logger.get_logger(__name__)

bridgeConfig = configManager.bridgeConfig.yaml_config

def GroupZeroMessage():
    rooms = []
    lights = []
    for group, obj in bridgeConfig["groups"].items():
        rooms.append(obj.id_v2)
    for light, obj in bridgeConfig["lights"].items():
        lights.append(obj.id_v2)
    bridgeConfig["groups"]["0"].groupZeroStream(rooms, lights)

def authorize(username, resource='', resourceId='', resourceParam=''):
    if username not in bridgeConfig["apiUsers"] and request.remote_addr != "127.0.0.1":
        return [{"error": {"type": 1, "address": "/" + resource + "/" + resourceId, "description": "unauthorized user"}}]

    if resourceId not in ["0", "new", "timezones", "whitelist"] and resourceId != '' and resourceId not in bridgeConfig[resource]:
        logging.debug(str(resourceId) + " not in bridgeConfig " + str(resource))
        return [{"error": {"type": 3, "address": "/" + resource + "/" + resourceId, "description": "resource, " + resource + "/" + resourceId + ", not available"}}]

    if resourceId != "0" and resourceParam != '' and not hasattr(bridgeConfig[resource][resourceId], resourceParam):
        logging.debug(str(resourceId) + " has no attribute " + str(resourceParam))
        return [{"error": {"type": 3, "address": "/" + resource + "/" + resourceId + "/" + resourceParam, "description": "resource, " + resource + "/" + resourceId + "/" + resourceParam + ", not available"}}]
    if request.remote_addr != "127.0.0.1":
        bridgeConfig["apiUsers"][username].last_use_date = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S")
    return ["success"]


def buildConfig():
    result = staticConfig()
    config = bridgeConfig["config"]
    result.update({"Hue Essentials key": config["Hue Essentials key"], "Remote API enabled": config["Remote API enabled"], "apiversion": config["apiversion"], "bridgeid": config["bridgeid"],
                   "ipaddress": config["ipaddress"], "netmask": config["netmask"], "gateway": config["gateway"], "mac": config["mac"], "name": config["name"], "swversion": config["swversion"], "swupdate2": config["swupdate2"], "timezone": config["timezone"], "discovery": config["discovery"]})
    result["UTC"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    result["localtime"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    result["whitelist"] = {}
    for key, user in bridgeConfig["apiUsers"].items():
        result["whitelist"][key] = {"create date": user.create_date,
                                    "last use date": user.last_use_date, "name": user.name}
    return result


class NewUser(Resource):
    def get(self):
        return [{"error": {"type": 4, "address": "/api", "description": "method, GET, not available for resource, /"}}]

    def post(self):
        postDict = request.get_json(force=True)
        logging.info(postDict)
        if "devicetype" in postDict:
            last_button_press = bridgeConfig["config"]["linkbutton"]["lastlinkbuttonpushed"]
            if last_button_press + 30 >= datetime.now().timestamp(): # 30 sec offset
                username = str(uuid.uuid1()).replace('-', '')
                if postDict["devicetype"].startswith("Hue Essentials"):
                    username = "hueess" + username[-26:]
                response = [{"success": {"username": username}}]
                client_key = None
                if "generateclientkey" in postDict and postDict["generateclientkey"]:
                    client_key = str(uuid.uuid4()).replace('-', '').upper()
                    # client_key = "321c0c2ebfa7361e55491095b2f5f9db"

                    response[0]["success"]["clientkey"] = client_key
                bridgeConfig["apiUsers"][username] = ApiUser.ApiUser(username, postDict["devicetype"], client_key)
                logging.debug(response)
                configManager.bridgeConfig.save_config()
                return response
            else:
                logging.error("link button not pressed")
                logging.error("last_button_press" + str(last_button_press))
                logging.error("current time" + str(datetime.now().timestamp()))
                return [{"error": {"type": 101, "address": "/api/", "description": "link button not pressed"}}]
        else:
            logging.error("parameter, " + list(postDict.keys())[0] + ", not available")
            return [{"error": {"type": 6, "address": "/api/" + list(postDict.keys())[0], "description":"parameter, " + list(postDict.keys())[0] + ", not available"}}]


class ShortConfig(Resource):
    def get(self):
        config = bridgeConfig["config"]
        return {"apiversion": config["apiversion"], "bridgeid": config["bridgeid"], "datastoreversion": staticConfig()["datastoreversion"], "factorynew": False, "mac": config["mac"], "modelid": "BSB002", "name": config["name"], "replacesbridgeid": None, "starterkitid": "", "swversion": config["swversion"]}


class EntireConfig(Resource):
    def get(self, username):
        authorisation = authorize(username)
        if "success" not in authorisation:
            return authorisation
        result = {}
        result["config"] = buildConfig()
        for resource in ["lights", "groups", "scenes", "rules", "resourcelinks", "schedules", "sensors"]:
            result[resource] = {}
            for resource_id in bridgeConfig[resource]:
                if resource_id != "0":
                    result[resource][resource_id] = bridgeConfig[resource][resource_id].getV1Api().copy()
        return result


class ResourceElements(Resource):
    def get(self, username, resource):
        authorisation = authorize(username)
        if "success" in authorisation:
            if resource == "capabilities":
                return capabilities()
            else:
                response = {}
                if resource in ["lights", "groups", "scenes", "rules", "resourcelinks", "schedules", "sensors", "apiUsers"]:
                    for object in bridgeConfig[resource]:
                        response[object] = bridgeConfig[resource][object].getV1Api().copy()
                elif resource == "config":
                    response = buildConfig()
                return response
        elif resource == "config":
            config = bridgeConfig["config"]

            return {"name": config["name"], "datastoreversion": staticConfig()["datastoreversion"], "swversion": config["swversion"], "apiversion": config["apiversion"], "mac": config["mac"], "bridgeid": config["bridgeid"], "factorynew": False, "replacesbridgeid": None, "modelid": staticConfig()["modelid"], "starterkitid": ""}
        return [{"error": {"type": 1, "address": "/", "description": "unauthorized user"}}]

    def post(self, username, resource):
        authorisation = authorize(username, resource)
        if "success" not in authorisation:
            return authorisation

        if resource in ["lights", "sensors"] and request.get_data(as_text=True) == "":
            # if was a request to scan for lights or sensors
            Thread(target=scanForLights).start()
            return [{"success": {"/" + resource: "Searching for new devices"}}]
        postDict = request.get_json(force=True)
        logging.info(postDict)
        if resource == "lights":  # add light manually from the web interface
            Thread(target=manualAddLight, args=[postDict["ip"], postDict["protocol"], postDict["config"]]).start()
            return [{"success": {"/" + resource: "Searching for new devices"}}]
        v2Resource = None
        # find the first unused id for new object
        new_object_id = nextFreeId(bridgeConfig, resource)
        postDict["id_v1"] = new_object_id
        postDict["owner"] = bridgeConfig["apiUsers"][username]
        if resource == "groups":
            if "type" in postDict:
                if postDict["type"] == "Zone":
                    v2Resource = "zone"
                    bridgeConfig[resource][new_object_id] = Group.Group(postDict)
                elif postDict["type"] == "Room":
                    v2Resource = "room"
                    bridgeConfig[resource][new_object_id] = Group.Group(postDict)
                elif postDict["type"] == "Entertainment":
                    v2Resource = "entertainment_configuration"
                    bridgeConfig[resource][new_object_id] = EntertainmentConfiguration.EntertainmentConfiguration(postDict)

            if "lights" in postDict:
                for light in postDict["lights"]:
                    bridgeConfig[resource][new_object_id].add_light(
                        bridgeConfig["lights"][light])
            if "locations" in postDict:
                for light, location in postDict["locations"].items():
                    bridgeConfig[resource][new_object_id].locations[bridgeConfig["lights"]
                                                                    [light]] = [{"x": location[0], "y": location[1], "z": location[2]}]
            # trigger stream messages
            GroupZeroMessage()
        elif resource == "scenes":
            v2Resource = "scene"
            if "group" in postDict:
                postDict["group"] = weakref.ref(
                    bridgeConfig["groups"][postDict["group"]])
            elif "lights" in postDict:
                objLights = []
                for light in postDict["lights"]:
                    objLights.append(weakref.ref(
                        bridgeConfig["lights"][light]))
                postDict["lights"] = objLights
            bridgeConfig[resource][new_object_id] = Scene.Scene(postDict)
            scene = bridgeConfig[resource][new_object_id]
            if "lightstates" in postDict:
                for light, state in postDict["lightstates"].items():
                    scene.lightstates[bridgeConfig["lights"][light]] = state
            else:
                if "group" in postDict:
                    for light in postDict["group"]().lights:
                        scene.lightstates[light()] = {
                            "on": light().state["on"]}
                elif "lights" in postDict:
                    for light in postDict["lights"]:
                        scene.lightstates[light()] = {
                            "on": light().state["on"]}
                # add remaining state details in one shot.
                sceneStates = list(scene.lightstates.items())
                for light, state in sceneStates:
                    if "bri" in light.state:
                        state["bri"] = light.state["bri"]
                    if "colormode" in light.state:
                        if light.state["colormode"] == "ct":
                            state["ct"] = light.state["ct"]
                        elif light.state["colormode"] == "xy":
                            state["xy"] = light.state["xy"]
                        elif light.state["colormode"] == "hs":
                            state["hue"] = light.state["hue"]
                            state["sat"] = light.state["sat"]

        elif resource == "rules":
            bridgeConfig[resource][new_object_id] = Rule.Rule(postDict)
        elif resource == "resourcelinks":
            bridgeConfig[resource][new_object_id] = ResourceLink.ResourceLink(postDict)
        elif resource == "sensors":
            v2Resource = "device"
            bridgeConfig[resource][new_object_id] = Sensor.Sensor(postDict)
        elif resource == "schedules":
            bridgeConfig[resource][new_object_id] = Schedule.Schedule(postDict)
        newObject = bridgeConfig[resource][new_object_id]
        if v2Resource != "none":
            streamMessage = {"creationtime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "data": [],
                             "id_v1": "/" + resource + "/" + new_object_id,
                             "id": str(uuid.uuid4()),
                             "type": "add"
                             }
            if resource == "groups":
                if v2Resource == "room":
                    streamMessage["data"].append(newObject.getV2Room())
                elif v2Resource == "zone":
                    streamMessage["data"].append(newObject.getV2Zone())
                elif  v2Resource == "entertainment_configuration":
                    streamMessage["data"].append(newObject.getV2Api())
                else:
                    streamMessage["data"].append(newObject.getV2GroupedLight())
            elif hasattr(newObject, 'getV2Api'):
                streamMessage["data"].append(newObject.getV2Api())
            bridgeConfig["temp"]["eventstream"].append(streamMessage)
            logging.debug(streamMessage)
        logging.info(json.dumps([{"success": {"id": new_object_id}}],
                                sort_keys=True, indent=4, separators=(',', ': ')))
        configManager.bridgeConfig.save_config(backup=False, resource=resource)
        return [{"success": {"id": new_object_id}}]

    def put(self, username, resource):
        authorisation = authorize(username, resource)
        if "success" not in authorisation:
            return authorisation
        putDict = request.get_json(force=True)
        # apply timezone OS variable
        if resource == "config" and "timezone" in putDict:
            os.environ['TZ'] = putDict["timezone"]
            if tzset is not None:
                tzset()

        for key, value in putDict.items():
            if isinstance(value, dict):
                bridgeConfig[resource][key].update(value)
            else:
                bridgeConfig[resource][key] = value

        if resource == "config":
            if "swupdate2" in putDict:
                if "checkforupdate" in putDict["swupdate2"] and putDict["swupdate2"]["checkforupdate"] == True:
                    versionCheck()
                    githubCheck()
                if "install" in putDict["swupdate2"] and putDict["swupdate2"]["install"] == True:
                    githubInstall()
            if "users" in putDict:
                for key, value in putDict["users"].items():
                    for email, hash in bridgeConfig["config"]["users"].items():
                        if putDict["users"][key] == bridgeConfig["config"]["users"][email]:
                            bridgeConfig["config"]["users"][email]["password"] = generate_password_hash(str(value['password']))

        # build response list
        responseList = []
        response_location = "/" + resource + "/"
        for key, value in putDict.items():
            responseList.append({"success": {response_location + key: value}})
        logging.debug(responseList)
        configManager.bridgeConfig.save_config(backup=False, resource=resource)
        return responseList


class Element(Resource):

    def get(self, username, resource, resourceid):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation

        if resource == "info" and resourceid == "timezones":
            return capabilities()["timezones"]["values"]

        if resource in ["lights", "sensors"] and resourceid == "new":
            response = bridgeConfig["temp"]["scanResult"]
            logging.debug(response)
            return response
        if resource in ["lights", "groups", "scenes", "rules", "resourcelinks", "schedules", "sensors"]:
            return bridgeConfig[resource][resourceid].getV1Api()
        return bridgeConfig[resource][resourceid]

    def put(self, username, resource, resourceid):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation

        putDict = request.get_json(force=True)
        logging.info(putDict)
        currentTime = datetime.now()
        responseList = []
        response_location = "/" + resource + "/" + resourceid + "/"
        for key, value in putDict.items():
            responseList.append({"success": {response_location + key: value}})
        if "group" in putDict:
            putDict["group"] = weakref.ref(
                bridgeConfig["groups"][putDict["group"]])
        if resource == "scenes" and "lights" in putDict:
            objList = []
            for light in putDict["lights"]:
                objList.append(weakref.ref(bridgeConfig["lights"][light]))
            putDict["lights"] = objList
        if "lightstates" in putDict:
            lightStates = weakref.WeakKeyDictionary()
            for light, state in putDict["lightstates"].items():
                lightStates[bridgeConfig["lights"][light]] = state
            putDict["lightstates"] = lightStates
        if resource == "sensors":
            if "state" in putDict:
                for state in putDict["state"].keys():
                    bridgeConfig["sensors"][resourceid].dxState[state] = currentTime
                bridgeConfig["sensors"][resourceid].state["lastupdated"] = datetime.now(timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                bridgeConfig["sensors"][resourceid].dxState["lastupdated"] = currentTime
        elif resource == "groups":
            if "lights" in putDict:
                bridgeConfig["groups"][resourceid].lights = [] #empty the list
                for light in putDict["lights"]:
                    bridgeConfig["groups"][resourceid].add_light(bridgeConfig["lights"][light])
            if "stream" in putDict:
                if "active" in putDict["stream"]:
                    if putDict["stream"]["active"]:
                        logging.info("start hue entertainment")
                        Thread(target=entertainmentService, args=[
                               bridgeConfig["groups"][resourceid], bridgeConfig["apiUsers"][username]]).start()
                    else:
                        logging.info("stop hue entertainent")
                        Popen(["killall", "openssl"])
            if "action" in putDict:
                bridgeConfig["groups"][resourceid].dxState["any_on"] = currentTime
            # lights where removed from group, delete scenes
            if "lights" in putDict and len(putDict["lights"]) == 0:
                for scene in list(bridgeConfig["scenes"].keys()):
                    if bridgeConfig["scenes"][scene].type == "GroupScene":
                        if bridgeConfig["scenes"][scene].group().id_v1 == resourceid:
                            del bridgeConfig["scenes"][scene]
            if "locations" in putDict:
                for light, location in putDict["locations"].items():
                    bridgeConfig["groups"][resourceid].locations[bridgeConfig["lights"][light]] = [{"x": location[0], "y": location[1], "z": location[2]}]
        bridgeConfig[resource][resourceid].update_attr(putDict)
        rulesProcessor(bridgeConfig[resource][resourceid], currentTime)
        logging.debug(responseList)
        return responseList

    def delete(self, username, resource, resourceid):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation
        if resource == "resourcelinks":
            for link in bridgeConfig["resourcelinks"][resourceid].links:
                try:
                    pices = link.split("/")
                    if hasattr(bridgeConfig[pices[1]][pices[2]], "recycle") and bridgeConfig[pices[1]][pices[2]].recycle:
                        del bridgeConfig[pices[1]][pices[2]]
                except:
                    logging.info("link not found")
            configManager.bridgeConfig.save_config()
        # delete also light and temperature sensor
        if resource == "sensors" and bridgeConfig["sensors"][resourceid].modelid == "SML001":
            for sensor in list(bridgeConfig["sensors"].keys()):
                if bridgeConfig["sensors"][sensor].uniqueid != None and bridgeConfig["sensors"][sensor].uniqueid[:-1] == bridgeConfig["sensors"][resourceid].uniqueid[:-1] and bridgeConfig["sensors"][sensor].id_v1 != resourceid:
                    del bridgeConfig["sensors"][sensor]
        # delete the object
        del bridgeConfig[resource][resourceid]
        # clean scenes
        if resource == "groups":
            for scene in list(bridgeConfig["scenes"].keys()):
                if bridgeConfig["scenes"][scene].type == "GroupScene":
                    if bridgeConfig["scenes"][scene].group().id_v1 == resourceid:
                        del bridgeConfig["scenes"][scene]
        if resource in ["groups", "lights"]:
            GroupZeroMessage() # trigger stream messages
        if resource == "lights":
            configManager.bridgeConfig.save_config(backup=False, resource='groups')
            configManager.bridgeConfig.save_config(backup=False, resource='scenes')
        configManager.bridgeConfig.save_config(backup=False, resource=resource)
        return [{"success": "/" + resource + "/" + resourceid + " deleted."}]


class ElementParam(Resource):
    def get(self, username, resource, resourceid, param):
        authorisation = authorize(username, resource, resourceid, param)
        if "success" not in authorisation:
            return authorisation
        return bridgeConfig[resource][resourceid].getV1Api()[param]

    def put(self, username, resource, resourceid, param):
        authorisation = authorize(username, resource, resourceid, param)
        if "success" not in authorisation:
            return authorisation
        putDict = request.get_json(force=True)
        currentTime = datetime.now()
        logging.info(putDict)
        if resource == "lights" and param == "state":  # state is applied to a light
            bridgeConfig[resource][resourceid].setV1State(putDict)
        elif param == "action":  # state is applied to a light
            if "scene" in putDict:
                bridgeConfig[resource][resourceid].setV1Action(
                    state={}, scene=bridgeConfig["scenes"][putDict["scene"]])
            else:
                bridgeConfig[resource][resourceid].setV1Action(
                    state=putDict, scene=None)
            if "on" in putDict:
                bridgeConfig["groups"][resourceid].dxState["any_on"] = currentTime
                bridgeConfig["groups"][resourceid].dxState["all_on"] = currentTime
                rulesProcessor(bridgeConfig[resource][resourceid], currentTime)
        if resource == "sensors" and param == "state":
            bridgeConfig[resource][resourceid].state.update(putDict)
            for state in putDict.keys():
                bridgeConfig["sensors"][resourceid].dxState[state] = currentTime
            bridgeConfig["sensors"][resourceid].state["lastupdated"] = datetime.now(timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            bridgeConfig["sensors"][resourceid].dxState["lastupdated"] = currentTime
            rulesProcessor(bridgeConfig[resource][resourceid], currentTime)
        bridgeConfig[resource][resourceid].update_attr({param: putDict})
        responseList = []
        responseLocation = "/" + resource + "/" + resourceid + "/" + param + "/"
        for key, value in putDict.items():
            responseList.append(
                {"success": {responseLocation + key: value}})
        logging.debug(responseList)
        return responseList

    def delete(self, username, resource, resourceid, param):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation
        if resourceid == "whitelist":
            for config in ["lights", "groups", "scenes", "rules", "resourcelinks", "schedules", "sensors"]:
                for object in bridgeConfig[config]:
                    if "owner" in bridgeConfig[config][object].getV1Api():
                        current_owner = bridgeConfig[config][object].getV1Api()["owner"]
                        if current_owner == param:
                            logging.debug("transfer ownership from: " + str(current_owner) + " to: " + str(username))
                            bridgeConfig[config][object].owner = bridgeConfig["apiUsers"][username]
            logging.debug("Deleted api user: " + str(param) + " " + bridgeConfig["apiUsers"][param].name)
            del bridgeConfig["apiUsers"][param]
            configManager.bridgeConfig.save_config()
            return [{"success": "/" + resource + "/" + resourceid + "/" + param + " deleted."}]
        if param not in bridgeConfig[resource][resourceid]:
            return [{"error": {"type": 4, "address": "/" + resource + "/" + resourceid, "description": "method, DELETE, not available for resource,  " + resource + "/" + resourceid}}]

        del bridgeConfig[resource][resourceid][param]
        configManager.bridgeConfig.save_config()
        return [{"success": "/" + resource + "/" + resourceid + "/" + param + " deleted."}]

class ElementParamId(Resource):
    def get(self, username, resource, resourceid, param, paramid):
        authorisation = authorize(username, resource, resourceid, param)
        if "success" not in authorisation:
            return authorisation
        return bridgeConfig[resource][resourceid].getV1Api()[param][paramid]

    def put(self, username, resource, resourceid, param, paramid):
        authorisation = authorize(username, resource, resourceid, param)
        if "success" not in authorisation:
            return authorisation
        putDict = request.get_json(force=True)
        currentTime = datetime.now()
        logging.info(putDict)
        responseList = []
        responseLocation = "/" + resource + "/" + \
            resourceid + "/" + param + "/" + paramid + "/"
        for key, value in putDict.items():
            responseList.append(
                {"success": {responseLocation + key: value}})
        if resource == "scenes" and param == "lightstates":
            paramid = bridgeConfig["lights"][paramid]
        bridgeConfig[resource][resourceid].update_attr(
            {param: {paramid: putDict}})
        logging.debug(responseList)
        return responseList
