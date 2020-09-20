#!/usr/bin/python3
from flask import Flask
from flask.json import jsonify
from flask_restful import Api
from functions.core import generateDxState
from threading import Thread
import ssl
import configManager
import logManager
import flask_login
from flaskUI.core import User #dummy import for flaks_login module
from services import mqtt, deconz, ssdp, scheduler, remoteApi, remoteDiscover
from flaskUI.restful import NewUser, EntireConfig, ResourceElements, Element, ElementParam

bridgeConfig = configManager.bridgeConfig.json_config
dxState = configManager.runtimeConfig.dxState
newLights = configManager.runtimeConfig.newLights
logging = logManager.logger.get_logger(__name__)

app = Flask(__name__, template_folder='flaskUI/templates',static_url_path="/static", static_folder='flaskUI/static')
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


### HUE API
api.add_resource(NewUser, '/api/', strict_slashes=False)
api.add_resource(EntireConfig, '/api/<string:username>', strict_slashes=False)
api.add_resource(ResourceElements, '/api/<string:username>/<string:resource>', strict_slashes=False)
api.add_resource(Element, '/api/<string:username>/<string:resource>/<string:resourceid>', strict_slashes=False)
api.add_resource(ElementParam, '/api/<string:username>/<string:resource>/<string:resourceid>/<string:param>/', strict_slashes=False)

### WEB INTERFACE
from flaskUI.core.views import core
from flaskUI.devices.views import devices
from flaskUI.error_pages.handlers import error_pages
app.register_blueprint(core)
app.register_blueprint(devices)
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
        Thread(target=deconz.websocketClient).start()
    if bridgeConfig["emulator"]["mqtt"]["enabled"]:
        Thread(target=mqtt.mqttServer).start()
    if not configManager.runtimeConfig.arg["disableOnlineDiscover"]:
        Thread(target=remoteDiscover.runRemoteDiscover, args=[bridgeConfig["config"]]).start()
    Thread(target=remoteApi.runRemoteApi, args=[BIND_IP, bridgeConfig["config"]]).start()
    Thread(target=ssdp.ssdpSearch, args=[HOST_IP, HOST_HTTP_PORT, mac]).start()
    Thread(target=ssdp.ssdpBroadcast, args=[HOST_IP, HOST_HTTP_PORT, mac]).start()

    Thread(target=scheduler.runScheduler).start()
    Thread(target=runHttps).start()
    runHttp()
