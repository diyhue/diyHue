from flask import render_template,request,Blueprint
from core.forms import LoginForm

core = Blueprint('core',__name__)

@core.route('/')
def index():
    return render_template('index.html')


@core.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        pass
    return render_template('accounts/login.html', form=form)
