# FASE 2 — Control gerencial para inventario perecible
## Entregable final

Fecha de generación: 2026-08-01
Fecha de actualización (cierre de pendientes): 2026-08-02

---

## ⚠️ Aviso de trazabilidad — IMPORTANTE, leer antes de aprobar la fase

Este ZIP se generó en un entorno de trabajo **sin acceso a red**, en dos
pasadas (2026-08-01 y 2026-08-02). En ambas se pudo verificar la
**sintaxis** de todos los archivos modificados (`python -m py_compile`,
sin errores, incluido el árbol completo `app/`), pero **no fue posible
instalar `requirements.txt` (fastapi/sqlalchemy/pydantic) ni ejecutar
los scripts de prueba**, ni los nuevos (`test_fase2_...py`) ni los 5 ya
existentes de Fase 1 y anteriores.

En consecuencia:

- ✅ Confirmado: no se tocó ningún modelo, ningún archivo de frontend,
  `main.py`, ni ninguna lógica fuera de `m03_inventario` y
  `m19_reportes`. Revisión manual línea por línea de cada cambio, en
  ambas pasadas, contra los backups correspondientes.
- ✅ Confirmado: sintaxis Python válida en los 9 archivos modificados en
  total (los 8 de la primera pasada + `exportadores.py`, agregado en la
  segunda) y en el árbol completo `app/` (`py_compile` sin errores).
- ✅ Confirmado (segunda pasada, auditoría independiente antes de tocar
  código): la lógica pura de `calcular_semaforo_vencimiento()` y
  `calcular_semaforo_stock()` fue reimplementada de forma aislada (sin
  dependencias de terceros) y verificada contra los 6 casos del brief
  más 8 casos de borde adicionales (29/30/90/91 días; stock
  igual/cercano/bajo el mínimo/mínimo=0) — los 14 casos pasan.
- ✅ Confirmado (segunda pasada): cada campo (`l.xxx`, `reporte.xxx`)
  usado en las nuevas funciones de exportación existe realmente en los
  schemas Pydantic correspondientes (`LotePorProducto`,
  `LoteProximoVencer`, `ReporteInventarioPorLote`,
  `ReporteProximosVencer`) — verificado por comparación automática de
  nombres de campo, no solo por lectura manual.
- ✅ Confirmado (segunda pasada): las 4 rutas de exportación nuevas
  quedaron registradas sin colisión de nombre de función ni de path con
  ninguna de las 14 rutas ya existentes del router.
- ❌ **NO confirmado por ejecución real**: que los 6 casos de prueba de
  `test_fase2_control_gerencial_perecibles.py` pasen con el motor real
  (SQLAlchemy + SQLite), ni que los 5 scripts de regresión existentes
  (`test_fase1_seguridad_perecibles.py`,
  `test_costo_unitario_inventario_frontend.py`,
  `test_costo_unitario_ventas_frontend.py`, `test_fase10_cierre_e2e.py`,
  `test_flujo_guia.py`) sigan pasando sin cambios. Este entorno nunca
  tuvo acceso a `pip`, en ninguna de las dos pasadas.

**Acción requerida antes de dar la Fase 2 por aprobada**, en un entorno
con acceso a `pip`:

```bash
cd backend
pip install -r requirements.txt --break-system-packages
python test_fase1_seguridad_perecibles.py
python test_fase2_control_gerencial_perecibles.py
python test_costo_unitario_inventario_frontend.py
python test_costo_unitario_ventas_frontend.py
python test_fase10_cierre_e2e.py
python test_flujo_guia.py
```

Todos deben terminar con código de salida `0` y sin líneas `FALLO`.
Si alguno falla, la Fase 2 **no** debe darse por aprobada hasta
corregirlo — los criterios de aceptación de la sección 8 del brief
(FEFO, Kardex y costos intactos) dependen de esa confirmación real, que
este entorno no pudo producir.

---

## 0. Cierre de pendientes (segunda pasada, 2026-08-02)

Una auditoría previa de esta misma fase (solo lectura, sin modificar
código) detectó dos pendientes reales frente al patrón ya establecido
en `m19_reportes`:

1. Los dos reportes nuevos de Fase 2 (`inventario-por-lote`,
   `proximos-vencer`) no tenían exportación a Excel/PDF, mientras que
   los 4 reportes ya existentes (`ventas`, `compras`,
   `inventario-valorizado`, `resumen-general`) sí la tienen.
2. Ningún test había sido ejecutado realmente (persiste — ver aviso de
   trazabilidad arriba; no es corregible sin acceso a red).

Esta segunda pasada cierra el pendiente **(1)** únicamente. Alcance
explícitamente **excluido** de esta pasada, por instrucción directa:
ningún refactor, ninguna modificación de lógica ya funcionando, ningún
cambio de frontend, ninguna fase nueva, ninguna funcionalidad fuera de
lo pedido. El pendiente (2) sigue abierto y depende de un entorno con
acceso a `pip`.

### 0.1 Qué se agregó

- `app/modules/m19_reportes/exportadores.py`: 8 funciones nuevas
  (`_fecha_texto`, `_dias_restantes_texto`, `_filas_inventario_por_lote`,
  `inventario_por_lote_excel`, `inventario_por_lote_pdf`,
  `_filas_proximos_vencer`, `proximos_vencer_excel`,
  `proximos_vencer_pdf`), agregadas al final del archivo, después de
  las funciones de `resumen_general`. Reutilizan sin modificar los dos
  helpers genéricos ya existentes (`_excel_desde_hojas`,
  `_pdf_desde_secciones`) — mismo patrón que usan `ventas_excel`,
  `compras_pdf`, etc. No consultan la base de datos: reciben los mismos
  objetos Pydantic (`schemas.ReporteInventarioPorLote`,
  `schemas.ReporteProximosVencer`) que ya devuelven
  `service.reporte_inventario_por_lote()` y
  `service.reporte_proximos_vencer()` (sin cambios en esos servicios).
- `app/modules/m19_reportes/router.py`: 4 endpoints `GET` nuevos,
  agregados después de `/resumen-general/exportar/pdf`, reutilizando
  sin modificar el helper `_descarga()` ya existente y las constantes
  `MEDIA_XLSX`/`MEDIA_PDF` ya existentes:
  - `GET /api/reportes/inventario-por-lote/exportar/excel?inventario_id=`
  - `GET /api/reportes/inventario-por-lote/exportar/pdf?inventario_id=`
  - `GET /api/reportes/proximos-vencer/exportar/excel?inventario_id=`
  - `GET /api/reportes/proximos-vencer/exportar/pdf?inventario_id=`

  Mismo esquema de autenticación (`get_usuario_actual`) y mismo
  parámetro opcional `inventario_id` que ya usan los endpoints JSON
  equivalentes `/inventario-por-lote` y `/proximos-vencer`.

### 0.2 Qué NO se tocó en esta pasada

- Ninguna función existente de `exportadores.py` (`ventas_excel`,
  `ventas_pdf`, `compras_excel`, `compras_pdf`,
  `inventario_valorizado_excel`, `inventario_valorizado_pdf`,
  `resumen_general_excel`, `resumen_general_pdf`, ni los dos helpers
  genéricos) — confirmado por comparación línea por línea contra el
  backup previo a esta pasada.
- Ninguna de las 14 rutas ya existentes en `router.py` — confirmado
  igual, diff limpio contra el backup previo a esta pasada (solo
  líneas agregadas, cero líneas eliminadas o modificadas).
- `service.py`, `schemas.py`, `repository.py` de `m19_reportes`: sin
  cambios (los reportes ya existían de la primera pasada; solo se les
  agregó su exportador).
- `m03_inventario` (ningún archivo): sin cambios.
- Frontend (`frontend_fase3_modulos/`): sin cambios, por instrucción
  explícita.
- Ningún modelo (`models.py`) de ningún módulo.

### 0.3 Verificaciones realizadas antes de cerrar

- `python -m py_compile` sobre los 2 archivos tocados y sobre el árbol
  completo `app/` (todos los módulos, no solo `m19_reportes`): sin
  errores.
- Verificación automática (AST) de que no hay funciones ni rutas
  duplicadas en `router.py`, ni funciones duplicadas en
  `exportadores.py`.
- Verificación automática de que cada campo referenciado en las nuevas
  funciones de exportación (`l.codigo_lote`, `reporte.valor_total`,
  etc.) existe realmente en el schema Pydantic correspondiente — no se
  encontró ningún campo inventado o faltante.
- Diff línea por línea contra backup pre-pasada: confirma que el
  cambio es 100% aditivo en ambos archivos.
- **No confirmado por ejecución real** (mismo motivo de siempre: sin
  `pip` en este entorno): que los archivos `.xlsx`/`.pdf` generados
  abran correctamente en Excel/Acrobat, ni que `openpyxl`/`reportlab`
  acepten sin error los tipos de dato pasados (fechas ya formateadas
  como texto, no como objetos `datetime`, siguiendo el mismo patrón que
  el resto del archivo). Se recomienda, en un entorno con `pip`,
  además de los 6 tests ya listados, una verificación manual mínima:
  ```bash
  curl -H "Authorization: Bearer <token>" \
    "http://localhost:8000/api/reportes/inventario-por-lote/exportar/excel" -o test.xlsx
  curl -H "Authorization: Bearer <token>" \
    "http://localhost:8000/api/reportes/proximos-vencer/exportar/pdf" -o test.pdf
  ```
  y confirmar que ambos archivos abren sin error y muestran datos.

---

## 1. Lista exacta de archivos modificados

Ninguno de estos archivos es un modelo (`models.py`) ni de frontend.

**Primera pasada (2026-08-01):**

| Archivo | Tipo de cambio |
|---|---|
| `backend/app/config.py` | Agregada 1 constante nueva |
| `backend/app/modules/m03_inventario/service.py` | Agregadas 2 funciones nuevas + 1 función existente ampliada |
| `backend/app/modules/m03_inventario/schemas.py` | Agregado 1 campo a un schema existente |
| `backend/app/modules/m19_reportes/repository.py` | Agregadas 2 funciones nuevas (solo lectura) |
| `backend/app/modules/m19_reportes/schemas.py` | Agregados 4 schemas nuevos + 1 campo a un schema existente |
| `backend/app/modules/m19_reportes/service.py` | Agregadas 2 funciones nuevas + 1 función existente ampliada |
| `backend/app/modules/m19_reportes/router.py` | Agregados 2 endpoints GET nuevos |

Archivo nuevo (test):

- `backend/test_fase2_control_gerencial_perecibles.py`

**Segunda pasada (2026-08-02) — cierre de pendiente "exportación
Excel/PDF de los reportes de Fase 2":**

| Archivo | Tipo de cambio |
|---|---|
| `backend/app/modules/m19_reportes/exportadores.py` | Agregadas 8 funciones nuevas (2 reportes × helper de filas + excel + pdf) |
| `backend/app/modules/m19_reportes/router.py` | Agregados 4 endpoints GET nuevos (excel/pdf × 2 reportes) |

**No modificado, en ninguna de las dos pasadas**:
`backend/app/modules/m03_inventario/repository.py` (se evaluó tocarlo
en la primera pasada y se revirtió — ver sección 3, riesgo evitado),
ningún archivo de `frontend_fase3_modulos/`, `app/main.py`,
`service.py`/`schemas.py`/`repository.py` de `m19_reportes` (ya
contenían todo lo necesario desde la primera pasada), ningún modelo, ni
ningún otro módulo (`m01`, `m02`, `m04`...`m21`).

Backups:

- Primera pasada, backup de los 8 archivos originales (antes de
  cualquier edición):
  `backups/20260802_030722_pre_fase2_control_gerencial_perecibles/`
- Segunda pasada, backup de `router.py` y `exportadores.py` tal como
  quedaron al cierre de la primera pasada (antes de agregarles las
  funciones de exportación):
  `backups/20260802_pre_fase2_export_pendientes/`

(ver carpeta `backups/` del ZIP).

---

## 2. Explicación técnica de cada cambio

### 2.1 `app/config.py`
Se agregó `FACTOR_ALERTA_STOCK_CERCANO: float = 1.2`. Define el margen
sobre `stock_minimo` que separa AMARILLO de VERDE en el semáforo de
stock (ver 2.2). No toca `DIAS_ALERTA_VENCIMIENTO` (Fase 1) ni ninguna
otra constante.

### 2.2 `app/modules/m03_inventario/service.py`
Se agregaron dos funciones **nuevas y centralizadas**, deliberadamente
separadas de `calcular_estado_lote()` (Fase 1, que sigue intacta):

- `calcular_semaforo_vencimiento(fecha_vencimiento, ahora=None) -> (semaforo, dias_restantes)`
  Clasifica en VERDE (>90 días), AMARILLO (30–90 días), ROJO (<30
  días), NEGRO (vencido), según lo pedido en la sección 1 del brief.
  Es de **solo lectura**: nunca participa en el bloqueo de salidas ni
  en FEFO — eso lo sigue decidiendo `calcular_estado_lote()` con su
  propio umbral (`DIAS_ALERTA_VENCIMIENTO = 30`), sin cambios.

- `calcular_semaforo_stock(stock_actual, stock_minimo) -> semaforo`
  Clasifica en ROJO (stock ≤ mínimo), AMARILLO (cercano al mínimo,
  dentro del margen `FACTOR_ALERTA_STOCK_CERCANO`), VERDE (normal),
  según la sección 2 del brief.

También se amplió `saldos()` (la función que ya existía) para agregar
`semaforo_stock` a cada fila que devuelve, **sin tocar** ningún campo
que ya traía (`stock_total`, `stock_minimo`, `bajo_stock_minimo`,
`costo_unitario_promedio` quedan exactamente igual).

### 2.3 `app/modules/m03_inventario/schemas.py`
Se agregó el campo `semaforo_stock: str` (con default `"VERDE"`, no
rompe nada si algún consumidor viejo no lo espera) al schema
`SaldoProductoOut`, que es la respuesta del endpoint ya existente
`GET /api/inventario/saldos/{inventario_id}`.

### 2.4 `app/modules/m19_reportes/repository.py`
Se agregaron dos funciones nuevas, ambas **puramente de lectura**:

- `listar_lotes(db, inventario_id=None)`: trae todos los `Lote` (con
  `ProductoInventario`/`Producto` precargados vía `joinedload`, para
  evitar N+1 queries), ordenados por fecha de vencimiento → producto →
  lote. Es la consulta base **compartida** por los dos reportes nuevos
  (evita duplicar la consulta).
- `proveedores_por_codigo_lote(db)`: arma un diccionario
  `codigo_lote -> razón social del proveedor`, reconstruyendo la
  relación a través de `OrdenCompraItem.lote` (el mismo campo que ya
  usa `m04_compras/importacion_service.py`). **No se agregó ninguna
  columna ni relación nueva al modelo** — el brief no permitía tocar
  modelos, y no existe hoy una FK directa Lote→Proveedor. Por eso el
  campo `proveedor` en el reporte queda `null` para lotes que no
  nacieron de una orden de compra con ese dato cargado (ingresos
  manuales, ajustes, etc.) — es "si existe relación", tal como pide el
  brief.

También se amplió `inventario_valorizado()` — en realidad el cambio
real de este campo está en `service.py` (ver 2.6), `repository.py`
sólo quedó con las dos funciones nuevas descritas arriba.

### 2.5 `app/modules/m19_reportes/schemas.py`
Se agregaron 4 schemas nuevos (`LotePorProducto`,
`ReporteInventarioPorLote`, `LoteProximoVencer`,
`ReporteProximosVencer`) y se agregó `semaforo_stock: str` a
`ProductoValorizado` (respuesta de
`GET /api/reportes/inventario-valorizado`, ya existente).

### 2.6 `app/modules/m19_reportes/service.py`
Se agregaron dos funciones nuevas:

- `reporte_inventario_por_lote(db, inventario_id=None)`: arma el
  reporte de la sección 3 del brief. Por cada lote calcula
  `estado_lote` reutilizando `m03_inventario.service.
  calcular_estado_lote()` (no se duplica esa lógica) y
  `semaforo_vencimiento`/`dias_restantes` reutilizando
  `calcular_semaforo_vencimiento()`. `valor_total_lote =
  cantidad_disponible × costo_unitario`.

- `reporte_proximos_vencer(db, inventario_id=None)`: arma el reporte
  de la sección 4 del brief. Sólo incluye lotes con
  `fecha_vencimiento` definida y `cantidad_disponible > 0`. La
  categoría (`ACTIVOS` / `PROXIMOS_A_VENCER` / `VENCIDOS`) se deriva
  **del mismo semáforo centralizado** (VERDE→ACTIVOS,
  AMARILLO+ROJO→PROXIMOS_A_VENCER, NEGRO→VENCIDOS), sin duplicar la
  clasificación. El orden (fecha de vencimiento → producto → lote) lo
  entrega ya armado `repository.listar_lotes()`, así que este reporte
  no vuelve a ordenar.

También se amplió `reporte_inventario_valorizado()` (ya existente)
para agregar `semaforo_stock` a cada fila, reutilizando
`calcular_semaforo_stock()`, sin tocar ningún cálculo que ya traía
(`valor_total`, `bajo_stock_minimo`, etc. quedan iguales).

### 2.7 `app/modules/m19_reportes/router.py`
Se agregaron dos endpoints nuevos, ambos `GET`, ambos protegidos por el
mismo `get_usuario_actual` que ya usa el resto del módulo:

- `GET /api/reportes/inventario-por-lote?inventario_id=` (opcional)
- `GET /api/reportes/proximos-vencer?inventario_id=` (opcional)

No se registró nada nuevo en `main.py`: el router de `m19_reportes` ya
estaba incluido (`app.include_router(m19_router)`), así que los
endpoints nuevos quedan disponibles automáticamente bajo el mismo
prefijo `/api/reportes`.

---

## 3. Riesgos encontrados

1. **No se pudo ejecutar ningún test en este entorno** (ver aviso al
   inicio de este documento). Es el riesgo principal: todo lo demás en
   esta lista se basa en revisión estática/manual, no en corridas
   reales.

2. **Definición de "cercano al mínimo" no estaba en el brief.** La
   sección 2 pide 3 niveles de stock pero sólo define con precisión
   ROJO (`≤ mínimo`) y VERDE (implícito, "normal"); AMARILLO
   ("cercano") quedó a criterio de esta implementación. Se usó un
   margen del 20% sobre el mínimo (`FACTOR_ALERTA_STOCK_CERCANO =
   1.2`), configurable en `config.py`. **Riesgo**: si el negocio
   esperaba otro margen (ej. 10%, o una cantidad fija en vez de
   porcentaje), sólo hay que cambiar esa constante — no hay lógica
   duplicada que corregir en varios lugares.

3. **`bajo_stock_minimo` (booleano ya existente) usa `<` estricto**,
   mientras que el semáforo nuevo (`ROJO`) usa `≤` porque el brief
   dice explícitamente "igual o menor al mínimo". Son dos campos
   distintos con semántica ligeramente distinta a propósito, para no
   alterar el comportamiento ya existente de `bajo_stock_minimo`
   (usado hoy por `m01_dashboard`). **Riesgo**: un producto con
   `stock_actual == stock_minimo` exacto aparecerá con
   `bajo_stock_minimo = false` pero `semaforo_stock = "ROJO"` —
   comportamiento esperado según el brief, pero puede sorprender si no
   se documenta (queda documentado en el código y aquí).

4. **Campo `proveedor` en "Inventario por lote" no siempre se puede
   completar.** Como no hay FK directa Lote→Proveedor en el modelo (y
   el brief no permite crear una), se reconstruye por coincidencia de
   texto (`codigo_lote` contra `OrdenCompraItem.lote`). Lotes creados
   sin pasar por una orden de compra con ese campo cargado (ingresos
   manuales desde el formulario, ajustes, etc.) quedarán con
   `proveedor: null`. Es el comportamiento correcto dado "si existe
   relación", pero conviene que negocio lo sepa antes de extrañar
   datos faltantes.

5. **`dias_restantes` se redondea hacia arriba (`ceil`)** para lotes
   vigentes (ej. 89 días y 3 horas se reporta como 90) y hacia abajo
   (`floor`) para vencidos, de forma que nunca se subestime cuánto
   falta ni se sobreestime cuánto tiempo lleva vencido. Es una
   decisión de redondeo razonable pero arbitraria; si negocio prefiere
   truncado simple, es un cambio de una línea en
   `calcular_semaforo_vencimiento()`.

6. **No se tocó `m03_inventario/repository.py`.** Se evaluó agregar
   ahí el cálculo de `semaforo_stock` pero se revirtió: ese archivo
   sigue el patrón de "solo acceso a datos" del proyecto (nunca llama
   a `service.py` de otro módulo), así que el cálculo del semáforo se
   dejó en `service.py`, que es donde ya vive `calcular_estado_lote`.
   Riesgo evitado, no incurrido: se documenta para que quede trazado
   que se consideró y por qué se descartó.

---

## 4. Resultado de todas las pruebas

**No ejecutado en este entorno** (sin acceso a red / paquetes). Ver
aviso al inicio del documento y sección 5.

Casos que el nuevo script `test_fase2_control_gerencial_perecibles.py`
cubre (pendiente de corrida real):

| Caso | Descripción | Resultado |
|---|---|---|
| 1 | Lote >90 días → semáforo VERDE | pendiente de ejecución |
| 2 | Lote 60 días → semáforo AMARILLO | pendiente de ejecución |
| 3 | Lote 15 días → semáforo ROJO | pendiente de ejecución |
| 4 | Lote vencido → semáforo NEGRO | pendiente de ejecución |
| 5 | Reporte inventario por lote: costo, cantidad, valor, estado | pendiente de ejecución |
| 6 | Reporte próximos a vencer: orden correcto | pendiente de ejecución |
| extra | Semáforo de stock (3 niveles) | pendiente de ejecución |
| extra | Regresión: FEFO, Kardex y costo unitario intactos | pendiente de ejecución |

---

## 5. Confirmación de que los tests de regresión continúan pasando

**No confirmado.** No se pudo correr ninguno de los 5 scripts de
regresión existentes en este entorno (`test_fase1_seguridad_
perecibles.py`, `test_costo_unitario_inventario_frontend.py`,
`test_costo_unitario_ventas_frontend.py`, `test_fase10_cierre_e2e.py`,
`test_flujo_guia.py`).

Lo que sí se verificó, por revisión manual del código:

- Ninguna función existente de Fase 1 (`calcular_estado_lote`,
  `registrar_ingreso`, `registrar_salida`, `registrar_ajuste`,
  validators) fue modificada — sólo se agregó código nuevo alrededor.
- `repository.saldos_por_inventario()` y `repository.
  inventario_valorizado()` (ambas ya existentes) no fueron tocadas: el
  campo `semaforo_stock` se agrega **después**, en la capa de
  `service.py`, sobre el diccionario ya armado.
- Los schemas ampliados (`SaldoProductoOut`, `ProductoValorizado`)
  sólo ganaron un campo nuevo con default — Pydantic no rompe por
  campos adicionales con default.

Esto reduce el riesgo de regresión pero **no reemplaza la corrida
real**. Antes de aprobar la fase, ejecutar los 6 comandos de la
sección "Aviso de trazabilidad" y confirmar salida `0` en todos.

---

## 6. Endpoints nuevos (referencia rápida)

Primera pasada:

```
GET /api/reportes/inventario-por-lote?inventario_id=<opcional>
GET /api/reportes/proximos-vencer?inventario_id=<opcional>
```

Segunda pasada (exportación, mismo patrón que ventas/compras/
inventario-valorizado/resumen-general):

```
GET /api/reportes/inventario-por-lote/exportar/excel?inventario_id=<opcional>
GET /api/reportes/inventario-por-lote/exportar/pdf?inventario_id=<opcional>
GET /api/reportes/proximos-vencer/exportar/excel?inventario_id=<opcional>
GET /api/reportes/proximos-vencer/exportar/pdf?inventario_id=<opcional>
```

Los 6 requieren autenticación (mismo esquema que el resto de
`/api/reportes/*`). Ninguno modifica datos: son 100% de lectura.

Campo nuevo en endpoints ya existentes (aditivo, no rompe consumidores
que ignoren campos desconocidos):

```
GET /api/inventario/saldos/{inventario_id}        -> + semaforo_stock
GET /api/reportes/inventario-valorizado            -> + semaforo_stock
```
