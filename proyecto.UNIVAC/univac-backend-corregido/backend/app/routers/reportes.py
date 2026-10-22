from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
import time
import threading

from ..database import get_db, SessionLocal
from ..auth import get_current_user
from ..models import Usuario

REPORT_TTL = 600
_report_cache = {}
_REPORT_MAX = 300
_report_lock = threading.Lock()

def _cache_get(key):
    with _report_lock:
        hit = _report_cache.get(key)
        if hit and time.time() - hit[0] < REPORT_TTL:
            return hit[1]
        if hit:
            _report_cache.pop(key, None)
    return None

def _cache_set(key, value):
    with _report_lock:
        now = time.time()
        _report_cache[key] = (now, value)
        if len(_report_cache) > _REPORT_MAX:
            _descartar = min(_report_cache.items(), key=lambda kv: kv[1][0])[0]
            _report_cache.pop(_descartar, None)

router = APIRouter(
    prefix="/reportes",
    tags=["Reportes"]
)


def _rows_to_dicts(result):
    cols = result.keys()
    return [dict(zip(cols, row)) for row in result.fetchall()]


def _clean_int(val):
    if val is None:
        return 0
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return 0


def _get_empresa_id(usuario):
    return _clean_int(usuario.empresa_id)


def _ejecutar_consultas(consultas, params, max_workers=4):
    def _ejecutar_una(nombre, sql, modo):
        with SessionLocal() as s:
            try:
                stmt = text(sql) if isinstance(sql, str) else sql
                result = s.execute(stmt, params)
                if modo == "rows":
                    return _rows_to_dicts(result)
                return result.scalar()
            except Exception as exc:
                raise RuntimeError(f"Error en consulta '{nombre}': {exc}") from exc

    resultados = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futuros = {
            executor.submit(_ejecutar_una, nombre, sql, modo): nombre
            for nombre, sql, modo in consultas
        }
        for futuro in futuros:
            nombre = futuros[futuro]
            resultados[nombre] = futuro.result()

    return resultados



@router.get("/sucursales")
def listar_sucursales(
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = _get_empresa_id(usuario)
    cache_key = ("sucursales", eid, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_compras = "comprobantes_compras" if estado == 0 else "_comprobantes_compras"
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"

    q = text(f"""
        SELECT ids.id_sucursal AS id, SUM(ids.cantidad) AS comprobantes
        FROM (
            SELECT c.id_sucursal, COUNT(*) AS cantidad
            FROM {t_ventas} AS c
            WHERE c.id_empresa = :eid AND c.id_sucursal IS NOT NULL
            GROUP BY c.id_sucursal
            UNION ALL
            SELECT c.id_sucursal, COUNT(*) AS cantidad
            FROM {t_compras} AS c
            WHERE c.id_empresa = :eid AND c.id_sucursal IS NOT NULL
            GROUP BY c.id_sucursal
        ) AS ids
        GROUP BY ids.id_sucursal
        ORDER BY ids.id_sucursal
    """)

    try:
        det = _rows_to_dicts(db.execute(q, params))
        result = [{"id": _clean_int(d["id"]), "comprobantes": _clean_int(d["comprobantes"])} for d in det]
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en el listado de sucursales")



@router.get("/dashboard")
def dashboard(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user)
):
    eid = _get_empresa_id(usuario)
    cache_key = ("dash", eid, desde, hasta, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_compras = "comprobantes_compras" if estado == 0 else "_comprobantes_compras"
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"
    t_ingresos = "ingresos_egresos" if estado == 0 else "_ingresos_egresos"

    wf_int = ""
    wf_dt  = ""
    if desde:
        wf_int += " AND c.fecha >= :desde_int"
        wf_dt  += " AND xcol >= :desde"
        params["desde_int"] = desde.replace("-", "")
        params["desde"]     = desde.replace("-", "")
    if hasta:
        wf_int += " AND c.fecha <= :hasta_int"
        wf_dt  += " AND xcol <= :hasta"
        params["hasta_int"] = hasta.replace("-", "")
        params["hasta"]     = hasta.replace("-", "")

    def wf(col):
        return wf_dt.replace("xcol", col) if wf_dt else ""


    q_ventas_contado = text(f"""
        SELECT SUM(IF(t.tipo = '+', c.total_comprobante, -c.total_comprobante)) AS total
        FROM {t_ventas} c
        LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
        WHERE c.id_empresa = :eid AND c.forma = 2 {wf_int}
    """)
    q_ventas_ctacte = text(f"""
        SELECT SUM(IF(t.tipo = '+', c.total_comprobante, -c.total_comprobante)) AS total
        FROM {t_ventas} c
        LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
        WHERE c.id_empresa = :eid AND c.forma = 1 {wf_int}
    """)
    q_cobranzas = text(f"""
        SELECT SUM(total_comprobante) AS total
        FROM comprobantes_cobranzas
        WHERE id_empresa = :eid {wf('fecha')}
    """)
    q_otros_ingresos = text(f"""
        SELECT SUM(ie.importe) AS total
        FROM {t_ingresos} ie
        LEFT JOIN tipos_movimientos t ON t.id = ie.id_tipo_movimiento
        WHERE ie.id_empresa = :eid AND SUBSTRING(t.tipo, 1, 1) = 'I' {wf('ie.fecha')}
    """)
    q_cc_clientes_vencidos = text("""
        SELECT SUM(saldo_comprobante) AS total
        FROM cuentas_corrientes_clientes
        WHERE id_empresa = :eid AND fecha_vencimiento <= :hasta
    """)
    q_cc_clientes_total = text("""
        SELECT SUM(saldo_comprobante) AS total
        FROM cuentas_corrientes_clientes
        WHERE id_empresa = :eid
    """)
    q_cheques_cartera = text("""
        SELECT SUM(importe) AS total
        FROM cheques
        WHERE id_empresa = :eid AND id_endosante = 0 AND id_esporadico = 0 AND devuelto = 0
    """)
    q_cheques_vencer = text("""
        SELECT SUM(importe) AS total
        FROM cheques
        WHERE id_empresa = :eid AND id_endosante = 0 AND id_esporadico = 0 AND devuelto = 0
          AND fecha_vencimiento <= :hasta
    """)
    q_cheques_recibidos = text(f"""
        SELECT SUM(importe) AS total
        FROM cheques
        WHERE id_empresa = :eid AND id_endosante = 0 AND id_esporadico = 0 AND devuelto = 0
          {wf('fecha_ingreso')}
    """)
    q_depositos = text(f"""
        SELECT SUM(debe) AS total
        FROM bancos
        WHERE id_empresa = :eid AND id_referencia = 2 {wf('fecha_vencimiento')}
    """)
    q_ventas_diarias = text(f"""
        SELECT c.fecha, SUM(IF(t.tipo = '+', c.total_comprobante, -c.total_comprobante)) AS total
        FROM {t_ventas} c
        LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
        WHERE c.id_empresa = :eid {wf_int}
        GROUP BY c.fecha ORDER BY c.fecha ASC
    """)


    q_compras_contado = text(f"""
        SELECT SUM(IF(t.tipo = '+', c.total_comprobante, -c.total_comprobante)) AS total
        FROM {t_compras} c
        LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
        WHERE c.id_empresa = :eid AND c.forma = 2 {wf_int}
    """)
    q_compras_ctacte = text(f"""
        SELECT SUM(IF(t.tipo = '+', c.total_comprobante, -c.total_comprobante)) AS total
        FROM {t_compras} c
        LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
        WHERE c.id_empresa = :eid AND c.forma = 1 {wf_int}
    """)
    q_ordenes_pago = text(f"""
        SELECT SUM(total_comprobante) AS total
        FROM comprobantes_pagos
        WHERE id_empresa = :eid {wf('fecha')}
    """)
    q_otros_egresos = text(f"""
        SELECT SUM(ie.importe) AS total
        FROM {t_ingresos} ie
        LEFT JOIN tipos_movimientos t ON t.id = ie.id_tipo_movimiento
        WHERE ie.id_empresa = :eid AND SUBSTRING(t.tipo, 1, 1) = 'E' {wf('ie.fecha')}
    """)
    q_cc_proveedores_vencidos = text("""
        SELECT SUM(saldo_comprobante) AS total
        FROM cuentas_corrientes_proveedores
        WHERE id_empresa = :eid AND fecha_vencimiento <= :hasta
    """)
    q_cc_proveedores_total = text("""
        SELECT SUM(saldo_comprobante) AS total
        FROM cuentas_corrientes_proveedores
        WHERE id_empresa = :eid
    """)
    q_cheques_entregados = text(f"""
        SELECT SUM(importe) AS total
        FROM cheques
        WHERE id_empresa = :eid AND (id_endosante <> 0 OR id_esporadico <> 0) AND devuelto = 0
          {wf('fecha_entrega')}
    """)
    q_bancos_ref1 = text(f"""
        SELECT SUM(haber) AS total
        FROM bancos
        WHERE id_empresa = :eid AND id_referencia = 1 {wf('fecha_vencimiento')}
    """)
    q_bancos_ref5 = text(f"""
        SELECT SUM(haber) AS total
        FROM bancos
        WHERE id_empresa = :eid AND id_referencia = 5 {wf('fecha_vencimiento')}
    """)
    q_bancos_ref3_debe = text(f"""
        SELECT SUM(debe) AS total
        FROM bancos
        WHERE id_empresa = :eid AND id_referencia = 3 {wf('fecha_vencimiento')}
    """)
    q_compras_diarias = text(f"""
        SELECT c.fecha, SUM(IF(t.tipo = '+', c.total_comprobante, -c.total_comprobante)) AS total
        FROM {t_compras} c
        LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
        WHERE c.id_empresa = :eid {wf_int}
        GROUP BY c.fecha ORDER BY c.fecha ASC
    """)

    if "hasta" not in params:
        params["hasta"] = date.today().strftime("%Y%m%d")

    try:
        resultados = _ejecutar_consultas([
            ("ventas_contado", q_ventas_contado, "scalar"),
            ("ventas_ctacte", q_ventas_ctacte, "scalar"),
            ("compras_contado", q_compras_contado, "scalar"),
            ("compras_ctacte", q_compras_ctacte, "scalar"),
            ("cobranzas", q_cobranzas, "scalar"),
            ("otros_ingresos", q_otros_ingresos, "scalar"),
            ("ordenes_pago", q_ordenes_pago, "scalar"),
            ("otros_egresos", q_otros_egresos, "scalar"),
            ("cc_clientes_vencidos", q_cc_clientes_vencidos, "scalar"),
            ("cc_clientes_total", q_cc_clientes_total, "scalar"),
            ("cc_proveedores_vencidos", q_cc_proveedores_vencidos, "scalar"),
            ("cc_proveedores_total", q_cc_proveedores_total, "scalar"),
            ("cheques_cartera", q_cheques_cartera, "scalar"),
            ("cheques_vencer", q_cheques_vencer, "scalar"),
            ("cheques_recibidos", q_cheques_recibidos, "scalar"),
            ("cheques_entregados", q_cheques_entregados, "scalar"),
            ("depositos", q_depositos, "scalar"),
            ("bancos_ref1", q_bancos_ref1, "scalar"),
            ("bancos_ref5", q_bancos_ref5, "scalar"),
            ("bancos_ref3_debe", q_bancos_ref3_debe, "scalar"),
            ("ventas_diarias", q_ventas_diarias, "rows"),
            ("compras_diarias", q_compras_diarias, "rows"),
        ], params)

        ventas_contado  = float(resultados["ventas_contado"] or 0)
        ventas_ctacte   = float(resultados["ventas_ctacte"] or 0)
        compras_contado = float(resultados["compras_contado"] or 0)
        compras_ctacte  = float(resultados["compras_ctacte"] or 0)
        cobranzas       = float(resultados["cobranzas"] or 0)
        otros_ingresos  = float(resultados["otros_ingresos"] or 0)
        ordenes_pago    = float(resultados["ordenes_pago"] or 0)
        otros_egresos   = float(resultados["otros_egresos"] or 0)

        cc_clientes_vencidos     = float(resultados["cc_clientes_vencidos"] or 0)
        cc_clientes_total        = float(resultados["cc_clientes_total"] or 0)
        cc_proveedores_vencidos  = float(resultados["cc_proveedores_vencidos"] or 0)
        cc_proveedores_total     = float(resultados["cc_proveedores_total"] or 0)

        cheques_cartera    = float(resultados["cheques_cartera"] or 0)
        cheques_vencer     = float(resultados["cheques_vencer"] or 0)
        cheques_recibidos  = float(resultados["cheques_recibidos"] or 0)
        cheques_entregados = float(resultados["cheques_entregados"] or 0)

        depositos        = float(resultados["depositos"] or 0)
        bancos_ref1      = float(resultados["bancos_ref1"] or 0)
        bancos_ref5      = float(resultados["bancos_ref5"] or 0)
        bancos_ref3_debe = float(resultados["bancos_ref3_debe"] or 0)

        ventas_diarias  = resultados["ventas_diarias"]
        compras_diarias = resultados["compras_diarias"]
    except Exception:
        raise HTTPException(status_code=500, detail="Error al consultar el dashboard")

    now_text = ""
    now = datetime.now()
    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
    if desde and hasta:
        now_text = f"{desde} al {hasta}"
    elif desde:
        now_text = f"Desde {desde}"
    elif hasta:
        now_text = f"Hasta {hasta}"
    else:
        now_text = f"Todos los datos - {meses[now.month - 1]} {now.year}"

    resp = {
        "periodo": now_text,
        "ventas_contado": ventas_contado,
        "ventas_ctacte": ventas_ctacte,
        "compras_contado": compras_contado,
        "compras_ctacte": compras_ctacte,
        "cobranzas": cobranzas,
        "otros_ingresos": otros_ingresos,
        "ordenes_pago": ordenes_pago,
        "otros_egresos": otros_egresos,
        "cc_clientes_vencidos": cc_clientes_vencidos,
        "cc_clientes_total": cc_clientes_total,
        "cc_proveedores_vencidos": cc_proveedores_vencidos,
        "cc_proveedores_total": cc_proveedores_total,
        "cheques_cartera": cheques_cartera,
        "cheques_vencer": cheques_vencer,
        "cheques_recibidos": cheques_recibidos,
        "cheques_entregados": cheques_entregados,
        "bancos_transferencia_recibida": depositos,
        "bancos_emision_cheque_proveedor": bancos_ref1,
        "bancos_transferencia_cuentas_propias": bancos_ref5,
        "bancos_deposito_efectivo_terceros": bancos_ref3_debe,
        "ventas_diarias": ventas_diarias,
        "compras_diarias": compras_diarias
    }
    _cache_set(cache_key, resp)
    return resp



@router.get("/compras/iva")
def compras_iva(
    anio: Optional[int] = Query(None),
    mes: Optional[int] = Query(None),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("compras_iva", eid, anio, mes, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_compras = "comprobantes_compras" if estado == 0 else "_comprobantes_compras"
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"

    where_extra = ""
    if anio:
        where_extra += " AND YEAR(c.fecha) = :anio"
        params["anio"] = anio
    if mes:
        where_extra += " AND MONTH(c.fecha) = :mes"
        params["mes"] = mes

    q_resumen = text(f"""
        SELECT
            COALESCE(SUM(c.total_comprobante), 0) AS total_ventas,
            COALESCE(SUM(c.neto_gravado), 0) AS neto_ventas,
            COALESCE(SUM(c.iva), 0) AS iva_ventas
        FROM {t_ventas} c
        WHERE c.id_empresa = :eid AND c.anulado = 0 {where_extra}
    """)
    q_compras_resumen = text(f"""
        SELECT
            COALESCE(SUM(c.total_comprobante), 0) AS total_compras,
            COALESCE(SUM(c.neto_gravado), 0) AS neto_compras,
            COALESCE(SUM(c.iva), 0) AS iva_compras
        FROM {t_compras} c
        WHERE c.id_empresa = :eid {where_extra}
    """)
    q_detalle = text(f"""
        SELECT
            COALESCE(t.nombre, CONCAT('Tipo ', c.id_comprobante)) AS concepto,
            COUNT(*) AS comprobantes,
            SUM(c.neto_gravado) AS neto,
            SUM(c.iva) AS iva
        FROM {t_compras} c
        LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
        WHERE c.id_empresa = :eid {where_extra}
        GROUP BY c.id_comprobante, t.nombre
        ORDER BY c.id_comprobante
    """)

    try:
        rv = db.execute(q_resumen, params).fetchone()
        rc = db.execute(q_compras_resumen, params).fetchone()
        det = _rows_to_dicts(db.execute(q_detalle, params))

        debito = float(rv[2]) if rv else 0
        credito = float(rc[2]) if rc else 0

        result = {
            "debito_fiscal": debito,
            "credito_fiscal": credito,
            "saldo": debito - credito,
            "total_ventas": float(rv[0]) if rv else 0,
            "neto_ventas": float(rv[1]) if rv else 0,
            "iva_ventas": debito,
            "total_compras": float(rc[0]) if rc else 0,
            "neto_compras": float(rc[1]) if rc else 0,
            "iva_compras": credito,
            "detalle": det
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Compras IVA")



@router.get("/compras/acumuladas")
def compras_acumuladas(
    mrad: int = Query(1, description="1=periodo, 2=fecha, 3=detalle fecha, 4=detalle registracion"),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("compras_acumuladas", eid, mrad, desde, hasta, sucursal, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_compras = "comprobantes_compras" if estado == 0 else "_comprobantes_compras"
    where = "WHERE c.id_empresa = :eid"

    if sucursal:
        sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
        if sucursal_ids:
            placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
            where += f" AND c.id_sucursal IN ({placeholders})"
            for i, s in enumerate(sucursal_ids):
                params[f"suc_{i}"] = s

    if mrad == 1:
        if desde:
            where += " AND CONCAT(LPAD(c.ano_imputacion,4,'0'),LPAD(c.mes_imputacion,2,'0')) >= :desde"
            params["desde"] = desde.replace("-", "")[:6]
        if hasta:
            where += " AND CONCAT(LPAD(c.ano_imputacion,4,'0'),LPAD(c.mes_imputacion,2,'0')) <= :hasta"
            params["hasta"] = hasta.replace("-", "")[:6]

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                MAX(c.fecha) AS fecha,
                COUNT(*) AS cantidad,
                SUM(IF(t.tipo = '+', c.neto_gravado, -c.neto_gravado)) AS ng,
                SUM(IF(t.tipo = '+', c.iva, -c.iva)) AS iv,
                SUM(IF(t.tipo = '+', c.percepcion_iva, -c.percepcion_iva)) AS piva,
                SUM(IF(t.tipo = '+', c.percepcion_i_brutos, -c.percepcion_i_brutos)) AS pib,
                SUM(IF(t.tipo = '+', c.exento, -c.exento)) AS pex,
                SUM(IF(t.tipo = '+', c.conceptos_no_gravados, -c.conceptos_no_gravados)) AS cng,
                SUM(IF(t.tipo = '+', c.total_comprobante, -c.total_comprobante)) AS tot
            FROM {t_compras} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            {where}
            GROUP BY c.mes_imputacion, c.ano_imputacion
            ORDER BY c.ano_imputacion, c.mes_imputacion
        """)

    elif mrad == 2:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")

        q = text(f"""
            SELECT
                MAX(c.mes_imputacion) AS mes_imputacion,
                MAX(c.ano_imputacion) AS ano_imputacion,
                c.fecha,
                COUNT(*) AS cantidad,
                SUM(IF(t.tipo = '+', c.neto_gravado, -c.neto_gravado)) AS ng,
                SUM(IF(t.tipo = '+', c.iva, -c.iva)) AS iv,
                SUM(IF(t.tipo = '+', c.percepcion_iva, -c.percepcion_iva)) AS piva,
                SUM(IF(t.tipo = '+', c.percepcion_i_brutos, -c.percepcion_i_brutos)) AS pib,
                SUM(IF(t.tipo = '+', c.exento, -c.exento)) AS pex,
                SUM(IF(t.tipo = '+', c.conceptos_no_gravados, -c.conceptos_no_gravados)) AS cng,
                SUM(IF(t.tipo = '+', c.total_comprobante, -c.total_comprobante)) AS tot
            FROM {t_compras} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            {where}
            GROUP BY c.fecha
            ORDER BY c.fecha
        """)

    elif mrad == 3:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                c.fecha,
                '1' AS cantidad,
                IF(t.tipo = '+', c.neto_gravado, -c.neto_gravado) AS ng,
                IF(t.tipo = '+', c.iva, -c.iva) AS iv,
                IF(t.tipo = '+', c.percepcion_iva, -c.percepcion_iva) AS piva,
                IF(t.tipo = '+', c.percepcion_i_brutos, -c.percepcion_i_brutos) AS pib,
                IF(t.tipo = '+', c.exento, -c.exento) AS pex,
                IF(t.tipo = '+', c.conceptos_no_gravados, -c.conceptos_no_gravados) AS cng,
                IF(t.tipo = '+', c.total_comprobante, -c.total_comprobante) AS tot
            FROM {t_compras} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            {where}
            ORDER BY c.fecha
        """)

    elif mrad == 4:
        if desde:
            where += " AND DATE(c.registracion) >= :desde"
            params["desde"] = desde
        if hasta:
            where += " AND DATE(c.registracion) <= :hasta"
            params["hasta"] = hasta

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                DATE(c.registracion) AS fecha,
                '1' AS cantidad,
                IF(t.tipo = '+', c.neto_gravado, -c.neto_gravado) AS ng,
                IF(t.tipo = '+', c.iva, -c.iva) AS iv,
                IF(t.tipo = '+', c.percepcion_iva, -c.percepcion_iva) AS piva,
                IF(t.tipo = '+', c.percepcion_i_brutos, -c.percepcion_i_brutos) AS pib,
                IF(t.tipo = '+', c.exento, -c.exento) AS pex,
                IF(t.tipo = '+', c.conceptos_no_gravados, -c.conceptos_no_gravados) AS cng,
                IF(t.tipo = '+', c.total_comprobante, -c.total_comprobante) AS tot
            FROM {t_compras} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            {where}
            ORDER BY DATE(c.registracion)
        """)
    else:
        raise HTTPException(status_code=400, detail="mRAD inválido. Use 1, 2, 3 o 4.")

    try:
        rows = _rows_to_dicts(db.execute(q, params))
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Compras Acumuladas")
    _cache_set(cache_key, rows)
    return rows



@router.get("/compras/provincias")
def compras_provincias(
    mrad: int = Query(1, description="1=agrupado por periodo, 2=agrupado por fecha, 3=detalle por fecha, 4=detalle por registracion"),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("compras_provincias", eid, mrad, desde, hasta, sucursal, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_compras = "comprobantes_compras" if estado == 0 else "_comprobantes_compras"
    where = "WHERE c.id_empresa = :eid"

    if sucursal:
        sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
        if sucursal_ids:
            placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
            where += f" AND c.id_sucursal IN ({placeholders})"
            for i, s in enumerate(sucursal_ids):
                params[f"suc_{i}"] = s

    if mrad == 1:
        if desde:
            where += " AND CONCAT(LPAD(c.ano_imputacion,4,'0'),LPAD(c.mes_imputacion,2,'0')) >= :desde"
            params["desde"] = desde.replace("-", "")[:6]
        if hasta:
            where += " AND CONCAT(LPAD(c.ano_imputacion,4,'0'),LPAD(c.mes_imputacion,2,'0')) <= :hasta"
            params["hasta"] = hasta.replace("-", "")[:6]

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                MAX(c.fecha) AS fecha,
                MAX(p.nombre) AS provincia,
                SUM(IF(t.tipo='+', c.neto_gravado, -c.neto_gravado)) AS ng,
                SUM(IF(t.tipo='+', c.iva, -c.iva)) AS iv,
                SUM(IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.conceptos_no_gravados), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.conceptos_no_gravados))) AS otros,
                SUM(IF(t.tipo='+', c.total_comprobante, -c.total_comprobante)) AS tot
            FROM {t_compras} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN provincias p ON p.id = c.id_provincia
            {where}
            GROUP BY c.mes_imputacion, c.ano_imputacion, c.id_provincia
            ORDER BY c.ano_imputacion, c.mes_imputacion
        """)

    elif mrad == 2:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")

        q = text(f"""
            SELECT
                MAX(c.mes_imputacion) AS mes_imputacion,
                MAX(c.ano_imputacion) AS ano_imputacion,
                c.fecha,
                MAX(p.nombre) AS provincia,
                SUM(IF(t.tipo='+', c.neto_gravado, -c.neto_gravado)) AS ng,
                SUM(IF(t.tipo='+', c.iva, -c.iva)) AS iv,
                SUM(IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.conceptos_no_gravados), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.conceptos_no_gravados))) AS otros,
                SUM(IF(t.tipo='+', c.total_comprobante, -c.total_comprobante)) AS tot
            FROM {t_compras} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN provincias p ON p.id = c.id_provincia
            {where}
            GROUP BY c.fecha, c.id_provincia
            ORDER BY c.fecha
        """)

    elif mrad == 3:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                c.fecha,
                p.nombre AS provincia,
                IF(t.tipo='+', c.neto_gravado, -c.neto_gravado) AS ng,
                IF(t.tipo='+', c.iva, -c.iva) AS iv,
                IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.conceptos_no_gravados), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.conceptos_no_gravados)) AS otros,
                IF(t.tipo='+', c.total_comprobante, -c.total_comprobante) AS tot
            FROM {t_compras} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN provincias p ON p.id = c.id_provincia
            {where}
            ORDER BY c.fecha
        """)

    elif mrad == 4:
        if desde:
            where += " AND DATE(c.registracion) >= :desde"
            params["desde"] = desde
        if hasta:
            where += " AND DATE(c.registracion) <= :hasta"
            params["hasta"] = hasta

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                DATE(c.registracion) AS fecha,
                p.nombre AS provincia,
                IF(t.tipo='+', c.neto_gravado, -c.neto_gravado) AS ng,
                IF(t.tipo='+', c.iva, -c.iva) AS iv,
                IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.conceptos_no_gravados), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.conceptos_no_gravados)) AS otros,
                IF(t.tipo='+', c.total_comprobante, -c.total_comprobante) AS tot
            FROM {t_compras} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN provincias p ON p.id = c.id_provincia
            {where}
            ORDER BY DATE(c.registracion)
        """)
    else:
        raise HTTPException(status_code=400, detail="mRAD inválido. Use 1, 2, 3 o 4.")

    try:
        rows = _rows_to_dicts(db.execute(q, params))
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Compras por Provincias")
    _cache_set(cache_key, rows)
    return rows



@router.get("/compras/proveedores")
def compras_proveedores(
    mrad: int = Query(1, description="Modo: 1=Acumulado, 2=Por fecha, 3=Por proveedor, 4=Por registracion"),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("compras_proveedores_v2", eid, mrad, desde, hasta, sucursal, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = {"eid": eid}
    t_compras = "comprobantes_compras" if estado == 0 else "_comprobantes_compras"
    t_esporadicos = "esporadicos" if estado == 0 else "_esporadicos"
    where = "WHERE c.id_empresa = :eid"

    if sucursal:
        sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
        if sucursal_ids:
            placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
            where += f" AND c.id_sucursal IN ({placeholders})"
            for i, s in enumerate(sucursal_ids):
                params[f"suc_{i}"] = s

    joins = f"""
        FROM {t_compras} c
        LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
        LEFT JOIN proveedores p ON p.id = c.id_proveedor
        LEFT JOIN {t_esporadicos} e ON e.id = c.id_esporadico
    """

    select_cols_agg = """
        MAX(c.mes_imputacion) AS mes_imputacion,
        MAX(c.ano_imputacion) AS ano_imputacion,
        MAX(c.fecha) AS fecha,
        MAX(p.nombre) AS proveedor,
        MAX(e.nombre) AS espo,
        SUM(IF(t.tipo = '+', c.neto_gravado, -c.neto_gravado)) AS ng,
        SUM(IF(t.tipo = '+', c.iva, -c.iva)) AS iv,
        SUM(IF(t.tipo = '+',
            (c.percepcion_iva + c.percepcion_i_brutos + c.exento + c.conceptos_no_gravados),
            -(c.percepcion_iva + c.percepcion_i_brutos + c.exento + c.conceptos_no_gravados)
        )) AS otros,
        SUM(IF(t.tipo = '+', c.total_comprobante, -c.total_comprobante)) AS tot
    """

    select_cols_det = """
        c.mes_imputacion, c.ano_imputacion,
        DATE(c.registracion) AS fecha,
        p.nombre AS proveedor,
        e.nombre AS espo,
        IF(t.tipo = '+', c.neto_gravado, -c.neto_gravado) AS ng,
        IF(t.tipo = '+', c.iva, -c.iva) AS iv,
        IF(t.tipo = '+',
            (c.percepcion_iva + c.percepcion_i_brutos + c.exento + c.conceptos_no_gravados),
            -(c.percepcion_iva + c.percepcion_i_brutos + c.exento + c.conceptos_no_gravados)
        ) AS otros,
        IF(t.tipo = '+', c.total_comprobante, -c.total_comprobante) AS tot
    """

    if mrad == 1:
        if desde:
            d = desde.replace("-", "")
            where += " AND CONCAT(LPAD(c.ano_imputacion, 4, '0'), LPAD(c.mes_imputacion, 2, '0')) >= :desde"
            params["desde"] = d
        if hasta:
            h = hasta.replace("-", "")
            where += " AND CONCAT(LPAD(c.ano_imputacion, 4, '0'), LPAD(c.mes_imputacion, 2, '0')) <= :hasta"
            params["hasta"] = h
        select_cols = select_cols_agg
        group = " GROUP BY c.mes_imputacion, c.ano_imputacion, c.id_proveedor, c.id_esporadico"
        order = " ORDER BY c.ano_imputacion, c.mes_imputacion"

    elif mrad == 2:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")
        select_cols = select_cols_agg
        group = " GROUP BY c.fecha, c.id_proveedor, c.id_esporadico"
        order = " ORDER BY tot DESC"

    elif mrad == 3:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")
        select_cols = select_cols_agg
        group = " GROUP BY c.id_proveedor, c.id_esporadico"
        order = " ORDER BY tot DESC"

    elif mrad == 4:
        if desde:
            where += " AND DATE(c.registracion) >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND DATE(c.registracion) <= :hasta"
            params["hasta"] = hasta.replace("-", "")
        select_cols = select_cols_det
        group = ""
        order = " ORDER BY tot DESC"

    else:
        raise HTTPException(status_code=400, detail="mRAD inválido. Use 1, 2, 3 o 4.")

    q = text(f"SELECT {select_cols} {joins} {where} {group} {order}")

    try:
        rows = _rows_to_dicts(db.execute(q, params))
        for r in rows:
            for k in ("ng", "iv", "otros", "tot"):
                r[k] = round(float(r[k] or 0), 2)
        if mrad in (3, 4):
            cSumador = 0.0
            for r in rows:
                cSumador += round(float(r["tot"] or 0), 2)
            for r in rows:
                r["porcentaje"] = round((float(r["tot"] or 0) / cSumador) * 100, 2) if cSumador else 0.0
        _cache_set(cache_key, rows)
        return rows
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Compras por Proveedores")



@router.get("/compras/insumos")
def compras_insumos(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    insumo: Optional[str] = Query(None),
    rubro: Optional[str] = Query(None, description="Filtro por nombre de rubro"),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    mrad: int = Query(3, description="1=periodo, 2=fecha, 3=fecha detalle, 4=registracion"),
    segundo: int = Query(2, description="1=agrupado, 2=desagregado"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("compras_insumos", eid, desde, hasta, insumo, rubro, sucursal, mrad, segundo, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_cuerpo = "comprobantes_cuerpo" if estado == 0 else "_comprobantes_cuerpo"
    t_esporadicos = "esporadicos" if estado == 0 else "_esporadicos"
    ins_q = ""
    if insumo:
        params["insumo"] = f"%{insumo}%"
        ins_q = " and (a.descripcion_larga LIKE :insumo or a.codigo_accesorio LIKE :insumo or a.codigo_de_barras LIKE :insumo)"

    rub_q = ""
    if rubro:
        rub_q = " and r.nombre LIKE :rubro"
        params["rubro"] = f"%{rubro}%"

    suc_q = ""
    if sucursal:
        sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
        if sucursal_ids:
            placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
            suc_q = f" and c.id_sucursal IN ({placeholders})"
            for i, s in enumerate(sucursal_ids):
                params[f"suc_{i}"] = s

    precio_total = (segundo == 2 and mrad in (1, 2))
    agrupado = (segundo == 1) and mrad in (1, 2)

    def av(expr):
        return f"MAX({expr})" if agrupado else expr

    if agrupado:
        caso_cant = "sum(c.cantidad) AS cant"
        caso_tot = "sum(c.cantidad*c.precio*(100-c.bonificacion)/100) AS tot"
    else:
        caso_cant = "c.cantidad AS cant"
        caso_tot = "round(c.cantidad*c.precio*(100-c.bonificacion)/100,2) AS tot"

    if precio_total:
        caso_precio_col10 = "round(c.cantidad*c.precio*(100-c.bonificacion)/100,2) AS precio_total"
    else:
        caso_precio_col10 = f"{av('c.precio_real')} AS precio_real"

    if mrad == 1:
        caso_fecha = "c.fecha_movimiento"
        if desde:
            params["desde"] = desde.replace("-", "")[:6]
        if hasta:
            params["hasta"] = hasta.replace("-", "")[:6]
        fechaf = ""
        if desde:
            fechaf += " and concat(lpad(year(c.fecha_movimiento),4,'0'),lpad(month(c.fecha_movimiento),2,'0'))>=:desde"
        if hasta:
            fechaf += " and concat(lpad(year(c.fecha_movimiento),4,'0'),lpad(month(c.fecha_movimiento),2,'0'))<=:hasta"
    elif mrad == 4:
        caso_fecha = "DATE(c.registracion)"
        if desde:
            params["desde"] = desde.replace("-", "")
        if hasta:
            params["hasta"] = hasta.replace("-", "")
        fechaf = ""
        if desde:
            fechaf += " and DATE(c.registracion)>=:desde"
        if hasta:
            fechaf += " and DATE(c.registracion)<=:hasta"
        orden = "DATE(c.registracion), nom"
    else:
        caso_fecha = "c.fecha_movimiento"
        if desde:
            params["desde"] = desde.replace("-", "")
        if hasta:
            params["hasta"] = hasta.replace("-", "")
        fechaf = ""
        if desde:
            fechaf += " and c.fecha_movimiento>=:desde"
        if hasta:
            fechaf += " and c.fecha_movimiento<=:hasta"

    if mrad != 4:
        orden = "c.fecha_movimiento, nom" if not agrupado else "nom"
    if agrupado and mrad in (1, 2):
        group = " GROUP BY c.id_articulo,c.id_unidad_medida"
    else:
        group = ""

    q = text(f"""
        SELECT
            {av("if(c.identificacion='C' and c.cantidad<0,'NC Compra',if(c.identificacion='C','Compra','Venta'))")} AS ide,
            {av("a.codigo_de_barras")} AS codigo_de_barras,
            {av("concat_ws(' ',a.descripcion_larga,a.codigo_accesorio)")} AS nom,
            {av("t.nombre")} AS tip,
            {av("r.nombre")} AS rub,
            {av(caso_fecha)} AS fecha,
            {caso_cant},
            {av("c.precio*(100-c.bonificacion)/100")} AS precio,
            {av("c.bonificacion")} AS bonificacion,
            {caso_precio_col10},
            {av("u.nombre")} AS uni,
            {av("i.nombre")} AS ali,
            {av("p.nombre")} AS pro,
            {av("e.nombre")} AS espo,
            {av("c.comprobante")} AS comprobante,
            {caso_tot}
        FROM {t_cuerpo} AS c
        LEFT JOIN articulos AS a ON a.id=c.id_articulo
        LEFT JOIN parametros_tipos_articulos AS t ON t.id=a.id_tipo
        LEFT JOIN rubros AS r ON r.id=a.id_rubro
        LEFT JOIN unidades AS u ON u.id=c.id_unidad_medida
        LEFT JOIN tipos_alicuotas_iva AS i ON i.id=c.id_alicuota_iva
        LEFT JOIN proveedores AS p ON p.id=c.id_clipro
        LEFT JOIN {t_esporadicos} AS e ON e.id=c.id_esporadico
        WHERE c.id_empresa=:eid and BINARY c.identificacion IN ('C','K','Q'){suc_q}{fechaf}
        {ins_q}
        {rub_q}
        {group}
        ORDER BY {orden}
    """)

    try:
        det = _rows_to_dicts(db.execute(q, params))
        result = {
            "totalInsumos": len(det),
            "cantidadTotal": sum(float(d["cant"] or 0) for d in det),
            "montoTotal": sum(float(d["tot"] or 0) for d in det),
            "detalle": det
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Compras Insumos")



@router.get("/ventas/acumuladas")
def ventas_acumuladas(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    mrad: int = Query(1, description="1=periodo (mes/ano), 2=fecha"),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("ventas_acumuladas", eid, desde, hasta, mrad, sucursal, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"
    where_extra = ""
    if sucursal:
        sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
        if sucursal_ids:
            placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
            where_extra += f" and c.id_sucursal IN ({placeholders})"
            for i, s in enumerate(sucursal_ids):
                params[f"suc_{i}"] = s

    if mrad == 1:
        if desde:
            params["desde"] = desde.replace("-", "")[:6]
        if hasta:
            params["hasta"] = hasta.replace("-", "")[:6]
        fechaf = ""
        if desde:
            fechaf += " and concat(lpad(c.ano_imputacion,4,'0'),lpad(c.mes_imputacion,2,'0'))>=:desde"
        if hasta:
            fechaf += " and concat(lpad(c.ano_imputacion,4,'0'),lpad(c.mes_imputacion,2,'0'))<=:hasta"
        group = " GROUP BY c.mes_imputacion,c.ano_imputacion"
        orden = "c.ano_imputacion,c.mes_imputacion"
    elif mrad in (2, 3, 4):
        if desde:
            params["desde"] = desde.replace("-", "")
        if hasta:
            params["hasta"] = hasta.replace("-", "")
        fechaf = ""
        if desde:
            fechaf += " and c.fecha>=:desde"
        if hasta:
            fechaf += " and c.fecha<=:hasta"
        group = " GROUP BY c.fecha"
        orden = "c.fecha"
    else:
        raise HTTPException(status_code=400, detail="mRAD inválido. Use 1, 2, 3 o 4.")

    q = text(f"""
        SELECT MAX(c.mes_imputacion) AS mes_imputacion, MAX(c.ano_imputacion) AS ano_imputacion, MAX(c.fecha) AS fecha, count(*) AS cantidad,
            sum(if(t.tipo='+',c.neto_gravado,-c.neto_gravado)) as ng,
            sum(if(t.tipo='+',c.iva,-c.iva)) as iv,
            sum(if(t.tipo='+',c.percepcion_iva,-c.percepcion_iva)) as piva,
            sum(if(t.tipo='+',c.retencion_ganancias,-c.retencion_ganancias)) as rg,
            sum(if(t.tipo='+',c.percepcion_i_brutos,-c.percepcion_i_brutos)) as pib,
            sum(if(t.tipo='+',c.exento,-c.exento)) as pex,
            sum(if(t.tipo='+',c.impuestos_internos,-c.impuestos_internos)) as imp,
            sum(if(t.tipo='+',c.total_comprobante,-c.total_comprobante)) as tot
        FROM {t_ventas} AS c
        LEFT JOIN tipos_comprobantes AS t ON t.id=c.id_comprobante
        WHERE c.id_empresa=:eid{where_extra}{fechaf}
        {group} ORDER BY {orden}
    """)

    try:
        result = _rows_to_dicts(db.execute(q, params))
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Ventas Acumuladas")



@router.get("/ventas/totales")
def ventas_totales(
    mrad: int = Query(1, description="1=periodo, 2=fecha, 3=registro_individual, 4=registracion_individual"),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("ventas_totales", eid, mrad, desde, hasta, sucursal, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"
    where_extra = ""
    if sucursal:
        sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
        if sucursal_ids:
            placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
            where_extra += f" and c.id_sucursal IN ({placeholders})"
            for i, s in enumerate(sucursal_ids):
                params[f"suc_{i}"] = s

    if mrad == 1:
        if desde:
            params["desde"] = desde.replace("-", "")[:6]
        if hasta:
            params["hasta"] = hasta.replace("-", "")[:6]
        fechaf = ""
        if desde:
            fechaf += " and concat(lpad(c.ano_imputacion,4,'0'),lpad(c.mes_imputacion,2,'0'))>=:desde"
        if hasta:
            fechaf += " and concat(lpad(c.ano_imputacion,4,'0'),lpad(c.mes_imputacion,2,'0'))<=:hasta"
        select_cols = "c.mes_imputacion, c.ano_imputacion, MAX(c.fecha) AS fecha, count(*) AS cantidad, sum(if(t.tipo='+',c.neto_gravado,-c.neto_gravado)) as ng, sum(if(t.tipo='+',c.iva,-c.iva)) as iv, sum(if(t.tipo='+',c.percepcion_iva,-c.percepcion_iva)) as piva, sum(if(t.tipo='+',c.retencion_ganancias,-c.retencion_ganancias)) as rg, sum(if(t.tipo='+',c.percepcion_i_brutos,-c.percepcion_i_brutos)) as pib, sum(if(t.tipo='+',c.exento,-c.exento)) as pex, sum(if(t.tipo='+',c.impuestos_internos,-c.impuestos_internos)) as imp, sum(if(t.tipo='+',c.total_comprobante,-c.total_comprobante)) as tot"
        group = " GROUP BY c.mes_imputacion, c.ano_imputacion"
        order = "c.ano_imputacion, c.mes_imputacion"
    elif mrad == 2:
        if desde:
            params["desde"] = desde.replace("-", "")
        if hasta:
            params["hasta"] = hasta.replace("-", "")
        fechaf = ""
        if desde:
            fechaf += " and c.fecha>=:desde"
        if hasta:
            fechaf += " and c.fecha<=:hasta"
        select_cols = "MAX(c.mes_imputacion) AS mes_imputacion, MAX(c.ano_imputacion) AS ano_imputacion, c.fecha, count(*) AS cantidad, sum(if(t.tipo='+',c.neto_gravado,-c.neto_gravado)) as ng, sum(if(t.tipo='+',c.iva,-c.iva)) as iv, sum(if(t.tipo='+',c.percepcion_iva,-c.percepcion_iva)) as piva, sum(if(t.tipo='+',c.retencion_ganancias,-c.retencion_ganancias)) as rg, sum(if(t.tipo='+',c.percepcion_i_brutos,-c.percepcion_i_brutos)) as pib, sum(if(t.tipo='+',c.exento,-c.exento)) as pex, sum(if(t.tipo='+',c.impuestos_internos,-c.impuestos_internos)) as imp, sum(if(t.tipo='+',c.total_comprobante,-c.total_comprobante)) as tot"
        group = " GROUP BY c.fecha"
        order = "c.fecha"
    elif mrad == 3:
        if desde:
            params["desde"] = desde.replace("-", "")
        if hasta:
            params["hasta"] = hasta.replace("-", "")
        fechaf = ""
        if desde:
            fechaf += " and c.fecha>=:desde"
        if hasta:
            fechaf += " and c.fecha<=:hasta"
        select_cols = "c.mes_imputacion, c.ano_imputacion, c.fecha, '1' AS cantidad, if(t.tipo='+',c.neto_gravado,-c.neto_gravado) as ng, if(t.tipo='+',c.iva,-c.iva) as iv, if(t.tipo='+',c.percepcion_iva,-c.percepcion_iva) as piva, if(t.tipo='+',c.retencion_ganancias,-c.retencion_ganancias) as rg, if(t.tipo='+',c.percepcion_i_brutos,-c.percepcion_i_brutos) as pib, if(t.tipo='+',c.exento,-c.exento) as pex, if(t.tipo='+',c.impuestos_internos,-c.impuestos_internos) as imp, if(t.tipo='+',c.total_comprobante,-c.total_comprobante) as tot"
        group = ""
        order = "c.fecha"
    elif mrad == 4:
        if desde:
            params["desde"] = desde.replace("-", "")
        if hasta:
            params["hasta"] = hasta.replace("-", "")
        fechaf = ""
        if desde:
            fechaf += " and DATE(c.registracion)>=:desde"
        if hasta:
            fechaf += " and DATE(c.registracion)<=:hasta"
        select_cols = "c.mes_imputacion, c.ano_imputacion, DATE(c.registracion) AS fecha, '1' AS cantidad, if(t.tipo='+',c.neto_gravado,-c.neto_gravado) as ng, if(t.tipo='+',c.iva,-c.iva) as iv, if(t.tipo='+',c.percepcion_iva,-c.percepcion_iva) as piva, if(t.tipo='+',c.retencion_ganancias,-c.retencion_ganancias) as rg, if(t.tipo='+',c.percepcion_i_brutos,-c.percepcion_i_brutos) as pib, if(t.tipo='+',c.exento,-c.exento) as pex, if(t.tipo='+',c.impuestos_internos,-c.impuestos_internos) as imp, if(t.tipo='+',c.total_comprobante,-c.total_comprobante) as tot"
        group = ""
        order = "DATE(c.registracion)"
    else:
        raise HTTPException(status_code=400, detail="mRAD inválido. Use 1, 2, 3 o 4.")

    q = text(f"""
        SELECT {select_cols}
        FROM {t_ventas} AS c
        LEFT JOIN tipos_comprobantes AS t ON t.id=c.id_comprobante
        WHERE c.id_empresa=:eid{where_extra}{fechaf}
        {group} ORDER BY {order}
    """)

    try:
        result = _rows_to_dicts(db.execute(q, params))
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Totales de Ventas")



@router.get("/ventas/provincias")
def ventas_provincias(
    mrad: int = Query(1, description="1=agrupado por periodo, 2=agrupado por fecha, 3=detalle por fecha, 4=detalle por registracion"),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("ventas_provincias", eid, mrad, desde, hasta, sucursal, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"
    where = "WHERE c.id_empresa = :eid"

    if sucursal:
        sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
        if sucursal_ids:
            placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
            where += f" AND c.id_sucursal IN ({placeholders})"
            for i, s in enumerate(sucursal_ids):
                params[f"suc_{i}"] = s

    if mrad == 1:
        if desde:
            where += " AND CONCAT(LPAD(c.ano_imputacion,4,'0'),LPAD(c.mes_imputacion,2,'0')) >= :desde"
            params["desde"] = desde.replace("-", "")[:6]
        if hasta:
            where += " AND CONCAT(LPAD(c.ano_imputacion,4,'0'),LPAD(c.mes_imputacion,2,'0')) <= :hasta"
            params["hasta"] = hasta.replace("-", "")[:6]

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                MAX(c.fecha) AS fecha,
                MAX(p.nombre) AS provincia,
                SUM(IF(t.tipo='+', c.neto_gravado, -c.neto_gravado)) AS ng,
                SUM(IF(t.tipo='+', c.iva, -c.iva)) AS iv,
                SUM(IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias))) AS otros,
                SUM(IF(t.tipo='+', c.total_comprobante, -c.total_comprobante)) AS tot
            FROM {t_ventas} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN provincias p ON p.id = c.id_provincia
            {where}
            GROUP BY c.mes_imputacion, c.ano_imputacion, c.id_provincia
            ORDER BY c.ano_imputacion, c.mes_imputacion
        """)

    elif mrad == 2:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")

        q = text(f"""
            SELECT
                MAX(c.mes_imputacion) AS mes_imputacion,
                MAX(c.ano_imputacion) AS ano_imputacion,
                c.fecha,
                MAX(p.nombre) AS provincia,
                SUM(IF(t.tipo='+', c.neto_gravado, -c.neto_gravado)) AS ng,
                SUM(IF(t.tipo='+', c.iva, -c.iva)) AS iv,
                SUM(IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias))) AS otros,
                SUM(IF(t.tipo='+', c.total_comprobante, -c.total_comprobante)) AS tot
            FROM {t_ventas} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN provincias p ON p.id = c.id_provincia
            {where}
            GROUP BY c.fecha, c.id_provincia
            ORDER BY c.fecha
        """)

    elif mrad == 3:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                c.fecha,
                p.nombre AS provincia,
                IF(t.tipo='+', c.neto_gravado, -c.neto_gravado) AS ng,
                IF(t.tipo='+', c.iva, -c.iva) AS iv,
                IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias)) AS otros,
                IF(t.tipo='+', c.total_comprobante, -c.total_comprobante) AS tot
            FROM {t_ventas} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN provincias p ON p.id = c.id_provincia
            {where}
            ORDER BY c.fecha
        """)

    elif mrad == 4:
        if desde:
            where += " AND DATE(c.registracion) >= :desde"
            params["desde"] = desde
        if hasta:
            where += " AND DATE(c.registracion) <= :hasta"
            params["hasta"] = hasta

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                DATE(c.registracion) AS fecha,
                p.nombre AS provincia,
                IF(t.tipo='+', c.neto_gravado, -c.neto_gravado) AS ng,
                IF(t.tipo='+', c.iva, -c.iva) AS iv,
                IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias)) AS otros,
                IF(t.tipo='+', c.total_comprobante, -c.total_comprobante) AS tot
            FROM {t_ventas} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN provincias p ON p.id = c.id_provincia
            {where}
            ORDER BY DATE(c.registracion)
        """)
    else:
        raise HTTPException(status_code=400, detail="mRAD inválido. Use 1, 2, 3 o 4.")

    try:
        rows = _rows_to_dicts(db.execute(q, params))
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Totales de Ventas por Provincias")
    _cache_set(cache_key, rows)
    return rows



@router.get("/ventas/vendedor")
def ventas_vendedor(
    mrad: int = Query(1, description="1=agrupado por periodo, 2=agrupado por fecha, 3=detalle por fecha, 4=detalle por registracion"),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("ventas_vendedor", eid, mrad, desde, hasta, sucursal, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"
    where = "WHERE c.id_empresa = :eid"

    if sucursal:
        sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
        if sucursal_ids:
            placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
            where += f" AND c.id_sucursal IN ({placeholders})"
            for i, s in enumerate(sucursal_ids):
                params[f"suc_{i}"] = s

    if mrad == 1:
        if desde:
            where += " AND CONCAT(LPAD(c.ano_imputacion,4,'0'),LPAD(c.mes_imputacion,2,'0')) >= :desde"
            params["desde"] = desde.replace("-", "")[:6]
        if hasta:
            where += " AND CONCAT(LPAD(c.ano_imputacion,4,'0'),LPAD(c.mes_imputacion,2,'0')) <= :hasta"
            params["hasta"] = hasta.replace("-", "")[:6]

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                MAX(c.fecha) AS fecha,
                MAX(p.nombre) AS vendedor,
                SUM(IF(t.tipo='+', c.neto_gravado, -c.neto_gravado)) AS ng,
                SUM(IF(t.tipo='+', c.iva, -c.iva)) AS iv,
                SUM(IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias))) AS otros,
                SUM(IF(t.tipo='+', c.total_comprobante, -c.total_comprobante)) AS tot
            FROM {t_ventas} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN vendedores p ON p.id = c.id_vendedor
            {where}
            GROUP BY c.mes_imputacion, c.ano_imputacion, c.id_vendedor
            ORDER BY c.ano_imputacion, c.mes_imputacion
        """)

    elif mrad == 2:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")

        q = text(f"""
            SELECT
                MAX(c.mes_imputacion) AS mes_imputacion,
                MAX(c.ano_imputacion) AS ano_imputacion,
                c.fecha,
                MAX(p.nombre) AS vendedor,
                SUM(IF(t.tipo='+', c.neto_gravado, -c.neto_gravado)) AS ng,
                SUM(IF(t.tipo='+', c.iva, -c.iva)) AS iv,
                SUM(IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias))) AS otros,
                SUM(IF(t.tipo='+', c.total_comprobante, -c.total_comprobante)) AS tot
            FROM {t_ventas} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN vendedores p ON p.id = c.id_vendedor
            {where}
            GROUP BY c.fecha, c.id_vendedor
            ORDER BY c.fecha
        """)

    elif mrad == 3:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                c.fecha,
                p.nombre AS vendedor,
                IF(t.tipo='+', c.neto_gravado, -c.neto_gravado) AS ng,
                IF(t.tipo='+', c.iva, -c.iva) AS iv,
                IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias)) AS otros,
                IF(t.tipo='+', c.total_comprobante, -c.total_comprobante) AS tot
            FROM {t_ventas} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN vendedores p ON p.id = c.id_vendedor
            {where}
            ORDER BY c.fecha
        """)

    elif mrad == 4:
        if desde:
            where += " AND DATE(c.registracion) >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND DATE(c.registracion) <= :hasta"
            params["hasta"] = hasta.replace("-", "")

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                DATE(c.registracion) AS fecha,
                p.nombre AS vendedor,
                IF(t.tipo='+', c.neto_gravado, -c.neto_gravado) AS ng,
                IF(t.tipo='+', c.iva, -c.iva) AS iv,
                IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias)) AS otros,
                IF(t.tipo='+', c.total_comprobante, -c.total_comprobante) AS tot
            FROM {t_ventas} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN vendedores p ON p.id = c.id_vendedor
            {where}
            ORDER BY DATE(c.registracion)
        """)

    else:
        raise HTTPException(status_code=400, detail="mRAD inválido. Use 1, 2, 3 o 4.")

    try:
        rows = _rows_to_dicts(db.execute(q, params))
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Totales de Ventas por Vendedor")
    _cache_set(cache_key, rows)
    return rows



@router.get("/ventas/zonas")
def ventas_zonas(
    mrad: int = Query(1, description="1=agrupado por periodo, 2=agrupado por fecha, 3=detalle por fecha, 4=detalle por registracion"),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("ventas_zonas", eid, mrad, desde, hasta, sucursal, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"
    where = "WHERE c.id_empresa = :eid"

    if sucursal:
        sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
        if sucursal_ids:
            placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
            where += f" AND c.id_sucursal IN ({placeholders})"
            for i, s in enumerate(sucursal_ids):
                params[f"suc_{i}"] = s

    if mrad == 1:
        if desde:
            where += " AND CONCAT(LPAD(c.ano_imputacion,4,'0'),LPAD(c.mes_imputacion,2,'0')) >= :desde"
            params["desde"] = desde.replace("-", "")[:6]
        if hasta:
            where += " AND CONCAT(LPAD(c.ano_imputacion,4,'0'),LPAD(c.mes_imputacion,2,'0')) <= :hasta"
            params["hasta"] = hasta.replace("-", "")[:6]

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                MAX(c.fecha) AS fecha,
                MAX(p.nombre) AS zona,
                SUM(IF(t.tipo='+', c.neto_gravado, -c.neto_gravado)) AS ng,
                SUM(IF(t.tipo='+', c.iva, -c.iva)) AS iv,
                SUM(IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias))) AS otros,
                SUM(IF(t.tipo='+', c.total_comprobante, -c.total_comprobante)) AS tot
            FROM {t_ventas} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN zonas p ON p.id = c.id_zona
            {where}
            GROUP BY c.mes_imputacion, c.ano_imputacion, c.id_zona
            ORDER BY c.ano_imputacion, c.mes_imputacion
        """)

    elif mrad == 2:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")

        q = text(f"""
            SELECT
                MAX(c.mes_imputacion) AS mes_imputacion,
                MAX(c.ano_imputacion) AS ano_imputacion,
                c.fecha,
                MAX(p.nombre) AS zona,
                SUM(IF(t.tipo='+', c.neto_gravado, -c.neto_gravado)) AS ng,
                SUM(IF(t.tipo='+', c.iva, -c.iva)) AS iv,
                SUM(IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias))) AS otros,
                SUM(IF(t.tipo='+', c.total_comprobante, -c.total_comprobante)) AS tot
            FROM {t_ventas} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN zonas p ON p.id = c.id_zona
            {where}
            GROUP BY c.fecha, c.id_zona
            ORDER BY c.fecha
        """)

    elif mrad == 3:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                c.fecha,
                p.nombre AS zona,
                IF(t.tipo='+', c.neto_gravado, -c.neto_gravado) AS ng,
                IF(t.tipo='+', c.iva, -c.iva) AS iv,
                IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias)) AS otros,
                IF(t.tipo='+', c.total_comprobante, -c.total_comprobante) AS tot
            FROM {t_ventas} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN zonas p ON p.id = c.id_zona
            {where}
            ORDER BY c.fecha
        """)

    elif mrad == 4:
        if desde:
            where += " AND DATE(c.registracion) >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND DATE(c.registracion) <= :hasta"
            params["hasta"] = hasta.replace("-", "")

        q = text(f"""
            SELECT
                c.mes_imputacion,
                c.ano_imputacion,
                DATE(c.registracion) AS fecha,
                p.nombre AS zona,
                IF(t.tipo='+', c.neto_gravado, -c.neto_gravado) AS ng,
                IF(t.tipo='+', c.iva, -c.iva) AS iv,
                IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias)) AS otros,
                IF(t.tipo='+', c.total_comprobante, -c.total_comprobante) AS tot
            FROM {t_ventas} c
            LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
            LEFT JOIN zonas p ON p.id = c.id_zona
            {where}
            ORDER BY DATE(c.registracion)
        """)

    else:
        raise HTTPException(status_code=400, detail="mRAD inválido. Use 1, 2, 3 o 4.")

    try:
        rows = _rows_to_dicts(db.execute(q, params))
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Totales de Ventas por Zonas")
    _cache_set(cache_key, rows)
    return rows



@router.get("/ventas/clientes_totales")
def ventas_clientes_totales(
    mrad: int = Query(1, description="1=agrupado por periodo, 2=agrupado por fecha, 3=detalle por cliente, 4=detalle por registracion"),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    cliente: Optional[str] = Query(None, description="Filtro por nombre de cliente"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("ventas_clientes_totales", eid, mrad, desde, hasta, sucursal, cliente, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"
    t_esporadicos = "esporadicos" if estado == 0 else "_esporadicos"
    where = "WHERE c.id_empresa = :eid"

    if sucursal:
        sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
        if sucursal_ids:
            placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
            where += f" AND c.id_sucursal IN ({placeholders})"
            for i, s in enumerate(sucursal_ids):
                params[f"suc_{i}"] = s

    if cliente:
        where += " AND p.nombre LIKE :cliente"
        params["cliente"] = f"%{cliente}%"

    joins = f"""
        FROM {t_ventas} c
        LEFT JOIN tipos_comprobantes t ON t.id = c.id_comprobante
        LEFT JOIN clientes p ON p.id = c.id_cliente
        LEFT JOIN {t_esporadicos} e ON e.id = c.id_esporadico
        LEFT JOIN zonas z ON z.id = p.id_zona
    """

    select_agg = """
        MAX(c.mes_imputacion) AS mes_imputacion, MAX(c.ano_imputacion) AS ano_imputacion, MAX(c.fecha) AS fecha,
        MAX(p.nombre) AS cliente, MAX(e.nombre) AS espo,
        SUM(IF(t.tipo='+', c.neto_gravado, -c.neto_gravado)) AS ng,
        SUM(IF(t.tipo='+', c.iva, -c.iva)) AS iv,
        SUM(IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias))) AS otros,
        SUM(IF(t.tipo='+', c.total_comprobante, -c.total_comprobante)) AS tot,
        0 AS porcentaje, MAX(z.nombre) AS zona
    """

    select_det = """
        c.mes_imputacion, c.ano_imputacion, DATE(c.registracion) AS fecha,
        p.nombre AS cliente, e.nombre AS espo,
        IF(t.tipo='+', c.neto_gravado, -c.neto_gravado) AS ng,
        IF(t.tipo='+', c.iva, -c.iva) AS iv,
        IF(t.tipo='+', (c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias), -(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias)) AS otros,
        IF(t.tipo='+', c.total_comprobante, -c.total_comprobante) AS tot,
        0 AS porcentaje, z.nombre AS zona
    """

    if mrad == 1:
        if desde:
            where += " AND CONCAT(LPAD(c.ano_imputacion,4,'0'),LPAD(c.mes_imputacion,2,'0')) >= :desde"
            params["desde"] = desde.replace("-", "")[:6]
        if hasta:
            where += " AND CONCAT(LPAD(c.ano_imputacion,4,'0'),LPAD(c.mes_imputacion,2,'0')) <= :hasta"
            params["hasta"] = hasta.replace("-", "")[:6]
        select_cols = select_agg
        group = " GROUP BY c.mes_imputacion, c.ano_imputacion, c.id_cliente, c.id_esporadico"
        order = " ORDER BY c.ano_imputacion, c.mes_imputacion"

    elif mrad == 2:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")
        select_cols = select_agg
        group = " GROUP BY c.fecha, c.id_cliente, c.id_esporadico"
        order = " ORDER BY tot DESC"

    elif mrad == 3:
        if desde:
            where += " AND c.fecha >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND c.fecha <= :hasta"
            params["hasta"] = hasta.replace("-", "")
        select_cols = select_agg
        group = " GROUP BY c.id_cliente, c.id_esporadico"
        order = " ORDER BY tot DESC"

    elif mrad == 4:
        if desde:
            where += " AND DATE(c.registracion) >= :desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            where += " AND DATE(c.registracion) <= :hasta"
            params["hasta"] = hasta.replace("-", "")
        select_cols = select_det
        group = ""
        order = " ORDER BY tot DESC"

    else:
        raise HTTPException(status_code=400, detail="mRAD inválido. Use 1, 2, 3 o 4.")

    q = text(f"SELECT {select_cols} {joins} {where} {group} {order}")

    try:
        rows = _rows_to_dicts(db.execute(q, params))
        if mrad in (3, 4):
            cSumador = sum(round(float(r["tot"] or 0), 2) for r in rows)
            if cSumador != 0:
                for r in rows:
                    r["porcentaje"] = round((round(float(r["tot"] or 0), 2) / cSumador) * 100, 2)
        _cache_set(cache_key, rows)
        return rows
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Totales de Ventas por Clientes")



@router.get("/ventas/insumos")
def ventas_insumos(
    mrad: int = Query(2, description="0=desde (dato unico), 1=periodo, 2=fecha, 3=rango de fecha, 4=registracion"),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    rubro: Optional[str] = Query(None, description="Filtro por nombre de rubro"),
    segundo: int = Query(1, description="1=agrupado por articulo, 2=agrupado por cliente+articulo"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("ventas_insumos", eid, mrad, desde, hasta, sucursal, rubro, segundo, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_cuerpo = "comprobantes_cuerpo" if estado == 0 else "_comprobantes_cuerpo"
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"
    t_esporadicos = "esporadicos" if estado == 0 else "_esporadicos"
    where = "WHERE c.id_empresa=:eid and c.identificacion like binary 'V'"

    if sucursal:
        sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
        if sucursal_ids:
            placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
            where += f" and c.id_sucursal IN ({placeholders})"
            for i, s in enumerate(sucursal_ids):
                params[f"suc_{i}"] = s

    if rubro:
        where += " and r.nombre LIKE :rubro"
        params["rubro"] = f"%{rubro}%"

    moneda = mrad != 1
    fechaf = ""
    if mrad == 1:
        if desde:
            fechaf += " and concat(lpad(year(c.fecha_movimiento),4,'0'),lpad(month(c.fecha_movimiento),2,'0'))>=:desde"
            params["desde"] = desde.replace("-", "")[:6]
        if hasta:
            fechaf += " and concat(lpad(year(c.fecha_movimiento),4,'0'),lpad(month(c.fecha_movimiento),2,'0'))<=:hasta"
            params["hasta"] = hasta.replace("-", "")[:6]
    elif mrad == 4:
        if desde:
            fechaf += " and DATE(c.registracion)>=:desde"
            params["desde"] = desde.replace("-", "")
        if hasta:
            fechaf += " and DATE(c.registracion)<=:hasta"
            params["hasta"] = hasta.replace("-", "")
    else:
        if desde:
            fechaf += " and c.fecha_movimiento>=:desde"
            params["desde"] = desde.replace("-", "")
        if hasta and mrad != 0:
            fechaf += " and c.fecha_movimiento<=:hasta"
            params["hasta"] = hasta.replace("-", "")

    if segundo == 1:
        group = "GROUP BY (c.cantidad>0),c.id_articulo,c.id_unidad_medida"
        order = "ORDER BY nom"
    else:
        group = "GROUP BY (c.cantidad>0),c.id_clipro,c.id_articulo,c.id_unidad_medida"
        order = "ORDER BY DATE(c.registracion),nom" if mrad == 4 else "ORDER BY c.fecha_movimiento,nom"

    moneda_join = "LEFT JOIN tipos_moneda AS m ON m.id=a.id_moneda " if moneda else ""
    precio_costo = "MAX(a.precio_costo * COALESCE(m.valor_en_pesos,1)) AS precio_costo" if moneda else "MAX(a.precio_costo) AS precio_costo"
    if moneda:
        utilidad = "sum(-c.cantidad * IF(v.total_en_dolares>1, c.precio_real/v.total_en_dolares, c.precio_real)) - sum(-c.cantidad * a.precio_costo * COALESCE(m.valor_en_pesos,1)) AS utilidad"
    else:
        utilidad = "sum(-c.cantidad * IF(v.total_en_dolares>1, c.precio_real/v.total_en_dolares, c.precio_real)) - sum(-c.cantidad * a.precio_costo) AS utilidad"
    if mrad == 4:
        tot = "sum(if(c.identificacion='C',c.cantidad,-c.cantidad) * IF(v.total_en_dolares>1, c.precio/v.total_en_dolares, c.precio)) AS tot"
    else:
        tot = "sum(if(c.identificacion='C',c.cantidad,-c.cantidad) * IF(v.total_en_dolares>1, c.precio/v.total_en_dolares, c.precio)*(100-c.bonificacion)/100) AS tot"

    q = text(f"""
        SELECT
            MAX(if(c.cantidad>0,'NC Venta','Venta')) AS ide,
            MAX(a.codigo_de_barras) AS codigo_de_barras,
            MAX(concat_ws(' ',a.descripcion_larga,a.codigo_accesorio)) AS nom,
            MAX(t.nombre) AS tip,
            MAX(r.nombre) AS rub,
            MAX(c.fecha_movimiento) AS fecha_movimiento,
            {precio_costo},
            sum(c.cantidad) AS cant,
            MAX(ROUND(IF(v.total_en_dolares>1, c.precio/v.total_en_dolares, c.precio)*(100-c.bonificacion)/100,2)) AS precio,
            MAX(c.bonificacion) AS bonificacion,
            MAX(IF(v.total_en_dolares>1, c.precio_real/v.total_en_dolares, c.precio_real)) AS precio_real,
            MAX(u.nombre) AS uni,
            MAX(i.nombre) AS ali,
            MAX(p.nombre) AS pro,
            MAX(e.nombre) AS espo,
            MAX(c.comprobante) AS comprobante,
            {tot},
            {utilidad},
            MAX(if(v.total_en_dolares>1,v.total_en_dolares,0)) AS tipo_cambio
        FROM {t_cuerpo} AS c
        LEFT JOIN articulos AS a ON a.id=c.id_articulo
        {moneda_join}LEFT JOIN parametros_tipos_articulos AS t ON t.id=a.id_tipo
        LEFT JOIN rubros AS r ON r.id=a.id_rubro
        LEFT JOIN unidades AS u ON u.id=c.id_unidad_medida
        LEFT JOIN tipos_alicuotas_iva AS i ON i.id=c.id_alicuota_iva
        LEFT JOIN clientes AS p ON p.id=c.id_clipro
        LEFT JOIN {t_esporadicos} AS e ON e.id=c.id_esporadico
        LEFT JOIN {t_ventas} AS v ON v.id=c.id_comprobante
        {where} {fechaf}
        {group}
        {order}
    """)

    try:
        det = _rows_to_dicts(db.execute(q, params))
        result = {
            "totalInsumos": len(det),
            "cantidadTotal": sum(float(d["cant"] or 0) for d in det),
            "montoTotal": sum(float(d["tot"] or 0) for d in det),
            "detalle": det
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Ventas Insumos")



@router.get("/herramientas/comparativos")
def herramientas_comparativos(
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("herramientas_comparativos", eid, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_compras = "comprobantes_compras" if estado == 0 else "_comprobantes_compras"
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"

    q = text(f"""
        SELECT
            periodo,
            SUM(ventas) AS ventas,
            SUM(compras) AS compras
        FROM (
            SELECT DATE_FORMAT(v.fecha, '%Y-%m') AS periodo,
                   SUM(IF(t.tipo = '+', v.total_comprobante, -v.total_comprobante)) AS ventas, 0 AS compras
            FROM {t_ventas} v
            LEFT JOIN tipos_comprobantes t ON t.id = v.id_comprobante
            WHERE v.id_empresa = :eid AND v.anulado = 0
            GROUP BY periodo
            UNION ALL
            SELECT DATE_FORMAT(c.fecha, '%Y-%m') AS periodo,
                   0 AS ventas, SUM(IF(t2.tipo = '+', c.total_comprobante, -c.total_comprobante)) AS compras
            FROM {t_compras} c
            LEFT JOIN tipos_comprobantes t2 ON t2.id = c.id_comprobante
            WHERE c.id_empresa = :eid
            GROUP BY periodo
        ) t
        GROUP BY periodo
        ORDER BY periodo DESC
        LIMIT 24
    """)

    try:
        result = _rows_to_dicts(db.execute(q, params))
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Herramientas Comparativos")



@router.get("/herramientas/cuenta")
def herramientas_cuenta(
    buscar: Optional[str] = Query(None),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("herramientas_cuenta", eid, buscar)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}

    if not buscar:
        q_clientes_all = text("""
            SELECT
                cl.nombre AS nombre,
                cp.fecha, cp.comprobante, cp.tipo, cp.debe, cp.haber, cp.saldo
            FROM cuentas_corrientes_clientes cp
            INNER JOIN clientes cl ON cl.id = cp.id_cliente AND cl.id_empresa = cp.id_empresa
            WHERE cp.id_empresa = :eid
            ORDER BY cp.fecha DESC
            LIMIT 200
        """)
        q_proveedores_all = text("""
            SELECT
                pr.nombre AS nombre,
                cp.fecha, cp.comprobante, cp.tipo, cp.debe, cp.haber, cp.saldo
            FROM cuentas_corrientes_proveedores cp
            INNER JOIN proveedores pr ON pr.id = cp.id_proveedor AND pr.id_empresa = cp.id_empresa
            WHERE cp.id_empresa = :eid
            ORDER BY cp.fecha DESC
            LIMIT 200
        """)
        try:
            result = {
                "clientes": _rows_to_dicts(db.execute(q_clientes_all, params)),
                "proveedores": _rows_to_dicts(db.execute(q_proveedores_all, params))
            }
            _cache_set(cache_key, result)
            return result
        except Exception:
            raise HTTPException(status_code=500, detail="Error en Herramientas Cuenta")

    q_clientes = text("""
        SELECT
            cl.nombre AS nombre,
            cc.fecha, cc.comprobante, cc.tipo, cc.debe, cc.haber, cc.saldo
        FROM cuentas_corrientes_clientes cc
        INNER JOIN clientes cl ON cl.id = cc.id_cliente AND cl.id_empresa = cc.id_empresa
        WHERE cc.id_empresa = :eid AND cl.nombre LIKE :buscar
        ORDER BY cc.fecha DESC
        LIMIT 200
    """)
    q_proveedores = text("""
        SELECT
            pr.nombre AS nombre,
            cp.fecha, cp.comprobante, cp.tipo, cp.debe, cp.haber, cp.saldo
        FROM cuentas_corrientes_proveedores cp
        INNER JOIN proveedores pr ON pr.id = cp.id_proveedor AND pr.id_empresa = cp.id_empresa
        WHERE cp.id_empresa = :eid AND pr.nombre LIKE :buscar
        ORDER BY cp.fecha DESC
        LIMIT 200
    """)

    params["buscar"] = f"%{buscar}%"

    try:
        result = {
            "clientes": _rows_to_dicts(db.execute(q_clientes, params)),
            "proveedores": _rows_to_dicts(db.execute(q_proveedores, params))
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Herramientas Cuenta")



@router.get("/herramientas/facturacion")
def herramientas_facturacion(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    tipo_comprobante: Optional[str] = Query(None),
    cliente: Optional[str] = Query(None),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("herramientas_facturacion", eid, desde, hasta, tipo_comprobante, cliente, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"
    where = "WHERE v.id_empresa = :eid AND v.anulado = 0"

    if desde:
        where += " AND v.fecha >= :desde"
        params["desde"] = desde.replace("-", "")
    if hasta:
        where += " AND v.fecha <= :hasta"
        params["hasta"] = hasta.replace("-", "")
    if cliente:
        where += " AND v.nombre_cliente LIKE :cli"
        params["cli"] = f"%{cliente}%"
    if tipo_comprobante and tipo_comprobante != "Todos":
        tipo_map = {
            "Factura A": 1, "Factura B": 6, "Factura C": 11,
            "Nota de Crédito": [3, 8, 13], "Nota de Débito": [2, 7, 12]
        }
        ids = tipo_map.get(tipo_comprobante)
        if ids is not None:
            if isinstance(ids, list):
                placeholders = ", ".join(f":tipo_{i}" for i in range(len(ids)))
                where += f" AND v.id_comprobante IN ({placeholders})"
                for i, tipo_id in enumerate(ids):
                    params[f"tipo_{i}"] = tipo_id
            else:
                where += " AND v.id_comprobante = :tipo"
                params["tipo"] = ids

    q = text(f"""
        SELECT
            CONCAT(COALESCE(NULLIF(t.abreviatura, ''), 'T'), '-',
                   LPAD(v.sucursal, 4, '0'), '-',
                   LPAD(v.numero, 8, '0')) AS comprobante,
            v.nombre_cliente AS cliente,
            v.fecha,
            IF(t.tipo = '+', v.total_comprobante, -v.total_comprobante) AS total,
            v.neto_gravado AS neto,
            v.iva
        FROM {t_ventas} v
        LEFT JOIN tipos_comprobantes t ON t.id = v.id_comprobante
        {where}
        ORDER BY v.fecha DESC
        LIMIT 500
    """)

    try:
        result = _rows_to_dicts(db.execute(q, params))
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Herramientas Facturacion")



@router.get("/herramientas/indicadores")
def herramientas_indicadores(
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("herramientas_indicadores", eid, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_compras = "comprobantes_compras" if estado == 0 else "_comprobantes_compras"
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"

    q_ventas = text(f"SELECT COALESCE(SUM(IF(t.tipo = '+', v.total_comprobante, -v.total_comprobante)), 0) FROM {t_ventas} v LEFT JOIN tipos_comprobantes t ON t.id = v.id_comprobante WHERE v.id_empresa = :eid AND v.anulado = 0")
    q_compras = text(f"SELECT COALESCE(SUM(total_comprobante), 0) FROM {t_compras} WHERE id_empresa = :eid")
    q_clientes = text("SELECT COUNT(*) FROM clientes WHERE id_empresa = :eid")
    q_proveedores = text("SELECT COUNT(*) FROM proveedores WHERE id_empresa = :eid")

    try:
        result = {
            "ventas_totales": float(db.execute(q_ventas, params).scalar()),
            "compras_totales": float(db.execute(q_compras, params).scalar()),
            "clientes": int(db.execute(q_clientes, params).scalar()),
            "proveedores": int(db.execute(q_proveedores, params).scalar())
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Herramientas Indicadores")


# QUES=11 del programa original - Compras y Ventas por Insumos, Artículos o

@router.get("/insumos/compras-ventas")
def insumos_compras_ventas(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    mrad: int = Query(1, description="1=periodo, 2=entre fechas, 3=detalle por movimiento, 4=registracion"),
    segundo: int = Query(2, description="1=agrupado, 2=desagregado"),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    rubro: Optional[str] = Query(None, description="Filtro por nombre de rubro"),
    estado: int = Query(0, description="0=usa precio_ultima_compra, >0=usa precio_ultima_compra_"),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("insumos_compras_ventas", eid, desde, hasta, mrad, segundo, sucursal, rubro, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_cuerpo = "comprobantes_cuerpo" if estado == 0 else "_comprobantes_cuerpo"
    t_esporadicos = "esporadicos" if estado == 0 else "_esporadicos"

    where = "WHERE c.id_empresa=:eid"
    if sucursal:
        sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
        if sucursal_ids:
            placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
            where += f" and c.id_sucursal IN ({placeholders})"
            for i, s in enumerate(sucursal_ids):
                params[f"suc_{i}"] = s
    if rubro:
        where += " and r.nombre LIKE :rubro"
        params["rubro"] = f"%{rubro}%"

    agrupado = (mrad == 1 or mrad == 2)

    def av(expr):
        return f"MAX({expr})" if agrupado else expr

    precio_arti = "a.precio_ultima_compra" if estado == 0 else "a.precio_ultima_compra_"
    caso_fecha = "c.fecha_movimiento" if mrad != 4 else "DATE(c.registracion)"

    fechaf = ""
    if mrad == 1:
        if desde:
            params["desde_per"] = desde.replace("-", "")[:6]
            fechaf += " and concat(lpad(year(c.fecha_movimiento),4,'0'),lpad(month(c.fecha_movimiento),2,'0'))>=:desde_per"
        if hasta:
            params["hasta_per"] = hasta.replace("-", "")[:6]
            fechaf += " and concat(lpad(year(c.fecha_movimiento),4,'0'),lpad(month(c.fecha_movimiento),2,'0'))<=:hasta_per"
    else:
        if desde:
            params["desde"] = desde.replace("-", "")
            fechaf += f" and {caso_fecha}>=:desde"
        if hasta:
            params["hasta"] = hasta.replace("-", "")
            fechaf += f" and {caso_fecha}<=:hasta"

    if agrupado:
        caso_cant = "sum(c.cantidad) AS cant"
        caso_tot = "sum(if(c.identificacion='C',c.cantidad,-c.cantidad)*c.precio) AS tot"
        group = " GROUP BY c.id_articulo,c.identificacion,c.id_unidad_medida"
        order = " ORDER BY nom"
    else:
        caso_cant = "c.cantidad AS cant"
        caso_tot = "(if(c.identificacion='C',c.cantidad,-c.cantidad)*c.precio) AS tot"
        group = ""
        order = f" ORDER BY {caso_fecha},nom"

    q = text(f"""
        SELECT
            {av("if(c.identificacion='C','Compra','Venta')")} AS ide,
            {av("a.codigo_de_barras")} AS codigo_de_barras,
            {av("concat_ws(' ',a.descripcion_larga,a.codigo_accesorio)")} AS nom,
            {av("t.nombre")} AS tip,
            {av("r.nombre")} AS rub,
            {av(caso_fecha)} AS fecha,
            {caso_cant},
            {av(f"IF(c.identificacion='C',{precio_arti},c.precio)")} AS precio,
            {av("c.bonificacion")} AS bonificacion,
            {av("c.precio_real")} AS precio_real,
            {av("u.nombre")} AS uni,
            {av("i.nombre")} AS ali,
            {av("p.nombre")} AS pro,
            {av("e.nombre")} AS espo,
            {av("c.comprobante")} AS comprobante,
            {caso_tot}
        FROM {t_cuerpo} AS c
        LEFT JOIN articulos AS a ON a.id=c.id_articulo
        LEFT JOIN parametros_tipos_articulos AS t ON t.id=a.id_tipo
        LEFT JOIN rubros AS r ON r.id=a.id_rubro
        LEFT JOIN unidades AS u ON u.id=c.id_unidad_medida
        LEFT JOIN tipos_alicuotas_iva AS i ON i.id=c.id_alicuota_iva
        LEFT JOIN proveedores AS p ON p.id=c.id_clipro
        LEFT JOIN {t_esporadicos} AS e ON e.id=c.id_esporadico
        {where} {fechaf}
        {group}
        {order}
    """)

    try:
        det = _rows_to_dicts(db.execute(q, params))
        result = {
            "titulo": "Compras y Ventas por Insumos, Artículos o Productos",
            "segundo": segundo,
            "totalMovimientos": len(det),
            "cantidadTotal": sum(float(d["cant"] or 0) for d in det),
            "montoTotal": sum(float(d["tot"] or 0) for d in det),
            "detalle": det
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Compras y Ventas por Insumos")


# QUES=12 del programa original - Ventas por Insumos, Artículos o Productos por

@router.get("/ventas/insumos-comprobante")
def ventas_insumos_comprobante(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    mrad: int = Query(1, description="1=periodo, 2=entre fechas, 3=detalle, 4=registracion"),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    cliente: Optional[str] = Query(None, description="Filtro por nombre de cliente"),
    deprueba: bool = Query(False, description="True=reemplaza nombre de cliente por 'Cliente DEMO'"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("ventas_insumos_comprobante", eid, desde, hasta, mrad, sucursal, cliente, deprueba, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid, "deprueba": 1 if deprueba else 0}
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"

    where = "WHERE c.id_empresa=:eid and c.anulado=0"
    if sucursal:
        sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
        if sucursal_ids:
            placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
            where += f" and c.id_sucursal IN ({placeholders})"
            for i, s in enumerate(sucursal_ids):
                params[f"suc_{i}"] = s
    if cliente:
        where += " and c.nombre_cliente LIKE :cliente"
        params["cliente"] = f"%{cliente}%"

    caso_fecha = "c.fecha" if mrad != 4 else "DATE(c.registracion)"
    caso_orden = "c.fecha,c.id_comprobante,c.sucursal,c.numero" if mrad != 4 else "DATE(c.registracion),c.id_comprobante,c.sucursal,c.numero"

    fechaf = ""
    if mrad == 1:
        if desde:
            params["desde_per"] = desde.replace("-", "")[:6]
            fechaf += " and concat(lpad(year(c.fecha),4,'0'),lpad(month(c.fecha),2,'0'))>=:desde_per"
        if hasta:
            params["hasta_per"] = hasta.replace("-", "")[:6]
            fechaf += " and concat(lpad(year(c.fecha),4,'0'),lpad(month(c.fecha),2,'0'))<=:hasta_per"
    else:
        if desde:
            params["desde"] = desde.replace("-", "")
            fechaf += f" and {caso_fecha}>=:desde"
        if hasta:
            params["hasta"] = hasta.replace("-", "")
            fechaf += f" and {caso_fecha}<=:hasta"

    q = text(f"""
        SELECT
            {caso_fecha} AS fecha,
            concat(ltrim(t.abreviatura),'-',t.letra,'-',lpad(cast(c.sucursal as char),5,'0'),'-',lpad(cast(c.numero as char),8,'0')) AS compro,
            IF(:deprueba, CONCAT('Cliente DEMO ', LPAD(c.id_cliente, 6, '0')), c.nombre_cliente) AS nombre_cliente,
            IF(c.cuit IS null or c.cuit='' or c.cuit='  -        - ','NO INFORMA',c.cuit) AS cuit,
            if(t.tipo='+',c.neto_gravado,-c.neto_gravado) as ng,
            if(t.tipo='+',c.iva,-c.iva) as iv,
            if(t.tipo='+',(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias),-(c.percepcion_iva+c.percepcion_i_brutos+c.exento+c.impuestos_internos+c.retencion_ganancias)) AS otros,
            if(t.tipo='+',c.total_comprobante,-c.total_comprobante) as tot,
            c.id,
            if(t.tipo='+',c.total_en_dolares,-c.total_en_dolares) as totus
        FROM {t_ventas} AS c
        LEFT JOIN tipos_comprobantes AS t ON t.id=c.id_comprobante
        {where} {fechaf}
        ORDER BY {caso_orden}
    """)

    try:
        det = _rows_to_dicts(db.execute(q, params))
        result = {
            "titulo": "Ventas por Insumos, Artículos o Productos por Comprobantes",
            "deprueba": deprueba,
            "cantidadComprobantes": len(det),
            "totalComprobantes": sum(float(d["tot"] or 0) for d in det),
            "detalle": det
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Ventas por Insumos por Comprobante")


# QUES=13 del programa original - Gastos. Combina 'Por Compras' (comprobantes

@router.get("/gastos/detalle")
def gastos_detalle(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    mrad: int = Query(1, description="1=periodo, 2=entre fechas, 3=detalle por movimiento, 4=registracion"),
    sucursal: Optional[str] = Query(None, description="IDs de sucursal separados por coma"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("gastos_detalle", eid, desde, hasta, mrad, sucursal, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_cuerpo = "comprobantes_cuerpo" if estado == 0 else "_comprobantes_cuerpo"
    t_ingresos = "ingresos_egresos" if estado == 0 else "_ingresos_egresos"

    def _add_sucursal(prefix):
        cond = ""
        if sucursal:
            sucursal_ids = [s.strip() for s in sucursal.split(",") if s.strip()]
            if sucursal_ids:
                placeholders = ", ".join(f":suc_{i}" for i in range(len(sucursal_ids)))
                cond += f" and {prefix}.id_sucursal IN ({placeholders})"
                for i, s in enumerate(sucursal_ids):
                    params[f"suc_{i}"] = s
        return cond

    donde_c = "WHERE c.id_empresa=:eid and BINARY c.identificacion IN ('C','K','Q')"
    if mrad in (1, 2):
        donde_c += " and t.es_gasto=1"
    donde_e = "WHERE c.id_empresa=:eid and substring(t.tipo,1,1)='E'"
    donde_c += _add_sucursal("c")
    donde_e += _add_sucursal("c")

    if mrad == 1:
        fechaf_c = ""
        if desde:
            params["desde_per"] = desde.replace("-", "")[:6]
            fechaf_c += " and concat(lpad(year(c.fecha_movimiento),4,'0'),lpad(month(c.fecha_movimiento),2,'0'))>=:desde_per"
        if hasta:
            params["hasta_per"] = hasta.replace("-", "")[:6]
            fechaf_c += " and concat(lpad(year(c.fecha_movimiento),4,'0'),lpad(month(c.fecha_movimiento),2,'0'))<=:hasta_per"
        fechaf_e = ""
        if desde:
            params["desde_per_e"] = desde.replace("-", "")[:6]
            fechaf_e += " and concat(lpad(year(c.fecha),4,'0'),lpad(month(c.fecha),2,'0'))>=:desde_per_e"
        if hasta:
            params["hasta_per_e"] = hasta.replace("-", "")[:6]
            fechaf_e += " and concat(lpad(year(c.fecha),4,'0'),lpad(month(c.fecha),2,'0'))<=:hasta_per_e"
        sel_c = "month(c.fecha_movimiento) AS mes,year(c.fecha_movimiento) AS ano,c.fecha_movimiento AS fecha,concat_ws(' ',a.descripcion_larga,a.codigo_accesorio) AS cuenta,sum(c.precio) AS importe,'Por Compras' AS tipo"
        sel_e = "month(c.fecha) AS mes,year(c.fecha) AS ano,c.fecha,k.nombre AS cuenta,sum(c.importe) AS importe,'Por Otros Egresos' AS tipo"
        group_c = " GROUP BY year(c.fecha_movimiento),month(c.fecha_movimiento),c.id_articulo"
        group_e = " GROUP BY year(c.fecha),month(c.fecha),c.id_cuenta_contable"
        order_c = " ORDER BY year(c.fecha_movimiento),month(c.fecha_movimiento),a.descripcion_larga"
        order_e = " ORDER BY year(c.fecha),month(c.fecha)"
    elif mrad == 2:
        fechaf_c = ""
        if desde:
            params["desde"] = desde.replace("-", "")
            fechaf_c += " and c.fecha_movimiento>=:desde"
        if hasta:
            params["hasta"] = hasta.replace("-", "")
            fechaf_c += " and c.fecha_movimiento<=:hasta"
        fechaf_e = ""
        if desde:
            params["desde_e"] = desde.replace("-", "")
            fechaf_e += " and c.fecha>=:desde_e"
        if hasta:
            params["hasta_e"] = hasta.replace("-", "")
            fechaf_e += " and c.fecha<=:hasta_e"
        sel_c = "month(c.fecha_movimiento) AS mes,year(c.fecha_movimiento) AS ano,c.fecha_movimiento AS fecha,concat_ws(' ',a.descripcion_larga,a.codigo_accesorio) AS cuenta,sum(c.precio) AS importe,'Por Compras' AS tipo"
        sel_e = "month(c.fecha) AS mes,year(c.fecha) AS ano,c.fecha,k.nombre AS cuenta,sum(c.importe) AS importe,'Por Otros Egresos' AS tipo"
        group_c = " GROUP BY c.fecha_movimiento,c.id_articulo"
        group_e = " GROUP BY c.fecha,c.id_cuenta_contable"
        order_c = " ORDER BY c.fecha_movimiento,a.descripcion_larga"
        order_e = " ORDER BY c.fecha"
    else:
        caso_fecha_c = "c.fecha_movimiento" if mrad == 3 else "DATE(c.registracion)"
        fechaf_c = ""
        if desde:
            params["desde"] = desde.replace("-", "")
            fechaf_c += f" and {caso_fecha_c}>=:desde"
        if hasta:
            params["hasta"] = hasta.replace("-", "")
            fechaf_c += f" and {caso_fecha_c}<=:hasta"
        fechaf_e = ""
        if desde:
            params["desde_e"] = desde.replace("-", "")
            fechaf_e += " and c.fecha>=:desde_e"
        if hasta:
            params["hasta_e"] = hasta.replace("-", "")
            fechaf_e += " and c.fecha<=:hasta_e"
        sel_c = f"month({caso_fecha_c}) AS mes,year({caso_fecha_c}) AS ano,{caso_fecha_c} AS fecha,concat_ws(' ',a.descripcion_larga,a.codigo_accesorio) AS cuenta,c.precio AS importe,'Por Compras' AS tipo"
        sel_e = "month(c.fecha) AS mes,year(c.fecha) AS ano,c.fecha,k.nombre AS cuenta,c.importe AS importe,'Por Otros Egresos' AS tipo"
        group_c = ""
        group_e = ""
        order_c = f" ORDER BY {caso_fecha_c}"
        order_e = " ORDER BY c.fecha"

    q_compras = text(f"""
        SELECT {sel_c}
        FROM {t_cuerpo} AS c
        LEFT JOIN articulos AS a ON a.id=c.id_articulo
        LEFT JOIN parametros_tipos_articulos AS t ON t.id=a.id_tipo
        {donde_c} {fechaf_c}
        {group_c}
        {order_c}
    """)
    q_egresos = text(f"""
        SELECT {sel_e}
        FROM {t_ingresos} AS c
        LEFT JOIN tipos_movimientos AS t ON t.id=c.id_tipo_movimiento
        LEFT JOIN plan_de_cuentas AS k ON k.id=c.id_cuenta_contable
        {donde_e} {fechaf_e}
        {group_e}
        {order_e}
    """)

    try:
        compras = _rows_to_dicts(db.execute(q_compras, params))
        egresos = _rows_to_dicts(db.execute(q_egresos, params))
        detalle = compras + egresos
        detalle.sort(key=lambda r: (int(r["mes"] or 0), int(r["ano"] or 0)))
        result = {
            "titulo": "Gastos",
            "mrad": mrad,
            "totalGastos": sum(float(d["importe"] or 0) for d in detalle),
            "detalle": detalle
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Gastos Detalle")


# QUES=14 del programa original - Ventas por Vendedores. mRAD: 1=periodo

@router.get("/ventas/vendedores")
def ventas_vendedores(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    mrad: int = Query(1, description="1=periodo, 2=agrupado por fecha, 3=detalle por fecha, 4=detalle por registracion"),
    rubro: Optional[str] = Query(None, description="Si se provee, desagrega por rubro del articulo"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("ventas_vendedores", eid, desde, hasta, mrad, rubro, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_cuerpo = "comprobantes_cuerpo" if estado == 0 else "_comprobantes_cuerpo"
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"

    def _fechaf_periodo(alias):
        ff = ""
        if desde:
            params["desde_per"] = desde.replace("-", "")[:6]
            ff += f" and CONCAT(LPAD({alias}.ano_imputacion,4,'0'), LPAD({alias}.mes_imputacion,2,'0')) >= :desde_per"
        if hasta:
            params["hasta_per"] = hasta.replace("-", "")[:6]
            ff += f" and CONCAT(LPAD({alias}.ano_imputacion,4,'0'), LPAD({alias}.mes_imputacion,2,'0')) <= :hasta_per"
        return ff

    def _fechaf_fecha(alias_expr=None):
        col = alias_expr or "v.fecha"
        ff = ""
        if desde:
            params["desde"] = desde.replace("-", "")
            ff += f" and {col} >= :desde"
        if hasta:
            params["hasta"] = hasta.replace("-", "")
            ff += f" and {col} <= :hasta"
        return ff

    if rubro:
        where = "WHERE v.id_empresa = :eid AND v.anulado = 0"
        if rubro:
            where += " AND r.nombre LIKE :rubro"
            params["rubro"] = f"%{rubro}%"

        select_rub = "r.nombre AS rubro"
        joins = f"""
            FROM {t_cuerpo} AS c
            LEFT JOIN {t_ventas} AS v ON v.id = c.id_comprobante
            LEFT JOIN tipos_comprobantes AS t ON t.id = v.id_comprobante
            LEFT JOIN vendedores AS p ON p.id = v.id_vendedor
            LEFT JOIN articulos AS a ON a.id = c.id_articulo
            LEFT JOIN rubros AS r ON r.id = a.id_rubro
            LEFT JOIN tipos_alicuotas_iva AS i ON i.id = c.id_alicuota_iva
        """
        aggs = ("ROUND(SUM(-c.cantidad * c.precio), 2) AS ng, "
                "ROUND(SUM(-c.cantidad * c.precio) * (i.porcentaje / 100), 2) AS iv, "
                "0 AS otros, "
                "ROUND(SUM(-c.cantidad * c.precio * (1 + i.porcentaje / 100)), 2) AS tot")

        if mrad == 1:
            cols = (f"v.mes_imputacion, v.ano_imputacion, MAX(v.fecha) AS fecha, "
                    f"MAX(p.nombre) AS vendedor, {select_rub}, {aggs}")
            group = " GROUP BY v.mes_imputacion, v.ano_imputacion, v.id_vendedor, a.id_rubro"
            order = " ORDER BY v.ano_imputacion, v.mes_imputacion"
            fechaf = _fechaf_periodo("v")
        elif mrad == 2:
            cols = (f"MAX(v.mes_imputacion) AS mes_imputacion, MAX(v.ano_imputacion) AS ano_imputacion, "
                    f"v.fecha, MAX(p.nombre) AS vendedor, {select_rub}, {aggs}")
            group = " GROUP BY v.fecha, v.id_vendedor, a.id_rubro"
            order = " ORDER BY v.fecha"
            fechaf = _fechaf_fecha("v.fecha")
        elif mrad == 3:
            cols = (f"MAX(v.mes_imputacion) AS mes_imputacion, MAX(v.ano_imputacion) AS ano_imputacion, "
                    f"MAX(v.fecha) AS fecha, MAX(p.nombre) AS vendedor, {select_rub}, {aggs}")
            group = " GROUP BY v.id_vendedor, a.id_rubro"
            order = " ORDER BY v.fecha"
            fechaf = _fechaf_fecha("v.fecha")
        else:
            cols = (f"MAX(v.mes_imputacion) AS mes_imputacion, MAX(v.ano_imputacion) AS ano_imputacion, "
                    f"MAX(DATE(v.registracion)) AS fecha, MAX(p.nombre) AS vendedor, {select_rub}, {aggs}")
            group = " GROUP BY v.id_vendedor, a.id_rubro"
            order = " ORDER BY DATE(v.registracion)"
            fechaf = _fechaf_fecha("DATE(v.registracion)")
    else:
        where = "WHERE v.id_empresa = :eid AND v.anulado = 0"
        select_rub = "'Todos los Rubros' AS rubro"
        joins = f"""
            FROM {t_ventas} AS v
            LEFT JOIN tipos_comprobantes AS t ON t.id = v.id_comprobante
            LEFT JOIN vendedores AS p ON p.id = v.id_vendedor
        """
        aggs = ("SUM(IF(t.tipo='+', v.neto_gravado, -v.neto_gravado)) AS ng, "
                "SUM(IF(t.tipo='+', v.iva, -v.iva)) AS iv, "
                "SUM(IF(t.tipo='+', (v.percepcion_iva + v.percepcion_i_brutos + v.exento + v.impuestos_internos + v.retencion_ganancias), "
                "-(v.percepcion_iva + v.percepcion_i_brutos + v.exento + v.impuestos_internos + v.retencion_ganancias))) AS otros, "
                "SUM(IF(t.tipo='+', v.total_comprobante, -v.total_comprobante)) AS tot")

        if mrad == 1:
            cols = (f"v.mes_imputacion, v.ano_imputacion, MAX(v.fecha) AS fecha, "
                    f"MAX(p.nombre) AS vendedor, {select_rub}, {aggs}")
            group = " GROUP BY v.mes_imputacion, v.ano_imputacion, v.id_vendedor"
            order = " ORDER BY v.ano_imputacion, v.mes_imputacion"
            fechaf = _fechaf_periodo("v")
        elif mrad == 2:
            cols = (f"MAX(v.mes_imputacion) AS mes_imputacion, MAX(v.ano_imputacion) AS ano_imputacion, "
                    f"v.fecha, MAX(p.nombre) AS vendedor, {select_rub}, {aggs}")
            group = " GROUP BY v.fecha, v.id_vendedor"
            order = " ORDER BY v.fecha"
            fechaf = _fechaf_fecha("v.fecha")
        elif mrad == 3:
            cols = (f"MAX(v.mes_imputacion) AS mes_imputacion, MAX(v.ano_imputacion) AS ano_imputacion, "
                    f"MAX(v.fecha) AS fecha, MAX(p.nombre) AS vendedor, {select_rub}, {aggs}")
            group = " GROUP BY v.id_vendedor"
            order = " ORDER BY v.fecha"
            fechaf = _fechaf_fecha("v.fecha")
        else:
            cols = (f"MAX(v.mes_imputacion) AS mes_imputacion, MAX(v.ano_imputacion) AS ano_imputacion, "
                    f"MAX(DATE(v.registracion)) AS fecha, MAX(p.nombre) AS vendedor, {select_rub}, {aggs}")
            group = " GROUP BY v.id_vendedor"
            order = " ORDER BY DATE(v.registracion)"
            fechaf = _fechaf_fecha("DATE(v.registracion)")

    q = text(f"""
        SELECT {cols}
        {joins}
        {where} {fechaf}
        {group}
        {order}
    """)

    try:
        det = _rows_to_dicts(db.execute(q, params))
        result = {
            "titulo": "Ventas por Vendedores",
            "rubro": rubro if rubro else "Todos los Rubros",
            "detalle": det
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Ventas por Vendedores")


def _fila_total_ventas(tot):
    return {
        "vend": "Total Venta" if tot is not None else None,
        "rub": None,
        "codigo_de_barras": None,
        "nom": None,
        "uni": None,
        "cant": None,
        "precio": None,
        "bonificacion": None,
        "tot": tot,
        "id_vendedor": 0,
        "id_rubro": 0,
        "filaSubtotal": True
    }


# QUES=15 del programa original - Ventas por Vendedores por Rubros y Artículos.

@router.get("/ventas/vendedores-rubros")
def ventas_vendedores_rubros(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    mrad: int = Query(1, description="1=periodo, 2=entre fechas, 3=detalle, 4=registracion"),
    segundo: int = Query(1, description="1=agrupado por articulo, 2=desagregado"),
    vendedor: Optional[str] = Query(None, description="Filtro por nombre de vendedor"),
    estado: int = Query(0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("ventas_vendedores_rubros", eid, desde, hasta, mrad, segundo, vendedor, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_cuerpo = "comprobantes_cuerpo" if estado == 0 else "_comprobantes_cuerpo"
    t_ventas = "comprobantes_ventas" if estado == 0 else "_comprobantes_ventas"
    where = "WHERE v.id_empresa=:eid and v.anulado=0 and c.id_empresa=:eid"

    if vendedor:
        where += " and p.nombre LIKE :vendedor"
        params["vendedor"] = f"%{vendedor}%"

    if mrad == 1:
        fechaf = ""
        if desde:
            params["desde_per"] = desde.replace("-", "")[:6]
            fechaf += " and concat(lpad(v.ano_imputacion,4,'0'),lpad(v.mes_imputacion,2,'0'))>=:desde_per"
        if hasta:
            params["hasta_per"] = hasta.replace("-", "")[:6]
            fechaf += " and concat(lpad(v.ano_imputacion,4,'0'),lpad(v.mes_imputacion,2,'0'))<=:hasta_per"
    elif mrad == 4:
        col_f = "DATE(v.registracion)"
        fechaf = ""
        if desde:
            params["desde"] = desde.replace("-", "")
            fechaf += f" and {col_f}>=:desde"
        if hasta:
            params["hasta"] = hasta.replace("-", "")
            fechaf += f" and {col_f}<=:hasta"
    else:
        col_f = "v.fecha"
        fechaf = ""
        if desde:
            params["desde"] = desde.replace("-", "")
            fechaf += f" and {col_f}>=:desde"
        if hasta:
            params["hasta"] = hasta.replace("-", "")
            fechaf += f" and {col_f}<=:hasta"

    agrupado = (segundo == 1)

    def av(expr):
        return f"MAX({expr})" if agrupado else expr

    if agrupado:
        caso_cant = "sum(-c.cantidad) AS cant"
        caso_tot = "sum(round(-c.cantidad*c.precio,2)) AS tot"
        group = " GROUP BY c.id_articulo,c.id_unidad_medida"
    else:
        caso_cant = "-c.cantidad AS cant"
        caso_tot = "round(-c.cantidad*c.precio,2) AS tot"
        group = ""

    q = text(f"""
        SELECT
            p.nombre AS vend,
            r.nombre AS rub,
            {av("a.codigo_de_barras")} AS codigo_de_barras,
            {av("concat_ws(' ',a.descripcion_larga,a.codigo_accesorio)")} AS nom,
            {av("substring(u.nombre,1,3)")} AS uni,
            {caso_cant},
            {av("c.precio")} AS precio,
            {av("c.bonificacion")} AS bonificacion,
            {caso_tot},
            {av("v.id_vendedor")} AS id_vendedor,
            {av("r.id")} AS id_rubro
        FROM {t_cuerpo} AS c
        LEFT JOIN {t_ventas} AS v ON v.id=c.id_comprobante
        LEFT JOIN vendedores AS p ON p.id=v.id_vendedor
        LEFT JOIN articulos AS a ON a.id=c.id_articulo
        LEFT JOIN rubros AS r ON r.id=a.id_rubro
        LEFT JOIN unidades AS u ON u.id=c.id_unidad_medida
        {where} {fechaf}
        {group}
        ORDER BY p.nombre,r.nombre,a.descripcion_larga
    """)

    try:
        det = _rows_to_dicts(db.execute(q, params))
        cantidad_total = sum(float(d["cant"] or 0) for d in det)
        monto_total = sum(float(d["tot"] or 0) for d in det)
        if det:
            acumulado = []
            vendedor = 0
            rubro = 0
            svnd = 0.0
            for fila in det:
                if vendedor != fila.get("id_vendedor") or rubro != fila.get("id_rubro"):
                    if vendedor != 0 and rubro != 0:
                        acumulado.append(_fila_total_ventas(svnd))
                        acumulado.append(_fila_total_ventas(None))
                    vendedor = fila.get("id_vendedor")
                    rubro = fila.get("id_rubro")
                    svnd = 0.0
                acumulado.append(fila)
                svnd = round(svnd + float(fila.get("tot") or 0), 2)
            acumulado.append(_fila_total_ventas(svnd))
            det = acumulado
        result = {
            "titulo": "Ventas por Vendedores por Rubros y Artículos",
            "segundo": segundo,
            "cantidadTotal": cantidad_total,
            "montoTotal": monto_total,
            "detalle": det
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Ventas por Vendedores Rubros")


# QUES=16 del programa original - Resultado de Ventas (Venta - Costo /

@router.get("/resultados/ventas")
def resultados_ventas(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    mrad: int = Query(1, description="1=periodo, 2=entre fechas, 3=detalle, 4=registracion"),
    segundo: int = Query(1, description="1=agrupado Venta-Costo, 2=desagregado Venta-Costo, 3=agrupado Venta-P.UltimaCompra, 4=desagregado Venta-P.UltimaCompra"),
    estado: int = Query(0, description="0=usa precio_ultima_compra, >0=usa precio_ultima_compra_"),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    cache_key = ("resultados_ventas", eid, desde, hasta, mrad, segundo, estado)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    params = {"eid": eid}
    t_cuerpo = "comprobantes_cuerpo" if estado == 0 else "_comprobantes_cuerpo"
    where = "WHERE c.id_empresa=:eid and c.identificacion='V'"

    agrupado = (segundo == 1 or segundo == 3)
    if segundo == 1 or segundo == 2:
        c_campo_precio = "a.precio_costo"
    else:
        c_campo_precio = "a.precio_ultima_compra" if estado == 0 else "a.precio_ultima_compra_"

    def av(expr):
        return f"MAX({expr})" if agrupado else expr

    caso_fecha = "c.fecha_movimiento"

    if mrad == 1:
        fechaf = ""
        if desde:
            params["desde_per"] = desde.replace("-", "")[:6]
            fechaf += " and concat(lpad(year(c.fecha_movimiento),4,'0'),lpad(month(c.fecha_movimiento),2,'0'))>=:desde_per"
        if hasta:
            params["hasta_per"] = hasta.replace("-", "")[:6]
            fechaf += " and concat(lpad(year(c.fecha_movimiento),4,'0'),lpad(month(c.fecha_movimiento),2,'0'))<=:hasta_per"
        order = " ORDER BY nom"
    elif mrad == 4:
        col_f = "DATE(c.registracion)"
        fechaf = ""
        if desde:
            params["desde"] = desde.replace("-", "")
            fechaf += f" and {col_f}>=:desde"
        if hasta:
            params["hasta"] = hasta.replace("-", "")
            fechaf += f" and {col_f}<=:hasta"
        order = f" ORDER BY {col_f},nom"
    else:
        fechaf = ""
        if desde:
            params["desde"] = desde.replace("-", "")
            fechaf += f" and {caso_fecha}>=:desde"
        if hasta:
            params["hasta"] = hasta.replace("-", "")
            fechaf += f" and {caso_fecha}<=:hasta"
        order = f" ORDER BY {caso_fecha},nom" if mrad == 3 else " ORDER BY nom"

    if agrupado:
        caso_cant = "sum(-c.cantidad) AS cant"
        caso_tot1 = "sum(-c.cantidad*c.precio) AS tot1"
        caso_tot2 = f"sum(-c.cantidad*c.precio)-sum(-c.cantidad*({c_campo_precio}*COALESCE(t.valor_en_pesos,1))) AS tot2"
        group = " GROUP BY c.id_articulo,c.id_unidad_medida"
    else:
        caso_cant = "-c.cantidad AS cant"
        caso_tot1 = "(-c.cantidad*c.precio) AS tot1"
        caso_tot2 = f"(-c.cantidad*c.precio)-(-c.cantidad*({c_campo_precio}*COALESCE(t.valor_en_pesos,1))) AS tot2"
        group = ""

    q = text(f"""
        SELECT
            {av(caso_fecha)} AS fecha,
            {caso_cant},
            {av("a.codigo_de_barras")} AS codigo_de_barras,
            {av("concat_ws(' ',a.descripcion_larga,a.codigo_accesorio)")} AS nom,
            {av(f"({c_campo_precio}*COALESCE(t.valor_en_pesos,1))")} AS prc,
            {av("c.precio")} AS precio,
            {caso_tot1},
            {caso_tot2}
        FROM {t_cuerpo} AS c
        LEFT JOIN articulos AS a ON a.id=c.id_articulo
        LEFT JOIN tipos_moneda AS t ON t.id=a.id_moneda
        {where} {fechaf}
        {group}
        {order}
    """)

    try:
        det = _rows_to_dicts(db.execute(q, params))
        result = {
            "titulo": "Resultado de Ventas = Venta - Costo" if segundo in (1, 2) else "Resultado de Ventas = Venta - P.Última Compra",
            "segundo": segundo,
            "estado": estado,
            "cantidadTotal": sum(float(d["cant"] or 0) for d in det),
            "ventaTotal": sum(float(d["tot1"] or 0) for d in det),
            "resultadoTotal": sum(float(d["tot2"] or 0) for d in det),
            "detalle": det
        }
        _cache_set(cache_key, result)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Error en Resultados de Ventas")
