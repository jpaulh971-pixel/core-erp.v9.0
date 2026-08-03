from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m10_ventas import importacion_schemas, importacion_service, schemas, service

router = APIRouter(prefix="/api/ventas", tags=["ventas"])


@router.post("", response_model=schemas.OrdenVentaOut, status_code=201)
def crear_orden(
    datos: schemas.OrdenVentaCrear,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.crear_orden(db, datos)


@router.get("", response_model=list[schemas.OrdenVentaOut])
def listar_ordenes(
    estado: str | None = None,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.listar_ordenes(db, estado)


# ---------------------------------------------------------------------
# Fase 10 — Importacion masiva de Ventas desde Excel. Registradas ANTES
# de las rutas "/{orden_id}/..." a proposito: "/importar/confirmar"
# tiene la misma forma de 2 segmentos que "/{orden_id}/confirmar"
# (idem "/importar/previsualizar" no colisiona, pero se mantienen
# juntas por claridad). Si esta seccion se registrara despues,
# "/{orden_id}/confirmar" capturaria primero la ruta con
# orden_id="importar" y el path param fallaria su validacion (int),
# devolviendo 422 en vez de ejecutar la importacion.
#
# Dos pasos, sin persistir una "carga" en base de datos: previsualizar()
# nunca escribe; confirmar() vuelve a validar el mismo archivo y, solo
# si es 100% valido (incluyendo stock agregado), ejecuta crear_orden ->
# confirmar_orden -> despachar_orden por cada "Orden de Venta" del Excel
# (todo-o-nada; ver importacion_service.py).
# ---------------------------------------------------------------------


@router.post("/importar/previsualizar", response_model=importacion_schemas.PreviewImportacionVentasOut)
async def importar_previsualizar(
    inventario_salida_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    contenido = await archivo.read()
    try:
        return importacion_service.previsualizar(db, inventario_salida_id, archivo.filename, contenido)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/importar/confirmar", response_model=importacion_schemas.ConfirmarImportacionVentasOut)
async def importar_confirmar(
    inventario_salida_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    contenido = await archivo.read()
    try:
        return importacion_service.confirmar(db, inventario_salida_id, archivo.filename, contenido)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{orden_id}", response_model=schemas.OrdenVentaOut)
def obtener_orden(
    orden_id: int,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.obtener_orden(db, orden_id)


@router.post("/{orden_id}/confirmar", response_model=schemas.OrdenVentaOut)
def confirmar_orden(
    orden_id: int,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.confirmar_orden(db, orden_id)


@router.post("/{orden_id}/despachar", response_model=schemas.OrdenVentaOut)
def despachar_orden(
    orden_id: int,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.despachar_orden(db, orden_id)


@router.post("/{orden_id}/cancelar", response_model=schemas.OrdenVentaOut)
def cancelar_orden(
    orden_id: int,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.cancelar_orden(db, orden_id)
