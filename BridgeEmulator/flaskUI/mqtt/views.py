from flask import render_template, request, Blueprint, redirect, url_for
import flask_login
import configManager

bridgeConfig = configManager.bridgeConfig.yaml_config


manageMqtt = Blueprint('mqtt',__name__)

@manageMqtt.route('/mqtt')
@flask_login.login_required
def mqtt():
    return render_template('mqtt.html', mqtt=bridgeConfig["emulator"]["mqtt"])
