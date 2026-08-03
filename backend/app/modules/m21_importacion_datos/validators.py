from typing import Optional

from fastapi import HTTPException, status


def validar_extension_excel(nombre_archivo: str) -> None:
    if not nombre_archivo.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser un Excel (.xlsx o .xls)",
        )


def validar_carga_existe(carga):
    if carga is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carga no encontrada")
    return carga


def validar_carga_no_confirmada(carga) -> None:
    if carga.estado == "CONFIRMADA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta carga ya fue confirmada, no se puede volver a confirmar",
        )


# ---------------------------------------------------------------------
# ETAPA 2: fecha de corte + modo de carga (HISTORICO / OPERATIVO)
# ---------------------------------------------------------------------


def validar_corte_configurado(corte) -> None:
    if corte is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No hay fecha de corte de inventario configurada para este inventario. "
                "Configurela con PUT /api/importacion-datos/{inventario_id}/fecha-corte "
                "antes de cargar compras/ventas historicas (o incluya la columna "
                "'tipo_movimiento'/'modo_carga' en cada fila del Excel)."
            ),
        )


def validar_modo_carga_excel(valor: str) -> str:
    """Normaliza y valida el valor de la columna opcional tipo_movimiento/
    modo_carga cuando el Excel la trae explicita."""
    normalizado = str(valor).strip().upper()
    if normalizado not in ("HISTORICO", "OPERATIVO"):
        raise ValueError(
            f"Valor invalido en columna tipo_movimiento/modo_carga: '{valor}'. "
            "Debe ser HISTORICO u OPERATIVO."
        )
    return normalizado


# ---------------------------------------------------------------------
# ETAPA 3: reemplazo de cargas confirmadas
# ---------------------------------------------------------------------


def validar_carga_confirmada(carga) -> None:
    if carga.estado != "CONFIRMADA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La carga esta en estado '{carga.estado}'; debe estar CONFIRMADA para poder reemplazarse.",
        )


def validar_carga_no_reemplazada(carga) -> None:
    if carga.estado_vigencia == "REEMPLAZADA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Esta carga ya fue reemplazada por la carga #{carga.carga_reemplazo_id}.",
        )


def validar_permiso_reemplazo(usuario) -> None:
    """Solo un ADMINISTRADOR puede reemplazar una carga confirmada
    (operacion sensible: borra Kardex/Lotes/Ordenes derivados)."""
    if getattr(usuario, "rol", None) != "ADMINISTRADOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un usuario con rol ADMINISTRADOR puede reemplazar una carga confirmada.",
        )


def validar_motivo_obligatorio(motivo: Optional[str]) -> str:
    if not motivo or not motivo.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El motivo del reemplazo es obligatorio.",
        )
    return motivo.strip()


def validar_sin_bloqueos(bloqueos: list) -> None:
    if bloqueos:
        detalle = "; ".join(f"[{b.tipo}] {b.detalle}" for b in bloqueos)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede reemplazar esta carga: {detalle}",
        )
