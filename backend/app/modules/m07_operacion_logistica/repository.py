"""Capa de acceso a datos (queries SQLAlchemy) del modulo m07_operacion_logistica."""
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.modules.m07_operacion_logistica.models import (
    HistorialOperacionLogistica,
    OperacionLogistica,
)


def crear(db: Session, operacion: OperacionLogistica) -> OperacionLogistica:
    db.add(operacion)
    db.commit()
    db.refresh(operacion)
    return operacion


def guardar(db: Session, operacion: OperacionLogistica) -> OperacionLogistica:
    db.add(operacion)
    db.commit()
    db.refresh(operacion)
    return operacion


def obtener(db: Session, operacion_id: int) -> Optional[OperacionLogistica]:
    return (
        db.query(OperacionLogistica)
        .options(joinedload(OperacionLogistica.historial))
        .filter(OperacionLogistica.id == operacion_id)
        .first()
    )


def listar(db: Session, estado: Optional[str] = None) -> list[OperacionLogistica]:
    q = db.query(OperacionLogistica)
    if estado is not None:
        q = q.filter(OperacionLogistica.estado == estado)
    return q.order_by(OperacionLogistica.id.desc()).all()


def registrar_historial(
    db: Session,
    operacion_id: int,
    usuario_id: int,
    estado_anterior: Optional[str],
    estado_nuevo: str,
    observaciones: Optional[str] = None,
) -> HistorialOperacionLogistica:
    entrada = HistorialOperacionLogistica(
        operacion_id=operacion_id,
        usuario_id=usuario_id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        observaciones=observaciones,
    )
    db.add(entrada)
    db.commit()
    db.refresh(entrada)
    return entrada
