"""
Servicio de cálculo de indicadores oceanográficos
- Transporte de Ekman y CUI (surgencia)
- Índices HCS (Corriente de Humboldt)
- Anomalías y climatologías
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Constantes físicas
RHO_AIR = 1.22  # kg/m3 densidad del aire
RHO_WATER = 1025.0  # kg/m3 densidad del agua
CD = 1.3e-3  # coeficiente de arrastre
C_DRAG = CD * RHO_AIR / RHO_WATER  # constante para Ekman
F_CORIOLIS_SCALE = 2 * 7.2921e-5  # 2 * omega

# Zonas costeras de Chile
ZONAS_COSTERAS = {
    "Norte Grande": ([-18.0, -24.0], [-72.0, -70.0]),
    "Norte Chico": ([-24.0, -30.0], [-73.0, -71.0]),
    "Centro": ([-30.0, -38.0], [-74.0, -72.0]),
    "Sur": ([-38.0, -46.0], [-76.0, -73.0]),
    "Austral": ([-46.0, -56.0], [-78.0, -65.0])
}

def calcular_ekman_transport(u10, v10, lat):
    """
    Calcular transporte de Ekman desde viento
    Ekman transport (m2/s) = (C_drag * rho_air / rho_water) / f * (viento cruzado a la costa)
    Para Chile (costa N-S): componente perpendicular = u10 (zonal)
    """
    f = F_CORIOLIS_SCALE * np.sin(np.radians(np.abs(lat)))
    f = np.maximum(f, 1e-6)  # evitar división por cero en el ecuador
    
    # Transporte de Ekman zonal y meridional
    transport_zonal = (C_DRAG / f) * v10  # Ekman hacia el oeste/este
    transport_meridional = -(C_DRAG / f) * u10  # Ekman hacia norte/sur
    
    return transport_zonal, transport_meridional

def calcular_cui(u10, v10, lat, lon):
    """
    Calcular Coastal Upwelling Index (CUI)
    Sigue metodología NOAA PFEL: componente del viento paralela a la costa
    Para costa chilena (orientación N-S): la componente sur del viento genera surgencia
    """
    # Para la costa de Chile (mayormente N-S):
    # El viento del sur (v10 negativo en hemisferio sur) genera transporte de Ekman hacia el oeste → surgencia
    # CUI = transporte de Ekman perpendicular a la costa (hacia el oeste)
    f = F_CORIOLIS_SCALE * np.sin(np.radians(np.abs(lat)))
    f = np.maximum(f, 1e-6)
    
    CUI = -(C_DRAG / f) * v10 * (-1)  # positivo = surgencia, negativo = downwelling
    return CUI

def calcular_anomalia(datos, climatologia=None, ventana=30):
    """Calcular anomalía respecto a climatología"""
    if climatologia is None:
        # Si no hay climatología, usar la media de toda la serie
        climatologia = datos.mean(skipna=True)
    return datos - climatologia

def calcular_climatologia_mensual(df, columna_valor, columna_fecha="fecha"):
    """Calcular climatología mensual (promedio histórico por mes)"""
    df = df.copy()
    df["mes"] = pd.to_datetime(df[columna_fecha]).dt.month
    clim = df.groupby("mes")[columna_valor].mean()
    return clim

def zona_para_lat(lat):
    """Determinar zona costera para una latitud"""
    for zona, (lat_range, _) in ZONAS_COSTERAS.items():
        min_lat = min(lat_range)
        max_lat = max(lat_range)
        if min_lat <= lat <= max_lat:
            return zona
    return "Desconocida"

def indice_hcs_sst(df_sst, lat_min=-40.0, lat_max=-18.0, lon_min=-85.0, lon_max=-70.0):
    """
    Calcular SST promedio del HCS (Sistema de Corriente de Humboldt)
    """
    mask = (
        (df_sst["lat"] >= lat_min) & (df_sst["lat"] <= lat_max) &
        (df_sst["lon"] >= lon_min) & (df_sst["lon"] <= lon_max)
    )
    return df_sst[mask]["valor"].mean()

def indice_extension_aguas_frias(df_sst, umbral=18.0):
    """
    Calcular extensión de aguas frías (SST < umbral) en el HCS
    Retorna área en km2 (aproximación)
    """
    frias = df_sst[df_sst["valor"] < umbral]
    if frias.empty:
        return 0.0
    # Aproximación: 1 grado ~ 111km
    area_aprox = len(frias) * 111 * 111 * 0.5  # media celda en km2
    return area_aprox

def generar_alertas(indicadores):
    """
    Generar alertas según umbrales definidos
    """
    alertas = []
    
    # ENOS: Niño 3.4 > ±0.5°C
    if "nino34" in indicadores and indicadores["nino34"] is not None:
        val = abs(indicadores["nino34"])
        if val >= 2.0:
            severidad = "Extremo"
        elif val >= 1.5:
            severidad = "Fuerte"
        elif val >= 1.0:
            severidad = "Moderado"
        elif val >= 0.5:
            severidad = "Débil"
        else:
            severidad = None
        
        if severidad:
            fase = "El Niño" if indicadores["nino34"] > 0 else "La Niña"
            alertas.append({
                "tipo": "ENOS",
                "severidad": severidad,
                "descripcion": f"{fase} {severidad}: Niño 3.4 = {indicadores[nino34]:.2f}°C",
                "valor": indicadores["nino34"],
                "umbral": 0.5
            })
    
    # Acidificación: pH < 7.8
    if "ph" in indicadores and indicadores["ph"] is not None:
        if indicadores["ph"] < 7.8:
            alertas.append({
                "tipo": "Acidificación",
                "severidad": "Crítica",
                "descripcion": f"pH crítico: {indicadores[ph]:.2f} (umbral: 7.8)",
                "valor": indicadores["ph"],
                "umbral": 7.8
            })
        elif indicadores["ph"] < 7.9:
            alertas.append({
                "tipo": "Acidificación",
                "severidad": "Alerta",
                "descripcion": f"pH bajo: {indicadores[ph]:.2f} (umbral: 7.8)",
                "valor": indicadores["ph"],
                "umbral": 7.8
            })
    
    return alertas

def calcular_productividad(chl, sst, par=None):
    """
    Estimar productividad primaria desde CHL (modelo simple)
    PP = CHL * PAR * P_opt (simplificación)
    """
    if par is None:
        par = 50  # valor típico PAR en E/m2/día
    
    # Modelo muy simplificado (VGPM-like)
    pb_opt = 1.0 + 0.05 * (sst - 20)  # tasa fotosintética óptima
    pp = chl * par * np.maximum(pb_opt, 0.1) * 0.01  # mg C/m3/día
    return np.maximum(pp, 0.001)
