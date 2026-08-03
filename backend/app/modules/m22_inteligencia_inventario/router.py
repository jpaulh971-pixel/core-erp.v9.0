"""Endpoints FastAPI del modulo m22_inteligencia_inventario.

FASE 3 -- Inteligencia de inventario para perecibles. Todos los
endpoints son GET de solo lectura; ninguno modifica stock, kardex ni
costos. Mismo patron (prefix + tags + Depends(get_db)/Depends
(get_usuario_actual)) que el resto de modulos del ERP.
"""
from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m22_inteligencia_inventario import schemas, service

router = APIRouter(prefix="/api/inteligencia-inventario", tags=["inteligencia-inventario"])


@router.get(
    "/{inventario_id}",
    response_model=schemas.ResumenInteligenciaInventario,
)
def indicadores_inventario(
    inventario_id: int,
    dias_analisis: int | None = Query(
        default=None,
        description=(
            "Ventana de dias de Kardex a considerar para consumo y rotacion. "
            "Si se omite, usa settings.DIAS_ANALISIS_INVENTARIO_DEFAULT."
        ),
    ),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    """Rotacion, dias de inventario, consumo promedio (diario/semanal/
    mensual) y riesgo de merma para todos los productos de un inventario."""
    return service.indicadores_inventario(db, inventario_id, dias_analisis)


@router.get(
    "/{inventario_id}/{producto_inventario_id}",
    response_model=schemas.IndicadorInventario,
)
def indicador_producto(
    inventario_id: int,
    producto_inventario_id: int,
    dias_analisis: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    """Mismos indicadores que el endpoint de lista, para un solo
    producto (misma logica reutilizada, sin calculos nuevos)."""
    return service.indicador_producto(db, inventario_id, producto_inventario_id, dias_analisis)
