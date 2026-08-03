"""Esquemas Pydantic (request/response) del modulo m16_theory_of_constraints."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class RestriccionProducto(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    demanda_confirmada_pendiente: float
    stock_disponible: float
    deficit: float
    es_restriccion: bool


class OrdenEnEspera(BaseModel):
    orden_id: int
    cliente_razon_social: str
    confirmado_en: Optional[datetime] = None
    dias_esperando: Optional[float] = None
    monto_estimado: float


class ContabilidadThroughput(BaseModel):
    desde: Optional[date] = None
    hasta: Optional[date] = None
    ingreso_ventas_despachadas: float
    costo_mercaderia_vendida: float
    throughput: float
    operating_expense: float
    utilidad_neta_toc: float
    inversion_inventario: float
    retorno_sobre_inversion_pct: Optional[float] = None
