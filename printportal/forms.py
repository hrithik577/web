# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SubmitField, PasswordField, TextAreaField, DateTimeLocalField
from wtforms.validators import DataRequired, NumberRange
from flask_wtf.file import FileAllowed, FileRequired, MultipleFileField

class ShopCodeForm(FlaskForm):
    shop_code = StringField('Print Shop Code', validators=[DataRequired()])
    submit = SubmitField('Select')

class UploadForm(FlaskForm):
    files = MultipleFileField('Upload Files', validators=[
        FileRequired(),
        FileAllowed(['pdf', 'docx', 'pptx', 'xlsx', 'png', 'jpg'], 'Only PDF, DOCX, PPTX, XLSX, PNG, JPG allowed!')
    ])
    copies = IntegerField('Number of Copies', validators=[DataRequired(), NumberRange(min=1)])
    color = BooleanField('Color Printing')
    duplex = BooleanField('Double-Sided')
    notes = TextAreaField('Special Instructions', validators=[])
    scheduled_at = DateTimeLocalField('Schedule Printing Date and Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    submit = SubmitField('Send to Shop')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')