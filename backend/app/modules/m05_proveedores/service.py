from sqlalchemy.orm import Session

from app.modules.m05_proveedores import repository, schemas, validators
from app.modules.m05_proveedores.models import Proveedor


def listar_proveedores(db: Session, solo_activos: bool = True) -> list[Proveedor]:
    return repository.listar(db, solo_activos)


def obtener_proveedor(db: Session, proveedor_id: int) -> Proveedor:
    proveedor = repository.obtener_por_id(db, proveedor_id)
    return validators.validar_proveedor_existe(proveedor)


def crear_proveedor(db: Session, datos: schemas.ProveedorCrear) -> Proveedor:
    validators.validar_ruc_disponible(repository.obtener_por_ruc(db, datos.ruc))
    proveedor = Proveedor(**datos.model_dump())
    return repository.crear(db, proveedor)


def actualizar_proveedor(db: Session, proveedor_id: int, datos: schemas.ProveedorActualizar) -> Proveedor:
    proveedor = obtener_proveedor(db, proveedor_id)
    cambios = datos.model_dump(exclude_unset=True)
    return repository.actualizar(db, proveedor, cambios)
