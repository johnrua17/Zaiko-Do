from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from app.config import Config
from app.database import get_connection
from functools import wraps
from app import mysql
from app.email import enviar_correos
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from dotenv import load_dotenv
import os

import bleach
import requests
import uuid
import random

load_dotenv(dotenv_path='/home/ZaikodDo/.env')

# Crear un Blueprint para las rutas de autenticación
auth_blueprint = Blueprint('auth', __name__)

def obtener_hora_actual_bogota():
    """Obtiene la hora actual en la zona horaria de Bogotá."""
    return datetime.now(Config.ZONE_BOGOTA)

def gestionar_intentos(correo, exito=False):
    """Gestiona los intentos fallidos de inicio de sesión."""
    conn = get_connection()
    cur = conn.cursor()

    if exito:
        # Restablecer intentos fallidos en caso de éxito
        cur.execute("""
            UPDATE usuario
            SET intentos_fallidos = 0, bloqueado_hasta = NULL, ultimo_intento = %s
            WHERE correo = %s
        """, (obtener_hora_actual_bogota(), correo))
    else:
        # Incrementar intentos fallidos
        cur.execute("""
            UPDATE usuario
            SET intentos_fallidos = intentos_fallidos + 1, ultimo_intento = %s
            WHERE correo = %s
        """, (obtener_hora_actual_bogota(), correo))

        # Verificar si el usuario alcanzó el límite de intentos
        cur.execute("SELECT intentos_fallidos FROM usuario WHERE correo = %s", [correo])
        result = cur.fetchone()

        if result and result['intentos_fallidos'] >= Config.MAX_INTENTOS:
            # Bloquear al usuario por el tiempo definido
            cur.execute("""
                UPDATE usuario
                SET bloqueado_hasta = %s
                WHERE correo = %s
            """, (obtener_hora_actual_bogota() + timedelta(minutes=Config.TIEMPO_BLOQUEO_MINUTOS), correo))

    conn.commit()
    cur.close()


CLOUDFLARE_SECRET_KEY = '0x4AAAAAAA7Y2N38H_aQLsbZAMpaIJcHhTY'

def verify_turnstile_token(token):
    """Envía el token de Turnstile a la API de Cloudflare para verificar su validez."""
    if not token:
        return False

    url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
    data = {
        'secret': CLOUDFLARE_SECRET_KEY,
        'response': token
    }

    try:
        # Envía el token a Cloudflare
        response = requests.post(url, data=data)
        result = response.json()

        return result.get('success', False)  # Retorna True si el token es válido

    except Exception as e:
        # Maneja cualquier error en la solicitud
        print(f"Error al verificar el token de Turnstile: {str(e)}")
        return False




@auth_blueprint.route('/login', methods=['GET', 'POST'], endpoint='login')
def login_user():
    """Autentica a un usuario en el sistema."""
    if request.method == 'POST':
        # Obtener y verificar el token de Turnstile
        # turnstile_token = request.form.get('cf-turnstile-response')
        # if not verify_turnstile_token(turnstile_token):
        #     return render_template('index.html', error_message='Error en la verificación de seguridad. Inténtelo nuevamente.')

        correo = request.form['email']
        contraseña = request.form['password']

        conn = get_connection()
        cur = conn.cursor()

        # Buscar al usuario en la base de datos
        cur.execute('SELECT * FROM usuario WHERE correo = %s', [correo])
        account = cur.fetchone()

        if account:
            # Verificar si está bloqueado
            if account['bloqueado_hasta'] and account['bloqueado_hasta'].replace(tzinfo=Config.ZONE_BOGOTA) > obtener_hora_actual_bogota():
                tiempo_restante = account['bloqueado_hasta'].replace(tzinfo=Config.ZONE_BOGOTA) - obtener_hora_actual_bogota()
                minutos_restantes = int(tiempo_restante.total_seconds() / 60)
                error_message = f"Cuenta bloqueada. Inténtelo de nuevo en {minutos_restantes} minutos."
                return render_template('index.html', error_message=error_message)

            if check_password_hash(account['contraseña'], contraseña):
                # Generar un nuevo session_id
                new_session_id = str(uuid.uuid4())

                # Actualizar el session_id en la base de datos
                cur.execute("""
                    UPDATE usuario
                    SET session_id = %s
                    WHERE idusuario = %s
                """, (new_session_id, account['idusuario']))
                conn.commit()

                # Guardar el session_id en la sesión del usuario
                session.update({
                    'logueado': True,
                    'idusuario': account['idusuario'],
                    'nombre': account['nombre'],
                    'role': account['role'],
                    'correo': account['correo'],
                    'idplan': account['idplan'],
                    'username': account['nombre'],
                    'session_id': new_session_id  # Guardar el session_id en la sesión
                })

                gestionar_intentos(correo, exito=True)
                return redirect(url_for('routes.admin'))
            else:
                gestionar_intentos(correo, exito=False)
                return render_template('index.html', error_message="Credenciales incorrectas.")               
        else:
           return render_template('index.html', error_message="El usuario no existe.")

    return render_template('index.html')

def validar_sesion(f):
    """Decorador para validar la sesión del usuario."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logueado' in session:
            try:
                with mysql.connection.cursor() as cur:
                    # Obtener el session_id almacenado en la base de datos
                    cur.execute('SELECT session_id FROM usuario WHERE idusuario = %s', [session['idusuario']])
                    result = cur.fetchone()

                    if result and result['session_id'] != session.get('session_id'):
                        # Si el session_id no coincide, cerrar la sesión actual
                        session.clear()  # Limpiar toda la sesión
                        print("Tu sesión ha sido cerrada porque iniciaste sesión en otro dispositivo.", 'error')
                        return redirect(url_for('auth.login'))
            except Exception as e:
                # Manejar errores de base de datos
                print(f"Error al validar la sesión: {e}")
                session.clear()  # Limpiar toda la sesión en caso de error
                print("Ocurrió un error al validar tu sesión. Por favor, inicia sesión nuevamente.", 'error')
                return redirect(url_for('auth.login'))
        else:
            # Si no hay sesión activa, redirigir al login
            return redirect(url_for('auth.login'))

        return f(*args, **kwargs)
    return decorated_function

CLOUDFLARE_SECRET_KEY_REGISTER = '0x4AAAAAAA7ZB7u4Qaog9mifEKyPvj1lai4'

def verify_turnstile_token_registro(token):
    """Envía el token de Turnstile a la API de Cloudflare para verificar su validez."""
    if not token:
        return False

    url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
    data = {
        'secret': CLOUDFLARE_SECRET_KEY_REGISTER,
        'response': token
    }

    try:
        # Envía el token a Cloudflare
        response = requests.post(url, data=data)
        result = response.json()

        return result.get('success', False)  # Retorna True si el token es válido

    except Exception as e:
        # Maneja cualquier error en la solicitud
        print(f"Error al verificar el token de Turnstile: {str(e)}")
        return False

@auth_blueprint.route('/register', methods=['GET', 'POST'], endpoint='register')
def register_user():
    """Registra un nuevo usuario en el sistema."""
    if request.method == 'POST':
        # Obtener y verificar el token de Turnstile
        # turnstile_token = request.form.get('cf-turnstile-response')
        # if not verify_turnstile_token_registro(turnstile_token):
        #     return render_template('register.html', message='Error en la verificación de seguridad. Inténtelo nuevamente.')
            
        nombre = bleach.clean(request.form['name'])
        correo = bleach.clean(request.form['email'])
        contraseña = request.form['password']

        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute('START TRANSACTION')

            # Verificar si el correo ya está registrado
            cur.execute('SELECT * FROM usuario WHERE correo = %s', [correo])
            if cur.fetchone():
                return render_template('register.html', message='El correo ya está en uso.')
            
            # Crear usuario
            contraseña_hash = generate_password_hash(contraseña)
            fecha_creacion_plan = obtener_hora_actual_bogota()
            otp = random.randint(100000, 999999)
            cur.execute("""
                INSERT INTO usuario (nombre, correo, contraseña, role, idplan, fecha_creacion_plan, token_verificacion, token_expiracion, verificado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (nombre, correo, contraseña_hash, 'usuario', 1, fecha_creacion_plan, otp, fecha_creacion_plan + timedelta(days=1), False))
            
            conn.commit()

            enviar_correos(correo, nombre, "vencimiento", otp)

            session['logueado'] = True
            session['idusuario'] = cur.lastrowid
            session['nombre'] = nombre
            session['role'] = 'usuario'
            session['username'] = nombre
            session['idplan'] = 1

            s = URLSafeTimedSerializer(os.getenv("SECRET_KEY"))
            token = s.dumps(correo, salt='email-confirm')
            return redirect(url_for('routes.validar', token=token))
        except Exception as e:
            conn.rollback()
            print(e)
            return render_template('register.html', message='Error en el registro. Inténtelo de nuevo más tarde.')
        finally:
            cur.close()
    return render_template('register.html')

@auth_blueprint.route('/validar_otp', methods=['GET', 'POST'], endpoint='validar_otp')
def validar_otp():
    """Valida el OTP ingresado por el usuario."""
    if request.method == 'POST':
        otp = request.form['otp']
        correo = request.form['correo']

        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute('SELECT * FROM usuario WHERE correo = %s', [correo])
            usuario = cur.fetchone()

            if usuario and usuario['token_verificacion'] == int(otp) and usuario['token_expiracion'] > obtener_hora_actual_bogota():
                cur.execute('UPDATE usuario SET verificado = %s WHERE correo = %s', (True, correo))
                conn.commit()
                return redirect(url_for('auth.admin'))
            else:
                return render_template('validar_otp.html', message='OTP incorrecto o expirado.')
        except Exception as e:
            conn.rollback()
            return render_template('validar_otp.html', message='Error al validar el OTP. Inténtelo de nuevo más tarde.')
        finally:
            cur.close()
    return render_template('validar_otp.html')
