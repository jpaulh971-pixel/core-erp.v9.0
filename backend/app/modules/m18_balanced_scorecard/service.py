"""Logica de negocio del modulo m18_balanced_scorecard.

Balanced Scorecard (Kaplan & Norton) de solo lectura sobre Ventas,
Clientes, Proveedores, Productos, Costos, Inventario, Lean Six Sigma e
Inteligencia Comercial ya implementados. No agrega tablas propias ni
recalcula ninguna regla de negocio de esos modulos -- cada perspectiva
reutiliza directo el servicio/repositorio que ya la calcula, mismo
criterio de "no duplicar logica" que ya aplican m01_dashboard,
m14_inteligencia_tributaria y m16_theory_of_constraints.

Perspectivas:
- Financiera: reutiliza la contabilidad de throughput ya calculada por
  Theory of Constraints (modulo 16).
- Clientes: reutiliza el ranking de clientes de Inteligencia Comercial
  (modulo 13) para medir concentracion de cartera, mas totales propios
  de cobertura (clientes activos vs. clientes que efectivamente
  compraron en el periodo).
- Procesos internos: reutiliza mermas/DPMO y tiempos de ciclo de Lean
  Six Sigma (modulo 15), mas la cuenta de productos en restriccion de
  stock de Theory of Constraints (modulo 16).
- Aprendizaje y crecimiento: adaptada -- este ERP no tiene modulo de
  Recursos Humanos, asi que se mide con lo que existe: amplitud de
  catalogo (Productos), diversificacion de abastecimiento (Proveedores)
  y catalogo subutilizado (rotacion de inventario, modulo 13).
"""
from datetime import date

from sqlalchemy.orm import Session

from app.modules.m13_inteligencia_comercial import repository as ic_repository
from app.modules.m13_inteligencia_comercial import service as ic_service
from app.modules.m15_lean_six_sigma import service as lss_service
from app.modules.m16_theory_of_constraints import service as toc_service
from app.modules.m18_balanced_scorecard import repository, schemas, validators


def perspectiva_financiera(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> schemas.PerspectivaFinanciera:
    validators.validar_rango_fechas(desde, hasta)
    toc = toc_service.contabilidad_throughput(db, desde, hasta)

    margen_pct = (
        (toc.utilidad_neta_toc / toc.ingreso_ventas_despachadas * 100)
        if toc.ingreso_ventas_despachadas > 0
        else None
    )

    return schemas.PerspectivaFinanciera(
        desde=desde,
        hasta=hasta,
        ingreso_ventas_despachadas=toc.ingreso_ventas_despachadas,
        costo_mercaderia_vendida=toc.costo_mercaderia_vendida,
        costos_adicionales_operacion=toc.operating_expense,
        utilidad_neta=toc.utilidad_neta_toc,
        margen_neto_pct=round(margen_pct, 2) if margen_pct is not None else None,
    )


def perspectiva_clientes(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> schemas.PerspectivaClientes:
    validators.validar_rango_fechas(desde, hasta)

    activos = repository.clientes_activos_total(db)
    con_compra = repository.clientes_distintos_con_despacho(db, desde, hasta)
    ordenes = repository.cantidad_ordenes_despachadas(db, desde, hasta)

    toc = toc_service.contabilidad_throughput(db, desde, hasta)
    ingreso_periodo = toc.ingreso_ventas_despachadas

    top3 = ic_repository.clientes_top(db, limit=3, desde=desde, hasta=hasta)
    monto_top3 = sum(c["monto_comprado"] for c in top3)

    pct_cobertura = (con_compra / activos * 100) if activos > 0 else None
    ticket_promedio = (ingreso_periodo / ordenes) if ordenes > 0 else None
    concentracion_pct = (monto_top3 / ingreso_periodo * 100) if ingreso_periodo > 0 else None

    return schemas.PerspectivaClientes(
        desde=desde,
        hasta=hasta,
        clientes_activos_total=activos,
        clientes_con_compra_en_periodo=con_compra,
        pct_clientes_activos_con_compra=(
            round(pct_cobertura, 2) if pct_cobertura is not None else None
        ),
        ticket_promedio_venta=(
            round(ticket_promedio, 2) if ticket_promedio is not None else None
        ),
        concentracion_top3_clientes_pct=(
            round(concentracion_pct, 2) if concentracion_pct is not None else None
        ),
    )


def perspectiva_procesos_internos(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> schemas.PerspectivaProcesosInternos:
    validators.validar_rango_fechas(desde, hasta)

    mermas = lss_service.resumen_mermas(db, desde, hasta)
    ciclo_compras = lss_service.tiempos_ciclo_compras(db, desde, hasta)
    ciclo_ventas = lss_service.tiempos_ciclo_ventas(db, desde, hasta)
    restricciones = toc_service.restricciones_stock(db)
    productos_en_restriccion = sum(1 for r in restricciones if r.es_restriccion)

    return schemas.PerspectivaProcesosInternos(
        desde=desde,
        hasta=hasta,
        dpmo_mermas=mermas.dpmo,
        nivel_sigma=mermas.nivel_sigma,
        dias_promedio_ciclo_compras=ciclo_compras.dias_promedio_total,
        dias_promedio_ciclo_ventas=ciclo_ventas.dias_promedio_confirmacion_a_despacho,
        productos_en_restriccion_stock=productos_en_restriccion,
    )


def perspectiva_aprendizaje_crecimiento(
    db: Session,
) -> schemas.PerspectivaAprendizajeCrecimiento:
    rotacion = ic_service.rotacion_inventario(db)
    sin_movimiento = sum(1 for r in rotacion if r.sin_movimiento)

    return schemas.PerspectivaAprendizajeCrecimiento(
        productos_activos_total=repository.productos_activos_total(db),
        proveedores_activos_total=repository.proveedores_activos_total(db),
        productos_sin_movimiento=sin_movimiento,
    )


def tablero(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> schemas.TableroBalancedScorecard:
    validators.validar_rango_fechas(desde, hasta)
    return schemas.TableroBalancedScorecard(
        desde=desde,
        hasta=hasta,
        financiera=perspectiva_financiera(db, desde, hasta),
        clientes=perspectiva_clientes(db, desde, hasta),
        procesos_internos=perspectiva_procesos_internos(db, desde, hasta),
        aprendizaje_crecimiento=perspectiva_aprendizaje_crecimiento(db),
    )
