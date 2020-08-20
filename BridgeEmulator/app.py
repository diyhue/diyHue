from flask import Flask, request
from flask.json import jsonify
from flask_restful import Resource, Api
from flask_login import LoginManager
from threading import Thread
from time import sleep
from datetime import datetime
import ssl
import uuid
import settings
from pprint import pprint
import configManager

bridgeConfig = configManager.bridgeConfig.json_config
dxState = configManager.runtimeConfig.dxState
newLights = configManager.runtimeConfig.newLights

app = Flask(__name__)
api = Api(app)

login_manager = LoginManager()
# We can now pass in our app to the login manager
login_manager.init_app(app)
# Tell users what view to go to when they need to login.
login_manager.login_view = "core.login"



def authorize(username, resource, resourceid):
    if username not in bridgeConfig["config"]["whitelist"] and request.remote_addr != "127.0.0.1":
        return [{"error":{"type":1,"address":"/","description":"unauthorized user"}}]

    if resourceid not in bridgeConfig[resource]:
        return [{"error":{"type":3,"address":"/" + resource + "/" + resourceid,"description":"resource, " + resource + "/" + resourceid + ", not available"}}]

    return ["success"]


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

        postDict = request.get_json(force=True)
        pprint(postDict)

        bridgeConfig[resource][resourceid].update(postDict)
        return [{"success":{"/lights/2/name":"IKEA Color"}}]
        responseLocation = "/" + resource + "/" + resourceid + "/"
        responseList = []
        for key, value in postDict.items():
            responseList.append({"success":{responseLocation + key: value}})
        pprint(responseList)
        return responseList


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
                    del Globals.bridge_config["sensors"][sensor]
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
            sanitizeBridgeScenes()
        del bridgeConfig[resource][resourceid][param]
        return [{"success": "/" + resource + "/" + resourceid + "/" + param + " deleted."}]




class ElementParam(Resource):
    def get(self,username, resource, resourceid, param):
        if username in bridgeConfig["config"]["whitelist"]:
            return bridgeConfig[resource][resourceid][param]
        return [{"error":{"type":1,"address":"/","description":"unauthorized user"}}]

    def put(self, username, resource, resourceid, param):
        postDict = request.get_json(force=True)
        pprint(postDict)

    def delete(self, username, resource, resourceid, param):
        authorisation = authorize(username, resource, resourceid)
        if "success" not in authorisation:
            return authorisation
        if param not in bridgeConfig[resource][resourceid]:
            return [{"error":{"type":4,"address":"/" + resource + "/" + resourceid, "description":"method, DELETE, not available for resource,  " + resource + "/" + resourceid}}]

        del bridgeConfig[resource][resourceid][param]
        return [{"success": "/" + resource + "/" + resourceid + "/" + param + " deleted."}]


api.add_resource(NewUser, '/api/', strict_slashes=False)
api.add_resource(EntireConfig, '/api/<string:username>', strict_slashes=False)
api.add_resource(ResourceElements, '/api/<string:username>/<string:resource>', strict_slashes=False)
api.add_resource(Element, '/api/<string:username>/<string:resource>/<string:resourceid>', strict_slashes=False)
api.add_resource(ElementParam, '/api/<string:username>/<string:resource>/<string:resourceid>/<string:param>/', strict_slashes=False)

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
    app.run(host="0.0.0.0", port=80, debug=True)

if __name__ == '__main__':
    #Thread(target=runHttps).start()
    #sleep(0.5)
    runHttp()
