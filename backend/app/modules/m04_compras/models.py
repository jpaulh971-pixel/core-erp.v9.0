"""Modulo 04 - Compras.

Orden de compra a proveedor, con items por producto. Maquina de estados:
SOLICITADA -> APROBADA -> RECIBIDA (recepcion genera ingreso real de
inventario via el modulo 03, en el Inventario indicado por
inventario_destino_id). SOLICITADA/APROBADA -> CANCELADA.

inventario_destino_id se agrega para que Compras siga funcionando con
el m03 multi-inventario (antes habia un solo almacen implicito).
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

ESTADOS_OC = ("SOLICITADA", "APROBADA", "RECIBIDA", "CANCELADA")


class OrdenCompra(Base):
    __tablename__ = "ordenes_compra"

    id = Column(Integer, primary_key=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False, index=True)
    inventario_destino_id = Column(Integer, ForeignKey("inventarios.id"), nullable=False, index=True)
    estado = Column(Enum(*ESTADOS_OC, name="estado_oc_enum"), nullable=False, default="SOLICITADA")
    moneda = Column(String(3), nullable=False, default="USD")
    observaciones = Column(String(500), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    aprobado_en = Column(DateTime(timezone=True), nullable=True)
    recibido_en = Column(DateTime(timezone=True), nullable=True)
    cancelado_en = Column(DateTime(timezone=True), nullable=True)

    # --- Campos opcionales de Fase 9 (Importacion de Compras Nacionalizadas).
    # Todos nullable: no afectan ninguna orden creada por el flujo manual
    # existente (formulario "Nueva orden de compra"), que nunca los envia.
    numero_orden_externo = Column(String(50), nullable=True)  # "Pedido"/"Orden Compra" del Excel del cliente
    invoice = Column(String(50), nullable=True)  # "Factura"
    documento_aduanero = Column(String(50), nullable=True)  # "DUA"
    pais_origen = Column(String(100), nullable=True)
    fecha_documento = Column(DateTime(timezone=True), nullable=True)  # "Fecha de Emision Factura"

    # --- Campos opcionales agregados para soportar el formato de Excel del
    # cliente (COMPRAS_ECO_NEOAGROX_2026.xlsx). Todos nullable: no afectan
    # ninguna orden creada por el flujo existente (manual o Fase 9).
    dias_credito = Column(Integer, nullable=True)  # "Dias de Credito"
    fecha_vencimiento_factura = Column(DateTime(timezone=True), nullable=True)  # "Fecha de Vencimiento" (de la factura, no del producto). Si no viene explicita, se calcula como fecha_documento + dias_credito.

    proveedor = relationship("Proveedor")
    inventario_destino = relationship("Inventario")
    items = relationship("OrdenCompraItem", back_populates="orden", cascade="all, delete-orphan")


class OrdenCompraItem(Base):
    __tablename__ = "ordenes_compra_items"

    id = Column(Integer, primary_key=True, index=True)
    orden_compra_id = Column(Integer, ForeignKey("ordenes_compra.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    cantidad = Column(Numeric(14, 3), nullable=False)
    costo_unitario = Column(Numeric(14, 4), nullable=False)

    # --- Campos opcionales de Fase 9 (Importacion de Compras Nacionalizadas).
    # Si vienen (import Excel), recibir_orden() los usa tal cual para el
    # ingreso de inventario (mismo registrar_ingreso de siempre). Si no
    # vienen (flujo manual existente), el comportamiento no cambia:
    # recibir_orden() sigue autogenerando el codigo de lote como antes.
    lote = Column(String(50), nullable=True)
    fecha_elaboracion = Column(DateTime(timezone=True), nullable=True)
    fecha_vencimiento = Column(DateTime(timezone=True), nullable=True)
    observaciones = Column(String(500), nullable=True)

    # --- Campos opcionales agregados para soportar el formato de Excel del
    # cliente (COMPRAS_ECO_NEOAGROX_2026.xlsx). Todos nullable: solo
    # datos de referencia/trazabilidad, no cambian la logica de inventario.
    presentacion = Column(String(50), nullable=True)  # "presentacion" (Bidon, Cilindro, etc.)
    unidad_medida = Column(String(30), nullable=True)  # "Unida de Medida" (LITROS, etc.)
    cantidad_por_unidad = Column(Numeric(14, 3), nullable=True)  # "CANTIDAD POR UNIDAD"
    concepto = Column(String(200), nullable=True)  # "CONCEPTO"/"Descripcion" tal como llega del Excel del cliente

    orden = relationship("OrdenCompra", back_populates="items")
    producto = relationship("Producto")
