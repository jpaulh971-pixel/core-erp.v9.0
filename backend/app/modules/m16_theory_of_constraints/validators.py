"""Reglas y validaciones de negocio del modulo m16_theory_of_constraints."""
from datetime import date

from fastapi import HTTPException, status


def validar_rango_fechas(desde: date | None, hasta: date | None) -> None:
    if desde is not None and hasta is not None and desde > hasta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'desde' no puede ser posterior a 'hasta'.",
        )
