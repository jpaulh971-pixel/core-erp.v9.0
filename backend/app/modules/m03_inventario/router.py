from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m03_inventario import repository, schemas, service

router = APIRouter(prefix="/api/inventario", tags=["inventario"])


# --- Inventarios ---

@router.get("/inventarios", response_model=list[schemas.InventarioOut])
def listar_inventarios(db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.listar_inventarios(db)


@router.post("/inventarios", response_model=schemas.InventarioOut, status_code=201)
def crear_inventario(
    datos: schemas.InventarioCrear, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)
):
    return service.crear_inventario(db, datos)


@router.get("/inventarios/{inventario_id}", response_model=schemas.InventarioOut)
def obtener_inventario(
    inventario_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)
):
    return service.obtener_inventario(db, inventario_id)


# --- Productos por inventario ---

@router.get(
    "/inventarios/{inventario_id}/productos",
    response_model=list[schemas.ProductoInventarioOut],
)
def productos_del_inventario(
    inventario_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)
):
    return service.listar_productos_por_inventario(db, inventario_id)


@router.post("/productos-inventario", response_model=schemas.ProductoInventarioOut, status_code=201)
def crear_producto_inventario(
    datos: schemas.ProductoInventarioCrear,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.obtener_o_crear_producto_inventario(
        db,
        producto_id=datos.producto_id,
        inventario_id=datos.inventario_id,
        codigo_interno=datos.codigo_interno,
        familia=datos.familia,
        presentacion=datos.presentacion,
        litros_presentacion=datos.litros_presentacion,
        marca=datos.marca,
    )


# --- Movimientos ---

@router.post("/ingresos", response_model=schemas.MovimientoKardexOut, status_code=201)
def ingreso(
    datos: schemas.IngresoInventarioCrear,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.registrar_ingreso(db, datos)


@router.post("/salidas", response_model=list[schemas.MovimientoKardexOut], status_code=201)
def salida(
    datos: schemas.SalidaInventarioCrear,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.registrar_salida(db, datos)


@router.post("/ajustes", response_model=schemas.MovimientoKardexOut, status_code=201)
def ajuste(
    datos: schemas.AjusteInventarioCrear,
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.registrar_ajuste(db, datos)


@router.get("/kardex/{producto_inventario_id}", response_model=list[schemas.MovimientoKardexOut])
def kardex(
    producto_inventario_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)
):
    return service.kardex_producto_inventario(db, producto_inventario_id)


@router.get("/saldos/{inventario_id}", response_model=list[schemas.SaldoProductoOut])
def saldos(inventario_id: int, db: Session = Depends(get_db), _u=Depends(get_usuario_actual)):
    return service.saldos(db, inventario_id)
