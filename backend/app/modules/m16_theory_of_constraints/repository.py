"""Capa de acceso a datos (queries SQLAlchemy) del modulo
m16_theory_of_constraints.

Solo lectura: queries de agregacion sobre Ventas, Inventario (kardex) y
Costos ya persistidos por esos modulos. No escribe ni redefine ninguna
regla de negocio de ellos -- mismo criterio que ya usan m01_dashboard,
m13_inteligencia_comercial, m14_inteligencia_tributaria y
m15_lean_six_sigma.
"""
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.modules.m03_inventario.models import MovimientoKardex
from app.modules.m08_costos.models import CostoAdicional
from app.modules.m10_ventas.models import OrdenVenta, OrdenVentaItem


def demanda_confirmada_por_producto(db: Session) -> dict[int, float]:
    """Cantidad pendiente de despachar por producto: suma de items de
    ordenes de venta ya CONFIRMADA (demanda real, aun no satisfecha)."""
    filas = (
        db.query(
            OrdenVentaItem.producto_id,
            func.sum(OrdenVentaItem.cantidad).label("cantidad_pendiente"),
        )
        .join(OrdenVenta, OrdenVenta.id == OrdenVentaItem.orden_venta_id)
        .filter(OrdenVenta.estado == "CONFIRMADA")
        .group_by(OrdenVentaItem.producto_id)
        .all()
    )
    return {f.producto_id: float(f.cantidad_pendiente or 0) for f in filas}


def ordenes_confirmadas_en_espera(db: Session) -> list[OrdenVenta]:
    """Ordenes CONFIRMADA que todavia no se pudieron despachar -- la cola
    de trabajo frente a la restriccion. Mas antiguas primero."""
    return (
        db.query(OrdenVenta)
        .options(joinedload(OrdenVenta.items), joinedload(OrdenVenta.cliente))
        .filter(OrdenVenta.estado == "CONFIRMADA")
        .order_by(OrdenVenta.confirmado_en.asc())
        .all()
    )


def _filtrar_periodo(q, columna, desde: date | None, hasta: date | None):
    if desde is not None:
        q = q.filter(columna >= desde)
    if hasta is not None:
        q = q.filter(columna <= hasta)
    return q


def ingreso_ventas_despachadas(db: Session, desde: date | None, hasta: date | None) -> float:
    q = (
        db.query(
            func.coalesce(
                func.sum(OrdenVentaItem.cantidad * OrdenVentaItem.precio_unitario_venta), 0
            )
        )
        .join(OrdenVenta, OrdenVenta.id == OrdenVentaItem.orden_venta_id)
        .filter(OrdenVenta.estado == "DESPACHADA")
    )
    q = _filtrar_periodo(q, OrdenVenta.despachado_en, desde, hasta)
    return float(q.scalar() or 0)


def costo_mercaderia_vendida(db: Session, desde: date | None, hasta: date | None) -> float:
    """Costo real (leido del kardex, no recalculado) de la mercaderia
    consumida en despachos de venta -- mismo criterio de 'no duplicar
    costos' que ya aplica el modulo 08."""
    q = db.query(
        func.coalesce(func.sum(MovimientoKardex.cantidad * MovimientoKardex.costo_unitario), 0)
    ).filter(
        MovimientoKardex.tipo_movimiento == "SALIDA",
        MovimientoKardex.referencia.like("Despacho orden de venta%"),
    )
    q = _filtrar_periodo(q, MovimientoKardex.creado_en, desde, hasta)
    return float(q.scalar() or 0)


def total_operating_expense(db: Session, desde: date | None, hasta: date | None) -> float:
    q = db.query(func.coalesce(func.sum(CostoAdicional.monto), 0))
    q = _filtrar_periodo(q, CostoAdicional.creado_en, desde, hasta)
    return float(q.scalar() or 0)
