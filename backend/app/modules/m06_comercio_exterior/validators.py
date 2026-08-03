from fastapi import HTTPException, status

from app.modules.m06_comercio_exterior.models import INCOTERMS_VALIDOS

TRANSICIONES_VALIDAS = {
    "BORRADOR": {"CONFIRMADA", "CANCELADA"},
    "CONFIRMADA": {"EMBARCADA", "CANCELADA"},
    "EMBARCADA": set(),
    "CANCELADA": set(),
}


def validar_declaracion_existe(declaracion):
    if declaracion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Declaracion de exportacion no encontrada"
        )
    return declaracion


def validar_incoterm(incoterm: str) -> None:
    if incoterm not in INCOTERMS_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incoterm invalido. Validos: {', '.join(INCOTERMS_VALIDOS)}",
        )


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
