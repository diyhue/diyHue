from flask import render_template, request, Blueprint, redirect, url_for
import flask_login
import configManager

bridgeConfig = configManager.bridgeConfig.json_config


devices = Blueprint('devices',__name__)

@devices.route('/devices')
@flask_login.login_required
def sensors():
    return render_template('devices.html', emulatorSensors=bridgeConfig["emulator"]["sensors"], sensors=bridgeConfig["sensors"])
