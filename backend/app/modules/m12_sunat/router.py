from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m12_sunat import schemas, service

router = APIRouter(prefix="/api/sunat", tags=["sunat"])


@router.post("/comprobantes", response_model=schemas.ComprobanteOut, status_code=201)
def emitir_comprobante(
    datos: schemas.ComprobanteCrear,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.emitir_comprobante(db, datos)


@router.get("/comprobantes", response_model=list[schemas.ComprobanteOut])
def listar_comprobantes(
    estado: str | None = None,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.listar_comprobantes(db, estado)


@router.get("/comprobantes/{comprobante_id}", response_model=schemas.ComprobanteOut)
def obtener_comprobante(
    comprobante_id: int,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.obtener_comprobante(db, comprobante_id)


@router.get("/ordenes/{orden_venta_id}/comprobante", response_model=schemas.ComprobanteOut)
def obtener_comprobante_por_orden(
    orden_venta_id: int,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.obtener_comprobante_por_orden(db, orden_venta_id)


@router.post("/comprobantes/{comprobante_id}/anular", response_model=schemas.ComprobanteOut)
def anular_comprobante(
    comprobante_id: int,
    datos: schemas.AnulacionCrear,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.anular_comprobante(db, comprobante_id, datos)
