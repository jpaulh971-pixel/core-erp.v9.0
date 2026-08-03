from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TipoCambioCrear(BaseModel):
    moneda_origen: str = Field(min_length=3, max_length=3, description="Ej: USD")
    moneda_destino: str = Field(min_length=3, max_length=3, description="Ej: PEN")
    fecha: date
    valor: float = Field(gt=0, description="Unidades de moneda_destino por 1 de moneda_origen")


class TipoCambioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    moneda_origen: str
    moneda_destino: str
    fecha: date
    valor: float
    creado_en: datetime


class ConversionOut(BaseModel):
    monto_origen: float
    moneda_origen: str
    moneda_destino: str
    fecha: date
    fecha_tipo_cambio: date
    tipo_cambio_aplicado: float
    monto_convertido: float


class TipoCambioVigenteOut(BaseModel):
    moneda_origen: str
    moneda_destino: str
    fecha_solicitada: date
    fecha_tipo_cambio: date
    valor: float
    invertido: bool = Field(
        description="True si se calculo como 1/valor a partir del par inverso registrado"
    )
