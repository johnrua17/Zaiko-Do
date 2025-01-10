from flask import Blueprint, render_template, redirect, url_for, request, session, jsonify
from app.auth import login_user, register_user
from app.utils import obtener_hora_actual_bogota
from flask_mysqldb import MySQL
from io import BytesIO
from openpyxl import Workbook
from flask import send_file
import bleach

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
    return redirect(url_for('routes.login'))

@routes_blueprint.route('/buscar_producto', methods=["POST"])
def buscar_producto():
    if not session.get('idusuario'):
        return jsonify({"error": "Usuario no autenticado"}), 401

    data = request.get_json()
    codigo_barras = data.get('codigo_barras')
    id_usuario_actual = session.get('idusuario')

    if not codigo_barras:
        return jsonify({"error": "Código de barras no proporcionado"}), 400

    try:
        cur = mysql.connection.cursor()
        query = """
            SELECT Codigo_de_barras, Nombre, Descripcion, Precio_Valor, Precio_Costo, Cantidad, Categoria
            FROM productos
            WHERE Codigo_de_barras = %s AND id_usuario = %s
        """
        cur.execute(query, (codigo_barras, id_usuario_actual))
        producto = cur.fetchone()

        if not producto:
            return jsonify({"error": "Producto no encontrado"}), 200

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
        print(f"Error al buscar el producto: {e}")
        return jsonify({"error": "Error al buscar el producto"}), 500
    finally:
        cur.close()

@routes_blueprint.route('/productos/listar', methods=["GET"])
def listar_productos():
    # Verificar si el usuario está autenticado
    if not session.get('idusuario'):
        return redirect(url_for('login'))


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
            return redirect(url_for('listar_productos'))


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
        return redirect(url_for('listar_productos'))


    finally:
        cur.close()

@routes_blueprint.route('/descargar_productos', methods=['POST'])
def descargar_productos():
    id_usuario = session.get('idusuario')
    username = session.get('username')

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
    except Exception as e:
        print(f"Error al generar el archivo: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@routes_blueprint.route('/admin', methods=["GET", "POST"])
def admin():
    saludo = session.get('saludo')
    username = session.get('username')
    idplan = session.get('idplan')

    if request.method == 'POST':
        codigo_barras = request.form.get('codigo_barras')

    return render_template('admin.html', saludo=saludo, username=username, idplan=idplan)

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
    return render_template('inventario.html')

@routes_blueprint.route('/clientes', methods=['GET'], endpoint='clientes')
def clientes():
    """Página para gestionar los clientes."""
    return render_template('clientes.html')

@routes_blueprint.route('/configuracion', methods=['GET'], endpoint='configuracion')
def configuracion():
    """Página para gestionar la configuración."""
    return render_template('configuracion.html')