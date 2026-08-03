from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GuiaRemisionDetalleCrear(BaseModel):
    """Solo para creacion MANUAL. En creacion desde-venta los detalles se
    derivan del Kardex real, no se reciben del cliente de la API."""

    producto_id: int
    lote_id: int
    cantidad: float = Field(gt=0)
    unidad_medida: str = Field(default="UND", max_length=20)


class GuiaRemisionCrear(BaseModel):
    cliente_id: int
    inventario_id: int
    motivo_traslado: str = Field(default="VENTA", max_length=200)
    numero_guia: Optional[str] = None
    detalles: list[GuiaRemisionDetalleCrear] = Field(min_length=1)


class GuiaDesdeVentaCrear(BaseModel):
    """La orden_venta_id viaja en la URL. Aqui solo va lo que no se puede
    derivar automaticamente del despacho."""

    motivo_traslado: str = Field(default="VENTA", max_length=200)
    numero_guia: Optional[str] = None


class GuiaRemisionDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    lote_id: int
    cantidad: float
    unidad_medida: str


class GuiaRemisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_guia: str
    fecha_emision: datetime
    estado: str
    cliente_id: int
    cliente_razon_social: str
    orden_venta_id: Optional[int] = None
    inventario_id: int
    motivo_traslado: str
    anulado_en: Optional[datetime] = None
    creado_en: datetime
    detalles: list[GuiaRemisionDetalleOut] = []
