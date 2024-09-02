#!/usr/bin/env python
from flask import Flask
from flask_cors import CORS
from flask_restful import Api
from threading import Thread
import ssl
import configManager
import logManager
import flask_login
from flaskUI.core import User #dummy import for flaks_login module
from flaskUI.restful import NewUser, ShortConfig, EntireConfig, ResourceElements, Element, ElementParam, ElementParamId
from flaskUI.v2restapi import AuthV1, ClipV2, ClipV2Resource, ClipV2ResourceId
from flaskUI.espDevices import Switch
from flaskUI.Credits import Credits
from werkzeug.serving import WSGIRequestHandler
from functions.daylightSensor import daylightSensor

bridgeConfig = configManager.bridgeConfig.yaml_config
logging = logManager.logger.get_logger(__name__)
_ = logManager.logger.get_logger("werkzeug")
WSGIRequestHandler.protocol_version = "HTTP/1.1"
app = Flask(__name__, template_folder='flaskUI/templates',static_url_path="/static", static_folder='flaskUI/static')
api = Api(app)
cors = CORS(app, resources={r"*": {"origins": "*"}})

app.config['SECRET_KEY'] = 'change_this_to_be_secure'
api.app.config['RESTFUL_JSON'] = {'ensure_ascii': False}

login_manager = flask_login.LoginManager()
# We can now pass in our app to the login manager
login_manager.init_app(app)
# Tell users what view to go to when they need to login.
login_manager.login_view = "core.login"

@login_manager.user_loader
def user_loader(email):
    if email not in bridgeConfig["config"]["users"]:
        return

    user = User()
    user.id = email
    return user

@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')
    if email not in bridgeConfig["config"]["users"]:
        return

    user = User()
    user.id = email

    # DO NOT ever store passwords in plaintext and always compare password
    # hashes using constant-time comparison!
    print(email)
    user.is_authenticated = request.form['password'] == bridgeConfig["config"]["users"][email]["password"]

    return user

### Licence/credits
api.add_resource(Credits, '/licenses/<string:resource>', strict_slashes=False)
### ESP devices
api.add_resource(Switch, '/switch')
### HUE API
api.add_resource(NewUser, '/api/', strict_slashes=False)
api.add_resource(ShortConfig, '/api/config', strict_slashes=False)
api.add_resource(EntireConfig, '/api/<string:username>', strict_slashes=False)
api.add_resource(ResourceElements, '/api/<string:username>/<string:resource>', strict_slashes=False)
api.add_resource(Element, '/api/<string:username>/<string:resource>/<string:resourceid>', strict_slashes=False)
api.add_resource(ElementParam, '/api/<string:username>/<string:resource>/<string:resourceid>/<string:param>/', strict_slashes=False)
api.add_resource(ElementParamId, '/api/<string:username>/<string:resource>/<string:resourceid>/<string:param>/<string:paramid>/', strict_slashes=False)

### V2 API
api.add_resource(AuthV1, '/auth/v1', strict_slashes=False)
#api.add_resource(EventStream, '/eventstream/clip/v2', strict_slashes=False)
api.add_resource(ClipV2, '/clip/v2/resource', strict_slashes=False)
api.add_resource(ClipV2Resource, '/clip/v2/resource/<string:resource>', strict_slashes=False)
api.add_resource(ClipV2ResourceId, '/clip/v2/resource/<string:resource>/<string:resourceid>', strict_slashes=False)

### WEB INTERFACE
from flaskUI.core.views import core
from flaskUI.devices.views import devices
from flaskUI.error_pages.handlers import error_pages
from services.eventStreamer import stream

app.register_blueprint(core)
app.register_blueprint(devices)
app.register_blueprint(error_pages)
app.register_blueprint(stream)

def runHttps(BIND_IP, HOST_HTTPS_PORT, CONFIG_PATH):
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(certfile=CONFIG_PATH + "/cert.pem")
    ctx.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
    ctx.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256')
    ctx.set_ecdh_curve('prime256v1')
    app.run(host=BIND_IP, port=HOST_HTTPS_PORT, ssl_context=ctx)

def runHttp(BIND_IP, HOST_HTTP_PORT):
    app.run(host=BIND_IP, port=HOST_HTTP_PORT)

if __name__ == '__main__':
    from services import mqtt, deconz, ssdp, mdns, scheduler, remoteApi, remoteDiscover, entertainment, stateFetch, eventStreamer, homeAssistantWS, updateManager
    ### variables initialization
    BIND_IP = configManager.runtimeConfig.arg["BIND_IP"]
    HOST_IP = configManager.runtimeConfig.arg["HOST_IP"]
    mac = configManager.runtimeConfig.arg["MAC"]
    HOST_HTTP_PORT = configManager.runtimeConfig.arg["HTTP_PORT"]
    HOST_HTTPS_PORT = configManager.runtimeConfig.arg["HTTPS_PORT"]
    CONFIG_PATH = configManager.runtimeConfig.arg["CONFIG_PATH"]
    DISABLE_HTTPS = configManager.runtimeConfig.arg["noServeHttps"]
    updateManager.startupCheck()

    Thread(target=daylightSensor, args=[bridgeConfig["config"]["timezone"], bridgeConfig["sensors"]["1"]]).start()
    ### start services
    if bridgeConfig["config"]["deconz"]["enabled"]:
        Thread(target=deconz.websocketClient).start()
    if bridgeConfig["config"]["mqtt"]["enabled"]:
        Thread(target=mqtt.mqttServer).start()
    if bridgeConfig["config"]["homeassistant"]["enabled"]:
        homeAssistantWS.create_ws_client(bridgeConfig)
    if not ("discovery" in bridgeConfig["config"] and bridgeConfig["config"]["discovery"] == False):
        Thread(target=remoteDiscover.runRemoteDiscover, args=[bridgeConfig["config"]]).start()
    Thread(target=remoteApi.runRemoteApi, args=[BIND_IP, bridgeConfig["config"]]).start()
    Thread(target=stateFetch.syncWithLights, args=[False]).start()
    Thread(target=ssdp.ssdpSearch, args=[HOST_IP, HOST_HTTP_PORT, mac]).start()
    Thread(target=ssdp.ssdpBroadcast, args=[HOST_IP, HOST_HTTP_PORT, mac]).start()
    Thread(target=mdns.mdnsListener, args=[HOST_IP, HOST_HTTP_PORT, "BSB002", bridgeConfig["config"]["bridgeid"]]).start()
    Thread(target=scheduler.runScheduler).start()
    Thread(target=eventStreamer.messageBroker).start()
    if not DISABLE_HTTPS:
        Thread(target=runHttps, args=[BIND_IP, HOST_HTTPS_PORT, CONFIG_PATH]).start()
    runHttp(BIND_IP, HOST_HTTP_PORT)
