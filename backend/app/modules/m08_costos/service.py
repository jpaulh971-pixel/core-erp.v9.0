from sqlalchemy.orm import Session

from app.modules.m04_compras import service as compras_service
from app.modules.m06_comercio_exterior import service as comercio_exterior_service
from app.modules.m08_costos import repository, schemas, validators
from app.modules.m08_costos.models import CostoAdicional
from app.modules.m09_moneda import service as moneda_service
from app.modules.m20_configuracion.models import ParametroSistema


def registrar_costo_adicional(
    db: Session, datos: schemas.CostoAdicionalCrear
) -> CostoAdicional:
    validators.validar_tipo_documento(datos.tipo_documento)
    validators.validar_tipo_costo(datos.tipo_costo)

    if datos.tipo_documento == "COMPRA":
        validators.validar_documento_referenciado(
            compras_service.repository.obtener_orden(db, datos.documento_id)
        )
    else:
        validators.validar_documento_referenciado(
            comercio_exterior_service.repository.obtener(db, datos.documento_id)
        )

    costo = CostoAdicional(**datos.model_dump())
    return repository.crear_costo(db, costo)


def _obtener_moneda_base(db: Session) -> str:
    parametro = (
        db.query(ParametroSistema).filter_by(clave="MONEDA_BASE").first()
    )
    return parametro.valor.upper() if parametro else "USD"


def _total_adicionales_en_moneda_base(
    db: Session, adicionales: list[CostoAdicional], moneda_base: str
) -> float:
    """Convierte cada costo adicional a la moneda base antes de sumarlo,
    usando el tipo de cambio vigente a la fecha en que se registro el
    costo (m09_moneda.convertir)."""
    total = 0.0
    for c in adicionales:
        moneda_costo = c.moneda.upper()
        monto = float(c.monto)
        if moneda_costo == moneda_base:
            total += monto
        else:
            fecha_costo = c.creado_en.date() if c.creado_en else None
            conversion = moneda_service.convertir(
                db, monto, moneda_costo, moneda_base, fecha_costo
            )
            total += conversion.monto_convertido
    return total


def costeo_compra(db: Session, orden_compra_id: int) -> schemas.CosteoCompraOut:
    orden = compras_service.obtener_orden(db, orden_compra_id)

    valor_mercaderia = sum(
        float(item.cantidad) * float(item.costo_unitario) for item in orden.items
    )
    cantidad_total = sum(float(item.cantidad) for item in orden.items)

    adicionales = repository.listar_costos_por_documento(db, "COMPRA", orden_compra_id)
    moneda_base = _obtener_moneda_base(db)
    total_adicionales = _total_adicionales_en_moneda_base(db, adicionales, moneda_base)

    costo_total = valor_mercaderia + total_adicionales
    costo_unitario_ponderado = costo_total / cantidad_total if cantidad_total > 0 else 0.0

    return schemas.CosteoCompraOut(
        orden_compra_id=orden_compra_id,
        valor_mercaderia=valor_mercaderia,
        costos_adicionales=total_adicionales,
        costo_total=costo_total,
        cantidad_total=cantidad_total,
        costo_unitario_ponderado=costo_unitario_ponderado,
        detalle_costos_adicionales=adicionales,
    )


def rentabilidad_exportacion(
    db: Session, declaracion_id: int
) -> schemas.RentabilidadExportacionOut:
    declaracion = comercio_exterior_service.obtener_declaracion(db, declaracion_id)

    ingreso = sum(
        float(item.cantidad) * float(item.precio_unitario_exportacion)
        for item in declaracion.items
    )

    # Costo real: se lee directo del kardex (costo del lote consumido en el
    # momento del embarque), no se recalcula ni se asume un promedio nuevo.
    referencia = f"Embarque declaracion de exportacion #{declaracion.id}"
    salidas = repository.salidas_kardex_por_referencia(db, referencia)
    costo_mercaderia_real = sum(
        float(m.cantidad) * float(m.costo_unitario) for m in salidas
    )

    adicionales = repository.listar_costos_por_documento(
        db, "EXPORTACION", declaracion_id
    )
    moneda_base = _obtener_moneda_base(db)
    total_adicionales = _total_adicionales_en_moneda_base(db, adicionales, moneda_base)

    utilidad_bruta = ingreso - costo_mercaderia_real - total_adicionales
    margen_pct = (utilidad_bruta / ingreso * 100) if ingreso > 0 else 0.0

    return schemas.RentabilidadExportacionOut(
        declaracion_id=declaracion_id,
        ingreso_exportacion=ingreso,
        costo_mercaderia_real=costo_mercaderia_real,
        costos_adicionales=total_adicionales,
        utilidad_bruta=utilidad_bruta,
        margen_pct=margen_pct,
        detalle_costos_adicionales=adicionales,
    )
