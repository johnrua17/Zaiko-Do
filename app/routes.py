from flask import Blueprint, render_template, redirect, url_for, request, session, jsonify
from app.auth import login_user, register_user
from app.utils import obtener_hora_actual_bogota, login_required
from app.database import get_connection
from flask_mysqldb import MySQL
from io import BytesIO
from openpyxl import Workbook
from flask import send_file
from flask import make_response
import bleach
import pytz
import uuid
import hashlib
import hmac
from datetime import datetime, timedelta
import pdfkit
import os
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from app.auth import validar_sesion  # Importar el decorador
from .reporte_ventas import query_reportes
import requests # Para el chatbot
import google.generativeai as genai # Para el chatbot
from app.ventas.devolucion import devolucion_venta
from app.clientes.clientestop import clientestop
from app.clientes.editarcliente import editarcliente
from app.ventas.detallesventa import detallesventa
from app.clientes.eliminarcliente import eliminarcliente
from app.ventas.ventas import obtenerventa,venta
from app.ventas.ventascredito import ventacredito
load_dotenv(dotenv_path='../.env')
from app.chatbot import get_message
TEMPLATES_DIR = '../../templates'   
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

# Crear un Blueprint para las rutas
routes_blueprint = Blueprint('routes', __name__)

mysql = None # Inicialización de MySQL

def init_mysql(app):
    global mysql
    mysql = MySQL(app)

# Registrar el filtro en el contexto de la aplicación
@routes_blueprint.app_template_filter('format')
def format_number(value, separator=','):
    if value is None:
        return ""
    try:
        # Formatear el número con separadores de miles
        return f"{int(value):,}".replace(",", separator)
    except (ValueError, TypeError):
        return value  # Si no es un número, devolver el valor original

@routes_blueprint.route('/login', methods=["GET", "POST"])
def login():
    return login_user()

@routes_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    return register_user()

from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

@routes_blueprint.route('/validar_otp/<token>', methods=['GET', 'POST'])
def validar(token):
    try:
        s = URLSafeTimedSerializer(os.getenv("SECRET_KEY"))
        correo = s.loads(token, salt='email-confirm', max_age=86400)  # Token válido por 24 horas
    except SignatureExpired:
        return render_template('login/validar_otp.html', message='El enlace de verificación ha expirado.')
    except BadSignature:
        return render_template('login/validar_otp.html', message='El enlace de verificación no es válido.')

    if request.method == 'POST':
        otp = request.form.get('otp')
        if not otp:
            return render_template('login/validar_otp.html', token=token, message='Por favor, proporciona el OTP.')

        conn = get_connection()
        cur = conn.cursor()

        try:
            # Verificar si el OTP es correcto
            cur.execute('SELECT * FROM usuario WHERE correo = %s AND token_verificacion = %s AND token_expiracion > NOW()', (correo, otp))
            usuario = cur.fetchone()

            if not usuario:
                return render_template('login/validar_otp.html', token=token, message='OTP incorrecto o expirado.')

            # Actualizar la columna verificado
            cur.execute('UPDATE usuario SET verificado = %s WHERE correo = %s', (True, correo))
            conn.commit()

            return redirect(url_for('routes.admin'))
        except Exception as e:
            conn.rollback()
            print(e)
            return render_template('login/validar_otp.html', token=token, message='Error al verificar el OTP. Inténtelo de nuevo más tarde.')
        finally:
            cur.close()
    return render_template('login/validar_otp.html', token=token)

@routes_blueprint.route('/')
def home():
    return render_template('home.html')

@routes_blueprint.route('/home')
def home_redirect():
    return redirect(url_for('routes.home'))

@routes_blueprint.route('/avisoPrivacidad')
def cookies():
    return render_template('cookies.html')

@routes_blueprint.route('/buscar_productos', methods=["POST"])
def buscar_producto():
    if not session.get('idusuario'):
        return jsonify({"error": "Usuario no autenticado"}), 401

    data = request.get_json()
    termino_busqueda = data.get('termino_busqueda')  # Recibe el término de búsqueda (Codigo de Barras) desde el cliente.
    id_usuario_actual = session.get('idusuario')

    if not termino_busqueda:
        return jsonify({"error": "No se proporcionó un término de búsqueda"}), 400

    try:
        cur = mysql.connection.cursor()

        # Consulta que busca por código de barras o por nombre del producto (usando LIKE para búsqueda parcial)
        query = """
            SELECT Codigo_de_barras, Nombre, Descripcion, Precio_Valor,Precio_Costo, Cantidad, Categoria
            FROM productos
            WHERE (Codigo_de_barras = %s) AND id_usuario = %s
        """
        # Agregar comodines para búsqueda parcial en el nombre
        like_term = f"%{termino_busqueda}%"
        cur.execute(query, (termino_busqueda, like_term, id_usuario_actual))
        productos = cur.fetchall()

        if not productos:
            return jsonify({"error": "No se encontraron productos"}), 200

        # Convertir los resultados a un formato JSON
        productos_json = [
            {
                "Codigo_de_barras": prod["Codigo_de_barras"],
                "Nombre": prod["Nombre"],
                "Descripcion": prod["Descripcion"],
                "Precio_Valor": prod["Precio_Valor"],
                "Precio_Costo": prod["Precio_Costo"],
                "Cantidad": prod["Cantidad"],
                "Categoria": prod["Categoria"]
            }
            for prod in productos
        ]

        return jsonify({"productos": productos_json})
    except Exception as e:
        print(f"Error al buscar productos: {e}")
        return jsonify({"error": "Error al buscar productos"}), 500
    finally:
        cur.close()


@routes_blueprint.route('/buscar_productoss', methods=["POST"])

def buscar_productos():
    if not session.get('idusuario'):
        return jsonify({"error": "Usuario no autenticado"}), 401

    data = request.get_json()
    termino_busqueda = data.get('termino_busqueda')  # Recibe el término de búsqueda desde el cliente.
    id_usuario_actual = session.get('idusuario')

    if not termino_busqueda:
        return jsonify({"error": "No se proporcionó un término de búsqueda"}), 400

    try:
        cur = mysql.connection.cursor()

        # Consulta que busca por múltiples columnas usando LIKE
        query = """
            SELECT Codigo_de_barras, Nombre, Descripcion, Precio_Valor, Precio_Costo, Cantidad, Categoria
            FROM productos
            WHERE (Nombre LIKE %s OR Descripcion LIKE %s OR Categoria LIKE %s)
              AND id_usuario = %s
        """
        # Agregar comodines para búsqueda parcial
        like_term = f"%{termino_busqueda}%"
        cur.execute(query, (like_term, like_term, like_term, id_usuario_actual))
        productos = cur.fetchall()

        if not productos:
            return jsonify({"error": "No se encontraron productos"}), 200

        # Convertir los resultados a un formato JSON
        productos_json = [
            {
                "Codigo_de_barras": prod["Codigo_de_barras"],
                "Nombre": prod["Nombre"],
                "Descripcion": prod["Descripcion"],
                "Precio_Valor": prod["Precio_Valor"],
                "Precio_Costo": prod["Precio_Costo"],
                "Stock": prod["Cantidad"],
                "Categoria": prod["Categoria"]
                
            }
            for prod in productos
        ]

        return jsonify({"productos": productos_json})
    except Exception as e:
        print(f"Error al buscar productos: {e}")
        return jsonify({"error": "Error al buscar productos"}), 500
    finally:
        cur.close()


@routes_blueprint.route('/productos/listar', methods=["GET"])
@login_required
def listar_productos():
    # Verificar si el usuario está autenticado
    if not session.get('idusuario'):
        return redirect(url_for('auth.login'))


    id_usuario_actual = session.get('idusuario')


    try:
       
        cur = mysql.connection.cursor()


        # Obtener todos los productos del usuario actual
        query = """
        SELECT Codigo_de_barras, Nombre, Descripcion, Precio_Valor, Cantidad, Categoria
        FROM productos
        WHERE id_usuario = %s
        """
        cur.execute(query, (id_usuario_actual,))
        productos = cur.fetchall()
        cur.close()


        # Renderizar la plantilla con los productos
        return render_template('productos/listar_productos.html', productos=productos)
    except Exception as e:
        print(f"Error al listar productos: {e}")
        return render_template('productos/listar_productos.html', error_message="Error al cargar los productos.")


@routes_blueprint.route('/productos/editar/<codigo_barras>', methods=['GET', 'POST'])
def editar_producto(codigo_barras):
    id_usuario_actual = session.get('idusuario')  # Obtener ID del usuario actual


    # Crear cursor para consultas
    cur = mysql.connection.cursor()


    # Consultar el producto con el código de barras
    cur.execute('SELECT * FROM productos WHERE Codigo_de_barras = %s AND id_usuario = %s',
                (codigo_barras, id_usuario_actual))
    producto = cur.fetchone()


    # Si no se encuentra el producto, devolver un error
    if not producto:
        return "Producto no encontrado, que va a editar payaso", 404


    if request.method == 'POST':
        # Capturar los datos del formulario
        codigo_barras = bleach.clean(request.form['codigo_barras'])
        nombre = bleach.clean(request.form['nombre'])
        descripcion = bleach.clean(request.form['descripcion'])
        precio_valor = request.form['precio_valor']
        precio_costo = request.form['precio_costo']
        cantidad = request.form['cantidad']
        categoria = bleach.clean(request.form['categoria'])
        try:
            cur.execute('START TRANSACTION')


            # Validar si el producto con el código de barras existe
            cur.execute('SELECT * FROM productos WHERE Codigo_de_barras = %s AND id_usuario = %s',
                        (codigo_barras, id_usuario_actual))
            existing_product = cur.fetchone()


            if not existing_product:
                return render_template('formulario_productos.html',
                                    message='El producto con este código de barras no existe.')


            # Actualizar el producto existente
            cur.execute('UPDATE productos SET Nombre = %s, Descripcion = %s, Precio_Valor = %s, Precio_Costo = %s, Cantidad = %s, Categoria = %s WHERE Codigo_de_barras = %s AND id_usuario = %s',
                        (nombre, descripcion, precio_valor, precio_costo, cantidad, categoria, codigo_barras, id_usuario_actual))


            mysql.connection.commit()


            return redirect(url_for('routes.listar_productos'))


        except Exception as e:
            mysql.connection.rollback()
            print(f"Error al editar el producto: {e}")  # Depuración
            return redirect(url_for('routes.listar_productos'))


        finally:
            cur.close()




   


    # Renderizar el formulario con los datos actuales del producto
    return render_template('productos/editar_producto.html', producto=producto)


@routes_blueprint.route('/productos/eliminar/<codigo_barras>', methods=['GET'])
def eliminar_producto(codigo_barras):
    id_usuario_actual = session.get('idusuario')  # Obtener ID del usuario actual


    # Crear cursor para consultas
    cur = mysql.connection.cursor()


    try:
        # Iniciar transacción
        cur.execute('START TRANSACTION')


        # Consultar si el producto existe
        cur.execute('SELECT * FROM productos WHERE Codigo_de_barras = %s AND id_usuario = %s',
                    (codigo_barras, id_usuario_actual))
        producto = cur.fetchone()


        if not producto:
            return render_template('formulario_productos.html', message='Producto no encontrado.')


        # Eliminar el producto de la base de datos
        cur.execute('DELETE FROM productos WHERE Codigo_de_barras = %s AND id_usuario = %s',
                    (codigo_barras, id_usuario_actual))


        # Confirmar la eliminación
        mysql.connection.commit()


        return redirect(url_for('routes.listar_productos'))


    except Exception as e:
        # Si ocurre un error, hacer rollback y mostrar mensaje
        mysql.connection.rollback()
        print(f"Error al eliminar el producto: {e}")  # Depuración
        return redirect(url_for('routes.listar_productos'))


    finally:
        cur.close()

@routes_blueprint.route('/descargar_productos', methods=['POST'])
def descargar_productos():
    id_usuario = session.get('idusuario')
    username = session.get('username')
    formato = request.args.get('format', 'xlsx')  # Por defecto, Excel

    if not id_usuario:
        return jsonify({"error": "Usuario no autenticado"}), 401

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT Codigo_de_barras, Nombre, Descripcion, Precio_Valor, Precio_Costo, Cantidad, Categoria 
            FROM productos 
            WHERE id_usuario = %s
        """, (id_usuario,))
        productos = cur.fetchall()

        if formato == 'xlsx':
            # Generar archivo Excel
            output = BytesIO()
            wb = Workbook()
            ws = wb.active
            ws.title = "Productos"
            encabezados = ["Código de Barras", "Nombre", "Descripción", "Precio Valor", "Precio Costo", "Cantidad", "Categoría"]
            ws.append(encabezados)

            for producto in productos:
                ws.append([
                    producto["Codigo_de_barras"],
                    producto["Nombre"],
                    producto["Descripcion"],
                    producto["Precio_Valor"],
                    producto["Precio_Costo"],
                    producto["Cantidad"],
                    producto["Categoria"]
                ])

            wb.save(output)
            output.seek(0)
            nombre_archivo = f"productos_{username}.xlsx"
            return send_file(output, as_attachment=True, download_name=nombre_archivo)

        elif formato == 'pdf':
            # Generar archivo PDF
            html = """
            <html>
            <head>
                <style>
                    table {
                        border-collapse: collapse;
                        width: 100%;
                    }
                    th, td {
                        border: 1px solid #ddd;
                        padding: 8px;
                    }
                    th {
                        background-color: #f2f2f2;
                        text-align: left;
                    }
                </style>
            </head>
            <body>
                <h2>Lista de Productos</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Código de Barras</th>
                            <th>Nombre</th>
                            <th>Descripción</th>
                            <th>Precio Valor</th>
                            <th>Precio Costo</th>
                            <th>Cantidad</th>
                            <th>Categoría</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for producto in productos:
                html += f"""
                <tr>
                    <td>{producto["Codigo_de_barras"]}</td>
                    <td>{producto["Nombre"]}</td>
                    <td>{producto["Descripcion"]}</td>
                    <td>${producto["Precio_Valor"]}</td>
                    <td>${producto["Precio_Costo"]}</td>
                    <td>{producto["Cantidad"]}</td>
                    <td>{producto["Categoria"]}</td>
                </tr>
                """
            html += """
                    </tbody>
                </table>
            </body>
            </html>
            """
            
            wkhtmltopdf_path = os.getenv('WKHTMLTOPDF_PATH')
            print("WKHTMLTOPDF_PATH:", wkhtmltopdf_path)
            config_pdfkit = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)

            pdf = pdfkit.from_string(html, False, configuration=config_pdfkit)
            pdf_output = BytesIO(pdf)
            pdf_output.seek(0)
            
            nombre_archivo = f"productos_{username}.pdf"
            return send_file(pdf_output, as_attachment=True, download_name=nombre_archivo)

        else:
            return jsonify({"error": "Formato no soportado"}), 400

    except Exception as e:
        print(f"Error al generar el archivo: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@routes_blueprint.route('/admin', methods=["GET", "POST"])
@validar_sesion
@login_required
def admin():
    from app import mysql
    id_usuario_actual = session.get('idusuario')
    print("este es el id de usuario")
    print(id_usuario_actual)
    saludo = session.get('saludo')
    username = session.get('username')
    idplan = session.get('idplan')
    
    return render_template('admin.html', saludo=saludo, username=username, idplan=idplan)

@routes_blueprint.route('/productos/agregar', methods=["GET", "POST"])
@login_required
def agregar_producto():
    from app import mysql
    if request.method == 'POST':
        codigo_barras = bleach.clean(request.form['codigo_barras'])
        nombre = bleach.clean(request.form['nombre'])
        descripcion = bleach.clean(request.form['descripcion'])
        precio_valor = request.form['precio_valor']
        precio_costo = request.form['precio_costo']
        cantidad = request.form['cantidad']
        categoria = bleach.clean(request.form['categoria'])
        id_usuario_actual = session.get('idusuario')

        cur = mysql.connection.cursor()
        cur.execute('SELECT idplan from usuario where idusuario = %s', (id_usuario_actual,))
        idplan = cur.fetchone()['idplan']

        if idplan == 1:
            cur.execute('SELECT limite_productos FROM planes WHERE idplan = %s', (idplan,))
            limite_productos = cur.fetchone()['limite_productos']
            cur.execute('SELECT COUNT(*) AS total_productos FROM productos WHERE id_usuario = %s', (id_usuario_actual,))
            total_productos = cur.fetchone()['total_productos']

            if total_productos >= limite_productos:
                return jsonify({'success': False, 'message': f'Has alcanzado el límite de {limite_productos} productos.'})

        if not (codigo_barras and nombre and precio_valor and precio_costo and cantidad and categoria):
            return render_template('productos/formulario_productos.html', message='Todos los campos son obligatorios.')

        try:
            cur.execute('START TRANSACTION')
            cur.execute('SELECT * FROM productos WHERE Codigo_de_barras = %s AND id_usuario = %s', 
                        (codigo_barras, id_usuario_actual))
            if cur.fetchone():
                return render_template('productos/formulario_productos.html', message='El código de barras ya está registrado.')

            cur.execute('INSERT INTO productos (id_usuario,Codigo_de_barras, Nombre, Descripcion, Precio_Valor, Precio_Costo, Cantidad, Categoria) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', 
                        (id_usuario_actual, codigo_barras, nombre, descripcion, precio_valor, precio_costo, cantidad, categoria))
            mysql.connection.commit()
            return render_template('productos/formulario_productos.html', message='Producto agregado exitosamente.')
        except Exception as e:
            mysql.connection.rollback()
            print(f"Error al agregar el producto: {e}")
            return render_template('productos/formulario_productos.html', message='Error al agregar el producto.')
        finally:
            cur.close()

    return render_template('productos/formulario_productos.html')

@routes_blueprint.route("/logout", methods=["POST"])
def logout():
    """Cierra la sesión del usuario."""
    try:
        if 'logueado' in session:
            conn = get_connection()
            cur = conn.cursor()
            # Limpiar el session_id en la base de datos
            cur.execute("""
                UPDATE usuario
                SET session_id = NULL
                WHERE idusuario = %s
            """, [session['idusuario']])
            conn.commit()
            cur.close()
            session.clear()
            return redirect(url_for('routes.login'))
        
        session.clear()
        return redirect(url_for('routes.login'))
    except Exception as e:
        print(f"Error al cerrar sesión: {e}")
        return redirect(url_for('routes.login'))


@routes_blueprint.route('/terminos_condiciones', methods=['GET'], endpoint='terminos_condiciones')
def terminos_condiciones():
    """Muestra los términos y condiciones."""
    return render_template('terminos_condiciones.html')

@routes_blueprint.route('/inventario', methods=['GET'], endpoint='inventario')
@login_required 
def inventario():
    """Página para gestionar el inventario."""
    if not session.get('idusuario'):
        return redirect(url_for('routes.login'))  # O el mecanismo que uses para autenticación
    id_usuario = session.get('idusuario')
    cur = mysql.connection.cursor()
    query = """
        SELECT Codigo_de_barras, Nombre, Descripcion, Precio_Valor, Cantidad, Categoria
        FROM productos
        WHERE id_usuario = %s
    """
    cur.execute(query, (id_usuario,))
    productos = cur.fetchall()
    cur.close()
    return render_template('inventario/inventario.html', productos=productos)

@routes_blueprint.route('/clientes', methods=['GET'], endpoint='clientes')
@login_required 
def clientes():
    """Página para gestionar los clientes."""
    if not session.get('idusuario'):
        return redirect(url_for('routes.login'))  # Redirigir si no está autenticado
    
    id_usuario = session.get('idusuario')
    cur = mysql.connection.cursor()
    query = """
        SELECT idcliente, nombre, identificacion, contacto, fecha_registro
        FROM clientes
        WHERE idusuario = %s
    """
    cur.execute(query, (id_usuario,))
    clientes = cur.fetchall()
    cur.close()
    
    return render_template('clientes/clientes.html', clientes=clientes)


@routes_blueprint.route('/clientes/nuevo', methods=['POST'], endpoint='agregar_cliente')
def agregar_cliente():
    """Agregar un nuevo cliente."""
    if not session.get('idusuario'):
        return jsonify({'error': 'No autenticado'}), 401
    
    data = request.json
    nombre = data.get('nombre')
    identificacion = data.get('identificacion')
    contacto = data.get('contacto')
    id_usuario = session.get('idusuario')
    
    cur = mysql.connection.cursor()
    query = """
        INSERT INTO clientes (nombre, identificacion, contacto, fecha_registro, idusuario)
        VALUES (%s, %s, %s, NOW(), %s)
    """
    cur.execute(query, (nombre, identificacion, contacto, id_usuario))
    mysql.connection.commit()
    cur.close()
    
    return jsonify({'message': 'Cliente agregado correctamente'}), 201

@routes_blueprint.route('/configuracion', methods=['GET'], endpoint='configuracion')
def configuracion():
    """Página para gestionar la configuración."""
    return render_template('configuracion/configuracion.html')


@routes_blueprint.route('/planes', methods=['GET'])
@login_required 
def planes():

    nombre = session.get('nombre')
    id_usuario = session.get('idusuario')

    try:
        cur = mysql.connection.cursor()

        # Obtener información del plan del usuario si está autenticado
        if id_usuario:
            cur.execute('SELECT idplan, fecha_expiracion_plan FROM usuario WHERE idusuario = %s', [id_usuario])
            user_info = cur.fetchone()
            if user_info:
                id_plan = user_info['idplan']
                fecha_expiracion_plan = user_info['fecha_expiracion_plan']
        else:
            id_plan = None
            fecha_expiracion_plan = None

        # Obtener todos los planes con detalles adicionales
        cur.execute('SELECT idplan, nombre, precio, duracion FROM planes')
        planes = cur.fetchall()

        query_fecha_inicio_plan_a_devolver = ("""SELECT fecha_inicio
                    FROM historial_planes_usuarios
                    WHERE idusuario = %s
                    ORDER BY fecha_inicio DESC
                    LIMIT 1;""")

        cur.execute(query_fecha_inicio_plan_a_devolver, (id_usuario,))
        fecha_inicio_plan_a_devolver = cur.fetchone()

        timezone = pytz.timezone('America/Bogota')
        fecha_actual = datetime.now(timezone)

        puede_pedir_devolucion = False

        # Verifica si se obtuvo una fecha de inicio del plan, o sea la fecha del plan del que quiere devolucion, en test no va a funcionar porque necesito comprar un plan para eso
        if fecha_inicio_plan_a_devolver:
            fecha_inicio = fecha_inicio_plan_a_devolver[0]  
            diferencia_horas = (fecha_actual - fecha_inicio).total_seconds() / 3600

            # Si no han pasado más de 24 horas
            if diferencia_horas < 24:
                puede_pedir_devolucion = True
        

        
        #puede_pedir_devolucion = True #esto es solo para testear, no deberia definirla como true
        ha_hecho_solicitud = True

        #verifica si ya ha hecho una solicitud de devolucion y en que estado esta dicha solicitud
        query_ha_hecho_solicitud = ("""SELECT estado 
                                    FROM solicitudes_devolucion
                                    WHERE idusuario = %s 
                                    AND idplan_comprado = %s
                                    ORDER BY fecha_solicitud DESC
                                    LIMIT 1;
                                    """)

        cur.execute(query_ha_hecho_solicitud, (id_usuario, id_plan))
        ha_hecho_solicitud_result = cur.fetchone()

        if ha_hecho_solicitud_result is None:
            ha_hecho_solicitud = False
        else:
            ha_hecho_solicitud = ha_hecho_solicitud_result['estado']

        print(f"ha hecho devolucion es {ha_hecho_solicitud}")
        print(f"el idplan de este usuario es {id_plan}")
            # Enviar datos a la plantilla
        return render_template('configuracion/planes.html', planes=planes, nombre=nombre, plan_actual=id_plan, fecha_expiracion_plan=fecha_expiracion_plan, puede_pedir_devolucion=puede_pedir_devolucion, ha_hecho_solicitud=ha_hecho_solicitud)

    except Exception as e:
        print("esta mierda da error")
        return render_template('configuracion/planes.html', message=f'Error: {str(e)}')
    finally:
        cur.close()



@routes_blueprint.route('/suscribir/<int:idplan>', methods=['GET'])
def suscribir(idplan):
    
    id_usuario = session.get('idusuario')
    # correo_usuario = session.get('correo')
    if not id_usuario:
            return redirect(url_for('auth.login')) # Redirigir al login si el usuario no está autenticado

    cur = mysql.connection.cursor()
    cur.execute('SELECT correo FROM usuario WHERE idusuario= %s', [id_usuario])
    correo_usuario=  cur.fetchone()['correo']
    
    # Obtener la hora actual en Bogotá
    bogota_tz = pytz.timezone('America/Bogota')
    fecha_actual = datetime.now(bogota_tz)

    # fecha_actual = obtener_hora_actual_bogota()

    # Verificar los últimos 5 tokens creados para este usuario
    cur = mysql.connection.cursor()
    cur.execute('SELECT idplan, estado, token, fecha_expiracion FROM suscripciones WHERE idusuario = %s ORDER BY fecha_creacion DESC LIMIT 5', (id_usuario,))
    suscripciones = cur.fetchall()

    for suscripcion in suscripciones:
        if suscripcion['idplan'] == idplan:
            # Comprobar el estado del token
            if suscripcion['estado'] in ['aprobado', 'rechazado']:
                continue

            # Convertir fecha_expiracion a zona horaria Bogotá si no tiene información de zona horaria
            fecha_expiracion = suscripcion['fecha_expiracion']
            if fecha_expiracion and fecha_expiracion.tzinfo is None:
                fecha_expiracion = bogota_tz.localize(fecha_expiracion)

            # Comprobar si la fecha de expiración ha pasado
            if fecha_expiracion and fecha_actual > fecha_expiracion:
                continue

            # Si el estado es pendiente y la fecha de expiración no ha pasado, usar el token existente
            if suscripcion['estado'] == 'pendiente' and fecha_expiracion and fecha_actual <= fecha_expiracion:
                return redirect(url_for('routes.detalle_plan', token=suscripcion['token']))

    # Generar un nuevo token si no se encontró uno válido
    token = str(uuid.uuid4())
    fecha_creacion_str = fecha_actual.strftime('%Y-%m-%d %H:%M:%S')
    fecha_expiracion = fecha_actual + timedelta(minutes=15)
    fecha_expiracion_str = fecha_expiracion.strftime('%Y-%m-%d %H:%M:%S')

    # Guardar el nuevo token en la base de datos
    cur.execute('INSERT INTO suscripciones (idusuario, correo, idplan, token, fecha_creacion, fecha_expiracion) VALUES (%s, %s, %s, %s, %s, %s)',
                (id_usuario, correo_usuario, idplan, token, fecha_creacion_str, fecha_expiracion_str))
    mysql.connection.commit()

    # Redirigir a la página de detalles del plan con el token en la URL
    return redirect(url_for('routes.detalle_plan', token=token))

@routes_blueprint.route('/detalle_plan/<token>', methods=['GET'])
def detalle_plan(token):
    cur = mysql.connection.cursor()
    cur.execute('SELECT p.nombre, p.precio,p.duracion, s.token, s.correo, s.fecha_expiracion FROM suscripciones s JOIN planes p ON s.idplan = p.idplan WHERE s.token = %s', [token])
    suscripcion = cur.fetchone()

    if not suscripcion:
        return 'Token inválido o expirado.', 404

    # Obtener la hora actual en Bogotá, Colombia
    # bogota_tz = pytz.timezone('America/Bogota')
    # hora_actual = datetime.now(bogota_tz)
    hora_actual= obtener_hora_actual_bogota()
    hora_actual_str = hora_actual.strftime('%Y-%m-%d %H:%M:%S')
    print("Hora actual en Bogotá:", hora_actual_str)

    # La fecha de expiración ya está en la hora de Bogotá
    fecha_expiracion_bogota = suscripcion['fecha_expiracion']
    fecha_expiracion_bogota_str = fecha_expiracion_bogota.strftime('%Y-%m-%d %H:%M:%S')
    # print("Fecha de expiración en Bogotá:", fecha_expiracion_bogota_str)

    # Comparar la fecha de expiración con la hora actual
    if fecha_expiracion_bogota_str <= hora_actual_str:
        return 'Token inválido o expirado.', 404

    # Debes tener tu secreto de integridad configurado
    secreto_integridad = "prod_integrity_HuFn5nkn0F1LVkpJWZuIU1m3fUdznjCK"

    # Convertir el precio a centavos
    precio_centavos = int(suscripcion['precio'] * 100)

    # Construye la cadena para el hash
    cadena_concatenada = f"{suscripcion['token']}{precio_centavos}COP{secreto_integridad}"

    # Calcula el hash SHA-256
    integrity_hash = hashlib.sha256(cadena_concatenada.encode()).hexdigest()

    return render_template('configuracion/detalle_plan.html', suscripcion=suscripcion, integrity_hash=integrity_hash, precio_centavos=precio_centavos)




def validar_firma(signature, event_data, secreto_eventos, timestamp):
    """
    Valida la firma del evento usando el checksum y el secreto proporcionados.

    :param signature: Diccionario con la firma del evento.
    :param event_data: Datos del evento recibidos.
    :param secreto_eventos: Secreto de eventos para verificar la firma.
    :param timestamp: Timestamp del evento.
    :return: True si la firma es válida, False en caso contrario.
    """

    # Extraer propiedades de la firma
    properties = signature.get('properties', [])
    checksum_proporcionado = signature.get('checksum', '')

    # Obtener los valores de los datos del evento
    transaction_id = event_data.get('transaction', {}).get('id', '')
    transaction_status = event_data.get('transaction', {}).get('status', '')
    transaction_amount_in_cents = event_data.get('transaction', {}).get('amount_in_cents', '')

    # Imprimir las variables para seguimiento
    # print(f"Transaction ID: {transaction_id}")
    # print(f"Transaction Status: {transaction_status}")
    # print(f"Transaction Amount in Cents: {transaction_amount_in_cents}")
    # print(f"Timestamp: {timestamp}")
    # print(f"Secret: {secreto_eventos}")

    # Construir la cadena para el hash usando f-strings
    cadena_concatenada = f"{transaction_id}{transaction_status}{transaction_amount_in_cents}{timestamp}{secreto_eventos}"

    # Imprimir la cadena concatenada para seguimiento
    # print(f"Cadena Concatenada: {cadena_concatenada}")

    # Calcular el checksum esperado
    checksum_calculado = hashlib.sha256(cadena_concatenada.encode()).hexdigest()
    # print(f"Checksum Calculado: {checksum_calculado}")

    # Comparar el checksum calculado con el proporcionado
    return hmac.compare_digest(checksum_calculado, checksum_proporcionado)


@routes_blueprint.route('/pagos_wompi', methods=['POST'])
def actualizar_estado():
    data = request.get_json()
    secreto_eventos = "prod_events_cLkaC4Xb6f7iEiResaBK7FmKWxFDa1g3"

    # Verificar si la solicitud contiene datos suficientes
    if 'data' not in data or 'transaction' not in data['data']:
        return jsonify({'success': False, 'message': 'Datos insuficientes'}), 400

    # Verificar la firma
    signature = data.get('signature', {})
    event_data = data['data']
    # Obtener el timestamp
    timestamp = data.get('timestamp', '')
    if not validar_firma(signature, event_data, secreto_eventos, timestamp):
        return jsonify({'success': False, 'message': 'Firma no válida'}), 400

    transaction = data['data']['transaction']
    reference = transaction.get('reference')
    status = transaction.get('status')
    finalized_at = transaction.get('finalized_at')
    transaction_amount_in_cents = event_data.get('transaction', {}).get('amount_in_cents', '')

    # Verificar si se recibieron los datos necesarios
    if not reference or not status or not finalized_at:
        return jsonify({'success': False, 'message': 'Datos de transacción incompletos'}), 400

    # Parsear la fecha finalized_at de Wompi
    try:
        fecha_finalizada = datetime.strptime(finalized_at, "%Y-%m-%dT%H:%M:%S.%fZ")
        # Convertir a la zona horaria de Bogotá
        timezone_bogota = pytz.timezone('America/Bogota')
        fecha_finalizada_bogota = fecha_finalizada.astimezone(timezone_bogota)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al parsear la fecha: {str(e)}'}), 400

    # Actualizar la base de datos según el estado de la transacción
    cur = mysql.connection.cursor()

    try:
        if status == 'APPROVED':
            # Actualizar estado en suscripciones
            cur.execute("UPDATE suscripciones SET estado='aprobado' WHERE token=%s", [reference])

            # Obtener información de la suscripción aprobada
            cur.execute("SELECT idusuario, idplan FROM suscripciones WHERE token=%s", [reference])
            suscripcion_info = cur.fetchone()
            if suscripcion_info:
                idusuario = suscripcion_info['idusuario']
                idplan = suscripcion_info['idplan']

                # Guardar información actual del plan en historial_planes
                cur.execute("INSERT INTO historial_planes (idusuario, idplan_anterior, fecha_creacion_plan_anterior, fecha_expiracion_plan_anterior) "
                            "SELECT idusuario, idplan, fecha_creacion_plan, fecha_expiracion_plan FROM usuario WHERE idusuario=%s",
                            [idusuario])

                # Obtener la duración del plan desde la base de datos
                cur.execute("SELECT duracion FROM planes WHERE idplan=%s", [idplan])
                duracion_plan = cur.fetchone()
                if duracion_plan and 'duracion' in duracion_plan:
                    try:
                        duracion = int(duracion_plan['duracion'])
                        # Calcular fecha de expiración según la duración del plan
                        fecha_expiracion = fecha_finalizada_bogota + timedelta(days=duracion)
                        # Actualizar idplan y fechas en tabla usuario
                        cur.execute("UPDATE usuario SET idplan=%s, fecha_creacion_plan=%s, fecha_expiracion_plan=%s WHERE idusuario=%s",
                                    [idplan, fecha_finalizada_bogota, fecha_expiracion, idusuario])


                        # Obtener información del plan
                        cur.execute("SELECT nombre, precio FROM planes WHERE idplan=%s", [idplan])
                        plan_info = cur.fetchone()

                        # Obtener información del usuario y plan para el correo
                        cur.execute("SELECT nombre,correo FROM usuario WHERE idusuario=%s", [idusuario])
                        usuario_info = cur.fetchone()
                        if plan_info:
                            nombre_plan = plan_info['nombre']
                            precio_plan = int(plan_info['precio'])
                            # Registrar en el historial de planes
                            registrar_historial_plan(idusuario, nombre_plan, transaction_amount_in_cents, duracion, fecha_finalizada_bogota, fecha_expiracion)

                        if usuario_info:
                            destinatario = usuario_info['correo']
                            nombre = usuario_info['nombre']
                            nombre_plan = plan_info['nombre']

                            # enviar_correo_agradecimiento(destinatario,nombre, nombre_plan, fecha_expiracion)




                        mysql.connection.commit()
                        return jsonify({'success': True}), 200
                    except ValueError:
                        mysql.connection.rollback()
                        return jsonify({'success': False, 'message': 'Duración del plan no es un número válido'}), 500

                else:
                    # Si no se encuentra la duración del plan, rollback y mensaje de error
                    mysql.connection.rollback()
                    return jsonify({'success': False, 'message': 'No se encontró la duración del plan'}), 500
        elif status == 'VOIDED':
            # Obtener información anterior del usuario desde la tabla historial_planes
            cur.execute("SELECT idplan_anterior, fecha_creacion_plan_anterior, fecha_expiracion_plan_anterior "
                        "FROM historial_planes WHERE idusuario=(SELECT idusuario FROM suscripciones WHERE token=%s) "
                        "ORDER BY id DESC LIMIT 1", [reference])
            historial_info = cur.fetchone()

            if historial_info:
                idplan_anterior = historial_info['idplan_anterior']
                fecha_creacion_plan_anterior = historial_info['fecha_creacion_plan_anterior']
                fecha_expiracion_plan_anterior = historial_info['fecha_expiracion_plan_anterior']
                 # Actualizar el plan del usuario a los valores anteriores
                cur.execute("UPDATE usuario SET idplan=%s, fecha_creacion_plan=%s, fecha_expiracion_plan=%s "
                            "WHERE idusuario=(SELECT idusuario FROM suscripciones WHERE token=%s)",
                            [idplan_anterior, fecha_creacion_plan_anterior, fecha_expiracion_plan_anterior, reference])
                cur.execute("UPDATE suscripciones SET estado='anulado' WHERE token=%s", [reference])
                mysql.connection.commit()
                return jsonify({'success': True}), 200
            else:
                mysql.connection.rollback()
                return jsonify({'success': False, 'message': 'No se encontró información previa del usuario'}), 500
        else:
            cur.execute("UPDATE suscripciones SET estado='rechazado' WHERE token=%s", [reference])
            mysql.connection.commit()
            return jsonify({'success': True}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': f'Error al actualizar la base de datos: {str(e)}'}), 500

    finally:
        cur.close()

    return jsonify({'success': False, 'message': 'Evento no procesado'}), 400


def registrar_historial_plan(idusuario, nombre_plan, transaction_amount_in_cents, duracion, fecha_inicio, fecha_fin):
    cur = mysql.connection.cursor()
    try:
        cur.execute(
            "INSERT INTO historial_planes_usuarios (idusuario, nombre_plan, precio, duracion, fecha_inicio, fecha_fin) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (idusuario, nombre_plan, transaction_amount_in_cents, duracion, fecha_inicio, fecha_fin)
        )
        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        # print(f"Error al registrar el historial del plan: {str(e)}")
    finally:
        cur.close()

@routes_blueprint.route('/solicitar-devolucion', methods=['POST'])
def solicitar_devolucion():
    # Obtener el usuario actual desde la sesión
    id_usuario_actual = session.get('idusuario')
    
    if id_usuario_actual:
        # Lógica para procesar la devolución (usando el usuario_actual)
        print(f"El usuario {id_usuario_actual} ha solicitado una devolución.")

        cur = mysql.connection.cursor()


        # Buscar el plan actual del usuario
        cur.execute("SELECT idplan FROM usuario WHERE idusuario = %s", [id_usuario_actual])
        plan_actual = cur.fetchone()

        if not plan_actual:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        idplan_actual = plan_actual['idplan']

        timezone = pytz.timezone('America/Bogota')
        fecha_actual = datetime.now(timezone)
        fecha_solicitud = fecha_actual.date()


        # Insertar la nueva solicitud
        cur.execute("""
            INSERT INTO solicitudes_devolucion (idusuario, idplan_comprado, fecha_solicitud)
            VALUES (%s, %s, %s)
        """, [id_usuario_actual, idplan_actual, fecha_solicitud])
        
        mysql.connection.commit()
        cur.close()

        

        # # Obtener la última suscripción activa del usuario
        # cur.execute("SELECT idplan_anterior, fecha_creacion_plan_anterior, fecha_expiracion_plan_anterior "
        #             "FROM historial_planes WHERE idusuario=%s"
        #             "ORDER BY id DESC LIMIT 1", [id_usuario_actual])
        
        # historial_info = cur.fetchone()

        # if historial_info:
        #     idplan_anterior = historial_info['idplan_anterior']
        #     fecha_creacion_plan_anterior = historial_info['fecha_creacion_plan_anterior']
        #     fecha_expiracion_plan_anterior = historial_info['fecha_expiracion_plan_anterior']
        #         # Actualizar el plan del usuario a los valores anteriores
        #     cur.execute("UPDATE usuario SET idplan=%s, fecha_creacion_plan=%s, fecha_expiracion_plan=%s "
        #                 "WHERE idusuario=%s",
        #                 [idplan_anterior, fecha_creacion_plan_anterior, fecha_expiracion_plan_anterior, id_usuario_actual])
        #     mysql.connection.commit()


        return jsonify({'success': True})
    else:
        return redirect(url_for('auth.login'))

@routes_blueprint.route('/ventas/reporte', methods=["GET", "POST"])
@login_required
def reporte_ventas():    

    id_usuario_actual = session.get('idusuario')


    #Fecha de hoy para ventas diarias
    timezone = pytz.timezone('America/Bogota')
    fecha_actual = datetime.now(timezone)
    fecha = fecha_actual.date()
    fecha_inicio = fecha - timedelta(days=7)
    fecha_fin = fecha
    lista_consultas_para_reporte = query_reportes(id_usuario_actual, fecha_inicio, fecha_fin)

    if request.method == 'POST':
        data = request.get_json()
        fecha_inicio = data.get("fecha_inicio"),
        fecha_fin = data.get("fecha_fin")
        print("Datos recibidos:", data)  # Verifica que los datos se están recibiendo correctamente
        lista_consultas_para_reporte = query_reportes(id_usuario_actual, fecha_inicio, fecha_fin)
        print(f"categorias vendidas {lista_consultas_para_reporte[0]}")
        print(f"ganancias categoria {lista_consultas_para_reporte[1]}")
        print(f"ventas metoido pago {lista_consultas_para_reporte[2]}")
        print(f"ventas dia {lista_consultas_para_reporte[3]}")
        print(f"ganancias dia {lista_consultas_para_reporte[4]}")
        print(f"ventas mes {lista_consultas_para_reporte[5]}")
        print(f"ganancias mes {lista_consultas_para_reporte[6]}")


        return jsonify({
            'categorias_vendidas': lista_consultas_para_reporte[0],
            'ganancias_categoria': lista_consultas_para_reporte[1],
            'ventas_metodo_pago': lista_consultas_para_reporte[2],
            'ventas_dia': lista_consultas_para_reporte[3],
            'ganancias_dia': lista_consultas_para_reporte[4],
            'ventas_mes': lista_consultas_para_reporte[5],
            'ganancias_mes': lista_consultas_para_reporte[6],
        })
    

    

    
    return render_template('ventas/reporte_ventas.html',
                            categorias_vendidas=lista_consultas_para_reporte[0],
                            ganancias_categoria=lista_consultas_para_reporte[1],
                            ventas_metodo_pago=lista_consultas_para_reporte[2],
                            ventas_dia=lista_consultas_para_reporte[3],
                            ganancias_dia=lista_consultas_para_reporte[4],
                            ventas_mes=lista_consultas_para_reporte[5],
                            ganancias_mes=lista_consultas_para_reporte[6],)



@routes_blueprint.route('/ventas/registrar', methods=["POST"])
def registrar_venta():
    # Verificar si el usuario está autenticado
    if not session.get('idusuario'):
        return jsonify({"error": "Usuario no autenticado"}), 401

    # Obtener datos de la solicitud
    data = request.get_json()
    cliente = data.get("cliente", "Consumidor Final")
    idcliente = data.get("idcliente", "222222222222")
    productos = data.get("productos", [])
    metodo_pago = data.get("metodo_pago", "efectivo")
    pagocon = data.get("pagocon", 0)
    contacto = data.get("contacto", "")
    nota = data.get("nota", "")
    credito = data.get("credito", 0)
    id_usuario_actual = session.get('idusuario')
    print(f"el metodo de pago es {metodo_pago}")
    print(f"el nombre del cliente es {cliente}")
    print(f"su id es {idcliente}")
    print(f"el contacto es {contacto}")
    print(f"la nota es {nota}")

    # Validar que se envíen productos en la venta
    if not productos:
        return jsonify({"error": "No hay productos en la venta"}), 400

    print(f"los productos son {productos}")

    try:
        cur = mysql.connection.cursor()
        total_venta = 0
        
        # Verificar stock y calcular el total de la venta
        for producto in productos:
            codigo_barras = producto["Codigo_de_barras"]
            cantidad_solicitada = int(producto["Cantidad"])
            precio_unitario = float(producto["Precio_Valor"])

            # Obtener el stock actual del producto
            cur.execute("SELECT Cantidad FROM productos WHERE Codigo_de_barras = %s AND id_usuario = %s", 
                        (codigo_barras, id_usuario_actual))
            producto_db = cur.fetchone()

            if not producto_db:
                return jsonify({"error": f"Producto con código {codigo_barras} no encontrado"}), 400

            stock_disponible = producto_db["Cantidad"]

            # Verificar que haya suficiente stock
            if cantidad_solicitada > stock_disponible:
                print("no hay stock")
                return jsonify({"error": f"No hay suficiente stock para el producto {codigo_barras}. Stock disponible: {stock_disponible}"}), 400

            # Acumular el total de la venta
            total_venta += cantidad_solicitada * precio_unitario
        
        # Fecha y hora de Bogotá
        timezone = pytz.timezone('America/Bogota')
        fecha_actual = datetime.now(timezone)
        fecha = fecha_actual.date()
        hora = fecha_actual.time()
        
       
        fecha_servidor = fecha

        # Obtener el último idventausuario
        cur.execute('SELECT MAX(idventausuario) AS max_id FROM ventas WHERE idusuario = %s', (id_usuario_actual,))
        result = cur.fetchone()
        idventausuario = 1 if result['max_id'] is None else result['max_id'] + 1

        # Insertar la venta en la tabla ventas
        query_venta = """
        INSERT INTO ventas (
            idusuario, totalventa, pagocon, fecha, hora, metodo_pago,
            idventausuario, cliente, idcliente, credito, fecha_servidor
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(query_venta, (
            id_usuario_actual, total_venta, pagocon, fecha, hora, metodo_pago,
            idventausuario, cliente, idcliente, credito, fecha_servidor
        ))
        mysql.connection.commit()

        # Actualizar la tabla creditos si crédito es 1
        if credito == 1:
            # Convertir el valor a entero o flotante, dependiendo del formato que necesites
            abono = 0 #por ahora es cero
            #abono = (pagocon)  # Si es un número entero
            # nota = request.form.get('notaCliente')[:100]
            
            cur.execute(
                'INSERT INTO creditos (nombre_cliente, identificacion_cliente, contacto_cliente, total_compra, abono, idventausuario, idusuario, fecha_registro, hora, nota) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (cliente, idcliente ,contacto , total_venta , abono, idventausuario, id_usuario_actual, fecha, hora, nota)
            )
            mysql.connection.commit()

        
      

        cur.close()

        return jsonify({
            'success': 'Venta registrada correctamente.',
            'idventa': idventausuario,
            'total_venta': total_venta,
            'fecha': str(fecha)
        }), 200

    except Exception as e:
        print(f"Error al registrar venta: {e}")
        mysql.connection.rollback()
        return jsonify({"error": "Error al registrar la venta. Por favor, intente nuevamente."}), 500
    finally:
        if cur:
            cur.close()

@routes_blueprint.route('/ventas/agregar_productos', methods=["POST"])
def agregar_productos():
    try:
        datos = request.json
        id_venta = datos.get('idventa')
        productos = datos.get('productos', [])
        fecha = datos.get('fecha')
        total = datos.get('total_final'),

        if not id_venta or not productos:
            return jsonify({'error': 'Datos incompletos para agregar productos.'}), 400

        cur = mysql.connection.cursor()

        for producto in productos:
            # Insertar el producto en la tabla detalleventas
            query_detalleventas = """
            INSERT INTO detalleventas (
                idventa, codigo_de_barras, nombre, descripcion, valor,
                costo, cantidad, categoria, idusuario, fecha
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(query_detalleventas, (
                id_venta,
                producto.get('Codigo_de_barras'),
                producto.get('Nombre'),
                producto.get('Descripcion', ''),
                producto.get('Precio_Valor', ''),
                producto.get('Precio_Costo'),
                producto.get('Cantidad'),
                producto.get('Categoria', ''),
                session.get('idusuario'),
                fecha
            ))

            # Reducir la cantidad en la tabla productos
            query_actualizar_productos = """
            UPDATE productos
            SET Cantidad = Cantidad - %s
            WHERE Codigo_de_barras = %s AND id_usuario = %s AND Cantidad >= %s
            """
            cantidad = producto.get('Cantidad')
            cur.execute(query_actualizar_productos, (
                cantidad,
                producto.get('Codigo_de_barras'),
                session.get('idusuario'),
                cantidad
            ))

            # Verificar si la cantidad disponible es insuficiente
            if cur.rowcount == 0:
                mysql.connection.rollback()
                return jsonify({'error': f'No hay suficiente stock para el producto {producto.get("Nombre")}.'}), 400

        # Confirmar los cambios
        mysql.connection.commit()
        cur.close()

        return jsonify({'success': 'Productos agregados correctamente.'}), 200

    except Exception as e:
        print(f"Error al agregar productosssssss: {e}")
        mysql.connection.rollback()
        return jsonify({'error': 'Error al agregar productos. Por favor, intente nuevamente.'}), 500

@routes_blueprint.route('/buscar_producto_codigo', methods=["POST"])  # Para la barra de admin.html
def buscar_producto_codigo():
    if not session.get('idusuario'):
        return jsonify({"error": "Usuario no autenticado"}), 401

    data = request.get_json()
    codigo_barras = data.get('codigo_barras')  # Recibe el código de barras desde el cliente.
    id_usuario_actual = session.get('idusuario')

    if not codigo_barras:
        return jsonify({"error": "No se proporcionó un código de barras"}), 400

    try:
        cur = mysql.connection.cursor()

        # Consulta específica para buscar solo por código de barras
        query = """
            SELECT Codigo_de_barras, Nombre, Descripcion, Precio_Valor, Precio_Costo, Cantidad, Categoria
            FROM productos
            WHERE Codigo_de_barras = %s AND id_usuario = %s
        """
        cur.execute(query, (codigo_barras, id_usuario_actual))
        producto = cur.fetchone()

        if not producto:
            return jsonify({"error": "No se encontró el producto"}), 200

        # Verificar si hay existencias disponibles
        if producto["Cantidad"] <= 0:
            return jsonify({"error": f"El producto '{producto['Nombre']}' no tiene existencias disponibles."}), 200

        # Convertir el resultado a formato JSON
        producto_json = {
            "Codigo_de_barras": producto["Codigo_de_barras"],
            "Nombre": producto["Nombre"],
            "Descripcion": producto["Descripcion"],
            "Precio_Valor": producto["Precio_Valor"],
            "Precio_Costo": producto["Precio_Costo"],
            "Stock": producto["Cantidad"],
            "Categoria": producto["Categoria"]
        }

        return jsonify({"producto": producto_json})
    except Exception as e:
        print(f"Error al buscar producto: {e}")
        return jsonify({"error": "Error al buscar producto"}), 500
    finally:
        cur.close()



@routes_blueprint.route('/creditos/detalles/<int:idcredito>', methods=['GET'])
def obtener_detalles_credito(idcredito):
    # Verificar si el usuario está autenticado
    if not session.get('idusuario'):
        return jsonify({"error": "Usuario no autenticado"}), 403

    id_usuario_actual = session.get('idusuario')

    try:
        cur = mysql.connection.cursor()

        # Obtener los detalles del crédito
        consulta_credito = """
            SELECT idcredito, nombre_cliente, identificacion_cliente, total_compra, abono, fecha_registro, nota, idventausuario
            FROM creditos
            WHERE idcredito = %s AND idusuario = %s
        """
        cur.execute(consulta_credito, (idcredito, id_usuario_actual))
        credito = cur.fetchone()
        print(credito)

        if not credito:
            return jsonify({"error": "Crédito no encontrado"}), 404

        # Obtener los productos asociados a la venta
        consulta_productos = """
            SELECT nombre, cantidad, valor
            FROM detalleventas
            WHERE idventa = %s AND idusuario = %s
        """
        cur.execute(consulta_productos, (credito["idventausuario"], id_usuario_actual))
        productos = cur.fetchall()

        # Obtener el historial de abonos
        consulta_abonos = """
            SELECT fecha_abono, hora_abono, monto_abono
            FROM registro_abonos
            WHERE idcredito = %s AND idusuario = %s
        """
        cur.execute(consulta_abonos, (idcredito, id_usuario_actual))
        abonos = cur.fetchall()

        # Convertir timedelta a cadena en el historial de abonos
        for abono in abonos:
            if isinstance(abono["hora_abono"], timedelta):
                abono["hora_abono"] = str(abono["hora_abono"])  # Convertir a cadena


        # Cerrar la conexión
        cur.close()

        # Devolver los datos en formato JSON
        return jsonify({
            "credito": credito,
            "productos": productos,
            "abonos": abonos
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Ocurrió un error al obtener los detalles del crédito"}), 500

@routes_blueprint.route('/creditos/abonar', methods=['POST'])
def abonar_credito():
    # Verificar si el usuario está autenticado
    if not session.get('idusuario'):
        return jsonify({"error": "Usuario no autenticado"}), 403

    id_usuario_actual = session.get('idusuario')

    try:
        # Obtener los datos del cuerpo de la solicitud
        datos = request.get_json()
        idcredito = datos.get('idcredito')
        monto = datos.get('monto')

        if not idcredito or not monto:
            return jsonify({"error": "Datos incompletos"}), 400

        cur = mysql.connection.cursor()

        # Obtener el abono actual y total_compra
        consulta_credito = """
            SELECT idventausuario, total_compra, abono 
            FROM creditos 
            WHERE idcredito = %s AND idusuario = %s
        """
        cur.execute(consulta_credito, (idcredito, id_usuario_actual))
        resultado = cur.fetchone()

        if not resultado:
            return jsonify({"error": "Crédito no encontrado"}), 404

        idventausuario = resultado["idventausuario"]
        total_compra = resultado["total_compra"] or 0
        abono_actual = resultado["abono"] or 0

        # Validar que el abono no exceda el total de la compra
        if (abono_actual + monto) > total_compra:
            return jsonify({"error": "El abono excede el total de la compra"}), 200

        # Registrar el abono en la tabla registro_abonos
        query_abono = """
            INSERT INTO registro_abonos (idcredito, idusuario, monto_abono, fecha_abono, hora_abono)
            VALUES (%s, %s, %s, %s, %s)
        """
        # Definir la zona horaria de Bogotá
        bogota_tz = pytz.timezone('America/Bogota')

        # Obtener la fecha y hora en la zona horaria de Bogotá
        fecha_actual = datetime.now(bogota_tz).date()
        hora_actual = datetime.now(bogota_tz).time()
        cur.execute(query_abono, (idcredito, id_usuario_actual, monto, fecha_actual, hora_actual))

        # Actualizar el campo abono en la tabla creditos
        query_actualizar_abono = """
            UPDATE creditos
            SET abono = abono + %s, estado = CASE WHEN (abono + %s) >= total_compra THEN 'Pagado' ELSE 'Activo' END
            WHERE idcredito = %s AND idusuario = %s
        """
        cur.execute(query_actualizar_abono, (monto, monto, idcredito, id_usuario_actual))

        # Actualizar el campo pagocon en la tabla ventas
        query_venta = """
            UPDATE ventas
            SET pagocon = pagocon + %s
            WHERE idventausuario = %s AND idusuario = %s
        """
        cur.execute(query_venta, (monto, idventausuario, id_usuario_actual))

        # Confirmar los cambios en la base de datos
        mysql.connection.commit()
        cur.close()

        return jsonify({"success": "Abono registrado correctamente"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Ocurrió un error al registrar el abono"}), 500


@routes_blueprint.route('/creditos/obtener', methods=['GET'])
def obtener_creditos():
    # Verificar si el usuario está autenticado
    if not session.get('idusuario'):
        return jsonify({"error": "Usuario no autenticado"}), 403

    id_usuario_actual = session.get('idusuario')

    try:
        cur = mysql.connection.cursor()

        # Consulta para obtener los créditos del usuario actual
        query = """
            SELECT idcredito, nombre_cliente, identificacion_cliente, total_compra, abono, fecha_registro, estado
            FROM creditos
            WHERE idusuario = %s
        """
        cur.execute(query, (id_usuario_actual,))
        creditos = cur.fetchall()

        # Convertir los créditos a una lista de diccionarios
        creditos_json = []
        for credito in creditos:
            credito_dict = {
                "idcredito": credito["idcredito"],
                "nombre_cliente": credito["nombre_cliente"],
                "identificacion_cliente": credito["identificacion_cliente"],
                "total_compra": float(credito["total_compra"]),
                "abono": float(credito["abono"]),
                "fecha_registro": credito["fecha_registro"].strftime("%d/%m/%y"),  # Formatear fecha
                "estado": credito["estado"]
            }
            creditos_json.append(credito_dict)

        # Cerrar la conexión
        cur.close()

        # Devolver los créditos en formato JSON
        return jsonify(creditos_json), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Ocurrió un error al obtener los créditos"}), 500


@routes_blueprint.route('/ventas/realizadas', methods=["GET"])
@login_required
def ventas_realizadas():
    return venta()

@routes_blueprint.route('/ventas/realizadas/credito', methods=["GET"])
@login_required
def ventas_realizadas_credito():
    return ventacredito()

@routes_blueprint.route('/obtener_ventas', methods=["POST"])
@login_required
def obtener_ventas():
    return obtenerventa()

@routes_blueprint.route('/detalles/<int:idventa>', methods=["GET"])
def detalles_venta(idventa):
    return detallesventa(idventa)


@routes_blueprint.route('/devolucion/<int:idventa>', methods=["POST"])
def aplicar_devolucion(idventa):
    return devolucion_venta(idventa)

@routes_blueprint.route('/factura/<int:idventa>', methods=["GET"])
def generar_factura(idventa):
    # Verificar que el usuario esté autenticado
    if not session.get('idusuario'):
        return redirect(url_for('routes.login'))

    idusuario = session.get('idusuario')
    try:
        cur = mysql.connection.cursor()

        # Obtener la venta de la tabla ventas
        query_venta = """
            SELECT * FROM ventas 
            WHERE idventausuario = %s AND idusuario = %s
        """
        cur.execute(query_venta, (idventa, idusuario))
        venta = cur.fetchone()
        if not venta:
            return "Venta no encontrada", 404

        # Obtener el detalle de la venta (productos)
        query_detalle = """
            SELECT * FROM detalleventas 
            WHERE idventa = %s AND idusuario = %s
        """
        cur.execute(query_detalle, (idventa, idusuario))
        detalles = cur.fetchall()
        cur.close()

        # Renderizar la plantilla HTML de la factura
        html = render_template('factura.html', venta=venta, detalles=detalles)
        
        wkhtmltopdf_path = os.getenv('WKHTMLTOPDF_PATH')

        config_pdfkit = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        
        pdf = pdfkit.from_string(html, False, configuration=config_pdfkit)

        # Preparar la respuesta con el PDF
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=factura_{idventa}.pdf'
        return response

    except Exception as e:
        print("Error generando factura:", e)
        return "Error generando factura", 500
@routes_blueprint.route('/ventana_administracion')
@login_required
def ventana_administracion():
    rol_usuario_actual = session.get('role')  # Obtener el rol del usuario

    # Verificar si el usuario es administrador
    if rol_usuario_actual != 'admin':
        return render_template('admin_usuarios.html', error_message="No tienes permisos para acceder a esta página.")

    try:
        # Conectar a la base de datos usando un cursor que retorna diccionarios
        cursor = mysql.connection.cursor()
   
        # Consulta para obtener la información de los usuarios junto con sus planes, ventas e inactividad
        query = """
            SELECT 
                u.idusuario,
                u.nombre AS nombre_usuario,
                u.correo,
                u.role,
                p.nombre AS plan_actual,
                u.fecha_creacion_plan,
                u.fecha_expiracion_plan,
                COUNT(v.idventas) AS total_ventas,
                MAX(v.fecha) AS ultima_venta,
                DATEDIFF(NOW(), u.ultimo_intento) AS dias_inactivo,
                COALESCE(sd.estado, 'none') AS estado_devolucion
            FROM 
                usuario u
            LEFT JOIN 
                planes p ON u.idplan = p.idplan
            LEFT JOIN 
                ventas v ON u.idusuario = v.idusuario
            LEFT JOIN (
                SELECT 
                    sd1.idusuario,
                    sd1.estado
                FROM 
                    solicitudes_devolucion sd1
                INNER JOIN (
                    SELECT 
                        idusuario,
                        MAX(fecha_solicitud) AS ultima_fecha
                    FROM 
                        solicitudes_devolucion
                    GROUP BY 
                        idusuario
                ) sd2 ON sd1.idusuario = sd2.idusuario AND sd1.fecha_solicitud = sd2.ultima_fecha
            ) sd ON u.idusuario = sd.idusuario
            GROUP BY 
                u.idusuario;
        """
        cursor.execute(query)
        usuarios = cursor.fetchall()
        cursor.close()

        # Renderizar la plantilla 'admin.html' con la información de los usuarios
        return render_template('configuracion/ventana_administracion.html', usuarios=usuarios, rol_usuario_actual=rol_usuario_actual)

    except Exception as e:
        print(f"Error al listar usuarios: {e}")
        # Renderizar la misma plantilla con un mensaje de error
        return render_template('admin.html', error_message="Error al cargar la información de los usuarios.")
    
@routes_blueprint.route('/manejar-devolucion', methods=['POST'])
def manejar_devolucion():
    data = request.get_json()  # Obtener los datos enviados desde el frontend
    id_usuario = data['idUsuario']
    accion = data['accion']  # 'aceptar' o 'rechazar'
    print(f"manejar devolucion: el usuario al que le acpete o rechaze essss {id_usuario}")

    try:
        cursor = mysql.connection.cursor()

        # 1. Actualizar el estado en la tabla solicitudes_devolucion
        nuevo_estado = 'aprobada' if accion == 'aceptar' else 'rechazada'
        cursor.execute("""
            UPDATE solicitudes_devolucion
            SET estado = %s
            WHERE idusuario = %s
        """, (nuevo_estado, id_usuario))

        # 2. Si la acción es "aceptar", actualizar el plan del usuario
        if accion == 'aceptar':
            # Obtener el plan anterior desde historial_planes
            cursor.execute("""
                SELECT idplan_anterior, fecha_creacion_plan_anterior, fecha_expiracion_plan_anterior
                FROM historial_planes
                WHERE idusuario = %s
                ORDER BY id DESC
                LIMIT 1
            """, (id_usuario,))
            plan_anterior = cursor.fetchone()

            # Determinar el idplan a asignar
            if plan_anterior:
                idplan_nuevo = plan_anterior['idplan_anterior']
                fecha_creacion_plan = plan_anterior['fecha_creacion_plan_anterior']
                fecha_expiracion_plan = plan_anterior['fecha_expiracion_plan_anterior']
            else:
                # Si no hay registros en historial_planes, asignar idplan = 1 (plan por defecto)
                idplan_nuevo = 1
                fecha_creacion_plan = None  # O asigna una fecha por defecto si es necesario
                fecha_expiracion_plan = None  # O asigna una fecha por defecto si es necesario

            # Actualizar la tabla usuario con el nuevo plan
            cursor.execute("""
                UPDATE usuario
                SET idplan = %s,
                    fecha_creacion_plan = %s,
                    fecha_expiracion_plan = %s
                WHERE idusuario = %s
            """, (idplan_nuevo, fecha_creacion_plan, fecha_expiracion_plan, id_usuario))
        
        mysql.connection.commit()
        cursor.close()

        # Retornar una respuesta de éxito al frontend
        return jsonify({'success': True, 'message': f'Devolución {accion} correctamente.'})

    except Exception as e:
        print(f"Error al manejar la devolución: {e}")
        return jsonify({'success': False, 'message': 'Hubo un error al procesar la devolución.'}), 500
    
@routes_blueprint.route('/usuarios/eliminar/<int:id_usuario>', methods=['GET'])
def eliminar_usuario(id_usuario):
    id_usuario_actual = session.get('idusuario')  # Obtener ID del usuario actual
    cur = mysql.connection.cursor()

    try:
        # Iniciar transacción
        cur.execute('START TRANSACTION')

        # Eliminar registros dependientes en las tablas relacionadas
        cur.execute('DELETE FROM productos WHERE id_usuario = %s', (id_usuario,))
        cur.execute('DELETE FROM suscripciones WHERE idusuario = %s', (id_usuario,))
        cur.execute('DELETE FROM historial_planes_usuarios WHERE idusuario = %s', (id_usuario,))
        cur.execute('DELETE FROM historial_planes WHERE idusuario = %s', (id_usuario,))
        cur.execute('DELETE FROM ventas WHERE idusuario = %s', (id_usuario,))
        cur.execute('DELETE FROM creditos WHERE idusuario = %s', (id_usuario,))

        # Ahora eliminar el usuario de la tabla 'usuario'
        cur.execute('DELETE FROM usuario WHERE idusuario = %s', (id_usuario,))

        # Confirmar la eliminación
        mysql.connection.commit()

        return redirect(url_for('routes.ventana_administracion'))  # Redirigir a la ventana de administración

    except Exception as e:
        # Si ocurre un error, hacer rollback y mostrar mensaje
        mysql.connection.rollback()
        print(f"Error al eliminar el usuario: {e}")  # Depuración
        return redirect(url_for('routes.ventana_administracion'))  # Redirigir en caso de error

    finally:
        cur.close()
@routes_blueprint.route('/usuarios/editar/<int:id_usuario>', methods=['GET', 'POST'])
def editar_usuario(id_usuario):
    id_usuario_actual = session.get('idusuario')  # Obtener ID del usuario actual
    if not id_usuario_actual:
        return redirect(url_for('routes.login'))  # Redirigir si no está autenticado

    if request.method == 'POST':
        # Obtener los datos del formulario
        nombre = request.form.get('nombre')
        correo = request.form.get('correo')
        fecha_expiracion_plan = request.form.get('fecha_expiracion_plan')  
        role = request.form.get('role')
        idplan = request.form.get('idplan')
        # Crear cursor para consultas
        cur = mysql.connection.cursor()
        try:
            # Iniciar transacción
            cur.execute('START TRANSACTION')

            # Consultar si el usuario existe
            cur.execute("SELECT * FROM usuario WHERE idusuario = %s", (id_usuario,))
            usuario = cur.fetchone()

            if not usuario:
             
                return redirect(url_for('routes.ventana_administracion'))

            # Actualizar el usuario
            cur.execute(''' 
                UPDATE usuario
                SET nombre = %s, correo = %s, fecha_expiracion_plan = %s, role = %s, idplan = %s
                WHERE idusuario = %s
            ''', (nombre, correo, fecha_expiracion_plan if fecha_expiracion_plan else None, role, idplan, id_usuario))

            # Confirmar la actualización
            mysql.connection.commit()

             
            return redirect(url_for('routes.ventana_administracion'))

        except Exception as e:
            # Si ocurre un error, hacer rollback y mostrar mensaje
            mysql.connection.rollback()
            return redirect(url_for('routes.ventana_administracion'))

        finally:
            cur.close()

    else:
        # Si es un GET, traer los datos actuales del usuario
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuario WHERE idusuario = %s", (id_usuario,))
        usuario = cur.fetchone()
        cur.close()

        if not usuario:
             return redirect(url_for('routes.ventana_administracion'))

        return render_template('configuracion/editar_usuario.html', usuario=usuario)

@routes_blueprint.route('/clientes/eliminar/<int:idcliente>', methods=['DELETE'], endpoint='eliminar_cliente')
def eliminar_cliente(idcliente):
    return eliminarcliente(idcliente)

@routes_blueprint.route('/clientes/editar/<int:idcliente>', methods=['PUT'], endpoint='editar_cliente')
def editar_cliente(idcliente):
    return editarcliente(idcliente)

@routes_blueprint.route('/clientes/top', methods=['GET'], endpoint='clientes_top')
@login_required
def clientes_top():
    """Obtener los 10 clientes con más compras."""
    return clientestop()

@routes_blueprint.route('/chatbot', methods=['POST'], endpoint='chatbot')
def chatbot():
    user_input = request.json.get('message')
    try:
        # Recibir la respuesta desde chatbot.py
        response = get_message(user_input)
        print(response)
        if response and response.text:
            reply_text = response.text
        else:
            reply_text = "La respuesta de la API no contiene datos válidos."
        return jsonify({'reply': reply_text})
    except Exception as e:
        # Manejo de errores más específico
        return jsonify({'reply': f'Error al conectar con la API de Gémini: {str(e)}'}), 500

from flask import render_template
@routes_blueprint.route('/chatbot', methods=['GET'], endpoint='chatbot_page')
def chatbot_page():
    return render_template('chatbot.html')