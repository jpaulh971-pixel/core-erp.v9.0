"""Endpoints FastAPI del modulo m14_inteligencia_tributaria."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m14_inteligencia_tributaria import schemas, service

router = APIRouter(prefix="/api/inteligencia-tributaria", tags=["inteligencia_tributaria"])


@router.get("/resumen-igv", response_model=schemas.ResumenIGV)
def resumen_igv(
    desde: date | None = Query(default=None, description="Filtra por fecha de emision"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de emision"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.resumen_igv(db, desde, hasta)


@router.get("/libro-ventas", response_model=list[schemas.ComprobanteLibroVentas])
def libro_ventas(
    desde: date | None = Query(default=None, description="Filtra por fecha de emision"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de emision"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.libro_ventas(db, desde, hasta)


@router.get("/comprobantes-anulados", response_model=list[schemas.ComprobanteAnulado])
def comprobantes_anulados(
    desde: date | None = Query(default=None, description="Filtra por fecha de emision"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de emision"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.comprobantes_anulados(db, desde, hasta)
