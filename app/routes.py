"""
Rutas principales de la aplicación web HDO
"""
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify, request

main_bp = Blueprint("main", __name__)

@main_bp.route("/hdo/")
def index():
    """Página principal - Dashboard consolidado"""
    return render_template("index.html", titulo="Humboldt Digital Ocean")

@main_bp.route("/hdo/enos")
def enos():
    """Dashboard ENOS"""
    return render_template("dashboard_enos.html", titulo="ENOS - El Niño / La Niña")

@main_bp.route("/hdo/surgencia")
def surgencia():
    """Dashboard Surgencia Costera"""
    return render_template("dashboard_surgencia.html", titulo="Surgencia Costera")

@main_bp.route("/hdo/humboldt-current")
def humboldt():
    """Dashboard Corriente de Humboldt"""
    return render_template("dashboard_humboldt.html", titulo="Corriente de Humboldt")

@main_bp.route("/hdo/acidificacion")
def acidificacion():
    """Dashboard Acidificación Oceánica"""
    return render_template("dashboard_humboldt.html", titulo="Acidificación Oceánica",
                           modulo="acidificacion")

@main_bp.route("/hdo/productividad")
def productividad():
    """Dashboard Productividad Primaria"""
    return render_template("dashboard_humboldt.html", titulo="Productividad Primaria",
                           modulo="productividad")

@main_bp.route("/hdo/alertas")
def alertas():
    """Panel de Alertas"""
    return render_template("dashboard_humboldt.html", titulo="Alertas",
                           modulo="alertas")

@main_bp.route("/hdo/mapa")
def mapa():
    """Mapa interactivo"""
    return render_template("dashboard_humboldt.html", titulo="Mapa Interactivo",
                           modulo="mapa")

@main_bp.route("/hdo/api/docs")
def api_docs():
    """Documentación de la API"""
    return render_template("api_docs.html", titulo="API REST - Documentación")
