from flask import render_template, request, Blueprint, url_for
import flask_login
import configManager
import logManager
from flaskUI.devices.forms import DevicesForm
from functions.devicesRules import addTradfriDimmer, addTradfriCtRemote, addTradfriOnOffSwitch, addTradfriSceneRemote

logging = logManager.logger.get_logger(__name__)
#################
suportedDevicesRules = ["TRADFRI remote control", "TRADFRI on/off switch", "TRADFRI wireless dimmer"]
dailightMotionEmulation = ["TRADFRI motion sensor", "lumi.sensor_motion"]
#################
bridgeConfig = configManager.bridgeConfig.json_config

devices = Blueprint('devices',__name__)

@devices.route('/devices', methods=['GET', 'POST'])
@flask_login.login_required
def sensors():
    form = DevicesForm()
    groups = []
    devicesConfig = []
    motionSensorsConfig = []

    for key, device in bridgeConfig["emulator"]["sensors"].items():
        if device["modelid"] in suportedDevicesRules:
            devicesConfig.append({"name": bridgeConfig["sensors"][device["bridgeId"]]["name"], "id": device["bridgeId"], "modelid": device["modelid"], "configured": device["configured"] if "configured" in device else {"room": None, "option": None}})
        if device["modelid"] in dailightMotionEmulation:
            motionSensorsConfig.append({"name": bridgeConfig["sensors"][device["bridgeId"]]["name"], "id": device["bridgeId"], "lightSensor":  device["lightSensor"]})
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
        # set new rules
        formFields = request.form.to_dict()
        for key, value in formFields.items():
            if key.startswith('device-'):
                deviceid = key[7:]
                modelid = bridgeConfig["sensors"][deviceid]["modelid"]
                if modelid == "TRADFRI on/off switch":
                    addTradfriOnOffSwitch(deviceid, value)
                elif modelid == "TRADFRI remote control":
                    if formFields["config-" + deviceid] == "Color Temp Switch":
                        addTradfriCtRemote(deviceid, value)
                    elif formFields["config-" + deviceid] == "Scene Switch":
                        addTradfriSceneRemote(deviceid, value)
        # save current html fields
        for key, device in bridgeConfig["emulator"]["sensors"].items():
            if "device-" + device["bridgeId"] in formFields:
                bridgeConfig["emulator"]["sensors"][key]["configured"] = {"room": formFields["device-" + device["bridgeId"]]}
                if "config-" + device["bridgeId"] in formFields:
                    bridgeConfig["emulator"]["sensors"][key]["configured"]["option"] = formFields["config-" + device["bridgeId"]]
            elif "motion-" + device["bridgeId"] in formFields:
                bridgeConfig["emulator"]["sensors"][key]["lightSensor"] = formFields["motion-" + device["bridgeId"]]
        configManager.bridgeConfig.save_config()

    return render_template('devices.html', groups=groups, devicesConfig=devicesConfig, motionSensors=motionSensorsConfig, form=form)
