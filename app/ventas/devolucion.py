from flask import  session, jsonify

def devolucion_venta(idventa):
    from app.routes import mysql
    try:
        id_usuario = session.get('idusuario')  # Obtener el id_usuario de la sesión
        cursor = mysql.connection.cursor()
        
        # 1. Obtener el código de barras y la cantidad de los productos vendidos
        cursor.execute(
            "SELECT codigo_de_barras, cantidad FROM detalleventas WHERE idventa = %s AND idusuario = %s",
            (idventa, id_usuario)
        )
        productos_vendidos = cursor.fetchall()

        # 2. Actualizar la cantidad en la tabla 'productos'
        for producto in productos_vendidos:
            cursor.execute(
                'UPDATE productos SET cantidad = cantidad + %s WHERE codigo_de_barras = %s AND id_usuario = %s',
                (producto['cantidad'], producto['codigo_de_barras'], id_usuario)
            )

        # 3. Poner en cero el total de la venta y marcarla como devuelta
        cursor.execute(
            "UPDATE ventas SET totalventa = 0, devuelto = TRUE WHERE idventausuario = %s AND idusuario = %s",
            (idventa, id_usuario)
        )

        # 4. Poner en cero el precio_valor y precio_costo en detalleventas
        cursor.execute(
            "UPDATE detalleventas SET valor = 0, costo = 0 WHERE idventa = %s AND idusuario = %s",
            (idventa, id_usuario)
        )

        mysql.connection.commit()
        cursor.close()
        return jsonify({"success": "Devolución aplicada correctamente."}), 200
    except Exception as e:
        print(f"Error al aplicar la devolución: {e}")  # Asegúrate de que 'e' esté definido
        return jsonify({"error": "Error al aplicar la devolución."}), 500