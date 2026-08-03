from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m02_productos import schemas, service

router = APIRouter(prefix="/api/productos", tags=["productos"])


@router.get("", response_model=list[schemas.ProductoOut])
def listar(solo_activos: bool = True, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.listar_productos(db, solo_activos)


@router.get("/{producto_id}", response_model=schemas.ProductoOut)
def obtener(producto_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.obtener_producto(db, producto_id)


@router.post("", response_model=schemas.ProductoOut, status_code=201)
def crear(datos: schemas.ProductoCrear, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.crear_producto(db, datos)


@router.patch("/{producto_id}", response_model=schemas.ProductoOut)
def actualizar(
    producto_id: int,
    datos: schemas.ProductoActualizar,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.actualizar_producto(db, producto_id, datos)
