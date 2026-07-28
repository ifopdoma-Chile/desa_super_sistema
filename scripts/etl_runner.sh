#!/bin/bash
# ETL Runner para HDO - Humboldt Digital Ocean
# Ejecuta todos los pipelines de datos secuencialmente
cd /Data2/super_sistema
source /Data2/super_sistema/venv/bin/activate
export HDO_DB_HOST=localhost HDO_DB_PORT=5432 HDO_DB_NAME=hdo HDO_DB_USER=postgres HDO_DB_PASS=hdo2026
export CMEMS_USERNAME=agarcia5
export CMEMS_PASSWORD=Dream.2004

echo "[$(date)] HDO ETL: Iniciando pipelines..."
echo "[$(date)] 1. Descargando NOAA..."
python3 scripts/descargar_noaa.py 2>&1
echo "[$(date)] 2. Descargando CMEMS..."
python3 scripts/descargar_cmems.py 2>&1
echo "[$(date)] 3. Calculando indicadores..."
python3 scripts/calcular_indicadores.py 2>&1
echo "[$(date)] HDO ETL: Completado."
