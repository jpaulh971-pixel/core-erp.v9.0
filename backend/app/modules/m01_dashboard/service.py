"""Logica de negocio del modulo m01_dashboard.

Panel ejecutivo de solo lectura: consolida KPIs de Inventario, Ventas y
Costos en un unico llamado. No recalcula ni redefine ninguna regla de
negocio de esos modulos -- para saldos y alertas de stock reutiliza
directo el servicio de Inventario (mismo criterio de "no duplicar logica"
que ya aplican Compras, Comercio Exterior y Ventas al descontar stock via
el servicio de Inventario).
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.modules.m01_dashboard import repository, schemas
from app.modules.m03_inventario import service as inventario_service


def resumen_ejecutivo(db: Session) -> schemas.DashboardOut:
    # m01 no redefine que inventario usar: reutiliza el primero registrado
    # en m03 (hoy en la practica es unico, INV-001 creado por seed.py). Si
    # todavia no existe ningun inventario, el resumen queda con saldos
    # vacios en vez de romper el Dashboard.
    inventarios = inventario_service.listar_inventarios(db)
    saldos = inventario_service.saldos(db, inventarios[0].id) if inventarios else []
    alertas = [s for s in saldos if s["bajo_stock_minimo"]]

    valor_total = repository.valor_total_inventario(db)
    stock_total_general = sum(s["stock_total"] for s in saldos)
    costo_promedio_general = (
        valor_total / stock_total_general if stock_total_general > 0 else 0.0
    )

    # Producto de mayor/menor costo: solo lectura del maximo/minimo entre los
    # costo_unitario_promedio ya calculados por saldos() (m03_inventario),
    # sin ningun calculo de costeo nuevo. Se excluyen los productos sin
    # stock (costo 0.0) del "menor costo" para no marcar como "mas barato"
    # a un producto que en realidad no tiene lotes valorizados.
    con_costo = [s for s in saldos if s["costo_unitario_promedio"] > 0]
    producto_mayor_costo = None
    producto_menor_costo = None
    if con_costo:
        mayor = max(con_costo, key=lambda s: s["costo_unitario_promedio"])
        menor = min(con_costo, key=lambda s: s["costo_unitario_promedio"])
        producto_mayor_costo = schemas.ProductoCosto(
            producto_id=mayor["producto_id"],
            codigo=mayor["codigo_interno"],
            nombre=mayor["nombre"],
            costo_unitario_promedio=mayor["costo_unitario_promedio"],
        )
        producto_menor_costo = schemas.ProductoCosto(
            producto_id=menor["producto_id"],
            codigo=menor["codigo_interno"],
            nombre=menor["nombre"],
            costo_unitario_promedio=menor["costo_unitario_promedio"],
        )

    inventario = schemas.ResumenInventario(
        total_productos_activos=len(saldos),
        valor_total_inventario=valor_total,
        productos_bajo_stock_minimo=len(alertas),
        alertas_stock=[
            schemas.AlertaStock(
                producto_id=a["producto_id"],
                codigo=a["codigo_interno"],  # el dict de saldos usa "codigo_interno", no "codigo"
                nombre=a["nombre"],
                stock_total=a["stock_total"],
                stock_minimo=a["stock_minimo"],
                costo_unitario_promedio=a["costo_unitario_promedio"],
            )
            for a in alertas
        ],
        costo_unitario_promedio_general=costo_promedio_general,
        producto_mayor_costo=producto_mayor_costo,
        producto_menor_costo=producto_menor_costo,
    )

    ventas = schemas.ResumenVentas(
        ordenes_por_estado=repository.ordenes_venta_por_estado(db),
        total_vendido_despachadas=repository.total_vendido_despachadas(db),
    )

    compras = schemas.ResumenCompras(
        total_comprado_recibidas=repository.total_comprado_recibidas(db),
    )

    costos = schemas.ResumenCostos(
        total_costos_adicionales=repository.total_costos_adicionales(db),
        costos_adicionales_por_tipo=repository.costos_adicionales_por_tipo(db),
    )

    return schemas.DashboardOut(
        generado_en=datetime.now(timezone.utc),
        inventario=inventario,
        ventas=ventas,
        compras=compras,
        costos=costos,
    )
