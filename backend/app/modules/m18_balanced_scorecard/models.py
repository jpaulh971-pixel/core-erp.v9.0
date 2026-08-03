"""Modulo 18 - Balanced Scorecard.

No define tablas propias: consolida en solo lectura, en las 4
perspectivas clasicas de Kaplan & Norton, indicadores ya calculados por
otros modulos (Ventas, Costos, Inventario, Clientes, Proveedores,
Productos, Lean Six Sigma, Theory of Constraints, Inteligencia
Comercial). Mismo criterio de "no duplicar logica" que ya aplican
m01_dashboard, m13_inteligencia_comercial, m14_inteligencia_tributaria,
m15_lean_six_sigma y m16_theory_of_constraints.

Nota de alcance: este ERP no tiene modulo de Recursos Humanos, asi que
la perspectiva "Aprendizaje y Crecimiento" se adapta con lo unico que
existe en el sistema para medir capacidad y diversificacion: amplitud
de catalogo de productos, diversificacion de proveedores y catalogo
subutilizado (sin movimiento). No se inventan datos de capacitacion ni
de personal.
"""
from app.database import Base  # noqa: F401
