"""
HDO - Humboldt Digital Ocean | Servicios de base de datos
=========================================================
Version con datos locales IFOP/DOMA + globales.
Actualizado: 26 julio 2026
"""
import pandas as pd
from datetime import datetime, timedelta
from app.servicios.db import query, get_db
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# ENOS (El Nino / La Nina) - datos globales + locales
# ============================================================================

def get_enos_ultimos(limite=60):
    sql = """
        SELECT fecha, oni, nino34, soi, hci, mei, nino12_hdo, fuente

        FROM hdo.enos_indicadores
        ORDER BY fecha DESC LIMIT %s
    """
    return query(sql, (limite,))

def get_enos_historico(desde=None, hasta=None):
    sql = "SELECT fecha, oni, nino34, soi, hci, mei, nino12_hdo, fuente FROM hdo.enos_indicadores WHERE 1=1"
    params = []
    if desde:
        sql += " AND fecha >= %s"; params.append(desde)
    if hasta:
        sql += " AND fecha <= %s"; params.append(hasta)
    sql += " ORDER BY fecha ASC"
    return query(sql, params)

# ============================================================================
# DOMA - TSM por zona IFOP
# ============================================================================

def get_doma_tsm_zonas():
    sql = "SELECT DISTINCT zona FROM hdo.doma_indicador_tsm ORDER BY zona"
    return query(sql)

def get_doma_tsm(zona=None, limite=365):
    sql = "SELECT zona, fecha, mean_temp, min_temp, max_temp, num_puntos FROM hdo.doma_indicador_tsm WHERE 1=1"
    params = []
    if zona:
        sql += " AND zona = %s"; params.append(zona)
    sql += " ORDER BY fecha DESC LIMIT %s"; params.append(limite)
    return query(sql, params)

def get_doma_tsm_ultimo():
    sql = """
        SELECT DISTINCT ON (zona) zona, fecha, mean_temp, min_temp, max_temp, num_puntos
        FROM hdo.doma_indicador_tsm ORDER BY zona, fecha DESC
    """
    return query(sql)

def get_doma_tsm_historico(zona, desde=None, hasta=None):
    sql = "SELECT fecha, mean_temp, min_temp, max_temp FROM hdo.doma_indicador_tsm WHERE zona = %s"
    params = [zona]
    if desde:
        sql += " AND fecha >= %s"; params.append(desde)
    if hasta:
        sql += " AND fecha <= %s"; params.append(hasta)
    sql += " ORDER BY fecha ASC"
    return query(sql, params)

# ============================================================================
# DOMA - Clorofila por zona
# ============================================================================

def get_doma_clo(zona=None, limite=365):
    sql = "SELECT zona, fecha, mean_temp as mean_chl, min_temp as min_chl, max_temp as max_chl, num_puntos FROM hdo.doma_indicador_clo WHERE 1=1"
    params = []
    if zona:
        sql += " AND zona = %s"; params.append(zona)
    sql += " ORDER BY fecha DESC LIMIT %s"; params.append(limite)
    return query(sql, params)

def get_doma_clo_ultimo():
    sql = """
        SELECT DISTINCT ON (zona) zona, fecha, mean_temp as mean_chl, min_temp as min_chl, max_temp as max_chl
        FROM hdo.doma_indicador_clo ORDER BY zona, fecha DESC
    """
    return query(sql)

# ============================================================================
# DOMA - Nivel del mar
# ============================================================================

def get_doma_nivelmar(zona=None, limite=365):
    sql = "SELECT zona, fecha, mean_nivelmar, min_nivelmar, max_nivelmar FROM hdo.doma_indicador_nivelmar WHERE 1=1"
    params = []
    if zona:
        sql += " AND zona = %s"; params.append(zona)
    sql += " ORDER BY fecha DESC LIMIT %s"; params.append(limite)
    return query(sql, params)

def get_doma_nivelmar_ultimo():
    sql = """
        SELECT DISTINCT ON (zona) zona, fecha, mean_nivelmar, min_nivelmar, max_nivelmar
        FROM hdo.doma_indicador_nivelmar ORDER BY zona, fecha DESC
    """
    return query(sql)

# ============================================================================
# DOMA - Anomalias TSM
# ============================================================================

def get_doma_atsm(zona=None, limite=365):
    sql = "SELECT zona, fecha, mean_temp, min_temp, max_temp FROM hdo.doma_indicador_atsm WHERE 1=1"
    params = []
    if zona:
        sql += " AND zona = %s"; params.append(zona)
    sql += " ORDER BY fecha DESC LIMIT %s"; params.append(limite)
    return query(sql, params)

def get_doma_atsm_ultimo():
    sql = """
        SELECT DISTINCT ON (zona) zona, fecha, mean_temp, min_temp, max_temp
        FROM hdo.doma_indicador_atsm ORDER BY zona, fecha DESC
    """
    return query(sql)

# ============================================================================
# Nino 3.4 y SOI locales IFOP
# ============================================================================

def get_nino34_local(desde_anio=None, hasta_anio=None):
    sql = "SELECT anio as ano, mes, dato FROM hdo.nino34_local WHERE 1=1"
    params = []
    if desde_anio:
        sql += " AND anio >= %s"; params.append(desde_anio)
    if hasta_anio:
        sql += " AND anio <= %s"; params.append(hasta_anio)
    sql += " ORDER BY anio ASC, mes ASC"
    return query(sql, params)

def get_soi_local(desde_anio=None, hasta_anio=None):
    sql = "SELECT anio as ano, mes, dato FROM hdo.soi_local WHERE 1=1"
    params = []
    if desde_anio:
        sql += " AND anio >= %s"; params.append(desde_anio)
    if hasta_anio:
        sql += " AND anio <= %s"; params.append(hasta_anio)
    sql += " ORDER BY anio ASC, mes ASC"
    return query(sql, params)

# ============================================================================
# Estaciones meteorologicas IFOP
# ============================================================================

def get_estaciones_meteo(activas_only=True):
    sql = "SELECT id, nombre, latitud, longitud, activa, fuente FROM hdo.estaciones_meteorologicas"
    if activas_only:
        sql += " WHERE activa = true"
    sql += " ORDER BY nombre"
    return query(sql)

def get_ultimas_lecturas_por_estacion(estacion_id=None):
    if estacion_id:
        sql = """
            SELECT e.nombre as estacion, le.variable, le.valor, le.unidad, le.horamedicion
            FROM hdo.lecturas_estaciones le
            JOIN hdo.estaciones_meteorologicas e ON e.id = le.estacion_id
            WHERE le.estacion_id = %s
            ORDER BY le.horamedicion DESC LIMIT 50
        """
        return query(sql, (estacion_id,))
    else:
        sql = """
            SELECT DISTINCT ON (e.id, le.variable)
                e.id as estacion_id, e.nombre as estacion, e.latitud, e.longitud,
                le.variable, le.valor, le.unidad, le.horamedicion
            FROM hdo.estaciones_meteorologicas e
            JOIN hdo.lecturas_estaciones le ON le.estacion_id = e.id
            WHERE e.activa = true
            ORDER BY e.id, le.variable, le.horamedicion DESC
        """
        return query(sql)

def get_serie_estacion(estacion_id, variable=None, dias=30):
    sql = """
        SELECT le.horamedicion, le.variable, le.valor, le.unidad
        FROM hdo.lecturas_estaciones le
        WHERE le.estacion_id = %s AND le.horamedicion >= NOW() - INTERVAL '%s days'
    """
    params = [estacion_id, dias]
    if variable:
        sql += " AND le.variable = %s"; params.append(variable)
    sql += " ORDER BY le.horamedicion ASC"
    return query(sql, params)

# ============================================================================
# Perfiles CTD DOMA
# ============================================================================

def get_doma_perfiles_estaciones():
    sql = "SELECT DISTINCT estacion FROM hdo.doma_datos_estacion ORDER BY estacion"
    return query(sql)

def get_doma_perfiles(estacion=None, limite=500):
    sql = "SELECT estacion, fecha_ano, mes, dia, profundidad, temp, salinidad, sigma_t, oxigeno, clorofila_a FROM hdo.doma_datos_estacion WHERE 1=1"
    params = []
    if estacion:
        sql += " AND estacion = %s"; params.append(estacion)
    sql += " ORDER BY fecha_ano DESC, mes DESC, dia DESC, profundidad ASC LIMIT %s"
    params.append(limite)
    return query(sql, params)

# ============================================================================
# SHOA / SAPO
# ============================================================================

def get_sho_puertos():
    sql = "SELECT codigo, latitud, longitud, region FROM hdo.sho_puerto ORDER BY codigo"
    return query(sql)

def get_sho_climatologia(puerto=None, variable=None):
    sql = "SELECT puerto, variable, mes, media, sd, p05, p25, p50, p75, p95, n_anios FROM hdo.sho_climatologia WHERE 1=1"
    params = []
    if puerto:
        sql += " AND puerto = %s"; params.append(puerto)
    if variable:
        sql += " AND variable = %s"; params.append(variable)
    sql += " ORDER BY puerto, variable, mes"
    return query(sql, params)

def get_sho_mensual(puerto=None, variable=None, limite=500):
    sql = "SELECT puerto, variable, anio, mes, valor_mean, valor_min, valor_max, n_obs FROM hdo.sho_mensual WHERE 1=1"
    params = []
    if puerto:
        sql += " AND puerto = %s"; params.append(puerto)
    if variable:
        sql += " AND variable = %s"; params.append(variable)
    sql += " ORDER BY anio DESC, mes DESC LIMIT %s"
    params.append(limite)
    return query(sql, params)

# ============================================================================
# Datos satelitales locales
# ============================================================================

def get_satelital_local(variable=None, limite=1000):
    sql = "SELECT fecha, variable, lat, lon, valor, fuente FROM hdo.satelital_local WHERE 1=1"
    params = []
    if variable:
        sql += " AND variable = %s"; params.append(variable)
    sql += " ORDER BY fecha DESC LIMIT %s"
    params.append(limite)
    return query(sql, params)

# ============================================================================
# Surgencia, HCS, Acidificacion, Alertas (original)
# ============================================================================

def get_surgencia_ultimos(limite=100):
    sql = "SELECT fecha, latitud, zona, ekman_transport, cui, sst_costera, anomalia_surgencia FROM hdo.surgencia ORDER BY fecha DESC LIMIT %s"
    return query(sql, (limite,))

def get_surgencia_por_zona(zona, limite=365):
    sql = "SELECT fecha, latitud, ekman_transport, cui, sst_costera FROM hdo.surgencia WHERE zona = %s ORDER BY fecha DESC LIMIT %s"
    return query(sql, (zona, limite))

def get_hcs_ultimos(limite=60):
    sql = "SELECT fecha, sst_promedio, sst_anomalia, chl_promedio, ssh_promedio, productividad, extension_aguas_frias FROM hdo.hcs_indicadores ORDER BY fecha DESC LIMIT %s"
    return query(sql, (limite,))

def get_acidificacion_ultimos(limite=100):
    sql = "SELECT fecha, lat, lon, ph, aragonito, ph_anomalia, profundidad FROM hdo.acidificacion ORDER BY fecha DESC LIMIT %s"
    return query(sql, (limite,))

def get_alertas_activas():
    sql = "SELECT fecha, tipo, severidad, descripcion, valor, umbral FROM hdo.alertas WHERE activa = TRUE ORDER BY fecha DESC, severidad ASC"
    return query(sql)

def get_satelital(variable, limite=1000):
    sql = "SELECT fecha, lat, lon, valor, unidad, fuente FROM hdo.productos_satelitales WHERE variable = %s ORDER BY fecha DESC LIMIT %s"
    return query(sql, (variable, limite))

# ============================================================================
# Dashboard
# ============================================================================

def get_estadisticas_dashboard():
    stats = {}
    stats["enos"] = get_enos_ultimos(1)[0] if get_enos_ultimos(1) else None
    stats["surgencia"] = get_surgencia_ultimos(1)[0] if get_surgencia_ultimos(1) else None
    stats["hcs"] = get_hcs_ultimos(1)[0] if get_hcs_ultimos(1) else None
    stats["alertas"] = get_alertas_activas()
    stats["alertas_count"] = len(stats["alertas"])
    stats["acidificacion"] = get_acidificacion_ultimos(1)[0] if get_acidificacion_ultimos(1) else None

    # Nuevos: datos locales IFOP
    try:
        tsm = get_doma_tsm_ultimo()
        stats["doma_tsm"] = tsm if tsm else None
        stats["doma_tsm_count"] = len(tsm) if tsm else 0
    except:
        stats["doma_tsm"] = None; stats["doma_tsm_count"] = 0

    try:
        estaciones = get_estaciones_meteo()
        stats["estaciones_count"] = len(estaciones)
    except:
        stats["estaciones_count"] = 0

    try:
        lecturas = get_ultimas_lecturas_por_estacion()
        stats["lecturas_count"] = len(lecturas)
    except:
        stats["lecturas_count"] = 0

    stats["ultima_actualizacion"] = datetime.now()
    return stats
