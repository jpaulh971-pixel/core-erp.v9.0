from fastapi import HTTPException, status


def validar_guia_existe(guia):
    if guia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guia de remision no encontrada"
        )
    return guia


def validar_orden_despachada(orden) -> None:
    """La guia desde-venta solo puede generarse sobre una orden que ya
    fue DESPACHADA (es decir, que ya genero salida real de Kardex)."""
    if orden.estado != "DESPACHADA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La orden de venta #{orden.id} esta en estado {orden.estado}; "
                "solo se puede generar una guia de remision desde una orden DESPACHADA."
            ),
        )


def validar_orden_sin_guia_previa(guia_existente) -> None:
    if guia_existente is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Ya existe la guia de remision #{guia_existente.id} "
                f"({guia_existente.numero_guia}) generada para esta orden de venta."
            ),
        )


def validar_trazabilidad_lote(movimientos: list, item) -> None:
    """Regla obligatoria: si no existe movimiento de Kardex SALIDA con
    lote_id para un item despachado, se registra un error de
    trazabilidad. Nunca se inventa un lote."""
    if not movimientos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Error de trazabilidad: no se encontro movimiento de Kardex de SALIDA "
                f"con lote real para el producto_id={item.producto_id} de esta orden de venta. "
                "No se puede generar la guia de remision sin un lote trazable."
            ),
        )


def validar_cantidad_coincide_con_despacho(item, total_kardex: float) -> None:
    """La suma de las salidas de Kardex trazadas para este item debe
    coincidir con lo despachado; si no coincide, es un error de
    trazabilidad y no se genera la guia."""
    if abs(float(item.cantidad) - total_kardex) > 1e-6:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Error de trazabilidad: la cantidad despachada segun Kardex "
                f"({total_kardex}) no coincide con la cantidad del item de venta "
                f"({float(item.cantidad)}) para producto_id={item.producto_id}."
            ),
        )
