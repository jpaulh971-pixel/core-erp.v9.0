from fastapi import HTTPException, status


def validar_ruc_disponible(existente) -> None:
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cliente con ese RUC",
        )


def validar_cliente_existe(cliente):
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return cliente


def validar_cliente_activo(cliente) -> None:
    if not cliente.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cliente esta inactivo",
        )
