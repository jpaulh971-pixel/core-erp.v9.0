# Informe de Pruebas — Cierre Definitivo Fase 10 (Ventas Almacén)

Fecha: 2026-08-01
Continúa desde: `core_erp_fase10_cierre_ventas_almacen.zip` + auditoría técnica de esta sesión.

## Alcance de este cierre

Único cambio permitido y realizado: corrección de 3 líneas en
`backend/test_fase10_cierre_e2e.py` (el script de prueba, no el
sistema). No se tocó `m10_ventas` (backend ni frontend), no se
agregaron módulos, no se agregó lógica financiera.

### Corrección aplicada al script de prueba

- `s.stock_total` / `s.producto_id` → `s["stock_total"]` /
  `s["producto_id"]` (la función real `inventario_service.saldos()`
  devuelve `list[dict]`, no objetos).
- `inventario_service.listar_saldos(...)` (función que no existe en
  el backend) → `inventario_service.saldos(...)` (función real).

Se verificó por `diff -rq` contra el ZIP de entrada que **ningún otro
archivo cambió**: ni `backend/app/` (incluye `m10_ventas` completo),
ni `frontend_fase3_modulos/`.

## TERMINADO (verificado por ejecución real en este entorno)

1. **Backend compila sin errores**: `py_compile` sobre todo `app/` y
   los 4 scripts de prueba (`test_fase10_cierre_e2e.py`,
   `test_flujo_guia.py`, `test_costo_unitario_ventas_frontend.py`,
   `test_costo_unitario_inventario_frontend.py`) → **OK**.

2. **Test E2E de cierre corregido, ejecutado de punta a punta**:

   ```
   PREVISUALIZAR OK: 1 fila(s) valida(s), inventario intacto (100).
   CONFIRMAR OK: orden 1 estado DESPACHADA
   INVENTARIO OK: saldo 100 -> 80.0 (salida de 20, sin duplicar).
   KARDEX OK: 1 movimiento SALIDA nuevo, cantidad 20.000, lote 1 (FEFO automatico).
   REPORTE OK: por_producto incluye 'Producto E2E Cierre' con cantidad 20.0;
   total_ordenes=1, total_vendido=300.0.

   E2E CIERRE FASE 10 (VENTAS ALMACEN): TODO OK.
   ```

   Flujo verificado con datos reales (SQLite + dependencias reales
   instaladas, sin mocks): Excel → `previsualizar()` → `confirmar()`
   (crea → confirma → despacha la orden internamente) → salida real de
   Inventario vía FEFO → Kardex → `reportes_service.reporte_ventas()`.

3. **Los otros 3 scripts de prueba funcional incluidos en el proyecto
   pasan igual que antes** (no fueron tocados, se re-ejecutaron como
   control de regresión): `test_flujo_guia.py`,
   `test_costo_unitario_ventas_frontend.py`,
   `test_costo_unitario_inventario_frontend.py` → **TODO OK**.

4. **Frontend sin cambios**: `node --check` sobre `ventas.js`,
   `inventario.js`, `reportes.js`, `compras.js` → sintaxis OK. `diff`
   byte a byte contra el ZIP anterior confirma que
   `frontend_fase3_modulos/` es idéntico.

5. **Endpoints de Ventas**: se confirmó por inspección de código que
   las 4 rutas siguen registradas y montadas igual que antes:
   `/api/ventas/importar/previsualizar`,
   `/api/ventas/importar/confirmar`, `/api/inventario/inventarios`,
   `/api/reportes/ventas`. El test E2E ejercita directamente las
   funciones de servicio reales que estas rutas invocan
   (`importacion_service.previsualizar/confirmar`,
   `inventario_service.saldos`, `reportes_service.reporte_ventas`),
   por lo que el comportamiento de negocio queda verificado de punta a
   punta.

## PENDIENTE

- Prueba manual en navegador del modal de Importar Ventas (drag/drop),
  fuera del alcance de este entorno (no hay browser real disponible
  aquí).

## ERRORES

- Ninguno pendiente. El único error real detectado en la auditoría
  previa (bug de sintaxis en el script de prueba, no en el sistema)
  quedó corregido y verificado por ejecución.

## RIESGOS

- Asimetría de diseño, ya documentada e intencional: la importación de
  Compras es parcial (omite filas inválidas y continúa), la de Ventas
  es todo-o-nada (una fila inválida cancela toda la importación). No
  es un bug; queda anotado para que el criterio de aceptación de
  futuras fases lo tenga presente.

## Conclusión

Fase 10 — Cierre Ventas Almacén: **CERRADA**. Sistema listo para
iniciar la auditoría general del ERP.
