"""
Servicio de descarga de datos Copernicus Marine (CMEMS)
SST, CHL, viento, pH
Datasets NRT vigentes (catálogo 2026):
- SST:  METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2 (OSTIA L4 0.05°)
- Viento: cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H (L4 NRT 0.125°)
- CHL:  cmems_obs-oc_glo_bgc-plankton_nrt_l3-multi-4km_P1D (GlobColour L3 NRT)
- BGC:  cmems_mod_glo_bgc-car_anfc_0.25deg_P1D-m (ph, talk, dissic)
"""
import os
import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Configuración regional
LAT_MIN, LAT_MAX = -56.0, -18.0
LON_MIN, LON_MAX = -85.0, -65.0

# Datasets CMEMS reales
DATASET_SST = "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2"
DATASET_VIENTO = "cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H"
DATASET_CHL = "cmems_obs-oc_glo_bgc-plankton_nrt_l3-multi-4km_P1D"
DATASET_BGC = "cmems_mod_glo_bgc-car_anfc_0.25deg_P1D-m"

# Variables
VAR_SST = "analysed_sst"
VAR_U10, VAR_V10 = "eastward_wind", "northward_wind"
VAR_CHL = "CHL"
VAR_PH = "ph"

# Directorio de caché
DATA_DIR = "/Data2/super_sistema/data"
NC_CACHE = os.path.join(DATA_DIR, "nc_cache")
os.makedirs(NC_CACHE, exist_ok=True)

def get_cmems_client():
    """Obtener cliente CMEMS (lazy load)"""
    try:
        from copernicusmarine import subset
        return subset
    except ImportError:
        logger.warning("copernicusmarine no instalado, usando stub")
        return None

def descargar_sst(fecha_inicio, fecha_fin, force=False):
    """
    Descargar SST diaria desde CMEMS (OSTIA L4 NRT 0.05°)
    """
    cache_file = os.path.join(NC_CACHE, f"sst_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.nc")

    if os.path.exists(cache_file) and not force:
        logger.info(f"Usando caché: {cache_file}")
        return xr.open_dataset(cache_file)

    try:
        subset = get_cmems_client()
        if subset:
            subset(
                dataset_id=DATASET_SST,
                variables=[VAR_SST],
                minimum_longitude=LON_MIN,
                maximum_longitude=LON_MAX,
                minimum_latitude=LAT_MIN,
                maximum_latitude=LAT_MAX,
                start_datetime=fecha_inicio.strftime("%Y-%m-%dT00:00:00"),
                end_datetime=fecha_fin.strftime("%Y-%m-%dT23:59:59"),
                output_filename=os.path.basename(cache_file),
                output_directory=NC_CACHE,
            )
            ds = xr.open_dataset(cache_file)
        else:
            # Datos sintéticos para desarrollo (sin copernicusmarine)
            ds = _crear_datos_sinteticos_sst(fecha_inicio, fecha_fin)
            ds.to_netcdf(cache_file)

        logger.info(f"SST descargada: {cache_file}")
        return ds
    except Exception as e:
        logger.error(f"Error descargando SST CMEMS real: {e}, usando sintéticos")
        return _crear_datos_sinteticos_sst(fecha_inicio, fecha_fin)

def descargar_viento(fecha_inicio, fecha_fin, force=False):
    """
    Descargar viento (u10, v10) desde CMEMS (L4 NRT 0.125°)
    """
    cache_file = os.path.join(NC_CACHE, f"viento_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.nc")

    if os.path.exists(cache_file) and not force:
        return xr.open_dataset(cache_file)

    try:
        subset = get_cmems_client()
        if subset:
            subset(
                dataset_id=DATASET_VIENTO,
                variables=[VAR_U10, VAR_V10],
                minimum_longitude=LON_MIN,
                maximum_longitude=LON_MAX,
                minimum_latitude=LAT_MIN,
                maximum_latitude=LAT_MAX,
                start_datetime=fecha_inicio.strftime("%Y-%m-%dT00:00:00"),
                end_datetime=fecha_fin.strftime("%Y-%m-%dT23:59:59"),
                output_filename=os.path.basename(cache_file),
                output_directory=NC_CACHE,
            )
            ds = xr.open_dataset(cache_file)
        else:
            ds = _crear_datos_sinteticos_viento(fecha_inicio, fecha_fin)
            ds.to_netcdf(cache_file)
        return ds
    except Exception as e:
        logger.error(f"Error descargando viento: {e}")
        return _crear_datos_sinteticos_viento(fecha_inicio, fecha_fin)

def descargar_chl(fecha_inicio, fecha_fin, force=False):
    """Descargar Clorofila-a desde CMEMS (GlobColour L3 NRT 4km)"""
    cache_file = os.path.join(NC_CACHE, f"chl_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.nc")

    if os.path.exists(cache_file) and not force:
        return xr.open_dataset(cache_file)

    try:
        subset = get_cmems_client()
        if subset:
            subset(
                dataset_id=DATASET_CHL,
                variables=[VAR_CHL],
                minimum_longitude=LON_MIN,
                maximum_longitude=LON_MAX,
                minimum_latitude=LAT_MIN,
                maximum_latitude=LAT_MAX,
                start_datetime=fecha_inicio.strftime("%Y-%m-%dT00:00:00"),
                end_datetime=fecha_fin.strftime("%Y-%m-%dT23:59:59"),
                output_filename=os.path.basename(cache_file),
                output_directory=NC_CACHE,
            )
            ds = xr.open_dataset(cache_file)
        else:
            ds = _crear_datos_sinteticos_chl(fecha_inicio, fecha_fin)
            ds.to_netcdf(cache_file)
        return ds
    except Exception as e:
        logger.error(f"Error descargando CHL CMEMS real: {e}, usando sintéticos")
        return _crear_datos_sinteticos_chl(fecha_inicio, fecha_fin)

def descargar_bgc(fecha_inicio, fecha_fin, force=False):
    """
    Descargar biogeoquímicos (pH) desde CMEMS (Global BGC Analysis/Forecast)
    """
    cache_file = os.path.join(NC_CACHE, f"bgc_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.nc")

    if os.path.exists(cache_file) and not force:
        return xr.open_dataset(cache_file)

    try:
        subset = get_cmems_client()
        if subset:
            subset(
                dataset_id=DATASET_BGC,
                variables=[VAR_PH],
                minimum_longitude=LON_MIN,
                maximum_longitude=LON_MAX,
                minimum_latitude=LAT_MIN,
                maximum_latitude=LAT_MAX,
                start_datetime=fecha_inicio.strftime("%Y-%m-%dT00:00:00"),
                end_datetime=fecha_fin.strftime("%Y-%m-%dT23:59:59"),
                output_filename=os.path.basename(cache_file),
                output_directory=NC_CACHE,
            )
            ds = xr.open_dataset(cache_file)
        else:
            ds = _crear_datos_sinteticos_bgc(fecha_inicio, fecha_fin)
            ds.to_netcdf(cache_file)
        return ds
    except Exception as e:
        logger.error(f"Error descargando BGC: {e}")
        return _crear_datos_sinteticos_bgc(fecha_inicio, fecha_fin)

# ============================================================================
# Funciones para datos sintéticos (desarrollo / fallback)
# ============================================================================

def _crear_datos_sinteticos_sst(fecha_inicio, fecha_fin):
    """Crear datos SST sintéticos para desarrollo"""
    import numpy as np
    times = pd.date_range(fecha_inicio, fecha_fin, freq="D")
    lats = np.linspace(LAT_MIN, LAT_MAX, 20)
    lons = np.linspace(LON_MIN, LON_MAX, 20)
    
    # SST: gradiente latitudinal + upwelling costero + ruido
    lon2d, lat2d = np.meshgrid(lons, lats)
    coast_dist = np.abs(lon2d + 75) / 10  # proxy distancia a costa
    
    data = np.zeros((len(times), len(lats), len(lons)))
    for t_idx, t in enumerate(times):
        season = 2 * np.pi * (t.timetuple().tm_yday / 365.0)
        base_sst = 22 - 0.4 * (lat2d + 20)  # gradiente latitudinal
        seasonal = 3 * np.sin(season + np.pi * (lat2d + 30) / 60)
        upwelling = -2 * np.exp(-coast_dist)  # surgencia costera
        noise = np.random.randn(len(lats), len(lons)) * 0.5
        data[t_idx] = base_sst + seasonal + upwelling + noise
    
    ds = xr.Dataset(
        {"analysed_sst": (["time", "lat", "lon"], data)},
        coords={"time": times, "lat": lats, "lon": lons},
        attrs={"units": "degC", "source": "HDO synthetic (CMEMS proxy)"}
    )
    return ds

def _crear_datos_sinteticos_viento(fecha_inicio, fecha_fin):
    """Crear datos de viento sintéticos"""
    times = pd.date_range(fecha_inicio, fecha_fin, freq="D")
    lats = np.linspace(LAT_MIN, LAT_MAX, 10)
    lons = np.linspace(LON_MIN, LON_MAX, 10)
    lon2d, lat2d = np.meshgrid(lons, lats)
    
    n_t, n_lat, n_lon = len(times), len(lats), len(lons)
    
    u10 = np.random.randn(n_t, n_lat, n_lon) * 3 + 2
    v10 = np.random.randn(n_t, n_lat, n_lon) * 3 - 5  # viento sur predominante
    
    ds = xr.Dataset(
        {"u10": (["time", "lat", "lon"], u10), "v10": (["time", "lat", "lon"], v10)},
        coords={"time": times, "lat": lats, "lon": lons},
        attrs={"units": "m/s", "source": "HDO synthetic"}
    )
    return ds

def _crear_datos_sinteticos_chl(fecha_inicio, fecha_fin):
    """Crear datos CHL sintéticos"""
    times = pd.date_range(fecha_inicio, fecha_fin, freq="D")
    lats = np.linspace(LAT_MIN, LAT_MAX, 15)
    lons = np.linspace(LON_MIN, LON_MAX, 15)
    lon2d, lat2d = np.meshgrid(lons, lats)
    
    n_t, n_lat, n_lon = len(times), len(lats), len(lons)
    
    # CHL: más alta en costa y en primavera/verano
    coast_dist = np.abs(lon2d + 75) / 10
    data = np.zeros((n_t, n_lat, n_lon))
    for t_idx, t in enumerate(times):
        season = 2 * np.pi * (t.timetuple().tm_yday / 365.0)
        base = 0.5 * np.exp(-coast_dist)  # costa: alta
        bloom = 2 * np.exp(-coast_dist) * np.maximum(0, np.sin(season - np.pi/2))
        noise = np.random.lognormal(0, 0.3, (n_lat, n_lon)) * 0.1
        data[t_idx] = base + bloom + noise
    
    ds = xr.Dataset(
        {"chl": (["time", "lat", "lon"], data)},
        coords={"time": times, "lat": lats, "lon": lons},
        attrs={"units": "mg/m3", "source": "HDO synthetic"}
    )
    return ds

def _crear_datos_sinteticos_bgc(fecha_inicio, fecha_fin):
    """Crear datos BGC (pH, aragonito) sintéticos"""
    times = pd.date_range(fecha_inicio, fecha_fin, freq="ME")
    lats = np.linspace(LAT_MIN, LAT_MAX, 10)
    lons = np.linspace(LON_MIN, LON_MAX, 10)
    lon2d, lat2d = np.meshgrid(lons, lats)
    
    n_t, n_lat, n_lon = len(times), len(lats), len(lons)
    
    # pH: ~8.05 en norte, ~7.95 en sur con tendencia decreciente
    ph_base = 8.05 - 0.001 * (lat2d + 20)
    ph_trend = -0.001 * np.arange(n_t)[:, None, None]  # acidificación ~0.01/año
    ph_noise = np.random.randn(n_t, n_lat, n_lon) * 0.02
    ph = ph_base + ph_trend + ph_noise
    
    # Aragonito: saturado en norte (~2.5), subsaturado en sur (~1.2)
    arag_base = 2.5 - 0.03 * (lat2d + 20)
    arag_noise = np.random.randn(n_t, n_lat, n_lon) * 0.05
    aragonito = arag_base * np.ones((n_t, n_lat, n_lon)) + arag_noise
    aragonito = np.maximum(aragonito, 0.5)
    
    ds = xr.Dataset(
        {"ph": (["time", "lat", "lon"], ph),
         "aragonite_saturation": (["time", "lat", "lon"], aragonito)},
        coords={"time": times, "lat": lats, "lon": lons},
        attrs={"units": "pH/omega", "source": "HDO synthetic"}
    )
    return ds
