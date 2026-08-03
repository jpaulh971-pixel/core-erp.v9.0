from fastapi import HTTPException, status


def validar_codigo_disponible(existente) -> None:
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un producto con ese codigo",
        )


def validar_producto_existe(producto):
    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    return producto
