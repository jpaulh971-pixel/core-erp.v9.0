"""Validadores del modulo m24_reportes_gerenciales_inventario (Fase 4C).

Los 4 endpoints de esta fase son de solo lectura y reciben unicamente
parametros opcionales de query (limite de filas, umbral de dias sin
rotacion). Se validan aca para mantener el patron Repository ->
Service -> Router -> Schemas -> Validators del resto del ERP.
"""
from fastapi import HTTPException, status


def validar_limite(limite: int | None) -> None:
    """El parametro 'limite' (top-valor) debe ser un entero positivo
    cuando se especifica; None significa 'sin limite' y es valido."""
    if limite is not None and limite <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'limite' debe ser un numero entero mayor a 0.",
        )


def validar_dias_sin_rotacion(dias_sin_rotacion: int | None) -> None:
    """El umbral de dias sin movimiento (sin-rotacion) debe ser un
    entero positivo cuando se especifica; None usa el valor por
    defecto de settings."""
    if dias_sin_rotacion is not None and dias_sin_rotacion <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'dias_sin_rotacion' debe ser un numero entero mayor a 0.",
        )
