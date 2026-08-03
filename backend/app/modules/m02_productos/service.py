from sqlalchemy.orm import Session

from app.modules.m02_productos import repository, schemas, validators
from app.modules.m02_productos.models import Producto


def listar_productos(db: Session, solo_activos: bool = True) -> list[Producto]:
    return repository.listar(db, solo_activos)


def obtener_producto(db: Session, producto_id: int) -> Producto:
    producto = repository.obtener_por_id(db, producto_id)
    return validators.validar_producto_existe(producto)


def crear_producto(db: Session, datos: schemas.ProductoCrear) -> Producto:
    validators.validar_codigo_disponible(repository.obtener_por_codigo(db, datos.codigo))
    producto = Producto(**datos.model_dump())
    return repository.crear(db, producto)


def actualizar_producto(db: Session, producto_id: int, datos: schemas.ProductoActualizar) -> Producto:
    producto = obtener_producto(db, producto_id)
    cambios = {k: v for k, v in datos.model_dump(exclude_unset=True).items()}
    return repository.actualizar(db, producto, cambios)
