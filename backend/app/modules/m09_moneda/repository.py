from datetime import date

from sqlalchemy.orm import Session

from app.modules.m09_moneda.models import TipoCambio


def crear_tipo_cambio(db: Session, tipo_cambio: TipoCambio) -> TipoCambio:
    db.add(tipo_cambio)
    db.commit()
    db.refresh(tipo_cambio)
    return tipo_cambio


def obtener_por_par_y_fecha(
    db: Session, moneda_origen: str, moneda_destino: str, fecha: date
) -> TipoCambio | None:
    return (
        db.query(TipoCambio)
        .filter(
            TipoCambio.moneda_origen == moneda_origen,
            TipoCambio.moneda_destino == moneda_destino,
            TipoCambio.fecha == fecha,
        )
        .first()
    )


def obtener_vigente(
    db: Session, moneda_origen: str, moneda_destino: str, fecha: date
) -> TipoCambio | None:
    """Ultimo tipo de cambio registrado para el par con fecha <= fecha dada."""
    return (
        db.query(TipoCambio)
        .filter(
            TipoCambio.moneda_origen == moneda_origen,
            TipoCambio.moneda_destino == moneda_destino,
            TipoCambio.fecha <= fecha,
        )
        .order_by(TipoCambio.fecha.desc())
        .first()
    )


def listar_por_par(db: Session, moneda_origen: str, moneda_destino: str) -> list[TipoCambio]:
    return (
        db.query(TipoCambio)
        .filter(
            TipoCambio.moneda_origen == moneda_origen,
            TipoCambio.moneda_destino == moneda_destino,
        )
        .order_by(TipoCambio.fecha.desc())
        .all()
    )
