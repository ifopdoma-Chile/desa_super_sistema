"""
HDO - Humboldt Digital Ocean
Configuración central del sistema
"""
import os

class Config:
    """Configuración base"""
    SECRET_KEY = os.environ.get("HDO_SECRET_KEY", "hdo-humboldt-digital-ocean-2026")
    
    # PostgreSQL en sapogis local
    DB_HOST = os.environ.get("HDO_DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("HDO_DB_PORT", 5432))
    DB_NAME = os.environ.get("HDO_DB_NAME", "hdo")
    DB_USER = os.environ.get("HDO_DB_USER", "postgres")
    DB_PASS = os.environ.get("HDO_DB_PASS", "")
    
    SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Para consultas sin SQLAlchemy
    DB_URI = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER}"
    
    # CMEMS credenciales
    CMEMS_USERNAME = "agarcia5"
    CMEMS_PASSWORD = "Dream.2004"
    
    # Región de interés: Chile costero
    LAT_MIN = -56.0
    LAT_MAX = -18.0
    LON_MIN = -85.0
    LON_MAX = -65.0
    
    # Rutas
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    NC_CACHE_DIR = os.path.join(DATA_DIR, "nc_cache")
    
    # Asegurar directorios de datos
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(NC_CACHE_DIR, exist_ok=True)

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
