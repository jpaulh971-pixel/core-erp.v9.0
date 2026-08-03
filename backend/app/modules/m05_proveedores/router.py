from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m05_proveedores import schemas, service

router = APIRouter(prefix="/api/proveedores", tags=["proveedores"])


@router.get("", response_model=list[schemas.ProveedorOut])
def listar(solo_activos: bool = True, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.listar_proveedores(db, solo_activos)


@router.get("/{proveedor_id}", response_model=schemas.ProveedorOut)
def obtener(proveedor_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.obtener_proveedor(db, proveedor_id)


@router.post("", response_model=schemas.ProveedorOut, status_code=201)
def crear(datos: schemas.ProveedorCrear, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.crear_proveedor(db, datos)


@router.patch("/{proveedor_id}", response_model=schemas.ProveedorOut)
def actualizar(
    proveedor_id: int,
    datos: schemas.ProveedorActualizar,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.actualizar_proveedor(db, proveedor_id, datos)
