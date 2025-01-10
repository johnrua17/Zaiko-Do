from flask_mysqldb import MySQL

mysql = MySQL()

def init_db(app):
    """
    Inicializa la extensión MySQL con la configuración de la aplicación Flask.
    """
    mysql.init_app(app)

def get_connection():
    """
    Obtiene una conexión a la base de datos MySQL.
    Retorna un objeto de conexión que se puede utilizar para realizar consultas.
    """
    return mysql.connection

def execute_query(query, params=None):
    """
    Ejecuta una consulta SQL con parámetros opcionales.
    Retorna los resultados de la consulta o None si no hay resultados.

    Args:
        query (str): Consulta SQL a ejecutar.
        params (tuple): Parámetros opcionales para la consulta.

    Returns:
        list or dict: Resultados de la consulta.
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, params or ())
        connection.commit()
        return cursor.fetchall()
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        connection.rollback()
        return None
    finally:
        cursor.close()

def execute_update(query, params=None):
    """
    Ejecuta una consulta SQL de actualización o inserción con parámetros opcionales.
    Retorna True si la operación fue exitosa, False en caso contrario.

    Args:
        query (str): Consulta SQL a ejecutar.
        params (tuple): Parámetros opcionales para la consulta.

    Returns:
        bool: True si la operación fue exitosa, False en caso contrario.
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(query, params or ())
        connection.commit()
        return True
    except Exception as e:
        print(f"Error al ejecutar la actualización: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()
