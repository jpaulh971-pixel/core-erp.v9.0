"""Reglas y validaciones de negocio del modulo m07_operacion_logistica."""
from fastapi import HTTPException, status

TRANSICIONES_VALIDAS = {
    "RECEPCION": {"INSPECCION"},
    "INSPECCION": {"UBICACION"},
    "UBICACION": {"DISPONIBLE"},
    "DISPONIBLE": {"RESERVADO"},
    "RESERVADO": {"PICKING"},
    "PICKING": {"PACKING"},
    "PACKING": {"CARGA"},
    "CARGA": {"DESPACHO"},
    "DESPACHO": {"ENTREGADO"},
    "ENTREGADO": {"CERRADO"},
    "CERRADO": set(),
}


def validar_operacion_existe(operacion):
    if operacion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Operacion logistica no encontrada"
        )
    return operacion


def validar_transicion(estado_actual: str, estado_destino: str) -> None:
    """No permite saltos ni retrocesos: solo la transicion inmediata
    siguiente en la maquina de estados lineal."""
    permitidos = TRANSICIONES_VALIDAS.get(estado_actual, set())
    if estado_destino not in permitidos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No se puede pasar de {estado_actual} a {estado_destino}. "
                f"Transicion valida desde {estado_actual}: "
                f"{sorted(permitidos) or 'ninguna (estado final)'}"
            ),
        )


def validar_orden_compra_recibida(orden_compra) -> None:
    if orden_compra.estado != "RECIBIDA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La orden de compra #{orden_compra.id} debe estar RECIBIDA "
                f"para referenciarla en una recepcion logistica (esta en "
                f"{orden_compra.estado})."
            ),
        )


def validar_inventario_id_para_recepcion_directa(inventario_id) -> None:
    if inventario_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "inventario_id es obligatorio para una recepcion directa "
                "(sin orden_compra_id): indica en que inventario/almacen "
                "logico ingresa el stock."
            ),
        )


def validar_orden_venta_para_reserva(orden_venta, producto_id: int) -> None:
    if orden_venta.estado != "CONFIRMADA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La orden de venta #{orden_venta.id} debe estar CONFIRMADA "
                f"para reservar stock contra ella (esta en {orden_venta.estado})."
            ),
        )
    if not any(item.producto_id == producto_id for item in orden_venta.items):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La orden de venta #{orden_venta.id} no incluye el "
                f"producto #{producto_id} entre sus items."
            ),
        )


def validar_stock_suficiente_picking(stock_disponible: float, cantidad_requerida: float) -> None:
    if cantidad_requerida > stock_disponible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Stock insuficiente para picking: disponible {stock_disponible}, "
                f"requerido {cantidad_requerida}"
            ),
        )


def validar_hay_lote_disponible(lotes: list) -> None:
    if not lotes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay lotes con stock disponible para hacer picking de este producto.",
        )


def validar_orden_venta_despachada_para_despacho(orden_venta) -> None:
    """Si la operacion esta ligada a una orden de venta, el descuento real
    de inventario lo ejecuta unicamente m10_ventas.despachar_orden -- esta
    validacion solo exige que ya haya ocurrido, para no duplicar esa logica
    aqui (ver service.py)."""
    if orden_venta.estado != "DESPACHADA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La orden de venta #{orden_venta.id} debe estar DESPACHADA "
                f"(via POST /api/ventas/{{id}}/despachar) antes de cerrar el "
                f"despacho logistico de esta operacion (esta en {orden_venta.estado})."
            ),
        )
