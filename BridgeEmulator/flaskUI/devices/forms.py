from flask_wtf import FlaskForm
from wtforms import SubmitField

class DevicesForm(FlaskForm):
    submit = SubmitField('Save')
