from flask import render_template, request, Blueprint, redirect, url_for, make_response
from werkzeug.security import generate_password_hash,check_password_hash
from flaskUI.core.forms import LoginForm
import flask_login
import configManager
from flaskUI.core import User

bridgeConfig = configManager.bridgeConfig.yaml_config

core = Blueprint('core',__name__)

@core.route('/')
@flask_login.login_required
def index():
    return render_template('index.html', groups=bridgeConfig["groups"], lights=bridgeConfig["lights"])

@core.route('/state', methods=['GET', 'PUT'])
@flask_login.login_required
def interface_api():
    if request.method == 'GET':
        result = {}
        for group in bridgeConfig["groups"]:
            result[bridgeConfig["groups"][group].id_v1] = {"name": bridgeConfig["groups"][group].name, "on":  bridgeConfig["groups"][group].state["any_on"], "lights": []}
            for light in bridgeConfig["groups"][group].lights:
                result[bridgeConfig["groups"][group].id_v1]["lights"].append(light().state)
        return result
    elif request.method == 'PUT':
        putDict = request.json
        bridgeConfig["groups"][putDict["group"]].setV1Action(state=putDict["action"], scene=None)
        return "success"

@core.route('/save')
def save_config():
    configManager.bridgeConfig.save_config()
    return "config saved"


@core.route('/config')
@flask_login.login_required
def config():
    return render_template('config.html', config=bridgeConfig["config"])


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
