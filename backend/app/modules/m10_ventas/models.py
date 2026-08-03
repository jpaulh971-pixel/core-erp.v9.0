"""Modulo 10 - Ventas (circuito de venta local; no hay exportacion en
este negocio, los clientes son todos internos/domesticos).

Orden de venta con items. Al pasar a DESPACHADA se descuenta stock real
del Inventario indicado (inventario_salida_id) via FEFO (modulo 03),
reutilizando el mismo servicio que usan Compras y Comercio Exterior.

El cliente es una FK real hacia el catalogo del modulo 11 Clientes (ya
implementado), no un campo simple -- a diferencia de Comercio Exterior,
que no se migra porque este negocio no exporta.

inventario_salida_id se agrega para que Ventas siga funcionando con el
m03 multi-inventario (antes habia un solo almacen implicito).
"""
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

ESTADOS_ORDEN_VENTA = ("BORRADOR", "CONFIRMADA", "DESPACHADA", "CANCELADA")


class OrdenVenta(Base):
    __tablename__ = "ordenes_venta"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    inventario_salida_id = Column(Integer, ForeignKey("inventarios.id"), nullable=False, index=True)
    moneda = Column(String(3), nullable=False, default="PEN")
    estado = Column(
        Enum(*ESTADOS_ORDEN_VENTA, name="estado_orden_venta_enum"),
        nullable=False,
        default="BORRADOR",
    )
    observaciones = Column(String(500), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    confirmado_en = Column(DateTime(timezone=True), nullable=True)
    despachado_en = Column(DateTime(timezone=True), nullable=True)
    cancelado_en = Column(DateTime(timezone=True), nullable=True)

    # --- Campos opcionales de Fase 10 (Importacion masiva de Ventas).
    # Todos nullable: no afectan ninguna orden creada por el flujo manual
    # existente (formulario "Nueva orden de venta"), que nunca los envia.
    # No redefinen ni reemplazan `estado` (maquina de estados del flujo
    # BORRADOR->CONFIRMADA->DESPACHADA->CANCELADA); `estado_documento` es
    # el estado que trae el propio documento del cliente en el Excel.
    numero_orden_externo = Column(String(50), nullable=True)  # "Orden de Venta" del Excel
    vendedor = Column(String(120), nullable=True)
    factura = Column(String(50), nullable=True)
    guia_remision = Column(String(50), nullable=True)
    fecha_emision = Column(DateTime(timezone=True), nullable=True)
    dias_credito = Column(Integer, nullable=True)
    fecha_vencimiento = Column(DateTime(timezone=True), nullable=True)  # vencimiento del credito, no de lote
    estado_documento = Column(String(50), nullable=True)
    ruc_cliente = Column(String(20), nullable=True)  # RUC tal cual llega en el Excel (trazabilidad)
    anio = Column(Integer, nullable=True)
    meses = Column(String(20), nullable=True)
    cultivo = Column(String(100), nullable=True)
    fundo = Column(String(150), nullable=True)

    cliente = relationship("Cliente")
    inventario_salida = relationship("Inventario")
    items = relationship(
        "OrdenVentaItem", back_populates="orden", cascade="all, delete-orphan"
    )

    @property
    def cliente_razon_social(self) -> str:
        return self.cliente.razon_social


class OrdenVentaItem(Base):
    __tablename__ = "ordenes_venta_items"

    id = Column(Integer, primary_key=True, index=True)
    orden_venta_id = Column(Integer, ForeignKey("ordenes_venta.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    cantidad = Column(Numeric(14, 3), nullable=False)
    precio_unitario_venta = Column(Numeric(14, 4), nullable=False)

    # --- Campos opcionales de Fase 10 (Importacion masiva de Ventas). Si
    # vienen (import Excel) se guardan tal cual, solo como dato de
    # referencia/trazabilidad del documento de origen: no participan en
    # el calculo de precio_unitario_venta ni en el despacho/Kardex/FEFO.
    unidad_medida = Column(String(20), nullable=True)
    descripcion = Column(String(300), nullable=True)
    sub_total = Column(Numeric(14, 4), nullable=True)
    igv = Column(Numeric(14, 4), nullable=True)
    total = Column(Numeric(14, 4), nullable=True)

    orden = relationship("OrdenVenta", back_populates="items")
    producto = relationship("Producto")
