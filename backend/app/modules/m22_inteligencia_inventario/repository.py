"""Capa de acceso a datos (queries SQLAlchemy) del modulo
m22_inteligencia_inventario.

FASE 3 -- Solo lectura. Reutiliza directamente las tablas ya existentes
de m03_inventario (Lote, MovimientoKardex, ProductoInventario) y m02
(Producto). No crea ninguna tabla ni columna nueva: toda la
"inteligencia" es una agregacion/lectura sobre el Kardex y los Lotes que
el motor de m03_inventario ya viene grabando.
"""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.m03_inventario.models import Lote, MovimientoKardex, ProductoInventario


def movimientos_por_producto_en_periodo(
    db: Session, inventario_id: int, desde: datetime
) -> dict[int, dict[str, float]]:
    """Suma de cantidad de MovimientoKardex, agrupada por
    producto_inventario_id y tipo_movimiento, dentro de un inventario y
    desde una fecha dada (inclusive) hasta ahora. Es la unica consulta
    que alimenta consumo real, consumo promedio y rotacion -- todas
    lecturas puras sobre el Kardex ya existente, sin duplicar la
    consulta por cada calculo.

    Retorna: {producto_inventario_id: {"INGRESO": x, "SALIDA": y,
    "AJUSTE_POSITIVO": z, "AJUSTE_NEGATIVO": w}} (solo se incluyen los
    tipos que realmente tuvieron movimientos en el periodo).
    """
    filas = (
        db.query(
            MovimientoKardex.producto_inventario_id,
            MovimientoKardex.tipo_movimiento,
            func.coalesce(func.sum(MovimientoKardex.cantidad), 0).label("cantidad"),
        )
        .filter(
            MovimientoKardex.inventario_id == inventario_id,
            MovimientoKardex.creado_en >= desde,
        )
        .group_by(MovimientoKardex.producto_inventario_id, MovimientoKardex.tipo_movimiento)
        .all()
    )
    resultado: dict[int, dict[str, float]] = {}
    for pi_id, tipo, cantidad in filas:
        resultado.setdefault(pi_id, {})[tipo] = float(cantidad or 0)
    return resultado


def fecha_vencimiento_minima_por_producto(db: Session, inventario_id: int) -> dict[int, datetime]:
    """Fecha de vencimiento mas proxima entre los lotes CON STOCK
    (cantidad_actual > 0) de cada producto dentro de un inventario. Se
    incluyen intencionalmente los lotes ya vencidos (no se filtra por
    fecha): un lote vencido que sigue en stock (aun no dado de baja por
    ajuste) es precisamente la senal de mayor riesgo de merma que este
    modulo necesita detectar, no algo que deba ocultarse del calculo.
    Solo lectura sobre Lote/ProductoInventario, sin agregar columnas."""
    filas = (
        db.query(
            Lote.producto_inventario_id,
            func.min(Lote.fecha_vencimiento).label("fecha_vencimiento_min"),
        )
        .join(ProductoInventario, ProductoInventario.id == Lote.producto_inventario_id)
        .filter(
            ProductoInventario.inventario_id == inventario_id,
            Lote.cantidad_actual > 0,
            Lote.fecha_vencimiento.isnot(None),
        )
        .group_by(Lote.producto_inventario_id)
        .all()
    )
    return {pi_id: fecha for pi_id, fecha in filas}
