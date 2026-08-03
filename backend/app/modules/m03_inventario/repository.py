from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.modules.m02_productos.models import Producto
from app.modules.m03_inventario.models import Inventario, Lote, MovimientoKardex, ProductoInventario


# --- Inventario ---

def crear_inventario(db: Session, inventario: Inventario) -> Inventario:
    db.add(inventario)
    db.commit()
    db.refresh(inventario)
    return inventario


def obtener_inventario(db: Session, inventario_id: int) -> Optional[Inventario]:
    return db.query(Inventario).filter(Inventario.id == inventario_id).first()


def listar_inventarios(db: Session) -> list[Inventario]:
    return db.query(Inventario).order_by(Inventario.codigo).all()


# --- ProductoInventario ---

def obtener_producto_inventario(
    db: Session, producto_id: int, inventario_id: int
) -> Optional[ProductoInventario]:
    return (
        db.query(ProductoInventario)
        .filter(
            ProductoInventario.producto_id == producto_id,
            ProductoInventario.inventario_id == inventario_id,
        )
        .first()
    )


def obtener_producto_inventario_por_id(db: Session, id_: int) -> Optional[ProductoInventario]:
    return db.query(ProductoInventario).filter(ProductoInventario.id == id_).first()


def crear_producto_inventario(db: Session, pi: ProductoInventario) -> ProductoInventario:
    db.add(pi)
    db.commit()
    db.refresh(pi)
    return pi


def listar_productos_por_inventario(db: Session, inventario_id: int) -> list[ProductoInventario]:
    return (
        db.query(ProductoInventario)
        .filter(ProductoInventario.inventario_id == inventario_id)
        .all()
    )


# --- Lotes / Kardex ---

def crear_lote(db: Session, lote: Lote) -> Lote:
    db.add(lote)
    db.commit()
    db.refresh(lote)
    return lote


def registrar_movimiento(db: Session, movimiento: MovimientoKardex) -> MovimientoKardex:
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento


def obtener_lote(db: Session, lote_id: int) -> Optional[Lote]:
    return db.query(Lote).filter(Lote.id == lote_id).first()


def obtener_lote_por_codigo(db: Session, codigo_lote: str) -> Optional[Lote]:
    """Busca un lote por su codigo, sin distinguir mayusculas/minusculas.
    Funcion de solo lectura (no crea ni modifica nada), usada por la
    importacion de compras nacionalizadas (m04_compras/importacion_service.py)
    para la validacion 'No duplicar lotes'. No cambia ninguna logica de
    inventario existente."""
    return db.query(Lote).filter(func.lower(Lote.codigo_lote) == codigo_lote.strip().lower()).first()


def lotes_disponibles_fefo(
    db: Session, producto_inventario_id: int, fecha_referencia: datetime | None = None
) -> list[Lote]:
    """Lotes con stock > 0 de un producto DENTRO de un inventario, ordenados
    FEFO (vencimiento mas proximo primero, si no tiene vencimiento el mas
    antiguo primero). El algoritmo de ordenamiento NO cambia.

    FASE 1 (seguridad operativa perecibles): se agrega el filtro de
    candidatos validos. Un lote VENCIDO (fecha_vencimiento ya pasada,
    comparada en vivo contra el momento de la consulta, no contra la
    columna Lote.estado que puede estar desactualizada en datos
    historicos) o BLOQUEADO nunca participa de FEFO. AGOTADO ya queda
    excluido por cantidad_actual > 0.

    Paso 2 (carga historica): si se informa fecha_referencia, se filtra
    "vencido a esa fecha" en vez de "vencido a hoy", para que una venta
    historica se evalue contra la realidad de vencimientos en su propia
    fecha (un lote que vencio ENTRE la fecha historica y hoy debe seguir
    contando como disponible para esa reconstruccion). Sin
    fecha_referencia, comportamiento identico al de antes."""
    ahora = fecha_referencia or datetime.now(timezone.utc)
    return (
        db.query(Lote)
        .filter(
            Lote.producto_inventario_id == producto_inventario_id,
            Lote.cantidad_actual > 0,
            Lote.estado != "BLOQUEADO",
            or_(Lote.fecha_vencimiento.is_(None), Lote.fecha_vencimiento >= ahora),
        )
        .order_by(Lote.fecha_vencimiento.asc().nulls_last(), Lote.fecha_ingreso.asc())
        .all()
    )


def stock_total_producto_inventario(db: Session, producto_inventario_id: int) -> float:
    total = (
        db.query(func.coalesce(func.sum(Lote.cantidad_actual), 0))
        .filter(Lote.producto_inventario_id == producto_inventario_id)
        .scalar()
    )
    return float(total or 0)


def kardex_por_producto_inventario(db: Session, producto_inventario_id: int) -> list[MovimientoKardex]:
    return (
        db.query(MovimientoKardex)
        .filter(MovimientoKardex.producto_inventario_id == producto_inventario_id)
        .order_by(MovimientoKardex.creado_en.desc())
        .all()
    )


def saldos_por_inventario(db: Session, inventario_id: int) -> list[dict]:
    """Nota (visualizacion de Costo Unitario): se agrega
    `valor_lotes` = sum(cantidad_actual * costo_unitario), la misma
    expresion que ya usaba m01_dashboard/m19_reportes para valorizar
    inventario. Solo se usa para DERIVAR (division) un costo unitario
    promedio de solo lectura; no se toca el costo_unitario ya guardado
    en cada Lote ni la logica de PEPS/FEFO que lo calcula."""
    filas = (
        db.query(
            ProductoInventario.id,
            ProductoInventario.inventario_id,
            ProductoInventario.producto_id,
            ProductoInventario.codigo_interno,
            Producto.nombre,
            Producto.stock_minimo,
            func.coalesce(func.sum(Lote.cantidad_actual), 0).label("stock_total"),
            func.coalesce(func.sum(Lote.cantidad_actual * Lote.costo_unitario), 0).label("valor_lotes"),
        )
        .join(Producto, Producto.id == ProductoInventario.producto_id)
        .outerjoin(Lote, Lote.producto_inventario_id == ProductoInventario.id)
        .filter(ProductoInventario.inventario_id == inventario_id, ProductoInventario.estado.is_(True))
        .group_by(ProductoInventario.id)
        .order_by(ProductoInventario.codigo_interno)
        .all()
    )
    resultado = []
    for f in filas:
        stock_total = float(f.stock_total or 0)
        valor_lotes = float(f.valor_lotes or 0)
        resultado.append(
            {
                "producto_inventario_id": f.id,
                "inventario_id": f.inventario_id,
                "producto_id": f.producto_id,
                "codigo_interno": f.codigo_interno,
                "nombre": f.nombre,
                "stock_total": stock_total,
                "stock_minimo": float(f.stock_minimo or 0),
                "bajo_stock_minimo": stock_total < float(f.stock_minimo or 0),
                "costo_unitario_promedio": (valor_lotes / stock_total) if stock_total > 0 else 0.0,
            }
        )
    return resultado


def costo_unitario_por_referencia(db: Session, referencia: str) -> dict[int, float]:
    """Costo unitario promedio ponderado, agrupado por producto_id, de los
    movimientos de SALIDA del kardex asociados a una referencia de
    documento (ej. el despacho de una orden de venta o el embarque de una
    declaracion de exportacion). Es una lectura pura sobre el kardex ya
    generado por registrar_salida()/FEFO: no crea ningun costo nuevo, solo
    reexpone (promediado) el costo_unitario que el motor de costeo ya
    grabo en cada MovimientoKardex."""
    filas = (
        db.query(
            ProductoInventario.producto_id,
            func.sum(MovimientoKardex.cantidad).label("cantidad"),
            func.sum(MovimientoKardex.cantidad * MovimientoKardex.costo_unitario).label("valor"),
        )
        .join(ProductoInventario, ProductoInventario.id == MovimientoKardex.producto_inventario_id)
        .filter(
            MovimientoKardex.tipo_movimiento == "SALIDA",
            MovimientoKardex.referencia == referencia,
        )
        .group_by(ProductoInventario.producto_id)
        .all()
    )
    resultado: dict[int, float] = {}
    for f in filas:
        cantidad = float(f.cantidad or 0)
        valor = float(f.valor or 0)
        resultado[f.producto_id] = (valor / cantidad) if cantidad > 0 else 0.0
    return resultado


def costo_unitario_por_referencias(db: Session, referencias: list[str]) -> dict[str, float]:
    """Costo unitario promedio ponderado, agrupado por referencia EXACTA
    (no por producto_id), de los movimientos de SALIDA del kardex.

    A diferencia de costo_unitario_por_referencia() (que agrupa por
    producto_id dentro de UNA referencia de documento completo), esta
    funcion agrupa por cada referencia exacta recibida -- pensada para
    referencias a nivel de LINEA/item de un documento (ej. 'Despacho
    orden de venta #12 item #34'), de forma que dos lineas del mismo
    producto que consumieron lotes/costos distintos (PEPS/FEFO) no se
    mezclen en un promedio comun del documento.

    Es una lectura pura, aditiva, sobre el kardex ya generado por
    registrar_salida(): no crea ni modifica ningun costo, no toca el
    motor FEFO ni ninguna funcion existente de este archivo.
    """
    if not referencias:
        return {}
    filas = (
        db.query(
            MovimientoKardex.referencia,
            func.sum(MovimientoKardex.cantidad).label("cantidad"),
            func.sum(MovimientoKardex.cantidad * MovimientoKardex.costo_unitario).label("valor"),
        )
        .filter(
            MovimientoKardex.tipo_movimiento == "SALIDA",
            MovimientoKardex.referencia.in_(referencias),
        )
        .group_by(MovimientoKardex.referencia)
        .all()
    )
    resultado: dict[str, float] = {}
    for f in filas:
        cantidad = float(f.cantidad or 0)
        valor = float(f.valor or 0)
        resultado[f.referencia] = (valor / cantidad) if cantidad > 0 else 0.0
    return resultado
