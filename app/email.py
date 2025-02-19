from datetime import datetime
import pytz
import os
import mysql.connector
from dotenv import load_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
from email.utils import formataddr
import random

# Cargar configuración de la base de datos desde un archivo .env
load_dotenv(dotenv_path='/home/ZaikodDo/.env')


# Configuración para cargar plantillas
# Ruta absoluta al directorio 'templates'
#TEMPLATES_DIR = "/home/ZaikodDo/Zaiko-Do/templates"
TEMPLATES_DIR = "C:/Users/Cami_/OneDrive/Documentos/Visual Proyects/ZaikoDo/vZaikodo/Zaiko-Do/templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

# Configuración del servidor de correo
SMTP_SERVER = "smtp.gmail.com"
#SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = 587
#SMTP_PORT = int(os.getenv("SMTP_PORT"))
MAIL_USERNAME = "zaikodo.services@gmail.com"
#MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = SECRET_MAIL = os.getenv("SECRET_MAIL")

# Conexión a la base de datos
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("SECRET_HOST"),
            user=os.getenv("SECRET_USER_BD"),
            password=os.getenv("SECRET_KEY"),
            database=os.getenv("SECRET_BD")
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

def enviar_correos(destinatario, nombre_usuario, tipo, otp):
    if tipo == "vencimiento":
        try:
            current_year = datetime.now().year

            # Cargar y renderizar la plantilla HTML
            template = env.get_template("Correos/correo_verificacion.html")
            html = template.render(
                nombre_usuario=nombre_usuario,
                destinatario=destinatario,
                current_year=current_year,
                otp = otp
            )

            # Crear el mensaje de correo
            mensaje = MIMEMultipart("alternative")
            mensaje["Subject"] = "Confirmación de correo"
            mensaje["From"] = formataddr(("Zaikodo", MAIL_USERNAME))
            mensaje["To"] = destinatario
            mensaje.attach(MIMEText(html, "html"))

            # Enviar el correo
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(MAIL_USERNAME, MAIL_PASSWORD)
                server.sendmail(MAIL_USERNAME, destinatario, mensaje.as_string())

            print(f"Correo enviado exitosamente a: {destinatario}")

        except Exception as e:
            print(f"Error al enviar el correo a {destinatario}: {e}")

