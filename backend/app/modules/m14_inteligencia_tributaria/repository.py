"""Capa de acceso a datos (queries SQLAlchemy) del modulo
m14_inteligencia_tributaria.

Solo lectura: queries de agregacion sobre los comprobantes electronicos
ya persistidos por SUNAT (modulo 12). No redefine ninguna regla de esa
emision (serie/correlativo, IGV, transiciones de estado); solo reporta.
"""
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.m12_sunat.models import ComprobanteElectronico

ESTADOS_VALIDOS_PARA_IGV = ("EMITIDO", "ACEPTADO")


def _filtrar_periodo(q, desde: date | None, hasta: date | None):
    if desde is not None:
        q = q.filter(ComprobanteElectronico.emitido_en >= desde)
    if hasta is not None:
        q = q.filter(ComprobanteElectronico.emitido_en <= hasta)
    return q


def resumen_por_tipo_comprobante(
    db: Session, desde: date | None, hasta: date | None
) -> list[dict]:
    """Agrega subtotal/IGV/total por tipo de comprobante, solo de los que
    siguen vigentes para efectos tributarios (EMITIDO o ACEPTADO; un
    ANULADO no genera obligacion de IGV)."""
    q = db.query(
        ComprobanteElectronico.tipo_comprobante,
        func.count(ComprobanteElectronico.id).label("cantidad"),
        func.coalesce(func.sum(ComprobanteElectronico.subtotal), 0).label("subtotal"),
        func.coalesce(func.sum(ComprobanteElectronico.igv), 0).label("igv"),
        func.coalesce(func.sum(ComprobanteElectronico.total), 0).label("total"),
    ).filter(ComprobanteElectronico.estado.in_(ESTADOS_VALIDOS_PARA_IGV))
    q = _filtrar_periodo(q, desde, hasta)
    filas = q.group_by(ComprobanteElectronico.tipo_comprobante).all()
    return [
        {
            "tipo_comprobante": f.tipo_comprobante,
            "cantidad": int(f.cantidad or 0),
            "subtotal": float(f.subtotal or 0),
            "igv": float(f.igv or 0),
            "total": float(f.total or 0),
        }
        for f in filas
    ]


def libro_ventas(
    db: Session, desde: date | None, hasta: date | None
) -> list[ComprobanteElectronico]:
    """Registro de ventas: todos los comprobantes del periodo (con su
    estado), ordenados por serie-correlativo -- igual criterio que exige
    SUNAT para el registro de ventas e ingresos."""
    q = db.query(ComprobanteElectronico)
    q = _filtrar_periodo(q, desde, hasta)
    return q.order_by(
        ComprobanteElectronico.serie, ComprobanteElectronico.correlativo
    ).all()


def comprobantes_anulados(
    db: Session, desde: date | None, hasta: date | None
) -> list[ComprobanteElectronico]:
    q = db.query(ComprobanteElectronico).filter(
        ComprobanteElectronico.estado == "ANULADO"
    )
    q = _filtrar_periodo(q, desde, hasta)
    return q.order_by(ComprobanteElectronico.anulado_en.desc()).all()
