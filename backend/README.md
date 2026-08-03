# Core ERP — Almacén de Exportación

Proyecto **nuevo**, construido desde cero según la especificación: un solo
almacén central, un único usuario Administrador, sin sucursales, sin
tiendas, sin permisos por sucursal. El proyecto anterior de Panadería
(`core_erp_avance_fase1`) **no fue reutilizado** en ningún archivo; solo se
usó como referencia visual/estructural.

## Estado actual (nota de actualización — Fase de despliegue a producción)

> Lo que sigue debajo de esta nota es el **registro histórico** de cómo
> se construyó el proyecto, fase a fase, y quedó desactualizado en dos
> puntos concretos que conviene aclarar antes de publicar el repo:
>
> - El sistema **ya tiene los 24 módulos implementados**, incluyendo
>   `m07_operacion_logistica` (Operación Logística) y
>   `m06_comercio_exterior` (Comercio Exterior), que el historial de
>   abajo describía como "fuera de alcance" en una iteración anterior.
>   Se agregaron `m17_guias_remision`, `m21_importacion_datos`,
>   `m22_inteligencia_inventario`, `m23_dashboard_inventario` y
>   `m24_reportes_gerenciales_inventario` en fases posteriores a las
>   que documenta este README.
> - La contraseña de ejemplo del usuario admin en la sección "Cómo
>   correrlo" está desactualizada (ver corrección más abajo).
>
> Se conserva el historial completo debajo porque documenta decisiones
> de diseño reales (FEFO, máquinas de estado, "no duplicar lógica",
> etc.) que siguen vigentes.

### Fase 1 — Arquitectura completa (LISTA)
Los 20 módulos existen como estructura, cada uno con:
`__init__.py`, `models.py`, `schemas.py`, `service.py`, `router.py`,
`repository.py`, `validators.py`, `templates/`, `static/`.

```
01 Dashboard Ejecutivo          → m01_dashboard          ✅ implementado
02 Productos                    → m02_productos          ✅ implementado
03 Inventario                   → m03_inventario          ✅ implementado
04 Compras                      → m04_compras             ✅ implementado
05 Proveedores                  → m05_proveedores         ✅ implementado
06 Comercio Exterior            → m06_comercio_exterior   ✅ implementado (fuera de alcance real, ver nota)
07 Operación Logística          → m07_operacion_logistica ⛔ fuera de alcance (no se implementa)
08 Costos                       → m08_costos             ✅ implementado
09 Moneda                       → m09_moneda             ✅ implementado
10 Ventas                       → m10_ventas              ✅ implementado (cliente_id FK real)
11 Clientes                     → m11_clientes            ✅ implementado
12 SUNAT                        → m12_sunat               ✅ implementado
13 Inteligencia Comercial       → m13_inteligencia_comercial ✅ implementado
14 Inteligencia Tributaria      → m14_inteligencia_tributaria ✅ implementado
15 Lean Six Sigma               → m15_lean_six_sigma      ✅ implementado
16 Theory of Constraints        → m16_theory_of_constraints ✅ implementado
17 Balanced Scorecard           → m18_balanced_scorecard  ✅ implementado
18 Reportes                     → m19_reportes
19 Configuración                → m20_configuracion       ✅ implementado (usuario único + login)
```

> **Aclaración de alcance (negocio real: sin exportación, clientes
> internos):** el módulo 06 Comercio Exterior quedó implementado desde
> una iteración anterior con el supuesto de exportación, pero el negocio
> real no exporta — todos los clientes son domésticos. Comercio Exterior
> se deja tal cual (no se elimina código funcional sin pedido explícito),
> pero el flujo real de venta es exclusivamente el del módulo 10 Ventas,
> ya migrado a `cliente_id` (FK a Clientes). Operación Logística (07) se
> omite del todo por pedido explícito: no se implementa su lógica.

> Monte Carlo fue retirado del alcance a pedido explícito (carpeta `m17_monte_carlo`
> eliminada, sin referencias en `main.py`).

Los módulos sin ✅ están en fase de arquitectura: su `router.py` expone
`GET /api/<modulo>/status` para confirmar que están montados en `main.py`,
pero no tienen lógica de negocio todavía.

### Fase 2 — Implementación módulo por módulo (EN CURSO)
Siguiendo el orden (Arquitectura → Inventario → **Compras** → …), ya se
implementó:

- **20 Configuración**: usuario único Administrador (tabla `usuarios`),
  login JWT (`POST /api/auth/login`), parámetros del sistema.
- **02 Productos**: catálogo base (CRUD), requerido como base para
  Inventario.
- **03 Inventario**: almacén central único (se autocrea), lotes,
  ingreso de stock, salida de stock por **FEFO** (vencimiento más próximo
  primero, luego más antiguo, en una sola transacción atómica), ajustes
  con validación de stock negativo, kardex de movimientos, saldos por
  producto con alerta de stock mínimo.
- **05 Proveedores**: catálogo base (CRUD), requerido como base para
  Compras — mismo criterio que Productos para Inventario.
- **04 Compras**: orden de compra con máquina de estados
  `SOLICITADA → APROBADA → RECIBIDA` (o `CANCELADA` desde SOLICITADA/APROBADA).
  **Al recibir una orden, se dispara automáticamente un ingreso real de
  inventario por cada item** (nuevo lote + movimiento de kardex),
  reutilizando el servicio de Inventario sin duplicar lógica.
- **06 Comercio Exterior**: declaración de exportación (tipo DUA) con
  máquina de estados `BORRADOR → CONFIRMADA → EMBARCADA` (o `CANCELADA`
  desde BORRADOR/CONFIRMADA). **Al embarcar, se dispara automáticamente
  una salida real de inventario por FEFO por cada item**, reutilizando el
  servicio de Inventario. Si el stock no alcanza, la declaración se queda
  en `CONFIRMADA` para corregir antes de reintentar, no queda a medio
  embarcar.
  > Decisión de diseño explícita: el cliente/importador se modela como
  > campos simples (`cliente_nombre`, `pais_destino`, `incoterm`) en vez
  > de una FK a una tabla `clientes`, porque el módulo 11 Clientes aún
  > no existe. Cuando se implemente, se migra a FK sin romper el flujo.

- **08 Costos**: no duplica el costo real (ese ya vive en el kardex de
  Inventario, registrado lote a lote en cada salida FEFO). Este módulo
  solo agrega los **costos adicionales** que no viven en Inventario ni en
  Compras (flete, seguro, aduana, almacenaje, manipuleo, otro), asociados
  a una orden de compra o a una declaración de exportación. Con eso arma:
  - **Costeo de compra (landed cost)**: valor de mercadería (de los items
    de la orden) + costos adicionales prorrateados → costo unitario
    ponderado real.
  - **Rentabilidad de exportación**: ingreso de exportación vs. costo
    real de lo que efectivamente salió del almacén (leído directo del
    kardex por la referencia de embarque, no recalculado) menos los
    costos adicionales de esa exportación → utilidad bruta y margen %.

- **09 Moneda**: registro de **tipos de cambio** por par de monedas y
  fecha (`moneda_origen → moneda_destino`, valor = unidades de destino
  por 1 de origen). Expone:
  - Registrar/actualizar tipo de cambio de un par en una fecha dada
    (si ya existe ese par+fecha, lo actualiza en vez de duplicar).
  - **Tipo de cambio vigente**: para una fecha, busca el registro más
    reciente con `fecha <= solicitada`; si no existe el par directo pero
    sí el inverso, lo calcula como `1/valor` (marcando `invertido=true`).
  - **Conversión** de un monto entre dos monedas usando el vigente de
    esa fecha.
  - Es un módulo de soporte: no reescribe montos de otros módulos
    (Costos, Compras, Comercio Exterior siguen guardando su monto en la
    moneda original); si más adelante necesitan expresar un monto en
    otra divisa, consultan aquí el tipo de cambio vigente. No se tocó
    ningún otro módulo para esta implementación.

- **10 Ventas**: circuito de **venta local**, en paralelo al de
  exportación (mismo patrón que Comercio Exterior, pero para el mercado
  interno). Orden de venta con máquina de estados
  `BORRADOR → CONFIRMADA → DESPACHADA` (o `CANCELADA` desde
  BORRADOR/CONFIRMADA). **Al despachar, se dispara automáticamente una
  salida real de inventario por FEFO por cada item**, reutilizando el
  mismo servicio de Inventario que usan Compras y Comercio Exterior —
  sin duplicar lógica. Si el stock no alcanza, la orden se queda en
  `CONFIRMADA` para corregir antes de reintentar, no queda a medio
  despachar.
  > Decisión de diseño explícita (mismo criterio que en el módulo 06): el
  > cliente se modela como campo simple (`cliente_nombre`) en vez de una
  > FK a `clientes`, porque el módulo 11 aún no existe. Cuando se
  > implemente, se migra a FK sin romper el flujo.

- **11 Clientes**: catálogo mínimo (CRUD), mismo criterio estructural que
  Proveedores (módulo 05) para Compras: RUC único, razón social,
  contacto, teléfono, email, país, activo/inactivo.
  > Por ahora es un catálogo independiente: Ventas (módulo 10) y
  > Comercio Exterior (módulo 06) siguen usando su propio campo simple
  > `cliente_nombre`. Migrar esos dos módulos para que referencien esta
  > tabla por FK es un paso explícito aparte — no se tocó ningún módulo
  > ya implementado en esta iteración, tal como se especificó.

- **10 Ventas — migrado a `cliente_id`**: reemplacé el campo simple
  `cliente_nombre` por una FK real (`cliente_id → clientes.id`), ahora
  que el módulo 11 Clientes existe. Al crear una orden se valida que el
  cliente exista **y** esté activo (reutilizando `m11_clientes.service`,
  sin duplicar lógica). `OrdenVentaOut` expone `cliente_id` y
  `cliente_razon_social` (vía `joinedload` + propiedad de conveniencia en
  el modelo). Comercio Exterior (módulo 06) no se tocó: el negocio real
  no exporta, así que ese módulo queda como está, sin más desarrollo.
- **Operación Logística (07): omitida por pedido explícito.** No se
  implementa su lógica de negocio; queda solo como arquitectura
  (`GET /api/operacion-logistica/status`).

- **12 SUNAT**: emisión de comprobantes electrónicos (Factura/Boleta)
  para las órdenes de venta ya **DESPACHADAS** (mercadería físicamente
  entregada). No duplica montos: el subtotal se calcula directo de los
  items de la orden de venta (mismo criterio de "no recalcular" que
  Costos aplica sobre el kardex). Solo agrega lo propio de SUNAT:
  - **Tipo de comprobante**: FACTURA (requiere RUC válido de 11 dígitos)
    o BOLETA (RUC u DNI de 8 dígitos), validado contra el documento real
    del cliente.
  - **Serie y correlativo automáticos**: F001 para facturas, B001 para
    boletas, correlativo autoincremental por serie.
  - **IGV** calculado al 18% sobre el subtotal → total.
  - Snapshot del cliente (RUC, razón social) al momento de emitir, para
    que el comprobante no cambie si el cliente edita sus datos después.
  - Una orden de venta solo puede tener **un** comprobante (409 si se
    intenta duplicar).
  - Ciclo de vida: `EMITIDO → ACEPTADO/RECHAZADO` (simulado — no hay
    integración real con la API de SUNAT, fuera de alcance de este ERP)
    y `EMITIDO/ACEPTADO → ANULADO` con motivo obligatorio.

- **01 Dashboard Ejecutivo**: panel de solo lectura (`GET
  /api/dashboard/resumen`) que consolida en un único llamado los KPIs de
  Inventario, Ventas y Costos, tal como se sugirió. No agrega ninguna
  tabla propia ni recalcula reglas de negocio: son queries de agregación
  sobre datos ya persistidos por esos módulos (mismo criterio de "no
  duplicar lógica" que ya aplican Compras/Ventas al reutilizar el
  servicio de Inventario).
  - **Inventario**: total de productos activos, valor total del
    inventario (`cantidad_actual × costo_unitario` de todos los lotes),
    cantidad de productos bajo su stock mínimo y el detalle de esas
    alertas (reutiliza `inventario_service.saldos`, sin reimplementarlo).
  - **Ventas**: cantidad de órdenes por estado (`BORRADOR`, `CONFIRMADA`,
    `DESPACHADA`, `CANCELADA`) y total vendido de las órdenes ya
    `DESPACHADA` (venta efectivamente concretada).
  - **Costos**: total de costos adicionales registrados y su desglose
    por tipo (FLETE, SEGURO, ADUANA, ALMACENAJE, MANIPULEO, OTRO).

- **13 Inteligencia Comercial**: analítica de solo lectura sobre Ventas,
  Clientes, Productos e Inventario ya implementados — no agrega tablas
  propias ni recalcula reglas de negocio de esos módulos.
  - **Productos más vendidos** (`GET
    /api/inteligencia-comercial/productos-mas-vendidos`): ranking por
    cantidad y monto vendido, de órdenes ya `DESPACHADA`, con filtro
    opcional por rango de fecha de despacho.
  - **Clientes top** (`GET /api/inteligencia-comercial/clientes-top`):
    ranking de clientes por monto comprado y cantidad de órdenes, mismo
    filtro de fechas.
  - **Rotación de inventario** (`GET
    /api/inteligencia-comercial/rotacion-inventario`): por producto,
    índice de rotación (unidades vendidas históricas / stock actual,
    reutilizando `inventario_service.saldos` sin duplicarlo) y una
    bandera `sin_movimiento` para detectar stock inmovilizado (productos
    con stock pero cero ventas despachadas).

- **14 Inteligencia Tributaria**: reportes de solo lectura sobre los
  comprobantes electrónicos ya emitidos por SUNAT (módulo 12) — no
  agrega tablas propias ni redefine ninguna regla de emisión,
  serie/correlativo o transición de estado (esas siguen viviendo
  únicamente en `m12_sunat`).
  - **Resumen de IGV** (`GET /api/inteligencia-tributaria/resumen-igv`):
    subtotal, IGV y total agregados por tipo de comprobante (FACTURA/
    BOLETA), con filtro opcional por rango de fecha de emisión. Solo
    considera comprobantes vigentes (`EMITIDO`/`ACEPTADO`); un
    `ANULADO` no genera obligación de IGV.
  - **Registro/libro de ventas** (`GET
    /api/inteligencia-tributaria/libro-ventas`): listado de todos los
    comprobantes del período (cualquier estado), ordenados por
    serie-correlativo, con RUC/razón social del cliente y montos —
    mismo criterio que exige SUNAT para el registro de ventas e
    ingresos.
  - **Comprobantes anulados** (`GET
    /api/inteligencia-tributaria/comprobantes-anulados`): control y
    auditoría de anulaciones, con motivo y fecha.

- **15 Lean Six Sigma**: métricas de solo lectura sobre Inventario
  (kardex), Compras y Ventas ya implementados — no agrega tablas propias
  ni redefine FEFO, máquinas de estado ni ninguna otra regla de esos
  módulos; solo mide lo que ya quedó registrado.
  - **Mermas de inventario** (`GET /api/lean-six-sigma/mermas`): total y
    detalle por producto de los ajustes negativos de kardex (defectos),
    con **DPMO** (defectos por millón de oportunidades, oportunidades =
    total de movimientos de kardex del período) y el **nivel sigma**
    equivalente (aproximación de Bothe, la misma que usan las tablas
    estándar de Six Sigma: 3.4 DPMO ≈ 6σ, 66 807 DPMO ≈ 3σ, etc.).
  - **Tiempos de ciclo de Compras** (`GET
    /api/lean-six-sigma/tiempos-ciclo/compras`): días promedio
    solicitud→aprobación, aprobación→recepción y total, sobre órdenes ya
    `RECIBIDA`.
  - **Tiempos de ciclo de Ventas** (`GET
    /api/lean-six-sigma/tiempos-ciclo/ventas`): días promedio
    confirmación→despacho, sobre órdenes ya `DESPACHADA`.
  - Todos aceptan filtro opcional `desde`/`hasta`.

- **16 Theory of Constraints**: identifica la restricción (cuello de
  botella) del flujo Compras → Inventario → Ventas y arma la
  contabilidad de throughput, todo de solo lectura sobre Ventas,
  Inventario y Costos ya implementados — no agrega tablas propias ni
  redefine FEFO, máquinas de estado ni ninguna otra regla de esos
  módulos.
  - **Restricciones de stock** (`GET
    /api/theory-of-constraints/restricciones-stock`): por producto,
    compara la demanda ya confirmada (órdenes `CONFIRMADA`, aún sin
    despachar) contra el stock disponible; un `deficit` positivo marca
    ese producto como la restricción real que impide despachar la
    demanda ya comprometida.
  - **Órdenes en espera** (`GET
    /api/theory-of-constraints/ordenes-en-espera`): la cola de órdenes
    `CONFIRMADA` que todavía no se pudo despachar, con días esperando —
    el trabajo acumulado frente a la restricción.
  - **Contabilidad de throughput** (`GET
    /api/theory-of-constraints/contabilidad-throughput`): T (ingreso de
    ventas despachadas − costo real de mercadería vendida, leído del
    kardex), OE (costos adicionales del módulo 08), utilidad neta TOC
    (T − OE) e inversión en inventario (reutiliza la valorización de
    `m01_dashboard`), con retorno % sobre esa inversión. Acepta filtro
    opcional `desde`/`hasta`.

- **18 Balanced Scorecard**: tablero de solo lectura sobre Ventas,
  Clientes, Proveedores, Productos, Costos, Inventario, Lean Six Sigma
  (15) e Inteligencia Comercial (13) ya implementados — no agrega
  tablas propias ni recalcula ninguna regla de negocio de esos módulos;
  cada perspectiva reutiliza directo el servicio que ya la calcula.
  - **Financiera** (`GET /api/balanced-scorecard/financiera`): reutiliza
    la contabilidad de throughput de Theory of Constraints (16) —
    ingreso de ventas despachadas, costo de mercadería vendida, costos
    adicionales y utilidad neta — y agrega el margen neto %.
  - **Clientes** (`GET /api/balanced-scorecard/clientes`): clientes
    activos vs. clientes que efectivamente compraron en el período
    (cobertura de cartera), ticket promedio de venta y concentración de
    ingresos en el top 3 de clientes (reutiliza el ranking de
    Inteligencia Comercial, 13) — mide dependencia de pocos clientes.
  - **Procesos internos** (`GET
    /api/balanced-scorecard/procesos-internos`): DPMO y nivel sigma de
    mermas, tiempos de ciclo de Compras y Ventas (reutiliza Lean Six
    Sigma, 15) y cantidad de productos en restricción de stock
    (reutiliza Theory of Constraints, 16).
  - **Aprendizaje y crecimiento** (`GET
    /api/balanced-scorecard/aprendizaje-crecimiento`): adaptada — este
    ERP no tiene módulo de Recursos Humanos, así que se mide con lo que
    existe: amplitud de catálogo activo (Productos), diversificación de
    abastecimiento (Proveedores activos) y catálogo subutilizado
    (productos con stock pero cero ventas despachadas, reutiliza la
    rotación de inventario de Inteligencia Comercial, 13). No se
    inventan datos de capacitación ni de personal.
  - **Tablero consolidado** (`GET /api/balanced-scorecard/tablero`):
    las 4 perspectivas en un único llamado. Todos los endpoints con
    período aceptan filtro opcional `desde`/`hasta`, excepto Aprendizaje
    y Crecimiento, que es una foto del estado actual del catálogo.

Próximo paso sugerido: **19 Reportes** (el único módulo que queda).
Dime "Continúa" y sigo con ese.

## Cómo correrlo

Este entorno de generación no tiene acceso a red, así que no pude instalar
dependencias ni levantar el servidor aquí — sí verifiqué que **todos los
archivos `.py` compilan sin errores de sintaxis** (`python -m py_compile`).
Corre esto en tu máquina:

```bash
pip install -r requirements.txt
cp .env.example .env     # completar SECRET_KEY (obligatoria) y, opcionalmente, ADMIN_PASSWORD
python3 seed.py          # crea admin/<ADMIN_PASSWORD o "Admin123*" por defecto>, almacén central, producto demo
uvicorn app.main:app --reload
# docs interactivas: http://127.0.0.1:8000/docs
```

> La contraseña por defecto del usuario `admin` (si no se define
> `ADMIN_PASSWORD`) es **`Admin123*`**, no `admin123`. Ver
> `backend/.env.example`.

## Despliegue en producción (Render)

Este repo incluye:
- `render.yaml` (raíz del repo): blueprint de Render con Build/Start
  Command, variable de entorno de base de datos y un Persistent Disk
  para SQLite ya definidos.
- `backend/Procfile`: alternativa manual si no se usa el blueprint
  (`web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
- `backend/.env.example`: variables de entorno requeridas/recomendadas.
- `.gitignore` (raíz del repo): excluye `__pycache__/`, `*.db`, `.env`,
  logs y carpetas de backups/evidencias de las sesiones de auditoría.

Antes de publicar:
1. Definir `SECRET_KEY` y `ADMIN_PASSWORD` como variables de entorno
   reales en Render (no usar los valores de ejemplo).
2. Confirmar la estrategia de persistencia: el Persistent Disk de
   `render.yaml` sirve para mantener SQLite entre despliegues, pero
   para producción con más de un usuario concurrente se recomienda
   migrar `DATABASE_URL` a Postgres gestionado de Render.
3. Definir `CORS_ORIGINS` (variable de entorno, ver `backend/.env.example`)
   con el/los dominio(s) reales donde se sirve el Frontend, separados por
   coma. El backend nunca usa `allow_origins=["*"]`; sin `CORS_ORIGINS`
   definida solo acepta llamadas desde `localhost`/`127.0.0.1`.

### Flujo de prueba sugerido (Inventario)

```bash
# 1. Login
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 2. Ingreso de stock (usa el token del paso anterior)
curl -X POST http://127.0.0.1:8000/api/inventario/ingresos \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"producto_id":1,"codigo_lote":"L001","cantidad":500,"costo_unitario":2.5}'

# 3. Saldos
curl http://127.0.0.1:8000/api/inventario/saldos -H "Authorization: Bearer <TOKEN>"
```

### Flujo de prueba sugerido (Compras)

```bash
# 1. Crear orden de compra (proveedor_id=1 y producto_id=1 vienen del seed)
curl -X POST http://127.0.0.1:8000/api/compras \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"proveedor_id":1,"items":[{"producto_id":1,"cantidad":200,"costo_unitario":3.1}]}'

# 2. Aprobar
curl -X POST http://127.0.0.1:8000/api/compras/1/aprobar -H "Authorization: Bearer <TOKEN>"

# 3. Recibir (esto genera el ingreso de inventario automaticamente)
curl -X POST http://127.0.0.1:8000/api/compras/1/recibir -H "Authorization: Bearer <TOKEN>"

# 4. Confirmar que el stock subio
curl http://127.0.0.1:8000/api/inventario/saldos -H "Authorization: Bearer <TOKEN>"
```

### Flujo de prueba sugerido (Comercio Exterior)

```bash
# 1. Crear declaracion de exportacion (producto_id=1 ya debe tener stock,
#    por ejemplo despues de recibir la compra de arriba)
curl -X POST http://127.0.0.1:8000/api/comercio-exterior/declaraciones \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"cliente_nombre":"Importadora Demo GmbH","pais_destino":"Alemania","incoterm":"FOB","items":[{"producto_id":1,"cantidad":150,"precio_unitario_exportacion":5.8}]}'

# 2. Confirmar
curl -X POST http://127.0.0.1:8000/api/comercio-exterior/declaraciones/1/confirmar -H "Authorization: Bearer <TOKEN>"

# 3. Embarcar (esto descuenta stock real via FEFO)
curl -X POST http://127.0.0.1:8000/api/comercio-exterior/declaraciones/1/embarcar -H "Authorization: Bearer <TOKEN>"

# 4. Confirmar que el stock bajo
curl http://127.0.0.1:8000/api/inventario/saldos -H "Authorization: Bearer <TOKEN>"
```

### Flujo de prueba sugerido (Costos)

```bash
# 1. Costeo de compra (usa la orden recibida en el flujo de Compras de arriba)
curl -X POST http://127.0.0.1:8000/api/costos/adicionales \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"tipo_documento":"COMPRA","documento_id":1,"tipo_costo":"FLETE","monto":45.0}'

curl http://127.0.0.1:8000/api/costos/compras/1/costeo -H "Authorization: Bearer <TOKEN>"

# 2. Rentabilidad de exportacion (usa la declaracion embarcada de arriba)
curl -X POST http://127.0.0.1:8000/api/costos/adicionales \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"tipo_documento":"EXPORTACION","documento_id":1,"tipo_costo":"ADUANA","monto":20.0}'

curl http://127.0.0.1:8000/api/costos/exportaciones/1/rentabilidad -H "Authorization: Bearer <TOKEN>"
```

### Flujo de prueba sugerido (Moneda)

```bash
# 1. Registrar tipo de cambio USD -> PEN para una fecha
curl -X POST http://127.0.0.1:8000/api/moneda/tipos-cambio \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"moneda_origen":"USD","moneda_destino":"PEN","fecha":"2026-07-22","valor":3.75}'

# 2. Consultar el vigente (usa el mas reciente <= fecha pedida)
curl "http://127.0.0.1:8000/api/moneda/tipos-cambio/USD/PEN/vigente?fecha=2026-07-22" \
  -H "Authorization: Bearer <TOKEN>"

# 3. Convertir un monto (ej. costo de flete en USD a PEN)
curl "http://127.0.0.1:8000/api/moneda/convertir?monto=45&moneda_origen=USD&moneda_destino=PEN&fecha=2026-07-22" \
  -H "Authorization: Bearer <TOKEN>"

# 4. El par inverso funciona sin registrarlo aparte (PEN -> USD = 1/3.75)
curl "http://127.0.0.1:8000/api/moneda/tipos-cambio/PEN/USD/vigente?fecha=2026-07-22" \
  -H "Authorization: Bearer <TOKEN>"
```

### Flujo de prueba sugerido (Clientes)

```bash
# 1. Crear cliente
curl -X POST http://127.0.0.1:8000/api/clientes \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"ruc":"20123456789","razon_social":"Bodega San Martin SAC","pais":"Peru"}'

# 2. Listar clientes activos
curl http://127.0.0.1:8000/api/clientes -H "Authorization: Bearer <TOKEN>"

# 3. Actualizar datos de contacto
curl -X PATCH http://127.0.0.1:8000/api/clientes/1 \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"contacto":"Maria Torres","telefono":"+51 999 111 222"}'
```

### Flujo de prueba sugerido (Ventas)

```bash
# 1. Crear orden de venta (producto_id=1 ya debe tener stock, cliente_id=1 del flujo de arriba)
curl -X POST http://127.0.0.1:8000/api/ventas \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"cliente_id":1,"items":[{"producto_id":1,"cantidad":30,"precio_unitario_venta":6.5}]}'

# 2. Confirmar
curl -X POST http://127.0.0.1:8000/api/ventas/1/confirmar -H "Authorization: Bearer <TOKEN>"

# 3. Despachar (esto descuenta stock real via FEFO)
curl -X POST http://127.0.0.1:8000/api/ventas/1/despachar -H "Authorization: Bearer <TOKEN>"

# 4. Confirmar que el stock bajo
curl http://127.0.0.1:8000/api/inventario/saldos -H "Authorization: Bearer <TOKEN>"
```

### Flujo de prueba sugerido (SUNAT)

```bash
# 1. Emitir factura para una orden de venta ya DESPACHADA (cliente con RUC de 11 digitos)
curl -X POST http://127.0.0.1:8000/api/sunat/comprobantes \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"orden_venta_id":1,"tipo_comprobante":"FACTURA"}'

# 2. Consultar el comprobante de esa orden
curl http://127.0.0.1:8000/api/sunat/ordenes/1/comprobante -H "Authorization: Bearer <TOKEN>"

# 3. Listar todos los comprobantes emitidos
curl http://127.0.0.1:8000/api/sunat/comprobantes -H "Authorization: Bearer <TOKEN>"

# 4. Anular (requiere motivo)
curl -X POST http://127.0.0.1:8000/api/sunat/comprobantes/1/anular \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"motivo":"Error en cantidad facturada"}'
```

### Flujo de prueba sugerido (Dashboard)

```bash
# Panel unico: KPIs de Inventario + Ventas + Costos en un solo llamado
curl http://127.0.0.1:8000/api/dashboard/resumen -H "Authorization: Bearer <TOKEN>"
```

### Flujo de prueba sugerido (Inteligencia Comercial)

```bash
# Top 5 productos mas vendidos (ordenes ya despachadas)
curl "http://127.0.0.1:8000/api/inteligencia-comercial/productos-mas-vendidos?limit=5" \
  -H "Authorization: Bearer <TOKEN>"

# Top clientes por monto comprado, filtrado por fecha de despacho
curl "http://127.0.0.1:8000/api/inteligencia-comercial/clientes-top?desde=2026-01-01&hasta=2026-12-31" \
  -H "Authorization: Bearer <TOKEN>"

# Indice de rotacion de inventario (detecta stock sin movimiento)
curl http://127.0.0.1:8000/api/inteligencia-comercial/rotacion-inventario \
  -H "Authorization: Bearer <TOKEN>"
```

### Flujo de prueba sugerido (Inteligencia Tributaria)

```bash
# Resumen de IGV por tipo de comprobante (para declarar)
curl "http://127.0.0.1:8000/api/inteligencia-tributaria/resumen-igv?desde=2026-01-01&hasta=2026-12-31" \
  -H "Authorization: Bearer <TOKEN>"

# Registro de ventas (libro de ventas) del periodo
curl "http://127.0.0.1:8000/api/inteligencia-tributaria/libro-ventas?desde=2026-01-01&hasta=2026-12-31" \
  -H "Authorization: Bearer <TOKEN>"

# Comprobantes anulados (auditoria)
curl http://127.0.0.1:8000/api/inteligencia-tributaria/comprobantes-anulados \
  -H "Authorization: Bearer <TOKEN>"
```

### Flujo de prueba sugerido (Lean Six Sigma)

```bash
# Mermas de inventario: DPMO y nivel sigma
curl http://127.0.0.1:8000/api/lean-six-sigma/mermas -H "Authorization: Bearer <TOKEN>"

# Tiempos de ciclo de Compras (solicitud -> aprobacion -> recepcion)
curl http://127.0.0.1:8000/api/lean-six-sigma/tiempos-ciclo/compras -H "Authorization: Bearer <TOKEN>"

# Tiempos de ciclo de Ventas (confirmacion -> despacho)
curl http://127.0.0.1:8000/api/lean-six-sigma/tiempos-ciclo/ventas -H "Authorization: Bearer <TOKEN>"
```

### Flujo de prueba sugerido (Theory of Constraints)

```bash
# Productos donde el stock es la restriccion real (deficit > 0)
curl http://127.0.0.1:8000/api/theory-of-constraints/restricciones-stock -H "Authorization: Bearer <TOKEN>"

# Cola de ordenes confirmadas esperando poder despacharse
curl http://127.0.0.1:8000/api/theory-of-constraints/ordenes-en-espera -H "Authorization: Bearer <TOKEN>"

# Contabilidad de throughput (T, OE, utilidad neta TOC)
curl http://127.0.0.1:8000/api/theory-of-constraints/contabilidad-throughput -H "Authorization: Bearer <TOKEN>"
```

### Flujo de prueba sugerido (Balanced Scorecard)

```bash
# Perspectiva financiera (ingreso, costo, utilidad neta, margen %)
curl http://127.0.0.1:8000/api/balanced-scorecard/financiera -H "Authorization: Bearer <TOKEN>"

# Perspectiva clientes (cobertura, ticket promedio, concentracion top 3)
curl http://127.0.0.1:8000/api/balanced-scorecard/clientes -H "Authorization: Bearer <TOKEN>"

# Perspectiva procesos internos (DPMO, nivel sigma, tiempos de ciclo)
curl http://127.0.0.1:8000/api/balanced-scorecard/procesos-internos -H "Authorization: Bearer <TOKEN>"

# Perspectiva aprendizaje y crecimiento (catalogo, proveedores, stock sin movimiento)
curl http://127.0.0.1:8000/api/balanced-scorecard/aprendizaje-crecimiento -H "Authorization: Bearer <TOKEN>"

# Tablero consolidado (las 4 perspectivas en un solo llamado, con filtro opcional de fechas)
curl "http://127.0.0.1:8000/api/balanced-scorecard/tablero?desde=2026-01-01&hasta=2026-12-31" \
  -H "Authorization: Bearer <TOKEN>"
```

## Siguiente iteración

Dime "Continúa" y sigo con **19 Reportes** (el único módulo que queda),
sin volver a tocar los módulos ya implementados de forma no solicitada
ni regenerar la arquitectura, tal como se especificó. Comercio Exterior
y Operación Logística siguen fuera de alcance por pedido explícito (el
negocio no exporta).
