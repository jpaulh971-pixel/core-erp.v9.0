from datetime import date

from sqlalchemy.orm import Session

from app.modules.m09_moneda import repository, schemas, validators
from app.modules.m09_moneda.models import TipoCambio


def registrar_tipo_cambio(db: Session, datos: schemas.TipoCambioCrear) -> TipoCambio:
    moneda_origen = datos.moneda_origen.upper()
    moneda_destino = datos.moneda_destino.upper()
    validators.validar_codigo_moneda(moneda_origen)
    validators.validar_codigo_moneda(moneda_destino)
    validators.validar_par_distinto(moneda_origen, moneda_destino)

    existente = repository.obtener_por_par_y_fecha(db, moneda_origen, moneda_destino, datos.fecha)
    if existente is not None:
        existente.valor = datos.valor
        db.commit()
        db.refresh(existente)
        return existente

    tipo_cambio = TipoCambio(
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        fecha=datos.fecha,
        valor=datos.valor,
    )
    return repository.crear_tipo_cambio(db, tipo_cambio)


def _buscar_vigente_directo_o_inverso(
    db: Session, moneda_origen: str, moneda_destino: str, fecha: date
):
    """Busca el par directo; si no existe, busca el inverso y devuelve 1/valor.

    Retorna una tupla (valor, fecha_tipo_cambio, invertido) o None si no hay
    ningun tipo de cambio registrado para el par en ninguna direccion.
    """
    directo = repository.obtener_vigente(db, moneda_origen, moneda_destino, fecha)
    if directo is not None:
        return float(directo.valor), directo.fecha, False

    inverso = repository.obtener_vigente(db, moneda_destino, moneda_origen, fecha)
    if inverso is not None:
        return 1.0 / float(inverso.valor), inverso.fecha, True

    return None


def obtener_tipo_cambio_vigente(
    db: Session, moneda_origen: str, moneda_destino: str, fecha: date | None = None
) -> schemas.TipoCambioVigenteOut:
    moneda_origen = moneda_origen.upper()
    moneda_destino = moneda_destino.upper()
    validators.validar_codigo_moneda(moneda_origen)
    validators.validar_codigo_moneda(moneda_destino)
    fecha_solicitada = fecha or date.today()

    if moneda_origen == moneda_destino:
        return schemas.TipoCambioVigenteOut(
            moneda_origen=moneda_origen,
            moneda_destino=moneda_destino,
            fecha_solicitada=fecha_solicitada,
            fecha_tipo_cambio=fecha_solicitada,
            valor=1.0,
            invertido=False,
        )

    resultado = _buscar_vigente_directo_o_inverso(
        db, moneda_origen, moneda_destino, fecha_solicitada
    )
    validators.validar_tipo_cambio_existe(resultado, moneda_origen, moneda_destino)
    valor, fecha_tipo_cambio, invertido = resultado

    return schemas.TipoCambioVigenteOut(
        moneda_origen=moneda_origen,
        moneda_destino=moneda_destino,
        fecha_solicitada=fecha_solicitada,
        fecha_tipo_cambio=fecha_tipo_cambio,
        valor=valor,
        invertido=invertido,
    )


def convertir(
    db: Session,
    monto: float,
    moneda_origen: str,
    moneda_destino: str,
    fecha: date | None = None,
) -> schemas.ConversionOut:
    fecha_solicitada = fecha or date.today()
    vigente = obtener_tipo_cambio_vigente(db, moneda_origen, moneda_destino, fecha_solicitada)

    return schemas.ConversionOut(
        monto_origen=monto,
        moneda_origen=vigente.moneda_origen,
        moneda_destino=vigente.moneda_destino,
        fecha=fecha_solicitada,
        fecha_tipo_cambio=vigente.fecha_tipo_cambio,
        tipo_cambio_aplicado=vigente.valor,
        monto_convertido=monto * vigente.valor,
    )


def listar_historial_par(db: Session, moneda_origen: str, moneda_destino: str) -> list[TipoCambio]:
    return repository.listar_por_par(db, moneda_origen.upper(), moneda_destino.upper())
