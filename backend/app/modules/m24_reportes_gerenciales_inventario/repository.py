"""Capa de acceso a datos del modulo m24_reportes_gerenciales_inventario
(Fase 4C - backend).

Este modulo no posee tablas propias (ver models.py). Los Reportes
Gerenciales de Inventario son una agregacion de solo lectura sobre
datos que ya existen en m03_inventario, m19_reportes y
m22_inteligencia_inventario, consultados via las funciones de negocio
de esos modulos (ver service.py).

La UNICA consulta nueva que agrega esta capa es
`ultimo_movimiento_por_producto`: ningun modulo existente expone hoy
la fecha del ultimo MovimientoKardex por producto (m22 solo suma
cantidades DENTRO de una ventana de dias, no calcula "hace cuantos
dias fue el ultimo movimiento"), y ese dato es indispensable para el
reporte "Productos sin rotacion". Es una consulta de lectura pura
sobre MovimientoKardex (m03_inventario), sin agregar columnas ni
duplicar ningun calculo de stock/costo ya existente.

`listar_inventarios` se reexpone tal cual (mismo criterio que
m23_dashboard_inventario.repository), para que service.py pueda
recorrer los inventarios sin importar directamente el repository de
m03_inventario.
"""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.m03_inventario import repository as inventario_repository
from app.modules.m03_inventario.models import Inventario, MovimientoKardex


def listar_inventarios(db: Session) -> list[Inventario]:
    """Reutiliza tal cual la consulta ya existente en
    m03_inventario.repository.listar_inventarios(). No se agrega
    ningun filtro ni logica nueva."""
    return inventario_repository.listar_inventarios(db)


def ultimo_movimiento_por_producto(db: Session, inventario_id: int) -> dict[int, datetime]:
    """Fecha del MovimientoKardex mas reciente (cualquier tipo:
    INGRESO/SALIDA/AJUSTE_POSITIVO/AJUSTE_NEGATIVO) de cada
    producto_inventario dentro de un inventario. No filtra por tipo de
    movimiento: cualquier movimiento -- incluido un ingreso -- cuenta
    como actividad reciente del producto sobre stock, que es lo que
    'dias sin rotacion' necesita reportar.

    Retorna: {producto_inventario_id: fecha_ultimo_movimiento}. Un
    producto sin ningun MovimientoKardex simplemente no aparece en el
    dict (service.py lo interpreta como 'sin movimiento registrado').
    """
    filas = (
        db.query(
            MovimientoKardex.producto_inventario_id,
            func.max(MovimientoKardex.creado_en).label("ultimo_movimiento"),
        )
        .filter(MovimientoKardex.inventario_id == inventario_id)
        .group_by(MovimientoKardex.producto_inventario_id)
        .all()
    )
    return {pi_id: fecha for pi_id, fecha in filas}
