from sqlalchemy.orm import Session

from app.security import crear_access_token, verificar_password
from app.modules.m20_configuracion import repository, validators


def autenticar(db: Session, username: str, password: str) -> str:
    usuario = repository.obtener_usuario_por_username(db, username)
    password_valido = bool(usuario) and verificar_password(password, usuario.password_hash)
    validators.validar_credenciales(usuario, password_valido)
    return crear_access_token(subject=usuario.username)
