from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.m10_ventas import service as ventas_service
from app.modules.m12_sunat import repository, schemas, validators
from app.modules.m12_sunat.models import (
    SERIES_POR_TIPO,
    TASA_IGV,
    ComprobanteElectronico,
)


def emitir_comprobante(db: Session, datos: schemas.ComprobanteCrear) -> ComprobanteElectronico:
    validators.validar_tipo_comprobante(datos.tipo_comprobante)

    orden = ventas_service.obtener_orden(db, datos.orden_venta_id)
    validators.validar_orden_despachada(orden)
    validators.validar_no_duplicado(repository.obtener_por_orden(db, orden.id))

    cliente = orden.cliente
    validators.validar_documento_cliente(datos.tipo_comprobante, cliente.ruc)

    serie = SERIES_POR_TIPO[datos.tipo_comprobante]
    correlativo = repository.ultimo_correlativo(db, datos.tipo_comprobante, serie) + 1

    subtotal = sum(float(item.cantidad) * float(item.precio_unitario_venta) for item in orden.items)
    igv = round(subtotal * TASA_IGV, 2)
    total = round(subtotal + igv, 2)

    comprobante = ComprobanteElectronico(
        orden_venta_id=orden.id,
        tipo_comprobante=datos.tipo_comprobante,
        serie=serie,
        correlativo=correlativo,
        cliente_id=cliente.id,
        cliente_ruc=cliente.ruc,
        cliente_razon_social=cliente.razon_social,
        moneda=orden.moneda,
        subtotal=round(subtotal, 2),
        igv=igv,
        total=total,
        estado="EMITIDO",
    )
    return repository.crear(db, comprobante)


def obtener_comprobante(db: Session, comprobante_id: int) -> ComprobanteElectronico:
    return validators.validar_comprobante_existe(repository.obtener(db, comprobante_id))


def obtener_comprobante_por_orden(db: Session, orden_venta_id: int) -> ComprobanteElectronico:
    ventas_service.obtener_orden(db, orden_venta_id)  # valida que la orden exista
    return validators.validar_comprobante_existe(repository.obtener_por_orden(db, orden_venta_id))


def listar_comprobantes(db: Session, estado: str | None = None) -> list[ComprobanteElectronico]:
    return repository.listar(db, estado)


def anular_comprobante(
    db: Session, comprobante_id: int, datos: schemas.AnulacionCrear
) -> ComprobanteElectronico:
    comprobante = obtener_comprobante(db, comprobante_id)
    validators.validar_transicion(comprobante.estado, "ANULADO")
    comprobante.estado = "ANULADO"
    comprobante.motivo_anulacion = datos.motivo
    comprobante.anulado_en = datetime.now(timezone.utc)
    return repository.guardar(db, comprobante)
