"""
API REST Publica del HDO
Endpoints: /hdo/api/v1/*
Sin autenticacion - Version con datos locales IFOP
"""
import csv
import io
from datetime import datetime, date as date_type
from flask import Blueprint, jsonify, request, Response

from app.servicios.datos import (
    get_enos_ultimos, get_enos_historico,
    get_doma_tsm, get_doma_tsm_historico, get_doma_tsm_ultimo, get_doma_tsm_zonas,
    get_doma_clo, get_doma_clo_ultimo,
    get_doma_nivelmar, get_doma_nivelmar_ultimo,
    get_doma_atsm, get_doma_atsm_ultimo,
    get_nino34_local, get_soi_local,
    get_surgencia_ultimos, get_surgencia_por_zona,
    get_hcs_ultimos, get_acidificacion_ultimos,
    get_alertas_activas, get_satelital, get_satelital_local,
    get_estaciones_meteo, get_ultimas_lecturas_por_estacion, get_serie_estacion,
    get_doma_perfiles, get_doma_perfiles_estaciones,
    get_sho_climatologia, get_sho_mensual, get_sho_puertos,
    get_estadisticas_dashboard
)

api_bp = Blueprint("api", __name__)

def rows_to_csv(rows, columns):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({c: str(row.get(c, "")) for c in columns})
    return output.getvalue()

def serialize_row(row):
    if row is None:
        return None
    result = {}
    for key, value in dict(row).items():
        if isinstance(value, (datetime, date_type)):
            result[key] = value.strftime("%Y-%m-%d") if hasattr(value, 'strftime') else str(value)
        elif isinstance(value, bytes):
            result[key] = str(value)
        else:
            result[key] = value
    return result

def json_or_csv_response(data, columns=None):
    fmt = request.args.get("formato", "json")
    if fmt == "csv" and columns:
        csv_data = rows_to_csv(data, columns)
        return Response(csv_data, mimetype="text/csv",
                       headers={"Content-Disposition": "attachment; filename=hdo_export.csv"})
    return jsonify({"data": [serialize_row(r) for r in data], "count": len(data)})

# ============================================================================
# ENOS
# ============================================================================
@api_bp.route("/enos", methods=["GET"])
def api_enos():
    limite = request.args.get("limite", 60, type=int)
    data = get_enos_ultimos(limite)
    cols = ["fecha", "oni", "nino34", "soi", "hci", "mei", "nino12_hdo", "nino34_local", "soi_local"]
    return json_or_csv_response(data, cols)

@api_bp.route("/enos/historico", methods=["GET"])
def api_enos_historico():
    desde = request.args.get("desde")
    hasta = request.args.get("hasta")
    data = get_enos_historico(desde, hasta)
    cols = ["fecha", "oni", "nino34", "soi", "hci", "mei", "nino12_hdo", "nino34_local", "soi_local"]
    return json_or_csv_response(data, cols)

@api_bp.route("/enos/local/nino34", methods=["GET"])
def api_nino34_local():
    desde = request.args.get("desde", type=int)
    hasta = request.args.get("hasta", type=int)
    data = get_nino34_local(desde, hasta)
    cols = ["ano", "mes", "dato"]
    return json_or_csv_response(data, cols)

@api_bp.route("/enos/local/soi", methods=["GET"])
def api_soi_local():
    desde = request.args.get("desde", type=int)
    hasta = request.args.get("hasta", type=int)
    data = get_soi_local(desde, hasta)
    cols = ["ano", "mes", "dato"]
    return json_or_csv_response(data, cols)

@api_bp.route("/enos/comparativo", methods=["GET"])
def api_enos_comparativo():
    data = get_enos_ultimos(120)
    result = []
    for r in data:
        result.append({
            "fecha": r.get("fecha"),
            "nino34_global": r.get("nino34"),
            "nino34_local": r.get("nino34_local"),
            "soi_global": r.get("soi"),
            "soi_local": r.get("soi_local")
        })
    return jsonify({"data": result, "count": len(result)})

# ============================================================================
# DOMA - TSM
# ============================================================================
@api_bp.route("/doma/zonas", methods=["GET"])
def api_doma_zonas():
    data = get_doma_tsm_zonas()
    return jsonify({"zonas": [r["zona"] for r in data]})

@api_bp.route("/doma/tsm", methods=["GET"])
def api_doma_tsm():
    zona = request.args.get("zona")
    limite = request.args.get("limite", 365, type=int)
    data = get_doma_tsm(zona, limite)
    cols = ["zona", "fecha", "mean_temp", "min_temp", "max_temp", "num_puntos"]
    return json_or_csv_response(data, cols)

@api_bp.route("/doma/tsm/ultimo", methods=["GET"])
def api_doma_tsm_ultimo():
    data = get_doma_tsm_ultimo()
    cols = ["zona", "fecha", "mean_temp", "min_temp", "max_temp", "num_puntos"]
    return json_or_csv_response(data, cols)

# ============================================================================
# DOMA - Clorofila
# ============================================================================
@api_bp.route("/doma/clo", methods=["GET"])
def api_doma_clo():
    zona = request.args.get("zona")
    limite = request.args.get("limite", 365, type=int)
    data = get_doma_clo(zona, limite)
    cols = ["zona", "fecha", "mean_chl", "min_chl", "max_chl", "num_puntos"]
    return json_or_csv_response(data, cols)

@api_bp.route("/doma/clo/ultimo", methods=["GET"])
def api_doma_clo_ultimo():
    data = get_doma_clo_ultimo()
    cols = ["zona", "fecha", "mean_chl", "min_chl", "max_chl"]
    return json_or_csv_response(data, cols)

# ============================================================================
# DOMA - Nivel del mar y ATSM
# ============================================================================
@api_bp.route("/doma/nivelmar", methods=["GET"])
def api_doma_nivelmar():
    zona = request.args.get("zona")
    limite = request.args.get("limite", 365, type=int)
    data = get_doma_nivelmar(zona, limite)
    cols = ["zona", "fecha", "mean_nivelmar", "min_nivelmar", "max_nivelmar"]
    return json_or_csv_response(data, cols)

@api_bp.route("/doma/atsm", methods=["GET"])
def api_doma_atsm():
    zona = request.args.get("zona")
    limite = request.args.get("limite", 365, type=int)
    data = get_doma_atsm(zona, limite)
    cols = ["zona", "fecha", "mean_temp", "min_temp", "max_temp"]
    return json_or_csv_response(data, cols)

# ============================================================================
# Estaciones meteorologicas
# ============================================================================
@api_bp.route("/estaciones", methods=["GET"])
def api_estaciones():
    data = get_estaciones_meteo()
    cols = ["id", "nombre", "latitud", "longitud", "activa", "fuente"]
    return json_or_csv_response(data, cols)

@api_bp.route("/estaciones/lecturas", methods=["GET"])
def api_estaciones_lecturas():
    estacion_id = request.args.get("estacion_id", type=int)
    data = get_ultimas_lecturas_por_estacion(estacion_id)
    cols = ["estacion_id", "estacion", "variable", "valor", "unidad", "horamedicion"]
    return json_or_csv_response(data, cols)

@api_bp.route("/estaciones/<int:estacion_id>/serie", methods=["GET"])
def api_estacion_serie(estacion_id):
    variable = request.args.get("variable")
    dias = request.args.get("dias", 30, type=int)
    data = get_serie_estacion(estacion_id, variable, dias)
    cols = ["horamedicion", "variable", "valor", "unidad"]
    return json_or_csv_response(data, cols)

# ============================================================================
# Perfiles CTD
# ============================================================================
@api_bp.route("/doma/perfiles/estaciones", methods=["GET"])
def api_doma_perfiles_estaciones():
    data = get_doma_perfiles_estaciones()
    return jsonify({"estaciones": [r["estacion"] for r in data]})

@api_bp.route("/doma/perfiles", methods=["GET"])
def api_doma_perfiles():
    estacion = request.args.get("estacion")
    limite = request.args.get("limite", 500, type=int)
    data = get_doma_perfiles(estacion, limite)
    cols = ["estacion", "fecha_ano", "mes", "dia", "profundidad", "temp", "salinidad", "sigma_t", "oxigeno", "clorofila_a"]
    return json_or_csv_response(data, cols)

# ============================================================================
# SHOA
# ============================================================================
@api_bp.route("/sho/puertos", methods=["GET"])
def api_sho_puertos():
    data = get_sho_puertos()
    cols = ["codigo", "latitud", "longitud", "region"]
    return json_or_csv_response(data, cols)

@api_bp.route("/sho/climatologia", methods=["GET"])
def api_sho_climatologia():
    puerto = request.args.get("puerto")
    variable = request.args.get("variable")
    data = get_sho_climatologia(puerto, variable)
    cols = ["puerto", "variable", "mes", "media", "sd", "p05", "p25", "p50", "p75", "p95", "n_anios"]
    return json_or_csv_response(data, cols)

@api_bp.route("/sho/mensual", methods=["GET"])
def api_sho_mensual():
    puerto = request.args.get("puerto")
    variable = request.args.get("variable")
    limite = request.args.get("limite", 500, type=int)
    data = get_sho_mensual(puerto, variable, limite)
    cols = ["puerto", "variable", "anio", "mes", "valor_mean", "valor_min", "valor_max", "n_obs"]
    return json_or_csv_response(data, cols)

# ============================================================================
# Datos satelitales locales
# ============================================================================
@api_bp.route("/satelital/local", methods=["GET"])
def api_satelital_local():
    variable = request.args.get("variable")
    limite = request.args.get("limite", 1000, type=int)
    data = get_satelital_local(variable, limite)
    cols = ["fecha", "variable", "lat", "lon", "valor", "fuente"]
    return json_or_csv_response(data, cols)

# ============================================================================
# Original: Surgencia, HCS, Acidificacion, Alertas
# ============================================================================
@api_bp.route("/surgencia", methods=["GET"])
def api_surgencia():
    limite = request.args.get("limite", 100, type=int)
    zona = request.args.get("zona")
    if zona:
        data = get_surgencia_por_zona(zona, limite)
    else:
        data = get_surgencia_ultimos(limite)
    cols = ["fecha", "latitud", "zona", "ekman_transport", "cui", "sst_costera", "anomalia_surgencia"]
    return json_or_csv_response(data, cols)

@api_bp.route("/hcs", methods=["GET"])
def api_hcs():
    limite = request.args.get("limite", 60, type=int)
    data = get_hcs_ultimos(limite)
    cols = ["fecha", "sst_promedio", "sst_anomalia", "chl_promedio", "ssh_promedio", "productividad", "extension_aguas_frias"]
    return json_or_csv_response(data, cols)

@api_bp.route("/acidificacion", methods=["GET"])
def api_acidificacion():
    limite = request.args.get("limite", 100, type=int)
    data = get_acidificacion_ultimos(limite)
    cols = ["fecha", "lat", "lon", "ph", "aragonito", "ph_anomalia", "profundidad"]
    return json_or_csv_response(data, cols)

@api_bp.route("/alertas", methods=["GET"])
def api_alertas():
    data = get_alertas_activas()
    cols = ["fecha", "tipo", "severidad", "descripcion", "valor", "umbral"]
    return json_or_csv_response(data, cols)

@api_bp.route("/status", methods=["GET"])
def api_status():
    stats = get_estadisticas_dashboard()
    return jsonify({
        "sistema": "Humboldt Digital Ocean",
        "version": "2.0.0",
        "status": "operativo",
        "ultima_actualizacion": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "datos": {
            "enos": stats["enos"] is not None,
            "surgencia": stats["surgencia"] is not None,
            "hcs": stats["hcs"] is not None,
            "acidificacion": stats["acidificacion"] is not None,
            "alertas_activas": stats["alertas_count"],
            "doma_tsm_zonas": stats.get("doma_tsm_count", 0),
            "estaciones_meteorologicas": stats.get("estaciones_count", 0),
            "lecturas_recientes": stats.get("lecturas_count", 0)
        }
    })
