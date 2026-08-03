from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.modules.m21_importacion_datos.models import (
    BitacoraReemplazo,
    CargaComprasHistorico,
    CargaComprasHistoricoFila,
    CargaInventarioInicial,
    CargaInventarioInicialFila,
    CargaVentasHistorico,
    CargaVentasHistoricoFila,
    ConfiguracionCorteInventario,
)


def crear_carga(db: Session, carga: CargaInventarioInicial) -> CargaInventarioInicial:
    db.add(carga)
    db.commit()
    db.refresh(carga)
    return carga


def agregar_fila(db: Session, fila: CargaInventarioInicialFila) -> CargaInventarioInicialFila:
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


def obtener_carga(db: Session, carga_id: int) -> Optional[CargaInventarioInicial]:
    return (
        db.query(CargaInventarioInicial)
        .options(joinedload(CargaInventarioInicial.filas))
        .filter(CargaInventarioInicial.id == carga_id)
        .first()
    )


def listar_cargas(db: Session) -> list[CargaInventarioInicial]:
    return db.query(CargaInventarioInicial).order_by(CargaInventarioInicial.creado_en.desc()).all()


def guardar_carga(db: Session, carga: CargaInventarioInicial) -> CargaInventarioInicial:
    db.add(carga)
    db.commit()
    db.refresh(carga)
    return carga


def guardar_fila(db: Session, fila: CargaInventarioInicialFila) -> CargaInventarioInicialFila:
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


def filas_pendientes(db: Session, carga_id: int) -> list[CargaInventarioInicialFila]:
    return (
        db.query(CargaInventarioInicialFila)
        .filter(
            CargaInventarioInicialFila.carga_id == carga_id,
            CargaInventarioInicialFila.valida.is_(True),
            CargaInventarioInicialFila.procesada.is_(False),
        )
        .order_by(CargaInventarioInicialFila.numero_fila)
        .all()
    )


# ---------------------------------------------------------------------
# ETAPA 2: ConfiguracionCorteInventario
# ---------------------------------------------------------------------


def obtener_corte_por_inventario(db: Session, inventario_id: int) -> Optional[ConfiguracionCorteInventario]:
    return (
        db.query(ConfiguracionCorteInventario)
        .filter(ConfiguracionCorteInventario.inventario_id == inventario_id)
        .first()
    )


def guardar_corte(db: Session, corte: ConfiguracionCorteInventario) -> ConfiguracionCorteInventario:
    db.add(corte)
    db.commit()
    db.refresh(corte)
    return corte


# ---------------------------------------------------------------------
# ETAPA 2: Compras historico
# ---------------------------------------------------------------------


def crear_carga_compras(db: Session, carga: CargaComprasHistorico) -> CargaComprasHistorico:
    db.add(carga)
    db.commit()
    db.refresh(carga)
    return carga


def agregar_fila_compras(db: Session, fila: CargaComprasHistoricoFila) -> CargaComprasHistoricoFila:
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


def obtener_carga_compras(db: Session, carga_id: int) -> Optional[CargaComprasHistorico]:
    return (
        db.query(CargaComprasHistorico)
        .options(joinedload(CargaComprasHistorico.filas))
        .filter(CargaComprasHistorico.id == carga_id)
        .first()
    )


def listar_cargas_compras(db: Session) -> list[CargaComprasHistorico]:
    return db.query(CargaComprasHistorico).order_by(CargaComprasHistorico.creado_en.desc()).all()


def guardar_carga_compras(db: Session, carga: CargaComprasHistorico) -> CargaComprasHistorico:
    db.add(carga)
    db.commit()
    db.refresh(carga)
    return carga


def guardar_fila_compras(db: Session, fila: CargaComprasHistoricoFila) -> CargaComprasHistoricoFila:
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


def filas_pendientes_compras(db: Session, carga_id: int) -> list[CargaComprasHistoricoFila]:
    return (
        db.query(CargaComprasHistoricoFila)
        .filter(
            CargaComprasHistoricoFila.carga_id == carga_id,
            CargaComprasHistoricoFila.valida.is_(True),
            CargaComprasHistoricoFila.procesada.is_(False),
        )
        .order_by(CargaComprasHistoricoFila.numero_fila)
        .all()
    )


# ---------------------------------------------------------------------
# ETAPA 2: Ventas historico
# ---------------------------------------------------------------------


def crear_carga_ventas(db: Session, carga: CargaVentasHistorico) -> CargaVentasHistorico:
    db.add(carga)
    db.commit()
    db.refresh(carga)
    return carga


def agregar_fila_ventas(db: Session, fila: CargaVentasHistoricoFila) -> CargaVentasHistoricoFila:
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


def obtener_carga_ventas(db: Session, carga_id: int) -> Optional[CargaVentasHistorico]:
    return (
        db.query(CargaVentasHistorico)
        .options(joinedload(CargaVentasHistorico.filas))
        .filter(CargaVentasHistorico.id == carga_id)
        .first()
    )


def listar_cargas_ventas(db: Session) -> list[CargaVentasHistorico]:
    return db.query(CargaVentasHistorico).order_by(CargaVentasHistorico.creado_en.desc()).all()


def guardar_carga_ventas(db: Session, carga: CargaVentasHistorico) -> CargaVentasHistorico:
    db.add(carga)
    db.commit()
    db.refresh(carga)
    return carga


def guardar_fila_ventas(db: Session, fila: CargaVentasHistoricoFila) -> CargaVentasHistoricoFila:
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


def filas_pendientes_ventas(db: Session, carga_id: int) -> list[CargaVentasHistoricoFila]:
    return (
        db.query(CargaVentasHistoricoFila)
        .filter(
            CargaVentasHistoricoFila.carga_id == carga_id,
            CargaVentasHistoricoFila.valida.is_(True),
            CargaVentasHistoricoFila.procesada.is_(False),
        )
        .order_by(CargaVentasHistoricoFila.numero_fila)
        .all()
    )


# ---------------------------------------------------------------------
# ETAPA 3: reemplazo de cargas confirmadas (con trazabilidad)
#
# Mismo patron "eager commit" que el resto del modulo (cada funcion hace
# su propio db.commit()). La atomicidad de TODO el reemplazo (borrar lo
# viejo + confirmar lo nuevo + enlazar + bitacora, todo o nada) la
# gestiona el motor en service.py con una unica transaccion SQLAlchemy
# real (ver _transaccion_atomica), no cada funcion individual de aqui.
# ---------------------------------------------------------------------


def filas_procesadas_compras(db: Session, carga_id: int) -> list[CargaComprasHistoricoFila]:
    """Filas que SI generaron una Orden de Compra real durante confirmar_compras()."""
    return (
        db.query(CargaComprasHistoricoFila)
        .filter(
            CargaComprasHistoricoFila.carga_id == carga_id,
            CargaComprasHistoricoFila.procesada.is_(True),
        )
        .all()
    )


def filas_procesadas_ventas(db: Session, carga_id: int) -> list[CargaVentasHistoricoFila]:
    """Filas que SI generaron una Orden de Venta real durante confirmar_ventas()."""
    return (
        db.query(CargaVentasHistoricoFila)
        .filter(
            CargaVentasHistoricoFila.carga_id == carga_id,
            CargaVentasHistoricoFila.procesada.is_(True),
        )
        .all()
    )


def marcar_carga_reemplazada(
    db: Session,
    carga: CargaInventarioInicial,
    nueva_carga: CargaInventarioInicial,
    usuario_id: Optional[int],
    motivo: str,
    observaciones: Optional[str],
) -> CargaInventarioInicial:
    """Nunca borra la carga vieja: solo la marca REEMPLAZADA/INACTIVA (no
    participa en calculos) y la enlaza con la carga nueva, ambas dos
    direcciones, para que la auditoria pueda recorrer el historial
    completo desde cualquiera de las dos puntas."""
    carga.estado_vigencia = "REEMPLAZADA"
    carga.reemplazada_en = datetime.now(timezone.utc)
    carga.reemplazada_por_usuario_id = usuario_id
    carga.motivo_reemplazo = motivo
    carga.observaciones_reemplazo = observaciones
    carga.carga_reemplazo_id = nueva_carga.id
    nueva_carga.carga_original_id = carga.id
    db.add(carga)
    db.add(nueva_carga)
    db.commit()
    db.refresh(carga)
    db.refresh(nueva_carga)
    return carga


def marcar_carga_reemplazada_compras(
    db: Session,
    carga: CargaComprasHistorico,
    nueva_carga: CargaComprasHistorico,
    usuario_id: Optional[int],
    motivo: str,
    observaciones: Optional[str],
) -> CargaComprasHistorico:
    carga.estado_vigencia = "REEMPLAZADA"
    carga.reemplazada_en = datetime.now(timezone.utc)
    carga.reemplazada_por_usuario_id = usuario_id
    carga.motivo_reemplazo = motivo
    carga.observaciones_reemplazo = observaciones
    carga.carga_reemplazo_id = nueva_carga.id
    nueva_carga.carga_original_id = carga.id
    db.add(carga)
    db.add(nueva_carga)
    db.commit()
    db.refresh(carga)
    db.refresh(nueva_carga)
    return carga


def marcar_carga_reemplazada_ventas(
    db: Session,
    carga: CargaVentasHistorico,
    nueva_carga: CargaVentasHistorico,
    usuario_id: Optional[int],
    motivo: str,
    observaciones: Optional[str],
) -> CargaVentasHistorico:
    carga.estado_vigencia = "REEMPLAZADA"
    carga.reemplazada_en = datetime.now(timezone.utc)
    carga.reemplazada_por_usuario_id = usuario_id
    carga.motivo_reemplazo = motivo
    carga.observaciones_reemplazo = observaciones
    carga.carga_reemplazo_id = nueva_carga.id
    nueva_carga.carga_original_id = carga.id
    db.add(carga)
    db.add(nueva_carga)
    db.commit()
    db.refresh(carga)
    db.refresh(nueva_carga)
    return carga


def crear_bitacora(db: Session, registro: BitacoraReemplazo) -> BitacoraReemplazo:
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


def listar_bitacora(db: Session, tipo_carga: Optional[str] = None) -> list[BitacoraReemplazo]:
    q = db.query(BitacoraReemplazo).order_by(BitacoraReemplazo.creado_en.desc())
    if tipo_carga:
        q = q.filter(BitacoraReemplazo.tipo_carga == tipo_carga)
    return q.all()


def listar_bitacora_por_carga(db: Session, carga_anterior_id: int) -> list[BitacoraReemplazo]:
    return (
        db.query(BitacoraReemplazo)
        .filter(BitacoraReemplazo.carga_anterior_id == carga_anterior_id)
        .order_by(BitacoraReemplazo.creado_en.desc())
        .all()
    )
