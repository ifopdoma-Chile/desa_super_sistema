"""
Servicio de descarga de indices NOAA CPC
Indicadores: ONI, Nino 3.4, SOI
"""
import re
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

NOAA_BASE = "https://www.cpc.ncep.noaa.gov/data/indices"

URLS = {
    "oni": f"{NOAA_BASE}/oni.ascii.txt",
    "nino34": f"{NOAA_BASE}/ersst5.nino.mth.91-20.ascii",
    "soi": f"{NOAA_BASE}/soi",
}

SEASON_MAP = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}

def descargar_oni():
    try:
        resp = requests.get(URLS["oni"], timeout=30)
        resp.raise_for_status()
        lines = resp.text.strip().split("\n")
        data = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    season = parts[0]
                    yr = int(parts[1])
                    anom = float(parts[3])
                    if season in SEASON_MAP and 1950 <= yr <= 2030:
                        mon = SEASON_MAP[season]
                        data.append({"fecha": datetime(yr, mon, 1), "oni": anom})
                except (ValueError, IndexError):
                    continue
        df = pd.DataFrame(data)
        logger.info(f"ONI descargado: {len(df)} registros")
        return df
    except Exception as e:
        logger.error(f"Error descargando ONI: {e}")
        return pd.DataFrame()

def descargar_nino34():
    """Descargar Nino 3.4 (ERSSTv5)
    Columnas: YR, MON, NINO1+2, ANOM1, NINO3, ANOM3, NINO4, ANOM4, NINO3.4, ANOM34"""
    try:
        resp = requests.get(URLS["nino34"], timeout=30)
        resp.raise_for_status()
        lines = resp.text.strip().split("\n")
        data = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 10:
                try:
                    yr = int(parts[0])
                    mon = int(parts[1])
                    # Column 10 (index 9) is the NINO3.4 anomaly
                    nino34_anom = float(parts[9])
                    if yr < 1950 or yr > 2030 or mon < 1 or mon > 12:
                        continue
                    if -10 < nino34_anom < 10:
                        data.append({"fecha": datetime(yr, mon, 1), "nino34": nino34_anom})
                except Exception:
                    pass
        df = pd.DataFrame(data)
        logger.info(f"Nino 3.4 descargado: {len(df)} registros")
        return df
    except Exception as e:
        logger.error(f"Error descargando Nino 3.4: {e}")
        return pd.DataFrame()

def descargar_soi():
    try:
        resp = requests.get(URLS["soi"], timeout=30)
        resp.raise_for_status()
        lines = resp.text.strip().split("\n")
        data = []
        for line in lines:
            parts = re.split(r"\s+", line.strip())
            if len(parts) < 2:
                continue
            try:
                yr = int(parts[0])
                if yr < 1950 or yr > 2030:
                    continue
                # Reconstruir: puede que -999.9 esté pegado al valor anterior
                raw = " ".join(parts[1:])
                # Insertar espacio antes de -999.9 si está pegado
                raw = re.sub(r"(\d)(-999\.9)", r"\1 \2", raw)
                raw = re.sub(r"(\d)(-999)", r"\1 -999", raw)
                month_vals = raw.split()
                for i, val in enumerate(month_vals[:12]):
                    try:
                        soi = float(val)
                        if -50 < soi < 50:
                            data.append({"fecha": datetime(yr, i + 1, 1), "soi": soi})
                    except ValueError:
                        continue
            except ValueError:
                continue
        df = pd.DataFrame(data)
        logger.info(f"SOI descargado: {len(df)} registros")
        return df
    except Exception as e:
        logger.error(f"Error descargando SOI: {e}")
        return pd.DataFrame()

def descargar_todos():
    df_oni = descargar_oni()
    df_nino = descargar_nino34()
    df_soi = descargar_soi()
    dfs = [df.set_index("fecha") for df in [df_oni, df_nino, df_soi] if not df.empty]
    if dfs:
        combined = dfs[0].join(dfs[1:], how="outer").reset_index()
        combined = combined.sort_values("fecha")
        logger.info(f"Indices NOAA combinados: {len(combined)} registros")
        return combined
    return pd.DataFrame()
