#!/usr/bin/env python3
"""
ETL: Descargar datos satelitales desde Copernicus Marine (CMEMS)
Frecuencia: diaria (SST, CHL, viento), mensual (BGC)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from app.servicios.cmems import descargar_sst, descargar_viento, descargar_chl, descargar_bgc
from app.servicios.db import insert_many, query
from app.servicios.indicadores import calcular_ekman_transport, calcular_cui, zona_para_lat

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def _coord_name(ds, *candidates):
    """Return the first coordinate name found in the dataset"""
    for c in candidates:
        if c in ds.coords or c in ds.dims:
            return c
    return candidates[0]  # fallback

def procesar_sst(ds):
    rows = []
    lat_name = _coord_name(ds, "latitude", "lat", "Latitude")
    lon_name = _coord_name(ds, "longitude", "lon", "Longitude")
    sst_var = "analysed_sst" if "analysed_sst" in ds else ("sst" if "sst" in ds else None)
    if sst_var is None:
        logger.warning("No SST variable found in dataset")
        return []

    # Detectar unidades: OSTIA L4 entrega SST en Kelvin. Convertir a °C.
    units = str(getattr(ds[sst_var], "units", "")).lower()
    convert_k = "kelvin" in units or units.startswith("k")

    lats = ds[lat_name].values
    lons = ds[lon_name].values
    for t_idx in range(len(ds.time)):
        fecha = pd.Timestamp(ds.time.values[t_idx]).to_pydatetime()
        vals = np.asarray(ds[sst_var][t_idx, :, :].values, dtype=float)
        if convert_k:
            vals = vals - 273.15
        mask = ~np.isnan(vals)
        lat2d, lon2d = np.meshgrid(lats, lons, indexing="ij")
        lat_flat = lat2d[mask]
        lon_flat = lon2d[mask]
        val_flat = vals[mask]
        for i in range(len(lat_flat)):
            rows.append((fecha.date(), "sst", float(lat_flat[i]),
                        float(lon_flat[i]), float(val_flat[i]), "degC", "CMEMS"))
    if rows:
        cols = ["fecha", "variable", "lat", "lon", "valor", "unidad", "fuente"]
        for i in range(0, len(rows), 5000):
            insert_many("productos_satelitales", cols, rows[i:i+5000])
        logger.info(f"SST insertada: {len(rows)} registros")
    return rows

def procesar_viento(ds):
    surgencia_rows = []
    lat_name = _coord_name(ds, "latitude", "lat", "Latitude")
    lon_name = _coord_name(ds, "longitude", "lon", "Longitude")
    lats = ds[lat_name].values
    lons = ds[lon_name].values
    u10_name = "eastward_wind" if "eastward_wind" in ds else ("u10" if "u10" in ds else None)
    v10_name = "northward_wind" if "northward_wind" in ds else ("v10" if "v10" in ds else None)
    if u10_name is None or v10_name is None:
        logger.warning("No u10/v10 (o eastward/northward_wind) en dataset de viento")
        return []
    lat2d, lon2d = np.meshgrid(lats, lons, indexing="ij")
    # Agrupar por día: promedio de viento diario (el producto es horario)
    u_daily = ds[u10_name].resample(time="1D").mean(dim="time")
    v_daily = ds[v10_name].resample(time="1D").mean(dim="time")
    for t_idx in range(len(u_daily.time)):
        fecha = pd.Timestamp(u_daily.time.values[t_idx]).to_pydatetime()
        u10 = np.asarray(u_daily[t_idx, :, :].values, dtype=float)
        v10 = np.asarray(v_daily[t_idx, :, :].values, dtype=float)
        mask = ~(np.isnan(u10) | np.isnan(v10))
        lat_flat = lat2d[mask]
        lon_flat = lon2d[mask]
        u_flat = u10[mask]
        v_flat = v10[mask]
        for i in range(len(lat_flat)):
            lat = float(lat_flat[i])
            lon = float(lon_flat[i])
            cui = calcular_cui(u_flat[i], v_flat[i], lat, lon)
            ekman_z, ekman_m = calcular_ekman_transport(u_flat[i], v_flat[i], lat)
            zona = zona_para_lat(lat)
            surgencia_rows.append((fecha.date(), lat, zona, float(ekman_z),
                                  float(cui) if not hasattr(cui, "__len__") else float(cui[0]),
                                  0.0, 0.0))
    if surgencia_rows:
        cols = ["fecha", "latitud", "zona", "ekman_transport", "cui", "sst_costera", "anomalia_surgencia"]
        for i in range(0, len(surgencia_rows), 5000):
            insert_many("surgencia", cols, surgencia_rows[i:i+5000])
        logger.info(f"Surgencia calculada: {len(surgencia_rows)} registros")
    return surgencia_rows

def procesar_chl(ds):
    rows = []
    lat_name = _coord_name(ds, "latitude", "lat", "Latitude")
    lon_name = _coord_name(ds, "longitude", "lon", "Longitude")
    chl_var = "CHL" if "CHL" in ds else ("chl" if "chl" in ds else None)
    if chl_var is None:
        logger.warning("No CHL variable found in dataset")
        return []
    lats = ds[lat_name].values
    lons = ds[lon_name].values
    lat2d, lon2d = np.meshgrid(lats, lons, indexing="ij")
    for t_idx in range(len(ds.time)):
        fecha = pd.Timestamp(ds.time.values[t_idx]).to_pydatetime()
        vals = np.asarray(ds[chl_var][t_idx, :, :].values, dtype=float)
        mask = ~np.isnan(vals)
        lat_flat = lat2d[mask]
        lon_flat = lon2d[mask]
        val_flat = vals[mask]
        for i in range(len(lat_flat)):
            rows.append((fecha.date(), "chl", float(lat_flat[i]),
                        float(lon_flat[i]), float(val_flat[i]), "mg/m3", "CMEMS"))
    if rows:
        cols = ["fecha", "variable", "lat", "lon", "valor", "unidad", "fuente"]
        for i in range(0, len(rows), 5000):
            insert_many("productos_satelitales", cols, rows[i:i+5000])
        logger.info(f"CHL insertada: {len(rows)} registros")

def procesar_bgc(ds):
    rows = []
    lat_name = _coord_name(ds, "latitude", "lat", "Latitude")
    lon_name = _coord_name(ds, "longitude", "lon", "Longitude")
    lats = ds[lat_name].values
    lons = ds[lon_name].values
    ph_name = "ph" if "ph" in ds else None
    if ph_name is None:
        logger.warning("No variable ph en dataset BGC")
        return
    lat2d, lon2d = np.meshgrid(lats, lons, indexing="ij")
    # El dataset BGC trae depth (modelo 3D). Usar superficie (depth index 0).
    ph_da = ds[ph_name]
    if "depth" in ph_da.dims:
        ph_da = ph_da.isel(depth=0)
    elif "lev" in ph_da.dims:
        ph_da = ph_da.isel(lev=0)
    for t_idx in range(len(ds.time)):
        fecha = pd.Timestamp(ds.time.values[t_idx]).to_pydatetime()
        ph_vals = np.asarray(ph_da[t_idx, :, :].values, dtype=float)
        mask = ~np.isnan(ph_vals)
        lat_flat = lat2d[mask]
        lon_flat = lon2d[mask]
        ph_flat = ph_vals[mask]
        for i in range(len(lat_flat)):
            rows.append((fecha.date(), float(lat_flat[i]), float(lon_flat[i]),
                        float(ph_flat[i]), None, 0.0, 0))
    if rows:
        cols = ["fecha", "lat", "lon", "ph", "aragonito", "ph_anomalia", "profundidad"]
        for i in range(0, len(rows), 5000):
            insert_many("acidificacion", cols, rows[i:i+5000])
        logger.info(f"BGC insertado: {len(rows)} registros")

def _limpiar_ventana(table, fecha_min, fecha_max, variable=None):
    """Borrar registros del periodo que se va a reinsertar (evita duplicados).
    Si `variable` se indica, solo se borran registros de esa variable
    (productos_satelitales comparte la tabla con SST y CHL)."""
    try:
        if variable:
            query(f"DELETE FROM hdo.{table} WHERE fecha >= %s AND fecha <= %s AND variable = %s",
                  (fecha_min.strftime("%Y-%m-%d"), fecha_max.strftime("%Y-%m-%d"), variable),
                  fetch=False)
        else:
            query(f"DELETE FROM hdo.{table} WHERE fecha >= %s AND fecha <= %s",
                  (fecha_min.strftime("%Y-%m-%d"), fecha_max.strftime("%Y-%m-%d")),
                  fetch=False)
        logger.info(f"Limpieza {table} {fecha_min:%Y-%m-%d} a {fecha_max:%Y-%m-%d} (variable={variable})")
    except Exception as e:
        logger.warning(f"No se pudo limpiar {table}: {e}")

def main():
    hoy = datetime.now()
    hace_7d = hoy - timedelta(days=7)
    hace_30d = hoy - timedelta(days=30)
    logger.info("=== INICIANDO DESCARGA CMEMS ===")
    logger.info("Descargando SST...")
    ds_sst = descargar_sst(hace_7d, hoy)
    if ds_sst is not None:
        _limpiar_ventana("productos_satelitales", hace_7d, hoy, variable="sst")
        procesar_sst(ds_sst)
    logger.info("Descargando viento...")
    ds_viento = descargar_viento(hace_7d, hoy)
    if ds_viento is not None:
        _limpiar_ventana("surgencia", hace_7d, hoy)
        procesar_viento(ds_viento)
    logger.info("Descargando CHL...")
    ds_chl = descargar_chl(hace_30d, hoy)
    if ds_chl is not None:
        _limpiar_ventana("productos_satelitales", hace_30d, hoy, variable="chl")
        procesar_chl(ds_chl)
    logger.info("Descargando BGC...")
    ds_bgc = descargar_bgc(hace_30d, hoy)
    if ds_bgc is not None:
        _limpiar_ventana("acidificacion", hace_30d, hoy)
        procesar_bgc(ds_bgc)
    logger.info("=== DESCARGA CMEMS COMPLETADA ===")

if __name__ == "__main__":
    main()
