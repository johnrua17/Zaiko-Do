from flask import Flask, render_template, redirect, url_for, request, flash
from werkzeug.security import check_password_hash, generate_password_hash
from flask import session
from flask_mysqldb import MySQL, MySQLdb
from datetime import datetime, timedelta
import pytz
import requests
import bleach
from flask_mail import Mail, Message
from flask import jsonify

app = Flask(__name__ , template_folder="templates")

app.secret_key = "Zaikodo"


# Configuración de la conexión a la base de datos MySQL
app.config['MYSQL_HOST'] = 'bb8xmknvzukpsmgzmsf2-mysql.services.clever-cloud.com'
app.config['MYSQL_USER'] = 'uh5cr91ugvcpsou7'
app.config['MYSQL_PASSWORD'] = 'BFXoblKJ8YszXDOyQSHx'
app.config['MYSQL_DB'] = 'bb8xmknvzukpsmgzmsf2'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Inicialización de la extensión MySQL
mysql = MySQL(app)

@app.route('/login', methods=["GET", "POST"])
def login():
    return login_user()


# Zona horaria de Bogotá
ZONE_BOGOTA = pytz.timezone('America/Bogota')

# Definir constantes para el manejo de intentos
MAX_INTENTOS = 3  # Máximo de intentos fallidos permitidos
TIEMPO_BLOQUEO_MINUTOS = 15  # Tiempo de bloqueo en minutos

# Función para obtener la hora actual en Bogotá
def obtener_hora_actual_bogota():
    return datetime.now(ZONE_BOGOTA)


# Función para gestionar los intentos de inicio de sesión
def gestionar_intentos(correo, exito=False):
    from app import mysql
    cur = mysql.connection.cursor()

    if exito:
        # Restablecer intentos fallidos si el login es exitoso
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

        # Verificar si el usuario ha alcanzado el máximo de intentos
        cur.execute("SELECT intentos_fallidos FROM usuario WHERE correo = %s", [correo])
        result = cur.fetchone()

        if result and result['intentos_fallidos'] >= MAX_INTENTOS:
            # Bloquear al usuario por un periodo determinado
            cur.execute("""
                UPDATE usuario 
                SET bloqueado_hasta = %s 
                WHERE correo = %s
            """, (obtener_hora_actual_bogota() + timedelta(minutes=TIEMPO_BLOQUEO_MINUTOS), correo))

    mysql.connection.commit()

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
                return render_template('index.html', error_message=error_message)

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
                return render_template('index.html', error_message=error_message)

        # Si el usuario no existe, no hacer nada y mostrar mensaje
        error_message = "El usuario no existe."
        # logger.warning(f'Usuario no encontrado: {correo}')
        return render_template('index.html', error_message=error_message)

    # Si la solicitud no es POST, redirigir a la página de inicio
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    return register_user()




def register_user():
    if request.method == 'POST':

        # Obtener y verificar el token de Turnstile
        # turnstile_token = request.form.get('cf-turnstile-response')
        # if not verify_turnstile_token(turnstile_token):
        #     logger.info('Fallo la verificación de Turnstile.')
        #     return render_template('login/register.html', message='Error en la verificación de seguridad. Inténtelo nuevamente.')


        nombre = bleach.clean(request.form['name'])
        correo = bleach.clean(request.form['email'])
        contraseña = request.form['password']

        # Obtener la zona horaria de Bogotá
        timezone_bogota = pytz.timezone('America/Bogota')
        fecha_creacion_plan = datetime.now(timezone_bogota)

        cur = mysql.connection.cursor()

        try:
            cur.execute('START TRANSACTION')

            cur.execute('SELECT * FROM usuario WHERE correo = %s', [correo])
            existing_user = cur.fetchone()

            if existing_user:
                return render_template('login/register.html', message='El correo ya está en uso.')

            contraseña_hash = generate_password_hash(contraseña)

            cur.execute('INSERT INTO usuario (nombre, correo, contraseña, role, idplan, fecha_creacion_plan, fecha_expiracion_plan) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                        (nombre, correo, contraseña_hash, 'usuario', 1, fecha_creacion_plan, None))

            id_usuario = cur.lastrowid

            mysql.connection.commit()

            session['logueado'] = True
            session['idusuario'] = id_usuario
            session['nombre'] = nombre
            session['role'] = 'usuario'
            session['username'] = nombre
            session['idplan'] = 1

            # enviar_correo_registro_exitoso(nombre, correo)
            # logger.info(f'Nuevo usuario registrado: {correo}')

            return redirect(url_for('admin'))

        except Exception as e:
            mysql.connection.rollback()
            
            return render_template('register.html', message='Error en el registro. Inténtelo de nuevo más tarde.')

        finally:
            cur.close()

    return render_template('register.html')

@app.route('/buscar_producto', methods=["POST"])
def buscar_producto():
    # Verificar si el usuario está autenticado
    if not session.get('idusuario'):
        return jsonify({"error": "Usuario no autenticado"}), 401

    # Obtener datos de la solicitud
    data = request.get_json()
    codigo_barras = data.get('codigo_barras')
    id_usuario_actual = session.get('idusuario')

    if not codigo_barras:
        return jsonify({"error": "Código de barras no proporcionado"}), 400

    try:
        # Usar la conexión de MySQL
        cur = mysql.connection.cursor()

        # Consultar el producto en la base de datos
        query = """
            SELECT Codigo_de_barras, Nombre, Descripcion, Precio_Valor, Precio_Costo, Cantidad, Categoria
            FROM productos
            WHERE Codigo_de_barras = %s AND id_usuario = %s
        """
        cur.execute(query, (codigo_barras, id_usuario_actual))
        producto = cur.fetchone()

        if not producto:
            return jsonify({"error": "Producto no encontrado"}), 200

        # Formatear la respuesta con los datos del producto
        return jsonify({
            "codigo": producto["Codigo_de_barras"],
            "nombre": producto["Nombre"],
            "descripcion": producto["Descripcion"],
            "precio": producto["Precio_Valor"],
            "precio_costo": producto["Precio_Costo"],
            "stock": producto["Cantidad"],
            "categoria": producto["Categoria"],
        })
    except Exception as e:
        print(f"Error al buscar el producto: {e}")  # Registro para depuración
        return jsonify({"error": "Error al buscar el producto"}), 500
    finally:
        cur.close()


@app.route('/admin', methods=["GET", "POST"])
def admin():
    saludo = session.get('saludo')
    username = session.get('username')
    idplan = session.get('idplan')
    id_usuario_actual = session.get('idusuario')

    if request.method == 'POST':
        codigo_barras = request.form.get('codigo_barras')


    # Renderizar la plantilla si no hay búsqueda
    return render_template('admin.html', saludo=saludo, username=username, idplan=idplan)

@app.route('/productos/agregar', methods=["GET", "POST"])
def agregar_producto():
    if request.method == 'POST':
        # Capturar los datos del formulario
        codigo_barras = bleach.clean(request.form['codigo_barras'])
        nombre = bleach.clean(request.form['nombre'])
        descripcion = bleach.clean(request.form['descripcion'])
        precio_valor = request.form['precio_valor']
        precio_costo = request.form['precio_costo']
        cantidad = request.form['cantidad']
        categoria = bleach.clean(request.form['categoria'])

        # Obtener el id del usuario actual desde la sesión
        id_usuario_actual = session.get('idusuario')
        cur = mysql.connection.cursor()

        cur.execute('SELECT idplan from usuario where idusuario = %s',(id_usuario_actual,))
        idplan = cur.fetchone()['idplan']
            
            # Si el idplan es 1 (plan gratuito), verificar el límite de productos
        if idplan == 1:
                # Obtener el límite de productos del plan gratuito
            cur.execute('SELECT limite_productos FROM planes WHERE idplan = %s', (idplan,))
            limite_productos = cur.fetchone()['limite_productos']

                # Contar cuántos productos tiene el usuario actualmente
            cur.execute('SELECT COUNT(*) AS total_productos FROM productos WHERE id_usuario = %s', (id_usuario_actual,))
            total_productos = cur.fetchone()['total_productos']

                # Si ha alcanzado el límite de productos, devolver un mensaje
            if total_productos >= limite_productos:
                return jsonify({'success': False, 'message': f'Has alcanzado el límite de {limite_productos} productos en el plan gratuito. Para tener productos ilimitados, adquiere cualquier plan.  Para adquirir un plan, ve a "Configuración" en el menú lateral, selecciona "Planes Disponibles" y elige el que más te guste.'})


        # Validar campos obligatorios
        if not (codigo_barras and nombre and precio_valor and precio_costo and cantidad and categoria):
            return render_template('formulario_productos.html', message='Todos los campos son obligatorios.')

        

        try:
            cur.execute('START TRANSACTION')

            # Validar si el código de barras ya existe
            cur.execute('SELECT * FROM productos WHERE Codigo_de_barras = %s AND id_usuario = %s', 
                        (codigo_barras, id_usuario_actual))
            existing_product = cur.fetchone()

            if existing_product:
                return render_template('formulario_productos.html', 
                                       message='El código de barras ya está registrado.')
                # print(message)

            # Insertar el producto
            cur.execute('INSERT INTO productos (id_usuario,Codigo_de_barras, Nombre, Descripcion, Precio_Valor, Precio_Costo, Cantidad, Categoria) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', 
                        ( id_usuario_actual,codigo_barras, nombre, descripcion, precio_valor, precio_costo, cantidad, categoria))

            mysql.connection.commit()

            return render_template('formulario_productos.html', 
                                   message='Producto agregado exitosamente.')

        except Exception as e:
            mysql.connection.rollback()
            print(f"Error al agregar el producto: {e}")  # Depuración
            return render_template('formulario_productos.html', 
                                   message='Error al agregar el producto. Inténtelo más tarde.')

        finally:
            cur.close()

    return render_template('formulario_productos.html')

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for('login'))
if __name__ == '__main__':
    app.run(debug=True , host="0.0.0.0", port=5000, threaded=True)

@app.route('/buscar_productos', methods=['POST'])
def buscar_productos():
    # Verificar si el usuario está autenticado
    if not session.get('idusuario'):
        return jsonify({"error": "Usuario no autenticado"}), 401

    # Obtener los datos enviados en la solicitud
    data = request.get_json()
    termino_busqueda = data.get('termino_busqueda')
    id_usuario_actual = session.get('idusuario')

    if not termino_busqueda:
        return jsonify({"error": "No se proporcionó un término de búsqueda"}), 400

    try:
        cur = mysql.connection.cursor()

        # Consulta SQL para buscar productos que coincidan con el término de búsqueda
        query = """
        SELECT Codigo_de_barras, Nombre, Descripcion, Precio_Valor, Cantidad, Categoria
        FROM productos
        WHERE id_usuario = %s AND 
              (Nombre LIKE %s OR Categoria LIKE %s OR Codigo_de_barras LIKE %s)
        """
        termino_busqueda = f"%{termino_busqueda}%"  # Agregar comodines para la búsqueda parcial
        cur.execute(query, (id_usuario_actual, termino_busqueda, termino_busqueda, termino_busqueda))
        productos = cur.fetchall()
        cur.close()

        if not productos:
            return jsonify({"error": "No se encontraron productos"}), 200

        return jsonify({"productos": productos})
    except Exception as e:
        print(f"Error al buscar productos: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500