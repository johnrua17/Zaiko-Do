from flask import jsonify,session,request
def editarcliente(idcliente):
    from app.routes import mysql
    """Editar un cliente existente."""
    if not session.get('idusuario'):
        return jsonify({'error': 'No autenticado'}), 401

    data = request.json
    nombre = data.get('nombre')
    contacto = data.get('contacto')

    cur = mysql.connection.cursor()
    
    # Verificar si el cliente pertenece al usuario autenticado
    cur.execute("SELECT idusuario FROM clientes WHERE idcliente = %s", (idcliente,))
    result = cur.fetchone()
    
    if not result or result["idusuario"] != session.get('idusuario'):
        return jsonify({'error': 'Acceso no autorizado'}), 403

    # Actualizar el cliente
    query = """
        UPDATE clientes 
        SET nombre = %s, contacto = %s
        WHERE idcliente = %s and idusuario =%s
    """
    cur.execute(query, (nombre, contacto, idcliente,session.get('idusuario')))
    mysql.connection.commit()
    cur.close()

    return jsonify({'message': 'Cliente actualizado correctamente'}), 200
