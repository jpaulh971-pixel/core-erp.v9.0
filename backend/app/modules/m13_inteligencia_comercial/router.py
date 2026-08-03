"""Endpoints FastAPI del modulo m13_inteligencia_comercial."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m13_inteligencia_comercial import schemas, service

router = APIRouter(prefix="/api/inteligencia-comercial", tags=["inteligencia_comercial"])


@router.get("/productos-mas-vendidos", response_model=list[schemas.ProductoMasVendido])
def productos_mas_vendidos(
    limit: int = Query(default=10, gt=0, le=100),
    desde: date | None = Query(default=None, description="Filtra por fecha de despacho"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de despacho"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.productos_mas_vendidos(db, limit, desde, hasta)


@router.get("/clientes-top", response_model=list[schemas.ClienteTop])
def clientes_top(
    limit: int = Query(default=10, gt=0, le=100),
    desde: date | None = Query(default=None, description="Filtra por fecha de despacho"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de despacho"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.clientes_top(db, limit, desde, hasta)


@router.get("/rotacion-inventario", response_model=list[schemas.RotacionProducto])
def rotacion_inventario(
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.rotacion_inventario(db)


@router.get("/margen-productos", response_model=list[schemas.MargenProducto])
def margen_productos(
    limit: int = Query(default=10, gt=0, le=100),
    desde: date | None = Query(default=None, description="Filtra por fecha de despacho"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de despacho"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.margen_por_producto(db, limit, desde, hasta)
