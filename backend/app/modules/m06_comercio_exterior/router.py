from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m06_comercio_exterior import schemas, service

router = APIRouter(prefix="/api/comercio-exterior", tags=["comercio_exterior"])


@router.get("/declaraciones", response_model=list[schemas.DeclaracionOut])
def listar(estado: str | None = None, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.listar_declaraciones(db, estado)


@router.get("/declaraciones/{declaracion_id}", response_model=schemas.DeclaracionOut)
def obtener(declaracion_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.obtener_declaracion(db, declaracion_id)


@router.post("/declaraciones", response_model=schemas.DeclaracionOut, status_code=201)
def crear(datos: schemas.DeclaracionCrear, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.crear_declaracion(db, datos)


@router.post("/declaraciones/{declaracion_id}/confirmar", response_model=schemas.DeclaracionOut)
def confirmar(declaracion_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.confirmar_declaracion(db, declaracion_id)


@router.post("/declaraciones/{declaracion_id}/embarcar", response_model=schemas.DeclaracionOut)
def embarcar(declaracion_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.embarcar_declaracion(db, declaracion_id)


@router.post("/declaraciones/{declaracion_id}/cancelar", response_model=schemas.DeclaracionOut)
def cancelar(declaracion_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.cancelar_declaracion(db, declaracion_id)
