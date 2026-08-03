"""Endpoints FastAPI del modulo m15_lean_six_sigma."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m15_lean_six_sigma import schemas, service

router = APIRouter(prefix="/api/lean-six-sigma", tags=["lean_six_sigma"])


@router.get("/mermas", response_model=schemas.ResumenMermas)
def resumen_mermas(
    desde: date | None = Query(default=None, description="Filtra por fecha de movimiento"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de movimiento"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.resumen_mermas(db, desde, hasta)


@router.get("/tiempos-ciclo/compras", response_model=schemas.TiemposCicloCompras)
def tiempos_ciclo_compras(
    desde: date | None = Query(default=None, description="Filtra por fecha de recepcion"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de recepcion"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.tiempos_ciclo_compras(db, desde, hasta)


@router.get("/tiempos-ciclo/ventas", response_model=schemas.TiemposCicloVentas)
def tiempos_ciclo_ventas(
    desde: date | None = Query(default=None, description="Filtra por fecha de despacho"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de despacho"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.tiempos_ciclo_ventas(db, desde, hasta)
