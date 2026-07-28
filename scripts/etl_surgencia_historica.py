#!/usr/bin/env python3
"""
ETL: Cargar datos historicos de surgencia desde archivos NetCDF
- SST costera desde MUR GHRSST TSM
- Anomalia calculada respecto a climatologia movil
"""
import sys, os, glob, logging
from datetime import datetime, date
import numpy as np
import netCDF4 as nc

sys.path.insert(0, '/Data2/super_sistema')
os.environ.setdefault('HDO_DB_HOST', 'localhost')
os.environ.setdefault('HDO_DB_PORT', '5432')
os.environ.setdefault('HDO_DB_NAME', 'hdo')
os.environ.setdefault('HDO_DB_USER', 'postgres')
os.environ.setdefault('HDO_DB_PASS', 'hdo2026')

from app.servicios.db import query, insert_many

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Puntos de monitoreo HDO (latitud objetivo -> zona)
PUNTOS = [
    (-18.0, 'Norte Grande'), (-21.0, 'Norte Grande'), (-22.22, 'Norte Grande'),
    (-26.44, 'Norte Chico'), (-27.0, 'Norte Chico'),
    (-30.67, 'Centro'), (-34.0, 'Centro'), (-34.89, 'Centro'),
    (-39.11, 'Sur'), (-42.0, 'Sur'), (-43.33, 'Sur'),
    (-47.56, 'Austral'), (-51.0, 'Austral'), (-51.78, 'Austral'), (-56.0, 'Austral'),
]

LON_COSTA = -71.5

def find_nearest_lat(lat_array, target):
    idx = np.argmin(np.abs(lat_array - target))
    return idx, float(lat_array[idx])

def extract_sst_costera(nc_path, target_lats, lon_target=-71.5):
    try:
        ds = nc.Dataset(nc_path)
        lat = ds.variables['lat'][:]
        lon = ds.variables['lon'][:]
        lon_idx = np.argmin(np.abs(lon - lon_target))
        
        results = {}
        for tlat in target_lats:
            lat_idx, actual_lat = find_nearest_lat(lat, tlat)
            sst_data = ds.variables['analysed_sst'][0, lat_idx, lon_idx]
            if hasattr(sst_data, 'mask') and sst_data.mask:
                sst_c = None
            else:
                sst_c = float(sst_data) - 273.15
                if sst_c < -2 or sst_c > 35:
                    sst_c = None
            results[tlat] = sst_c
        
        ds.close()
        return results
    except Exception as e:
        logger.error(f'Error leyendo {nc_path}: {e}')
        return {}

def main():
    logger.info('=== ETL SURGENCIA HISTORICA ===')
    
    target_lats = [p[0] for p in PUNTOS]
    lat_to_zona = {p[0]: p[1] for p in PUNTOS}
    
    tsm_dir = '/Data/sapo2024/Historico/TSM/'
    tsm_files = sorted(glob.glob(os.path.join(tsm_dir, '*.nc')))
    logger.info(f'Encontrados {len(tsm_files)} archivos TSM')
    
    if not tsm_files:
        logger.error('No hay archivos TSM para procesar')
        return
    
    # Muestrear: ~500 puntos temporales
    step = max(1, len(tsm_files) // 500)
    sampled = tsm_files[::step]
    logger.info(f'Procesando {len(sampled)} archivos (step={step})')
    
    # Calcular climatologia
    logger.info('Calculando climatologia...')
    clim_sums = {lat: [] for lat in target_lats}
    for fpath in sampled[:50]:
        sst_vals = extract_sst_costera(fpath, target_lats)
        for lat, val in sst_vals.items():
            if val is not None:
                clim_sums[lat].append(val)
    
    climatologia = {}
    for lat, vals in clim_sums.items():
        if vals:
            climatologia[lat] = np.mean(vals)
            logger.info(f'  Lat {lat:.2f}: climatologia = {climatologia[lat]:.2f}C ({len(vals)} muestras)')
    
    # Procesar todos los archivos muestreados
    rows = []
    processed = 0
    for fpath in sampled:
        fname = os.path.basename(fpath)
        try:
            fecha_str = fname[:8]
            fecha = datetime.strptime(fecha_str, '%Y%m%d').date()
        except:
            continue
        
        sst_vals = extract_sst_costera(fpath, target_lats)
        
        for lat, sst in sst_vals.items():
            if sst is None:
                continue
            zona = lat_to_zona.get(lat)
            if zona is None:
                continue
            
            anomalia = sst - climatologia.get(lat, sst)
            rows.append((fecha, round(lat, 2), zona, None, None, round(sst, 2), round(anomalia, 2)))
        
        processed += 1
        if processed % 50 == 0:
            logger.info(f'  Procesados {processed}/{len(sampled)}, {len(rows)} registros')
    
    logger.info(f'Total registros generados: {len(rows)}')
    
    if rows:
        logger.info('Limpiando datos placeholder existentes...')
        query("DELETE FROM hdo.surgencia WHERE sst_costera = 0.00 AND anomalia_surgencia = 0.00", fetch=False)
        
        cols = ['fecha', 'latitud', 'zona', 'ekman_transport', 'cui', 'sst_costera', 'anomalia_surgencia']
        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            insert_many('surgencia', cols, batch)
            logger.info(f'  Insertado batch {i//batch_size + 1}: {len(batch)} registros')
        
        logger.info(f'=== ETL COMPLETADO: {len(rows)} registros insertados ===')
    else:
        logger.warning('No se generaron registros')

if __name__ == '__main__':
    main()
