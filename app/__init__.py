from flask import Flask
from flask_mysqldb import MySQL

# Inicializar MySQL
mysql = MySQL()

def create_app():
    # Crear la instancia de la aplicación Flask
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    # Cargar la configuración desde config.py
    from app.config import Config
    app.config.from_object(Config)

    # Inicializar extensiones
        

    # Registrar Blueprints para rutas
    from app.routes import routes_blueprint
    from app.auth import auth_blueprint
    app.register_blueprint(routes_blueprint, url_prefix="")
    app.register_blueprint(auth_blueprint, url_prefix="")

    from app.routes import init_mysql
    init_mysql(app)

    return app