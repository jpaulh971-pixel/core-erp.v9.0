from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FilaErrorOut(BaseModel):
    numero_fila: int
    mensaje_error: str


class CargaPreviewOut(BaseModel):
    carga_id: int
    nombre_archivo: str
    inventario_id: int
    estado: str
    total_filas: int
    filas_validas: int
    filas_con_error: int
    # Filas VÁLIDAS cuyo "Costo unitario" vino en 0. No son un error (0 es
    # un valor de negocio legítimo, ej. muestras gratuitas) por eso no se
    # bloquea la importación, pero se informan aparte para que el usuario
    # no termine con "Valor Inventario" en 0 por un costo que en realidad
    # faltaba en el Excel y no por ser una muestra gratuita real.
    filas_costo_cero: int = 0
    errores: list[FilaErrorOut]


class CargaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_archivo: str
    inventario_id: int
    estado: str
    total_filas: int
    filas_validas: int
    filas_con_error: int
    creado_en: datetime
    confirmado_en: Optional[datetime] = None


class CargaConfirmarOut(BaseModel):
    carga_id: int
    estado: str
    filas_procesadas: int
    filas_fallidas_en_confirmacion: list[FilaErrorOut]


# ---------------------------------------------------------------------
# ETAPA 2: fecha de corte + cargas historicas de Compras y Ventas
# ---------------------------------------------------------------------


class ConfiguracionCorteInventarioIn(BaseModel):
    fecha_corte: datetime


class ConfiguracionCorteInventarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inventario_id: int
    fecha_corte: datetime


class CargaComprasPreviewOut(BaseModel):
    carga_id: int
    nombre_archivo: str
    inventario_id: int
    estado: str
    total_filas: int
    filas_validas: int
    filas_con_error: int
    filas_historico: int
    filas_operativo: int
    errores: list[FilaErrorOut]


class CargaComprasOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_archivo: str
    inventario_id: int
    estado: str
    total_filas: int
    filas_validas: int
    filas_con_error: int
    creado_en: datetime
    confirmado_en: Optional[datetime] = None


class CargaComprasConfirmarOut(BaseModel):
    carga_id: int
    estado: str
    filas_procesadas: int
    filas_historico_creadas: int
    filas_operativas_creadas: int
    filas_fallidas_en_confirmacion: list[FilaErrorOut]


class CargaVentasPreviewOut(BaseModel):
    carga_id: int
    nombre_archivo: str
    inventario_id: int
    estado: str
    total_filas: int
    filas_validas: int
    filas_con_error: int
    filas_historico: int
    filas_operativo: int
    errores: list[FilaErrorOut]


class CargaVentasOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_archivo: str
    inventario_id: int
    estado: str
    total_filas: int
    filas_validas: int
    filas_con_error: int
    creado_en: datetime
    confirmado_en: Optional[datetime] = None


class CargaVentasConfirmarOut(BaseModel):
    carga_id: int
    estado: str
    filas_procesadas: int
    filas_historico_creadas: int
    filas_operativas_creadas: int
    filas_fallidas_en_confirmacion: list[FilaErrorOut]


# ---------------------------------------------------------------------
# ETAPA 3: reemplazo de cargas confirmadas (con trazabilidad)
# ---------------------------------------------------------------------


class ReemplazoSolicitud(BaseModel):
    """Body del endpoint de reemplazo. El motivo es OBLIGATORIO (regla de
    negocio): sin motivo no se permite ni siquiera intentar el reemplazo."""

    motivo: str
    observaciones: Optional[str] = None


class BloqueoReemplazoOut(BaseModel):
    tipo: str
    detalle: str


class ValidacionReemplazoOut(BaseModel):
    carga_id: int
    tipo_carga: str
    estado_carga: str
    estado_vigencia: str
    puede_reemplazar: bool
    bloqueos: list[BloqueoReemplazoOut]


class ReemplazoOut(BaseModel):
    carga_anterior_id: int
    carga_anterior_estado_vigencia: str
    carga_nueva_id: int
    carga_nueva_estado_vigencia: str
    kardex_eliminados: int
    lotes_eliminados: int
    ordenes_eliminadas: int
    filas_procesadas: int
    filas_fallidas_en_confirmacion: list[FilaErrorOut]
    motivo: str
    tiempo_ejecucion_ms: int
    bitacora_id: int


class BitacoraReemplazoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo_carga: str
    carga_anterior_id: int
    carga_nueva_id: Optional[int] = None
    usuario_username: str
    ip_origen: Optional[str] = None
    motivo: str
    observaciones: Optional[str] = None
    cantidad_lotes_eliminados: int
    cantidad_kardex_eliminados: int
    cantidad_ordenes_eliminadas: int
    cantidad_registros_nuevos: int
    tiempo_ejecucion_ms: int
    resultado: str
    detalle: Optional[str] = None
    creado_en: datetime
