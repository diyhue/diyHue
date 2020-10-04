import configManager
import logManager
import uuid
import json
import requests
from threading import Thread
from time import sleep
from datetime import datetime
from lights.manage import updateGroupStats, splitLightsToDevices, groupZero, sendLightRequest
from lights.discover import scanForLights
from functions.core import generateDxState, nextFreeId, capabilities
from flask_restful import Resource
from flask import request
from pprint import pprint

logging = logManager.logger.get_logger(__name__)


bridgeConfig = configManager.bridgeConfig.json_config
dxState = configManager.runtimeConfig.dxState
newLights = configManager.runtimeConfig.newLights


def authorize(username, resource=None, resourceId=None, resourceParam=None):
    if username not in bridgeConfig["config"]["whitelist"] and request.remote_addr != "127.0.0.1":
        return [{"error":{"type":1,"address":"/","description":"unauthorized user"}}]

    if resourceId not in ["0", "new"] and resourceId != None and resourceId not in bridgeConfig[resource]:
        return [{"error":{"type":3,"address":"/" + resource + "/" + resourceId,"description":"resource, " + resource + "/" + resourceId + ", not available"}}]

    if resourceId != "0" and resourceParam != None and resourceParam not in bridgeConfig[resource][resourceId]:
        return [{"error":{"type":3,"address":"/" + resource + "/" + resourceId + "/" + resourceParam,"description":"resource, " + resource + "/" + resourceId + "/" + resourceParam + ", not available"}}]

    return ["success"]

def resourceRecycle():
    sleep(5) #give time to application to delete all resources, then start the cleanup
    resourcelinks = {"groups": [],"lights": [], "sensors": [], "rules": [], "scenes": [], "schedules": [], "resourcelinks": []}
    for resourcelink in bridgeConfig["resourcelinks"].keys():
        for link in bridgeConfig["resourcelinks"][resourcelink]["links"]:
            link_parts = link.split("/")
            resourcelinks[link_parts[1]].append(link_parts[2])

    for resource in resourcelinks.keys():
        for key in list(bridgeConfig[resource]):
            if "recycle" in bridgeConfig[resource][key] and bridgeConfig[resource][key]["recycle"] and key not in resourcelinks[resource]:
                logging.info("delete " + resource + " / " + key)
                del bridgeConfig[resource][key]


class NewUser(Resource):
    def get(self):
        return [{"error":{"type":4,"address":"/","description":"method, GET, not available for resource, /"}}]

    def post(self):
        postDict = request.get_json(force=True)
        pprint(postDict)
        if "devicetype" in postDict:
            last_button_press = bridgeConfig["emulator"]["linkbutton"]["lastlinkbuttonpushed"]
            if last_button_press+30 >= datetime.now().timestamp() or bridgeConfig["config"]["linkbutton"]:
                username = str(uuid.uuid1()).replace('-', '')
                if postDict["devicetype"].startswith("Hue Essentials"):
                    username = "hueess" + username[-26:]
                bridgeConfig["config"]["whitelist"][username] = {"last use date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"create date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"name": postDict["devicetype"]}
                response = [{"success": {"username": username}}]
                if "generateclientkey" in postDict and postDict["generateclientkey"]:
                    response[0]["success"]["clientkey"] = "321c0c2ebfa7361e55491095b2f5f9db"
                pprint(response)
                configManager.bridgeConfig.save_config()
                return response
            else:
                return [{"error":{"type":101,"address":"","description":"link button not pressed"}}]
        else:
            return [{"error":{"type":6,"address":"/" + list(postDict.keys())[0],"description":"parameter, " + list(postDict.keys())[0] + ", not available"}}]

class EntireConfig(Resource):
    def get(self,username):
        authorisation = authorize(username)
        if "success" not in authorisation:
            return authorisation
        return  bridgeConfig

class ResourceElements(Resource):
    def get(self,username, resource):
        if username in bridgeConfig["config"]["whitelist"]:
            if resource == "capabilities":
                return capabilities()
            else:
                return  bridgeConfig[resource]
        elif resource == "config":
            config = bridgeConfig["config"]
            return {"name":config["name"],"datastoreversion":"94","swversion":config["swversion"],"apiversion":config["apiversion"],"mac":config["mac"],"bridgeid":config["bridgeid"],"factorynew":False,"replacesbridgeid":None,"modelid":config["modelid"],"starterkitid":""}
        return [{"error":{"type":1,"address":"/","description":"unauthorized user"}}]

    def post(self, username, resource):
        authorisation = authorize(username, resource)
        if "success" not in authorisation:
            return authorisation
        if (resource == "lights" or resource == "sensors") and request.get_data(as_text=True) == "":
            print("scan for light")
            #if was a request to scan for lights of sensors
            Thread(target=scanForLights).start()
            sleep(7) #give no more than 5 seconds for light scanning (otherwise will face app disconnection timeout)
            return [{"success": {"/" + resource: "Searching for new devices"}}]
        postDict = request.get_json(force=True)
        pprint(postDict)
        # find the first unused id for new object
        new_object_id = nextFreeId(bridgeConfig, resource)
        if resource == "scenes": # store scene
            postDict.update({"version": 2, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "owner" :username})
            if "locked" not in postDict:
                postDict["locked"] = False
            if "picture" not in postDict:
                postDict["picture"] = ""
            if "type" not in postDict:
                postDict["type"] = "LightScene"
            if "lightstates" not in postDict or len(postDict["lightstates"]) == 0:
                postDict["lightstates"] = {}
                if "lights" in postDict:
                    lights = postDict["lights"]
                elif "group" in postDict:
                    lights = bridgeConfig["groups"][postDict["group"]]["lights"]
                for light in lights:
                    postDict["lightstates"][light] = {"on": bridgeConfig["lights"][light]["state"]["on"]}
                    if "bri" in bridgeConfig["lights"][light]["state"]:
                        postDict["lightstates"][light]["bri"] = bridgeConfig["lights"][light]["state"]["bri"]
                    if "colormode" in bridgeConfig["lights"][light]["state"]:
                        if bridgeConfig["lights"][light]["state"]["colormode"] in ["ct", "xy"] and bridgeConfig["lights"][light]["state"]["colormode"] in bridgeConfig["lights"][light]["state"]:
                            postDict["lightstates"][light][bridgeConfig["lights"][light]["state"]["colormode"]] = bridgeConfig["lights"][light]["state"][bridgeConfig["lights"][light]["state"]["colormode"]]
                        elif bridgeConfig["lights"][light]["state"]["colormode"] == "hs":
                            postDict["lightstates"][light]["hue"] = bridgeConfig["lights"][light]["state"]["hue"]
                            postDict["lightstates"][light]["sat"] = bridgeConfig["lights"][light]["state"]["sat"]

        elif resource == "groups":
            if "type" not in postDict:
                postDict["type"] = "LightGroup"
            if postDict["type"] in ["Room", "Zone"] and "class" not in postDict:
                postDict["class"] = "Other"
            elif postDict["type"] == "Entertainment" and "stream" not in postDict:
                postDict["stream"] = {"active": False, "owner": username, "proxymode": "auto", "proxynode": "/bridge"}
            postDict.update({"action": {"on": False}, "state": {"any_on": False, "all_on": False}})
        elif resource == "schedules":
            try:
                postDict.update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "time": postDict["localtime"]})
            except KeyError:
                postDict.update({"created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "localtime": postDict["time"]})
            if postDict["localtime"].startswith("PT") or postDict["localtime"].startswith("R/PT"):
                postDict.update({"starttime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")})
            if not "status" in postDict:
                postDict.update({"status": "enabled"})
        elif resource == "rules":
            postDict.update({"owner": username, "lasttriggered" : "none", "created": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), "timestriggered": 0})
            if not "status" in postDict:
                postDict.update({"status": "enabled"})
        elif resource == "sensors":
            if "state" not in postDict:
                postDict["state"] = {}
            if "lastupdated" not in postDict["state"]:
                postDict["state"]["lastupdated"] = "none"
            if postDict["modelid"] == "PHWA01":
                postDict["state"]["status"] = 0
            elif postDict["modelid"] == "PHA_CTRL_START":
                postDict.update({"state": {"flag": False, "lastupdated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}, "config": {"on": True,"reachable": True}})
        elif resource == "resourcelinks":
            postDict.update({"owner" :username})
        generateDxState()
        bridgeConfig[resource][new_object_id] = postDict
        logging.info(json.dumps([{"success": {"id": new_object_id}}], sort_keys=True, indent=4, separators=(',', ': ')))
        configManager.bridgeConfig.save_config()
        return [{"success": {"id": new_object_id}}]


class Element(Resource):

    def get(self, username, resource, resourceid):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation

        if resource in ["lights", "sensors"] and resourceid == "new":
            response = newLights.copy()
            newLights.clear()
            return response
        return bridgeConfig[resource][resourceid]


    def put(self, username, resource, resourceid):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation

        putDict = request.get_json(force=True)
        pprint(putDict)

        if resource == "schedules":
            if "status" in putDict and putDict["status"] == "enabled" and (bridgeConfig["schedules"][resourceid]["localtime"].startswith("PT") or bridgeConfig["schedules"][resourceid]["localtime"].startswith("R/PT")):
                bridgeConfig["schedules"][resourceid]["starttime"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
            bridgeConfig[resource][resourceid].update(putDict)
        elif resource == "scenes":
            if "storelightstate" in putDict:
                if "lights" in bridgeConfig["scenes"][resourceid]:
                    lights = bridgeConfig["scenes"][resourceid]["lights"]
                elif "group" in bridgeConfig["scenes"][resourceid]:
                    lights = bridgeConfig["groups"][bridgeConfig["scenes"][resourceid]["group"]]["lights"]
                for light in lights:
                    bridgeConfig["scenes"][resourceid]["lightstates"][light] = {}
                    bridgeConfig["scenes"][resourceid]["lightstates"][light]["on"] = bridgeConfig["lights"][light]["state"]["on"]
                    if "bri" in bridgeConfig["lights"][light]["state"]:
                        bridgeConfig["scenes"][resourceid]["lightstates"][light]["bri"] = bridgeConfig["lights"][light]["state"]["bri"]
                    if "colormode" in bridgeConfig["lights"][light]["state"]:
                        if bridgeConfig["lights"][light]["state"]["colormode"] in ["ct", "xy"]:
                            bridgeConfig["scenes"][resourceid]["lightstates"][light][bridgeConfig["lights"][light]["state"]["colormode"]] = bridgeConfig["lights"][light]["state"][bridgeConfig["lights"][light]["state"]["colormode"]]
                        elif bridgeConfig["lights"][light]["state"]["colormode"] == "hs" and "hue" in bridgeConfig["scenes"][resourceid]["lightstates"][light]:
                            bridgeConfig["scenes"][resourceid]["lightstates"][light]["hue"] = bridgeConfig["lights"][light]["state"]["hue"]
                            bridgeConfig["scenes"][resourceid]["lightstates"][light]["sat"] = bridgeConfig["lights"][light]["state"]["sat"]
        elif resource == "sensors":
            currentTime = datetime.now()
            for key, value in putDict.items():
                if key not in dxState["sensors"][resourceid]:
                    dxState["sensors"][resourceid][key] = {}
                if type(value) is dict:
                    bridgeConfig["sensors"][resourceid][key].update(value)
                    for element in value.keys():
                        dxState["sensors"][resourceid][key][element] = currentTime
                else:
                    bridgeConfig["sensors"][resourceid][key] = value
                    dxState["sensors"][resourceid][key] = currentTime
            dxState["sensors"][resourceid]["state"]["lastupdated"] = currentTime
            bridgeConfig["sensors"][resourceid]["state"]["lastupdated"] = currentTime.strftime("%Y-%m-%dT%H:%M:%S")
            if resourceid == "1" and bridgeConfig[resource][resourceid]["modelid"] == "PHDL00":
                bridgeConfig["sensors"]["1"]["config"]["configured"] = True ##mark daylight sensor as configured
        elif resource == "groups" and "stream" in putDict:
            if "active" in putDict["stream"]:
                if putDict["stream"]["active"]:
                    for light in bridgeConfig["groups"][resourceid]["lights"]:
                        bridgeConfig["lights"][light]["state"]["mode"] = "streaming"
                    logging.info("start hue entertainment")
                    Popen(["/opt/hue-emulator/entertain-srv", "server_port=2100", "dtls=1", "psk_list=" + username + ",321c0c2ebfa7361e55491095b2f5f9db"])
                    sleep(0.2)
                    bridgeConfig["groups"][resourceid]["stream"].update({"active": True, "owner": username, "proxymode": "auto", "proxynode": "/bridge"})
                else:
                    for light in bridgeConfig["groups"][resourceid]["lights"]:
                        bridgeConfig["lights"][light]["state"]["mode"] = "homeautomation"
                    logging.info("stop hue entertainent")
                    Popen(["killall", "entertain-srv"])
                    bridgeConfig["groups"][resourceid]["stream"].update({"active": False, "owner": None})
            else:
                bridgeConfig[resource][resourceid].update(putDict)
        elif resource == "lights" and "config" in putDict:
            bridgeConfig["lights"][resourceid]["config"].update(putDict["config"])
            if "startup" in putDict["config"] and bridgeConfig["emulator"]["lights"][resourceid]["protocol"] == "native":
                if putDict["config"]["startup"]["mode"] == "safety":
                    requests.post("http://" + bridgeConfig["emulator"]["lights"][resourceid]["ip"] + "/", json={"startup": 1})
                elif putDict["config"]["startup"]["mode"] == "powerfail":
                    requests.post("http://" + bridgeConfig["emulator"]["lights"][resourceid]["ip"] + "/", json={"startup": 0})

                #add exception on json output as this dictionary has tree levels
                response_dictionary = {"success":{"/lights/" + resourceid + "/config/startup": {"mode": putDict["config"]["startup"]["mode"]}}}
                logging.info(json.dumps(response_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))
                return response_dictionary
        else:
            bridgeConfig[resource][resourceid].update(putDict)
            if resource == "groups" and "lights" in putDict: #need to update scene lightstates
                for scene in bridgeConfig["scenes"]: # iterate over scenes
                    for light in putDict["lights"]: # check each scene to make sure it has a lightstate for each new light
                        if "lightstates" in bridgeConfig["scenes"][scene] and light not in bridgeConfig["scenes"][scene]["lightstates"]: # copy first light state to new light
                            if ("lights" in bridgeConfig["scenes"][scene] and light in bridgeConfig["scenes"][scene]["lights"]) or \
                            (bridgeConfig["scenes"][scene]["type"] == "GroupScene" and light in bridgeConfig["groups"][bridgeConfig["scenes"][scene]["group"]]["lights"]):
                                # Either light is in the scene or part of the group now, add lightscene based on previous scenes
                                new_state = next(iter(bridgeConfig["scenes"][scene]["lightstates"]))
                                new_state = bridgeConfig["scenes"][scene]["lightstates"][new_state]
                                bridgeConfig["scenes"][scene]["lightstates"][light] = new_state
            responseDictionary = []
            response_location = "/" + resource + "/" + resourceid + "/"
            for key, value in putDict.items():
                    responseDictionary.append({"success":{response_location + key: value}})
            return responseDictionary



    def delete(self, username, resource, resourceid):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation
        if resource == "resourcelinks":
            Thread(target=resourceRecycle).start()
        elif resource == "sensors":
            ## delete also related sensors
            for sensor in list(bridgeConfig["sensors"]):
                if sensor != resourceid and "uniqueid" in bridgeConfig["sensors"][sensor] and bridgeConfig["sensors"][sensor]["uniqueid"].startswith(bridgeConfig["sensors"][resourceid]["uniqueid"][:26]):
                    del bridgeConfig["sensors"][sensor]
                    logging.info('Delete related sensor ' + sensor)
            ### remove the sensor from emulator key
            for sensor in list(bridgeConfig["emulator"]["sensors"]):
                if bridgeConfig["emulator"]["sensors"][sensor]["bridgeId"] == resourceid:
                    del bridgeConfig["emulator"]["sensors"][sensor]
        elif resource == "lights":
            # Remove this light from every group
            for group_id, group in bridgeConfig["groups"].items():
                if "lights" in group and resourceid in group["lights"]:
                    group["lights"].remove(resourceid)
            del bridgeConfig["emulator"]["lights"][resourceid]
        elif resource == "groups":
            configManager.bridgeConfig.sanitizeBridgeScenes()
        del bridgeConfig[resource][resourceid]
        return [{"success": "/" + resource + "/" + resourceid + " deleted."}]
        configManager.bridgeConfig.save_config()


class ElementParam(Resource):
    def get(self,username, resource, resourceid, param):
        authorisation = authorize(username, resource, resourceid, param)
        if "success" not in authorisation:
            return authorisation
        return bridgeConfig[resource][resourceid][param]

    def put(self, username, resource, resourceid, param):
        authorisation = authorize(username, resource, resourceid, param)
        if "success" not in authorisation:
            return authorisation
        putDict = request.get_json(force=True)
        currentTime = datetime.now()
        pprint(putDict)
        if resource == "groups": #state is applied to a group
            if param == "stream":
                if "active" in putDict:
                    if putDict["active"]:
                        logging.info("start hue entertainment")
                        Popen(["/opt/hue-emulator/entertain-srv", "server_port=2100", "dtls=1", "psk_list=" + username + ",321c0c2ebfa7361e55491095b2f5f9db"])
                        sleep(0.2)
                        bridgeConfig["groups"][resourceid]["stream"].update({"active": True, "owner": username, "proxymode": "auto", "proxynode": "/bridge"})
                    else:
                        Popen(["killall", "entertain-srv"])
                        bridgeConfig["groups"][resourceid]["stream"].update({"active": False, "owner": None})
            elif "scene" in putDict: #scene applied to group
                if bridgeConfig["scenes"][putDict["scene"]]["type"] == "GroupScene":
                    splitLightsToDevices(bridgeConfig["scenes"][putDict["scene"]]["group"], {}, bridgeConfig["scenes"][putDict["scene"]]["lightstates"])
                else:
                    splitLightsToDevices(resourceid, {}, bridgeConfig["scenes"][putDict["scene"]]["lightstates"])
            elif "bri_inc" in putDict or "ct_inc" in putDict or "hue_inc" in putDict:
                splitLightsToDevices(resourceid, putDict)
            elif "scene_inc" in putDict:
                switchScene(resourceid, putDict["scene_inc"])
            elif resourceid == "0": #if group is 0 the scene applied to all lights
                groupZero(putDict)
            else: # the state is applied to particular group (resourceid)
                if "on" in putDict:
                    bridgeConfig["groups"][resourceid]["state"]["any_on"] = putDict["on"]
                    bridgeConfig["groups"][resourceid]["state"]["all_on"] = putDict["on"]
                    dxState["groups"][resourceid]["state"]["any_on"] = currentTime
                    dxState["groups"][resourceid]["state"]["all_on"] = currentTime
                bridgeConfig["groups"][resourceid][param].update(putDict)
                splitLightsToDevices(resourceid, putDict)
        elif resource == "lights": #state is applied to a light
            for key in putDict.keys():
                if key in ["ct", "xy"]: #colormode must be set by bridge
                    bridgeConfig["lights"][resourceid]["state"]["colormode"] = key
                elif key in ["hue", "sat"]:
                    bridgeConfig["lights"][resourceid]["state"]["colormode"] = "hs"

            updateGroupStats(resourceid, bridgeConfig["lights"], bridgeConfig["groups"])
            sendLightRequest(resourceid, putDict, bridgeConfig["lights"], bridgeConfig["emulator"]["lights"])
        elif resource == "sensors":
            if param == "state":
                for key in putDict.keys():
                    # track time of state changes in dxState
                    if not key in bridgeConfig["sensors"][resourceid]["state"] or bridgeConfig["sensors"][resourceid]["state"][key] != putDict[key]:
                        dxState["sensors"][resourceid]["state"][key] = currentTime
            elif resourceid == "1":
                bridgeConfig["sensors"]["1"]["config"]["configured"] = True ##mark daylight sensor as configured
            dxState["sensors"][resourceid]["state"]["lastupdated"] = currentTime
            bridgeConfig["sensors"][resourceid]["state"]["lastupdated"] = currentTime.strftime("%Y-%m-%dT%H:%M:%S")
        if  resourceid != "0" and "scene" not in putDict: #group 0 is virtual, must not be saved in bridge configuration, also the recall scene
            try:
                bridgeConfig[resource][resourceid][param].update(putDict)
            except KeyError:
                bridgeConfig[resource][resourceid][param] = putDict
        responseDictionary = []
        responseLocation = "/" + resource + "/" + resourceid + "/" + param + "/"
        for key, value in putDict.items():
                responseDictionary.append({"success":{responseLocation + key: value}})
        return responseDictionary


    def delete(self, username, resource, resourceid, param):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation
        if param not in bridgeConfig[resource][resourceid]:
            return [{"error":{"type":4,"address":"/" + resource + "/" + resourceid, "description":"method, DELETE, not available for resource,  " + resource + "/" + resourceid}}]

        del bridgeConfig[resource][resourceid][param]
        return [{"success": "/" + resource + "/" + resourceid + "/" + param + " deleted."}]
        configManager.bridgeConfig.save_config()
