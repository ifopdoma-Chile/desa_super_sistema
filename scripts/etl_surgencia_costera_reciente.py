#!/usr/bin/env python3
"""
ETL: Completar sst_costera y anomalia_surgencia reales (TSM MUR GHRSST)
para las fechas recientes que el ETL diario de viento inserta como 0.0.
"""
import sys, os, glob, logging
from datetime import datetime, timedelta
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
    logger.info('=== ETL SURGENCIA COSTERA RECIENTE (MUR) ===')

    hoy = datetime.now()
    hace_45d = hoy - timedelta(days=45)
    target_lats = [p[0] for p in PUNTOS]
    lat_to_zona = {p[0]: p[1] for p in PUNTOS}

    tsm_dir = '/Data/sapo2024/Historico/TSM/'
    # Solo archivos de los últimos 45 días
    tsm_files = []
    for f in sorted(glob.glob(os.path.join(tsm_dir, '*.nc'))):
        try:
            fecha_str = os.path.basename(f)[:8]
            fecha = datetime.strptime(fecha_str, '%Y%m%d')
        except Exception:
            continue
        if fecha >= hace_45d:
            tsm_files.append(f)
    logger.info(f'Archivos TSM de los últimos 45 días: {len(tsm_files)}')

    if not tsm_files:
        logger.error('No hay archivos TSM recientes')
        return

    # Climatología (media del año completo si está disponible, si no media de la ventana)
    clim_sums = {lat: [] for lat in target_lats}
    all_files = sorted(glob.glob(os.path.join(tsm_dir, '*.nc')))
    sample = all_files[::max(1, len(all_files)//100)][:100]
    for fpath in sample:
        sst_vals = extract_sst_costera(fpath, target_lats)
        for lat, val in sst_vals.items():
            if val is not None:
                clim_sums[lat].append(val)

    climatologia = {}
    for lat, vals in clim_sums.items():
        if vals:
            climatologia[lat] = np.mean(vals)
            logger.info(f'  Lat {lat:.2f}: climatologia = {climatologia[lat]:.2f}C ({len(vals)} muestras)')

    # Procesar archivos recientes
    rows = []
    for fpath in tsm_files:
        fname = os.path.basename(fpath)
        try:
            fecha_str = fname[:8]
            fecha = datetime.strptime(fecha_str, '%Y%m%d').date()
        except Exception:
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

    logger.info(f'Registros generados: {len(rows)}')

    if rows:
        # Actualizar sst_costera/anomalia en las filas de viento existentes.
        # La grilla de viento (0.125°) no coincide exactamente con los PUNTOS
        # objetivo, así que se actualiza el rango de latitud cercano (±0.08°).
        updated = 0
        for (fecha, lat, zona, _, _, sst, anom) in rows:
            n = query(
                "UPDATE hdo.surgencia SET sst_costera=%s, anomalia_surgencia=%s "
                "WHERE fecha=%s AND zona=%s AND latitud BETWEEN %s AND %s",
                params=(sst, anom, fecha, zona, lat - 0.08, lat + 0.08), fetch=False)
            updated += 1
        logger.info(f'Actualizadas {updated} filas de surgencia con SST costera real')
    else:
        logger.warning('No se generaron registros')

    logger.info('=== ETL SURGENCIA COSTERA COMPLETADO ===')

if __name__ == '__main__':
    main()
