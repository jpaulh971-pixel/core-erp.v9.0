# Reporte de Validación Funcional — Módulo m21_importacion_datos

## Aviso de entorno (leer primero)

Este entorno de ejecución **no tiene acceso a red** (proxy de egress
deniega todo tráfico, confirmado con `pip install` y `apt-get install`:
ambos devuelven `403 Forbidden` / "no matching distribution"). Las
dependencias del proyecto (`fastapi`, `sqlalchemy`, `pydantic`,
`python-jose`, `passlib`) **no están instaladas** y no se pudieron
instalar en esta sesión.

Resultado: **no fue posible levantar la aplicación real ni ejecutar los
8 casos con `TestClient` + SQLite como se pidió.** No se fabricó
ninguna salida de prueba simulada. Lo que sigue es una traza de código
línea por línea (no una ejecución) de cada caso, mas la validación
estática que sí se pudo ejecutar en este entorno.

## Lo que SÍ se ejecutó en este entorno

```
python -m py_compile $(find app -name "*.py")   -> OK, sin errores
```

Todo el backend (incluyendo m21, m03, m04, m10, m08, m17, m19, m01)
compila sin errores de sintaxis ni de imports a nivel de módulo.

## Traza de código por caso (sin ejecución real)

### CASO 1 — Importar y confirmar Inventario Inicial
`previsualizar()` lee el Excel y valida fila por fila sin tocar m02/m03.
`confirmar()` recorre `repository.filas_pendientes()` y por cada fila
llama a `_procesar_fila()`, que hace *get-or-create* de `Producto` (m02)
y llama a `inventario_service.registrar_ingreso()` (m03), el cual crea
`ProductoInventario` (si no existe) + `Lote` + `MovimientoKardex` con
`referencia="Carga inventario inicial #{id} (archivo ..., fila ...)"`.
Traza correcta: Producto → Lote → Kardex quedan enlazados y el patrón de
`referencia` es el que usa después el motor de reemplazo para
localizarlos.

### CASO 2 — Reemplazar Inventario Inicial
`verificar_reemplazo_inventario()` bloquea si hay movimientos de Kardex
posteriores sobre esos lotes o si el stock ya fue consumido.
`reemplazar_inventario()`: previsualiza el archivo nuevo FUERA de la
transacción (aborta sin tocar nada si hay errores); dentro de
`_transaccion_atomica()` localiza Kardex por patrón de referencia,
borra Kardex y Lotes propios de la carga vieja, confirma la carga
nueva, marca la carga vieja `estado_vigencia="REEMPLAZADA"` (nunca se
borra la fila de carga) y enlaza `carga_reemplazo_id`/`carga_original_id`,
y registra `BitacoraReemplazo`. Los lotes/Kardex "antiguos" no quedan
"desactivados" con un flag booleano (m03 no tiene esa columna y no se
tocó m03): quedan eliminados físicamente, mientras que la carga en sí
permanece como registro histórico marcado REEMPLAZADA.

### CASO 3 — Importar y confirmar Compras Históricas
`confirmar_compras()` → `_procesar_fila_compra()` crea proveedor
(get-or-create), `OrdenCompra` vía `compras_service`, y al recibir la
orden (`m04_compras.service.recibir_orden`) se genera Kardex con
`referencia="Recepcion orden de compra #{id}"`, prorrateando costos
adicionales de `m08_costos` si existen (landed cost). Traza correcta.

### CASO 4 — Reemplazar Compras
`verificar_reemplazo_compras()` bloquea si hay `CostoAdicional` u
`OperacionLogistica` sobre esas órdenes, o Kardex posterior. Si no hay
bloqueos, `reemplazar_compras()` borra Kardex/Lotes propios, desvincula
`orden_compra_id` en las filas y borra las `OrdenCompra` (cascada borra
sus items), confirma la carga nueva, marca la vieja REEMPLAZADA y
registra bitácora — todo dentro de la misma transacción atómica.

### CASO 5 — Importar y confirmar Ventas Históricas
`confirmar_ventas()` → `_procesar_fila_venta()` crea `OrdenVenta`, y al
despachar (`m10_ventas.service.despachar_orden`) descuenta stock real
vía FEFO (`m03_inventario.service.registrar_salida` →
`repository.lotes_disponibles_fefo`), generando Kardex con
`referencia="Despacho orden de venta #{id}"`.

### CASO 6 — Reemplazar Ventas
`verificar_reemplazo_ventas()` bloquea si hay `GuiaRemision` u
`OperacionLogistica` sobre esas órdenes de venta. `reemplazar_ventas()`
sigue el mismo patrón que compras. FEFO no se modifica en absoluto: la
nueva carga vuelve a llamar `despachar_orden`, que usa la misma función
`registrar_salida`/`lotes_disponibles_fefo` sin cambios.

### CASO 7 — Reemplazo bloqueado
`validators.validar_sin_bloqueos()` lanza `HTTPException 409` con
`detail = "No se puede reemplazar esta carga: [TIPO] detalle; ..."`,
concatenando cada bloqueo detectado (ESTADO, YA_REEMPLAZADA,
MOVIMIENTOS_POSTERIORES/DERIVADOS, STOCK_CONSUMIDO, COSTEO,
OPERACION_LOGISTICA, GUIA_REMISION). El endpoint `GET .../reemplazar/validar`
devuelve el mismo detalle estructurado en `bloqueos` sin lanzar excepción.
Un intento de reemplazo bloqueado también se registra en
`BitacoraReemplazo` con `resultado="BLOQUEADO"` (vía `_bitacora_error`).

### CASO 8 — Rollback ante error forzado
Todo el cuerpo de `reemplazar_*` posterior a la previsualización corre
dentro de `_transaccion_atomica()`, que reemplaza temporalmente
`db.commit` por `db.flush` y solo hace el `commit()` real al salir sin
excepción; ante cualquier excepción hace `db.rollback()` real antes de
relanzarla. Como ninguna función interna (`confirmar`, `confirmar_compras`,
`confirmar_ventas`, los deletes de Kardex/Lotes/Ordenes, `marcar_carga_*`,
el `add` de la bitácora) hace un `commit()` real mientras el parche está
activo, un rollback en cualquier punto deshace absolutamente todo lo
hecho desde el inicio del bloque — incluida la bitácora de éxito, que
nunca llega a persistir. El fallo se documenta aparte, en su propia
transacción, vía `_bitacora_error(..., resultado="ERROR", ...)`.
**Este comportamiento está verificado por diseño (lectura de código),
no por ejecución real en este entorno** — ver aviso arriba.

## Conclusión

No se detectaron errores de código durante esta revisión. La lógica de
los 8 casos es consistente con el diseño de la Etapa 3 tal como está
escrita. Lo que falta, y que esta sesión no pudo hacer por falta de
red, es la ejecución real de estos 8 casos con `TestClient` sobre
SQLite para confirmar el comportamiento en tiempo de ejecución
(por ejemplo, errores de tipos, de sesión de SQLAlchemy, o de
serialización Pydantic que solo aparecen al correr, no al compilar).
Se recomienda ejecutar ese flujo en un entorno con acceso a red o con
las dependencias preinstaladas.
