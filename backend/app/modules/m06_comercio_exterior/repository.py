from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.modules.m06_comercio_exterior.models import DeclaracionExportacion


def crear(db: Session, declaracion: DeclaracionExportacion) -> DeclaracionExportacion:
    db.add(declaracion)
    db.commit()
    db.refresh(declaracion)
    return declaracion


def obtener(db: Session, declaracion_id: int) -> Optional[DeclaracionExportacion]:
    return (
        db.query(DeclaracionExportacion)
        .options(joinedload(DeclaracionExportacion.items))
        .filter(DeclaracionExportacion.id == declaracion_id)
        .first()
    )


def listar(db: Session, estado: Optional[str] = None) -> list[DeclaracionExportacion]:
    q = db.query(DeclaracionExportacion).options(joinedload(DeclaracionExportacion.items))
    if estado:
        q = q.filter(DeclaracionExportacion.estado == estado)
    return q.order_by(DeclaracionExportacion.creado_en.desc()).all()


def guardar(db: Session, declaracion: DeclaracionExportacion) -> DeclaracionExportacion:
    db.add(declaracion)
    db.commit()
    db.refresh(declaracion)
    return declaracion
