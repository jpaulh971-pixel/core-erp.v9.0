"""Capa de acceso a datos (queries SQLAlchemy) del modulo
m18_balanced_scorecard.

Solo lectura: agrega lo unico que ningun otro modulo expone todavia
(totales de catalogo activo, clientes distintos con despacho en un
periodo, cantidad de ordenes despachadas). Todo lo demas (ingreso,
costo de mercaderia vendida, DPMO, tiempos de ciclo, restricciones de
stock, rotacion, ranking de clientes) se reutiliza directo de los
repositorios/servicios de m03, m05, m11, m13, m15 y m16 -- sin volver a
consultarlo aqui.
"""
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.m02_productos.models import Producto
from app.modules.m05_proveedores.models import Proveedor
from app.modules.m10_ventas.models import OrdenVenta
from app.modules.m11_clientes.models import Cliente


def _filtrar_periodo(q, columna, desde: date | None, hasta: date | None):
    if desde is not None:
        q = q.filter(columna >= desde)
    if hasta is not None:
        q = q.filter(columna <= hasta)
    return q


def productos_activos_total(db: Session) -> int:
    return db.query(func.count(Producto.id)).filter(Producto.activo.is_(True)).scalar() or 0


def proveedores_activos_total(db: Session) -> int:
    return db.query(func.count(Proveedor.id)).filter(Proveedor.activo.is_(True)).scalar() or 0


def clientes_activos_total(db: Session) -> int:
    return db.query(func.count(Cliente.id)).filter(Cliente.activo.is_(True)).scalar() or 0


def clientes_distintos_con_despacho(
    db: Session, desde: date | None, hasta: date | None
) -> int:
    q = db.query(func.count(func.distinct(OrdenVenta.cliente_id))).filter(
        OrdenVenta.estado == "DESPACHADA"
    )
    q = _filtrar_periodo(q, OrdenVenta.despachado_en, desde, hasta)
    return q.scalar() or 0


def cantidad_ordenes_despachadas(
    db: Session, desde: date | None, hasta: date | None
) -> int:
    q = db.query(func.count(OrdenVenta.id)).filter(OrdenVenta.estado == "DESPACHADA")
    q = _filtrar_periodo(q, OrdenVenta.despachado_en, desde, hasta)
    return q.scalar() or 0
