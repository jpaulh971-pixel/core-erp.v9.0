from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.modules.m03_inventario.models import MovimientoKardex
from app.modules.m17_guias_remision.models import GuiaRemision


def crear_guia(db: Session, guia: GuiaRemision) -> GuiaRemision:
    db.add(guia)
    db.commit()
    db.refresh(guia)
    return guia


def obtener_guia(db: Session, guia_id: int) -> Optional[GuiaRemision]:
    return (
        db.query(GuiaRemision)
        .options(joinedload(GuiaRemision.detalles), joinedload(GuiaRemision.cliente))
        .filter(GuiaRemision.id == guia_id)
        .first()
    )


def obtener_guia_por_orden_venta(db: Session, orden_venta_id: int) -> Optional[GuiaRemision]:
    return (
        db.query(GuiaRemision)
        .filter(GuiaRemision.orden_venta_id == orden_venta_id)
        .first()
    )


def listar_guias(db: Session, estado: Optional[str] = None) -> list[GuiaRemision]:
    q = db.query(GuiaRemision).options(
        joinedload(GuiaRemision.detalles), joinedload(GuiaRemision.cliente)
    )
    if estado:
        q = q.filter(GuiaRemision.estado == estado)
    return q.order_by(GuiaRemision.creado_en.desc()).all()


def contar_guias(db: Session) -> int:
    return db.query(GuiaRemision).count()


def movimientos_salida_por_referencia(
    db: Session, producto_inventario_id: int, referencia: str
) -> list[MovimientoKardex]:
    """Lectura pura del Kardex ya existente: NO crea ni modifica nada.
    Devuelve los movimientos de SALIDA de un producto_inventario que
    quedaron marcados con la referencia de un despacho puntual."""
    return (
        db.query(MovimientoKardex)
        .filter(
            MovimientoKardex.producto_inventario_id == producto_inventario_id,
            MovimientoKardex.tipo_movimiento == "SALIDA",
            MovimientoKardex.referencia == referencia,
        )
        .order_by(MovimientoKardex.creado_en.asc())
        .all()
    )
