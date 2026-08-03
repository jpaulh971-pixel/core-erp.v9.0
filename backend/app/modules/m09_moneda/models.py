"""Modulo 09 - Moneda.

Registra tipos de cambio entre pares de monedas por fecha y expone la
conversion de montos. Es un modulo de soporte: no reescribe montos de
otros modulos (Costos, Compras, Comercio Exterior siguen guardando el
monto en su moneda original); estos consultan aqui el tipo de cambio
vigente cuando necesitan expresar un monto en otra moneda.
"""
from sqlalchemy import Column, Date, DateTime, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class TipoCambio(Base):
    __tablename__ = "tipos_cambio"
    __table_args__ = (
        UniqueConstraint(
            "moneda_origen", "moneda_destino", "fecha", name="uq_tipo_cambio_par_fecha"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    moneda_origen = Column(String(3), nullable=False, index=True)
    moneda_destino = Column(String(3), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    # Cuantas unidades de moneda_destino equivalen a 1 unidad de moneda_origen
    valor = Column(Numeric(18, 6), nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
