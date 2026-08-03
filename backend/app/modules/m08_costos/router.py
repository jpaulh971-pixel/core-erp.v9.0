from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m08_costos import schemas, service

router = APIRouter(prefix="/api/costos", tags=["costos"])


@router.post("/adicionales", response_model=schemas.CostoAdicionalOut, status_code=201)
def registrar_adicional(
    datos: schemas.CostoAdicionalCrear,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.registrar_costo_adicional(db, datos)


@router.get("/compras/{orden_compra_id}/costeo", response_model=schemas.CosteoCompraOut)
def costeo_compra(
    orden_compra_id: int,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.costeo_compra(db, orden_compra_id)


@router.get(
    "/exportaciones/{declaracion_id}/rentabilidad",
    response_model=schemas.RentabilidadExportacionOut,
)
def rentabilidad_exportacion(
    declaracion_id: int,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.rentabilidad_exportacion(db, declaracion_id)
