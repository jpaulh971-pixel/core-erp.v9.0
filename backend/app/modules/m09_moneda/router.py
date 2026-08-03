from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m09_moneda import schemas, service

router = APIRouter(prefix="/api/moneda", tags=["moneda"])


@router.post("/tipos-cambio", response_model=schemas.TipoCambioOut, status_code=201)
def registrar_tipo_cambio(
    datos: schemas.TipoCambioCrear,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.registrar_tipo_cambio(db, datos)


@router.get("/tipos-cambio/{moneda_origen}/{moneda_destino}", response_model=list[schemas.TipoCambioOut])
def historial_tipo_cambio(
    moneda_origen: str,
    moneda_destino: str,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.listar_historial_par(db, moneda_origen, moneda_destino)


@router.get("/tipos-cambio/{moneda_origen}/{moneda_destino}/vigente", response_model=schemas.TipoCambioVigenteOut)
def tipo_cambio_vigente(
    moneda_origen: str,
    moneda_destino: str,
    fecha: date | None = Query(default=None, description="Default: hoy"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.obtener_tipo_cambio_vigente(db, moneda_origen, moneda_destino, fecha)


@router.get("/convertir", response_model=schemas.ConversionOut)
def convertir(
    monto: float = Query(gt=0),
    moneda_origen: str = Query(min_length=3, max_length=3),
    moneda_destino: str = Query(min_length=3, max_length=3),
    fecha: date | None = Query(default=None, description="Default: hoy"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.convertir(db, monto, moneda_origen, moneda_destino, fecha)
