"""Modulo 12 - SUNAT.

Emision de comprobantes electronicos (Factura/Boleta) para las ordenes
de venta del modulo 10. No recalcula ni duplica montos de negocio: el
subtotal se deriva directo de los items de la OrdenVenta (ya despachada,
es decir, mercaderia real y fisicamente entregada). Este modulo solo
agrega lo que le compete a SUNAT: tipo de comprobante, serie/correlativo,
IGV y el ciclo de vida del comprobante en si.

No hay integracion real con la API de SUNAT (fuera de alcance de este
ERP); se modela el comprobante y su ciclo de vida localmente.
"""
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

TIPOS_COMPROBANTE = ("FACTURA", "BOLETA")
ESTADOS_COMPROBANTE = ("EMITIDO", "ACEPTADO", "RECHAZADO", "ANULADO")
TASA_IGV = 0.18

SERIES_POR_TIPO = {"FACTURA": "F001", "BOLETA": "B001"}


class ComprobanteElectronico(Base):
    __tablename__ = "comprobantes_electronicos"
    __table_args__ = (
        UniqueConstraint("orden_venta_id", name="uq_comprobante_por_orden"),
    )

    id = Column(Integer, primary_key=True, index=True)
    orden_venta_id = Column(Integer, ForeignKey("ordenes_venta.id"), nullable=False, index=True)
    tipo_comprobante = Column(
        Enum(*TIPOS_COMPROBANTE, name="tipo_comprobante_enum"), nullable=False
    )
    serie = Column(String(4), nullable=False)
    correlativo = Column(Integer, nullable=False)

    # Snapshot del cliente al momento de emitir: un comprobante ya emitido
    # no debe cambiar aunque el cliente actualice sus datos despues.
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    cliente_ruc = Column(String(20), nullable=False)
    cliente_razon_social = Column(String(200), nullable=False)

    moneda = Column(String(3), nullable=False)
    subtotal = Column(Numeric(14, 2), nullable=False)
    igv = Column(Numeric(14, 2), nullable=False)
    total = Column(Numeric(14, 2), nullable=False)

    estado = Column(
        Enum(*ESTADOS_COMPROBANTE, name="estado_comprobante_enum"),
        nullable=False,
        default="EMITIDO",
    )
    motivo_anulacion = Column(String(300), nullable=True)

    emitido_en = Column(DateTime(timezone=True), server_default=func.now())
    anulado_en = Column(DateTime(timezone=True), nullable=True)

    orden = relationship("OrdenVenta")

    @property
    def numero_completo(self) -> str:
        return f"{self.serie}-{self.correlativo:08d}"
