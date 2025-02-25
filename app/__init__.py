from flask import Flask
from flask_mysqldb import MySQL
from flask_mail import Mail, Message

# Inicializar MySQL
mysql = MySQL()

def create_app():
    # Crear la instancia de la aplicación Flask
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    # Cargar la configuración desde config.py
    from app.config import Config,os
    app.config.from_object(Config)

    # Configuración de Flask-Mail
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USE_SSL"] = False

    app.config['MAIL_USERNAME'] = 'zaikodo.services@gmail.com'
    app.config['MAIL_PASSWORD'] = MAIL_PASSWORD =  os.getenv("SECRET_MAIL")

    app.config["MAIL_DEFAULT_SENDER"] = ('ZaikoDo','zaikodo.services@gmail.com')

    from app.email import init_mail
    init_mail(app)
    

    


        

    # Registrar Blueprints para rutas
    from app.routes import routes_blueprint
    from app.auth import auth_blueprint
    app.register_blueprint(routes_blueprint, url_prefix="")
    app.register_blueprint(auth_blueprint, url_prefix="")

    from app.routes import init_mysql
    init_mysql(app)

    return app