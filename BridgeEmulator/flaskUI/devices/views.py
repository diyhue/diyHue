from flask import render_template, request, Blueprint, url_for
import flask_login
import configManager
import logManager
from flaskUI.devices.forms import DevicesForm
from functions.devicesRules import addTradfriDimmer, addTradfriCtRemote, addTradfriOnOffSwitch, addTradfriSceneRemote

logging = logManager.logger.get_logger(__name__)
#################
suportedDevicesRules = ["TRADFRI remote control", "TRADFRI on/off switch", "TRADFRI wireless dimmer"]
dailightMotionEmulation = ["TRADFRI motion sensor", "lumi.sensor_motion", "lumi.motion.ac02"]
#################
bridgeConfig = configManager.bridgeConfig.yaml_config

devices = Blueprint('devices',__name__)

@devices.route('/devices', methods=['GET', 'POST'])
@flask_login.login_required
def sensors():
    form = DevicesForm()
    groups = []
    devicesConfig = []
    motionSensorsConfig = []

    for key, device in bridgeConfig["sensors"].items():
        if device.modelid in suportedDevicesRules:
            devicesConfig.append({"name": device.name, "id": device.id_v1, "modelid": device.modelid, "configured": device.protocol_cfg["configured"] if "configured" in  device.protocol_cfg else {"room": None, "option": None}})
        if device.type == "ZLLLightLevel" and "modelid" in device.protocol_cfg and device.protocol_cfg["modelid"] in dailightMotionEmulation:
            motionSensorsConfig.append({"name": device.name, "id": device.id_v1, "lightSensor":  device.protocol_cfg["lightSensor"]})
    for key, group in bridgeConfig["groups"].items():
        groups.append({"name": group.name, "id": group.id_v1})
    if request.method == 'POST':
        # clean all previews rules
        for resourcelink in list(bridgeConfig["resourcelinks"]):
            if bridgeConfig["resourcelinks"][resourcelink].classid == 15555:
                for link in bridgeConfig["resourcelinks"][resourcelink].links:
                    pices = link.split("/")
                    object = bridgeConfig[pices[1]][pices[2]]
                    if object.recycle:
                        del bridgeConfig[pices[1]][pices[2]]
                del bridgeConfig["resourcelinks"][resourcelink]
        # set new rules
        formFields = request.form.to_dict()
        for key, value in formFields.items():
            if key.startswith('device-'):
                deviceid = key[7:]
                modelid = bridgeConfig["sensors"][deviceid].modelid
                if modelid == "TRADFRI on/off switch":
                    addTradfriOnOffSwitch(deviceid, value)
                elif modelid == "TRADFRI remote control":
                    if formFields["config-" + deviceid] == "Color Temp Switch":
                        addTradfriCtRemote(deviceid, value)
                    elif formFields["config-" + deviceid] == "Scene Switch":
                        addTradfriSceneRemote(deviceid, value)
                elif modelid == "TRADFRI wireless dimmer":
                    addTradfriDimmer(deviceid, value)
        # save current html fields
        for key, device in bridgeConfig["sensors"].items():
            if "device-" + device.id_v1 in formFields:
                device.protocol_cfg["configured"] = {"room": formFields["device-" + device.id_v1]}
                if "config-" + device.id_v1 in formFields:
                    device.protocol_cfg["configured"]["option"] = formFields["config-" + device.id_v1]
            elif "motion-" + device.id_v1 in formFields:
                device.protocol_cfg["lightSensor"] = formFields["motion-" + device.id_v1]
        configManager.bridgeConfig.save_config()

    return render_template('devices.html', groups=groups, devicesConfig=devicesConfig, motionSensors=motionSensorsConfig, form=form)
