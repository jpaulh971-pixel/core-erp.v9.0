"""Endpoints FastAPI del modulo m18_balanced_scorecard."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m18_balanced_scorecard import schemas, service

router = APIRouter(prefix="/api/balanced-scorecard", tags=["balanced_scorecard"])


@router.get("/financiera", response_model=schemas.PerspectivaFinanciera)
def financiera(
    desde: date | None = Query(default=None, description="Filtra por fecha de despacho/gasto"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de despacho/gasto"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.perspectiva_financiera(db, desde, hasta)


@router.get("/clientes", response_model=schemas.PerspectivaClientes)
def clientes(
    desde: date | None = Query(default=None, description="Filtra por fecha de despacho"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de despacho"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.perspectiva_clientes(db, desde, hasta)


@router.get("/procesos-internos", response_model=schemas.PerspectivaProcesosInternos)
def procesos_internos(
    desde: date | None = Query(default=None, description="Filtra por fecha de movimiento/ciclo"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de movimiento/ciclo"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.perspectiva_procesos_internos(db, desde, hasta)


@router.get("/aprendizaje-crecimiento", response_model=schemas.PerspectivaAprendizajeCrecimiento)
def aprendizaje_crecimiento(
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.perspectiva_aprendizaje_crecimiento(db)


@router.get("/tablero", response_model=schemas.TableroBalancedScorecard)
def tablero(
    desde: date | None = Query(default=None, description="Filtra por fecha de despacho/gasto"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de despacho/gasto"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.tablero(db, desde, hasta)
