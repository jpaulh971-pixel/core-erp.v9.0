from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m11_clientes import schemas, service

router = APIRouter(prefix="/api/clientes", tags=["clientes"])


@router.get("", response_model=list[schemas.ClienteOut])
def listar(solo_activos: bool = True, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.listar_clientes(db, solo_activos)


@router.get("/{cliente_id}", response_model=schemas.ClienteOut)
def obtener(cliente_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.obtener_cliente(db, cliente_id)


@router.post("", response_model=schemas.ClienteOut, status_code=201)
def crear(datos: schemas.ClienteCrear, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.crear_cliente(db, datos)


@router.patch("/{cliente_id}", response_model=schemas.ClienteOut)
def actualizar(
    cliente_id: int,
    datos: schemas.ClienteActualizar,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.actualizar_cliente(db, cliente_id, datos)
