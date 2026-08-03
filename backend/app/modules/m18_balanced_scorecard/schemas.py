"""Esquemas Pydantic (request/response) del modulo m18_balanced_scorecard."""
from datetime import date
from typing import Optional

from pydantic import BaseModel


class PerspectivaFinanciera(BaseModel):
    desde: Optional[date] = None
    hasta: Optional[date] = None
    ingreso_ventas_despachadas: float
    costo_mercaderia_vendida: float
    costos_adicionales_operacion: float
    utilidad_neta: float
    margen_neto_pct: Optional[float] = None


class PerspectivaClientes(BaseModel):
    desde: Optional[date] = None
    hasta: Optional[date] = None
    clientes_activos_total: int
    clientes_con_compra_en_periodo: int
    pct_clientes_activos_con_compra: Optional[float] = None
    ticket_promedio_venta: Optional[float] = None
    concentracion_top3_clientes_pct: Optional[float] = None


class PerspectivaProcesosInternos(BaseModel):
    desde: Optional[date] = None
    hasta: Optional[date] = None
    dpmo_mermas: float
    nivel_sigma: float
    dias_promedio_ciclo_compras: Optional[float] = None
    dias_promedio_ciclo_ventas: Optional[float] = None
    productos_en_restriccion_stock: int


class PerspectivaAprendizajeCrecimiento(BaseModel):
    productos_activos_total: int
    proveedores_activos_total: int
    productos_sin_movimiento: int


class TableroBalancedScorecard(BaseModel):
    desde: Optional[date] = None
    hasta: Optional[date] = None
    financiera: PerspectivaFinanciera
    clientes: PerspectivaClientes
    procesos_internos: PerspectivaProcesosInternos
    aprendizaje_crecimiento: PerspectivaAprendizajeCrecimiento
