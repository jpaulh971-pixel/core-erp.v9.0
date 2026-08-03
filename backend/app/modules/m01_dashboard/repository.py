"""Capa de acceso a datos (queries SQLAlchemy) del modulo m01_dashboard.

Solo lectura: son queries de agregacion sobre tablas de otros modulos ya
implementados (Inventario, Ventas, Costos), sin escribir ni recalcular
ninguna regla de negocio ya resuelta en esos modulos. Es el mismo criterio
que ya usa Costos al leer directo el kardex de Inventario.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.m03_inventario.models import Lote
from app.modules.m04_compras.models import OrdenCompra, OrdenCompraItem
from app.modules.m08_costos.models import CostoAdicional
from app.modules.m10_ventas.models import OrdenVenta, OrdenVentaItem


def valor_total_inventario(db: Session) -> float:
    """Suma cantidad_actual * costo_unitario de todos los lotes (valorizacion
    de inventario al costo de ingreso de cada lote)."""
    total = (
        db.query(func.coalesce(func.sum(Lote.cantidad_actual * Lote.costo_unitario), 0))
        .scalar()
    )
    return float(total or 0)


def ordenes_venta_por_estado(db: Session) -> dict[str, int]:
    filas = (
        db.query(OrdenVenta.estado, func.count(OrdenVenta.id))
        .group_by(OrdenVenta.estado)
        .all()
    )
    return {estado: cantidad for estado, cantidad in filas}


def total_vendido_despachadas(db: Session) -> float:
    """Total vendido (cantidad * precio_unitario_venta) de items cuya orden
    ya fue DESPACHADA -- venta efectivamente concretada, mercaderia ya
    entregada. No mezcla monedas distintas de forma implicita: es la suma
    en las monedas originales tal como se registraron (mismo criterio que
    Costos/Compras/Comercio Exterior, que no convierten de forma automatica)."""
    total = (
        db.query(func.coalesce(func.sum(OrdenVentaItem.cantidad * OrdenVentaItem.precio_unitario_venta), 0))
        .join(OrdenVenta, OrdenVenta.id == OrdenVentaItem.orden_venta_id)
        .filter(OrdenVenta.estado == "DESPACHADA")
        .scalar()
    )
    return float(total or 0)


def total_comprado_recibidas(db: Session) -> float:
    """Total comprado (cantidad * costo_unitario) de items cuya orden de
    compra ya fue RECIBIDA -- compra efectivamente concretada, mercaderia
    ya ingresada a inventario. Mismo criterio que total_vendido_despachadas:
    no mezcla monedas, suma en las monedas originales tal como se
    registraron."""
    total = (
        db.query(func.coalesce(func.sum(OrdenCompraItem.cantidad * OrdenCompraItem.costo_unitario), 0))
        .join(OrdenCompra, OrdenCompra.id == OrdenCompraItem.orden_compra_id)
        .filter(OrdenCompra.estado == "RECIBIDA")
        .scalar()
    )
    return float(total or 0)


def costos_adicionales_por_tipo(db: Session) -> dict[str, float]:
    filas = (
        db.query(CostoAdicional.tipo_costo, func.coalesce(func.sum(CostoAdicional.monto), 0))
        .group_by(CostoAdicional.tipo_costo)
        .all()
    )
    return {tipo: float(monto) for tipo, monto in filas}


def total_costos_adicionales(db: Session) -> float:
    total = db.query(func.coalesce(func.sum(CostoAdicional.monto), 0)).scalar()
    return float(total or 0)
