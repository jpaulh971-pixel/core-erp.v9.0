# INFORME TÉCNICO — FASE 4C BACKEND: REPORTES GERENCIALES DE INVENTARIO

## 1. Punto de partida

Se trabajó únicamente desde el checkpoint aprobado `Core_ERP_Fase4B_Validacion_Dashboard.zip`
(contenido dentro del ZIP entregado en Fase 4B, `proyecto_actualizado/`). No se modificó
arquitectura, no se eliminó ningún módulo, no se rehizo ningún cálculo existente.

## 2. Backup previo

Antes de tocar cualquier archivo se generó un backup completo del backend:

```
backend/backups/20260802_072658_pre_fase4c_reportes_gerenciales_inventario/
    app/        (copia completa de backend/app tal como estaba al iniciar Fase 4C)
    main.py     (copia adicional del main.py original)
```

## 3. Archivos creados

Módulo nuevo completo, con la arquitectura obligatoria Repository → Service → Router →
Schemas → Validators:

```
backend/app/modules/m24_reportes_gerenciales_inventario/
├── __init__.py
├── models.py       (sin tablas propias — mismo patrón que m23_dashboard_inventario)
├── schemas.py       (ResumenEjecutivoInventario, ReporteTopValorInventario,
                       ReporteProductosCriticos, ReporteProductosSinRotacion)
├── repository.py     (listar_inventarios reexportado + ultima consulta nueva:
                       ultimo_movimiento_por_producto)
├── service.py         (orquesta y consolida m19/m22/m23, sin recalcular nada)
├── router.py            (4 endpoints GET)
├── validators.py          (validación de query params: limite, dias_sin_rotacion)
├── static/                (vacío, presente por convención del resto de módulos)
└── templates/              (vacío, presente por convención del resto de módulos)
```

Documentación y evidencias:

```
backend/INFORME_TECNICO_FASE4C_BACKEND_REPORTES_GERENCIALES.md   (este archivo)
backend/RESUMEN_ARCHIVOS_MODIFICADOS_FASE4C.txt
backend/test_fase4c_reportes_gerenciales.py                       (script de pruebas funcionales)
backend/evidencias_pruebas_fase4c/                                  (logs de ejecución real)
```

## 4. Archivos modificados (forma aditiva, sin tocar código existente)

| Archivo | Cambio |
|---|---|
| `backend/app/main.py` | 2 líneas agregadas: import de `m24_router` y `app.include_router(m24_router)`, al final de la lista existente. Ningún router ni import previo se tocó. |
| `backend/app/config.py` | 1 setting nuevo agregado al final de la clase `Settings`: `UMBRAL_DIAS_SIN_ROTACION: int = 30`. Ningún setting existente se modificó. |

Ningún otro archivo del backend fue tocado.

## 5. Arquitectura utilizada

Se respetó el mismo patrón que ya usan `m19_reportes`, `m22_inteligencia_inventario` y
`m23_dashboard_inventario`:

```
router.py  -> valida query params (validators.py) -> llama a service.py
service.py -> orquesta: llama a los service.py de m19/m22/m23 (y a m03 para costo
              unitario promedio), combina resultados, arma los schemas de respuesta
repository.py -> SOLO la consulta que no existía en ningún otro módulo
                 (ultimo_movimiento_por_producto sobre MovimientoKardex)
schemas.py -> Pydantic, sin campos de escritura (módulo 100% de solo lectura)
models.py  -> sin tablas propias (igual que m23), documentado el motivo
```

## 6. Endpoints creados

Prefijo: `/api/reportes-gerenciales-inventario`

| Método | Ruta | Descripción | Origen del cálculo |
|---|---|---|---|
| GET | `/resumen` | Resumen ejecutivo (7 indicadores) | `m23_dashboard_inventario.service.resumen_dashboard()` — reexpuesto tal cual, cero recálculo |
| GET | `/top-valor?limite=N` | Ranking de productos por valor | `m19_reportes.service.reporte_inventario_valorizado()` — ordenado y con `%` de participación derivado |
| GET | `/productos-criticos` | Bajo stock + riesgo de merma alto/crítico + próximos a vencer + vencidos | `m19_reportes` (valorizado, próximos a vencer) + `m22_inteligencia_inventario` (riesgo de merma) |
| GET | `/sin-rotacion?dias_sin_rotacion=N` | Productos con stock sin consumo | `m22_inteligencia_inventario` (`sin_consumo`/`stock_inmovilizado`) + consulta nueva de última fecha de movimiento (Kardex) |

Los 4 endpoints requieren autenticación (`Depends(get_usuario_actual)`), igual que el
resto del ERP.

## 7. Módulos reutilizados (sin duplicar lógica)

- **m03_inventario**: `service.saldos()` (costo unitario promedio por producto, para
  `valor_comprometido` / `valor_inventario`), `repository.listar_inventarios()` (vía
  reexport en m24, mismo criterio que ya usa m23).
- **m19_reportes**: `service.reporte_inventario_valorizado()` (bajo stock, top-valor),
  `service.reporte_proximos_vencer(inventario_id=None)` (próximos a vencer / vencidos).
- **m22_inteligencia_inventario**: `service.indicadores_inventario()` (riesgo de merma,
  `sin_consumo`, `stock_inmovilizado`) — recorrido por inventario, igual criterio que ya
  usa `m23_dashboard_inventario.service._riesgo_merma_total` (m22 no expone una versión
  global de este cálculo, por eso se recorre en el módulo consumidor sin reimplementarlo).
- **m23_dashboard_inventario**: `service.resumen_dashboard()` — reutilizado literal, sin
  ningún campo recalculado.

**Único cálculo nuevo agregado por m24** (porque no existía en ningún módulo fuente):
`repository.ultimo_movimiento_por_producto()`, una consulta de solo lectura sobre
`MovimientoKardex` (fecha máxima por `producto_inventario_id`), necesaria para calcular
`dias_sin_movimiento` en el reporte "Productos sin rotación". No duplica ningún cálculo
de stock, costo o kardex existente — solo lee una fecha que ningún reporte anterior
exponía.

## 8. Pruebas realizadas

Todas ejecutadas contra el motor real (FastAPI + SQLAlchemy + SQLite), sin mocks:

1. **`py_compile` completo de `backend/app`** → OK, sin errores (ver
   `evidencias_pruebas_fase4c/evidencia_py_compile.log`).
2. **Verificación de imports** → `import app.main` se ejecuta sin errores.
3. **Verificación de registro de router** → `m24_router` presente en `app.routes`.
4. **Verificación de rutas duplicadas** → se recorrieron todas las rutas registradas
   (path + métodos) buscando colisiones: 0 duplicados.
5. **Levantamiento de FastAPI real** → `TestClient(app)` sobre la app completa (con
   todos los módulos existentes cargados).
6. **Datos de prueba creados**: 1 inventario, 5 productos (con distintos escenarios:
   bajo stock, próximo a vencer, vencido, sin rotación, alto valor/normal), 5 lotes, 5
   movimientos de Kardex con fechas desplazadas en el tiempo.
7. **Pruebas de los 4 endpoints reales** (`/resumen`, `/top-valor`,
   `/productos-criticos`, `/sin-rotacion`) → 200 OK, resultados coherentes con los datos
   de prueba (ver `evidencias_pruebas_fase4c/evidencia_endpoints_m24.log`).
8. **Validación de parámetros inválidos** (`limite=0`, `dias_sin_rotacion=-5`) → 400 Bad
   Request con el mensaje esperado.
9. **Validación de Swagger/OpenAPI** → `GET /openapi.json` incluye las 4 rutas nuevas
   bajo el tag `reportes-gerenciales-inventario`.
10. **Verificación cruzada contra módulos fuente**: se comparó programáticamente que
    `/resumen` de m24 es idéntico byte-a-byte (mismo dict) al resultado de
    `m23_dashboard_inventario.service.resumen_dashboard()`, y que la suma de
    `valor_total` en `/top-valor` coincide con `valor_total_inventario` de
    `m19_reportes.service.reporte_inventario_valorizado()`.
11. **Regresión de fases anteriores**: se re-ejecutaron los scripts de prueba ya
    existentes en el proyecto (`test_fase1_seguridad_perecibles.py`,
    `test_fase2_control_gerencial_perecibles.py`,
    `test_fase3_inteligencia_inventario.py`) contra el backend actualizado con m24 ya
    registrado → los 3 terminaron con "TODOS LOS CASOS OK", sin ninguna regresión (ver
    `evidencias_pruebas_fase4c/evidencia_regresion_*.log`).

## 9. Limitaciones encontradas

- **Granularidad de `productos-criticos` por tipo VENCIMIENTO**: el reporte de
  vencimiento (`m19_reportes.reporte_proximos_vencer`) trabaja a nivel de **lote**, no de
  producto. Si un producto tiene dos lotes críticos, aparece dos veces en
  `productos-criticos` (una fila por lote), igual que ya ocurre en el reporte fuente de
  m19. No se agregó una deduplicación por producto para no introducir un criterio de
  agregación nuevo que el brief no pidió explícitamente (ej. ¿sumar stock? ¿quedarse con
  el lote más crítico?); queda como decisión de negocio pendiente para una fase futura
  si se requiere.
- **`dias_sin_movimiento = null`**: cuando un producto con stock nunca tuvo un
  `MovimientoKardex` registrado (ej. datos migrados directamente a Lote sin pasar por
  Kardex), el campo se reporta como `null` en vez de un número, porque no hay fecha de
  referencia real desde la cual contar. El producto igual aparece en el reporte (se
  interpreta como el caso más crítico de "sin rotación", ya que no hay evidencia de
  ningún movimiento).
- **`sin-rotacion` limitado a la ventana de análisis de m22**: la clasificación
  `sin_consumo` / `stock_inmovilizado` que usa este reporte proviene de
  `m22_inteligencia_inventario`, que analiza por defecto los últimos
  `DIAS_ANALISIS_INVENTARIO_DEFAULT` (90) días de Kardex. Un producto sin movimientos
  desde antes de esa ventana igual queda correctamente marcado como sin rotación (la
  ventana solo afecta el cálculo de consumo/rotación de m22, no la fecha real del último
  movimiento, que se calcula aparte con la consulta nueva de m24).
- **Entorno de pruebas**: se usó SQLite (mismo motor que usa el proyecto por defecto vía
  `DATABASE_URL`), no se probó contra PostgreSQL/otro motor de producción si el
  despliegue real usa uno distinto.
