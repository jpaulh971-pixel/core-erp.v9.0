from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m17_guias_remision import schemas, service

router = APIRouter(prefix="/api/guias-remision", tags=["guias-remision"])


@router.post("", response_model=schemas.GuiaRemisionOut, status_code=201)
def crear_guia(
    datos: schemas.GuiaRemisionCrear,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.crear_guia(db, datos)


@router.post(
    "/desde-venta/{orden_venta_id}", response_model=schemas.GuiaRemisionOut, status_code=201
)
def crear_desde_venta(
    orden_venta_id: int,
    datos: schemas.GuiaDesdeVentaCrear,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.crear_desde_orden_venta(db, orden_venta_id, datos)


@router.get("", response_model=list[schemas.GuiaRemisionOut])
def listar_guias(
    estado: str | None = None,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.listar_guias(db, estado)


@router.get("/{guia_id}", response_model=schemas.GuiaRemisionOut)
def obtener_guia(guia_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.obtener_guia(db, guia_id)
