"""Modulo 19 - Reportes.

No define tablas propias: es un modulo de solo lectura que consolida
datos ya persistidos por Ventas (m10), Compras (m04) e Inventario (m03)
en reportes operativos (ventas por periodo, compras por periodo,
inventario valorizado y un resumen general). No agrega logica de
negocio nueva ni redefine reglas de esos modulos; solo agrega/reporta.
"""
from app.database import Base  # noqa: F401
