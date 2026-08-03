from datetime import datetime, timezone

from fastapi import HTTPException, status


def _como_aware(fecha: datetime) -> datetime:
    """Normaliza a datetime timezone-aware (UTC) para poder comparar
    contra datetime.now(timezone.utc) sin importar si el dato vino
    guardado como naive (algunos datos historicos/de import Excel)."""
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha


def validar_stock_suficiente(stock_disponible: float, cantidad_requerida: float) -> None:
    if cantidad_requerida > stock_disponible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Stock insuficiente: disponible {stock_disponible}, "
                f"solicitado {cantidad_requerida}"
            ),
        )


def validar_lote_existe(lote):
    if lote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado")
    return lote


def validar_ajuste_no_deja_negativo(cantidad_actual: float, delta: float) -> None:
    if cantidad_actual + delta < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El ajuste dejaria el lote con stock negativo",
        )


def validar_inventario_existe(inventario):
    if inventario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventario no encontrado")
    return inventario


def validar_codigo_inventario_libre(db, repository, codigo: str) -> None:
    existentes = repository.listar_inventarios(db)
    if any(inv.codigo == codigo for inv in existentes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un inventario con codigo {codigo}",
        )


def validar_producto_en_inventario(producto_inventario):
    if producto_inventario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Este producto no existe en el inventario indicado",
        )
    return producto_inventario


def validar_lote_pertenece_a_producto_inventario(lote, producto_inventario_id: int) -> None:
    if lote.producto_inventario_id != producto_inventario_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El lote indicado no pertenece a ese producto/inventario",
        )


# --- FASE 1: seguridad operativa perecibles ---

def validar_lote_no_vencido(lote, fecha_referencia: datetime | None = None) -> None:
    """Bloqueo central: ningun lote vencido puede salir del inventario
    (venta, guia o exportacion), sin importar si su columna Lote.estado
    ya fue sincronizada o no. Compara fecha_vencimiento contra el
    momento real de la salida.

    Paso 2 (carga historica): si se informa fecha_referencia (la fecha
    real, historica, del movimiento que se esta reconstruyendo), el
    vencimiento se evalua contra ESA fecha en vez de contra el momento
    real de ejecucion. Sin fecha_referencia (flujo operativo normal), el
    comportamiento es exactamente el de antes."""
    if lote.fecha_vencimiento is None:
        return
    referencia = _como_aware(fecha_referencia) if fecha_referencia is not None else datetime.now(timezone.utc)
    if _como_aware(lote.fecha_vencimiento) < referencia:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El lote seleccionado está vencido y no puede ser utilizado.",
        )


def validar_lote_no_bloqueado(lote) -> None:
    """BLOQUEADO es un estado manual (cuarentena/retencion de calidad).
    Esta fase no agrega ninguna pantalla ni endpoint para asignarlo,
    pero si algun lote llega bloqueado (dato existente o fase futura),
    tampoco puede salir del inventario."""
    if lote.estado == "BLOQUEADO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El lote seleccionado está bloqueado y no puede ser utilizado.",
        )


def validar_vencimiento_obligatorio_si_perecible(producto, fecha_vencimiento) -> None:
    """Si el producto esta marcado como perecible, ningun lote puede
    crearse sin fecha de vencimiento. Se valida aca (en el punto real
    donde nace el Lote) para cubrir de una sola vez compras manuales,
    importacion Excel y cualquier otro creador futuro, sin duplicar la
    regla en cada modulo llamador."""
    if producto.perecible and fecha_vencimiento is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Producto '{producto.nombre}' es perecible: "
                "la fecha de vencimiento es obligatoria para crear el lote."
            ),
        )
