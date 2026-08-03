from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.modules.m12_sunat.models import ComprobanteElectronico


def crear(db: Session, comprobante: ComprobanteElectronico) -> ComprobanteElectronico:
    db.add(comprobante)
    db.commit()
    db.refresh(comprobante)
    return comprobante


def obtener(db: Session, comprobante_id: int) -> Optional[ComprobanteElectronico]:
    return (
        db.query(ComprobanteElectronico)
        .filter(ComprobanteElectronico.id == comprobante_id)
        .first()
    )


def obtener_por_orden(db: Session, orden_venta_id: int) -> Optional[ComprobanteElectronico]:
    return (
        db.query(ComprobanteElectronico)
        .filter(ComprobanteElectronico.orden_venta_id == orden_venta_id)
        .first()
    )


def listar(db: Session, estado: Optional[str] = None) -> list[ComprobanteElectronico]:
    q = db.query(ComprobanteElectronico)
    if estado:
        q = q.filter(ComprobanteElectronico.estado == estado)
    return q.order_by(ComprobanteElectronico.emitido_en.desc()).all()


def ultimo_correlativo(db: Session, tipo_comprobante: str, serie: str) -> int:
    """Ultimo correlativo usado para ese tipo+serie (0 si no hay ninguno)."""
    comprobante = (
        db.query(ComprobanteElectronico)
        .filter(
            ComprobanteElectronico.tipo_comprobante == tipo_comprobante,
            ComprobanteElectronico.serie == serie,
        )
        .order_by(ComprobanteElectronico.correlativo.desc())
        .first()
    )
    return comprobante.correlativo if comprobante is not None else 0


def guardar(db: Session, comprobante: ComprobanteElectronico) -> ComprobanteElectronico:
    db.add(comprobante)
    db.commit()
    db.refresh(comprobante)
    return comprobante
