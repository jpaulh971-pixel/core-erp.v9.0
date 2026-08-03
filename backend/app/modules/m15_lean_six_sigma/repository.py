"""Capa de acceso a datos (queries SQLAlchemy) del modulo
m15_lean_six_sigma.

Solo lectura: queries de agregacion sobre Inventario (kardex), Compras y
Ventas ya persistidos por esos modulos. No escribe ni redefine ninguna
regla de negocio de ellos -- mismo criterio que ya usan m01_dashboard,
m13_inteligencia_comercial y m14_inteligencia_tributaria.
"""
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.m02_productos.models import Producto
from app.modules.m03_inventario.models import MovimientoKardex, ProductoInventario
from app.modules.m04_compras.models import OrdenCompra
from app.modules.m10_ventas.models import OrdenVenta


def _filtrar_periodo(q, columna, desde: date | None, hasta: date | None):
    if desde is not None:
        q = q.filter(columna >= desde)
    if hasta is not None:
        q = q.filter(columna <= hasta)
    return q


def total_movimientos_kardex(db: Session, desde: date | None, hasta: date | None) -> int:
    q = db.query(func.count(MovimientoKardex.id))
    q = _filtrar_periodo(q, MovimientoKardex.creado_en, desde, hasta)
    return int(q.scalar() or 0)


def mermas_por_producto(db: Session, desde: date | None, hasta: date | None) -> list[dict]:
    """Ajustes negativos de inventario (mermas/discrepancias) agrupados por
    producto -- se consideran 'defectos' para el calculo de DPMO."""
    q = (
        db.query(
            Producto.id,
            Producto.codigo,
            Producto.nombre,
            func.count(MovimientoKardex.id).label("eventos"),
            func.coalesce(func.sum(MovimientoKardex.cantidad), 0).label("cantidad_mermada"),
        )
        .join(ProductoInventario, ProductoInventario.producto_id == Producto.id)
        .join(MovimientoKardex, MovimientoKardex.producto_inventario_id == ProductoInventario.id)
        .filter(MovimientoKardex.tipo_movimiento == "AJUSTE_NEGATIVO")
    )
    q = _filtrar_periodo(q, MovimientoKardex.creado_en, desde, hasta)
    filas = q.group_by(Producto.id).order_by(func.sum(MovimientoKardex.cantidad).desc()).all()
    return [
        {
            "producto_id": f.id,
            "codigo": f.codigo,
            "nombre": f.nombre,
            "eventos": int(f.eventos or 0),
            "cantidad_mermada": float(f.cantidad_mermada or 0),
        }
        for f in filas
    ]


def ordenes_compra_recibidas(db: Session, desde: date | None, hasta: date | None) -> list[OrdenCompra]:
    q = db.query(OrdenCompra).filter(OrdenCompra.estado == "RECIBIDA")
    q = _filtrar_periodo(q, OrdenCompra.recibido_en, desde, hasta)
    return q.all()


def ordenes_venta_despachadas(db: Session, desde: date | None, hasta: date | None) -> list[OrdenVenta]:
    q = db.query(OrdenVenta).filter(OrdenVenta.estado == "DESPACHADA")
    q = _filtrar_periodo(q, OrdenVenta.despachado_en, desde, hasta)
    return q.all()
