"""Logica de negocio del modulo m07_operacion_logistica.

Trazabilidad fisica de la mercaderia dentro del almacen central sobre la
maquina de estados lineal RECEPCION -> INSPECCION -> UBICACION ->
DISPONIBLE -> RESERVADO -> PICKING -> PACKING -> CARGA -> DESPACHO ->
ENTREGADO -> CERRADO (sin saltos, sin retrocesos -- ver validators.py).

Reglas de integracion para no duplicar tablas ni logica de negocio:

- Recepcion: si se referencia una Orden de Compra ya RECIBIDA, el ingreso
  de stock (lote + kardex) ya lo hizo m04_compras.recibir_orden -- esta
  operacion NO vuelve a ingresar stock, solo registra el seguimiento
  fisico. Si no se referencia orden de compra, esta operacion SI ejecuta
  el ingreso real via m03_inventario (importacion / recepcion directa).
- Picking: identifica en solo lectura (FEFO, o FIFO si no hay
  vencimiento) el lote que fisicamente se va a picking y registra cual
  fue y cuanto, reutilizando el mismo criterio de m03_inventario. NO
  descuenta stock aqui.
- Despacho: el descuento real de inventario (salida FEFO + movimiento de
  Kardex) lo ejecuta unicamente m10_ventas.despachar_orden. Esta
  operacion solo valida que la orden de venta asociada ya este
  DESPACHADA antes de avanzar, para no duplicar ese descuento.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.m02_productos import service as productos_service
from app.modules.m03_inventario import repository as inventario_repository
from app.modules.m03_inventario import schemas as inventario_schemas
from app.modules.m03_inventario import service as inventario_service
from app.modules.m04_compras import service as compras_service
from app.modules.m05_proveedores import service as proveedores_service
from app.modules.m07_operacion_logistica import repository, schemas, validators
from app.modules.m07_operacion_logistica.models import OperacionLogistica
from app.modules.m10_ventas import service as ventas_service
from app.modules.m20_configuracion.models import Usuario


def _avanzar_estado(
    db: Session,
    operacion: OperacionLogistica,
    estado_nuevo: str,
    campo_timestamp: str,
    usuario: Usuario,
    observaciones: str | None,
) -> OperacionLogistica:
    """Valida la transicion, marca el nuevo estado + su timestamp de etapa
    y deja constancia en el historial de auditoria. Punto unico de avance
    de estado para que ninguna transicion se salte esta secuencia."""
    validators.validar_transicion(operacion.estado, estado_nuevo)
    estado_anterior = operacion.estado
    operacion.estado = estado_nuevo
    setattr(operacion, campo_timestamp, datetime.now(timezone.utc))
    operacion = repository.guardar(db, operacion)
    repository.registrar_historial(
        db,
        operacion_id=operacion.id,
        usuario_id=usuario.id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        observaciones=observaciones,
    )
    return obtener_operacion(db, operacion.id)


def obtener_operacion(db: Session, operacion_id: int) -> OperacionLogistica:
    return validators.validar_operacion_existe(repository.obtener(db, operacion_id))


def listar_operaciones(db: Session, estado: str | None = None) -> list[OperacionLogistica]:
    return repository.listar(db, estado)


def registrar_recepcion(
    db: Session, datos: schemas.RecepcionCrear, usuario: Usuario
) -> OperacionLogistica:
    productos_service.obtener_producto(db, datos.producto_id)  # valida existencia
    proveedores_service.obtener_proveedor(db, datos.proveedor_id)  # valida existencia

    lote_id = None
    if datos.orden_compra_id is not None:
        orden_compra = compras_service.obtener_orden(db, datos.orden_compra_id)
        validators.validar_orden_compra_recibida(orden_compra)
        # El ingreso real de stock (lote + kardex) ya lo hizo
        # m04_compras.recibir_orden -- no se vuelve a ingresar aqui.
    else:
        # Recepcion directa (p. ej. importacion sin OC formal): esta
        # operacion SI ejecuta el ingreso real, reutilizando el servicio
        # de m03_inventario sin duplicar su logica.
        validators.validar_inventario_id_para_recepcion_directa(datos.inventario_id)
        movimiento = inventario_service.registrar_ingreso(
            db,
            inventario_schemas.IngresoInventarioCrear(
                producto_id=datos.producto_id,
                inventario_id=datos.inventario_id,
                codigo_lote=datos.codigo_lote,
                cantidad=datos.cantidad,
                costo_unitario=datos.costo_unitario,
                fecha_vencimiento=datos.fecha_vencimiento,
                referencia=f"Recepcion logistica directa (proveedor #{datos.proveedor_id})",
            ),
        )
        lote_id = movimiento.lote_id

    operacion = OperacionLogistica(
        producto_id=datos.producto_id,
        proveedor_id=datos.proveedor_id,
        orden_compra_id=datos.orden_compra_id,
        inventario_id=datos.inventario_id,
        lote_id=lote_id,
        codigo_lote=datos.codigo_lote,
        cantidad=datos.cantidad,
        costo_unitario=datos.costo_unitario,
        estado="RECEPCION",
        recepcion_en=datetime.now(timezone.utc),
    )
    operacion = repository.crear(db, operacion)
    repository.registrar_historial(
        db,
        operacion_id=operacion.id,
        usuario_id=usuario.id,
        estado_anterior=None,
        estado_nuevo="RECEPCION",
        observaciones=datos.observaciones,
    )
    return obtener_operacion(db, operacion.id)


def registrar_inspeccion(
    db: Session, operacion_id: int, datos: schemas.InspeccionActualizar, usuario: Usuario
) -> OperacionLogistica:
    operacion = obtener_operacion(db, operacion_id)
    operacion.conforme = datos.conforme
    operacion.observaciones_inspeccion = datos.observaciones
    return _avanzar_estado(
        db, operacion, "INSPECCION", "inspeccion_en", usuario, datos.observaciones
    )


def registrar_ubicacion(
    db: Session, operacion_id: int, datos: schemas.UbicacionActualizar, usuario: Usuario
) -> OperacionLogistica:
    operacion = obtener_operacion(db, operacion_id)
    operacion.rack = datos.rack
    operacion.pasillo = datos.pasillo
    operacion.ubicacion_fisica = datos.ubicacion_fisica
    return _avanzar_estado(
        db, operacion, "UBICACION", "ubicacion_en", usuario, datos.observaciones
    )


def marcar_disponible(
    db: Session, operacion_id: int, datos: schemas.DisponibleActualizar, usuario: Usuario
) -> OperacionLogistica:
    operacion = obtener_operacion(db, operacion_id)
    return _avanzar_estado(
        db, operacion, "DISPONIBLE", "disponible_en", usuario, datos.observaciones
    )


def reservar(
    db: Session, operacion_id: int, datos: schemas.ReservaCrear, usuario: Usuario
) -> OperacionLogistica:
    operacion = obtener_operacion(db, operacion_id)
    orden_venta = ventas_service.obtener_orden(db, datos.orden_venta_id)
    validators.validar_orden_venta_para_reserva(orden_venta, operacion.producto_id)
    operacion.orden_venta_id = datos.orden_venta_id
    return _avanzar_estado(
        db, operacion, "RESERVADO", "reservado_en", usuario, datos.observaciones
    )


def registrar_picking(
    db: Session, operacion_id: int, datos: schemas.PickingActualizar, usuario: Usuario
) -> OperacionLogistica:
    """Identifica en solo lectura el lote que fisicamente se picking (FEFO,
    o FIFO si no hay vencimiento) y deja constancia de cual fue y cuanto.
    No descuenta stock: eso ocurre recien al despachar la orden de venta
    (m10_ventas), que es cuando la mercaderia fisicamente sale del
    almacen central."""
    operacion = obtener_operacion(db, operacion_id)
    validators.validar_stock_suficiente_picking(
        inventario_repository.stock_total_producto(db, operacion.producto_id),
        float(operacion.cantidad),
    )
    lotes_fefo = inventario_repository.lotes_disponibles_fefo(db, operacion.producto_id)
    validators.validar_hay_lote_disponible(lotes_fefo)
    lote_elegido = lotes_fefo[0]

    operacion.lote_picking_id = lote_elegido.id
    operacion.cantidad_picking = operacion.cantidad
    operacion.metodo_consumo = "FEFO" if lote_elegido.fecha_vencimiento is not None else "FIFO"
    return _avanzar_estado(db, operacion, "PICKING", "picking_en", usuario, datos.observaciones)


def registrar_packing(
    db: Session, operacion_id: int, datos: schemas.PackingActualizar, usuario: Usuario
) -> OperacionLogistica:
    operacion = obtener_operacion(db, operacion_id)
    operacion.peso = datos.peso
    operacion.cajas = datos.cajas
    operacion.pallets = datos.pallets
    return _avanzar_estado(db, operacion, "PACKING", "packing_en", usuario, datos.observaciones)


def registrar_carga(
    db: Session, operacion_id: int, datos: schemas.CargaActualizar, usuario: Usuario
) -> OperacionLogistica:
    operacion = obtener_operacion(db, operacion_id)
    operacion.vehiculo = datos.vehiculo
    operacion.conductor = datos.conductor
    operacion.fecha_carga = datos.fecha_carga or datetime.now(timezone.utc)
    return _avanzar_estado(db, operacion, "CARGA", "carga_en", usuario, datos.observaciones)


def registrar_despacho(
    db: Session, operacion_id: int, datos: schemas.DespachoActualizar, usuario: Usuario
) -> OperacionLogistica:
    """No descuenta inventario aqui: exige que la orden de venta asociada
    ya haya sido despachada via m10_ventas.despachar_orden (que es quien
    ejecuta la salida real por FEFO y genera el movimiento de Kardex),
    para no duplicar esa logica."""
    operacion = obtener_operacion(db, operacion_id)
    orden_venta = ventas_service.obtener_orden(db, operacion.orden_venta_id)
    validators.validar_orden_venta_despachada_para_despacho(orden_venta)
    return _avanzar_estado(db, operacion, "DESPACHO", "despacho_en", usuario, datos.observaciones)


def registrar_entrega(
    db: Session, operacion_id: int, datos: schemas.EntregaActualizar, usuario: Usuario
) -> OperacionLogistica:
    operacion = obtener_operacion(db, operacion_id)
    return _avanzar_estado(
        db, operacion, "ENTREGADO", "entregado_en", usuario, datos.observaciones
    )


def cerrar_operacion(
    db: Session, operacion_id: int, datos: schemas.CierreActualizar, usuario: Usuario
) -> OperacionLogistica:
    operacion = obtener_operacion(db, operacion_id)
    return _avanzar_estado(db, operacion, "CERRADO", "cerrado_en", usuario, datos.observaciones)
