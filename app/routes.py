from flask import Blueprint, render_template, redirect, url_for, request, session, jsonify
from app.auth import login_user, register_user
from app.utils import obtener_hora_actual_bogota
from flask_mysqldb import MySQL
from io import BytesIO
from openpyxl import Workbook
from flask import send_file
import bleach
import pytz
import uuid
import hashlib
import hmac
from datetime import datetime, timedelta
import pdfkit  # Para convertir a PDF (requiere wkhtmltopdf instalado)
''' para Windows:
    Descarga el instalador desde wkhtmltopdf.org.
    Durante la instalación, marca la opción para agregar wkhtmltopdf al PATH del sistema.'''
from . import forms
# Crear un Blueprint para las rutas
routes_blueprint = Blueprint('routes', __name__)

# Inicialización de MySQL
mysql = None

def init_mysql(app):
    global mysql
    mysql = MySQL(app)

@routes_blueprint.route('/login', methods=["GET", "POST"])
def login():
    return login_user()

@routes_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    return register_user()

@routes_blueprint.route('/')
def home():
    return render_template('home.html')

@routes_blueprint.route('/home')
def home_redirect():
    return redirect(url_for('routes.home'))

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


@routes_blueprint.route('/productos/listar', methods=["GET"])
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
        return render_template('listar_productos.html', productos=productos)
    except Exception as e:
        print(f"Error al listar productos: {e}")
        return render_template('listar_productos.html', error_message="Error al cargar los productos.")


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
    return render_template('editar_producto.html', producto=producto)


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
            pdf_output = BytesIO()
            pdfkit.from_string(html, pdf_output)
            pdf_output.seek(0)
            nombre_archivo = f"productos_{username}.pdf"
            return send_file(pdf_output, as_attachment=True, download_name=nombre_archivo)

        else:
            return jsonify({"error": "Formato no soportado"}), 400

    except Exception as e:
        print(f"Error al generar el archivo: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@routes_blueprint.route('/admin', methods=["GET", "POST"])
def admin():
    from app import mysql
    VentasCreditoForm = forms.VentasCreditoForm(request.form)
    saludo = session.get('saludo')
    username = session.get('username')
    idplan = session.get('idplan')

    if request.method == 'POST':
        print("--------------------------POST--------------------------")
        print(VentasCreditoForm.nombre.data)
        print(VentasCreditoForm.id.data)
        print(VentasCreditoForm.contacto.data)
        print(VentasCreditoForm.nota.data)
        return redirect(url_for('routes.admin'))
    
    return render_template('admin.html', saludo=saludo, username=username, idplan=idplan, VentasCreditoForm = VentasCreditoForm)

@routes_blueprint.route('/productos/agregar', methods=["GET", "POST"])
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
            return render_template('formulario_productos.html', message='Todos los campos son obligatorios.')

        try:
            cur.execute('START TRANSACTION')
            cur.execute('SELECT * FROM productos WHERE Codigo_de_barras = %s AND id_usuario = %s', 
                        (codigo_barras, id_usuario_actual))
            if cur.fetchone():
                return render_template('formulario_productos.html', message='El código de barras ya está registrado.')

            cur.execute('INSERT INTO productos (id_usuario,Codigo_de_barras, Nombre, Descripcion, Precio_Valor, Precio_Costo, Cantidad, Categoria) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', 
                        (id_usuario_actual, codigo_barras, nombre, descripcion, precio_valor, precio_costo, cantidad, categoria))
            mysql.connection.commit()
            return render_template('formulario_productos.html', message='Producto agregado exitosamente.')
        except Exception as e:
            mysql.connection.rollback()
            print(f"Error al agregar el producto: {e}")
            return render_template('formulario_productos.html', message='Error al agregar el producto.')
        finally:
            cur.close()

    return render_template('formulario_productos.html')

@routes_blueprint.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for('routes.login'))

@routes_blueprint.route('/terminos_condiciones', methods=['GET'], endpoint='terminos_condiciones')
def terminos_condiciones():
    """Muestra los términos y condiciones."""
    return render_template('terminos_condiciones.html')

@routes_blueprint.route('/inventario', methods=['GET'], endpoint='inventario')
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
    return render_template('inventario.html', productos=productos)

@routes_blueprint.route('/clientes', methods=['GET'], endpoint='clientes')
def clientes():
    """Página para gestionar los clientes."""
    return render_template('clientes.html')

@routes_blueprint.route('/configuracion', methods=['GET'], endpoint='configuracion')
def configuracion():
    """Página para gestionar la configuración."""
    return render_template('configuracion.html')


@routes_blueprint.route('/planes', methods=['GET'])
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

        # Enviar datos a la plantilla
        return render_template('planes.html', planes=planes, nombre=nombre, plan_actual=id_plan, fecha_expiracion_plan=fecha_expiracion_plan)

    except Exception as e:
        return render_template('planes.html', message=f'Error: {str(e)}')
    finally:
        cur.close()



@routes_blueprint.route('/suscribir/<int:idplan>', methods=['GET'])
def suscribir(idplan):
    id_usuario = session.get('idusuario')
    # correo_usuario = session.get('correo')


    cur = mysql.connection.cursor()
    cur.execute('SELECT correo FROM usuario WHERE idusuario= %s', [id_usuario])
    correo_usuario=  cur.fetchone()['correo']
    if not id_usuario or not correo_usuario:
        return render_template('index.html')  # Redirigir al login si el usuario no está autenticado

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

    return render_template('detalle_plan.html', suscripcion=suscripcion, integrity_hash=integrity_hash, precio_centavos=precio_centavos)




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

@routes_blueprint.route('/ventas/registrar', methods=["POST"])
def registrar_venta():
    # Verificar si el usuario está autenticado
    if not session.get('idusuario'):
        return jsonify({"error": "Usuario no autenticado"}), 401

    # Obtener datos de la solicitud
    data = request.get_json()
    productos = data.get("productos", [])
    metodo_pago = data.get("metodo_pago", "efectivo")
    pagocon = data.get("pagocon", 0)
    id_usuario_actual = session.get('idusuario')

    # Validar que se envíen productos en la venta
    if not productos:
        return jsonify({"error": "No hay productos en la venta"}), 400

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
                return jsonify({"error": f"No hay suficiente stock para el producto {codigo_barras}. Stock disponible: {stock_disponible}"}), 400

            # Acumular el total de la venta
            total_venta += cantidad_solicitada * precio_unitario

        # Fecha y hora de Bogotá
        timezone = pytz.timezone('America/Bogota')
        fecha_actual = datetime.now(timezone)
        fecha = fecha_actual.date()
        hora = fecha_actual.time()
        
        # Valores predeterminados para la venta
        devuelto = float(pagocon) - total_venta if float(pagocon) >= total_venta else 0
        cliente = "Consumidor Final"
        idcliente = "222222222222"
        credito = 0
        fecha_servidor = fecha

        # Obtener el último idventausuario
        cur.execute('SELECT MAX(idventausuario) AS max_id FROM ventas WHERE idusuario = %s', (id_usuario_actual,))
        result = cur.fetchone()
        idventausuario = 1 if result['max_id'] is None else result['max_id'] + 1

        # Insertar la venta en la tabla ventas
        query_venta = """
        INSERT INTO ventas (
            idusuario, totalventa, pagocon, fecha, hora, metodo_pago,
            idventausuario, devuelto, cliente, idcliente, credito, fecha_servidor
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(query_venta, (
            id_usuario_actual, total_venta, pagocon, fecha, hora, metodo_pago,
            idventausuario, devuelto, cliente, idcliente, credito, fecha_servidor
        ))

        # Registrar cada producto vendido: insertar el detalle y actualizar el stock
        for producto in productos:
            codigo_barras = producto["Codigo_de_barras"]
            cantidad_solicitada = int(producto["Cantidad"])
            precio_unitario = float(producto["Precio_Valor"])
            
            # Insertar en la tabla detalle de venta
            query_detalle = """
            INSERT INTO detalle_ventas (
                idventausuario, idusuario, Codigo_de_barras, Cantidad, Precio_Unitario
            ) VALUES (%s, %s, %s, %s, %s)
            """
            cur.execute(query_detalle, (idventausuario, id_usuario_actual, codigo_barras, cantidad_solicitada, precio_unitario))

            # Actualizar el stock del producto
            query_update_stock = """
            UPDATE productos 
            SET Cantidad = Cantidad - %s 
            WHERE Codigo_de_barras = %s AND id_usuario = %s AND Cantidad >= %s
            """
            cur.execute(query_update_stock, (cantidad_solicitada, codigo_barras, id_usuario_actual, cantidad_solicitada))

            # Verificar que el stock se haya actualizado correctamente
            if cur.rowcount == 0:
                mysql.connection.rollback()
                return jsonify({
                    "error": f"No se pudo actualizar el stock para el producto {codigo_barras}. Puede que no haya suficiente stock."
                }), 400

        # Confirmar los cambios en la base de datos
        mysql.connection.commit()
        cur.close()

        return jsonify({
            'success': 'Venta registrada correctamente.',
            'idventa': idventausuario,
            'total_venta': total_venta,
            'fecha': str(fecha),
            'devuelto': devuelto
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
                producto.get('Precio_Valor'),
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
        print(f"Error al agregar productos: {e}")
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
            "Cantidad": producto["Cantidad"],
            "Categoria": producto["Categoria"]
        }

        return jsonify({"producto": producto_json})
    except Exception as e:
        print(f"Error al buscar producto: {e}")
        return jsonify({"error": "Error al buscar producto"}), 500
    finally:
        cur.close()