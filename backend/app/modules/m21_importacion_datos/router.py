from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m21_importacion_datos import schemas, service

router = APIRouter(prefix="/api/importacion-datos", tags=["importacion-datos"])


@router.post("/inventario-inicial/previsualizar", response_model=schemas.CargaPreviewOut, status_code=201)
async def previsualizar_inventario_inicial(
    inventario_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    contenido = await archivo.read()
    try:
        return service.previsualizar(db, inventario_id, archivo.filename, contenido)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/inventario-inicial", response_model=list[schemas.CargaOut])
def listar_cargas(db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.listar_cargas(db)


@router.get("/inventario-inicial/{carga_id}", response_model=schemas.CargaOut)
def obtener_carga(carga_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.obtener_carga(db, carga_id)


@router.post("/inventario-inicial/{carga_id}/confirmar", response_model=schemas.CargaConfirmarOut)
def confirmar_carga(carga_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.confirmar(db, carga_id)


# ---------------------------------------------------------------------
# ETAPA 2: fecha de corte de inventario
# ---------------------------------------------------------------------


@router.put("/{inventario_id}/fecha-corte", response_model=schemas.ConfiguracionCorteInventarioOut)
def configurar_fecha_corte(
    inventario_id: int,
    datos: schemas.ConfiguracionCorteInventarioIn,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.configurar_corte_inventario(db, inventario_id, datos.fecha_corte)


@router.get("/{inventario_id}/fecha-corte", response_model=schemas.ConfiguracionCorteInventarioOut)
def obtener_fecha_corte(
    inventario_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)
):
    return service.obtener_corte_inventario(db, inventario_id)


# ---------------------------------------------------------------------
# ETAPA 2: Compras historico
# ---------------------------------------------------------------------


@router.post("/compras/previsualizar", response_model=schemas.CargaComprasPreviewOut, status_code=201)
async def previsualizar_compras(
    inventario_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    contenido = await archivo.read()
    try:
        return service.previsualizar_compras(db, inventario_id, archivo.filename, contenido)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/compras", response_model=list[schemas.CargaComprasOut])
def listar_cargas_compras(db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.listar_cargas_compras(db)


@router.get("/compras/{carga_id}", response_model=schemas.CargaComprasOut)
def obtener_carga_compras(carga_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.obtener_carga_compras(db, carga_id)


@router.post("/compras/{carga_id}/confirmar", response_model=schemas.CargaComprasConfirmarOut)
def confirmar_carga_compras(carga_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.confirmar_compras(db, carga_id)


# ---------------------------------------------------------------------
# ETAPA 2: Ventas historico
# ---------------------------------------------------------------------


@router.post("/ventas/previsualizar", response_model=schemas.CargaVentasPreviewOut, status_code=201)
async def previsualizar_ventas(
    inventario_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    contenido = await archivo.read()
    try:
        return service.previsualizar_ventas(db, inventario_id, archivo.filename, contenido)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/ventas", response_model=list[schemas.CargaVentasOut])
def listar_cargas_ventas(db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.listar_cargas_ventas(db)


@router.get("/ventas/{carga_id}", response_model=schemas.CargaVentasOut)
def obtener_carga_ventas(carga_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.obtener_carga_ventas(db, carga_id)


@router.post("/ventas/{carga_id}/confirmar", response_model=schemas.CargaVentasConfirmarOut)
def confirmar_carga_ventas(carga_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.confirmar_ventas(db, carga_id)


# ---------------------------------------------------------------------
# ETAPA 3: reemplazo de cargas confirmadas (Inventario Inicial / Compras / Ventas)
# ---------------------------------------------------------------------


def _ip_origen(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get(
    "/inventario-inicial/{carga_id}/reemplazar/validar",
    response_model=schemas.ValidacionReemplazoOut,
)
def validar_reemplazo_inventario_inicial(
    carga_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)
):
    return service.verificar_reemplazo_inventario(db, carga_id)


@router.post(
    "/inventario-inicial/{carga_id}/reemplazar",
    response_model=schemas.ReemplazoOut,
)
async def reemplazar_inventario_inicial(
    carga_id: int,
    request: Request,
    motivo: str = Form(...),
    observaciones: str | None = Form(None),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    contenido = await archivo.read()
    try:
        return service.reemplazar_inventario(
            db, carga_id, archivo.filename, contenido, motivo, observaciones, usuario, _ip_origen(request)
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/compras/{carga_id}/reemplazar/validar",
    response_model=schemas.ValidacionReemplazoOut,
)
def validar_reemplazo_compras(
    carga_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)
):
    return service.verificar_reemplazo_compras(db, carga_id)


@router.post(
    "/compras/{carga_id}/reemplazar",
    response_model=schemas.ReemplazoOut,
)
async def reemplazar_compras_historico(
    carga_id: int,
    request: Request,
    motivo: str = Form(...),
    observaciones: str | None = Form(None),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    contenido = await archivo.read()
    try:
        return service.reemplazar_compras(
            db, carga_id, archivo.filename, contenido, motivo, observaciones, usuario, _ip_origen(request)
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/ventas/{carga_id}/reemplazar/validar",
    response_model=schemas.ValidacionReemplazoOut,
)
def validar_reemplazo_ventas(
    carga_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)
):
    return service.verificar_reemplazo_ventas(db, carga_id)


@router.post(
    "/ventas/{carga_id}/reemplazar",
    response_model=schemas.ReemplazoOut,
)
async def reemplazar_ventas_historico(
    carga_id: int,
    request: Request,
    motivo: str = Form(...),
    observaciones: str | None = Form(None),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_actual),
):
    contenido = await archivo.read()
    try:
        return service.reemplazar_ventas(
            db, carga_id, archivo.filename, contenido, motivo, observaciones, usuario, _ip_origen(request)
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/reemplazos/bitacora",
    response_model=list[schemas.BitacoraReemplazoOut],
)
def listar_bitacora_reemplazos(
    tipo_carga: str | None = None,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.listar_bitacora_reemplazos(db, tipo_carga)
