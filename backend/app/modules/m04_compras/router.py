from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m04_compras import importacion_schemas, importacion_service, schemas, service

router = APIRouter(prefix="/api/compras", tags=["compras"])


@router.get("", response_model=list[schemas.OrdenCompraOut])
def listar(estado: str | None = None, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.listar_ordenes(db, estado)


@router.get("/{orden_id}", response_model=schemas.OrdenCompraOut)
def obtener(orden_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.obtener_orden(db, orden_id)


@router.post("", response_model=schemas.OrdenCompraOut, status_code=201)
def crear(datos: schemas.OrdenCompraCrear, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.crear_orden(db, datos)


@router.post("/{orden_id}/aprobar", response_model=schemas.OrdenCompraOut)
def aprobar(orden_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.aprobar_orden(db, orden_id)


@router.post("/{orden_id}/recibir", response_model=schemas.OrdenCompraOut)
def recibir(orden_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.recibir_orden(db, orden_id)


@router.post("/{orden_id}/cancelar", response_model=schemas.OrdenCompraOut)
def cancelar(orden_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.cancelar_orden(db, orden_id)


# ---------------------------------------------------------------------
# Fase 9 — Importacion masiva de Compras Nacionalizadas desde Excel.
# Dos pasos, sin persistir una "carga" en base de datos: previsualizar()
# nunca escribe; confirmar() vuelve a validar el mismo archivo y recien
# ahi ejecuta crear_orden -> aprobar_orden -> recibir_orden por cada
# "Orden Compra" del Excel (ver importacion_service.py).
# ---------------------------------------------------------------------


@router.post("/importar/previsualizar", response_model=importacion_schemas.PreviewImportacionComprasOut)
async def importar_previsualizar(
    inventario_destino_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    contenido = await archivo.read()
    try:
        return importacion_service.previsualizar(db, inventario_destino_id, archivo.filename, contenido)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/importar/confirmar", response_model=importacion_schemas.ConfirmarImportacionComprasOut)
async def importar_confirmar(
    inventario_destino_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    contenido = await archivo.read()
    try:
        return importacion_service.confirmar(db, inventario_destino_id, archivo.filename, contenido)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
