from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ComprobanteCrear(BaseModel):
    orden_venta_id: int
    tipo_comprobante: str = Field(description="FACTURA o BOLETA")


class AnulacionCrear(BaseModel):
    motivo: str = Field(min_length=1, max_length=300)


class ComprobanteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    orden_venta_id: int
    tipo_comprobante: str
    serie: str
    correlativo: int
    numero_completo: str
    cliente_id: int
    cliente_ruc: str
    cliente_razon_social: str
    moneda: str
    subtotal: float
    igv: float
    total: float
    estado: str
    motivo_anulacion: Optional[str] = None
    emitido_en: datetime
    anulado_en: Optional[datetime] = None
