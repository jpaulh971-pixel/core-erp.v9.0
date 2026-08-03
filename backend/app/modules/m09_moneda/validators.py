from fastapi import HTTPException, status


def validar_codigo_moneda(codigo: str) -> None:
    if len(codigo) != 3 or not codigo.isalpha():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Codigo de moneda invalido: '{codigo}'. Debe ser ISO-4217 de 3 letras (ej: USD, PEN, EUR).",
        )


def validar_par_distinto(moneda_origen: str, moneda_destino: str) -> None:
    if moneda_origen == moneda_destino:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="moneda_origen y moneda_destino no pueden ser la misma para registrar un tipo de cambio.",
        )


def validar_tipo_cambio_existe(tipo_cambio, moneda_origen: str, moneda_destino: str) -> None:
    if tipo_cambio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No hay tipo de cambio registrado para {moneda_origen}->{moneda_destino} "
                "(ni su par inverso) en o antes de la fecha solicitada."
            ),
        )
