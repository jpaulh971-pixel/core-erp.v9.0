"""Capa de acceso a datos (queries SQLAlchemy) del modulo
m13_inteligencia_comercial.

Solo lectura: queries de agregacion sobre Ventas, Clientes y Productos ya
persistidos por esos modulos (mismo criterio que ya usa m01_dashboard y
m08_costos), sin escribir ni redefinir ninguna regla de negocio de ellos.
"""
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.m02_productos.models import Producto
from app.modules.m10_ventas.models import OrdenVenta, OrdenVentaItem
from app.modules.m11_clientes.models import Cliente


def _query_items_despachados(db: Session, desde: date | None, hasta: date | None):
    q = (
        db.query(OrdenVenta, OrdenVentaItem)
        .join(OrdenVentaItem, OrdenVentaItem.orden_venta_id == OrdenVenta.id)
        .filter(OrdenVenta.estado == "DESPACHADA")
    )
    if desde is not None:
        q = q.filter(OrdenVenta.despachado_en >= desde)
    if hasta is not None:
        q = q.filter(OrdenVenta.despachado_en <= hasta)
    return q


def productos_mas_vendidos(
    db: Session, limit: int, desde: date | None, hasta: date | None
) -> list[dict]:
    q = (
        db.query(
            Producto.id,
            Producto.codigo,
            Producto.nombre,
            func.sum(OrdenVentaItem.cantidad).label("cantidad_vendida"),
            func.sum(
                OrdenVentaItem.cantidad * OrdenVentaItem.precio_unitario_venta
            ).label("monto_vendido"),
        )
        .join(OrdenVentaItem, OrdenVentaItem.producto_id == Producto.id)
        .join(OrdenVenta, OrdenVenta.id == OrdenVentaItem.orden_venta_id)
        .filter(OrdenVenta.estado == "DESPACHADA")
    )
    if desde is not None:
        q = q.filter(OrdenVenta.despachado_en >= desde)
    if hasta is not None:
        q = q.filter(OrdenVenta.despachado_en <= hasta)

    filas = (
        q.group_by(Producto.id)
        .order_by(func.sum(OrdenVentaItem.cantidad).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "producto_id": f.id,
            "codigo": f.codigo,
            "nombre": f.nombre,
            "cantidad_vendida": float(f.cantidad_vendida or 0),
            "monto_vendido": float(f.monto_vendido or 0),
        }
        for f in filas
    ]


def clientes_top(
    db: Session, limit: int, desde: date | None, hasta: date | None
) -> list[dict]:
    q = (
        db.query(
            Cliente.id,
            Cliente.ruc,
            Cliente.razon_social,
            func.sum(
                OrdenVentaItem.cantidad * OrdenVentaItem.precio_unitario_venta
            ).label("monto_comprado"),
            func.count(func.distinct(OrdenVenta.id)).label("cantidad_ordenes"),
        )
        .join(OrdenVenta, OrdenVenta.cliente_id == Cliente.id)
        .join(OrdenVentaItem, OrdenVentaItem.orden_venta_id == OrdenVenta.id)
        .filter(OrdenVenta.estado == "DESPACHADA")
    )
    if desde is not None:
        q = q.filter(OrdenVenta.despachado_en >= desde)
    if hasta is not None:
        q = q.filter(OrdenVenta.despachado_en <= hasta)

    filas = (
        q.group_by(Cliente.id)
        .order_by(func.sum(OrdenVentaItem.cantidad * OrdenVentaItem.precio_unitario_venta).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "cliente_id": f.id,
            "ruc": f.ruc,
            "razon_social": f.razon_social,
            "monto_comprado": float(f.monto_comprado or 0),
            "cantidad_ordenes": int(f.cantidad_ordenes or 0),
        }
        for f in filas
    ]


def cantidad_vendida_por_producto(db: Session) -> dict[int, float]:
    """Cantidad total vendida (historica, ordenes DESPACHADA) por producto,
    usada para calcular el indice de rotacion de inventario."""
    filas = (
        db.query(
            OrdenVentaItem.producto_id,
            func.sum(OrdenVentaItem.cantidad).label("cantidad_vendida"),
        )
        .join(OrdenVenta, OrdenVenta.id == OrdenVentaItem.orden_venta_id)
        .filter(OrdenVenta.estado == "DESPACHADA")
        .group_by(OrdenVentaItem.producto_id)
        .all()
    )
    return {f.producto_id: float(f.cantidad_vendida or 0) for f in filas}
