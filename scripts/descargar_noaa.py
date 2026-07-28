#!/usr/bin/env python3
"""
ETL: Descargar indicadores ENOS desde NOAA CPC
Frecuencia: mensual (post publicacion NOAA)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timedelta
import pandas as pd
from app.servicios.noaa import descargar_todos
from app.servicios.db import insert_many, query, get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def poblar_enos():
    logger.info("Iniciando descarga de indices NOAA...")
    df = descargar_todos()
    
    if df.empty:
        logger.warning("No se descargaron datos NOAA")
        return 0
    
    # Limpiar datos existentes del periodo
    fecha_min = df["fecha"].min().strftime("%Y-%m-%d")
    fecha_max = df["fecha"].max().strftime("%Y-%m-%d")
    logger.info(f"Periodo: {fecha_min} a {fecha_max}")
    
    query("DELETE FROM hdo.enos_indicadores WHERE fecha >= %s AND fecha <= %s", 
          (fecha_min, fecha_max), fetch=False)
    
    # Insertar datos nuevos
    rows = []
    for _, row in df.iterrows():
        fecha = row.get("fecha")
        if pd.isna(fecha):
            continue
        rows.append((
            fecha,
            row.get("oni") if not pd.isna(row.get("oni")) else None,
            row.get("nino34") if not pd.isna(row.get("nino34")) else None,
            row.get("soi") if not pd.isna(row.get("soi")) else None,
            None, None, None,
            "NOAA CPC"
        ))
    
    if rows:
        columns = ["fecha", "oni", "nino34", "soi", "hci", "mei", "nino12_hdo", "fuente"]
        count = insert_many("enos_indicadores", columns, rows)
        logger.info(f"Insertados {count} registros en enos_indicadores")
    
    logger.info("Descarga NOAA completada")
    return len(rows)

if __name__ == "__main__":
    poblar_enos()
