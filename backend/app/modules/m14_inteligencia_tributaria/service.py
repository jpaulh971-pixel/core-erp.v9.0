"""Logica de negocio del modulo m14_inteligencia_tributaria.

Inteligencia tributaria de solo lectura sobre los comprobantes
electronicos ya emitidos por SUNAT (modulo 12): resumen de IGV para
declarar, registro de ventas y control de anulaciones. No redefine
ninguna regla de emision, serie/correlativo ni transicion de estado --
esas siguen viviendo unicamente en m12_sunat.
"""
from datetime import date

from sqlalchemy.orm import Session

from app.modules.m14_inteligencia_tributaria import repository, schemas, validators


def resumen_igv(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> schemas.ResumenIGV:
    validators.validar_rango_fechas(desde, hasta)
    por_tipo = repository.resumen_por_tipo_comprobante(db, desde, hasta)

    return schemas.ResumenIGV(
        desde=desde,
        hasta=hasta,
        por_tipo_comprobante=[schemas.ResumenPorTipoComprobante(**f) for f in por_tipo],
        total_comprobantes=sum(f["cantidad"] for f in por_tipo),
        total_subtotal=sum(f["subtotal"] for f in por_tipo),
        total_igv=sum(f["igv"] for f in por_tipo),
        total_general=sum(f["total"] for f in por_tipo),
    )


def libro_ventas(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> list[schemas.ComprobanteLibroVentas]:
    validators.validar_rango_fechas(desde, hasta)
    comprobantes = repository.libro_ventas(db, desde, hasta)
    return [schemas.ComprobanteLibroVentas.model_validate(c) for c in comprobantes]


def comprobantes_anulados(
    db: Session, desde: date | None = None, hasta: date | None = None
) -> list[schemas.ComprobanteAnulado]:
    validators.validar_rango_fechas(desde, hasta)
    comprobantes = repository.comprobantes_anulados(db, desde, hasta)
    return [schemas.ComprobanteAnulado.model_validate(c) for c in comprobantes]
