from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Inventario ---

class InventarioCrear(BaseModel):
    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=1, max_length=150)


class InventarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    activo: bool


# --- ProductoInventario ---

class ProductoInventarioCrear(BaseModel):
    producto_id: int
    inventario_id: int
    codigo_interno: str = Field(min_length=1, max_length=30)
    familia: Optional[str] = None
    presentacion: Optional[str] = None
    litros_presentacion: Optional[float] = None
    marca: Optional[str] = None


class ProductoInventarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    inventario_id: int
    codigo_interno: str
    familia: Optional[str] = None
    presentacion: Optional[str] = None
    litros_presentacion: Optional[float] = None
    marca: Optional[str] = None
    estado: bool


# --- Movimientos ---

class IngresoInventarioCrear(BaseModel):
    producto_id: int
    inventario_id: int
    codigo_lote: str = Field(min_length=1, max_length=50)
    cantidad: float = Field(gt=0)
    costo_unitario: float = Field(ge=0)
    fecha_elaboracion: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    referencia: Optional[str] = None
    # --- Opcional, Paso 2 (Carga historica de Compras/Ventas). Si se
    # informa, el lote (fecha_ingreso) y el movimiento de kardex
    # (creado_en) nacen con ESTA fecha en vez de la fecha real de
    # ejecucion del proceso de carga, para reconstruir correctamente la
    # realidad operativa pasada. Si no se informa (flujo manual/operativo
    # normal), el comportamiento es exactamente el de antes (server_default
    # = momento real).
    fecha_movimiento: Optional[datetime] = None

    # Datos de ProductoInventario, usados solo si hay que CREARLO (primera
    # vez que este producto entra a este inventario). Si ya existe, se
    # ignoran y se conserva lo ya registrado.
    codigo_interno: Optional[str] = None
    familia: Optional[str] = None
    presentacion: Optional[str] = None
    litros_presentacion: Optional[float] = None
    marca: Optional[str] = None


class SalidaInventarioCrear(BaseModel):
    producto_id: int
    inventario_id: int
    cantidad: float = Field(gt=0)
    lote_id: Optional[int] = Field(
        default=None,
        description="Si se indica, se consume solo de ese lote; si no, FEFO automatico dentro del inventario",
    )
    referencia: Optional[str] = None
    # --- Opcional, Paso 2 (Carga historica de Compras/Ventas). Ver
    # IngresoInventarioCrear.fecha_movimiento arriba: misma semantica,
    # ademas se usa como fecha de referencia para decidir que lotes estan
    # vencidos (FEFO), en vez de comparar contra el momento real.
    fecha_movimiento: Optional[datetime] = None


class AjusteInventarioCrear(BaseModel):
    lote_id: int
    cantidad: float = Field(description="Positivo para ajuste a favor, negativo para ajuste en contra")
    referencia: Optional[str] = None


class LoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_inventario_id: int
    codigo_lote: str
    cantidad_inicial: float
    cantidad_actual: float
    costo_unitario: float
    fecha_elaboracion: Optional[datetime] = None
    fecha_ingreso: datetime
    fecha_vencimiento: Optional[datetime] = None


class MovimientoKardexOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_inventario_id: int
    inventario_id: int
    lote_id: int
    tipo_movimiento: str
    cantidad: float
    costo_unitario: float
    saldo_resultante: float
    referencia: Optional[str] = None
    creado_en: datetime


class SaldoProductoOut(BaseModel):
    producto_inventario_id: int
    inventario_id: int
    producto_id: int
    codigo_interno: str
    nombre: str
    stock_total: float
    stock_minimo: float
    bajo_stock_minimo: bool
    semaforo_stock: str = Field(
        default="VERDE",
        description=(
            "FASE 2 (control gerencial): VERDE (stock normal), AMARILLO "
            "(cercano al minimo) o ROJO (igual o menor al minimo). Calculado "
            "por m03_inventario.service.calcular_semaforo_stock; no redefine "
            "bajo_stock_minimo, que se mantiene igual."
        ),
    )
    costo_unitario_promedio: float = Field(
        default=0.0,
        description=(
            "Promedio ponderado (por cantidad_actual) del costo_unitario ya "
            "registrado en los lotes vigentes de este producto en este "
            "inventario. Es una lectura/agregacion de datos ya calculados "
            "por el motor de costeo (ingresos/PEPS/FEFO de m03); no "
            "redefine ni recalcula ningun costo."
        ),
    )
