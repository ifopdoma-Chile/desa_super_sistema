"""
Datos geográficos de apoyo para HDO
"""
import json

# Polígonos de zonas costeras de Chile
ZONAS_COSTERAS = {
    "Norte Grande": {
        "lat": [-18.0, -24.0],
        "lon": [-72.0, -70.0],
        "puertos_principales": ["Arica", "Iquique", "Antofagasta"]
    },
    "Norte Chico": {
        "lat": [-24.0, -30.0],
        "lon": [-73.0, -71.0],
        "puertos_principales": ["Coquimbo", "La Serena"]
    },
    "Centro": {
        "lat": [-30.0, -38.0],
        "lon": [-74.0, -72.0],
        "puertos_principales": ["Valparaíso", "San Antonio", "Talcahuano"]
    },
    "Sur": {
        "lat": [-38.0, -46.0],
        "lon": [-76.0, -73.0],
        "puertos_principales": ["Puerto Montt", "Castro"]
    },
    "Austral": {
        "lat": [-46.0, -56.0],
        "lon": [-78.0, -65.0],
        "puertos_principales": ["Punta Arenas"]
    }
}

# Región Niño 1+2 (para downscaling ENOS)
REGION_NINO12 = {
    "lat_min": -10.0,
    "lat_max": 0.0,
    "lon_min": -90.0,
    "lon_max": -80.0
}

# Límites del HCS (Sistema Corriente de Humboldt)
LIMITES_HCS = {
    "lat_min": -40.0,
    "lat_max": -18.0,
    "lon_min": -85.0,
    "lon_max": -70.0
}

# Tabla de umbrales ENOS
UMBRALES_ENOS = {
    "Débil": 0.5,
    "Moderado": 1.0,
    "Fuerte": 1.5,
    "Muy Fuerte": 2.0
}

def get_zonas_geojson():
    """Retornar zonas en formato GeoJSON simplificado"""
    features = []
    for nombre, zona in ZONAS_COSTERAS.items():
        feature = {
            "type": "Feature",
            "properties": {
                "name": nombre,
                "puertos": zona["puertos_principales"]
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [zona["lon"][0], zona["lat"][0]],
                    [zona["lon"][1], zona["lat"][0]],
                    [zona["lon"][1], zona["lat"][1]],
                    [zona["lon"][0], zona["lat"][1]],
                    [zona["lon"][0], zona["lat"][0]]
                ]]
            }
        }
        features.append(feature)
    
    return {"type": "FeatureCollection", "features": features}

def clasificar_enos(nino34):
    """Clasificar intensidad ENOS según valor Niño 3.4"""
    abs_val = abs(nino34)
    if abs_val < 0.5:
        return "Neutro"
    for nombre, umbral in sorted(UMBRALES_ENOS.items(), key=lambda x: x[1]):
        if abs_val >= umbral:
            intensidad = nombre
    return intensidad
