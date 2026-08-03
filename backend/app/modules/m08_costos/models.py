"""Modulo 08 - Costos.

No duplica costos: el costo real de la mercaderia que sale del almacen ya
queda registrado en cada MovimientoKardex (modulo 03) al momento del
consumo FEFO. Este modulo solo agrega los costos adicionales (flete,
seguro, aduana, almacenaje) que no viven en Inventario ni en Compras, y
con eso arma costeo de compra (landed cost) y rentabilidad de exportacion.
"""
from sqlalchemy import Column, DateTime, Enum, Integer, Numeric, String
from sqlalchemy.sql import func

from app.database import Base

TIPOS_DOCUMENTO = ("COMPRA", "EXPORTACION")
TIPOS_COSTO = ("FLETE", "SEGURO", "ADUANA", "ALMACENAJE", "MANIPULEO", "OTRO")


class CostoAdicional(Base):
    __tablename__ = "costos_adicionales"

    id = Column(Integer, primary_key=True, index=True)
    tipo_documento = Column(
        Enum(*TIPOS_DOCUMENTO, name="tipo_documento_costo_enum"), nullable=False
    )
    documento_id = Column(Integer, nullable=False, index=True)
    tipo_costo = Column(Enum(*TIPOS_COSTO, name="tipo_costo_enum"), nullable=False)
    descripcion = Column(String(255), nullable=True)
    monto = Column(Numeric(14, 4), nullable=False)
    moneda = Column(String(3), nullable=False, default="USD")
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
