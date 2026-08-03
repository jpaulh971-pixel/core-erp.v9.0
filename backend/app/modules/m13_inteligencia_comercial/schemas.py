"""Esquemas Pydantic (request/response) del modulo m13_inteligencia_comercial."""
from pydantic import BaseModel


class ProductoMasVendido(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    cantidad_vendida: float
    monto_vendido: float


class ClienteTop(BaseModel):
    cliente_id: int
    ruc: str
    razon_social: str
    monto_comprado: float
    cantidad_ordenes: int


class RotacionProducto(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    cantidad_vendida_historica: float
    stock_actual: float
    indice_rotacion: float | None
    sin_movimiento: bool
    costo_unitario_promedio: float = 0.0


class MargenProducto(BaseModel):
    """Analisis de margen por producto, derivado unicamente de datos ya
    calculados (costo_unitario_promedio de m03_inventario.saldos y el
    precio/monto vendido de productos_mas_vendidos). No introduce ninguna
    regla de costeo nueva."""

    producto_id: int
    codigo: str
    nombre: str
    costo_unitario: float
    precio_venta_promedio: float
    margen_pct: float | None
    rentabilidad: float
