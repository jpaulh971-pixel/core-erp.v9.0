"""Modulo 17 - Guias de Remision.

Documento de traslado que se limita a LEER informacion ya generada por
Ventas (m10) e Inventario (m03): no crea stock, no modifica Kardex y no
modifica cantidades de inventario.

Trazabilidad esperada:

    Orden de Venta (m10)
        -> Despacho (m10.despachar_orden)
            -> Movimiento Kardex SALIDA (m03, referencia = despacho)
                -> Lote usado (FEFO, m03)
                    -> Detalle Guia de Remision (lote_id real)
                        -> Cliente (m11)

Si un despacho no dejo un movimiento Kardex con lote_id trazable, la guia
NO se genera (no se inventa el lote): ver validators.validar_trazabilidad_lote.
"""
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

ESTADOS_GUIA_REMISION = ("EMITIDA", "ANULADA")


class GuiaRemision(Base):
    __tablename__ = "guias_remision"

    id = Column(Integer, primary_key=True, index=True)
    numero_guia = Column(String(30), unique=True, nullable=False, index=True)
    fecha_emision = Column(DateTime(timezone=True), server_default=func.now())
    estado = Column(
        Enum(*ESTADOS_GUIA_REMISION, name="estado_guia_remision_enum"),
        nullable=False,
        default="EMITIDA",
    )
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    orden_venta_id = Column(Integer, ForeignKey("ordenes_venta.id"), nullable=True, index=True)
    inventario_id = Column(Integer, ForeignKey("inventarios.id"), nullable=False, index=True)
    motivo_traslado = Column(String(200), nullable=False, default="VENTA")
    anulado_en = Column(DateTime(timezone=True), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    cliente = relationship("Cliente")
    orden_venta = relationship("OrdenVenta")
    inventario = relationship("Inventario")
    detalles = relationship(
        "GuiaRemisionDetalle", back_populates="guia", cascade="all, delete-orphan"
    )

    @property
    def cliente_razon_social(self) -> str:
        return self.cliente.razon_social


class GuiaRemisionDetalle(Base):
    """Un renglon por lote real consumido (via Kardex/FEFO), nunca un
    lote inventado. Un mismo producto puede tener varios renglones si el
    despacho FEFO consumio mas de un lote."""

    __tablename__ = "guias_remision_detalle"

    id = Column(Integer, primary_key=True, index=True)
    guia_id = Column(Integer, ForeignKey("guias_remision.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    cantidad = Column(Numeric(14, 3), nullable=False)
    unidad_medida = Column(String(20), nullable=False, default="UND")

    guia = relationship("GuiaRemision", back_populates="detalles")
    producto = relationship("Producto")
    lote = relationship("Lote")
