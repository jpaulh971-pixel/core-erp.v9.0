"""Logica de negocio del modulo m22_inteligencia_inventario.

FASE 3 -- Inteligencia de inventario para perecibles. Solo lectura:
calcula rotacion, dias de inventario, consumo promedio y riesgo de
merma a partir de datos YA existentes en m03_inventario (Lote,
MovimientoKardex, ProductoInventario) y m02_productos (Producto). No
crea tablas, no escribe kardex, no modifica ningun stock ni costo.

Todas las funciones de calculo puro (calcular_rotacion,
calcular_consumo_promedio, calcular_dias_inventario,
evaluar_riesgo_merma) estan centralizadas aca para que la clasificacion
de riesgo de merma sea una unica fuente de verdad, parametrizable via
app.config.settings, reutilizable por cualquier otro modulo futuro sin
duplicar la logica (mismo criterio ya usado en m03_inventario.service
para los semaforos de Fase 1/2).
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.modules.m03_inventario import repository as inventario_repository
from app.modules.m03_inventario import service as inventario_service
from app.modules.m22_inteligencia_inventario import repository, schemas, validators

# Niveles de riesgo de merma (Fase 3, requisito minimo: 4 niveles).
RIESGO_BAJO = "BAJO"
RIESGO_MEDIO = "MEDIO"
RIESGO_ALTO = "ALTO"
RIESGO_CRITICO = "CRITICO"


# ---------------------------------------------------------------------
# Funciones de calculo puro (sin acceso a base de datos). Reciben los
# datos ya obtenidos y devuelven el indicador correspondiente. Se
# separan de la orquestacion (indicadores_inventario, mas abajo) para
# poder probarlas de forma aislada y para que ningun calculo quede
# duplicado entre productos.
# ---------------------------------------------------------------------


def calcular_rotacion(consumo_real_periodo: float, stock_promedio_periodo: float) -> float | None:
    """Rotacion de inventario = consumo real (unidades de SALIDA del
    Kardex en el periodo) / stock promedio del periodo.

    Division invalida (stock_promedio_periodo <= 0, es decir no hubo
    stock en el periodo que pudiera rotar) -> None, nunca ZeroDivisionError.
    """
    if stock_promedio_periodo <= 0:
        return None
    return consumo_real_periodo / stock_promedio_periodo


def calcular_consumo_promedio(consumo_real_periodo: float, dias_analisis: int) -> tuple[float, float, float]:
    """Consumo promedio diario/semanal/mensual, a partir del consumo
    real (SALIDA de Kardex) durante dias_analisis. dias_analisis ya fue
    validado > 0 (validators.validar_dias_analisis) antes de llegar aca,
    por lo que la division es siempre valida."""
    diario = consumo_real_periodo / dias_analisis
    return diario, diario * 7, diario * 30


def calcular_dias_inventario(
    stock_actual: float, consumo_promedio_diario: float
) -> tuple[float | None, bool, bool]:
    """Dias de inventario = stock disponible / consumo promedio diario.

    Retorna (dias_inventario, sin_consumo, sin_stock):
      - stock_actual <= 0            -> (0.0, sin_consumo, True):
        no hay inventario que cubrir, sin importar el consumo.
      - stock_actual > 0 y consumo_promedio_diario <= 0
                                      -> (None, True, False):
        division invalida (consumo cero); no se puede estimar cobertura,
        se reporta explicitamente como "sin_consumo" en vez de infinito.
      - caso normal                  -> (stock/consumo, False, False)
    """
    sin_stock = stock_actual <= 0
    sin_consumo = consumo_promedio_diario <= 0
    if sin_stock:
        return 0.0, sin_consumo, True
    if sin_consumo:
        return None, True, False
    return stock_actual / consumo_promedio_diario, False, False


def evaluar_riesgo_merma(
    dias_restantes_vencimiento: int | None,
    rotacion_inventario: float | None,
    dias_inventario: float | None,
    stock_inmovilizado: bool,
) -> tuple[str, int]:
    """Clasificacion centralizada y parametrizable del riesgo de merma
    (BAJO / MEDIO / ALTO / CRITICO), a partir de 4 factores reales:
    dias para vencer, rotacion, dias de inventario y stock inmovilizado.

    Cada factor suma puntos (0 si el dato no aplica/no existe, nunca
    penaliza por ausencia de dato) segun umbrales de app.config.settings;
    la suma total (0-12) se mapea a un nivel via los umbrales de score
    tambien parametrizables en settings. Devuelve (nivel, score) para
    trazabilidad del calculo.
    """
    score = 0

    # Factor 1: dias para vencer (peso maximo 4 -- un lote ya vencido en
    # stock es la senal mas fuerte de riesgo de merma posible).
    if dias_restantes_vencimiento is not None:
        if dias_restantes_vencimiento < 0:
            score += 4
        elif dias_restantes_vencimiento <= settings.UMBRAL_DIAS_VENCER_CRITICO:
            score += 3
        elif dias_restantes_vencimiento <= settings.UMBRAL_DIAS_VENCER_ALTO:
            score += 2
        elif dias_restantes_vencimiento <= settings.UMBRAL_DIAS_VENCER_MEDIO:
            score += 1

    # Factor 2: rotacion (peso maximo 3 -- rotacion baja o nula implica
    # que el stock no se esta consumiendo al ritmo esperado).
    if rotacion_inventario is not None:
        if rotacion_inventario <= 0:
            score += 3
        elif rotacion_inventario < settings.UMBRAL_ROTACION_BAJA:
            score += 2
        elif rotacion_inventario < settings.UMBRAL_ROTACION_MEDIA:
            score += 1

    # Factor 3: dias de inventario (peso maximo 3 -- demasiados dias de
    # cobertura sobre stock perecible aumenta la ventana de exposicion
    # a que venza antes de consumirse).
    if dias_inventario is not None:
        if dias_inventario >= settings.UMBRAL_DIAS_INVENTARIO_CRITICO:
            score += 3
        elif dias_inventario >= settings.UMBRAL_DIAS_INVENTARIO_ALTO:
            score += 2
        elif dias_inventario >= settings.UMBRAL_DIAS_INVENTARIO_MEDIO:
            score += 1

    # Factor 4: stock inmovilizado (peso 2 -- senal explicita pedida por
    # el brief, independiente de la rotacion para que un producto con
    # stock parcialmente movido pero congelado tambien quede marcado).
    if stock_inmovilizado:
        score += 2

    if score >= settings.SCORE_RIESGO_MERMA_CRITICO:
        nivel = RIESGO_CRITICO
    elif score >= settings.SCORE_RIESGO_MERMA_ALTO:
        nivel = RIESGO_ALTO
    elif score >= settings.SCORE_RIESGO_MERMA_MEDIO:
        nivel = RIESGO_MEDIO
    else:
        nivel = RIESGO_BAJO

    return nivel, score


# ---------------------------------------------------------------------
# Orquestacion: arma un IndicadorInventario por producto, reutilizando
# m03_inventario.service.saldos() (stock actual, costo, semaforo) y
# m03_inventario.service.calcular_semaforo_vencimiento() (dias
# restantes), y una sola consulta de Kardex + una de Lotes por
# inventario (repository de este modulo) para no duplicar queries por
# producto.
# ---------------------------------------------------------------------


def _indicador_de(
    saldo: dict,
    dias_analisis: int,
    movimientos_producto: dict[str, float],
    fecha_vencimiento_min: datetime | None,
    ahora: datetime,
) -> schemas.IndicadorInventario:
    ingresos = movimientos_producto.get("INGRESO", 0.0)
    salidas = movimientos_producto.get("SALIDA", 0.0)
    ajustes_pos = movimientos_producto.get("AJUSTE_POSITIVO", 0.0)
    ajustes_neg = movimientos_producto.get("AJUSTE_NEGATIVO", 0.0)

    stock_actual = saldo["stock_total"]

    # Reconstruccion del stock al inicio del periodo a partir de los
    # movimientos reales de Kardex (nunca simulado): stock_final =
    # stock_inicial + ingresos - salidas + ajustes_pos - ajustes_neg
    # => stock_inicial = stock_final - ingresos + salidas - ajustes_pos + ajustes_neg
    stock_inicial_estimado = stock_actual - ingresos + salidas - ajustes_pos + ajustes_neg
    # Defensa: si el Kardex del periodo es mas viejo que el historial
    # real disponible (o hay datos parciales), no dejar un stock inicial
    # negativo sin sentido de negocio.
    stock_inicial_estimado = max(stock_inicial_estimado, 0.0)
    stock_promedio_periodo = (stock_inicial_estimado + stock_actual) / 2

    consumo_real_periodo = salidas
    rotacion = calcular_rotacion(consumo_real_periodo, stock_promedio_periodo)
    consumo_diario, consumo_semanal, consumo_mensual = calcular_consumo_promedio(
        consumo_real_periodo, dias_analisis
    )
    dias_inventario, sin_consumo, sin_stock = calcular_dias_inventario(stock_actual, consumo_diario)

    _semaforo_venc, dias_restantes = inventario_service.calcular_semaforo_vencimiento(
        fecha_vencimiento_min, ahora
    )

    stock_inmovilizado = stock_actual > 0 and consumo_real_periodo == 0

    riesgo, score = evaluar_riesgo_merma(dias_restantes, rotacion, dias_inventario, stock_inmovilizado)

    return schemas.IndicadorInventario(
        producto_inventario_id=saldo["producto_inventario_id"],
        inventario_id=saldo["inventario_id"],
        producto_id=saldo["producto_id"],
        codigo_interno=saldo["codigo_interno"],
        nombre=saldo["nombre"],
        stock_actual=stock_actual,
        dias_analisis=dias_analisis,
        consumo_real_periodo=consumo_real_periodo,
        stock_promedio_periodo=stock_promedio_periodo,
        rotacion_inventario=rotacion,
        consumo_promedio_diario=consumo_diario,
        consumo_promedio_semanal=consumo_semanal,
        consumo_promedio_mensual=consumo_mensual,
        dias_inventario=dias_inventario,
        sin_consumo=sin_consumo,
        sin_stock=sin_stock,
        dias_restantes_vencimiento=dias_restantes,
        stock_inmovilizado=stock_inmovilizado,
        riesgo_merma=riesgo,
        score_riesgo_merma=score,
    )


def indicadores_inventario(
    db: Session, inventario_id: int, dias_analisis: int | None = None
) -> schemas.ResumenInteligenciaInventario:
    """Indicadores de inteligencia (rotacion, dias de inventario,
    consumo promedio, riesgo de merma) para TODOS los productos de un
    inventario."""
    dias_analisis = dias_analisis or settings.DIAS_ANALISIS_INVENTARIO_DEFAULT
    validators.validar_dias_analisis(dias_analisis)
    inventario_service.obtener_inventario(db, inventario_id)  # valida existencia

    ahora = datetime.now(timezone.utc)
    desde = ahora - timedelta(days=dias_analisis)

    saldos = inventario_service.saldos(db, inventario_id)
    movimientos = repository.movimientos_por_producto_en_periodo(db, inventario_id, desde)
    vencimientos = repository.fecha_vencimiento_minima_por_producto(db, inventario_id)

    indicadores = [
        _indicador_de(
            saldo,
            dias_analisis,
            movimientos.get(saldo["producto_inventario_id"], {}),
            vencimientos.get(saldo["producto_inventario_id"]),
            ahora,
        )
        for saldo in saldos
    ]

    return schemas.ResumenInteligenciaInventario(
        inventario_id=inventario_id,
        dias_analisis=dias_analisis,
        total_productos=len(indicadores),
        productos_riesgo_critico=sum(1 for i in indicadores if i.riesgo_merma == RIESGO_CRITICO),
        productos_riesgo_alto=sum(1 for i in indicadores if i.riesgo_merma == RIESGO_ALTO),
        indicadores=indicadores,
    )


def indicador_producto(
    db: Session, inventario_id: int, producto_inventario_id: int, dias_analisis: int | None = None
) -> schemas.IndicadorInventario:
    """Mismo calculo que indicadores_inventario(), para un solo
    producto_inventario. No agrega ninguna consulta ni logica nueva:
    reutiliza saldos()/movimientos/vencimientos ya usados arriba,
    filtrando al producto pedido, para que el resultado sea siempre
    identico al que aparece en la lista completa."""
    dias_analisis = dias_analisis or settings.DIAS_ANALISIS_INVENTARIO_DEFAULT
    validators.validar_dias_analisis(dias_analisis)
    inventario_service.obtener_inventario(db, inventario_id)  # valida existencia

    producto_inventario = inventario_repository.obtener_producto_inventario_por_id(
        db, producto_inventario_id
    )
    validators.validar_producto_inventario_pertenece(producto_inventario, inventario_id)

    ahora = datetime.now(timezone.utc)
    desde = ahora - timedelta(days=dias_analisis)

    saldos = inventario_service.saldos(db, inventario_id)
    saldo = next(
        (s for s in saldos if s["producto_inventario_id"] == producto_inventario_id), None
    )
    # saldos() solo incluye ProductoInventario.estado == True (mismo
    # filtro que ya usa m03_inventario.repository.saldos_por_inventario);
    # si el producto existe pero esta inactivo, no hay saldo que
    # calcular -- se reporta como no encontrado en vez de un error 500.
    validators.validar_producto_inventario_pertenece(
        producto_inventario if saldo is not None else None, inventario_id
    )
    movimientos = repository.movimientos_por_producto_en_periodo(db, inventario_id, desde)
    vencimientos = repository.fecha_vencimiento_minima_por_producto(db, inventario_id)

    return _indicador_de(
        saldo,
        dias_analisis,
        movimientos.get(producto_inventario_id, {}),
        vencimientos.get(producto_inventario_id),
        ahora,
    )
