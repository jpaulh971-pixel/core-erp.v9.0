from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.m05_proveedores.models import Proveedor


def listar(db: Session, solo_activos: bool = True) -> list[Proveedor]:
    q = db.query(Proveedor)
    if solo_activos:
        q = q.filter(Proveedor.activo.is_(True))
    return q.order_by(Proveedor.razon_social).all()


def obtener_por_id(db: Session, proveedor_id: int) -> Optional[Proveedor]:
    return db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()


def obtener_por_ruc(db: Session, ruc: str) -> Optional[Proveedor]:
    return db.query(Proveedor).filter(Proveedor.ruc == ruc).first()


def obtener_por_razon_social(db: Session, razon_social: str) -> Optional[Proveedor]:
    """Busca por razon social exacta, sin distinguir mayusculas/minusculas.
    Usado por la importacion de compras nacionalizadas
    (m04_compras/importacion_service.py) cuando la columna 'Proveedor' del
    Excel trae el nombre en vez del RUC/codigo interno."""
    return (
        db.query(Proveedor)
        .filter(func.lower(Proveedor.razon_social) == razon_social.strip().lower())
        .first()
    )


def crear(db: Session, proveedor: Proveedor) -> Proveedor:
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return proveedor


def actualizar(db: Session, proveedor: Proveedor, cambios: dict) -> Proveedor:
    for campo, valor in cambios.items():
        setattr(proveedor, campo, valor)
    db.commit()
    db.refresh(proveedor)
    return proveedor
