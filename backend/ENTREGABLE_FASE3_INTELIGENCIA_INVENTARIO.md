# FASE 3 — Inteligencia de inventario para perecibles
## Entregable técnico / informe de trazabilidad

Fecha de generación: 2026-08-02

---

## ⚠️ Aviso de trazabilidad — IMPORTANTE, leer antes de aprobar la fase

Este ZIP se generó en un entorno de trabajo **sin acceso a red**. Se
intentó `pip install fastapi sqlalchemy pydantic pydantic-settings
python-jose passlib python-multipart` y falló con `No matching
distribution found` — no hay ningún paquete de `requirements.txt`
instalado ni instalable en este entorno (mismo tipo de limitación que
ya se documentó en el entregable de Fase 2).

En consecuencia:

- ✅ **Confirmado por ejecución real**: `python -m py_compile` sobre
  **todo el árbol `app/`** (incluye los 6 archivos nuevos del módulo
  `m22_inteligencia_inventario` y los 2 archivos modificados,
  `config.py` y `main.py`) — sin errores.
- ✅ **Confirmado por ejecución real**: parseo AST individual de los 7
  archivos nuevos/modificados — sin errores de sintaxis.
- ✅ **Confirmado por ejecución real**: script de verificación que
  recorre los 21 `router.py` del proyecto (incluye el nuevo) y compara
  method+path de las 127 rutas totales del sistema — **0 duplicados**,
  y 0 nombres de función duplicados dentro de un mismo router.
- ✅ **Confirmado por ejecución real**: script que recorre los 277
  imports internos `app.*` de todo el árbol y verifica que cada módulo
  importado resuelve a un archivo/paquete real en disco — **0 imports
  rotos**.
- ✅ **Confirmado por ejecución real**: las 4 funciones de cálculo puro
  del módulo nuevo (`calcular_rotacion`, `calcular_consumo_promedio`,
  `calcular_dias_inventario`, `evaluar_riesgo_merma`) se **extrajeron y
  ejecutaron de forma aislada en Python puro** (sin fastapi/sqlalchemy/
  pydantic, que no están disponibles aquí) contra los mismos 9
  escenarios numéricos que usa `test_fase3_inteligencia_inventario.py`
  — los 13 checks numéricos pasaron. Esto confirma que los valores
  esperados escritos en el test real son aritméticamente correctos,
  pero **no reemplaza** una corrida real del test contra SQLAlchemy/
  SQLite (ver más abajo).
- ❌ **NO confirmado por ejecución real**: que
  `test_fase3_inteligencia_inventario.py` pase con el motor real
  (FastAPI + SQLAlchemy + SQLite), ni que los scripts de regresión ya
  existentes (`test_fase1_seguridad_perecibles.py`,
  `test_fase2_control_gerencial_perecibles.py`,
  `test_costo_unitario_inventario_frontend.py`,
  `test_costo_unitario_ventas_frontend.py`, `test_fase10_cierre_e2e.py`,
  `test_flujo_guia.py`) sigan pasando sin cambios. Este entorno nunca
  tuvo acceso a `pip`.

**Acción requerida antes de dar la Fase 3 por aprobada**, en un entorno
con acceso a `pip`:

```bash
cd backend
pip install -r requirements.txt --break-system-packages
python test_fase1_seguridad_perecibles.py
python test_fase2_control_gerencial_perecibles.py
python test_fase3_inteligencia_inventario.py
python test_costo_unitario_inventario_frontend.py
python test_costo_unitario_ventas_frontend.py
python test_fase10_cierre_e2e.py
python test_flujo_guia.py
```

Todos deben terminar con código de salida `0` y sin líneas `FALLO`. Si
alguno falla, la Fase 3 **no** debe darse por aprobada hasta corregirlo.

---

## 1. Alcance cumplido

Módulo de inteligencia de inventario para perecibles, **100% de solo
lectura**, con los 4 cálculos pedidos y nada más:

1. ✅ Rotación de inventario
2. ✅ Días de inventario
3. ✅ Consumo promedio (diario / semanal / mensual)
4. ✅ Riesgo de merma (BAJO / MEDIO / ALTO / CRÍTICO)

No se implementó ningún cálculo, endpoint ni pantalla fuera de estos 4
puntos.

---

## 2. Archivos identificados como afectados (antes de tocar nada)

Se identificaron **2 archivos existentes** a modificar (ambos de forma
puramente aditiva) y **1 módulo nuevo** a crear:

| Archivo | Tipo de cambio |
|---|---|
| `backend/app/config.py` | Aditivo: se agregan 12 settings nuevas (umbrales parametrizables de Fase 3). Ninguna línea existente se tocó. |
| `backend/app/main.py` | Aditivo: 1 línea de import + 1 línea de `include_router` para el nuevo router. Ninguna línea existente se tocó. |
| `backend/app/modules/m22_inteligencia_inventario/` (nuevo) | Módulo nuevo completo: `__init__.py`, `repository.py`, `service.py`, `schemas.py`, `validators.py`, `router.py`. No lleva `models.py` porque no crea ninguna tabla. |

Ningún otro archivo del proyecto fue tocado.

---

## 3. Backups y checkpoint (previos a cualquier modificación)

- **Checkpoint completo previo a Fase 3**:
  `backups/CHECKPOINT_PRE_FASE3_20260802_045410.zip` (raíz de este
  entregable) — copia íntegra del proyecto tal como llegó (cierre de
  Fase 2), generada **antes** de escribir cualquier línea de esta fase.
- **Backups puntuales** (carpeta
  `backups/20260802_045410_pre_fase3_inteligencia_inventario/`):
  - `config.py.bak` — copia de `config.py` antes de agregar las 12
    settings nuevas.
  - `main.py.bak` — copia de `main.py` antes de registrar el router
    nuevo.

Diff real backup → archivo final (ver sección 8, "Validaciones
realizadas") confirma que ambos cambios son **estrictamente aditivos**:
solo líneas agregadas (`>`), cero líneas eliminadas o modificadas.

---

## 4. Diseño técnico

### 4.1 Arquitectura

Se siguió exactamente el patrón `Repository → Service → Router →
Schemas → Validators` ya usado en `m03_inventario` y `m19_reportes`:

- **`repository.py`**: 2 queries SQLAlchemy nuevas, ambas de solo
  lectura sobre tablas ya existentes (`MovimientoKardex`, `Lote`,
  `ProductoInventario`). No se crea ninguna tabla ni columna.
- **`service.py`**: lógica de negocio pura y centralizada (ver 4.2),
  más la orquestación que reutiliza `m03_inventario.service.saldos()` y
  `m03_inventario.service.calcular_semaforo_vencimiento()` (Fase 1/2)
  para no duplicar ningún cálculo ya existente.
- **`schemas.py`**: `IndicadorInventario` (por producto) y
  `ResumenInteligenciaInventario` (envoltorio de lista).
- **`validators.py`**: validación de `dias_analisis` y de pertenencia
  producto↔inventario, mismo criterio que `m03_inventario.validators`.
- **`router.py`**: 2 endpoints GET, mismo patrón `APIRouter(prefix=...,
  tags=...)` + `Depends(get_db)` / `Depends(get_usuario_actual)` que
  todos los routers del proyecto.

### 4.2 Cálculos implementados (lógica centralizada y parametrizable)

Las 4 funciones puras viven en
`m22_inteligencia_inventario/service.py` y son la única fuente de
verdad de cada cálculo — cualquier módulo futuro puede reutilizarlas
sin duplicar lógica (mismo criterio que ya aplica
`m03_inventario.service.calcular_semaforo_vencimiento` /
`calcular_semaforo_stock`):

**Rotación de inventario** (`calcular_rotacion`)
`rotación = consumo_real_periodo / stock_promedio_periodo`
- `consumo_real_periodo`: suma de `MovimientoKardex.cantidad` con
  `tipo_movimiento = 'SALIDA'` dentro de la ventana de `dias_analisis`
  (dato real de Kardex, no simulado).
- `stock_promedio_periodo`: `(stock_inicial_estimado + stock_actual) /
  2`, donde `stock_inicial_estimado` se reconstruye a partir del
  Kardex real (`stock_final − ingresos + salidas − ajustes_pos +
  ajustes_neg`), nunca simulado.
- División inválida (`stock_promedio_periodo <= 0`) → `None`, nunca
  `ZeroDivisionError`.

**Días de inventario** (`calcular_dias_inventario`)
`días_inventario = stock_disponible / consumo_promedio_diario`
- `stock_actual <= 0` → `0.0` (sin importar el consumo), flag
  `sin_stock=True`.
- `stock_actual > 0` y `consumo_promedio_diario <= 0` → `None`
  (división inválida, consumo cero), flag `sin_consumo=True`.
- Caso normal → división directa.

**Consumo promedio** (`calcular_consumo_promedio`)
`diario = consumo_real_periodo / dias_analisis`; `semanal = diario ×
7`; `mensual = diario × 30`. Construido únicamente sobre movimientos
reales de `SALIDA` del Kardex — no usa datos simulados.

**Riesgo de merma** (`evaluar_riesgo_merma`)
Sistema de puntaje (score 0-12) centralizado y 100% parametrizable vía
`app.config.settings`, con 4 factores basados en datos reales
disponibles:

| Factor | Peso máx. | Fuente real |
|---|---|---|
| Días para vencer | 4 | `Lote.fecha_vencimiento` del lote con stock más próximo a vencer (o ya vencido) |
| Rotación | 3 | `calcular_rotacion()` de arriba |
| Días de inventario | 3 | `calcular_dias_inventario()` de arriba |
| Stock inmovilizado | 2 | `stock_actual > 0` y `consumo_real_periodo == 0` |

El score total se mapea a BAJO / MEDIO / ALTO / CRÍTICO vía 3 umbrales
también parametrizables (`SCORE_RIESGO_MERMA_MEDIO/ALTO/CRITICO`). Un
factor sin dato disponible (ej. producto no perecible sin
`fecha_vencimiento`) suma 0 puntos — nunca penaliza por ausencia de
dato.

### 4.3 Reutilización de infraestructura existente (sin duplicar lógica)

- `m03_inventario.service.saldos()` → stock actual, costo unitario
  promedio, semáforo de stock (Fase 2) — reutilizado tal cual.
- `m03_inventario.service.calcular_semaforo_vencimiento()` → días
  restantes de vencimiento — reutilizado tal cual (Fase 1/2).
- `m03_inventario.repository.obtener_producto_inventario_por_id()` →
  reutilizado para el endpoint de detalle por producto.
- Ninguna consulta a `MovimientoKardex` o `Lote` se duplica: hay
  exactamente 2 queries nuevas (una por Kardex, una por vencimientos),
  reutilizadas tanto por el endpoint de lista como por el de detalle.

---

## 5. Endpoints nuevos

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/api/inteligencia-inventario/{inventario_id}` | Indicadores (rotación, días de inventario, consumo promedio, riesgo de merma) de todos los productos de un inventario. Query param opcional `dias_analisis`. |
| `GET` | `/api/inteligencia-inventario/{inventario_id}/{producto_inventario_id}` | Mismo cálculo para un solo producto (reutiliza la misma lógica, sin cálculos nuevos). |

Ningún endpoint existente fue modificado, movido ni eliminado. Total de
rutas del sistema tras la fase: **127** (verificado por script, sección
8), sin colisión con las ya existentes.

---

## 6. Funciones nuevas

**`m22_inteligencia_inventario/repository.py`**
- `movimientos_por_producto_en_periodo(db, inventario_id, desde)`
- `fecha_vencimiento_minima_por_producto(db, inventario_id)`

**`m22_inteligencia_inventario/service.py`**
- `calcular_rotacion(consumo_real_periodo, stock_promedio_periodo)`
- `calcular_consumo_promedio(consumo_real_periodo, dias_analisis)`
- `calcular_dias_inventario(stock_actual, consumo_promedio_diario)`
- `evaluar_riesgo_merma(dias_restantes, rotacion, dias_inventario, stock_inmovilizado)`
- `_indicador_de(...)` (privada, arma un `IndicadorInventario`)
- `indicadores_inventario(db, inventario_id, dias_analisis)`
- `indicador_producto(db, inventario_id, producto_inventario_id, dias_analisis)`

**`m22_inteligencia_inventario/validators.py`**
- `validar_dias_analisis(dias_analisis)`
- `validar_producto_inventario_pertenece(producto_inventario, inventario_id)`

**`m22_inteligencia_inventario/router.py`**
- `indicadores_inventario(...)` (handler del endpoint de lista)
- `indicador_producto(...)` (handler del endpoint de detalle)

---

## 7. Cálculos implementados

1. Rotación de inventario (consumo real / stock promedio, con stock
   promedio reconstruido desde Kardex real).
2. Días de inventario (stock disponible / consumo promedio diario, con
   manejo explícito de consumo cero, stock cero y división inválida).
3. Consumo promedio diario, semanal y mensual (a partir de SALIDA real
   de Kardex).
4. Riesgo de merma en 4 niveles (BAJO/MEDIO/ALTO/CRÍTICO), score
   centralizado y parametrizable combinando días para vencer, rotación,
   días de inventario y stock inmovilizado.

---

## 8. Validaciones realizadas (todas por ejecución real de scripts en este entorno)

| Validación | Resultado |
|---|---|
| `py_compile` de todo `app/` | ✅ OK, sin errores |
| Parseo AST de los 7 archivos nuevos/modificados | ✅ OK, sin errores |
| Rutas duplicadas (method+path) en los 21 routers | ✅ 0 duplicados / 127 rutas únicas |
| Funciones duplicadas dentro de un mismo router | ✅ 0 duplicados |
| Imports internos `app.*` rotos (277 imports revisados) | ✅ 0 rotos |
| Archivos basura (`__pycache__`, `.pyc`, temporales, `.db` sueltos) | ✅ Se eliminaron `__pycache__`/`.pyc` preexistentes (de fases anteriores, no generados por esta fase); no quedan bases de datos ni temporales sueltos |
| Diff backup → archivo final de `config.py` y `main.py` | ✅ Estrictamente aditivo (solo líneas `>`, 0 líneas eliminadas/modificadas) |
| Consistencia de campos usados en `service.py` contra `schemas.IndicadorInventario` | ✅ Revisión manual campo a campo |
| Verificación aritmética de las 4 funciones de cálculo puro, ejecutada de forma aislada en Python estándar (sin dependencias externas) contra los 9 escenarios del test real | ✅ 13/13 checks numéricos correctos |
| Ejecución real de `test_fase3_inteligencia_inventario.py` contra FastAPI/SQLAlchemy/SQLite | ❌ No disponible en este entorno (sin acceso a `pip`/red) — pendiente en entorno con dependencias instaladas |
| Ejecución real de los 6 scripts de regresión de fases previas | ❌ No disponible en este entorno — pendiente |

---

## 9. Limitaciones encontradas

- **Sin acceso a red/pip en este entorno**: impide instalar
  `requirements.txt` y por lo tanto ejecutar cualquier test real contra
  el motor FastAPI/SQLAlchemy/SQLite (ni los nuevos de Fase 3 ni los 6
  ya existentes de fases anteriores). Se documentó explícitamente en
  vez de simular resultados, y se dejó como acción obligatoria antes de
  aprobar la fase (sección "Aviso de trazabilidad").
- **`stock_promedio_periodo` es una aproximación de 2 puntos**
  (inicio/fin del período), no un promedio ponderado por tiempo día a
  día. Se eligió así porque el sistema no mantiene una tabla de
  snapshots diarios de stock (y esta fase tiene prohibido crear tablas
  nuevas); es la misma limitación de datos que tendría cualquier
  cálculo de rotación clásico sobre un ERP sin snapshots históricos, y
  queda documentada en el docstring de `_indicador_de()`.
- **`stock_inicial_estimado` se acota en 0** si el Kardex del período
  analizado no alcanza a cubrir todo el historial real del producto (o
  hay datos parciales); es una defensa explícita para no reportar un
  stock inicial negativo sin sentido de negocio, documentada en el
  código.

---

## 10. Resumen de archivos modificados / creados

**Modificados (aditivo, con backup previo)**
- `backend/app/config.py`
- `backend/app/main.py`

**Creados**
- `backend/app/modules/m22_inteligencia_inventario/__init__.py`
- `backend/app/modules/m22_inteligencia_inventario/repository.py` (73 líneas)
- `backend/app/modules/m22_inteligencia_inventario/service.py` (307 líneas)
- `backend/app/modules/m22_inteligencia_inventario/schemas.py` (101 líneas)
- `backend/app/modules/m22_inteligencia_inventario/validators.py` (25 líneas)
- `backend/app/modules/m22_inteligencia_inventario/router.py` (52 líneas)
- `backend/test_fase3_inteligencia_inventario.py` (329 líneas, 11 casos)
- `backend/ENTREGABLE_FASE3_INTELIGENCIA_INVENTARIO.md` (este archivo)

**No tocados**: absolutamente ningún otro archivo del proyecto (front
end, otros módulos backend, modelos, migraciones, tests previos).
