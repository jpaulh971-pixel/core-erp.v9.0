"""Esquemas Pydantic (request/response) del modulo m22_inteligencia_inventario.

FASE 3 -- Inteligencia de inventario para perecibles. Modulo de SOLO
LECTURA: no define ningun schema de escritura (no hay Crear/Actualizar),
porque no persiste nada nuevo -- solo calcula indicadores sobre datos que
ya existen en m03_inventario (Lote, MovimientoKardex, ProductoInventario).
"""
from typing import Optional

from pydantic import BaseModel, Field


class IndicadorInventario(BaseModel):
    """Indicadores de inteligencia de inventario para UN producto dentro
    de UN inventario, calculados sobre datos reales de Kardex/Lotes (sin
    datos simulados). Cubre los 4 calculos pedidos en Fase 3: rotacion,
    dias de inventario, consumo promedio y riesgo de merma.
    """

    # --- Identificacion (mismo criterio que SaldoProductoOut de m03) ---
    producto_inventario_id: int
    inventario_id: int
    producto_id: int
    codigo_interno: str
    nombre: str

    # --- Datos base reutilizados de m03_inventario.saldos() ---
    stock_actual: float = Field(description="Stock disponible actual (suma de Lote.cantidad_actual).")

    # --- Ventana de analisis usada para consumo/rotacion ---
    dias_analisis: int = Field(
        description="Cantidad de dias de historial de Kardex considerados para consumo real, "
        "consumo promedio y rotacion (parametrizable via query param, ver router)."
    )

    # --- 1. Rotacion de inventario ---
    consumo_real_periodo: float = Field(
        description="Unidades de SALIDA reales registradas en el Kardex dentro de la ventana de "
        "dias_analisis (consumo real, no estimado)."
    )
    stock_promedio_periodo: float = Field(
        description="Promedio entre el stock reconstruido al inicio de la ventana (a partir de los "
        "movimientos reales de Kardex: ingresos, salidas y ajustes) y el stock actual."
    )
    rotacion_inventario: Optional[float] = Field(
        default=None,
        description="consumo_real_periodo / stock_promedio_periodo. None cuando "
        "stock_promedio_periodo es 0 (division invalida: no hubo stock que rotar en el periodo).",
    )

    # --- 3. Consumo promedio (a partir de consumo_real_periodo / dias_analisis) ---
    consumo_promedio_diario: float = Field(description="consumo_real_periodo / dias_analisis.")
    consumo_promedio_semanal: float = Field(description="consumo_promedio_diario * 7.")
    consumo_promedio_mensual: float = Field(description="consumo_promedio_diario * 30.")

    # --- 2. Dias de inventario ---
    dias_inventario: Optional[float] = Field(
        default=None,
        description="stock_actual / consumo_promedio_diario. None cuando consumo_promedio_diario "
        "es 0 y hay stock (division invalida / consumo cero: no se puede estimar cobertura). "
        "Es 0 cuando stock_actual es 0 (no hay inventario que cubrir, sin importar el consumo).",
    )
    sin_consumo: bool = Field(
        description="True si no hubo ninguna SALIDA de Kardex en la ventana de analisis."
    )
    sin_stock: bool = Field(description="True si stock_actual es 0.")

    # --- Insumos reutilizados para el riesgo de merma (de m03: Lote.fecha_vencimiento) ---
    dias_restantes_vencimiento: Optional[int] = Field(
        default=None,
        description="Dias restantes hasta el vencimiento del lote vigente (stock>0) mas proximo a "
        "vencer de este producto. Negativo si ya esta vencido. None si ningun lote con stock tiene "
        "fecha de vencimiento (producto no perecible o sin dato).",
    )
    stock_inmovilizado: bool = Field(
        description="True si stock_actual > 0 pero consumo_real_periodo es 0 (stock sin ningun "
        "movimiento de salida en la ventana analizada)."
    )

    # --- 4. Riesgo de merma ---
    riesgo_merma: str = Field(
        description="Clasificacion final: BAJO, MEDIO, ALTO o CRITICO. Ver "
        "service.evaluar_riesgo_merma() para el detalle centralizado y parametrizable del calculo."
    )
    score_riesgo_merma: int = Field(
        description="Puntaje interno (0-12) que produjo la clasificacion de riesgo_merma. Se expone "
        "para trazabilidad/auditoria del calculo, no es un indicador de negocio en si mismo."
    )


class ResumenInteligenciaInventario(BaseModel):
    """Envoltorio de lista con metadatos del calculo. No agrega ningun
    indicador nuevo: es solo el contenedor de la lista de
    IndicadorInventario para un inventario completo."""

    inventario_id: int
    dias_analisis: int
    total_productos: int
    productos_riesgo_critico: int
    productos_riesgo_alto: int
    indicadores: list[IndicadorInventario]
