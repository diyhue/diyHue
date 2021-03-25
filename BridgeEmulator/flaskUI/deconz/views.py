from flask import render_template, request, Blueprint, redirect, url_for
import flask_login
import configManager

bridgeConfig = configManager.bridgeConfig.yaml_config


manageDeconz = Blueprint('deconz',__name__)

@manageDeconz.route('/deconz')
@flask_login.login_required
def deconz():
    return render_template('deconz.html', mqtt=bridgeConfig["emulator"]["deconz"])
