"""Modulo 17 - Guias de Remision: logica de negocio.

Regla de oro de este modulo (no negociable): una Guia de Remision SOLO
LEE informacion que Ventas (m10) e Inventario (m03) ya generaron. Este
service:
  - NO crea Lote.
  - NO crea ni modifica MovimientoKardex.
  - NO modifica cantidad_actual de ningun Lote.
  - NO modifica el estado de la OrdenVenta.

Lo unico que este modulo escribe es su propia tabla (guias_remision /
guias_remision_detalle).
"""
from sqlalchemy.orm import Session

from app.modules.m02_productos import service as productos_service
from app.modules.m03_inventario import repository as inventario_repository
from app.modules.m03_inventario import service as inventario_service
from app.modules.m10_ventas import service as ventas_service
from app.modules.m11_clientes import service as clientes_service
from app.modules.m17_guias_remision import repository, schemas, validators
from app.modules.m17_guias_remision.models import GuiaRemision, GuiaRemisionDetalle


def _generar_numero_guia(db: Session) -> str:
    correlativo = repository.contar_guias(db) + 1
    return f"GR-{correlativo:06d}"


def _referencia_despacho(orden_venta_id: int) -> str:
    """Referencia de kardex a nivel de DOCUMENTO. Ya no es la que
    m10_ventas.service.despachar_orden usa para escribir en el Kardex
    (desde el fix de trazabilidad de costo por linea, ver
    m10_ventas/service.py, escribe a nivel de item con
    _referencia_despacho_item). Se conserva solo como fallback de
    compatibilidad para leer el Kardex de ordenes que fueron despachadas
    ANTES de ese fix."""
    return f"Despacho orden de venta #{orden_venta_id}"


def _referencia_despacho_item(orden_venta_id: int, item_id: int) -> str:
    """Debe coincidir EXACTO con la referencia a nivel de LINEA que
    m10_ventas.service.despachar_orden escribe en el Kardex (ver
    m10_ventas/service.py: _referencia_despacho_item)."""
    return f"{_referencia_despacho(orden_venta_id)} item #{item_id}"


# --- Creacion manual ---

def crear_guia(db: Session, datos: schemas.GuiaRemisionCrear) -> GuiaRemision:
    clientes_service.obtener_cliente(db, datos.cliente_id)  # valida existencia
    inventario_service.obtener_inventario(db, datos.inventario_id)  # valida existencia

    detalles: list[GuiaRemisionDetalle] = []
    for detalle in datos.detalles:
        productos_service.obtener_producto(db, detalle.producto_id)  # valida existencia
        lote = inventario_repository.obtener_lote(db, detalle.lote_id)
        if lote is None:
            validators.validar_trazabilidad_lote([], detalle)
        detalles.append(
            GuiaRemisionDetalle(
                producto_id=detalle.producto_id,
                lote_id=detalle.lote_id,
                cantidad=detalle.cantidad,
                unidad_medida=detalle.unidad_medida,
            )
        )

    guia = GuiaRemision(
        numero_guia=datos.numero_guia or _generar_numero_guia(db),
        cliente_id=datos.cliente_id,
        inventario_id=datos.inventario_id,
        motivo_traslado=datos.motivo_traslado,
        orden_venta_id=None,
        detalles=detalles,
    )
    return repository.crear_guia(db, guia)


# --- Creacion automatica desde una venta ya despachada ---

def crear_desde_orden_venta(
    db: Session, orden_venta_id: int, datos: schemas.GuiaDesdeVentaCrear
) -> GuiaRemision:
    orden = ventas_service.obtener_orden(db, orden_venta_id)  # 404 si no existe
    validators.validar_orden_despachada(orden)
    validators.validar_orden_sin_guia_previa(
        repository.obtener_guia_por_orden_venta(db, orden_venta_id)
    )

    referencia_documento = _referencia_despacho(orden.id)
    detalles: list[GuiaRemisionDetalle] = []

    for item in orden.items:
        producto_inventario = inventario_repository.obtener_producto_inventario(
            db, item.producto_id, orden.inventario_salida_id
        )
        movimientos: list = []
        if producto_inventario is not None:
            # Primero, referencia a nivel de LINEA (comportamiento desde
            # el fix de trazabilidad de costo por item en m10_ventas):
            # aisla los movimientos de ESTE item, incluso si la orden
            # repite el mismo producto en otra linea.
            movimientos = repository.movimientos_salida_por_referencia(
                db, producto_inventario.id, _referencia_despacho_item(orden.id, item.id)
            )
            if not movimientos:
                # Fallback: ordenes despachadas ANTES del fix, cuyo
                # kardex quedo grabado con la referencia antigua a nivel
                # de documento completo.
                movimientos = repository.movimientos_salida_por_referencia(
                    db, producto_inventario.id, referencia_documento
                )
        validators.validar_trazabilidad_lote(movimientos, item)

        total_kardex = sum(float(m.cantidad) for m in movimientos)
        validators.validar_cantidad_coincide_con_despacho(item, total_kardex)

        for movimiento in movimientos:
            detalles.append(
                GuiaRemisionDetalle(
                    producto_id=item.producto_id,
                    lote_id=movimiento.lote_id,  # lote REAL usado por FEFO en el Kardex
                    cantidad=movimiento.cantidad,
                    unidad_medida=item.producto.unidad_medida,
                )
            )

    guia = GuiaRemision(
        numero_guia=datos.numero_guia or _generar_numero_guia(db),
        cliente_id=orden.cliente_id,
        inventario_id=orden.inventario_salida_id,
        orden_venta_id=orden.id,
        motivo_traslado=datos.motivo_traslado,
        detalles=detalles,
    )
    return repository.crear_guia(db, guia)


def obtener_guia(db: Session, guia_id: int) -> GuiaRemision:
    return validators.validar_guia_existe(repository.obtener_guia(db, guia_id))


def listar_guias(db: Session, estado: str | None = None) -> list[GuiaRemision]:
    return repository.listar_guias(db, estado)
