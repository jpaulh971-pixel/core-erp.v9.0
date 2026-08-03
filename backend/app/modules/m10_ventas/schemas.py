from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class OrdenVentaItemCrear(BaseModel):
    producto_id: int
    cantidad: float = Field(gt=0)
    precio_unitario_venta: float = Field(ge=0)

    # --- Opcionales, Fase 10 (Importacion masiva de Ventas). Si no se
    # envian, el comportamiento es exactamente el de antes.
    unidad_medida: Optional[str] = None
    descripcion: Optional[str] = None
    sub_total: Optional[float] = None
    igv: Optional[float] = None
    total: Optional[float] = None


class OrdenVentaCrear(BaseModel):
    cliente_id: int
    inventario_salida_id: int
    moneda: str = Field(default="PEN", min_length=3, max_length=3)
    observaciones: Optional[str] = None
    items: list[OrdenVentaItemCrear] = Field(min_length=1)

    # --- Opcionales, Fase 10 (Importacion masiva de Ventas).
    numero_orden_externo: Optional[str] = None
    vendedor: Optional[str] = None
    factura: Optional[str] = None
    guia_remision: Optional[str] = None
    fecha_emision: Optional[datetime] = None
    dias_credito: Optional[int] = None
    fecha_vencimiento: Optional[datetime] = None
    estado_documento: Optional[str] = None
    ruc_cliente: Optional[str] = None
    anio: Optional[int] = None
    meses: Optional[str] = None
    cultivo: Optional[str] = None
    fundo: Optional[str] = None
    # --- Opcional, Paso 2 (Carga historica de Ventas). Distinto de
    # fecha_emision (esa es la fecha del documento/factura): esta es la
    # fecha REAL del movimiento que se esta reconstruyendo. Si se
    # informa, creado_en de la orden nace con esta fecha en vez de la
    # fecha en que corre el proceso de carga. Se propaga tambien a
    # confirmar_orden()/despachar_orden() por fuera de este schema (no
    # son parte de la creacion de la orden).
    fecha_movimiento: Optional[datetime] = None


class OrdenVentaItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    cantidad: float
    precio_unitario_venta: float
    unidad_medida: Optional[str] = None
    descripcion: Optional[str] = None
    sub_total: Optional[float] = None
    igv: Optional[float] = None
    total: Optional[float] = None
    costo_unitario: Optional[float] = Field(
        default=None,
        description=(
            "Costo unitario promedio ya registrado en el kardex al "
            "despachar esta orden (FEFO, m03). Queda en None mientras la "
            "orden no esta DESPACHADA, porque el costo real recien se "
            "conoce en ese momento; no se estima ni se recalcula aqui."
        ),
    )


class OrdenVentaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    cliente_razon_social: str
    inventario_salida_id: int
    moneda: str
    estado: str
    observaciones: Optional[str] = None
    creado_en: datetime
    confirmado_en: Optional[datetime] = None
    despachado_en: Optional[datetime] = None
    cancelado_en: Optional[datetime] = None
    numero_orden_externo: Optional[str] = None
    vendedor: Optional[str] = None
    factura: Optional[str] = None
    guia_remision: Optional[str] = None
    fecha_emision: Optional[datetime] = None
    dias_credito: Optional[int] = None
    fecha_vencimiento: Optional[datetime] = None
    estado_documento: Optional[str] = None
    ruc_cliente: Optional[str] = None
    anio: Optional[int] = None
    meses: Optional[str] = None
    cultivo: Optional[str] = None
    fundo: Optional[str] = None
    items: list[OrdenVentaItemOut] = []
