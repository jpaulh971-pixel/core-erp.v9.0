"""Esquemas Pydantic (request/response) del modulo m14_inteligencia_tributaria."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ResumenPorTipoComprobante(BaseModel):
    tipo_comprobante: str
    cantidad: int
    subtotal: float
    igv: float
    total: float


class ResumenIGV(BaseModel):
    desde: Optional[datetime] = None
    hasta: Optional[datetime] = None
    por_tipo_comprobante: list[ResumenPorTipoComprobante]
    total_comprobantes: int
    total_subtotal: float
    total_igv: float
    total_general: float


class ComprobanteLibroVentas(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_completo: str
    tipo_comprobante: str
    estado: str
    cliente_ruc: str
    cliente_razon_social: str
    moneda: str
    subtotal: float
    igv: float
    total: float
    emitido_en: datetime


class ComprobanteAnulado(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_completo: str
    tipo_comprobante: str
    cliente_ruc: str
    cliente_razon_social: str
    total: float
    motivo_anulacion: Optional[str] = None
    emitido_en: datetime
    anulado_en: Optional[datetime] = None
