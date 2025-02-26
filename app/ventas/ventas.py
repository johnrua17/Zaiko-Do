from flask import session,jsonify,render_template


def venta():
    # Verificar si el usuario está autenticado
    if not session.get('idusuario'):
        return redirect(url_for('auth.login'))
    return render_template('ventas/ventas_realizadas.html')

def obtenerventa():
    from app.routes import mysql
    # Verificar si el usuario está autenticado
    if not session.get('idusuario'):
        return jsonify({"error": "Usuario no autenticado"}), 403

    id_usuario_actual = session.get('idusuario')

    try:
        cur = mysql.connection.cursor()
        # Obtener las ventas realizadas por el usuario
        query = """
        SELECT * FROM ventas WHERE idusuario = %s
        """
        cur.execute(query, (id_usuario_actual,))
        ventas = cur.fetchall()
        cur.close()

        # Convertir las ventas a una lista de diccionarios
        ventas_json = []
        for venta in ventas:
            venta_dict = {
                "idventausuario": venta["idventausuario"],
                "totalventa": float(venta["totalventa"]),
                "fecha": venta["fecha"].strftime("%d/%m/%y"),  # Formatear fecha
                "hora": str(venta["hora"]),  # Convertir timedelta a cadena
                "metodo_pago": venta["metodo_pago"],
                "cliente": venta["cliente"]
            }
            ventas_json.append(venta_dict)

        # Devolver los datos en formato JSON
        return jsonify(ventas_json)
    except Exception as e:
        print(f"Error al obtener las ventas: {e}")
        return jsonify({"error": "Error al cargar las ventas."}), 500