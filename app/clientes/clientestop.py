from flask import render_template,session


def clientestop():

    from app.routes import mysql
    """Obtener los 10 clientes con más compras."""
    id_usuario = session.get('idusuario')
    cur = mysql.connection.cursor()

    query = """
        SELECT 
            COALESCE(c.idcliente, 0) AS idcliente,
            COALESCE(c.nombre, v.cliente, 'No suministrado') AS nombre,
            COALESCE(c.identificacion, v.idcliente, 'No suministrado') AS identificacion,
            COALESCE(c.contacto, 'No suministrado') AS contacto,
            SUM(v.totalventa) AS total_compras
        FROM ventas v
        LEFT JOIN clientes c ON c.identificacion = v.idcliente AND c.idusuario = %s
        WHERE v.idusuario = %s
        GROUP BY c.idcliente, c.nombre, c.identificacion, c.contacto, v.cliente, v.idcliente
        ORDER BY total_compras DESC
        LIMIT 10;
    """
    cur.execute(query, (id_usuario, id_usuario))
    
    clientes_top = cur.fetchall()
    
    cur.close()

    return render_template('clientes/clientes_top.html', clientes_top=clientes_top)