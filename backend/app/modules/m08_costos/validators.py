from fastapi import HTTPException, status

from app.modules.m08_costos.models import TIPOS_COSTO, TIPOS_DOCUMENTO


def validar_tipo_documento(tipo_documento: str) -> None:
    if tipo_documento not in TIPOS_DOCUMENTO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"tipo_documento invalido. Validos: {', '.join(TIPOS_DOCUMENTO)}",
        )


def validar_tipo_costo(tipo_costo: str) -> None:
    if tipo_costo not in TIPOS_COSTO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"tipo_costo invalido. Validos: {', '.join(TIPOS_COSTO)}",
        )


def validar_documento_referenciado(documento) -> None:
    if documento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El documento (orden de compra o declaracion de exportacion) no existe",
        )
