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

settings.init()

app = Flask(__name__)
api = Api(app)

login_manager = LoginManager()
# We can now pass in our app to the login manager
login_manager.init_app(app)
# Tell users what view to go to when they need to login.
login_manager.login_view = "core.login"


class NewUser(Resource):
    def get(self):
        return [{"error":{"type":4,"address":"/","description":"method, GET, not available for resource, /"}}]

    def post(self):
        postDict = request.get_json(force=True)
        if "devicetype" in postDict:
            last_button_press = settings.bridgeConfig["emulator"]["linkbutton"]["lastlinkbuttonpushed"]
            if last_button_press+30 >= datetime.now().timestamp() or settings.bridgeConfig["config"]["linkbutton"]:
                username = str(uuid.uuid1()).replace('-', '')
                if postDict["devicetype"].startswith("Hue Essentials"):
                    username = "hueess" + username[-26:]
                settings.bridgeConfig["config"]["whitelist"][username] = {"last use date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"create date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),"name": postDict["devicetype"]}
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
        if username in settings.bridgeConfig["config"]["whitelist"]:
            return  settings.bridgeConfig
        return [{"error":{"type":1,"address":"/","description":"unauthorized user"}}]

class ResourceElements(Resource):
    def get(self,username, resource):
        if username in settings.bridgeConfig["config"]["whitelist"]:
            return  settings.bridgeConfig[resource]
        elif resource == "config":
            config = settings.bridgeConfig["config"]
            return {"name":config["name"],"datastoreversion":"94","swversion":config["swversion"],"apiversion":config["apiversion"],"mac":config["mac"],"bridgeid":config["bridgeid"],"factorynew":False,"replacesbridgeid":None,"modelid":config["modelid"],"starterkitid":""}
        return [{"error":{"type":1,"address":"/","description":"unauthorized user"}}]

    def post(self, name):
        return light

    def delete(self,name):
        return light

class HueElement(Resource):
    def get(self,username, resource, resourceid):
        if username in settings.bridgeConfig["config"]["whitelist"]:
            if resourceid in settings.bridgeConfig[resource]:
                return settings.bridgeConfig[resource][resourceid]
            else:
                return [{"error":{"type":3,"address":"/" + resource + "/" + resourceid,"description":"resource, " + resource + "/" + resourceid + ", not available"}}]
        return [{"error":{"type":1,"address":"/","description":"unauthorized user"}}]

        # If you request a puppy not yet in the puppies list
        return {'name':None},404

    def post(self, name):
        return light

    def delete(self,name):
        return light

class HueElementParam(Resource):
    def get(self,username, resource, resourceid, param):
        if username in settings.bridgeConfig["config"]["whitelist"]:
            return settings.bridgeConfig[resource][resourceid][param]
        return [{"error":{"type":1,"address":"/","description":"unauthorized user"}}]


api.add_resource(NewUser, '/api/', strict_slashes=False)
api.add_resource(EntireConfig, '/api/<string:username>', strict_slashes=False)
api.add_resource(ResourceElements, '/api/<string:username>/<string:resource>', strict_slashes=False)
api.add_resource(HueElement, '/api/<string:username>/<string:resource>/<string:resourceid>', strict_slashes=False)
api.add_resource(HueElementParam, '/api/<string:username>/<string:resource>/<string:resourceid>/<string:param>/', strict_slashes=False)

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
    Thread(target=runHttps).start()
    sleep(0.5)
    runHttp()
