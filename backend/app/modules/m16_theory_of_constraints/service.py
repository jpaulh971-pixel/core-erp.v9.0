"""Logica de negocio del modulo m16_theory_of_constraints.

Theory of Constraints de solo lectura sobre Ventas, Inventario y Costos
ya implementados: identifica la restriccion (cuello de botella) del
flujo Compras -> Inventario -> Ventas y arma la contabilidad de
throughput (T, I, OE). No redefine FEFO, maquinas de estado ni ninguna
otra regla de esos modulos -- para stock y valorizacion de inventario
reutiliza directo los servicios existentes, sin duplicar logica (mismo
criterio que ya aplican m01_dashboard y m13_inteligencia_comercial).
"""
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.modules.m01_dashboard import repository as dashboard_repository
from app.modules.m03_inventario import service as inventario_service
from app.modules.m16_theory_of_constraints import repository, schemas, validators


def restricciones_stock(db: Session) -> list[schemas.RestriccionProducto]:
    """Para cada producto, compara la demanda ya confirmada (ordenes
    CONFIRMADA, aun sin despachar) contra el stock disponible. Un deficit
    positivo significa que el stock de ese producto es la restriccion que
    impide despachar la demanda ya comprometida."""
    # inventario_service.saldos() exige un inventario_id: se usa el primero
    # registrado (mismo criterio ya aplicado en m01_dashboard/m13).
    inventarios = inventario_service.listar_inventarios(db)
    saldos = inventario_service.saldos(db, inventarios[0].id) if inventarios else []
    demanda = repository.demanda_confirmada_por_producto(db)

    resultado = []
    for s in saldos:
        pendiente = demanda.get(s["producto_id"], 0.0)
        if pendiente <= 0:
            continue
        deficit = pendiente - s["stock_total"]
        resultado.append(
            schemas.RestriccionProducto(
                producto_id=s["producto_id"],
                codigo=s["codigo_interno"],  # el dict de saldos usa "codigo_interno", no "codigo"
                nombre=s["nombre"],
                demanda_confirmada_pendiente=pendiente,
                stock_disponible=s["stock_total"],
                deficit=deficit,
                es_restriccion=deficit > 0,
            )
        )
    resultado.sort(key=lambda r: r.deficit, reverse=True)
    return resultado


def ordenes_en_espera(db: Session) -> list[schemas.OrdenEnEspera]:
    """Cola de ordenes ya CONFIRMADA esperando poder despacharse -- el
    trabajo acumulado frente a la restriccion. Mas antiguas primero."""
    # SQLite no conserva tzinfo: aunque confirmado_en se guarda con
    # datetime.now(timezone.utc), al leerlo de la BD vuelve offset-naive.
    # 'ahora' debe generarse igual de naive (equivalente en UTC) para que
    # la resta de mas abajo no falle con
    # "can't subtract offset-naive and offset-aware datetimes".
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    ordenes = repository.ordenes_confirmadas_en_espera(db)

    resultado = []
    for o in ordenes:
        monto_estimado = sum(
            float(item.cantidad) * float(item.precio_unitario_venta) for item in o.items
        )
        confirmado_en_naive = (
            o.confirmado_en.replace(tzinfo=None) if o.confirmado_en is not None else None
        )
        dias_esperando = (
            (ahora - confirmado_en_naive).total_seconds() / 86400
            if confirmado_en_naive is not None
            else None
        )
        resultado.append(
            schemas.OrdenEnEspera(
                orden_id=o.id,
                cliente_razon_social=o.cliente_razon_social,
                confirmado_en=o.confirmado_en,
                dias_esperando=round(dias_esperando, 2) if dias_esperando is not None else None,
                monto_estimado=monto_estimado,
            )
        )
    return resultado


def contabilidad_throughput(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> schemas.ContabilidadThroughput:
    """Contabilidad de throughput (T, I, OE) segun Theory of Constraints:
    T = ingreso de ventas despachadas - costo totalmente variable (costo
    real de la mercaderia vendida, leido del kardex); OE = gastos de
    operacion (costos adicionales del modulo 08); Utilidad neta = T - OE;
    I = inversion en inventario (valorizacion actual, modulo 01/03)."""
    validators.validar_rango_fechas(desde, hasta)

    ingreso = repository.ingreso_ventas_despachadas(db, desde, hasta)
    costo_variable = repository.costo_mercaderia_vendida(db, desde, hasta)
    throughput = ingreso - costo_variable

    operating_expense = repository.total_operating_expense(db, desde, hasta)
    utilidad_neta = throughput - operating_expense

    inversion_inventario = dashboard_repository.valor_total_inventario(db)
    roi_pct = (
        (utilidad_neta / inversion_inventario * 100) if inversion_inventario > 0 else None
    )

    return schemas.ContabilidadThroughput(
        desde=desde,
        hasta=hasta,
        ingreso_ventas_despachadas=ingreso,
        costo_mercaderia_vendida=costo_variable,
        throughput=throughput,
        operating_expense=operating_expense,
        utilidad_neta_toc=utilidad_neta,
        inversion_inventario=inversion_inventario,
        retorno_sobre_inversion_pct=(round(roi_pct, 2) if roi_pct is not None else None),
    )
