"""Modulo 02 - Productos.

Catalogo de productos del almacen de exportacion. Base estructural para
Inventario, Compras, Ventas, Costos y Comercio Exterior.
"""
from sqlalchemy import Boolean, Column, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.database import Base


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(30), unique=True, nullable=False, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(500), nullable=True)
    unidad_medida = Column(String(20), nullable=False, default="UND")
    partida_arancelaria = Column(String(20), nullable=True)
    stock_minimo = Column(Numeric(14, 3), nullable=False, default=0)
    # FASE 9 (importacion de compras nacionalizadas): indica si el producto
    # requiere control de vencimiento. Se usa unicamente para la validacion
    # "si el producto es perecible, la Fecha de Vencimiento es obligatoria"
    # de la importacion de compras (m04_compras/importacion_service.py). No
    # afecta PEPS/FEFO/Kardex: Lote.fecha_vencimiento (m03_inventario) sigue
    # siendo el unico campo que usa el motor de FEFO, para cualquier
    # producto, perecible o no.
    perecible = Column(Boolean, default=False, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)

    inventarios_producto = relationship("ProductoInventario", back_populates="producto")
