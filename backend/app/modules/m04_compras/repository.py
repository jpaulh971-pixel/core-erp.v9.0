from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.modules.m04_compras.models import OrdenCompra, OrdenCompraItem


def crear_orden(db: Session, orden: OrdenCompra) -> OrdenCompra:
    db.add(orden)
    db.commit()
    db.refresh(orden)
    return orden


def obtener_orden(db: Session, orden_id: int) -> Optional[OrdenCompra]:
    return (
        db.query(OrdenCompra)
        .options(joinedload(OrdenCompra.items))
        .filter(OrdenCompra.id == orden_id)
        .first()
    )


def listar_ordenes(db: Session, estado: Optional[str] = None) -> list[OrdenCompra]:
    q = db.query(OrdenCompra).options(joinedload(OrdenCompra.items))
    if estado:
        q = q.filter(OrdenCompra.estado == estado)
    return q.order_by(OrdenCompra.creado_en.desc()).all()


def guardar(db: Session, orden: OrdenCompra) -> OrdenCompra:
    db.add(orden)
    db.commit()
    db.refresh(orden)
    return orden
