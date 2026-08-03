from typing import Optional

from sqlalchemy.orm import Session

from app.modules.m11_clientes.models import Cliente


def listar(db: Session, solo_activos: bool = True) -> list[Cliente]:
    q = db.query(Cliente)
    if solo_activos:
        q = q.filter(Cliente.activo.is_(True))
    return q.order_by(Cliente.razon_social).all()


def obtener_por_id(db: Session, cliente_id: int) -> Optional[Cliente]:
    return db.query(Cliente).filter(Cliente.id == cliente_id).first()


def obtener_por_ruc(db: Session, ruc: str) -> Optional[Cliente]:
    return db.query(Cliente).filter(Cliente.ruc == ruc).first()


def crear(db: Session, cliente: Cliente) -> Cliente:
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def actualizar(db: Session, cliente: Cliente, cambios: dict) -> Cliente:
    for campo, valor in cambios.items():
        setattr(cliente, campo, valor)
    db.commit()
    db.refresh(cliente)
    return cliente
