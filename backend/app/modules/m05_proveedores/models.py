"""Modulo 05 - Proveedores.

Catalogo minimo de proveedores, requerido como base estructural para
Compras (una orden de compra siempre pertenece a un proveedor).
"""
from sqlalchemy import Boolean, Column, Integer, String

from app.database import Base


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    ruc = Column(String(20), unique=True, nullable=False, index=True)
    razon_social = Column(String(200), nullable=False)
    contacto = Column(String(120), nullable=True)
    telefono = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    pais = Column(String(80), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
