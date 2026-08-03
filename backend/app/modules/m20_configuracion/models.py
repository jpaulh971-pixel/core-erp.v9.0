"""Modulo 20 - Configuracion.

Contiene el unico usuario del sistema: Administrador. No hay roles,
sucursales ni permisos por sucursal (diseno de almacen unico central).
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    nombre_completo = Column(String(150), nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(30), nullable=False, default="ADMINISTRADOR")
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())


class ParametroSistema(Base):
    """Parametros generales del ERP (almacen central, moneda base, etc)."""

    __tablename__ = "parametros_sistema"

    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(80), unique=True, nullable=False, index=True)
    valor = Column(String(255), nullable=False)
    descripcion = Column(String(255), nullable=True)
