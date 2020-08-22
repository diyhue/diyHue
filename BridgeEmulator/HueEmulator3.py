#!/usr/bin/python3
from flask import Flask, request
from flask.json import jsonify
from flask_restful import Resource, Api
from threading import Thread
from time import sleep
from datetime import datetime
import ssl
import uuid
import settings
from pprint import pprint
import configManager
import flask_login
from functions.ssdp import ssdpBroadcast, ssdpSearch
from functions.updateGroup import updateGroupStats
from functions.lightRequest import sendLightRequest
from functions import nextFreeId
from functions.core import generateDxState, splitLightsToDevices, groupZero
from protocols import protocols, yeelight, tasmota, shelly, native_single, native_multi, esphome, mqtt
from core import User

bridgeConfig = configManager.bridgeConfig.json_config
dxState = configManager.runtimeConfig.dxState
newLights = configManager.runtimeConfig.newLights

app = Flask(__name__)
api = Api(app)

app.config['SECRET_KEY'] = 'change_this_to_be_secure'

login_manager = flask_login.LoginManager()
# We can now pass in our app to the login manager
login_manager.init_app(app)
# Tell users what view to go to when they need to login.
login_manager.login_view = "core.login"


@login_manager.user_loader
def user_loader(email):
    if email not in bridgeConfig["emulator"]["users"]:
        return

    user = User()
    user.id = email
    return user


@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')
    if email not in bridgeConfig["emulator"]["users"]:
        return

    user = User()
    user.id = email

    # DO NOT ever store passwords in plaintext and always compare password
    # hashes using constant-time comparison!
    print(email)
    user.is_authenticated = request.form['password'] == bridgeConfig["emulator"]["users"][email]["password"]

    return user


def authorize(username, resource, resourceid):
    if username not in bridgeConfig["config"]["whitelist"] and request.remote_addr != "127.0.0.1":
        return [{"error":{"type":1,"address":"/","description":"unauthorized user"}}]

    if resourceid not in bridgeConfig[resource]:
        return [{"error":{"type":3,"address":"/" + resource + "/" + resourceid,"description":"resource, " + resource + "/" + resourceid + ", not available"}}]

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
        if username in bridgeConfig["config"]["whitelist"]:
            return  bridgeConfig
        return [{"error":{"type":1,"address":"/","description":"unauthorized user"}}]

class ResourceElements(Resource):
    def get(self,username, resource):
        if username in bridgeConfig["config"]["whitelist"]:
            return  bridgeConfig[resource]
        elif resource == "config":
            config = bridgeConfig["config"]
            return {"name":config["name"],"datastoreversion":"94","swversion":config["swversion"],"apiversion":config["apiversion"],"mac":config["mac"],"bridgeid":config["bridgeid"],"factorynew":False,"replacesbridgeid":None,"modelid":config["modelid"],"starterkitid":""}
        return [{"error":{"type":1,"address":"/","description":"unauthorized user"}}]

    def post(self, username, resource):
        if username not in bridgeConfig["config"]["whitelist"] and request.remote_addr != "127.0.0.1":
            return [{"error":{"type":1,"address":"/","description":"unauthorized user"}}]
        postDict = request.get_json(force=True)
        pprint(postDict)
        configManager.bridgeConfig.save_config()

class Element(Resource):

    def get(self, username, resource, resourceid):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation
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
                    Popen(["/opt/hue-emulator/entertain-srv", "server_port=2100", "dtls=1", "psk_list=" + url_pices[2] + ",321c0c2ebfa7361e55491095b2f5f9db"])
                    sleep(0.2)
                    bridgeConfig["groups"][resourceid]["stream"].update({"active": True, "owner": url_pices[2], "proxymode": "auto", "proxynode": "/bridge"})
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
                    sendRequest("http://" + bridgeConfig["emulator"]["lights"][resourceid]["ip"] + "/", "POST", {"startup": 1})
                elif putDict["config"]["startup"]["mode"] == "powerfail":
                    sendRequest("http://" + bridgeConfig["emulator"]["lights"][resourceid]["ip"] + "/", "POST", {"startup": 0})

                #add exception on json output as this dictionary has tree levels
                response_dictionary = {"success":{"/lights/" + resourceid + "/config/startup": {"mode": putDict["config"]["startup"]["mode"]}}}
                self._set_end_headers(bytes(json.dumps(response_dictionary,separators=(',', ':'),ensure_ascii=False), "utf8"))
                logging.info(json.dumps(response_dictionary, sort_keys=True, indent=4, separators=(',', ': ')))
                return
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
        elif resource == "groups":
            configManager.bridgeConfig.sanitizeBridgeScenes()
        del bridgeConfig[resource][resourceid][param]
        return [{"success": "/" + resource + "/" + resourceid + "/" + param + " deleted."}]


class ElementParam(Resource):
    def get(self,username, resource, resourceid, param):
        if username in bridgeConfig["config"]["whitelist"]:
            return bridgeConfig[resource][resourceid][param]
        return [{"error":{"type":1,"address":"/","description":"unauthorized user"}}]

    def put(self, username, resource, resourceid, param):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation
        if param not in bridgeConfig[resource][resourceid]:
            return [{"error":{"type":3,"address":"/" + resource + "/" + resourceid + "/" + param, "description":"/" + resource + "/" + resourceid + "/" + param + " , not available" }}]
        putDict = request.get_json(force=True)
        currentTime = datetime.now()
        pprint(putDict)
        if resource == "groups": #state is applied to a group
            if param == "stream":
                if "active" in putDict:
                    if putDict["active"]:
                        logging.info("start hue entertainment")
                        Popen(["/opt/hue-emulator/entertain-srv", "server_port=2100", "dtls=1", "psk_list=" + url_pices[2] + ",321c0c2ebfa7361e55491095b2f5f9db"])
                        sleep(0.2)
                        bridgeConfig["groups"][resourceid]["stream"].update({"active": True, "owner": url_pices[2], "proxymode": "auto", "proxynode": "/bridge"})
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
        response_location = "/" + resource + "/" + resourceid + "/" + param + "/"


    def delete(self, username, resource, resourceid, param):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation
        if param not in bridgeConfig[resource][resourceid]:
            return [{"error":{"type":4,"address":"/" + resource + "/" + resourceid, "description":"method, DELETE, not available for resource,  " + resource + "/" + resourceid}}]

        del bridgeConfig[resource][resourceid][param]
        return [{"success": "/" + resource + "/" + resourceid + "/" + param + " deleted."}]

### HUE API
api.add_resource(NewUser, '/api/', strict_slashes=False)
api.add_resource(EntireConfig, '/api/<string:username>', strict_slashes=False)
api.add_resource(ResourceElements, '/api/<string:username>/<string:resource>', strict_slashes=False)
api.add_resource(Element, '/api/<string:username>/<string:resource>/<string:resourceid>', strict_slashes=False)
api.add_resource(ElementParam, '/api/<string:username>/<string:resource>/<string:resourceid>/<string:param>/', strict_slashes=False)

### WEB INTERFACE
from core.views import core
from error_pages.handlers import error_pages
app.register_blueprint(core)
app.register_blueprint(error_pages)


def runHttps():
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(certfile="cert.pem")
    ctx.options |= ssl.OP_NO_TLSv1
    ctx.options |= ssl.OP_NO_TLSv1_1
    ctx.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
    ctx.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256')
    ctx.set_ecdh_curve('prime256v1')
    app.run(host="0.0.0.0", port=443, ssl_context=ctx)

def runHttp():
    app.run(host="0.0.0.0", port=80)

if __name__ == '__main__':
    ### variables initialization
    generateDxState()
    BIND_IP = configManager.runtimeConfig.arg["BIND_IP"]
    HOST_IP = configManager.runtimeConfig.arg["HOST_IP"]
    mac = configManager.runtimeConfig.arg["MAC"]
    HOST_HTTP_PORT = configManager.runtimeConfig.arg["HTTP_PORT"]
    ### config initialization
    configManager.bridgeConfig.updateConfig()
    configManager.bridgeConfig.save_config()
    ### start services
    if bridgeConfig["emulator"]["deconz"]["enabled"]:
        Thread(target=deconz.scanDeconz).start()
    if bridgeConfig["emulator"]["mqtt"]["enabled"]:
        Thread(target=mqtt.mqttServer).start()
    Thread(target=ssdpSearch, args=[HOST_IP, HOST_HTTP_PORT, mac]).start()
    Thread(target=ssdpBroadcast, args=[HOST_IP, HOST_HTTP_PORT, mac]).start()
    Thread(target=resourceRecycle).start()
    Thread(target=runHttps).start()
    sleep(0.5)
    runHttp()
