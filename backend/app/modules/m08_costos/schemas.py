from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CostoAdicionalCrear(BaseModel):
    tipo_documento: str = Field(description="COMPRA o EXPORTACION")
    documento_id: int
    tipo_costo: str = Field(
        description="FLETE, SEGURO, ADUANA, ALMACENAJE, MANIPULEO u OTRO"
    )
    descripcion: Optional[str] = None
    monto: float = Field(gt=0)
    moneda: str = Field(default="USD", min_length=3, max_length=3)


class CostoAdicionalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo_documento: str
    documento_id: int
    tipo_costo: str
    descripcion: Optional[str] = None
    monto: float
    moneda: str
    creado_en: datetime


class CosteoCompraOut(BaseModel):
    orden_compra_id: int
    valor_mercaderia: float
    costos_adicionales: float
    costo_total: float
    cantidad_total: float
    costo_unitario_ponderado: float
    detalle_costos_adicionales: list[CostoAdicionalOut] = []


class RentabilidadExportacionOut(BaseModel):
    declaracion_id: int
    ingreso_exportacion: float
    costo_mercaderia_real: float
    costos_adicionales: float
    utilidad_bruta: float
    margen_pct: float
    detalle_costos_adicionales: list[CostoAdicionalOut] = []
