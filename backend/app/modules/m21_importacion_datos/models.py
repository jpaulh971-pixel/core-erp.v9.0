"""Modulo 21 - Importacion de Datos (carga masiva Excel).

ETAPA 1: carga de INVENTARIO INICIAL (terminada).
ETAPA 2: carga historica de COMPRAS y VENTAS (esta entrega), con
  clasificacion HISTORICO/OPERATIVO por fila segun una fecha de corte
  configurable por inventario.

Flujo obligatorio de dos pasos:
  PREVISUALIZAR (lee y valida el Excel fila por fila, NO toca m02/m03/m04/m10)
  -> CONFIRMAR (recien ahi crea los registros reales, reutilizando
     obtener_o_crear_producto de m02 y registrar_ingreso de m03, o -en
     Etapa 2- los servicios de m04_compras/m10_ventas).

Cada fila del Excel queda registrada con su resultado de validacion (log
de errores por fila) y el nombre del archivo origen queda en la carga
para trazabilidad. Una carga ya CONFIRMADA no se vuelve a procesar.
"""
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

ESTADOS_CARGA = ("PREVISUALIZADA", "CON_ERRORES", "CONFIRMADA")
MODOS_CARGA = ("HISTORICO", "OPERATIVO")
ESTADOS_VIGENCIA = ("ACTIVA", "REEMPLAZADA")
RESULTADOS_BITACORA = ("EXITOSO", "BLOQUEADO", "ERROR")


class CargaInventarioInicial(Base):
    __tablename__ = "cargas_inventario_inicial"

    id = Column(Integer, primary_key=True, index=True)
    nombre_archivo = Column(String(255), nullable=False)
    inventario_id = Column(Integer, ForeignKey("inventarios.id"), nullable=False, index=True)
    estado = Column(Enum(*ESTADOS_CARGA, name="estado_carga_inv_inicial_enum"), nullable=False, default="PREVISUALIZADA")
    total_filas = Column(Integer, nullable=False, default=0)
    filas_validas = Column(Integer, nullable=False, default=0)
    filas_con_error = Column(Integer, nullable=False, default=0)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    confirmado_en = Column(DateTime(timezone=True), nullable=True)

    # --- ETAPA 3: reemplazo de carga confirmada (auditoria, nunca se borra) ---
    estado_vigencia = Column(
        Enum(*ESTADOS_VIGENCIA, name="estado_vigencia_inv_inicial_enum"),
        nullable=False,
        default="ACTIVA",
    )
    reemplazada_en = Column(DateTime(timezone=True), nullable=True)
    reemplazada_por_usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    motivo_reemplazo = Column(String(500), nullable=True)
    observaciones_reemplazo = Column(String(1000), nullable=True)
    carga_reemplazo_id = Column(Integer, ForeignKey("cargas_inventario_inicial.id"), nullable=True)
    carga_original_id = Column(Integer, ForeignKey("cargas_inventario_inicial.id"), nullable=True)

    inventario = relationship("Inventario")
    filas = relationship(
        "CargaInventarioInicialFila", back_populates="carga", cascade="all, delete-orphan"
    )


class CargaInventarioInicialFila(Base):
    """Una fila del Excel, tal como fue leida (datos_json), con su
    resultado de validacion. `procesada` indica si ya genero su
    ProductoInventario/Lote/Kardex durante la confirmacion."""

    __tablename__ = "cargas_inventario_inicial_filas"

    id = Column(Integer, primary_key=True, index=True)
    carga_id = Column(Integer, ForeignKey("cargas_inventario_inicial.id"), nullable=False, index=True)
    numero_fila = Column(Integer, nullable=False)
    datos_json = Column(Text, nullable=False)
    valida = Column(Boolean, nullable=False, default=True)
    mensaje_error = Column(String(500), nullable=True)
    procesada = Column(Boolean, nullable=False, default=False)

    carga = relationship("CargaInventarioInicial", back_populates="filas")


# ---------------------------------------------------------------------
# ETAPA 2: fecha de corte + cargas historicas de Compras y Ventas
# ---------------------------------------------------------------------


class ConfiguracionCorteInventario(Base):
    """Fecha de corte por inventario: las filas del Excel con fecha <= a
    esta se clasifican HISTORICO (documental, sin Kardex/stock); las
    posteriores, OPERATIVO (movimiento real). Un registro por inventario,
    se configura una sola vez y la reutilizan todas las cargas de
    compras/ventas historicas de ese inventario."""

    __tablename__ = "configuracion_corte_inventario"

    id = Column(Integer, primary_key=True, index=True)
    inventario_id = Column(
        Integer, ForeignKey("inventarios.id"), nullable=False, unique=True, index=True
    )
    fecha_corte = Column(DateTime(timezone=True), nullable=False)
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    inventario = relationship("Inventario")


class CargaComprasHistorico(Base):
    __tablename__ = "cargas_compras_historico"

    id = Column(Integer, primary_key=True, index=True)
    nombre_archivo = Column(String(255), nullable=False)
    inventario_id = Column(Integer, ForeignKey("inventarios.id"), nullable=False, index=True)
    estado = Column(
        Enum(*ESTADOS_CARGA, name="estado_carga_compras_hist_enum"),
        nullable=False,
        default="PREVISUALIZADA",
    )
    total_filas = Column(Integer, nullable=False, default=0)
    filas_validas = Column(Integer, nullable=False, default=0)
    filas_con_error = Column(Integer, nullable=False, default=0)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    confirmado_en = Column(DateTime(timezone=True), nullable=True)

    # --- ETAPA 3: reemplazo de carga confirmada (auditoria, nunca se borra) ---
    estado_vigencia = Column(
        Enum(*ESTADOS_VIGENCIA, name="estado_vigencia_compras_hist_enum"),
        nullable=False,
        default="ACTIVA",
    )
    reemplazada_en = Column(DateTime(timezone=True), nullable=True)
    reemplazada_por_usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    motivo_reemplazo = Column(String(500), nullable=True)
    observaciones_reemplazo = Column(String(1000), nullable=True)
    carga_reemplazo_id = Column(Integer, ForeignKey("cargas_compras_historico.id"), nullable=True)
    carga_original_id = Column(Integer, ForeignKey("cargas_compras_historico.id"), nullable=True)

    inventario = relationship("Inventario")
    filas = relationship(
        "CargaComprasHistoricoFila", back_populates="carga", cascade="all, delete-orphan"
    )


class CargaComprasHistoricoFila(Base):
    __tablename__ = "cargas_compras_historico_filas"

    id = Column(Integer, primary_key=True, index=True)
    carga_id = Column(Integer, ForeignKey("cargas_compras_historico.id"), nullable=False, index=True)
    numero_fila = Column(Integer, nullable=False)
    datos_json = Column(Text, nullable=False)
    modo_carga = Column(Enum(*MODOS_CARGA, name="modo_carga_compras_enum"), nullable=False)
    valida = Column(Boolean, nullable=False, default=True)
    mensaje_error = Column(String(500), nullable=True)
    procesada = Column(Boolean, nullable=False, default=False)
    orden_compra_id = Column(Integer, ForeignKey("ordenes_compra.id"), nullable=True)  # trazabilidad

    carga = relationship("CargaComprasHistorico", back_populates="filas")


class CargaVentasHistorico(Base):
    __tablename__ = "cargas_ventas_historico"

    id = Column(Integer, primary_key=True, index=True)
    nombre_archivo = Column(String(255), nullable=False)
    inventario_id = Column(Integer, ForeignKey("inventarios.id"), nullable=False, index=True)
    estado = Column(
        Enum(*ESTADOS_CARGA, name="estado_carga_ventas_hist_enum"),
        nullable=False,
        default="PREVISUALIZADA",
    )
    total_filas = Column(Integer, nullable=False, default=0)
    filas_validas = Column(Integer, nullable=False, default=0)
    filas_con_error = Column(Integer, nullable=False, default=0)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    confirmado_en = Column(DateTime(timezone=True), nullable=True)

    # --- ETAPA 3: reemplazo de carga confirmada (auditoria, nunca se borra) ---
    estado_vigencia = Column(
        Enum(*ESTADOS_VIGENCIA, name="estado_vigencia_ventas_hist_enum"),
        nullable=False,
        default="ACTIVA",
    )
    reemplazada_en = Column(DateTime(timezone=True), nullable=True)
    reemplazada_por_usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    motivo_reemplazo = Column(String(500), nullable=True)
    observaciones_reemplazo = Column(String(1000), nullable=True)
    carga_reemplazo_id = Column(Integer, ForeignKey("cargas_ventas_historico.id"), nullable=True)
    carga_original_id = Column(Integer, ForeignKey("cargas_ventas_historico.id"), nullable=True)

    inventario = relationship("Inventario")
    filas = relationship(
        "CargaVentasHistoricoFila", back_populates="carga", cascade="all, delete-orphan"
    )


class CargaVentasHistoricoFila(Base):
    __tablename__ = "cargas_ventas_historico_filas"

    id = Column(Integer, primary_key=True, index=True)
    carga_id = Column(Integer, ForeignKey("cargas_ventas_historico.id"), nullable=False, index=True)
    numero_fila = Column(Integer, nullable=False)
    datos_json = Column(Text, nullable=False)
    modo_carga = Column(Enum(*MODOS_CARGA, name="modo_carga_ventas_enum"), nullable=False)
    valida = Column(Boolean, nullable=False, default=True)
    mensaje_error = Column(String(500), nullable=True)
    procesada = Column(Boolean, nullable=False, default=False)
    orden_venta_id = Column(Integer, ForeignKey("ordenes_venta.id"), nullable=True)  # trazabilidad

    carga = relationship("CargaVentasHistorico", back_populates="filas")


# ---------------------------------------------------------------------
# ETAPA 3: bitacora de reemplazos (auditoria completa e inmutable)
# ---------------------------------------------------------------------


class BitacoraReemplazo(Base):
    """Registro inmutable de cada intento de reemplazo de una carga
    confirmada (exitoso, bloqueado o con error/rollback). No se edita ni
    se borra nunca: es el historial de auditoria exigido para saber
    quien reemplazo que, cuando, por que motivo y con que resultado."""

    __tablename__ = "bitacora_reemplazos_importacion"

    id = Column(Integer, primary_key=True, index=True)
    tipo_carga = Column(
        Enum("INVENTARIO_INICIAL", "COMPRAS", "VENTAS", name="tipo_carga_bitacora_enum"),
        nullable=False,
        index=True,
    )
    carga_anterior_id = Column(Integer, nullable=False, index=True)
    carga_nueva_id = Column(Integer, nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario_username = Column(String(50), nullable=False)
    ip_origen = Column(String(64), nullable=True)
    motivo = Column(String(500), nullable=False)
    observaciones = Column(String(1000), nullable=True)
    cantidad_lotes_eliminados = Column(Integer, nullable=False, default=0)
    cantidad_kardex_eliminados = Column(Integer, nullable=False, default=0)
    cantidad_ordenes_eliminadas = Column(Integer, nullable=False, default=0)
    cantidad_registros_nuevos = Column(Integer, nullable=False, default=0)
    tiempo_ejecucion_ms = Column(Integer, nullable=False, default=0)
    resultado = Column(
        Enum(*RESULTADOS_BITACORA, name="resultado_bitacora_enum"), nullable=False
    )
    detalle = Column(Text, nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
