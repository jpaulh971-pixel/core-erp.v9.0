from fastapi import HTTPException, status


def validar_ruc_disponible(existente) -> None:
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un proveedor con ese RUC",
        )


def validar_proveedor_existe(proveedor):
    if proveedor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proveedor no encontrado",
        )
    return proveedor


def validar_proveedor_activo(proveedor) -> None:
    if not proveedor.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El proveedor esta inactivo",
        )
