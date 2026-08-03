from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.m02_productos import service as productos_service
from app.modules.m03_inventario import schemas as inventario_schemas
from app.modules.m03_inventario import service as inventario_service
from app.modules.m10_ventas import repository, schemas, validators
from app.modules.m10_ventas.models import OrdenVenta, OrdenVentaItem
from app.modules.m11_clientes import service as clientes_service
from app.modules.m11_clientes import validators as clientes_validators


# =======================================================================
# FASE 1 (transacciones atomicas compras/ventas): mismo patron ya
# existente y probado en m21_importacion_datos._transaccion_atomica y
# en m04_compras._transaccion_atomica, reutilizado tal cual (sin
# inventar una arquitectura nueva).
# =======================================================================
@contextmanager
def _transaccion_atomica(db: Session):
    """Unica transaccion SQLAlchemy real para despachar_orden (todos los
    items o ninguno).

    El resto del modulo (y de m03, que reutilizamos tal cual) sigue el
    patron "eager commit" ya existente: cada funcion de repository hace
    su propio db.add()+db.commit()+db.refresh(). Eso es perfecto para su
    uso normal, pero si un item falla a mitad del loop (p.ej. stock
    insuficiente), cada commit() intermedio ya habria dejado grabadas en
    Kardex las salidas de los items anteriores, descontando stock de
    forma parcial mientras la orden queda colgada en un estado
    inconsistente.

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


def _referencia_despacho(orden_id: int) -> str:
    return f"Despacho orden de venta #{orden_id}"


def _referencia_despacho_item(orden_id: int, item_id: int) -> str:
    """Referencia de kardex a nivel de LINEA de la orden (no de todo el
    documento). Se usa para que cada item conserve su propio costo real
    cuando la orden repite el mismo producto en varias lineas que
    terminan consumiendo lotes/costos distintos (PEPS/FEFO). Sigue
    empezando con el mismo prefijo que _referencia_despacho() a
    proposito: el reporte agregado de m19_reportes (ventas_por_producto)
    sigue filtrando por LIKE 'Despacho orden de venta%' y no necesita
    ningun cambio."""
    return f"{_referencia_despacho(orden_id)} item #{item_id}"


def _adjuntar_costo_unitario(db: Session, orden: OrdenVenta) -> OrdenVenta:
    """Adjunta a cada item (solo para lectura/visualizacion) el costo
    unitario REAL que el kardex registro para ESA linea especifica al
    despacharse (m03, FEFO), leyendo por la referencia de kardex propia
    de cada item (_referencia_despacho_item). Esto evita que dos lineas
    del mismo producto que consumieron lotes distintos muestren un
    promedio mezclado del documento completo.

    Fallback de compatibilidad: si una orden fue despachada ANTES de
    este fix, su kardex quedo grabado con la referencia antigua a nivel
    de documento (_referencia_despacho, sin '#item'). Para esas ordenes
    ya historicas, se usa el promedio por producto+documento que ya
    exponia costo_unitario_por_referencia() (comportamiento previo, sin
    desglose por linea) en vez de dejar el costo en None.

    No modifica el estado ni los precios de la orden; si la orden aun no
    fue despachada, cada item queda con costo_unitario=None porque el
    costo real recien se conoce en ese momento."""
    if orden.estado != "DESPACHADA":
        for item in orden.items:
            item.costo_unitario = None
        return orden

    referencias_item = [_referencia_despacho_item(orden.id, item.id) for item in orden.items]
    costos_por_item = inventario_service.costo_unitario_por_referencias(db, referencias_item)

    costos_por_producto_doc: dict[int, float] = {}
    if any(costos_por_item.get(ref) is None for ref in referencias_item):
        costos_por_producto_doc = inventario_service.costo_unitario_por_referencia(
            db, _referencia_despacho(orden.id)
        )

    for item, ref in zip(orden.items, referencias_item):
        costo = costos_por_item.get(ref)
        if costo is None:
            costo = costos_por_producto_doc.get(item.producto_id)
        item.costo_unitario = costo
    return orden


def crear_orden(db: Session, datos: schemas.OrdenVentaCrear) -> OrdenVenta:
    cliente = clientes_service.obtener_cliente(db, datos.cliente_id)  # valida existencia
    clientes_validators.validar_cliente_activo(cliente)

    for item in datos.items:
        productos_service.obtener_producto(db, item.producto_id)  # valida existencia

    inventario_service.obtener_inventario(db, datos.inventario_salida_id)  # valida existencia

    orden = OrdenVenta(
        cliente_id=datos.cliente_id,
        inventario_salida_id=datos.inventario_salida_id,
        moneda=datos.moneda,
        observaciones=datos.observaciones,
        estado="BORRADOR",
        numero_orden_externo=datos.numero_orden_externo,
        vendedor=datos.vendedor,
        factura=datos.factura,
        guia_remision=datos.guia_remision,
        fecha_emision=datos.fecha_emision,
        dias_credito=datos.dias_credito,
        fecha_vencimiento=datos.fecha_vencimiento,
        estado_documento=datos.estado_documento,
        ruc_cliente=datos.ruc_cliente,
        anio=datos.anio,
        meses=datos.meses,
        cultivo=datos.cultivo,
        fundo=datos.fundo,
        items=[
            OrdenVentaItem(
                producto_id=item.producto_id,
                cantidad=item.cantidad,
                precio_unitario_venta=item.precio_unitario_venta,
                unidad_medida=item.unidad_medida,
                descripcion=item.descripcion,
                sub_total=item.sub_total,
                igv=item.igv,
                total=item.total,
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
    return repository.crear(db, orden)


def obtener_orden(db: Session, orden_id: int) -> OrdenVenta:
    orden = validators.validar_orden_existe(repository.obtener(db, orden_id))
    return _adjuntar_costo_unitario(db, orden)


def listar_ordenes(db: Session, estado: str | None = None) -> list[OrdenVenta]:
    ordenes = repository.listar(db, estado)
    return [_adjuntar_costo_unitario(db, orden) for orden in ordenes]


def confirmar_orden(db: Session, orden_id: int, fecha_movimiento: datetime | None = None) -> OrdenVenta:
    """Confirma la orden (deja de ser editable) pero todavia NO descuenta
    stock: eso ocurre recien al despachar, que es cuando la mercaderia
    fisicamente sale del almacen central."""
    orden = obtener_orden(db, orden_id)
    validators.validar_transicion(orden.estado, "CONFIRMADA")
    orden.estado = "CONFIRMADA"
    # Paso 2 (carga historica): con fecha_movimiento informada,
    # confirmado_en queda en la fecha real del documento en vez de la
    # fecha de carga. Sin ella (flujo manual normal), comportamiento
    # identico al de antes.
    orden.confirmado_en = fecha_movimiento or datetime.now(timezone.utc)
    return repository.guardar(db, orden)


def cancelar_orden(db: Session, orden_id: int) -> OrdenVenta:
    orden = obtener_orden(db, orden_id)
    validators.validar_transicion(orden.estado, "CANCELADA")
    orden.estado = "CANCELADA"
    orden.cancelado_en = datetime.now(timezone.utc)
    return repository.guardar(db, orden)


def despachar_orden(db: Session, orden_id: int, fecha_movimiento: datetime | None = None) -> OrdenVenta:
    """Al despachar, cada item genera una salida real de inventario por
    FEFO (modulo 03), reutilizando el servicio existente sin duplicar
    logica -- mismo patron que el embarque de Comercio Exterior. Si el
    stock no alcanza para algun item, la salida de ese item falla y toda
    la orden hace ROLLBACK (ver FASE 1 abajo): la orden NO cambia de
    estado y queda en CONFIRMADA para corregir stock o cantidades antes
    de reintentar.

    Paso 2 (carga historica): si se informa fecha_movimiento, tanto
    despachado_en de la orden como el kardex que genera m03 quedan con
    esa fecha real (y el FEFO evalua vencimiento contra ella), en vez de
    la fecha en que corre el proceso de carga. Sin fecha_movimiento
    (flujo manual normal), comportamiento identico al de antes.

    FASE 1 (atomicidad): el loop de items y el cambio de estado a
    DESPACHADA corren dentro de _transaccion_atomica (mismo patron que
    m21_importacion_datos y m04_compras). Antes de este fix, si un item
    fallaba a mitad del loop (p.ej. item 2 de 3 sin stock), los items
    anteriores ya habian quedado grabados en Kardex con descuento real
    de stock, aunque la orden entera no avanzara de estado. Ahora, ante
    cualquier fallo, se hace ROLLBACK completo: tampoco los items
    anteriores quedan grabados, y no hay descuentos parciales de
    inventario.
    """
    orden = obtener_orden(db, orden_id)
    validators.validar_transicion(orden.estado, "DESPACHADA")

    with _transaccion_atomica(db):
        for item in orden.items:
            inventario_service.registrar_salida(
                db,
                inventario_schemas.SalidaInventarioCrear(
                    producto_id=item.producto_id,
                    inventario_id=orden.inventario_salida_id,
                    cantidad=float(item.cantidad),
                    referencia=_referencia_despacho_item(orden.id, item.id),
                    fecha_movimiento=fecha_movimiento,
                ),
            )

        orden.estado = "DESPACHADA"
        orden.despachado_en = fecha_movimiento or datetime.now(timezone.utc)
        orden = repository.guardar(db, orden)

    return orden
