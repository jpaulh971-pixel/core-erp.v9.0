"""Capa de acceso a datos (queries SQLAlchemy) del modulo m19_reportes.

Solo lectura: consolida datos ya persistidos por Ventas (m10), Compras
(m04) e Inventario (m03). No redefine ninguna regla de negocio de esos
modulos (maquinas de estado, descuento/ingreso de stock); solo agrega
y reporta sobre lo que ya existe.
"""
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.modules.m02_productos.models import Producto
from app.modules.m03_inventario.models import Lote, MovimientoKardex, ProductoInventario
from app.modules.m04_compras.models import OrdenCompra, OrdenCompraItem
from app.modules.m05_proveedores.models import Proveedor
from app.modules.m10_ventas.models import OrdenVenta, OrdenVentaItem
from app.modules.m11_clientes.models import Cliente

ESTADO_VENTA_REALIZADA = "DESPACHADA"
ESTADO_COMPRA_REALIZADA = "RECIBIDA"


def _filtrar_periodo(q, columna, desde: date | None, hasta: date | None):
    if desde is not None:
        q = q.filter(columna >= desde)
    if hasta is not None:
        q = q.filter(columna <= hasta)
    return q


def ventas_totales(db: Session, desde: date | None, hasta: date | None) -> dict:
    """Total de ordenes y monto vendido en el periodo (ventas ya
    despachadas, que es cuando se descuenta stock real)."""
    q = db.query(
        func.count(OrdenVenta.id.distinct()).label("cantidad"),
    ).filter(OrdenVenta.estado == ESTADO_VENTA_REALIZADA)
    q = _filtrar_periodo(q, OrdenVenta.despachado_en, desde, hasta)
    cantidad = q.scalar() or 0

    q_total = (
        db.query(
            func.coalesce(
                func.sum(OrdenVentaItem.cantidad * OrdenVentaItem.precio_unitario_venta), 0
            )
        )
        .join(OrdenVenta, OrdenVenta.id == OrdenVentaItem.orden_venta_id)
        .filter(OrdenVenta.estado == ESTADO_VENTA_REALIZADA)
    )
    q_total = _filtrar_periodo(q_total, OrdenVenta.despachado_en, desde, hasta)
    total = q_total.scalar() or 0
    return {"cantidad_ordenes": int(cantidad), "total_vendido": float(total)}


def _costo_kardex_ventas_por_producto(
    db: Session, desde: date | None, hasta: date | None
) -> dict[int, float]:
    """Costo unitario promedio ponderado por producto, leido directamente de
    los MovimientoKardex de tipo SALIDA generados al despachar ordenes de
    venta (referencia = 'Despacho orden de venta #<id>'). Se filtra por
    MovimientoKardex.creado_en (momento del despacho, coincide con
    OrdenVenta.despachado_en) en vez de parsear el id de la referencia,
    que es un string libre y no una FK. Es una lectura/promedio sobre
    costos que el motor de costeo (FEFO) ya grabo -- no crea costo nuevo.
    """
    q = (
        db.query(
            ProductoInventario.producto_id,
            func.sum(MovimientoKardex.cantidad).label("cantidad"),
            func.sum(
                MovimientoKardex.cantidad * MovimientoKardex.costo_unitario
            ).label("valor"),
        )
        .join(
            ProductoInventario,
            ProductoInventario.id == MovimientoKardex.producto_inventario_id,
        )
        .filter(
            MovimientoKardex.tipo_movimiento == "SALIDA",
            MovimientoKardex.referencia.like("Despacho orden de venta%"),
        )
    )
    q = _filtrar_periodo(q, MovimientoKardex.creado_en, desde, hasta)
    filas = q.group_by(ProductoInventario.producto_id).all()
    resultado = {}
    for f in filas:
        cantidad = float(f.cantidad or 0)
        valor = float(f.valor or 0)
        resultado[f.producto_id] = (valor / cantidad) if cantidad > 0 else 0.0
    return resultado


def ventas_por_producto(db: Session, desde: date | None, hasta: date | None) -> list[dict]:
    q = (
        db.query(
            Producto.id,
            Producto.codigo,
            Producto.nombre,
            func.coalesce(func.sum(OrdenVentaItem.cantidad), 0).label("cantidad"),
            func.coalesce(
                func.sum(OrdenVentaItem.cantidad * OrdenVentaItem.precio_unitario_venta), 0
            ).label("total"),
        )
        .join(OrdenVentaItem, OrdenVentaItem.producto_id == Producto.id)
        .join(OrdenVenta, OrdenVenta.id == OrdenVentaItem.orden_venta_id)
        .filter(OrdenVenta.estado == ESTADO_VENTA_REALIZADA)
    )
    q = _filtrar_periodo(q, OrdenVenta.despachado_en, desde, hasta)
    filas = q.group_by(Producto.id, Producto.codigo, Producto.nombre).order_by(
        func.sum(OrdenVentaItem.cantidad * OrdenVentaItem.precio_unitario_venta).desc()
    ).all()
    costos_por_producto = _costo_kardex_ventas_por_producto(db, desde, hasta)
    return [
        {
            "producto_id": f.id,
            "codigo": f.codigo,
            "nombre": f.nombre,
            "cantidad": float(f.cantidad or 0),
            "total": float(f.total or 0),
            "costo_unitario_promedio": costos_por_producto.get(f.id),
        }
        for f in filas
    ]


def ventas_por_cliente(db: Session, desde: date | None, hasta: date | None) -> list[dict]:
    q = (
        db.query(
            Cliente.id,
            Cliente.razon_social,
            func.count(OrdenVenta.id.distinct()).label("cantidad_ordenes"),
            func.coalesce(
                func.sum(OrdenVentaItem.cantidad * OrdenVentaItem.precio_unitario_venta), 0
            ).label("total"),
        )
        .join(OrdenVenta, OrdenVenta.cliente_id == Cliente.id)
        .join(OrdenVentaItem, OrdenVentaItem.orden_venta_id == OrdenVenta.id)
        .filter(OrdenVenta.estado == ESTADO_VENTA_REALIZADA)
    )
    q = _filtrar_periodo(q, OrdenVenta.despachado_en, desde, hasta)
    filas = q.group_by(Cliente.id, Cliente.razon_social).order_by(
        func.sum(OrdenVentaItem.cantidad * OrdenVentaItem.precio_unitario_venta).desc()
    ).all()
    return [
        {
            "cliente_id": f.id,
            "razon_social": f.razon_social,
            "cantidad_ordenes": int(f.cantidad_ordenes or 0),
            "total": float(f.total or 0),
        }
        for f in filas
    ]


def compras_totales(db: Session, desde: date | None, hasta: date | None) -> dict:
    q = db.query(
        func.count(OrdenCompra.id.distinct()).label("cantidad"),
    ).filter(OrdenCompra.estado == ESTADO_COMPRA_REALIZADA)
    q = _filtrar_periodo(q, OrdenCompra.recibido_en, desde, hasta)
    cantidad = q.scalar() or 0

    q_total = (
        db.query(
            func.coalesce(
                func.sum(OrdenCompraItem.cantidad * OrdenCompraItem.costo_unitario), 0
            )
        )
        .join(OrdenCompra, OrdenCompra.id == OrdenCompraItem.orden_compra_id)
        .filter(OrdenCompra.estado == ESTADO_COMPRA_REALIZADA)
    )
    q_total = _filtrar_periodo(q_total, OrdenCompra.recibido_en, desde, hasta)
    total = q_total.scalar() or 0
    return {"cantidad_ordenes": int(cantidad), "total_comprado": float(total)}


def _costo_kardex_compras_por_producto(
    db: Session, desde: date | None, hasta: date | None
) -> dict[int, float]:
    """Costo unitario promedio ponderado por producto, leido directamente
    de los MovimientoKardex de tipo INGRESO generados al recibir ordenes
    de compra (referencia = 'Recepcion orden de compra #<id>...'). A
    diferencia de OrdenCompraItem.costo_unitario (costo de compra
    ORIGINAL, antes de costos adicionales), el kardex ya tiene el costo
    con landed cost aplicado -- flete/seguro/aduana prorrateados en
    m04_compras.service.recibir_orden() -- que es el mismo costo con el
    que nacio el Lote y con el que se valoriza el inventario. Se filtra
    por MovimientoKardex.creado_en (coincide con OrdenCompra.recibido_en)
    en vez de parsear el id de la referencia, que es un string libre y
    no una FK. Es una lectura/promedio sobre costos que el motor de
    costeo ya grabo -- no crea costo nuevo. Mismo patron que
    _costo_kardex_ventas_por_producto (arriba)."""
    q = (
        db.query(
            ProductoInventario.producto_id,
            func.sum(MovimientoKardex.cantidad).label("cantidad"),
            func.sum(
                MovimientoKardex.cantidad * MovimientoKardex.costo_unitario
            ).label("valor"),
        )
        .join(
            ProductoInventario,
            ProductoInventario.id == MovimientoKardex.producto_inventario_id,
        )
        .filter(
            MovimientoKardex.tipo_movimiento == "INGRESO",
            MovimientoKardex.referencia.like("Recepcion orden de compra%"),
        )
    )
    q = _filtrar_periodo(q, MovimientoKardex.creado_en, desde, hasta)
    filas = q.group_by(ProductoInventario.producto_id).all()
    resultado = {}
    for f in filas:
        cantidad = float(f.cantidad or 0)
        valor = float(f.valor or 0)
        resultado[f.producto_id] = (valor / cantidad) if cantidad > 0 else 0.0
    return resultado


def compras_por_producto(db: Session, desde: date | None, hasta: date | None) -> list[dict]:
    q = (
        db.query(
            Producto.id,
            Producto.codigo,
            Producto.nombre,
            func.coalesce(func.sum(OrdenCompraItem.cantidad), 0).label("cantidad"),
            func.coalesce(
                func.sum(OrdenCompraItem.cantidad * OrdenCompraItem.costo_unitario), 0
            ).label("total"),
        )
        .join(OrdenCompraItem, OrdenCompraItem.producto_id == Producto.id)
        .join(OrdenCompra, OrdenCompra.id == OrdenCompraItem.orden_compra_id)
        .filter(OrdenCompra.estado == ESTADO_COMPRA_REALIZADA)
    )
    q = _filtrar_periodo(q, OrdenCompra.recibido_en, desde, hasta)
    filas = q.group_by(Producto.id, Producto.codigo, Producto.nombre).order_by(
        func.sum(OrdenCompraItem.cantidad * OrdenCompraItem.costo_unitario).desc()
    ).all()
    costos_por_producto = _costo_kardex_compras_por_producto(db, desde, hasta)
    resultado = []
    for f in filas:
        cantidad = float(f.cantidad or 0)
        total = float(f.total or 0)
        # "total" sigue siendo el valor de la Orden de Compra tal como se
        # pacto con el proveedor (cantidad * OrdenCompraItem.costo_unitario,
        # SIN costos adicionales) -- es el monto comprometido/facturado.
        # "costo_unitario_promedio" en cambio se lee del Kardex de INGRESO
        # (ver _costo_kardex_compras_por_producto arriba), que SI incluye
        # el landed cost (flete/seguro/aduana) con el que el Lote/Kardex
        # realmente valorizan el inventario. Por eso, a proposito, ya no
        # es necesariamente igual a total/cantidad: son dos magnitudes
        # distintas (valor pactado vs. costo real de inventario), igual
        # que en ventas_por_producto (total = ingreso por venta, costo_
        # unitario_promedio = costo real de kardex).
        resultado.append(
            {
                "producto_id": f.id,
                "codigo": f.codigo,
                "nombre": f.nombre,
                "cantidad": cantidad,
                "total": total,
                "costo_unitario_promedio": costos_por_producto.get(f.id),
            }
        )
    return resultado


def compras_por_proveedor(db: Session, desde: date | None, hasta: date | None) -> list[dict]:
    q = (
        db.query(
            Proveedor.id,
            Proveedor.razon_social,
            func.count(OrdenCompra.id.distinct()).label("cantidad_ordenes"),
            func.coalesce(
                func.sum(OrdenCompraItem.cantidad * OrdenCompraItem.costo_unitario), 0
            ).label("total"),
        )
        .join(OrdenCompra, OrdenCompra.proveedor_id == Proveedor.id)
        .join(OrdenCompraItem, OrdenCompraItem.orden_compra_id == OrdenCompra.id)
        .filter(OrdenCompra.estado == ESTADO_COMPRA_REALIZADA)
    )
    q = _filtrar_periodo(q, OrdenCompra.recibido_en, desde, hasta)
    filas = q.group_by(Proveedor.id, Proveedor.razon_social).order_by(
        func.sum(OrdenCompraItem.cantidad * OrdenCompraItem.costo_unitario).desc()
    ).all()
    return [
        {
            "proveedor_id": f.id,
            "razon_social": f.razon_social,
            "cantidad_ordenes": int(f.cantidad_ordenes or 0),
            "total": float(f.total or 0),
        }
        for f in filas
    ]


def inventario_valorizado(db: Session) -> list[dict]:
    """Stock actual y valor por producto, ponderando el costo unitario de
    cada lote vigente (promedio ponderado por cantidad_actual)."""
    filas = (
        db.query(
            Producto.id,
            Producto.codigo,
            Producto.nombre,
            Producto.stock_minimo,
            func.coalesce(func.sum(Lote.cantidad_actual), 0).label("cantidad_actual"),
            func.coalesce(
                func.sum(Lote.cantidad_actual * Lote.costo_unitario), 0
            ).label("valor_total"),
        )
        .outerjoin(ProductoInventario, ProductoInventario.producto_id == Producto.id)
        .outerjoin(Lote, Lote.producto_inventario_id == ProductoInventario.id)
        .filter(Producto.activo.is_(True))
        .group_by(Producto.id, Producto.codigo, Producto.nombre, Producto.stock_minimo)
        .order_by(Producto.nombre)
        .all()
    )
    resultado = []
    for f in filas:
        cantidad_actual = float(f.cantidad_actual or 0)
        valor_total = float(f.valor_total or 0)
        valor_promedio = (valor_total / cantidad_actual) if cantidad_actual > 0 else 0.0
        stock_minimo = float(f.stock_minimo or 0)
        resultado.append(
            {
                "producto_id": f.id,
                "codigo": f.codigo,
                "nombre": f.nombre,
                "cantidad_actual": cantidad_actual,
                "valor_promedio_unitario": valor_promedio,
                "valor_total": valor_total,
                "stock_minimo": stock_minimo,
                "bajo_stock_minimo": cantidad_actual < stock_minimo,
            }
        )
    return resultado


# ---------------------------------------------------------------------
# FASE 2 - control gerencial para inventario perecible. Solo lectura:
# reutiliza Lote/ProductoInventario/Producto (m03/m02) tal como estan,
# no crea ninguna relacion nueva en el modelo.
# ---------------------------------------------------------------------


def listar_lotes(db: Session, inventario_id: int | None = None) -> list[Lote]:
    """Todos los Lotes (cualquier estado), con ProductoInventario y
    Producto precargados (joinedload, evita N+1), ordenados por fecha de
    vencimiento (los que no tienen, al final), luego por producto y por
    codigo de lote -- el orden que pide el reporte 'Productos proximos a
    vencer' y que tambien sirve, sin duplicar la consulta, para
    'Inventario por lote'. Base compartida de ambos reportes de Fase 2."""
    q = (
        db.query(Lote)
        .join(ProductoInventario, ProductoInventario.id == Lote.producto_inventario_id)
        .join(Producto, Producto.id == ProductoInventario.producto_id)
        .options(
            joinedload(Lote.producto_inventario).joinedload(ProductoInventario.producto)
        )
    )
    if inventario_id is not None:
        q = q.filter(ProductoInventario.inventario_id == inventario_id)
    return q.order_by(
        Lote.fecha_vencimiento.asc().nulls_last(), Producto.nombre, Lote.codigo_lote
    ).all()


def proveedores_por_codigo_lote(db: Session) -> dict[str, str]:
    """Solo lectura: mapea codigo_lote (normalizado a minusculas) -> razon
    social del proveedor, reconstruyendo la relacion a traves de
    OrdenCompraItem.lote (mismo campo que ya usa
    m04_compras/importacion_service.py para la validacion 'no duplicar
    lotes'). No agrega ninguna columna ni relacion nueva al modelo: es
    solo una lectura indirecta para la columna opcional 'Proveedor' del
    reporte 'Inventario por lote' (Fase 2), que solo se completa cuando
    el lote nacio de una orden de compra con ese dato cargado."""
    filas = (
        db.query(OrdenCompraItem.lote, Proveedor.razon_social)
        .join(OrdenCompra, OrdenCompra.id == OrdenCompraItem.orden_compra_id)
        .join(Proveedor, Proveedor.id == OrdenCompra.proveedor_id)
        .filter(OrdenCompraItem.lote.isnot(None))
        .all()
    )
    resultado: dict[str, str] = {}
    for codigo_lote, razon_social in filas:
        if codigo_lote:
            resultado[codigo_lote.strip().lower()] = razon_social
    return resultado
