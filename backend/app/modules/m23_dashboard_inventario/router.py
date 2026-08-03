"""Endpoints FastAPI del modulo m23_dashboard_inventario (Fase 4A - base).

Unico endpoint de esta fase, de solo lectura; no modifica stock,
kardex ni costos. Mismo patron (prefix + tags + Depends(get_db)/
Depends(get_usuario_actual)) que el resto de modulos del ERP.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m23_dashboard_inventario import schemas, service

router = APIRouter(prefix="/api/dashboard-inventario", tags=["dashboard-inventario"])


@router.get("/resumen", response_model=schemas.ResumenDashboardInventario)
def obtener_resumen_dashboard_inventario(
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    """Resumen gerencial base del Dashboard de Inventario. Consolida
    (sin recalcular) indicadores ya existentes en m03_inventario,
    m19_reportes y m22_inteligencia_inventario."""
    return service.resumen_dashboard(db)
