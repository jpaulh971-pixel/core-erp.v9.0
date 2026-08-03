from sqlalchemy.orm import Session

from app.modules.m03_inventario.models import MovimientoKardex
from app.modules.m08_costos.models import CostoAdicional


def crear_costo(db: Session, costo: CostoAdicional) -> CostoAdicional:
    db.add(costo)
    db.commit()
    db.refresh(costo)
    return costo


def listar_costos_por_documento(
    db: Session, tipo_documento: str, documento_id: int
) -> list[CostoAdicional]:
    return (
        db.query(CostoAdicional)
        .filter(
            CostoAdicional.tipo_documento == tipo_documento,
            CostoAdicional.documento_id == documento_id,
        )
        .order_by(CostoAdicional.creado_en)
        .all()
    )


def salidas_kardex_por_referencia(db: Session, referencia: str) -> list[MovimientoKardex]:
    return (
        db.query(MovimientoKardex)
        .filter(
            MovimientoKardex.tipo_movimiento == "SALIDA",
            MovimientoKardex.referencia == referencia,
        )
        .all()
    )
