from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.m02_productos import service as productos_service
from app.modules.m03_inventario import schemas as inventario_schemas
from app.modules.m03_inventario import service as inventario_service
from app.modules.m06_comercio_exterior import repository, schemas, validators
from app.modules.m06_comercio_exterior.models import (
    DeclaracionExportacion,
    DeclaracionExportacionItem,
)


def crear_declaracion(db: Session, datos: schemas.DeclaracionCrear) -> DeclaracionExportacion:
    validators.validar_incoterm(datos.incoterm)

    for item in datos.items:
        productos_service.obtener_producto(db, item.producto_id)  # valida existencia

    declaracion = DeclaracionExportacion(
        numero_dua=datos.numero_dua,
        cliente_nombre=datos.cliente_nombre,
        pais_destino=datos.pais_destino,
        incoterm=datos.incoterm,
        moneda=datos.moneda,
        observaciones=datos.observaciones,
        inventario_origen_id=datos.inventario_origen_id,
        estado="BORRADOR",
        items=[
            DeclaracionExportacionItem(
                producto_id=item.producto_id,
                cantidad=item.cantidad,
                precio_unitario_exportacion=item.precio_unitario_exportacion,
            )
            for item in datos.items
        ],
    )
    return repository.crear(db, declaracion)


def _referencia_embarque(declaracion_id: int) -> str:
    """Centraliza el string de referencia usado tanto al descontar el kardex
    (embarcar_declaracion) como al leer el costo real consumido
    (_adjuntar_costo_unitario y m08_costos.service.rentabilidad_exportacion).
    Debe coincidir caracter por caracter con el string ya usado en
    m08_costos (no se modifico ese archivo, solo se replica aqui)."""
    return f"Embarque declaracion de exportacion #{declaracion_id}"


def _adjuntar_costo_unitario(
    db: Session, declaracion: DeclaracionExportacion
) -> DeclaracionExportacion:
    """Enriquece los items con el costo unitario real ya calculado por el
    motor de costeo (lectura del kardex FEFO), sin recalcular nada. Solo
    aplica una vez la declaracion fue EMBARCADA, que es cuando existe un
    movimiento de kardex real asociado."""
    if declaracion.estado != "EMBARCADA":
        for item in declaracion.items:
            item.costo_unitario = None
        return declaracion

    costos_por_producto = inventario_service.costo_unitario_por_referencia(
        db, _referencia_embarque(declaracion.id)
    )
    for item in declaracion.items:
        item.costo_unitario = costos_por_producto.get(item.producto_id)
    return declaracion


def obtener_declaracion(db: Session, declaracion_id: int) -> DeclaracionExportacion:
    declaracion = validators.validar_declaracion_existe(
        repository.obtener(db, declaracion_id)
    )
    return _adjuntar_costo_unitario(db, declaracion)


def listar_declaraciones(db: Session, estado: str | None = None) -> list[DeclaracionExportacion]:
    declaraciones = repository.listar(db, estado)
    return [_adjuntar_costo_unitario(db, d) for d in declaraciones]


def confirmar_declaracion(db: Session, declaracion_id: int) -> DeclaracionExportacion:
    """Confirma la declaracion (deja de ser editable) pero todavia NO
    descuenta stock: eso ocurre recien al embarcar, que es cuando la
    mercaderia fisicamente sale del almacen central."""
    declaracion = obtener_declaracion(db, declaracion_id)
    validators.validar_transicion(declaracion.estado, "CONFIRMADA")
    declaracion.estado = "CONFIRMADA"
    declaracion.confirmado_en = datetime.now(timezone.utc)
    return repository.guardar(db, declaracion)


def cancelar_declaracion(db: Session, declaracion_id: int) -> DeclaracionExportacion:
    declaracion = obtener_declaracion(db, declaracion_id)
    validators.validar_transicion(declaracion.estado, "CANCELADA")
    declaracion.estado = "CANCELADA"
    declaracion.cancelado_en = datetime.now(timezone.utc)
    return repository.guardar(db, declaracion)


def embarcar_declaracion(db: Session, declaracion_id: int) -> DeclaracionExportacion:
    """Al embarcar, cada item genera una salida real de inventario por
    FEFO (modulo 03), reutilizando el servicio existente sin duplicar
    logica. Si el stock no alcanza para algun item, la salida de ese
    item falla y la declaracion NO cambia de estado (queda en
    CONFIRMADA para corregir stock o cantidades antes de reintentar)."""
    declaracion = obtener_declaracion(db, declaracion_id)
    validators.validar_transicion(declaracion.estado, "EMBARCADA")

    for item in declaracion.items:
        inventario_service.registrar_salida(
            db,
            inventario_schemas.SalidaInventarioCrear(
                producto_id=item.producto_id,
                inventario_id=declaracion.inventario_origen_id,
                cantidad=float(item.cantidad),
                referencia=_referencia_embarque(declaracion.id),
            ),
        )

    declaracion.estado = "EMBARCADA"
    declaracion.embarcado_en = datetime.now(timezone.utc)
    return repository.guardar(db, declaracion)
