"""Endpoints FastAPI del modulo m01_dashboard."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m01_dashboard import schemas, service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/resumen", response_model=schemas.DashboardOut)
def resumen_ejecutivo(
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.resumen_ejecutivo(db)
