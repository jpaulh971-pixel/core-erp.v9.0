"""Esquemas Pydantic (request/response) del modulo m01_dashboard."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AlertaStock(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    stock_total: float
    stock_minimo: float
    costo_unitario_promedio: float = 0.0


class ProductoCosto(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    costo_unitario_promedio: float


class ResumenInventario(BaseModel):
    total_productos_activos: int
    valor_total_inventario: float
    productos_bajo_stock_minimo: int
    alertas_stock: list[AlertaStock] = []
    costo_unitario_promedio_general: float = Field(
        default=0.0,
        description=(
            "valor_total_inventario / stock_total_general. Division de datos "
            "ya existentes, no un calculo de costeo nuevo."
        ),
    )
    producto_mayor_costo: Optional[ProductoCosto] = Field(
        default=None,
        description="Producto con el costo_unitario_promedio mas alto entre los saldos actuales.",
    )
    producto_menor_costo: Optional[ProductoCosto] = Field(
        default=None,
        description=(
            "Producto con el costo_unitario_promedio mas bajo (excluyendo "
            "productos sin stock, costo 0.0) entre los saldos actuales."
        ),
    )


class ResumenVentas(BaseModel):
    ordenes_por_estado: dict[str, int]
    total_vendido_despachadas: float


class ResumenCompras(BaseModel):
    total_comprado_recibidas: float


class ResumenCostos(BaseModel):
    total_costos_adicionales: float
    costos_adicionales_por_tipo: dict[str, float]


class DashboardOut(BaseModel):
    generado_en: datetime
    inventario: ResumenInventario
    ventas: ResumenVentas
    compras: ResumenCompras
    costos: ResumenCostos
