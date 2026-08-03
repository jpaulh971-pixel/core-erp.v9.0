from sqlalchemy.orm import Session

from app.modules.m11_clientes import repository, schemas, validators
from app.modules.m11_clientes.models import Cliente


def listar_clientes(db: Session, solo_activos: bool = True) -> list[Cliente]:
    return repository.listar(db, solo_activos)


def obtener_cliente(db: Session, cliente_id: int) -> Cliente:
    cliente = repository.obtener_por_id(db, cliente_id)
    return validators.validar_cliente_existe(cliente)


def crear_cliente(db: Session, datos: schemas.ClienteCrear) -> Cliente:
    validators.validar_ruc_disponible(repository.obtener_por_ruc(db, datos.ruc))
    cliente = Cliente(**datos.model_dump())
    return repository.crear(db, cliente)


def actualizar_cliente(db: Session, cliente_id: int, datos: schemas.ClienteActualizar) -> Cliente:
    cliente = obtener_cliente(db, cliente_id)
    cambios = datos.model_dump(exclude_unset=True)
    return repository.actualizar(db, cliente, cambios)
