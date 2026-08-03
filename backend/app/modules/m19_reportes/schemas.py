"""Esquemas Pydantic (request/response) del modulo m19_reportes."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProductoAgregado(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    cantidad: float
    total: float
    costo_unitario_promedio: Optional[float] = None


class ClienteAgregado(BaseModel):
    cliente_id: int
    razon_social: str
    cantidad_ordenes: int
    total: float


class ProveedorAgregado(BaseModel):
    proveedor_id: int
    razon_social: str
    cantidad_ordenes: int
    total: float


class ReporteVentas(BaseModel):
    desde: Optional[date] = None
    hasta: Optional[date] = None
    total_ordenes: int
    total_vendido: float
    por_producto: list[ProductoAgregado]
    por_cliente: list[ClienteAgregado]


class ReporteCompras(BaseModel):
    desde: Optional[date] = None
    hasta: Optional[date] = None
    total_ordenes: int
    total_comprado: float
    por_producto: list[ProductoAgregado]
    por_proveedor: list[ProveedorAgregado]


class ProductoValorizado(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    cantidad_actual: float
    valor_promedio_unitario: float
    valor_total: float
    stock_minimo: float
    bajo_stock_minimo: bool
    semaforo_stock: str = Field(
        default="VERDE",
        description=(
            "FASE 2 (control gerencial): VERDE/AMARILLO/ROJO. Calculado por "
            "m03_inventario.service.calcular_semaforo_stock; no redefine "
            "bajo_stock_minimo, que se mantiene igual."
        ),
    )


class ReporteInventarioValorizado(BaseModel):
    generado_en: datetime
    total_productos: int
    valor_total_inventario: float
    productos_bajo_stock_minimo: int
    productos: list[ProductoValorizado]


# --- FASE 2: control gerencial para inventario perecible ---

class LotePorProducto(BaseModel):
    """Una fila del reporte 'Inventario por lote' (solo lectura)."""

    producto_id: int
    producto: str
    codigo_producto: str
    codigo_lote: str
    fecha_ingreso: Optional[datetime] = None
    fecha_elaboracion: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    cantidad_inicial: float
    cantidad_disponible: float
    costo_unitario: float
    valor_total_lote: float
    estado_lote: str
    semaforo_vencimiento: str
    dias_restantes_vencimiento: Optional[int] = None
    proveedor: Optional[str] = None


class ReporteInventarioPorLote(BaseModel):
    generado_en: datetime
    total_lotes: int
    valor_total: float
    lotes: list[LotePorProducto]


class LoteProximoVencer(BaseModel):
    """Una fila del reporte 'Productos proximos a vencer' (solo lectura)."""

    producto_id: int
    producto: str
    codigo_producto: str
    codigo_lote: str
    fecha_vencimiento: datetime
    dias_restantes: Optional[int] = None
    categoria: str = Field(description="ACTIVOS | PROXIMOS_A_VENCER | VENCIDOS")
    estado_lote: str
    semaforo_vencimiento: str
    cantidad_disponible: float
    costo_unitario: float
    valor_stock_comprometido: float


class ReporteProximosVencer(BaseModel):
    generado_en: datetime
    total_lotes: int
    activos: int
    proximos_a_vencer: int
    vencidos: int
    valor_total_comprometido: float
    lotes: list[LoteProximoVencer]


class ResumenGeneral(BaseModel):
    desde: Optional[date] = None
    hasta: Optional[date] = None
    total_vendido_periodo: float
    total_comprado_periodo: float
    ordenes_venta_periodo: int
    ordenes_compra_periodo: int
    valor_inventario_actual: float
    productos_bajo_stock_minimo: int
