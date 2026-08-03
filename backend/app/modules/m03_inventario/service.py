import math
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.modules.m02_productos import service as productos_service
from app.modules.m03_inventario import repository, schemas, validators
from app.modules.m03_inventario.models import Inventario, Lote, MovimientoKardex, ProductoInventario


# --- FASE 1: seguridad operativa perecibles ---

def calcular_estado_lote(lote: Lote, ahora: datetime | None = None) -> str:
    """Calcula el estado REAL de un lote en el momento en que se llama,
    a partir de cantidad_actual y fecha_vencimiento. No depende de que
    Lote.estado ya haya sido sincronizado (por eso el bloqueo de
    vencidos en validators.validar_lote_no_vencido tampoco usa este
    resultado: compara la fecha directamente).

    BLOQUEADO es la unica excepcion: es un estado manual (no hay
    pantalla/endpoint en esta fase para asignarlo) y si ya esta puesto
    se respeta tal cual, no se pisa con un recalculo automatico.
    """
    if lote.estado == "BLOQUEADO":
        return "BLOQUEADO"

    if float(lote.cantidad_actual) <= 0:
        return "AGOTADO"

    if lote.fecha_vencimiento is not None:
        ahora = ahora or datetime.now(timezone.utc)
        venc = lote.fecha_vencimiento
        if venc.tzinfo is None:
            venc = venc.replace(tzinfo=timezone.utc)
        if venc < ahora:
            return "VENCIDO"
        limite_alerta = ahora + timedelta(days=settings.DIAS_ALERTA_VENCIMIENTO)
        if venc <= limite_alerta:
            return "PROXIMO_VENCER"

    return "ACTIVO"



# --- FASE 2: control gerencial (semaforos de solo lectura para reportes) ---
#
# Las dos funciones siguientes son deliberadamente independientes de
# calcular_estado_lote() (arriba). Esa funcion decide el estado
# OPERATIVO real de un lote y alimenta el bloqueo de salidas y el motor
# FEFO, con el umbral configurable settings.DIAS_ALERTA_VENCIMIENTO (30
# dias). Los semaforos de Fase 2 son solo de lectura/reporte gerencial,
# usan los umbrales fijos de negocio pedidos en Fase 2 (90/30 dias para
# vencimiento; stock_minimo +/- margen para stock) y NUNCA participan en
# ninguna decision de bloqueo, FEFO, costeo ni kardex. Se centralizan
# aca (junto a calcular_estado_lote) para que cualquier reporte del
# sistema (m19_reportes u otro) los reutilice sin duplicar la logica.

def calcular_semaforo_vencimiento(
    fecha_vencimiento: datetime | None, ahora: datetime | None = None
) -> tuple[str, int | None]:
    """Clasifica un lote segun su fecha_vencimiento en 4 niveles de
    alerta gerencial. Retorna (semaforo, dias_restantes):

      VERDE    -> mas de 90 dias para vencer (o sin fecha_vencimiento,
                   ej. producto no perecible: no hay riesgo que reportar)
      AMARILLO -> entre 30 y 90 dias (inclusive)
      ROJO     -> menos de 30 dias
      NEGRO    -> ya vencido (dias_restantes queda negativo o cero)

    dias_restantes es None solo cuando no hay fecha_vencimiento.
    """
    if fecha_vencimiento is None:
        return "VERDE", None

    ahora = ahora or datetime.now(timezone.utc)
    venc = fecha_vencimiento
    if venc.tzinfo is None:
        venc = venc.replace(tzinfo=timezone.utc)

    delta_segundos = (venc - ahora).total_seconds()

    if delta_segundos < 0:
        dias_restantes = math.floor(delta_segundos / 86400)
        return "NEGRO", dias_restantes

    dias_restantes = math.ceil(delta_segundos / 86400)
    if dias_restantes < 30:
        return "ROJO", dias_restantes
    if dias_restantes <= 90:
        return "AMARILLO", dias_restantes
    return "VERDE", dias_restantes


def calcular_semaforo_stock(stock_actual: float, stock_minimo: float) -> str:
    """Clasifica el nivel de stock de un producto en 3 niveles, a partir
    de stock_actual y stock_minimo (Producto.stock_minimo, ya existente).

      ROJO     -> stock_actual <= stock_minimo
      AMARILLO -> stock_actual dentro del margen
                   settings.FACTOR_ALERTA_STOCK_CERCANO por encima del
                   minimo (stock cercano al minimo)
      VERDE    -> stock normal, por encima de ese margen

    Si stock_minimo es 0 o no esta definido, se considera que cualquier
    stock positivo es normal (VERDE) y stock en cero es ROJO (no hay
    "minimo" contra el cual medir cercania, asi que no hay nivel
    AMARILLO posible en ese caso).
    """
    if stock_minimo <= 0:
        return "VERDE" if stock_actual > 0 else "ROJO"
    if stock_actual <= stock_minimo:
        return "ROJO"
    if stock_actual <= stock_minimo * settings.FACTOR_ALERTA_STOCK_CERCANO:
        return "AMARILLO"
    return "VERDE"


def _sincronizar_estado(lote: Lote) -> None:
    """Recalcula y deja escrito en el lote su estado actual. Se llama
    despues de cualquier operacion que cambie cantidad_actual (ingreso,
    salida, ajuste) para que la columna Lote.estado no quede
    desactualizada de cara a reportes futuros. El bloqueo de vencidos en
    si NUNCA depende de que esta sincronizacion se haya ejecutado."""
    lote.estado = calcular_estado_lote(lote)


# --- Inventario ---

def crear_inventario(db: Session, datos: schemas.InventarioCrear) -> Inventario:
    validators.validar_codigo_inventario_libre(db, repository, datos.codigo)
    return repository.crear_inventario(db, Inventario(codigo=datos.codigo, nombre=datos.nombre))


def obtener_inventario(db: Session, inventario_id: int) -> Inventario:
    return validators.validar_inventario_existe(repository.obtener_inventario(db, inventario_id))


def listar_inventarios(db: Session) -> list[Inventario]:
    return repository.listar_inventarios(db)


# --- ProductoInventario: obtiene o crea la "presencia" de un producto en un inventario ---

def obtener_o_crear_producto_inventario(
    db: Session,
    producto_id: int,
    inventario_id: int,
    codigo_interno: str | None = None,
    familia: str | None = None,
    presentacion: str | None = None,
    litros_presentacion: float | None = None,
    marca: str | None = None,
) -> ProductoInventario:
    productos_service.obtener_producto(db, producto_id)  # valida existencia
    obtener_inventario(db, inventario_id)  # valida existencia

    existente = repository.obtener_producto_inventario(db, producto_id, inventario_id)
    if existente is not None:
        return existente

    codigo = codigo_interno or f"AUTO-{producto_id}-{inventario_id}"
    pi = ProductoInventario(
        producto_id=producto_id,
        inventario_id=inventario_id,
        codigo_interno=codigo,
        familia=familia,
        presentacion=presentacion,
        litros_presentacion=litros_presentacion,
        marca=marca,
    )
    return repository.crear_producto_inventario(db, pi)


def listar_productos_por_inventario(db: Session, inventario_id: int) -> list[ProductoInventario]:
    obtener_inventario(db, inventario_id)
    return repository.listar_productos_por_inventario(db, inventario_id)


# --- Movimientos ---

def registrar_ingreso(db: Session, datos: schemas.IngresoInventarioCrear) -> MovimientoKardex:
    producto_inventario = obtener_o_crear_producto_inventario(
        db,
        producto_id=datos.producto_id,
        inventario_id=datos.inventario_id,
        codigo_interno=datos.codigo_interno,
        familia=datos.familia,
        presentacion=datos.presentacion,
        litros_presentacion=datos.litros_presentacion,
        marca=datos.marca,
    )

    # FASE 1 (seguridad operativa perecibles): si el producto es
    # perecible, la fecha de vencimiento es obligatoria para crear el
    # lote. Se valida aca -el punto real donde nace todo Lote del
    # sistema- para cubrir de una sola vez compras manuales,
    # importacion Excel y cualquier otro creador futuro.
    validators.validar_vencimiento_obligatorio_si_perecible(
        producto_inventario.producto, datos.fecha_vencimiento
    )

    lote = Lote(
        producto_inventario_id=producto_inventario.id,
        codigo_lote=datos.codigo_lote,
        cantidad_inicial=datos.cantidad,
        cantidad_actual=datos.cantidad,
        costo_unitario=datos.costo_unitario,
        fecha_elaboracion=datos.fecha_elaboracion,
        fecha_vencimiento=datos.fecha_vencimiento,
    )
    # Paso 2 (carga historica): si se informa fecha_movimiento, el lote
    # nace con esa fecha de ingreso real en vez de la fecha en que corre
    # el proceso de carga. Si no se informa (flujo operativo normal), se
    # deja sin tocar para que aplique el server_default=func.now() de
    # siempre.
    if datos.fecha_movimiento is not None:
        lote.fecha_ingreso = datos.fecha_movimiento
    _sincronizar_estado(lote)
    lote = repository.crear_lote(db, lote)

    movimiento = MovimientoKardex(
        producto_inventario_id=producto_inventario.id,
        inventario_id=producto_inventario.inventario_id,
        lote_id=lote.id,
        tipo_movimiento="INGRESO",
        cantidad=datos.cantidad,
        costo_unitario=datos.costo_unitario,
        saldo_resultante=lote.cantidad_actual,
        referencia=datos.referencia,
    )
    if datos.fecha_movimiento is not None:
        movimiento.creado_en = datos.fecha_movimiento
    return repository.registrar_movimiento(db, movimiento)


def registrar_salida(db: Session, datos: schemas.SalidaInventarioCrear) -> list[MovimientoKardex]:
    """Consume stock de un producto DENTRO de un inventario. Si se indica
    lote_id, consume solo de ese lote; si no, FEFO automatico entre los
    lotes de ese producto+inventario. Nunca cruza a otro inventario."""
    producto_inventario = repository.obtener_producto_inventario(
        db, datos.producto_id, datos.inventario_id
    )
    validators.validar_producto_en_inventario(producto_inventario)

    if datos.lote_id is not None:
        lote = validators.validar_lote_existe(repository.obtener_lote(db, datos.lote_id))
        validators.validar_lote_pertenece_a_producto_inventario(lote, producto_inventario.id)
        validators.validar_lote_no_vencido(lote, fecha_referencia=datos.fecha_movimiento)
        validators.validar_lote_no_bloqueado(lote)
        validators.validar_stock_suficiente(float(lote.cantidad_actual), datos.cantidad)
        return [
            _consumir_lote(
                db, lote, datos.cantidad, "SALIDA", datos.referencia, fecha_movimiento=datos.fecha_movimiento
            )
        ]

    # FASE 1 (seguridad operativa perecibles): el stock "disponible" para
    # una salida automatica por FEFO debe contar solo lotes que FEFO
    # realmente puede consumir (no vencidos, no bloqueados). Antes este
    # calculo usaba stock_total_producto_inventario() (todos los lotes,
    # incluidos vencidos), lo que permitia que la validacion de stock
    # pasara pero el bucle FEFO de abajo terminara sin poder completar
    # la cantidad pedida (por excluir los vencidos), dejando una salida
    # a medias sin avisar. Se resuelve el listado FEFO una sola vez y se
    # reutiliza para el chequeo de stock y para el consumo.
    lotes_fefo = repository.lotes_disponibles_fefo(
        db, producto_inventario.id, fecha_referencia=datos.fecha_movimiento
    )
    stock_disponible = sum(float(lote.cantidad_actual) for lote in lotes_fefo)
    validators.validar_stock_suficiente(stock_disponible, datos.cantidad)

    pendiente = datos.cantidad
    movimientos: list[MovimientoKardex] = []
    try:
        for lote in lotes_fefo:
            if pendiente <= 0:
                break
            # Defensa adicional: repository.lotes_disponibles_fefo() ya
            # excluye vencidos/bloqueados por SQL; se revalida aca con la
            # misma funcion central para que el bloqueo nunca dependa de
            # un solo punto de chequeo. Paso 2: misma fecha_referencia
            # que se uso para armar la lista, para no evaluar "vencido"
            # con dos criterios distintos dentro de la misma operacion.
            validators.validar_lote_no_vencido(lote, fecha_referencia=datos.fecha_movimiento)
            validators.validar_lote_no_bloqueado(lote)
            consumo = min(float(lote.cantidad_actual), pendiente)
            lote.cantidad_actual = float(lote.cantidad_actual) - consumo
            _sincronizar_estado(lote)
            db.add(lote)
            db.flush()

            movimiento = MovimientoKardex(
                producto_inventario_id=producto_inventario.id,
                inventario_id=producto_inventario.inventario_id,
                lote_id=lote.id,
                tipo_movimiento="SALIDA",
                cantidad=consumo,
                costo_unitario=lote.costo_unitario,
                saldo_resultante=lote.cantidad_actual,
                referencia=datos.referencia,
            )
            if datos.fecha_movimiento is not None:
                movimiento.creado_en = datos.fecha_movimiento
            db.add(movimiento)
            movimientos.append(movimiento)
            pendiente -= consumo
        db.commit()
    except Exception:
        db.rollback()
        raise

    for movimiento in movimientos:
        db.refresh(movimiento)
    return movimientos


def _consumir_lote(
    db: Session,
    lote: Lote,
    cantidad: float,
    tipo: str,
    referencia: str | None,
    fecha_movimiento: datetime | None = None,
) -> MovimientoKardex:
    lote.cantidad_actual = float(lote.cantidad_actual) - cantidad
    _sincronizar_estado(lote)
    db.add(lote)
    db.flush()
    movimiento = MovimientoKardex(
        producto_inventario_id=lote.producto_inventario_id,
        inventario_id=lote.producto_inventario.inventario_id,
        lote_id=lote.id,
        tipo_movimiento=tipo,
        cantidad=cantidad,
        costo_unitario=lote.costo_unitario,
        saldo_resultante=lote.cantidad_actual,
        referencia=referencia,
    )
    if fecha_movimiento is not None:
        movimiento.creado_en = fecha_movimiento
    return repository.registrar_movimiento(db, movimiento)


def registrar_ajuste(db: Session, datos: schemas.AjusteInventarioCrear) -> MovimientoKardex:
    lote = validators.validar_lote_existe(repository.obtener_lote(db, datos.lote_id))
    validators.validar_ajuste_no_deja_negativo(float(lote.cantidad_actual), datos.cantidad)

    # Nota: los ajustes (positivos o negativos) NO se bloquean para
    # lotes vencidos a proposito: un ajuste negativo es precisamente la
    # forma de dar de baja/destruir stock vencido del inventario.
    lote.cantidad_actual = float(lote.cantidad_actual) + datos.cantidad
    _sincronizar_estado(lote)
    db.add(lote)
    db.commit()
    db.refresh(lote)

    movimiento = MovimientoKardex(
        producto_inventario_id=lote.producto_inventario_id,
        inventario_id=lote.producto_inventario.inventario_id,
        lote_id=lote.id,
        tipo_movimiento="AJUSTE_POSITIVO" if datos.cantidad >= 0 else "AJUSTE_NEGATIVO",
        cantidad=abs(datos.cantidad),
        costo_unitario=lote.costo_unitario,
        saldo_resultante=lote.cantidad_actual,
        referencia=datos.referencia,
    )
    return repository.registrar_movimiento(db, movimiento)


def existe_lote_con_codigo(db: Session, codigo_lote: str) -> bool:
    """Solo lectura. Usado por m04_compras/importacion_service.py para la
    validacion 'No duplicar lotes' antes de escribir nada."""
    return repository.obtener_lote_por_codigo(db, codigo_lote) is not None


def kardex_producto_inventario(db: Session, producto_inventario_id: int) -> list[MovimientoKardex]:
    validators.validar_producto_en_inventario(
        repository.obtener_producto_inventario_por_id(db, producto_inventario_id)
    )
    return repository.kardex_por_producto_inventario(db, producto_inventario_id)


def saldos(db: Session, inventario_id: int) -> list[dict]:
    obtener_inventario(db, inventario_id)
    filas = repository.saldos_por_inventario(db, inventario_id)
    # FASE 2 (control gerencial): se agrega el semaforo de stock a cada
    # fila, calculado por la funcion centralizada calcular_semaforo_stock
    # a partir de los mismos stock_total/stock_minimo que el reporte ya
    # traia. No se toca ningun campo existente de la fila.
    for fila in filas:
        fila["semaforo_stock"] = calcular_semaforo_stock(fila["stock_total"], fila["stock_minimo"])
    return filas


def costo_unitario_por_referencia(db: Session, referencia: str) -> dict[int, float]:
    """Expone (solo lectura) el costo unitario promedio ya registrado en
    el kardex para una referencia de documento dada (ej. despacho de una
    orden de venta o embarque de una declaracion de exportacion). Otros
    modulos (Ventas, Comercio Exterior) reutilizan esta funcion para
    mostrar el Costo Unitario sin duplicar la consulta al kardex ni
    recalcular costeo propio."""
    return repository.costo_unitario_por_referencia(db, referencia)


def costo_unitario_por_referencias(db: Session, referencias: list[str]) -> dict[str, float]:
    """Expone (solo lectura) el costo unitario promedio ya registrado en
    el kardex, agrupado por referencia EXACTA en vez de por producto_id.
    Pensada para referencias a nivel de item/linea de un documento (ej.
    Ventas: 'Despacho orden de venta #<id> item #<item_id>'), de forma
    que cada linea conserve su propio costo real aunque el documento
    repita el mismo producto en varias lineas con lotes distintos. Ver
    repository.costo_unitario_por_referencias()."""
    return repository.costo_unitario_por_referencias(db, referencias)
