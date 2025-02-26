from flask import session,jsonify
from datetime import datetime, timedelta
def detallesventa(idventa):
    from app.routes import mysql
    try:
        idusuario = session.get("idusuario", None)
        if idusuario is None:
            return jsonify({"error": "Usuario no autenticado"}), 403

        print(f"Consultando detalles de venta: idventa={idventa}, idusuario={idusuario}")
        
        cur = mysql.connection.cursor()

        # Obtener detalles de los productos de la venta
        query_detalles = "SELECT * FROM detalleventas WHERE idventa = %s AND idusuario = %s"
        cur.execute(query_detalles, (idventa, idusuario))
        detalles = cur.fetchall()

        # Obtener información general de la venta
        query_venta = "SELECT totalventa, pagocon, fecha, hora, metodo_pago, devuelto, cliente, idcliente FROM ventas WHERE idventausuario = %s AND idusuario = %s"
        cur.execute(query_venta, (idventa, idusuario))
        venta = cur.fetchone()
        

        cur.close()

        if not detalles or not venta:
            print("No se encontraron detalles para la venta.")
            return jsonify({"error": "No se encontraron detalles para la venta."}), 404

        print("Detalles encontrados:", detalles)
        print("Información de la venta:", venta)

        # Convertir timedelta a una cadena en formato HH:MM:SS
        if isinstance(venta['hora'], timedelta):
            total_seconds = int(venta['hora'].total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            venta['hora'] = f"{hours:02}:{minutes:02}:{seconds:02}"

        # Combinar los datos en un solo JSON
        return jsonify({
            "detalles": detalles,
            "venta": venta
        })

    except Exception as e:
        print(f"Error al obtener los detalles de la venta: {e}")
        return jsonify({"error": "Error al cargar los detalles."}), 500
