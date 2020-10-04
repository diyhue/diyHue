from flask import render_template, request, Blueprint, url_for
import flask_login
import configManager
import logManager
from flaskUI.devices.forms import DevicesForm
from functions.devicesRules import addTradfriDimmer, addTradfriCtRemote, addTradfriOnOffSwitch, addTradfriSceneRemote

logging = logManager.logger.get_logger(__name__)
#################
suportedDevicesRules = ["TRADFRI remote control", "TRADFRI on/off switch", "TRADFRI wireless dimmer"]
suportedDevicesSettings = ["TRADFRI motion sensor"]
#################
bridgeConfig = configManager.bridgeConfig.json_config

devices = Blueprint('devices',__name__)

@devices.route('/devices', methods=['GET', 'POST'])
@flask_login.login_required
def sensors():
    form = DevicesForm
    groups = []
    devices = []
    devicesConfig = []

    for key, device in bridgeConfig["sensors"].items():
        if device["modelid"] in suportedDevicesRules:
            devices.append({"name": device["name"], "id": key, "modelid": device["modelid"]})
    for key, device in bridgeConfig["emulator"]["sensors"].items():
        if device["modelid"] in suportedDevicesSettings:
            devicesConfig.append({"name": key, "id": device["bridgeId"], "modelid": device["modelid"]})
    for key, group in bridgeConfig["groups"].items():
        groups.append({"name": group["name"], "id": key})
    if request.method == 'POST':
        # clean all previews rules
        for resourcelink in list(bridgeConfig["resourcelinks"]):
            if bridgeConfig["resourcelinks"][resourcelink]["classid"] == 15555:
                for link in bridgeConfig["resourcelinks"][resourcelink]["links"]:
                    pices = link.split('/')
                    if pices[1] == "rules":
                        del bridgeConfig["rules"][pices[2]]
                del bridgeConfig["resourcelinks"][resourcelink]
    return render_template('devices.html', groups=groups, devices=devices, devicesConfig=devicesConfig, form=form)
