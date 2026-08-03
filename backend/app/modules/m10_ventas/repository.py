from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.modules.m10_ventas.models import OrdenVenta


def crear(db: Session, orden: OrdenVenta) -> OrdenVenta:
    db.add(orden)
    db.commit()
    db.refresh(orden)
    return orden


def obtener(db: Session, orden_id: int) -> Optional[OrdenVenta]:
    return (
        db.query(OrdenVenta)
        .options(joinedload(OrdenVenta.items), joinedload(OrdenVenta.cliente))
        .filter(OrdenVenta.id == orden_id)
        .first()
    )


def listar(db: Session, estado: Optional[str] = None) -> list[OrdenVenta]:
    q = db.query(OrdenVenta).options(
        joinedload(OrdenVenta.items), joinedload(OrdenVenta.cliente)
    )
    if estado:
        q = q.filter(OrdenVenta.estado == estado)
    return q.order_by(OrdenVenta.creado_en.desc()).all()


def guardar(db: Session, orden: OrdenVenta) -> OrdenVenta:
    db.add(orden)
    db.commit()
    db.refresh(orden)
    return orden


def existe_factura(db: Session, factura: str) -> bool:
    """Solo lectura. Usado por m10_ventas/importacion_service.py para
    detectar Factura duplicada antes de escribir nada."""
    return db.query(OrdenVenta).filter(OrdenVenta.factura == factura).first() is not None


def existe_guia_remision(db: Session, guia_remision: str) -> bool:
    """Solo lectura. Usado por m10_ventas/importacion_service.py para
    detectar Guia de Remision duplicada antes de escribir nada."""
    return (
        db.query(OrdenVenta)
        .filter(OrdenVenta.guia_remision == guia_remision)
        .first()
        is not None
    )
