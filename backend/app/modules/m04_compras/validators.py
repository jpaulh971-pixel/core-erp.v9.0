from fastapi import HTTPException, status

TRANSICIONES_VALIDAS = {
    "SOLICITADA": {"APROBADA", "CANCELADA"},
    "APROBADA": {"RECIBIDA", "CANCELADA"},
    "RECIBIDA": set(),
    "CANCELADA": set(),
}


def validar_orden_existe(orden):
    if orden is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Orden de compra no encontrada"
        )
    return orden


def validar_transicion(estado_actual: str, estado_destino: str) -> None:
    permitidos = TRANSICIONES_VALIDAS.get(estado_actual, set())
    if estado_destino not in permitidos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No se puede pasar de {estado_actual} a {estado_destino}. "
                f"Transiciones validas desde {estado_actual}: {sorted(permitidos) or 'ninguna'}"
            ),
        )
