from wtforms import Form
from wtforms import StringField, IntegerField
from wtforms.validators import InputRequired, Length, NumberRange

class VentasCreditoForm(Form):
    nombre = StringField('Nombre', validators=[InputRequired(message="El nombre es obligatorio")])
    id = StringField('Identificación', validators=[
        InputRequired(message="La identificación es obligatoria"),
        Length(min=6, max=20, message="La identificación debe tener entre 6 y 20 caracteres")
    ])
    contacto = StringField('Contacto', validators=[
        InputRequired(message="El contacto es obligatorio"),
        Length(min=8, max=15, message="El contacto debe tener entre 8 y 15 caracteres")
    ])
    nota = StringField('Nota (máximo 100 caracteres)', validators=[
        Length(max=100, message="La nota no puede exceder los 100 caracteres")
    ])
