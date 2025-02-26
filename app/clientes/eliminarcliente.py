from flask import session,jsonify

def eliminarcliente(idcliente):
    from app.routes import mysql
    """Eliminar un cliente por su ID."""
    if not session.get('idusuario'):
        return jsonify({'error': 'No autenticado'}), 401

    cur = mysql.connection.cursor()
    
    # Verificar si el cliente pertenece al usuario autenticado
    cur.execute("SELECT idusuario FROM clientes WHERE idcliente = %s", (idcliente,))
    result = cur.fetchone()
    
    if not result or result["idusuario"] != session.get('idusuario'):
        return jsonify({'error': 'Acceso no autorizado'}), 403

    # Eliminar el cliente
    cur.execute("DELETE FROM clientes WHERE idcliente = %s", (idcliente,))
    mysql.connection.commit()
    cur.close()

    return jsonify({'message': 'Cliente eliminado correctamente'}), 200