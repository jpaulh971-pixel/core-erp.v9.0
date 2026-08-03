"""Capa de acceso a datos del modulo m23_dashboard_inventario (Fase 4A).

Este modulo no posee tablas propias (ver models.py): el Dashboard
Gerencial de Inventario es una agregacion de solo lectura sobre datos
que ya existen en m03_inventario, m19_reportes y
m22_inteligencia_inventario. Por eso esta capa se limita a reexponer,
SIN duplicar la consulta, el listado de inventarios que necesita
service.py de este modulo para recorrer m22 (que calcula riesgo de
merma por inventario_id, no de forma global).
"""
from sqlalchemy.orm import Session

from app.modules.m03_inventario import repository as inventario_repository
from app.modules.m03_inventario.models import Inventario


def listar_inventarios(db: Session) -> list[Inventario]:
    """Reutiliza tal cual la consulta ya existente en
    m03_inventario.repository.listar_inventarios(). No se agrega
    ningun filtro ni logica nueva."""
    return inventario_repository.listar_inventarios(db)
