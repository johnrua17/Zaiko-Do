# config.py
import os
import pytz
from dotenv import load_dotenv

# Carga las variables definidas en .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    MYSQL_HOST = os.getenv('MYSQL_HOST')
    MYSQL_USER = os.getenv('MYSQL_USER')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
    MYSQL_DB = os.getenv('MYSQL_DB')
    MAIL_PASSWORD =  os.getenv("SECRET_MAIL")

    MYSQL_CURSORCLASS = os.getenv('MYSQL_CURSORCLASS', 'DictCursor')
    
    # Obtiene la zona horaria y crea el objeto pytz correspondiente
    ZONE_BOGOTA = pytz.timezone(os.getenv('ZONE_BOGOTA', 'America/Bogota'))
    
    MAX_INTENTOS = int(os.getenv('MAX_INTENTOS', 3))
    TIEMPO_BLOQUEO_MINUTOS = int(os.getenv('TIEMPO_BLOQUEO_MINUTOS', 15))
