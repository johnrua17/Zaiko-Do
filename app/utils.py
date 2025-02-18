from datetime import datetime
from app.config import Config
from functools import wraps
from flask import session, redirect, url_for
# Función para obtener la hora actual en la zona horaria de Bogotá
def obtener_hora_actual_bogota():
    """
    Retorna la hora actual en la zona horaria de Bogotá.
    """
    return datetime.now(Config.ZONE_BOGOTA)

# Función para limpiar datos usando bleach
def limpiar_datos(dato):
    """
    Limpia los datos proporcionados para evitar vulnerabilidades como XSS.
    """
    import bleach
    return bleach.clean(dato)

# Función para formatear mensajes de error
def formatear_error(mensaje):
    """
    Formatea un mensaje de error para mostrarlo en la interfaz de usuario.
    """
    return {"error": True, "mensaje": mensaje}

# Función para calcular el tiempo restante para desbloquear una cuenta
def calcular_tiempo_restante(bloqueado_hasta):
    """
    Calcula el tiempo restante en minutos para desbloquear una cuenta.
    """
    ahora = obtener_hora_actual_bogota()
    tiempo_restante = bloqueado_hasta.replace(tzinfo=Config.ZONE_BOGOTA) - ahora
    minutos_restantes = int(tiempo_restante.total_seconds() / 60)
    return minutos_restantes

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('idusuario'):
            return redirect(url_for('routes.login')) 
        return f(*args, **kwargs)
    return decorated_function