from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DeclaracionItemCrear(BaseModel):
    producto_id: int
    cantidad: float = Field(gt=0)
    precio_unitario_exportacion: float = Field(ge=0)


class DeclaracionCrear(BaseModel):
    cliente_nombre: str = Field(min_length=1, max_length=200)
    pais_destino: str = Field(min_length=1, max_length=80)
    incoterm: str = Field(default="FOB", min_length=3, max_length=5)
    moneda: str = Field(default="USD", min_length=3, max_length=3)
    numero_dua: Optional[str] = None
    observaciones: Optional[str] = None
    inventario_origen_id: int = Field(
        description=(
            "Inventario/almacen logico del que sale la mercaderia al "
            "embarcar (mismo patron que inventario_destino_id en Compras "
            "e inventario_salida_id en Ventas)."
        )
    )
    items: list[DeclaracionItemCrear] = Field(min_length=1)


class DeclaracionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    cantidad: float
    precio_unitario_exportacion: float
    costo_unitario: Optional[float] = Field(
        default=None,
        description=(
            "Costo unitario real consumido del kardex (FEFO) al momento del "
            "embarque. Queda en None mientras la declaracion no esta EMBARCADA "
            "(el costo real recien se conoce al descontar stock)."
        ),
    )


class DeclaracionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero_dua: Optional[str] = None
    cliente_nombre: str
    pais_destino: str
    incoterm: str
    moneda: str
    estado: str
    observaciones: Optional[str] = None
    creado_en: datetime
    confirmado_en: Optional[datetime] = None
    embarcado_en: Optional[datetime] = None
    cancelado_en: Optional[datetime] = None
    items: list[DeclaracionItemOut] = []
