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
from flask_mail import Mail, Message
from flask import Flask, render_template


def init_mail(app):
    global mail
    mail = Mail(app)

def enviar_correos_vencimiento(destinatario, nombre_usuario, otp):
        try:
            asunto = 'Confirmación de correo'
            current_year = datetime.now().year
            cuerpo_html = render_template('Correos/correo_verificacion.html', nombre_usuario=nombre_usuario,
                    destinatario=destinatario,
                    current_year=current_year,
                    otp = otp)
            mensaje = Message(asunto, recipients=[destinatario])
            mensaje.html = cuerpo_html
            mail.send(mensaje)
            print(f"Correo enviado exitosamente a: {destinatario}")
        except Exception as e:
            print(f"Error al enviar el correo a {destinatario}: {e}")

def enviar_correos_contraeña(destinatario, nombre_usuario, link):
        try:
            asunto = 'Recuperación de contraseña'
            current_year = datetime.now().year
            cuerpo_html = render_template('Correos/correo_contrasena.html', nombre_usuario=nombre_usuario,
                    destinatario=destinatario,
                    current_year=current_year,
                    link = link)
            mensaje = Message(asunto, recipients=[destinatario])
            mensaje.html = cuerpo_html
            mail.send(mensaje)
            print(f"Correo enviado exitosamente a: {destinatario}")
        except Exception as e:
            print(f"Error al enviar el correo a {destinatario}: {e}")

# def enviar_correos(destinatario, nombre_usuario, tipo, otp):
#     if tipo == "vencimiento":
#         try:
#             current_year = datetime.now().year

#             # Cargar y renderizar la plantilla HTML
#             template = env.get_template("Correos/correo_verificacion.html")
#             html = template.render(
#                 nombre_usuario=nombre_usuario,
#                 destinatario=destinatario,
#                 current_year=current_year,
#                 otp = otp
#             )

#             # Crear el mensaje de correo
#             mensaje = MIMEMultipart("alternative")
#             mensaje["Subject"] = "Confirmación de correo"
#             mensaje["From"] = formataddr(("Zaikodo", MAIL_USERNAME))
#             mensaje["To"] = destinatario
#             mensaje.attach(MIMEText(html, "html"))

#             # Enviar el correo
#             with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
#                 server.starttls()
#                 server.login(MAIL_USERNAME, MAIL_PASSWORD)
#                 server.sendmail(MAIL_USERNAME, destinatario, mensaje.as_string())

#             print(f"Correo enviado exitosamente a: {destinatario}")

#         except Exception as e:
#             print(f"Error al enviar el correo a {destinatario}: {e}")

