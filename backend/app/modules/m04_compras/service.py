from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.modules.m02_productos import service as productos_service
from app.modules.m03_inventario import schemas as inventario_schemas
from app.modules.m03_inventario import service as inventario_service
from app.modules.m04_compras import repository, schemas, validators
from app.modules.m04_compras.models import OrdenCompra, OrdenCompraItem
from app.modules.m05_proveedores import service as proveedores_service


# =======================================================================
# FASE 1 (transacciones atomicas compras/ventas): mismo patron ya
# existente y probado en m21_importacion_datos._transaccion_atomica,
# reutilizado tal cual (sin inventar una arquitectura nueva).
# =======================================================================
@contextmanager
def _transaccion_atomica(db: Session):
    """Unica transaccion SQLAlchemy real para recibir_orden (todos los
    items o ninguno).

    El resto del modulo (y de m03, que reutilizamos tal cual) sigue el
    patron "eager commit" ya existente: cada funcion de repository hace
    su propio db.add()+db.commit()+db.refresh(). Eso es perfecto para su
    uso normal, pero si un item falla a mitad del loop, cada commit()
    intermedio ya habria dejado grabados los items anteriores en Kardex,
    con la orden colgada en un estado inconsistente.

    Para lograr atomicidad real SIN tocar Inventario/Kardex ni ningun
    otro modulo, este context manager reemplaza temporalmente el metodo
    commit() de la sesion por un simple flush(): la fila se ve reflejada
    de inmediato para las siguientes consultas del propio proceso, pero
    fisicamente NO se confirma en disco hasta el commit() real del final
    de este bloque. Si ocurre cualquier excepcion, se hace rollback()
    real -- deshace absolutamente todo lo que paso desde que se entro al
    bloque -- y se relanza la excepcion tal cual para que el llamador
    decida que responder.
    """
    commit_real = db.commit
    db.commit = db.flush
    try:
        yield db
        db.commit = commit_real
        commit_real()
    except Exception:
        db.commit = commit_real
        db.rollback()
        raise


def crear_orden(db: Session, datos: schemas.OrdenCompraCrear) -> OrdenCompra:
    proveedor = proveedores_service.obtener_proveedor(db, datos.proveedor_id)
    from app.modules.m05_proveedores import validators as proveedores_validators

    proveedores_validators.validar_proveedor_activo(proveedor)

    for item in datos.items:
        productos_service.obtener_producto(db, item.producto_id)  # valida existencia

    inventario_service.obtener_inventario(db, datos.inventario_destino_id)  # valida existencia

    # Formato Excel del cliente: si viene "Dias de Credito" pero no una
    # fecha de vencimiento de factura explicita, se calcula automaticamente
    # a partir de la fecha de emision de la factura (fecha_documento). Si
    # ya viene explicita (fecha_vencimiento_factura), se respeta tal cual.
    fecha_vencimiento_factura = datos.fecha_vencimiento_factura
    if fecha_vencimiento_factura is None and datos.fecha_documento is not None and datos.dias_credito is not None:
        fecha_vencimiento_factura = datos.fecha_documento + timedelta(days=datos.dias_credito)

    orden = OrdenCompra(
        proveedor_id=datos.proveedor_id,
        inventario_destino_id=datos.inventario_destino_id,
        moneda=datos.moneda,
        observaciones=datos.observaciones,
        estado="SOLICITADA",
        numero_orden_externo=datos.numero_orden_externo,
        invoice=datos.invoice,
        documento_aduanero=datos.documento_aduanero,
        pais_origen=datos.pais_origen,
        fecha_documento=datos.fecha_documento,
        dias_credito=datos.dias_credito,
        fecha_vencimiento_factura=fecha_vencimiento_factura,
        items=[
            OrdenCompraItem(
                producto_id=item.producto_id,
                cantidad=item.cantidad,
                costo_unitario=item.costo_unitario,
                lote=item.lote,
                fecha_elaboracion=item.fecha_elaboracion,
                fecha_vencimiento=item.fecha_vencimiento,
                observaciones=item.observaciones,
                presentacion=item.presentacion,
                unidad_medida=item.unidad_medida,
                cantidad_por_unidad=item.cantidad_por_unidad,
                concepto=item.concepto,
            )
            for item in datos.items
        ],
    )
    # Paso 2 (carga historica): si se informa fecha_movimiento, la orden
    # nace con esa fecha de creacion real en vez de la fecha en que corre
    # el proceso de carga. Sin fecha_movimiento (flujo manual normal), no
    # se toca el atributo y aplica el server_default=func.now() de siempre.
    if datos.fecha_movimiento is not None:
        orden.creado_en = datos.fecha_movimiento
    return repository.crear_orden(db, orden)


def obtener_orden(db: Session, orden_id: int) -> OrdenCompra:
    return validators.validar_orden_existe(repository.obtener_orden(db, orden_id))


def listar_ordenes(db: Session, estado: str | None = None) -> list[OrdenCompra]:
    return repository.listar_ordenes(db, estado)


def aprobar_orden(db: Session, orden_id: int, fecha_movimiento: datetime | None = None) -> OrdenCompra:
    orden = obtener_orden(db, orden_id)
    validators.validar_transicion(orden.estado, "APROBADA")
    orden.estado = "APROBADA"
    # Paso 2 (carga historica): con fecha_movimiento informada, aprobado_en
    # queda en la fecha real del documento en vez de la fecha de carga.
    # Sin ella (flujo manual normal), comportamiento identico al de antes.
    orden.aprobado_en = fecha_movimiento or datetime.now(timezone.utc)
    return repository.guardar(db, orden)


def cancelar_orden(db: Session, orden_id: int) -> OrdenCompra:
    orden = obtener_orden(db, orden_id)
    validators.validar_transicion(orden.estado, "CANCELADA")
    orden.estado = "CANCELADA"
    orden.cancelado_en = datetime.now(timezone.utc)
    return repository.guardar(db, orden)


def recibir_orden(db: Session, orden_id: int, fecha_movimiento: datetime | None = None) -> OrdenCompra:
    """Al recibir la orden, cada item genera un ingreso real de stock en
    Inventario (nuevo lote + movimiento de kardex), reutilizando el
    servicio del modulo 03 sin duplicar logica.

    Si la orden ya tiene costos adicionales registrados (m08_costos:
    flete, seguro, aduana, etc.), se prorratean sobre el costo_unitario
    de cada item segun su peso en el valor de mercaderia, para que el
    lote/kardex nazca con el costo de aterrizaje y no solo con el costo
    de compra. Si no hay costos adicionales, el factor de prorrateo es
    1.0 y el costo_unitario de cada item queda igual que antes.

    Paso 2 (carga historica): si se informa fecha_movimiento, tanto
    recibido_en de la orden como el lote/kardex que nace en m03 quedan
    con esa fecha real (y la validacion de vencimiento FEFO se evalua
    contra ella), en vez de la fecha en que corre el proceso de carga.
    Sin fecha_movimiento (flujo manual normal), comportamiento identico
    al de antes.

    FASE 1 (atomicidad): el loop de items y el cambio de estado a
    RECIBIDA corren dentro de _transaccion_atomica (mismo patron que
    m21_importacion_datos). Si algun item falla a mitad de la orden, se
    hace ROLLBACK completo: ni los items ya procesados quedan en Kardex,
    ni la orden cambia de estado -- ya no puede quedar "a medias".
    """
    orden = obtener_orden(db, orden_id)
    validators.validar_transicion(orden.estado, "RECIBIDA")

    from app.modules.m08_costos import service as costos_service

    costeo = costos_service.costeo_compra(db, orden.id)
    factor_landed_cost = (
        costeo.costo_total / costeo.valor_mercaderia
        if costeo.valor_mercaderia > 0
        else 1.0
    )

    with _transaccion_atomica(db):
        for item in orden.items:
            # Fase 9 (Importacion de Compras Nacionalizadas): si el item
            # trae lote/fechas propios (import Excel), se usan tal cual.
            # Si no (flujo manual de siempre), el codigo de lote
            # autogenerado y la ausencia de fechas quedan exactamente
            # igual que antes.
            inventario_service.registrar_ingreso(
                db,
                inventario_schemas.IngresoInventarioCrear(
                    producto_id=item.producto_id,
                    inventario_id=orden.inventario_destino_id,
                    codigo_lote=item.lote or f"OC-{orden.id}-P{item.producto_id}",
                    cantidad=float(item.cantidad),
                    costo_unitario=float(item.costo_unitario) * factor_landed_cost,
                    fecha_elaboracion=item.fecha_elaboracion,
                    fecha_vencimiento=item.fecha_vencimiento,
                    referencia=(
                        f"Recepcion orden de compra #{orden.id}"
                        + (f" (Factura {orden.invoice})" if orden.invoice else "")
                    ),
                    fecha_movimiento=fecha_movimiento,
                ),
            )

        orden.estado = "RECIBIDA"
        orden.recibido_en = fecha_movimiento or datetime.now(timezone.utc)
        orden = repository.guardar(db, orden)

    return orden
