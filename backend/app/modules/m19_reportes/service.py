"""Logica de negocio del modulo m19_reportes.

Consolida en reportes de solo lectura lo que ya existe en Ventas (m10),
Compras (m04) e Inventario (m03). No define maquinas de estado propias
ni modifica stock, ordenes o precios -- de eso se siguen encargando
esos modulos.
"""
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.modules.m03_inventario import service as inventario_service
from app.modules.m19_reportes import repository, schemas, validators


def reporte_ventas(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> schemas.ReporteVentas:
    validators.validar_rango_fechas(desde, hasta)
    totales = repository.ventas_totales(db, desde, hasta)
    por_producto = repository.ventas_por_producto(db, desde, hasta)
    por_cliente = repository.ventas_por_cliente(db, desde, hasta)
    return schemas.ReporteVentas(
        desde=desde,
        hasta=hasta,
        total_ordenes=totales["cantidad_ordenes"],
        total_vendido=totales["total_vendido"],
        por_producto=[schemas.ProductoAgregado(**p) for p in por_producto],
        por_cliente=[schemas.ClienteAgregado(**c) for c in por_cliente],
    )


def reporte_compras(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> schemas.ReporteCompras:
    validators.validar_rango_fechas(desde, hasta)
    totales = repository.compras_totales(db, desde, hasta)
    por_producto = repository.compras_por_producto(db, desde, hasta)
    por_proveedor = repository.compras_por_proveedor(db, desde, hasta)
    return schemas.ReporteCompras(
        desde=desde,
        hasta=hasta,
        total_ordenes=totales["cantidad_ordenes"],
        total_comprado=totales["total_comprado"],
        por_producto=[schemas.ProductoAgregado(**p) for p in por_producto],
        por_proveedor=[schemas.ProveedorAgregado(**p) for p in por_proveedor],
    )


def reporte_inventario_valorizado(db: Session) -> schemas.ReporteInventarioValorizado:
    productos = repository.inventario_valorizado(db)
    # FASE 2 (control gerencial): se agrega el semaforo de stock a cada
    # fila (funcion centralizada, reutilizada de m03_inventario.service),
    # sin tocar ningun campo ni calculo que ya existia en este reporte.
    for p in productos:
        p["semaforo_stock"] = inventario_service.calcular_semaforo_stock(
            p["cantidad_actual"], p["stock_minimo"]
        )
    return schemas.ReporteInventarioValorizado(
        generado_en=datetime.utcnow(),
        total_productos=len(productos),
        valor_total_inventario=sum(p["valor_total"] for p in productos),
        productos_bajo_stock_minimo=sum(1 for p in productos if p["bajo_stock_minimo"]),
        productos=[schemas.ProductoValorizado(**p) for p in productos],
    )


def reporte_inventario_por_lote(
    db: Session, inventario_id: int | None = None
) -> schemas.ReporteInventarioPorLote:
    """FASE 2 (control gerencial): reporte de inventario por lote.
    Solo lectura -- no modifica ningun movimiento, costo ni kardex.
    Reutiliza calcular_estado_lote() y calcular_semaforo_vencimiento()
    de m03_inventario.service (sin duplicar esa logica)."""
    lotes = repository.listar_lotes(db, inventario_id)
    proveedores = repository.proveedores_por_codigo_lote(db)

    items: list[schemas.LotePorProducto] = []
    for lote in lotes:
        producto = lote.producto_inventario.producto
        cantidad_disponible = float(lote.cantidad_actual)
        costo_unitario = float(lote.costo_unitario)
        semaforo, dias_restantes = inventario_service.calcular_semaforo_vencimiento(
            lote.fecha_vencimiento
        )
        items.append(
            schemas.LotePorProducto(
                producto_id=producto.id,
                producto=producto.nombre,
                codigo_producto=producto.codigo,
                codigo_lote=lote.codigo_lote,
                fecha_ingreso=lote.fecha_ingreso,
                fecha_elaboracion=lote.fecha_elaboracion,
                fecha_vencimiento=lote.fecha_vencimiento,
                cantidad_inicial=float(lote.cantidad_inicial),
                cantidad_disponible=cantidad_disponible,
                costo_unitario=costo_unitario,
                valor_total_lote=round(cantidad_disponible * costo_unitario, 2),
                estado_lote=inventario_service.calcular_estado_lote(lote),
                semaforo_vencimiento=semaforo,
                dias_restantes_vencimiento=dias_restantes,
                proveedor=proveedores.get(lote.codigo_lote.strip().lower()),
            )
        )

    return schemas.ReporteInventarioPorLote(
        generado_en=datetime.utcnow(),
        total_lotes=len(items),
        valor_total=round(sum(i.valor_total_lote for i in items), 2),
        lotes=items,
    )


def reporte_proximos_vencer(
    db: Session, inventario_id: int | None = None
) -> schemas.ReporteProximosVencer:
    """FASE 2 (control gerencial): reporte de productos proximos a
    vencer. Solo lectura. Incluye unicamente lotes con fecha_vencimiento
    y con cantidad_disponible > 0 (un lote sin stock no representa valor
    comprometido que gestionar). La categoria (ACTIVOS/PROXIMOS_A_VENCER/
    VENCIDOS) se deriva del mismo semaforo centralizado de vencimiento
    (VERDE->ACTIVOS, AMARILLO y ROJO->PROXIMOS_A_VENCER, NEGRO->
    VENCIDOS), sin duplicar esa clasificacion.

    repository.listar_lotes() ya devuelve los lotes ordenados por fecha
    de vencimiento, luego producto, luego lote -- el orden exacto que
    pide esta Fase 2 -- asi que no se vuelve a ordenar aca."""
    lotes = repository.listar_lotes(db, inventario_id)

    items: list[schemas.LoteProximoVencer] = []
    for lote in lotes:
        if lote.fecha_vencimiento is None or float(lote.cantidad_actual) <= 0:
            continue

        producto = lote.producto_inventario.producto
        semaforo, dias_restantes = inventario_service.calcular_semaforo_vencimiento(
            lote.fecha_vencimiento
        )
        if semaforo == "NEGRO":
            categoria = "VENCIDOS"
        elif semaforo in ("AMARILLO", "ROJO"):
            categoria = "PROXIMOS_A_VENCER"
        else:
            categoria = "ACTIVOS"

        cantidad_disponible = float(lote.cantidad_actual)
        costo_unitario = float(lote.costo_unitario)
        items.append(
            schemas.LoteProximoVencer(
                producto_id=producto.id,
                producto=producto.nombre,
                codigo_producto=producto.codigo,
                codigo_lote=lote.codigo_lote,
                fecha_vencimiento=lote.fecha_vencimiento,
                dias_restantes=dias_restantes,
                categoria=categoria,
                estado_lote=inventario_service.calcular_estado_lote(lote),
                semaforo_vencimiento=semaforo,
                cantidad_disponible=cantidad_disponible,
                costo_unitario=costo_unitario,
                valor_stock_comprometido=round(cantidad_disponible * costo_unitario, 2),
            )
        )

    return schemas.ReporteProximosVencer(
        generado_en=datetime.utcnow(),
        total_lotes=len(items),
        activos=sum(1 for i in items if i.categoria == "ACTIVOS"),
        proximos_a_vencer=sum(1 for i in items if i.categoria == "PROXIMOS_A_VENCER"),
        vencidos=sum(1 for i in items if i.categoria == "VENCIDOS"),
        valor_total_comprometido=round(sum(i.valor_stock_comprometido for i in items), 2),
        lotes=items,
    )


def resumen_general(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> schemas.ResumenGeneral:
    validators.validar_rango_fechas(desde, hasta)
    ventas = repository.ventas_totales(db, desde, hasta)
    compras = repository.compras_totales(db, desde, hasta)
    productos = repository.inventario_valorizado(db)
    return schemas.ResumenGeneral(
        desde=desde,
        hasta=hasta,
        total_vendido_periodo=ventas["total_vendido"],
        total_comprado_periodo=compras["total_comprado"],
        ordenes_venta_periodo=ventas["cantidad_ordenes"],
        ordenes_compra_periodo=compras["cantidad_ordenes"],
        valor_inventario_actual=sum(p["valor_total"] for p in productos),
        productos_bajo_stock_minimo=sum(1 for p in productos if p["bajo_stock_minimo"]),
    )
