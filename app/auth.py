from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from app.config import Config
from app.database import get_connection
import bleach

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

@auth_blueprint.route('/login', methods=['GET', 'POST'], endpoint='login')
def login_user():
    """Autentica a un usuario en el sistema."""
    if request.method == 'POST':
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

            # Verificar contraseña
            if check_password_hash(account['contraseña'], contraseña):
                session['logueado'] = True
                session['idusuario'] = account['idusuario']
                session['nombre'] = account['nombre']
                session['role'] = account['role']
                session['correo'] = account['correo']
                session['idplan'] = account['idplan']
                session['username'] = account['nombre']

                gestionar_intentos(correo, exito=True)
                return redirect(url_for('routes.admin'))
            else:
                gestionar_intentos(correo, exito=False)
                return render_template('index.html', error_message="Credenciales incorrectas.")

        return render_template('index.html', error_message="El usuario no existe.")
    return render_template('index.html')

@auth_blueprint.route('/register', methods=['GET', 'POST'], endpoint='register')
def register_user():
    """Registra un nuevo usuario en el sistema."""
    if request.method == 'POST':
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
            cur.execute("""
                INSERT INTO usuario (nombre, correo, contraseña, role, idplan, fecha_creacion_plan) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nombre, correo, contraseña_hash, 'usuario', 1, fecha_creacion_plan))

            conn.commit()

            session['logueado'] = True
            session['idusuario'] = cur.lastrowid
            session['nombre'] = nombre
            session['role'] = 'usuario'
            session['username'] = nombre
            session['idplan'] = 1

            return redirect(url_for('routes.admin'))
        except Exception as e:
            conn.rollback()
            return render_template('register.html', message='Error en el registro. Inténtelo de nuevo más tarde.')
        finally:
            cur.close()
    return render_template('register.html')