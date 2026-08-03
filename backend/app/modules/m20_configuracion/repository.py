from sqlalchemy.orm import Session

from app.modules.m20_configuracion.models import Usuario, ParametroSistema


def obtener_usuario_por_username(db: Session, username: str) -> Usuario | None:
    return db.query(Usuario).filter(Usuario.username == username).first()


def listar_parametros(db: Session) -> list[ParametroSistema]:
    return db.query(ParametroSistema).order_by(ParametroSistema.clave).all()
