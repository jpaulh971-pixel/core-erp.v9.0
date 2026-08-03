"""Esquemas Pydantic (request/response) del modulo m15_lean_six_sigma."""
from datetime import date
from typing import Optional

from pydantic import BaseModel


class MermaProducto(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    eventos: int
    cantidad_mermada: float


class ResumenMermas(BaseModel):
    desde: Optional[date] = None
    hasta: Optional[date] = None
    total_movimientos_kardex: int
    total_eventos_merma: int
    cantidad_total_mermada: float
    dpmo: float
    nivel_sigma: float
    top_productos: list[MermaProducto] = []


class TiemposCicloCompras(BaseModel):
    ordenes_evaluadas: int
    dias_promedio_solicitud_a_aprobacion: Optional[float] = None
    dias_promedio_aprobacion_a_recepcion: Optional[float] = None
    dias_promedio_total: Optional[float] = None
    dias_min_total: Optional[float] = None
    dias_max_total: Optional[float] = None


class TiemposCicloVentas(BaseModel):
    ordenes_evaluadas: int
    dias_promedio_confirmacion_a_despacho: Optional[float] = None
    dias_min: Optional[float] = None
    dias_max: Optional[float] = None
