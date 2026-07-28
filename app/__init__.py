"""
HDO - Humboldt Digital Ocean
Factory Flask application
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app(config_name=None):
    """Crear y configurar la aplicación Flask"""
    app = Flask(__name__, static_folder="static", template_folder="templates")
    
    if config_name is None:
        config_name = os.environ.get("HDO_CONFIG", "production")
    
    from config import config_by_name
    app.config.from_object(config_by_name.get(config_name, config_by_name["production"]))
    app.config["APPLICATION_ROOT"] = "/hdo/"
    
    # SQLAlchemy
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace(":postgres@", ":postgres:@")
    
    # Registrar blueprints y rutas
    from app.routes import main_bp
    from app.routes_api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/hdo/api/v1")
    
    # Inicializar DB
    db.init_app(app)
    
    # Contexto para templates
    @app.context_processor
    def inject_globals():
        return {
            "app_name": "Humboldt Digital Ocean",
            "app_version": "1.0.0",
            "app_url": "/hdo/"
        }
    
    return app
