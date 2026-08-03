"""Modulo 11 - Clientes.

Catalogo minimo de clientes, mismo criterio estructural que Proveedores
(modulo 05) para Compras. Por ahora es un catalogo independiente: Ventas
(modulo 10) y Comercio Exterior (modulo 06) siguen usando su propio campo
simple `cliente_nombre` -- la migracion de esos modulos a una FK real
hacia esta tabla es un paso explicito aparte, para no modificar modulos
ya implementados sin que se pida.
"""
from sqlalchemy import Boolean, Column, Integer, String

from app.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    ruc = Column(String(20), unique=True, nullable=False, index=True)
    razon_social = Column(String(200), nullable=False)
    contacto = Column(String(120), nullable=True)
    telefono = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    pais = Column(String(80), nullable=True)
    activo = Column(Boolean, default=True, nullable=False)
