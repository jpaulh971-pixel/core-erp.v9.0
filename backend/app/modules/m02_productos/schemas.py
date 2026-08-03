from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductoBase(BaseModel):
    codigo: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: Optional[str] = None
    unidad_medida: str = "UND"
    partida_arancelaria: Optional[str] = None
    stock_minimo: float = 0
    perecible: bool = False


class ProductoCrear(ProductoBase):
    pass


class ProductoActualizar(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    unidad_medida: Optional[str] = None
    partida_arancelaria: Optional[str] = None
    stock_minimo: Optional[float] = None
    perecible: Optional[bool] = None
    activo: Optional[bool] = None


class ProductoOut(ProductoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activo: bool
