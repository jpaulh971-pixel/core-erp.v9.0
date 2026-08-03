from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m20_configuracion import repository, schemas, service
from app.modules.m20_configuracion.models import Usuario

router = APIRouter(tags=["configuracion"])

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.post("/login", response_model=schemas.TokenResponse)
def login(datos: schemas.LoginRequest, db: Session = Depends(get_db)):
    token = service.autenticar(db, datos.username, datos.password)
    return schemas.TokenResponse(access_token=token)


@auth_router.get("/me", response_model=schemas.UsuarioOut)
def me(usuario: Usuario = Depends(get_usuario_actual)):
    return usuario


@router.get("/api/configuracion/parametros", response_model=list[schemas.ParametroOut])
def parametros(db: Session = Depends(get_db), _u: Usuario = Depends(get_usuario_actual)):
    return repository.listar_parametros(db)


@router.get("/api/configuracion/status")
def status():
    return {"modulo": "m20_configuracion", "estado": "implementado"}
