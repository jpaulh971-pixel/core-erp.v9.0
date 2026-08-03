from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProveedorBase(BaseModel):
    ruc: str = Field(min_length=1, max_length=20)
    razon_social: str = Field(min_length=1, max_length=200)
    contacto: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    pais: Optional[str] = None


class ProveedorCrear(ProveedorBase):
    pass


class ProveedorActualizar(BaseModel):
    razon_social: Optional[str] = None
    contacto: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    pais: Optional[str] = None
    activo: Optional[bool] = None


class ProveedorOut(ProveedorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activo: bool
