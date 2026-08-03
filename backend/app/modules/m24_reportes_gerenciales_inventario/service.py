"""Logica de negocio del modulo m24_reportes_gerenciales_inventario
(Fase 4C - backend).

Reportes Gerenciales de Inventario: 4 vistas de solo lectura que
consolidan y presentan, en un unico prefijo de API, indicadores que ya
existen en otros modulos. Ningun indicador se recalcula aca -- este
modulo solo lee, combina y (cuando hace falta, ej. porcentaje de
participacion) deriva con aritmetica simple sobre resultados que las
funciones de negocio de esos modulos ya producen. No se toca ningun
stock, kardex, costo ni tabla existente.

Origen de cada reporte:

  1) resumen_ejecutivo()
        -> m23_dashboard_inventario.service.resumen_dashboard()
           (reexpuesto tal cual, sin recalcular nada; ver schemas.py)

  2) top_valor()
        -> m19_reportes.service.reporte_inventario_valorizado()
           (ordenado por valor_total descendente; porcentaje_participacion
           se deriva dividiendo cada valor_total entre el
           valor_total_inventario ya devuelto por ese mismo reporte)

  3) productos_criticos()
        -> BAJO_STOCK:    m19_reportes.service.reporte_inventario_valorizado()
        -> VENCIMIENTO:   m19_reportes.service.reporte_proximos_vencer()
        -> RIESGO_MERMA:  m22_inteligencia_inventario.service.indicadores_inventario()
                           recorrido por inventario (igual que
                           m23_dashboard_inventario.service._riesgo_merma_total,
                           porque m22 no tiene una version global de ese
                           calculo), combinado con
                           m03_inventario.service.saldos() para el costo
                           unitario promedio (valor_comprometido)

  4) sin_rotacion()
        -> m22_inteligencia_inventario.service.indicadores_inventario()
           (sin_consumo / stock_inmovilizado), recorrido por inventario,
           combinado con la unica consulta nueva de este modulo
           (repository.ultimo_movimiento_por_producto) para calcular
           dias_sin_movimiento -- dato que ningun modulo existente
           expone todavia.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.modules.m03_inventario import service as inventario_service
from app.modules.m19_reportes import service as reportes_service
from app.modules.m22_inteligencia_inventario import service as inteligencia_service
from app.modules.m23_dashboard_inventario import service as dashboard_service
from app.modules.m24_reportes_gerenciales_inventario import repository, schemas

# Mapeo centralizado semaforo -> nivel_riesgo, usado en productos_criticos()
# para los 3 tipos de riesgo. Se define una sola vez aca para que los 3
# bloques (bajo stock, vencimiento, riesgo de merma) usen exactamente el
# mismo criterio de traduccion semaforo/clasificacion -> nivel_riesgo.
_NIVEL_POR_SEMAFORO_STOCK = {"ROJO": "ALTO", "AMARILLO": "MEDIO"}
_NIVEL_POR_SEMAFORO_VENCIMIENTO = {"NEGRO": "CRITICO", "ROJO": "ALTO", "AMARILLO": "MEDIO"}


# ---------------------------------------------------------------------
# 1) Resumen ejecutivo inventario
# ---------------------------------------------------------------------


def resumen_ejecutivo(db: Session) -> schemas.ResumenEjecutivoInventario:
    """Reexpone tal cual el resumen ya consolidado por
    m23_dashboard_inventario.service.resumen_dashboard(). No hay ningun
    calculo nuevo aca: solo se traduce el resultado al schema de este
    modulo para que quede documentado bajo el prefijo de Reportes
    Gerenciales de Inventario."""
    resumen = dashboard_service.resumen_dashboard(db)
    return schemas.ResumenEjecutivoInventario(**resumen.model_dump())


# ---------------------------------------------------------------------
# 2) Ranking productos mayor valor
# ---------------------------------------------------------------------


def top_valor(db: Session, limite: int | None = None) -> schemas.ReporteTopValorInventario:
    valorizado = reportes_service.reporte_inventario_valorizado(db)
    valor_total_inventario = valorizado.valor_total_inventario

    productos_ordenados = sorted(valorizado.productos, key=lambda p: p.valor_total, reverse=True)
    if limite is not None:
        productos_ordenados = productos_ordenados[:limite]

    items = [
        schemas.ProductoTopValor(
            producto=p.nombre,
            codigo_producto=p.codigo,
            stock_actual=p.cantidad_actual,
            costo_unitario=p.valor_promedio_unitario,
            valor_total=p.valor_total,
            porcentaje_participacion=round(
                (p.valor_total / valor_total_inventario * 100) if valor_total_inventario > 0 else 0.0,
                2,
            ),
        )
        for p in productos_ordenados
    ]

    return schemas.ReporteTopValorInventario(
        generado_en=datetime.utcnow(),
        total_productos=len(items),
        valor_total_inventario=valor_total_inventario,
        productos=items,
    )


# ---------------------------------------------------------------------
# 3) Productos criticos
# ---------------------------------------------------------------------


def _criticos_bajo_stock(db: Session) -> list[schemas.ProductoCritico]:
    valorizado = reportes_service.reporte_inventario_valorizado(db)
    items = []
    for p in valorizado.productos:
        if not p.bajo_stock_minimo:
            continue
        nivel = _NIVEL_POR_SEMAFORO_STOCK.get(p.semaforo_stock, "MEDIO")
        items.append(
            schemas.ProductoCritico(
                producto=p.nombre,
                codigo_producto=p.codigo,
                tipo_riesgo="BAJO_STOCK",
                nivel_riesgo=nivel,
                stock_actual=p.cantidad_actual,
                valor_comprometido=p.valor_total,
            )
        )
    return items


def _criticos_vencimiento(db: Session) -> list[schemas.ProductoCritico]:
    proximos_vencer = reportes_service.reporte_proximos_vencer(db, inventario_id=None)
    items = []
    for lote in proximos_vencer.lotes:
        if lote.categoria not in ("PROXIMOS_A_VENCER", "VENCIDOS"):
            continue
        nivel = _NIVEL_POR_SEMAFORO_VENCIMIENTO.get(lote.semaforo_vencimiento, "MEDIO")
        items.append(
            schemas.ProductoCritico(
                producto=lote.producto,
                codigo_producto=lote.codigo_producto,
                tipo_riesgo="VENCIMIENTO",
                nivel_riesgo=nivel,
                stock_actual=lote.cantidad_disponible,
                valor_comprometido=lote.valor_stock_comprometido,
            )
        )
    return items


def _criticos_riesgo_merma(db: Session) -> list[schemas.ProductoCritico]:
    """Recorre cada inventario (igual criterio que
    m23_dashboard_inventario.service._riesgo_merma_total): m22 calcula
    riesgo de merma por inventario_id, no existe una version global de
    esa funcion, por eso se recorre aca sin reimplementar su calculo
    interno. El costo unitario promedio para valor_comprometido se toma
    de m03_inventario.service.saldos() (misma fuente que usa m22
    internamente para stock_actual), sin volver a consultar el Kardex."""
    items: list[schemas.ProductoCritico] = []
    for inventario in repository.listar_inventarios(db):
        resumen = inteligencia_service.indicadores_inventario(db, inventario.id)
        saldos_por_pi = {
            s["producto_inventario_id"]: s for s in inventario_service.saldos(db, inventario.id)
        }
        for indicador in resumen.indicadores:
            if indicador.riesgo_merma not in ("ALTO", "CRITICO"):
                continue
            saldo = saldos_por_pi.get(indicador.producto_inventario_id, {})
            costo_unitario_promedio = saldo.get("costo_unitario_promedio", 0.0)
            items.append(
                schemas.ProductoCritico(
                    producto=indicador.nombre,
                    codigo_producto=indicador.codigo_interno,
                    tipo_riesgo="RIESGO_MERMA",
                    nivel_riesgo=indicador.riesgo_merma,
                    stock_actual=indicador.stock_actual,
                    valor_comprometido=round(indicador.stock_actual * costo_unitario_promedio, 2),
                )
            )
    return items


_ORDEN_NIVEL = {"CRITICO": 0, "ALTO": 1, "MEDIO": 2}


def productos_criticos(db: Session) -> schemas.ReporteProductosCriticos:
    items = _criticos_bajo_stock(db) + _criticos_riesgo_merma(db) + _criticos_vencimiento(db)
    items.sort(key=lambda i: (_ORDEN_NIVEL.get(i.nivel_riesgo, 99), -i.valor_comprometido))
    return schemas.ReporteProductosCriticos(
        generado_en=datetime.utcnow(),
        total_productos=len(items),
        productos=items,
    )


# ---------------------------------------------------------------------
# 4) Productos sin rotacion
# ---------------------------------------------------------------------


def sin_rotacion(
    db: Session, dias_sin_rotacion: int | None = None
) -> schemas.ReporteProductosSinRotacion:
    umbral = dias_sin_rotacion or settings.UMBRAL_DIAS_SIN_ROTACION
    ahora = datetime.now(timezone.utc)

    items: list[schemas.ProductoSinRotacion] = []
    for inventario in repository.listar_inventarios(db):
        resumen = inteligencia_service.indicadores_inventario(db, inventario.id)
        saldos_por_pi = {
            s["producto_inventario_id"]: s for s in inventario_service.saldos(db, inventario.id)
        }
        ultimos_movimientos = repository.ultimo_movimiento_por_producto(db, inventario.id)

        for indicador in resumen.indicadores:
            if indicador.stock_actual <= 0:
                continue
            if not (indicador.sin_consumo or indicador.stock_inmovilizado):
                continue

            ultimo_movimiento = ultimos_movimientos.get(indicador.producto_inventario_id)
            dias_sin_movimiento = None
            if ultimo_movimiento is not None:
                if ultimo_movimiento.tzinfo is None:
                    ultimo_movimiento = ultimo_movimiento.replace(tzinfo=timezone.utc)
                dias_sin_movimiento = (ahora - ultimo_movimiento).days

            # Solo entra al reporte si supera el umbral, o si nunca tuvo
            # movimiento registrado (caso mas critico: no hay forma de
            # saber cuanto lleva inmovilizado, pero ya sabemos que no
            # rota dentro de la ventana de analisis de m22).
            if dias_sin_movimiento is not None and dias_sin_movimiento < umbral:
                continue

            saldo = saldos_por_pi.get(indicador.producto_inventario_id, {})
            costo_unitario_promedio = saldo.get("costo_unitario_promedio", 0.0)
            items.append(
                schemas.ProductoSinRotacion(
                    producto=indicador.nombre,
                    codigo_producto=indicador.codigo_interno,
                    stock_actual=indicador.stock_actual,
                    valor_inventario=round(indicador.stock_actual * costo_unitario_promedio, 2),
                    dias_sin_movimiento=dias_sin_movimiento,
                )
            )

    items.sort(key=lambda i: (i.dias_sin_movimiento is None, -(i.dias_sin_movimiento or 0)))

    return schemas.ReporteProductosSinRotacion(
        generado_en=datetime.utcnow(),
        total_productos=len(items),
        productos=items,
    )
