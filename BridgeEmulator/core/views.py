from flask import render_template,request,Blueprint, redirect, url_for, make_response
from werkzeug.security import generate_password_hash,check_password_hash
from core.forms import LoginForm
from flask import request
import flask_login
import configManager
from core import User

bridgeConfig = configManager.bridgeConfig.json_config

core = Blueprint('core',__name__)

@core.route('/')
@flask_login.login_required
def index():
    return render_template('index.html')


@core.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'GET':
        return render_template('accounts/login.html', form=form)
    email = form.email.data
    if check_password_hash(bridgeConfig["emulator"]["users"][email]['password'],form.password.data):
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
