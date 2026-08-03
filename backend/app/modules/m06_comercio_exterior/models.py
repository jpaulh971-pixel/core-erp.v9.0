"""Modulo 06 - Comercio Exterior.

Declaracion de exportacion (tipo DUA) con items. Al pasar a EMBARCADA
se descuenta stock real de Inventario via FEFO (modulo 03).

Nota de diseno: el cliente/importador se modela como campos simples
(nombre, pais, incoterm) porque el modulo 11 Clientes aun no existe.
Cuando se implemente, se reemplaza por una FK sin romper el flujo.
"""
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

ESTADOS_DECLARACION = ("BORRADOR", "CONFIRMADA", "EMBARCADA", "CANCELADA")
INCOTERMS_VALIDOS = ("EXW", "FOB", "CIF", "CFR", "FCA", "DAP", "DDP")


class DeclaracionExportacion(Base):
    __tablename__ = "declaraciones_exportacion"

    id = Column(Integer, primary_key=True, index=True)
    numero_dua = Column(String(30), unique=True, nullable=True)
    cliente_nombre = Column(String(200), nullable=False)
    pais_destino = Column(String(80), nullable=False)
    incoterm = Column(String(5), nullable=False, default="FOB")
    moneda = Column(String(3), nullable=False, default="USD")
    inventario_origen_id = Column(Integer, ForeignKey("inventarios.id"), nullable=True, index=True)
    estado = Column(
        Enum(*ESTADOS_DECLARACION, name="estado_declaracion_enum"),
        nullable=False,
        default="BORRADOR",
    )
    observaciones = Column(String(500), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    confirmado_en = Column(DateTime(timezone=True), nullable=True)
    embarcado_en = Column(DateTime(timezone=True), nullable=True)
    cancelado_en = Column(DateTime(timezone=True), nullable=True)

    items = relationship(
        "DeclaracionExportacionItem", back_populates="declaracion", cascade="all, delete-orphan"
    )


class DeclaracionExportacionItem(Base):
    __tablename__ = "declaraciones_exportacion_items"

    id = Column(Integer, primary_key=True, index=True)
    declaracion_id = Column(
        Integer, ForeignKey("declaraciones_exportacion.id"), nullable=False, index=True
    )
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    cantidad = Column(Numeric(14, 3), nullable=False)
    precio_unitario_exportacion = Column(Numeric(14, 4), nullable=False)

    declaracion = relationship("DeclaracionExportacion", back_populates="items")
    producto = relationship("Producto")
