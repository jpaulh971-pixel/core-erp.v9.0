from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class OrdenCompraItemCrear(BaseModel):
    producto_id: int
    cantidad: float = Field(gt=0)
    costo_unitario: float = Field(ge=0)
    # --- Opcionales, Fase 9 (Importacion de Compras Nacionalizadas). Si no
    # se envian, el comportamiento es exactamente el de antes.
    lote: Optional[str] = None
    fecha_elaboracion: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    observaciones: Optional[str] = None
    # --- Opcionales, formato Excel del cliente (COMPRAS_ECO_NEOAGROX_2026).
    presentacion: Optional[str] = None
    unidad_medida: Optional[str] = None
    cantidad_por_unidad: Optional[float] = None
    concepto: Optional[str] = None


class OrdenCompraCrear(BaseModel):
    proveedor_id: int
    inventario_destino_id: int
    moneda: str = Field(default="USD", min_length=3, max_length=3)
    observaciones: Optional[str] = None
    items: list[OrdenCompraItemCrear] = Field(min_length=1)
    # --- Opcionales, Fase 9 (Importacion de Compras Nacionalizadas).
    numero_orden_externo: Optional[str] = None
    invoice: Optional[str] = None
    documento_aduanero: Optional[str] = None
    pais_origen: Optional[str] = None
    fecha_documento: Optional[datetime] = None
    # --- Opcionales, formato Excel del cliente (COMPRAS_ECO_NEOAGROX_2026).
    dias_credito: Optional[int] = None
    fecha_vencimiento_factura: Optional[datetime] = None
    # --- Opcional, Paso 2 (Carga historica de Compras). Distinto de
    # fecha_documento (esa es la fecha de la factura del proveedor): esta
    # es la fecha REAL del movimiento que se esta reconstruyendo. Si se
    # informa, creado_en de la orden nace con esta fecha en vez de la
    # fecha en que corre el proceso de carga. Se propaga tambien a
    # aprobar_orden()/recibir_orden() por fuera de este schema (no son
    # parte de la creacion de la orden).
    fecha_movimiento: Optional[datetime] = None


class OrdenCompraItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    cantidad: float
    costo_unitario: float
    lote: Optional[str] = None
    fecha_elaboracion: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    observaciones: Optional[str] = None
    presentacion: Optional[str] = None
    unidad_medida: Optional[str] = None
    cantidad_por_unidad: Optional[float] = None
    concepto: Optional[str] = None


class OrdenCompraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    proveedor_id: int
    inventario_destino_id: int
    estado: str
    moneda: str
    observaciones: Optional[str] = None
    creado_en: datetime
    aprobado_en: Optional[datetime] = None
    recibido_en: Optional[datetime] = None
    cancelado_en: Optional[datetime] = None
    numero_orden_externo: Optional[str] = None
    invoice: Optional[str] = None
    documento_aduanero: Optional[str] = None
    pais_origen: Optional[str] = None
    fecha_documento: Optional[datetime] = None
    dias_credito: Optional[int] = None
    fecha_vencimiento_factura: Optional[datetime] = None
    items: list[OrdenCompraItemOut] = []
