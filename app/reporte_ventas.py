from app import mysql
from datetime import datetime
import pytz

timezone = pytz.timezone('America/Bogota')
fecha_actual = datetime.now(timezone)
fecha = fecha_actual.date()

def query_reportes(id_usuario_actual, fecha_inicio, fecha_fin):
    try:
        with mysql.connection.cursor() as cur:
            # 1️⃣ Categorías vendidas
            query_categorias_vendidas = """
            SELECT
                categoria,
                SUM(CAST(cantidad AS DECIMAL(10,2)) * CAST(valor AS DECIMAL(10,2))) AS ingresos_brutos
            FROM
                detalleventas
            WHERE
                idusuario = %s
                AND fecha BETWEEN %s AND %s
            GROUP BY
                categoria;
            """
            cur.execute(query_categorias_vendidas, (id_usuario_actual, fecha_inicio, fecha_fin))
            categorias_vendidas = cur.fetchall()

            # 2️⃣ Ganancias por categoría
            query_ganancias_categoria = """
            SELECT
                categoria,
                SUM((CAST(valor AS DECIMAL(10,2)) - CAST(costo AS DECIMAL(10,2))) * CAST(cantidad AS DECIMAL(10,2))) AS ganancia_total
            FROM
                detalleventas
            WHERE
                idusuario = %s
                AND fecha BETWEEN %s AND %s
            GROUP BY
                categoria;
            """
            cur.execute(query_ganancias_categoria, (id_usuario_actual, fecha_inicio, fecha_fin))
            ganancias_categoria = cur.fetchall()

            # 3️⃣ Ventas por método de pago
            query_ventas_metodo_pago = """
                SELECT
                    v.metodo_pago,
                    SUM(v.totalventa) AS total_ventas
                FROM
                    ventas v
                WHERE
                    v.idusuario = %s
                    AND v.fecha BETWEEN %s AND %s
                GROUP BY
                    v.metodo_pago;
            """
            cur.execute(query_ventas_metodo_pago, (id_usuario_actual, fecha_inicio, fecha_fin))
            ventas_metodo_pago = cur.fetchall()

            # 4️⃣ Ventas del día actual
            query_ventas_dia = """
            SELECT
                SUM(CAST(cantidad AS DECIMAL(10,2)) * CAST(valor AS DECIMAL(10,2))) AS ingresos_brutos_hoy
            FROM
                detalleventas
            WHERE
                idusuario = %s
                AND fecha = %s;
            """
            cur.execute(query_ventas_dia, (id_usuario_actual, fecha))
            ventas_dia_result = cur.fetchone()
            ventas_dia = ventas_dia_result['ingresos_brutos_hoy'] if ventas_dia_result and ventas_dia_result['ingresos_brutos_hoy'] else 0

            # 5️⃣ Ganancias del día actual
            query_ganancias_dia = """
            SELECT
                SUM((CAST(valor AS DECIMAL(10,2)) - CAST(costo AS DECIMAL(10,2))) * CAST(cantidad AS DECIMAL(10,2))) AS ganancia_total
            FROM
                detalleventas
            WHERE
                idusuario = %s
                AND fecha = %s;
            """
            cur.execute(query_ganancias_dia, (id_usuario_actual, fecha))
            ganancias_dia_result = cur.fetchone()
            ganancias_dia = ganancias_dia_result['ganancia_total'] if ganancias_dia_result and ganancias_dia_result['ganancia_total'] else 0

        return [categorias_vendidas, ganancias_categoria, ventas_metodo_pago, ventas_dia, ganancias_dia]

    except Exception as e:
        print(f"Error en query_reportes: {e}")
        return None
