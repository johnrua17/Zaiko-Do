from flask import Flask, render_template, redirect, url_for, request, flash
from flask import session
from flask_mysqldb import MySQL, MySQLdb
from datetime import datetime, timedelta

app = Flask(__name__ , template_folder="templates")

app.secret_key = "Zaikodo"


# Configuración de la conexión a la base de datos MySQL
app.config['MYSQL_HOST'] = 'XXXXXXXXX'
app.config['MYSQL_USER'] = 'XXXXXXXXX'
app.config['MYSQL_PASSWORD'] = 'XXXXXXXXX'
app.config['MYSQL_DB'] = 'XXXXXXXXX'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Inicialización de la extensión MySQL
mysql = MySQL(app)

@app.route('/login', methods=["GET", "POST"])
def login():
    return login_user()


def login_user():
 
    if request.method == 'POST':
         # Obtener y verificar el token de Turnstile
        # turnstile_token = request.form.get('cf-turnstile-response')
        # if not verify_turnstile_token(turnstile_token):
        #     logger.info('Fallo la verificación de Turnstile.')
        #     return render_template('login/index.html', error_message='Error en la verificación de seguridad. Inténtelo nuevamente.')


        correo = request.form['email']
        contraseña = request.form['password']

        # Crear un cursor para la base de datos MySQL
        cur = mysql.connection.cursor()

        # Ejecutar una consulta SQL para buscar un usuario con el correo proporcionado
        cur.execute('SELECT * FROM usuario WHERE correo = %s', [correo])
        account = cur.fetchone()

        # Si el usuario existe, verificar la contraseña
        if account:
            # Verificar si el usuario está bloqueado
            if account['bloqueado_hasta'] and account['bloqueado_hasta'].replace(tzinfo=ZONE_BOGOTA) > obtener_hora_actual_bogota():
                tiempo_restante = account['bloqueado_hasta'].replace(tzinfo=ZONE_BOGOTA) - obtener_hora_actual_bogota()
                minutos_restantes = int(tiempo_restante.total_seconds() / 60)
                error_message = f"Cuenta bloqueada por demasiados intentos fallidos. Inténtelo de nuevo en {minutos_restantes} minutos."
                # logger.warning(f'Intento de inicio de sesión fallido: {correo}. Cuenta bloqueada.')
                return render_template('login/index.html', error_message=error_message)

            # Si la contraseña es correcta, establecer la sesión
            if check_password_hash(account['contraseña'], contraseña):
                # Establecer la sesión de usuario marcándolo como logueado
                session['logueado'] = True
                session['idusuario'] = account['idusuario']
                session["nombre"] = account["nombre"]
                session['role'] = account['role']
                session['correo'] = account['correo']
                session['idplan'] = account['idplan']
                session['username'] = session["nombre"]

                # Restablecer intentos fallidos
                gestionar_intentos(correo, exito=True)
                # logger.info(f'Inicio de sesión exitoso: {correo}')
                return redirect(url_for('admin'))

            else:
                # Incrementar intentos fallidos
                gestionar_intentos(correo, exito=False)

                # logger.warning(f'Intento de inicio de sesión fallido: {correo}')
                error_message = "Credenciales incorrectas"
                return render_template('login/index.html', error_message=error_message)

        # Si el usuario no existe, no hacer nada y mostrar mensaje
        error_message = "El usuario no existe."
        # logger.warning(f'Usuario no encontrado: {correo}')
        return render_template('index.html', error_message=error_message)

    # Si la solicitud no es POST, redirigir a la página de inicio
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True , host="0.0.0.0", port=5000, threaded=True)
