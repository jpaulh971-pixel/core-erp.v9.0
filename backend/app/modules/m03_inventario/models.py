"""Modulo 03 - Inventario.

Diseno multi-inventario (aprobado): el negocio maneja varios inventarios
independientes (ej. Inventario 1, Inventario 2). Cada Inventario tiene su
propio conjunto de productos (via ProductoInventario, con codigo interno,
familia, presentacion, litros y marca propios de ESE inventario), y el
stock (Lote, MovimientoKardex) cuelga de esa relacion, nunca del producto
global directamente. Dos inventarios nunca comparten codigo interno ni
lotes.

Un mismo Producto (maestro fisico global, m02) puede existir en varios
inventarios con datos distintos en cada uno.
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
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

# FASE 1 (seguridad operativa perecibles). Estados posibles de un Lote.
# ACTIVO / PROXIMO_VENCER / VENCIDO / AGOTADO se recalculan en vivo a
# partir de cantidad_actual y fecha_vencimiento (ver
# service.calcular_estado_lote): el valor persistido en esta columna es
# informativo/de reporte y se mantiene sincronizado en cada ingreso,
# salida y ajuste, pero el bloqueo real de lotes vencidos NUNCA confia
# solo en este campo (ver validators.validar_lote_no_vencido), para que
# lotes historicos que aun no fueron "tocados" por el sistema tras esta
# fase igual queden bloqueados correctamente. BLOQUEADO es la unica
# excepcion: es manual (no se auto-asigna en esta fase) y sí se respeta
# tal cual está guardado.
ESTADOS_LOTE = ("ACTIVO", "PROXIMO_VENCER", "VENCIDO", "BLOQUEADO", "AGOTADO")


class Inventario(Base):
    """Inventario independiente del cliente (ej. 'Inventario 1',
    'Inventario 2'). Cada uno maneja sus propios productos, familias,
    codigos internos, lotes y kardex -- nunca se mezclan entre si."""

    __tablename__ = "inventarios"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), unique=True, nullable=False, index=True)
    nombre = Column(String(150), nullable=False, unique=True)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    productos_inventario = relationship("ProductoInventario", back_populates="inventario")


class ProductoInventario(Base):
    """Relacion producto <-> inventario. Un mismo Producto (maestro fisico
    global, m02) puede existir en varios inventarios con codigo interno,
    familia, presentacion, litros y marca DISTINTOS en cada uno."""

    __tablename__ = "productos_inventario"
    __table_args__ = (
        UniqueConstraint("inventario_id", "codigo_interno", name="uq_codigo_interno_por_inventario"),
    )

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    inventario_id = Column(Integer, ForeignKey("inventarios.id"), nullable=False, index=True)
    codigo_interno = Column(String(30), nullable=False)
    familia = Column(String(100), nullable=True)
    presentacion = Column(String(100), nullable=True)
    litros_presentacion = Column(Numeric(14, 3), nullable=True)
    marca = Column(String(100), nullable=True)
    estado = Column(Boolean, default=True, nullable=False)

    producto = relationship("Producto", back_populates="inventarios_producto")
    inventario = relationship("Inventario", back_populates="productos_inventario")
    lotes = relationship("Lote", back_populates="producto_inventario")


class Lote(Base):
    __tablename__ = "lotes"

    id = Column(Integer, primary_key=True, index=True)
    producto_inventario_id = Column(
        Integer, ForeignKey("productos_inventario.id"), nullable=False, index=True
    )
    codigo_lote = Column(String(50), nullable=False)
    cantidad_inicial = Column(Numeric(14, 3), nullable=False)
    cantidad_actual = Column(Numeric(14, 3), nullable=False)
    costo_unitario = Column(Numeric(14, 4), nullable=False, default=0)
    fecha_elaboracion = Column(DateTime(timezone=True), nullable=True)
    fecha_ingreso = Column(DateTime(timezone=True), server_default=func.now())
    fecha_vencimiento = Column(DateTime(timezone=True), nullable=True)
    # FASE 1 (seguridad operativa perecibles). Ver ESTADOS_LOTE arriba.
    estado = Column(
        Enum(*ESTADOS_LOTE, name="estado_lote_enum"),
        nullable=False,
        default="ACTIVO",
        server_default="ACTIVO",
    )

    producto_inventario = relationship("ProductoInventario", back_populates="lotes")


class MovimientoKardex(Base):
    """Registro inmutable de todo ingreso/salida/ajuste de inventario,
    trazable por inventario + producto + lote."""

    __tablename__ = "movimientos_kardex"

    id = Column(Integer, primary_key=True, index=True)
    producto_inventario_id = Column(
        Integer, ForeignKey("productos_inventario.id"), nullable=False, index=True
    )
    inventario_id = Column(Integer, ForeignKey("inventarios.id"), nullable=False, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    tipo_movimiento = Column(
        Enum("INGRESO", "SALIDA", "AJUSTE_POSITIVO", "AJUSTE_NEGATIVO", name="tipo_movimiento_enum"),
        nullable=False,
    )
    cantidad = Column(Numeric(14, 3), nullable=False)
    costo_unitario = Column(Numeric(14, 4), nullable=False, default=0)
    saldo_resultante = Column(Numeric(14, 3), nullable=False)
    referencia = Column(String(120), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    producto_inventario = relationship("ProductoInventario")
    lote = relationship("Lote")
