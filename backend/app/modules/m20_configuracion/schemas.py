from typing import Optional

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nombre_completo: str
    rol: str
    activo: bool


class ParametroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    clave: str
    valor: str
    descripcion: Optional[str] = None
