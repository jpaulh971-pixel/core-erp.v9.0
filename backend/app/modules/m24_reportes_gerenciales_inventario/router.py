"""Endpoints FastAPI del modulo m24_reportes_gerenciales_inventario
(Fase 4C - backend).

Los 4 endpoints son de solo lectura; ninguno modifica stock, kardex ni
costos. Mismo patron (prefix + tags + Depends(get_db)/
Depends(get_usuario_actual)) que el resto de modulos del ERP.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m24_reportes_gerenciales_inventario import schemas, service, validators

router = APIRouter(
    prefix="/api/reportes-gerenciales-inventario", tags=["reportes-gerenciales-inventario"]
)


@router.get("/resumen", response_model=schemas.ResumenEjecutivoInventario)
def obtener_resumen_ejecutivo(
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    """Resumen ejecutivo de inventario. Reexpone (sin recalcular) el
    resumen ya consolidado por m23_dashboard_inventario."""
    return service.resumen_ejecutivo(db)


@router.get("/top-valor", response_model=schemas.ReporteTopValorInventario)
def obtener_top_valor(
    limite: int | None = Query(
        default=None,
        description="Cantidad maxima de productos a devolver (ordenados por valor_total descendente). Sin limite si se omite.",
    ),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    """Ranking de productos de mayor valor en inventario. Reutiliza
    m19_reportes.service.reporte_inventario_valorizado()."""
    validators.validar_limite(limite)
    return service.top_valor(db, limite)


@router.get("/productos-criticos", response_model=schemas.ReporteProductosCriticos)
def obtener_productos_criticos(
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    """Productos criticos: bajo stock, riesgo de merma alto/critico,
    proximos a vencer y vencidos. Combina (sin recalcular)
    m19_reportes y m22_inteligencia_inventario."""
    return service.productos_criticos(db)


@router.get("/sin-rotacion", response_model=schemas.ReporteProductosSinRotacion)
def obtener_sin_rotacion(
    dias_sin_rotacion: int | None = Query(
        default=None,
        description=(
            "Umbral minimo de dias sin movimiento de Kardex para incluir un producto. "
            "Si se omite, usa settings.UMBRAL_DIAS_SIN_ROTACION."
        ),
    ),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    """Productos con stock disponible pero sin consumo/rotacion dentro
    de la ventana de analisis de m22_inteligencia_inventario."""
    validators.validar_dias_sin_rotacion(dias_sin_rotacion)
    return service.sin_rotacion(db, dias_sin_rotacion)
