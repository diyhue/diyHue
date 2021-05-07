from flask import render_template, request, Blueprint, redirect, url_for, make_response
from werkzeug.security import generate_password_hash,check_password_hash
from flaskUI.core.forms import LoginForm
import flask_login
import uuid
import configManager
import HueObjects
from flaskUI.core import User

bridgeConfig = configManager.bridgeConfig.yaml_config

core = Blueprint('core',__name__)

@core.route('/')
@flask_login.login_required
def index():
    return render_template('index.html', groups=bridgeConfig["groups"], lights=bridgeConfig["lights"])

@core.route('/get-key')
@flask_login.login_required
def get_key():
    if len(bridgeConfig["apiUsers"]) == 0:
        # generate a new user for the web interface
        username = str(uuid.uuid1()).replace('-', '')
        bridgeConfig["apiUsers"][username] = HueObjects.ApiUser(username, 'WebUi', None)
        configManager.bridgeConfig.save_config()
    return list(bridgeConfig["apiUsers"])[0]

@core.route('/lights')
@flask_login.login_required
def get_lights():
    result = {}
    for light, object in bridgeConfig["lights"].items():
        result[light] = object.save()
    return result

@core.route('/save')
def save_config():
    configManager.bridgeConfig.save_config()
    return "config saved"


@core.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'GET':
        return render_template('accounts/login.html', form=form)
    email = form.email.data
    if email not in bridgeConfig["config"]["users"]:
        return 'User don\'t exist'
    if check_password_hash(bridgeConfig["config"]["users"][email]['password'],form.password.data):
        user = User()
        user.id = email
        flask_login.login_user(user)
        return redirect(url_for('core.index'))

    print(generate_password_hash(form.password.data))

    return 'Bad login'


@core.route('/description.xml')
def description_xml():
    HOST_HTTP_PORT = configManager.runtimeConfig.arg["HTTP_PORT"]
    mac = configManager.runtimeConfig.arg["MAC"]
    resp = make_response(render_template('description.xml', mimetype='text/xml', port=HOST_HTTP_PORT, name=bridgeConfig["config"]["name"], ipaddress=bridgeConfig["config"]["ipaddress"], serial=mac))
    resp.headers['Content-type'] = 'text/xml'
    return resp



@core.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect(url_for('core.login'))
