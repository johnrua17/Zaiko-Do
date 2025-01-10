import pytz

class Config:
    SECRET_KEY = "Zaikodo"
    MYSQL_HOST = "bb8xmknvzukpsmgzmsf2-mysql.services.clever-cloud.com"
    MYSQL_USER = "uh5cr91ugvcpsou7"
    MYSQL_PASSWORD = "BFXoblKJ8YszXDOyQSHx"
    MYSQL_DB = "bb8xmknvzukpsmgzmsf2"
    MYSQL_CURSORCLASS = "DictCursor"
    ZONE_BOGOTA = pytz.timezone("America/Bogota")
    MAX_INTENTOS = 3
    TIEMPO_BLOQUEO_MINUTOS = 15