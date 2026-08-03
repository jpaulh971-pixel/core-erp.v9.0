"""Reglas y validaciones de negocio del modulo m22_inteligencia_inventario."""
from fastapi import HTTPException, status


def validar_dias_analisis(dias_analisis: int) -> None:
    """La ventana de analisis debe ser un entero positivo (no tiene
    sentido dividir por una ventana de 0 o negativa dias)."""
    if dias_analisis <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'dias_analisis' debe ser un numero entero mayor a 0.",
        )


def validar_producto_inventario_pertenece(producto_inventario, inventario_id: int):
    """Reutiliza el mismo criterio que m03_inventario.validators.
    validar_producto_en_inventario, mas la verificacion de que
    pertenece al inventario_id indicado en la URL (para el endpoint de
    detalle por producto)."""
    if producto_inventario is None or producto_inventario.inventario_id != inventario_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Este producto no existe en el inventario indicado",
        )
    return producto_inventario
