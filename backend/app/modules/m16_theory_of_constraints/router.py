"""Endpoints FastAPI del modulo m16_theory_of_constraints."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m16_theory_of_constraints import schemas, service

router = APIRouter(prefix="/api/theory-of-constraints", tags=["theory_of_constraints"])


@router.get("/restricciones-stock", response_model=list[schemas.RestriccionProducto])
def restricciones_stock(
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.restricciones_stock(db)


@router.get("/ordenes-en-espera", response_model=list[schemas.OrdenEnEspera])
def ordenes_en_espera(
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.ordenes_en_espera(db)


@router.get("/contabilidad-throughput", response_model=schemas.ContabilidadThroughput)
def contabilidad_throughput(
    desde: date | None = Query(default=None, description="Filtra por fecha de despacho/gasto"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de despacho/gasto"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.contabilidad_throughput(db, desde, hasta)
