"""Endpoints FastAPI del modulo m07_operacion_logistica."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m07_operacion_logistica import schemas, service

router = APIRouter(prefix="/api/operacion-logistica", tags=["operacion_logistica"])


@router.get("", response_model=list[schemas.OperacionLogisticaOut])
def listar(
    estado: str | None = None,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.listar_operaciones(db, estado)


@router.get("/{operacion_id}", response_model=schemas.OperacionLogisticaOut)
def obtener(
    operacion_id: int,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.obtener_operacion(db, operacion_id)


@router.post("", response_model=schemas.OperacionLogisticaOut, status_code=201)
def recepcion(
    datos: schemas.RecepcionCrear,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    return service.registrar_recepcion(db, datos, usuario)


@router.post("/{operacion_id}/inspeccion", response_model=schemas.OperacionLogisticaOut)
def inspeccion(
    operacion_id: int,
    datos: schemas.InspeccionActualizar,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    return service.registrar_inspeccion(db, operacion_id, datos, usuario)


@router.post("/{operacion_id}/ubicacion", response_model=schemas.OperacionLogisticaOut)
def ubicacion(
    operacion_id: int,
    datos: schemas.UbicacionActualizar,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    return service.registrar_ubicacion(db, operacion_id, datos, usuario)


@router.post("/{operacion_id}/disponible", response_model=schemas.OperacionLogisticaOut)
def disponible(
    operacion_id: int,
    datos: schemas.DisponibleActualizar,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    return service.marcar_disponible(db, operacion_id, datos, usuario)


@router.post("/{operacion_id}/reservar", response_model=schemas.OperacionLogisticaOut)
def reservar(
    operacion_id: int,
    datos: schemas.ReservaCrear,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    return service.reservar(db, operacion_id, datos, usuario)


@router.post("/{operacion_id}/picking", response_model=schemas.OperacionLogisticaOut)
def picking(
    operacion_id: int,
    datos: schemas.PickingActualizar,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    return service.registrar_picking(db, operacion_id, datos, usuario)


@router.post("/{operacion_id}/packing", response_model=schemas.OperacionLogisticaOut)
def packing(
    operacion_id: int,
    datos: schemas.PackingActualizar,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    return service.registrar_packing(db, operacion_id, datos, usuario)


@router.post("/{operacion_id}/carga", response_model=schemas.OperacionLogisticaOut)
def carga(
    operacion_id: int,
    datos: schemas.CargaActualizar,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    return service.registrar_carga(db, operacion_id, datos, usuario)


@router.post("/{operacion_id}/despacho", response_model=schemas.OperacionLogisticaOut)
def despacho(
    operacion_id: int,
    datos: schemas.DespachoActualizar,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    return service.registrar_despacho(db, operacion_id, datos, usuario)


@router.post("/{operacion_id}/entrega", response_model=schemas.OperacionLogisticaOut)
def entrega(
    operacion_id: int,
    datos: schemas.EntregaActualizar,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    return service.registrar_entrega(db, operacion_id, datos, usuario)


@router.post("/{operacion_id}/cerrar", response_model=schemas.OperacionLogisticaOut)
def cerrar(
    operacion_id: int,
    datos: schemas.CierreActualizar,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    return service.cerrar_operacion(db, operacion_id, datos, usuario)
