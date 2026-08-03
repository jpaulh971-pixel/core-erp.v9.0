from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.m02_productos.models import Producto


def listar(db: Session, solo_activos: bool = True) -> list[Producto]:
    q = db.query(Producto)
    if solo_activos:
        q = q.filter(Producto.activo.is_(True))
    return q.order_by(Producto.codigo).all()


def obtener_por_id(db: Session, producto_id: int) -> Optional[Producto]:
    return db.query(Producto).filter(Producto.id == producto_id).first()


def obtener_por_codigo(db: Session, codigo: str) -> Optional[Producto]:
    return db.query(Producto).filter(Producto.codigo == codigo).first()


def obtener_por_nombre(db: Session, nombre: str) -> Optional[Producto]:
    """Busca por nombre exacto, sin distinguir mayusculas/minusculas. Usado
    por la importacion de compras (m04_compras/importacion_service.py)
    cuando la columna 'Producto' del Excel trae el nombre en vez del
    codigo interno."""
    return db.query(Producto).filter(func.lower(Producto.nombre) == nombre.strip().lower()).first()


def crear(db: Session, producto: Producto) -> Producto:
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


def actualizar(db: Session, producto: Producto, cambios: dict) -> Producto:
    for campo, valor in cambios.items():
        setattr(producto, campo, valor)
    db.commit()
    db.refresh(producto)
    return producto
