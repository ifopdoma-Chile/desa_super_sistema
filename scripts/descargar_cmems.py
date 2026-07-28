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
    
    lats = ds[lat_name].values
    lons = ds[lon_name].values
    for t_idx in range(len(ds.time)):
        fecha = pd.Timestamp(ds.time.values[t_idx]).to_pydatetime()
        for lat_idx in range(len(lats)):
            for lon_idx in range(len(lons)):
                val = float(ds[sst_var][t_idx, lat_idx, lon_idx].values)
                if not np.isnan(val):
                    rows.append((fecha.date(), "sst", float(lats[lat_idx]),
                                float(lons[lon_idx]), val, "degC", "CMEMS"))
    if rows:
        cols = ["fecha", "variable", "lat", "lon", "valor", "unidad", "fuente"]
        for i in range(0, len(rows), 500):
            insert_many("productos_satelitales", cols, rows[i:i+500])
        logger.info(f"SST insertada: {len(rows)} registros")
    return rows

def procesar_viento(ds):
    surgencia_rows = []
    lat_name = _coord_name(ds, "latitude", "lat", "Latitude")
    lon_name = _coord_name(ds, "longitude", "lon", "Longitude")
    lats = ds[lat_name].values
    lons = ds[lon_name].values
    for t_idx in range(len(ds.time)):
        fecha = pd.Timestamp(ds.time.values[t_idx]).to_pydatetime()
        for lat_idx in range(len(lats)):
            for lon_idx in range(len(lons)):
                lat = float(lats[lat_idx])
                lon = float(lons[lon_idx])
                u10 = float(ds.u10[t_idx, lat_idx, lon_idx].values)
                v10 = float(ds.v10[t_idx, lat_idx, lon_idx].values)
                if np.isnan(u10) or np.isnan(v10):
                    continue
                cui = calcular_cui(u10, v10, lat, lon)
                ekman_z, ekman_m = calcular_ekman_transport(u10, v10, lat)
                zona = zona_para_lat(lat)
                surgencia_rows.append((fecha.date(), lat, zona, float(ekman_z),
                                      float(cui) if not hasattr(cui, "__len__") else float(cui[0]),
                                      0.0, 0.0))
    if surgencia_rows:
        cols = ["fecha", "latitud", "zona", "ekman_transport", "cui", "sst_costera", "anomalia_surgencia"]
        insert_many("surgencia", cols, surgencia_rows)
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
    for t_idx in range(len(ds.time)):
        fecha = pd.Timestamp(ds.time.values[t_idx]).to_pydatetime()
        for lat_idx in range(len(lats)):
            for lon_idx in range(len(lons)):
                val = float(ds[chl_var][t_idx, lat_idx, lon_idx].values)
                if not np.isnan(val):
                    rows.append((fecha.date(), "chl", float(lats[lat_idx]),
                                float(lons[lon_idx]), val, "mg/m3", "CMEMS"))
    if rows:
        cols = ["fecha", "variable", "lat", "lon", "valor", "unidad", "fuente"]
        for i in range(0, len(rows), 500):
            insert_many("productos_satelitales", cols, rows[i:i+500])
        logger.info(f"CHL insertada: {len(rows)} registros")

def procesar_bgc(ds):
    rows = []
    lat_name = _coord_name(ds, "latitude", "lat", "Latitude")
    lon_name = _coord_name(ds, "longitude", "lon", "Longitude")
    lats = ds[lat_name].values
    lons = ds[lon_name].values
    for t_idx in range(len(ds.time)):
        fecha = pd.Timestamp(ds.time.values[t_idx]).to_pydatetime()
        for lat_idx in range(len(lats)):
            for lon_idx in range(len(lons)):
                ph_val = float(ds.ph[t_idx, lat_idx, lon_idx].values) if "ph" in ds else None
                arag_val = float(ds.aragonite_saturation[t_idx, lat_idx, lon_idx].values) if "aragonite_saturation" in ds else None
                if ph_val is not None and not np.isnan(ph_val):
                    rows.append((fecha.date(),
                                float(lats[lat_idx]),
                                float(lons[lon_idx]),
                                ph_val,
                                float(arag_val) if arag_val and not np.isnan(arag_val) else None,
                                0.0, 0))
    if rows:
        cols = ["fecha", "lat", "lon", "ph", "aragonito", "ph_anomalia", "profundidad"]
        insert_many("acidificacion", cols, rows)
        logger.info(f"BGC insertado: {len(rows)} registros")

def main():
    hoy = datetime.now()
    hace_7d = hoy - timedelta(days=7)
    hace_30d = hoy - timedelta(days=30)
    logger.info("=== INICIANDO DESCARGA CMEMS ===")
    logger.info("Descargando SST...")
    ds_sst = descargar_sst(hace_7d, hoy)
    if ds_sst is not None:
        procesar_sst(ds_sst)
    logger.info("Descargando viento...")
    ds_viento = descargar_viento(hace_7d, hoy)
    if ds_viento is not None:
        procesar_viento(ds_viento)
    logger.info("Descargando CHL...")
    ds_chl = descargar_chl(hace_30d, hoy)
    if ds_chl is not None:
        procesar_chl(ds_chl)
    logger.info("Descargando BGC...")
    ds_bgc = descargar_bgc(hace_30d, hoy)
    if ds_bgc is not None:
        procesar_bgc(ds_bgc)
    logger.info("=== DESCARGA CMEMS COMPLETADA ===")

if __name__ == "__main__":
    main()
