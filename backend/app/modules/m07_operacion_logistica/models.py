"""Modulo 07 - Operacion Logistica.

Trazabilidad fisica de un lote de mercaderia dentro del almacen central,
desde la recepcion hasta el cierre de la operacion. Maquina de estados
lineal (sin saltos, sin retrocesos):

RECEPCION -> INSPECCION -> UBICACION -> DISPONIBLE -> RESERVADO ->
PICKING -> PACKING -> CARGA -> DESPACHO -> ENTREGADO -> CERRADO

No duplica tablas de otros modulos: reutiliza Producto (02), Proveedor
(05), Lote/MovimientoKardex (03), OrdenCompra (04) y OrdenVenta (10) via
FK opcional. Ver docstring de service.py para las reglas exactas de
integracion (cuando este modulo ejecuta el movimiento real de inventario
y cuando solo lo valida, para no duplicar el descuento de stock que ya
hacen Compras y Ventas).
"""
from sqlalchemy import (
    Boolean,
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

ESTADOS_OL = (
    "RECEPCION",
    "INSPECCION",
    "UBICACION",
    "DISPONIBLE",
    "RESERVADO",
    "PICKING",
    "PACKING",
    "CARGA",
    "DESPACHO",
    "ENTREGADO",
    "CERRADO",
)


class OperacionLogistica(Base):
    __tablename__ = "operaciones_logisticas"

    id = Column(Integer, primary_key=True, index=True)
    estado = Column(
        Enum(*ESTADOS_OL, name="estado_operacion_logistica_enum"),
        nullable=False,
        default="RECEPCION",
    )

    # --- Recepcion ---
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False, index=True)
    orden_compra_id = Column(Integer, ForeignKey("ordenes_compra.id"), nullable=True, index=True)
    inventario_id = Column(Integer, ForeignKey("inventarios.id"), nullable=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=True, index=True)
    codigo_lote = Column(String(50), nullable=False)
    cantidad = Column(Numeric(14, 3), nullable=False)
    costo_unitario = Column(Numeric(14, 4), nullable=False)

    # --- Inspeccion ---
    conforme = Column(Boolean, nullable=True)
    observaciones_inspeccion = Column(String(500), nullable=True)

    # --- Ubicacion ---
    rack = Column(String(30), nullable=True)
    pasillo = Column(String(30), nullable=True)
    ubicacion_fisica = Column(String(100), nullable=True)

    # --- Reservado ---
    orden_venta_id = Column(Integer, ForeignKey("ordenes_venta.id"), nullable=True, index=True)

    # --- Picking ---
    lote_picking_id = Column(Integer, ForeignKey("lotes.id"), nullable=True, index=True)
    cantidad_picking = Column(Numeric(14, 3), nullable=True)
    metodo_consumo = Column(Enum("FEFO", "FIFO", name="metodo_consumo_enum"), nullable=True)

    # --- Packing ---
    peso = Column(Numeric(14, 3), nullable=True)
    cajas = Column(Integer, nullable=True)
    pallets = Column(Integer, nullable=True)

    # --- Carga ---
    vehiculo = Column(String(30), nullable=True)
    conductor = Column(String(120), nullable=True)
    fecha_carga = Column(DateTime(timezone=True), nullable=True)

    # --- Timestamps de cada etapa (mismo criterio que OrdenCompra/OrdenVenta) ---
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    recepcion_en = Column(DateTime(timezone=True), nullable=True)
    inspeccion_en = Column(DateTime(timezone=True), nullable=True)
    ubicacion_en = Column(DateTime(timezone=True), nullable=True)
    disponible_en = Column(DateTime(timezone=True), nullable=True)
    reservado_en = Column(DateTime(timezone=True), nullable=True)
    picking_en = Column(DateTime(timezone=True), nullable=True)
    packing_en = Column(DateTime(timezone=True), nullable=True)
    carga_en = Column(DateTime(timezone=True), nullable=True)
    despacho_en = Column(DateTime(timezone=True), nullable=True)
    entregado_en = Column(DateTime(timezone=True), nullable=True)
    cerrado_en = Column(DateTime(timezone=True), nullable=True)

    producto = relationship("Producto")
    proveedor = relationship("Proveedor")
    orden_compra = relationship("OrdenCompra")
    orden_venta = relationship("OrdenVenta")
    lote = relationship("Lote", foreign_keys=[lote_id])
    lote_picking = relationship("Lote", foreign_keys=[lote_picking_id])
    historial = relationship(
        "HistorialOperacionLogistica",
        back_populates="operacion",
        cascade="all, delete-orphan",
        order_by="HistorialOperacionLogistica.fecha_hora",
    )


class HistorialOperacionLogistica(Base):
    """Auditoria inmutable de cada cambio de estado: fecha, hora, usuario,
    estado anterior, estado nuevo y observaciones."""

    __tablename__ = "historial_operaciones_logisticas"

    id = Column(Integer, primary_key=True, index=True)
    operacion_id = Column(
        Integer, ForeignKey("operaciones_logisticas.id"), nullable=False, index=True
    )
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    fecha_hora = Column(DateTime(timezone=True), server_default=func.now())
    estado_anterior = Column(
        Enum(*ESTADOS_OL, name="estado_operacion_logistica_anterior_enum"), nullable=True
    )
    estado_nuevo = Column(
        Enum(*ESTADOS_OL, name="estado_operacion_logistica_nuevo_enum"), nullable=False
    )
    observaciones = Column(String(500), nullable=True)

    operacion = relationship("OperacionLogistica", back_populates="historial")
    usuario = relationship("Usuario")

    @property
    def usuario_username(self) -> str:
        return self.usuario.username
