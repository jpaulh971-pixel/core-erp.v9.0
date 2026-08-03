"""Schemas del modulo m23_dashboard_inventario (Fase 4A - base).

Unico schema de esta fase: la respuesta del endpoint
GET /api/dashboard-inventario/resumen. Los campos son exactamente los
7 indicadores pedidos para la base del Dashboard Gerencial de
Inventario; no se agrega ningun campo adicional (ABC, ranking de
riesgos y exportaciones quedan fuera de esta fase por alcance).
"""
from pydantic import BaseModel, Field


class ResumenDashboardInventario(BaseModel):
    valor_total_inventario: float = Field(
        ..., description="Valor total del inventario (suma cantidad_actual * costo_unitario)."
    )
    cantidad_productos: int = Field(
        ..., description="Cantidad de productos activos con presencia en inventario."
    )
    cantidad_lotes: int = Field(
        ..., description="Cantidad total de lotes registrados (todos los inventarios)."
    )
    productos_bajo_stock: int = Field(
        ..., description="Cantidad de productos por debajo de su stock minimo."
    )
    productos_proximos_vencer: int = Field(
        ..., description="Cantidad de lotes en estado PROXIMOS_A_VENCER (semaforo AMARILLO/ROJO)."
    )
    productos_vencidos: int = Field(
        ..., description="Cantidad de lotes vencidos (semaforo NEGRO)."
    )
    riesgo_merma_total: int = Field(
        ...,
        description=(
            "Cantidad total de productos en riesgo de merma ALTO o CRITICO, "
            "sumado entre todos los inventarios (m22_inteligencia_inventario)."
        ),
    )

    class Config:
        json_schema_extra = {
            "example": {
                "valor_total_inventario": 125430.50,
                "cantidad_productos": 48,
                "cantidad_lotes": 132,
                "productos_bajo_stock": 5,
                "productos_proximos_vencer": 9,
                "productos_vencidos": 2,
                "riesgo_merma_total": 4,
            }
        }
