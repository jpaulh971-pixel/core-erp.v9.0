# Informe técnico — Auditoría funcional end-to-end (reconstruida)

**Fecha:** 2026-08-03
**Alcance:** verificación funcional end-to-end de los módulos que no habían
sido ejercitados con datos reales hasta ahora: m06 (Comercio Exterior),
m07 (Operación Logística), m12 (SUNAT), m13 (Inteligencia Comercial),
m14 (Inteligencia Tributaria), m15 (Lean Six Sigma), m16 (Theory of
Constraints), m18 (Balanced Scorecard); más regresión de Compras,
Inventario, Ventas, Dashboard, Costos e Importación Histórica.

## 0. Nota de trazabilidad

El informe de auditoría parcial (con el estado original de las
secciones A–G y el escenario "B8") que se mencionó al iniciar esta
fase no estaba disponible en ningún ZIP ni documento entregado en esta
sesión. Por instrucción explícita del cliente, esta auditoría se
**reconstruyó desde cero** para regenerar la evidencia técnica, sin
reiniciar ni descartar nada de lo ya integrado en el ERP (Kárdex
histórico, m21, correcciones de moneda/hojas de costo, etc., que se
mantienen intactos y no se tocaron).

Metodología: se ejecutó un escenario realista de punta a punta usando
los `service` reales del backend (mismo patrón que
`test_fase10_cierre_e2e.py` y `test_flujo_guia.py`: SQLite real,
sin mocks), cubriendo el flujo completo Compras → Inventario → Ventas
→ SUNAT → Comercio Exterior → Operación Logística → módulos de
inteligencia de solo lectura.

## 1. Estado final por sección

| Sección | Módulo(s) | Estado |
|---|---|---|
| A | Compras → Inventario (regresión) | 🟢 VERDE |
| B | Ventas → Despacho (regresión, incl. escenario B8) | 🟢 VERDE |
| C | Dashboard (m01) / Reportes (m19) / Costos (m08) (regresión) | 🟢 VERDE |
| — | m12 SUNAT, m06 Comercio Exterior, m07 Operación Logística | 🟢 VERDE |
| D | m13 Inteligencia Comercial + m14 Inteligencia Tributaria | 🟢 VERDE |
| E | m15 Lean Six Sigma | 🟢 VERDE |
| F | m16 Theory of Constraints | 🟢 VERDE |
| G | m18 Balanced Scorecard | 🟢 VERDE |

**Escenario B8** (venta que excede el stock disponible): se verificó
que el despacho se rechaza de forma controlada y que el inventario
**no queda con un descuento parcial** — comportamiento correcto.

## 2. Bugs funcionales reales encontrados y corregidos

Los 3 bugs siguientes se detectaron ejecutando los flujos reales (no
eran visibles por lectura de código ni habían sido ejercitados antes,
justamente porque estos módulos nunca se habían probado end-to-end).
En los 3 casos se aplicó el **cambio mínimo indispensable**,
reutilizando el mismo patrón ya usado en el resto del ERP.

### Bug 1 — m16 Theory of Constraints: `ordenes_en_espera` fallaba siempre que había una orden CONFIRMADA en cola

- **Síntoma:** `TypeError: can't subtract offset-naive and offset-aware datetimes`.
- **Causa raíz:** SQLite no conserva el `tzinfo` de una columna
  `DateTime(timezone=True)`: `confirmado_en` se guarda con
  `datetime.now(timezone.utc)` pero al leerlo de la base vuelve
  *offset-naive*. La función comparaba ese valor contra un `ahora`
  generado con tzinfo, y la resta fallaba.
- **Corrección:** normalizar ambos datetimes a naive UTC antes de
  restar (mismo criterio que ya usa `m15_lean_six_sigma._dias_entre`
  con datetimes leídos de la BD).
- **Archivo modificado:** `app/modules/m16_theory_of_constraints/service.py`.

### Bug 2 — m07 Operación Logística: la recepción directa (sin Orden de Compra) estaba rota por completo

- **Síntoma:** `ValidationError: inventario_id Field required` al
  intentar registrar cualquier recepción directa (importación sin OC
  formal).
- **Causa raíz:** el schema `RecepcionCrear` nunca exponía
  `inventario_id`, pero `m03_inventario.IngresoInventarioCrear` lo
  exige como obligatorio. La ruta de recepción directa nunca pudo
  haberse ejecutado con éxito en producción.
- **Corrección:** se agregó `inventario_id` (opcional a nivel de
  schema, validado como obligatorio en `service.py` solo cuando no hay
  `orden_compra_id`) y la columna correspondiente en el modelo
  `OperacionLogistica`, para trazabilidad de en qué inventario/almacén
  lógico ingresó el stock.
- **Archivos modificados:** `models.py`, `schemas.py`, `service.py`,
  `validators.py` de `app/modules/m07_operacion_logistica/`.

### Bug 3 — m06 Comercio Exterior: `embarcar_declaracion` fallaba siempre

- **Síntoma:** `ValidationError: inventario_id Field required` al
  intentar embarcar cualquier declaración de exportación.
- **Causa raíz:** mismo patrón que el Bug 2 — el módulo nunca
  registraba de qué inventario/almacén lógico salía la mercadería, pero
  `m03_inventario.SalidaInventarioCrear` lo exige. La transición
  CONFIRMADA → EMBARCADA nunca pudo completarse en producción.
- **Corrección:** se agregó `inventario_origen_id` como campo
  obligatorio en `DeclaracionCrear` (mismo patrón que
  `inventario_destino_id` en Compras e `inventario_salida_id` en
  Ventas) y la columna correspondiente en el modelo
  `DeclaracionExportacion`.
- **Archivos modificados:** `models.py`, `schemas.py`, `service.py` de
  `app/modules/m06_comercio_exterior/`.

## 3. Archivos modificados (lista exacta, verificada con `diff -rq` contra el ZIP recibido)

```
backend/app/modules/m06_comercio_exterior/models.py
backend/app/modules/m06_comercio_exterior/schemas.py
backend/app/modules/m06_comercio_exterior/service.py
backend/app/modules/m07_operacion_logistica/models.py
backend/app/modules/m07_operacion_logistica/schemas.py
backend/app/modules/m07_operacion_logistica/service.py
backend/app/modules/m07_operacion_logistica/validators.py
backend/app/modules/m16_theory_of_constraints/service.py
```

Ningún otro archivo del backend fue tocado. No se modificó
arquitectura, no se crearon módulos nuevos, no se rediseñó ningún
flujo existente.

## 4. Verificación de no regresión

Se re-ejecutó, sin modificar ni uno, todo el conjunto de pruebas ya
entregado en sesiones previas:

| Script | Resultado |
|---|---|
| `test_flujo_guia.py` | ✅ OK |
| `test_costo_unitario_ventas_frontend.py` | ✅ OK |
| `test_costo_unitario_inventario_frontend.py` | ✅ OK |
| `test_fase10_cierre_e2e.py` | ✅ OK |
| `test_fase1_seguridad_perecibles.py` | ✅ OK |
| `test_fase2_control_gerencial_perecibles.py` | ✅ OK |
| `test_fase3_inteligencia_inventario.py` | ✅ OK |
| `test_fase4c_reportes_gerenciales.py` | ✅ OK |

Adicionalmente:
- `python3 -m py_compile` sobre **todo** el backend: sin errores.
- La aplicación FastAPI completa carga sin errores (147 rutas).
- Compras, Inventario, Ventas, Dashboard, Costos e Importación
  Histórica quedan verificados sin cambios de comportamiento.

## 5. Nuevo script de auditoría entregado

`backend/test_auditoria_end_to_end_2026-08-03.py` — reproducible,
documenta cada sección (A-G + extra), incluye el escenario B8 y los 3
bugs con sus asserts de regresión. Se puede volver a correr en
cualquier momento con:

```bash
pip install -r requirements.txt --break-system-packages
python3 test_auditoria_end_to_end_2026-08-03.py
```

## 6. Pendientes explícitamente fuera de este cierre

No se tocaron (correctamente, por estar fuera del alcance autorizado
para esta fase, que era solo verificación + corrección de bugs
funcionales comprobados):

- Re-validación de importadores (m21) con los 3 Excel reales del
  cliente — sigue pendiente de una sesión con esos archivos
  disponibles.
- Trazabilidad campo por campo de Observaciones/Usuario (Fase 5 del
  informe de release candidate).
- Prueba manual en navegador del modal de Importar Ventas (drag/drop)
  — requiere entorno con browser.

## 7. Conclusión

Auditoría funcional end-to-end cerrada en estado **🟢 VERDE** en las 7
secciones (A-G) más los módulos extra (SUNAT, Comercio Exterior,
Operación Logística). Se encontraron y corrigieron 3 bugs funcionales
reales con el cambio mínimo indispensable, sin romper arquitectura ni
trazabilidad, y sin ninguna regresión detectada en el resto del ERP.
