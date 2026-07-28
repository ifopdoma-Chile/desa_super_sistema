#!/usr/bin/env python3
"""
ETL: Calcular indicadores derivados
- HCS: SST promedio, anomalia, CHL, SSH, extension aguas frias
- Alertas segun umbrales
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from app.servicios.db import query, insert_many
from app.servicios.indicadores import (
    indice_hcs_sst, indice_extension_aguas_frias,
    calcular_productividad, generar_alertas
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def calcular_hcs():
    satelital = query("""
        SELECT fecha, variable, lat, lon, valor
        FROM hdo.productos_satelitales
        WHERE fecha >= NOW() - INTERVAL '30 days'
        ORDER BY fecha
    """)
    if not satelital:
        logger.warning("No hay datos satelitales para calcular HCS")
        return
    df = pd.DataFrame(satelital)
    hcs_rows = []
    for fecha in df["fecha"].unique():
        df_fecha = df[df["fecha"] == fecha]
        sst_data = df_fecha[df_fecha["variable"] == "sst"]
        chl_data = df_fecha[df_fecha["variable"] == "chl"]
        sst_prom = sst_data["valor"].mean() if not sst_data.empty else None
        chl_prom = chl_data["valor"].mean() if not chl_data.empty else None
        sst_anom = 0.0
        if sst_prom:
            sst_clim = df[df["variable"] == "sst"]["valor"].mean()
            sst_anom = sst_prom - sst_clim
        extension = indice_extension_aguas_frias(sst_data, umbral=18.0) if not sst_data.empty else 0
        prod = 0.001
        if not chl_data.empty and not sst_data.empty:
            prod = calcular_productividad(chl_data["valor"].mean(), sst_data["valor"].mean())
        def _to_native(v):
            return float(v) if v is not None else None
        hcs_rows.append((fecha, _to_native(sst_prom), _to_native(sst_anom), _to_native(chl_prom), 0.0, _to_native(prod), _to_native(extension)))
    if hcs_rows:
        cols = ["fecha", "sst_promedio", "sst_anomalia", "chl_promedio",
                "ssh_promedio", "productividad", "extension_aguas_frias"]
        insert_many("hcs_indicadores", cols, hcs_rows)
        logger.info(f"HCS calculado: {len(hcs_rows)} registros")

def calcular_alertas():
    enos = query("SELECT fecha, nino34 FROM hdo.enos_indicadores ORDER BY fecha DESC LIMIT 1")
    ph_data = query("SELECT fecha, ph FROM hdo.acidificacion ORDER BY fecha DESC LIMIT 1")
    cui_data = query("SELECT fecha, cui FROM hdo.surgencia ORDER BY fecha DESC LIMIT 1")
    alertas = []
    if enos:
        nino34 = enos[0]["nino34"]
        if nino34 and abs(nino34) >= 0.5:
            fase = "El Nino" if nino34 > 0 else "La Nina"
            severidad = "Debil"
            if abs(nino34) >= 2.0: severidad = "Extremo"
            elif abs(nino34) >= 1.5: severidad = "Fuerte"
            elif abs(nino34) >= 1.0: severidad = "Moderado"
            alertas.append((datetime.now().date(), "ENOS", severidad,
                          f"{fase} {severidad}: Nino 3.4 = {float(nino34):.2f}C", float(nino34), 0.5))
    if ph_data:
        ph = ph_data[0]["ph"]
        if ph and ph < 7.8:
            alertas.append((datetime.now().date(), "Acidificacion", "Critica",
                          f"pH critico: {float(ph):.2f} (umbral: 7.8)", float(ph), 7.8))
        elif ph and ph < 7.9:
            alertas.append((datetime.now().date(), "Acidificacion", "Alerta",
                          f"pH bajo: {float(ph):.2f} (umbral: 7.8)", float(ph), 7.8))
    if alertas:
        query("UPDATE hdo.alertas SET activa = FALSE WHERE activa = TRUE", fetch=False)
        cols = ["fecha", "tipo", "severidad", "descripcion", "valor", "umbral"]
        insert_many("alertas", cols, alertas)
        logger.info(f"Alertas generadas: {len(alertas)}")

def main():
    logger.info("=== CALCULANDO INDICADORES ===")
    calcular_hcs()
    calcular_alertas()
    logger.info("=== CALCULO COMPLETADO ===")

if __name__ == "__main__":
    main()
