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


# Cargar configuración de la base de datos desde un archivo .env
load_dotenv(dotenv_path='/home/ZaikodDo/.env')


# Configuración para cargar plantillas
# Ruta absoluta al directorio 'templates'
TEMPLATES_DIR = "/home/ZaikodDo/Zaiko-Do/templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

# Configuración del servidor de correo
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
MAIL_USERNAME = "zaikodo.services@gmail.com"
MAIL_PASSWORD = SECRET_MAIL = os.getenv("SECRET_MAIL")

# Conexión a la base de datos
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB")
    )



def enviar_correo(destinatario, nombre_usuario):
    try:
        current_year = datetime.now().year

        # Cargar y renderizar la plantilla HTML
        template = env.get_template("Correos/correo_vencimiento.html")
        html = template.render(
            nombre_usuario=nombre_usuario,
            destinatario=destinatario,
            current_year=current_year
        )

        # Crear el mensaje de correo
        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = "Notificación: Tu plan en Zaiko Do ha vencido"
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



# Función para actualizar planes vencidos y enviar correos
def actualizar_planes_vencidos():
    try:
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener la hora actual de Bogotá
        bogota_tz = pytz.timezone('America/Bogota')
        fecha_actual = datetime.now(bogota_tz).strftime('%Y-%m-%d %H:%M:%S')


        # Seleccionar los usuarios con planes vencidos
        cursor.execute("""
            SELECT idusuario, nombre, correo
            FROM usuario
            WHERE idplan != 1 AND fecha_expiracion_plan <= %s
        """, (fecha_actual,))

        usuarios_vencidos = cursor.fetchall()

        # Actualizar los planes de los usuarios seleccionados
        for usuario in usuarios_vencidos:
            idusuario = usuario['idusuario']
            nombre = usuario['nombre']
            correo = usuario['correo']

            cursor.execute("""
                UPDATE usuario
                SET idplan = 1,
                    fecha_creacion_plan = %s,
                    fecha_expiracion_plan = %s
                WHERE idusuario = %s
            """, (fecha_actual, fecha_actual, idusuario))

            # Enviar correo al usuario
            enviar_correo(correo, nombre)

        # Guardar los cambios en la base de datos
        conn.commit()
        print(f"{len(usuarios_vencidos)} usuarios actualizados y notificados.")

    except mysql.connector.Error as err:
        print(f"Error al actualizar los planes vencidos: {err}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

# Verificar si el script está siendo ejecutado directamente
if __name__ == "__main__":
    actualizar_planes_vencidos()
