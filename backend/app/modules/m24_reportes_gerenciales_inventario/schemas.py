"""Esquemas Pydantic (response) del modulo m24_reportes_gerenciales_inventario.

FASE 4C -- Reportes Gerenciales de Inventario. Modulo de SOLO LECTURA:
no define ningun schema de escritura, porque no persiste nada nuevo --
todos los campos aca provienen de indicadores ya calculados en
m03_inventario, m19_reportes, m22_inteligencia_inventario y
m23_dashboard_inventario (ver models.py y service.py para el origen
exacto de cada campo).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------
# 1) Resumen ejecutivo de inventario
# ---------------------------------------------------------------------


class ResumenEjecutivoInventario(BaseModel):
    """Mismos 7 indicadores que
    m23_dashboard_inventario.schemas.ResumenDashboardInventario. Este
    modulo NO recalcula nada: reexpone tal cual el resultado de
    m23_dashboard_inventario.service.resumen_dashboard() bajo el prefijo
    de Reportes Gerenciales de Inventario (ver service.py)."""

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
    productos_vencidos: int = Field(..., description="Cantidad de lotes vencidos (semaforo NEGRO).")
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


# ---------------------------------------------------------------------
# 2) Ranking de productos de mayor valor
# ---------------------------------------------------------------------


class ProductoTopValor(BaseModel):
    producto: str
    codigo_producto: str
    stock_actual: float
    costo_unitario: float = Field(
        ..., description="Costo unitario promedio ponderado (valor_promedio_unitario de m19_reportes)."
    )
    valor_total: float
    porcentaje_participacion: float = Field(
        ..., description="valor_total del producto / valor_total_inventario global, en porcentaje (0-100)."
    )


class ReporteTopValorInventario(BaseModel):
    generado_en: datetime
    total_productos: int
    valor_total_inventario: float
    productos: list[ProductoTopValor]


# ---------------------------------------------------------------------
# 3) Productos criticos
# ---------------------------------------------------------------------


class ProductoCritico(BaseModel):
    producto: str
    codigo_producto: str
    tipo_riesgo: str = Field(
        ..., description="BAJO_STOCK | RIESGO_MERMA | VENCIMIENTO (ver service.py para el origen de cada uno)."
    )
    nivel_riesgo: str = Field(..., description="MEDIO | ALTO | CRITICO.")
    stock_actual: float
    valor_comprometido: float = Field(
        ..., description="Valor economico del stock afectado por este riesgo (stock_actual * costo unitario)."
    )


class ReporteProductosCriticos(BaseModel):
    generado_en: datetime
    total_productos: int
    productos: list[ProductoCritico]


# ---------------------------------------------------------------------
# 4) Productos sin rotacion
# ---------------------------------------------------------------------


class ProductoSinRotacion(BaseModel):
    producto: str
    codigo_producto: str
    stock_actual: float
    valor_inventario: float
    dias_sin_movimiento: Optional[int] = Field(
        default=None,
        description=(
            "Dias transcurridos desde el ultimo MovimientoKardex (cualquier tipo) de este "
            "producto. None cuando el producto nunca tuvo un movimiento registrado en el Kardex."
        ),
    )


class ReporteProductosSinRotacion(BaseModel):
    generado_en: datetime
    total_productos: int
    productos: list[ProductoSinRotacion]
