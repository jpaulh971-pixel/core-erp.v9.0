"""Logica de negocio del modulo m15_lean_six_sigma.

Metricas Lean Six Sigma de solo lectura sobre Inventario, Compras y
Ventas ya implementados: mermas de inventario (DPMO / nivel sigma) y
tiempos de ciclo. No redefine ninguna regla de esos modulos (FEFO,
maquinas de estado, etc.) -- solo mide lo que ya quedo registrado.
"""
import math
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.modules.m15_lean_six_sigma import repository, schemas, validators


def _dias_entre(inicio: datetime | None, fin: datetime | None) -> float | None:
    if inicio is None or fin is None:
        return None
    return (fin - inicio).total_seconds() / 86400


def _dpmo_a_nivel_sigma(dpmo: float) -> float:
    """Aproximacion de Bothe para el nivel sigma a partir del DPMO.
    Sin defectos (DPMO=0) se reporta como el techo practico de 6.0."""
    if dpmo <= 0:
        return 6.0
    proporcion_defectuosa = min(dpmo / 1_000_000, 0.9999)
    valor = 29.37 - 2.221 * math.log(proporcion_defectuosa * 1_000_000)
    if valor < 0:
        return 6.0
    return round(0.8406 + math.sqrt(valor), 2)


def resumen_mermas(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> schemas.ResumenMermas:
    validators.validar_rango_fechas(desde, hasta)

    total_movimientos = repository.total_movimientos_kardex(db, desde, hasta)
    mermas = repository.mermas_por_producto(db, desde, hasta)

    total_eventos_merma = sum(m["eventos"] for m in mermas)
    cantidad_total_mermada = sum(m["cantidad_mermada"] for m in mermas)

    # Oportunidades = total de movimientos de kardex del periodo; defectos =
    # eventos de ajuste negativo (discrepancias detectadas entre stock
    # teorico y stock real).
    dpmo = (total_eventos_merma / total_movimientos * 1_000_000) if total_movimientos > 0 else 0.0

    return schemas.ResumenMermas(
        desde=desde,
        hasta=hasta,
        total_movimientos_kardex=total_movimientos,
        total_eventos_merma=total_eventos_merma,
        cantidad_total_mermada=cantidad_total_mermada,
        dpmo=round(dpmo, 2),
        nivel_sigma=_dpmo_a_nivel_sigma(dpmo),
        top_productos=[schemas.MermaProducto(**m) for m in mermas[:10]],
    )


def tiempos_ciclo_compras(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> schemas.TiemposCicloCompras:
    validators.validar_rango_fechas(desde, hasta)
    ordenes = repository.ordenes_compra_recibidas(db, desde, hasta)

    dias_aprobacion = [
        d for o in ordenes if (d := _dias_entre(o.creado_en, o.aprobado_en)) is not None
    ]
    dias_recepcion = [
        d for o in ordenes if (d := _dias_entre(o.aprobado_en, o.recibido_en)) is not None
    ]
    dias_totales = [
        d for o in ordenes if (d := _dias_entre(o.creado_en, o.recibido_en)) is not None
    ]

    return schemas.TiemposCicloCompras(
        ordenes_evaluadas=len(ordenes),
        dias_promedio_solicitud_a_aprobacion=(
            round(sum(dias_aprobacion) / len(dias_aprobacion), 2) if dias_aprobacion else None
        ),
        dias_promedio_aprobacion_a_recepcion=(
            round(sum(dias_recepcion) / len(dias_recepcion), 2) if dias_recepcion else None
        ),
        dias_promedio_total=(
            round(sum(dias_totales) / len(dias_totales), 2) if dias_totales else None
        ),
        dias_min_total=round(min(dias_totales), 2) if dias_totales else None,
        dias_max_total=round(max(dias_totales), 2) if dias_totales else None,
    )


def tiempos_ciclo_ventas(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> schemas.TiemposCicloVentas:
    validators.validar_rango_fechas(desde, hasta)
    ordenes = repository.ordenes_venta_despachadas(db, desde, hasta)

    dias = [
        d for o in ordenes if (d := _dias_entre(o.confirmado_en, o.despachado_en)) is not None
    ]

    return schemas.TiemposCicloVentas(
        ordenes_evaluadas=len(ordenes),
        dias_promedio_confirmacion_a_despacho=(
            round(sum(dias) / len(dias), 2) if dias else None
        ),
        dias_min=round(min(dias), 2) if dias else None,
        dias_max=round(max(dias), 2) if dias else None,
    )
