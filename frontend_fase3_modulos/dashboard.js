/**
 * dashboard.js — Page-script del módulo m01_dashboard (app/modules/m01_dashboard).
 *
 * Vive en la raíz del Frontend (no en pages/) porque config.js define
 * DASHBOARD_PATH = "dashboard.html" y sidebar.html enlaza a
 * "__ROOT__dashboard.html", igual que layout.js espera para
 * paginaActual() ("dashboard.html" -> "dashboard").
 *
 * Endpoints (contrato real: app/modules/m01_dashboard/router.py + schemas.py,
 * y app/modules/m19_reportes/router.py + schemas.py):
 *   GET /api/dashboard/resumen  (Bearer, sin parámetros) -> DashboardOut
 *     generado_en: datetime
 *     inventario: { total_productos_activos, valor_total_inventario,
 *                   productos_bajo_stock_minimo, alertas_stock: [{producto_id,
 *                   codigo, nombre, stock_total, stock_minimo,
 *                   costo_unitario_promedio}],
 *                   costo_unitario_promedio_general,
 *                   producto_mayor_costo: {producto_id, codigo, nombre,
 *                     costo_unitario_promedio} | null,
 *                   producto_menor_costo: (mismo shape) | null }
 *     ventas: { ordenes_por_estado: {ESTADO: cantidad}, total_vendido_despachadas }
 *     compras: { total_comprado_recibidas }
 *     costos: { total_costos_adicionales, costos_adicionales_por_tipo: {TIPO: monto} }
 *   GET /api/reportes/inventario-valorizado  (Bearer, sin parámetros)
 *     -> ReporteInventarioValorizado.productos[]: { producto_id, codigo,
 *        nombre, cantidad_actual, valor_promedio_unitario, valor_total,
 *        stock_minimo, bajo_stock_minimo }
 *     Es el MISMO endpoint que ya usan pages/inventario/inventario.js,
 *     pages/productos/productos.js y pages/reportes/reportes.js — se
 *     reutiliza aquí tal cual (mismos nombres de campo, sin recalcular
 *     nada) para que "Stock valorizado por producto" muestre exactamente
 *     el mismo costo unitario que esas otras pantallas.
 *
 * Panel de solo lectura: no hay creación/edición aquí, solo un botón de
 * "Actualizar" que repite ambos GET.
 *
 * FASE F15 — Corrección de deuda técnica (hallazgo F14 #2): se elimina el
 * `apiGet()` local (reimplementaba a mano el mismo Bearer + manejo de 401
 * + extracción de `detail` que ya centraliza api-client.js desde F0) y se
 * delega en `window.Api.get`, mismo patrón que el resto de módulos. Se
 * agrega también UI.mostrarCargando()/UI.ocultarCargando() alrededor del
 * único GET de este panel. No se modifica el endpoint ni ningún otro
 * comportamiento.
 *
 * FASE 5 — Dashboard frontend (costo unitario): se agregan los 3 KPIs de
 * costo que ya expone `GET /api/dashboard/resumen` desde la sesión de
 * backend anterior (costo_unitario_promedio_general, producto_mayor_costo,
 * producto_menor_costo) y una tabla nueva "Stock valorizado por producto"
 * que consume `GET /api/reportes/inventario-valorizado` (mismo endpoint ya
 * usado por Inventario/Productos/Reportes). NO se agrega ningún cálculo de
 * costeo nuevo: todo lo que se pinta aquí es un campo que el Backend ya
 * entrega o una división/máximo/mínimo que el propio Backend ya resolvió
 * (ver m01_dashboard/service.py). Las dos peticiones se hacen con
 * `Promise.allSettled` (mismo criterio que theory_of_constraints.js) para
 * que si un endpoint falla, el otro bloque de la pantalla igual se pinte
 * en vez de quedar los dos atascados en "Cargando…".
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const elError = document.getElementById("estadoError");
  const btnActualizar = document.getElementById("btnActualizar");

  function mostrarError(mensaje) {
    elError.textContent = mensaje;
    elError.style.display = "block";
  }

  function ocultarError() {
    elError.style.display = "none";
  }

  async function apiGet(path) {
    // FASE F15: delega en el cliente API centralizado (api-client.js),
    // igual que el resto de módulos, en vez de reimplementar Bearer +
    // manejo de 401 + extracción de `detail` a mano.
    return window.Api.get(path);
  }

  function filaVacia(colspan, texto) {
    return `<tr><td colspan="${colspan}" class="text-muted-erp">${texto}</td></tr>`;
  }

  // Traduce claves de estado (tal como las devuelve el Backend, p.ej.
  // "BORRADOR", "CONFIRMADA", "DESPACHADA", "CANCELADA") a una etiqueta
  // con color de badge de Bootstrap. No inventa estados nuevos: solo
  // aplica un color por defecto si aparece uno que no está en el mapa.
  const COLOR_ESTADO = {
    BORRADOR: "secondary",
    CONFIRMADA: "info",
    DESPACHADA: "success",
    CANCELADA: "danger",
  };

  function pintarKpis(r) {
    document.getElementById("kpiProductosActivos").textContent = U.formatearNumero(
      r.inventario.total_productos_activos
    );
    document.getElementById("kpiValorInventario").textContent = U.formatearMoneda(
      r.inventario.valor_total_inventario
    );
    document.getElementById("kpiBajoStock").textContent = U.formatearNumero(
      r.inventario.productos_bajo_stock_minimo
    );
    document.getElementById("kpiVendidoDespachadas").textContent = U.formatearMoneda(
      r.ventas.total_vendido_despachadas
    );
    document.getElementById("kpiCompradoRecibidas").textContent = U.formatearMoneda(
      r.compras.total_comprado_recibidas
    );
    document.getElementById("kpiCostosAdicionales").textContent = U.formatearMoneda(
      r.costos.total_costos_adicionales
    );
    document.getElementById("kpiCostoUnitarioPromedio").textContent = U.formatearMoneda(
      r.inventario.costo_unitario_promedio_general
    );
  }

  // Pinta el mini-card de producto_mayor_costo / producto_menor_costo.
  // Ambos pueden venir `null` (Backend: sin productos con costo_unitario_promedio
  // > 0 todavía, ej. inventario recién creado sin lotes) — se muestra un
  // texto neutro en ese caso, sin inventar datos.
  function pintarProductoCosto(elId, producto) {
    const el = document.getElementById(elId);
    if (!producto) {
      el.textContent = "Sin datos suficientes.";
      return;
    }
    el.innerHTML = `<code>${U.escaparHtml(producto.codigo)}</code> — ${U.escaparHtml(
      producto.nombre
    )} <span class="text-muted-erp">(${U.formatearMoneda(producto.costo_unitario_promedio)})</span>`;
  }

  function pintarOrdenesPorEstado(r) {
    const tbody = document.getElementById("tbodyOrdenesEstado");
    const entradas = Object.entries(r.ventas.ordenes_por_estado || {});
    tbody.innerHTML = entradas.length
      ? entradas
          .map(([estado, cantidad]) => {
            const color = COLOR_ESTADO[estado] || "secondary";
            return `
        <tr>
          <td><span class="badge text-bg-${color}">${U.escaparHtml(estado)}</span></td>
          <td class="text-end">${U.formatearNumero(cantidad)}</td>
        </tr>`;
          })
          .join("")
      : filaVacia(2, "Sin órdenes de venta registradas.");
  }

  function pintarCostosPorTipo(r) {
    const tbody = document.getElementById("tbodyCostosTipo");
    const entradas = Object.entries(r.costos.costos_adicionales_por_tipo || {});
    tbody.innerHTML = entradas.length
      ? entradas
          .map(
            ([tipo, monto]) => `
        <tr>
          <td>${U.escaparHtml(tipo)}</td>
          <td class="text-end">${U.formatearMoneda(monto)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(2, "Sin costos adicionales registrados.");
  }

  function pintarAlertasStock(r) {
    const tbody = document.getElementById("tbodyAlertasStock");
    const alertas = r.inventario.alertas_stock || [];
    tbody.innerHTML = alertas.length
      ? alertas
          .map(
            (a) => `
        <tr class="table-danger">
          <td><code>${U.escaparHtml(a.codigo)}</code></td>
          <td>${U.escaparHtml(a.nombre)}</td>
          <td class="text-end">${U.formatearNumero(a.stock_total, 2)}</td>
          <td class="text-end">${U.formatearNumero(a.stock_minimo, 2)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(4, "Sin alertas: ningún producto está bajo su stock mínimo.");
  }

  // Tabla "Stock valorizado por producto": pinta tal cual los campos que
  // entrega GET /api/reportes/inventario-valorizado (mismo endpoint y
  // mismos nombres de campo que pages/inventario/inventario.js y
  // pages/productos/productos.js). Cero cálculos nuevos.
  function pintarStockValorizado(r2) {
    const tbody = document.getElementById("tbodyStockValorizado");
    const productos = r2.productos || [];
    tbody.innerHTML = productos.length
      ? productos
          .map(
            (p) => `
        <tr${p.bajo_stock_minimo ? ' class="table-danger"' : ""}>
          <td><code>${U.escaparHtml(p.codigo)}</code></td>
          <td>${U.escaparHtml(p.nombre)}</td>
          <td class="text-end">${U.formatearNumero(p.cantidad_actual, 2)}</td>
          <td class="text-end">${U.formatearMoneda(p.valor_promedio_unitario)}</td>
          <td class="text-end">${U.formatearMoneda(p.valor_total)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(5, "Sin productos valorizados todavía.");
  }

  function tbodyError(id, colspan, mensaje) {
    const tbody = document.getElementById(id);
    if (tbody) tbody.innerHTML = filaVacia(colspan, mensaje);
  }

  async function cargarTodo() {
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      // FASE 5: dos peticiones independientes con Promise.allSettled — si
      // /api/reportes/inventario-valorizado falla, el resto del panel
      // (KPIs, órdenes por estado, costos, alertas) igual se pinta, y
      // viceversa. Mismo criterio que theory_of_constraints.js.
      const [resDashboard, resValorizado] = await Promise.allSettled([
        apiGet("/api/dashboard/resumen"),
        apiGet("/api/reportes/inventario-valorizado"),
      ]);

      if (resDashboard.status === "fulfilled") {
        const r = resDashboard.value;
        pintarKpis(r);
        pintarOrdenesPorEstado(r);
        pintarCostosPorTipo(r);
        pintarAlertasStock(r);
        pintarProductoCosto("kpiProductoMayorCosto", r.inventario.producto_mayor_costo);
        pintarProductoCosto("kpiProductoMenorCosto", r.inventario.producto_menor_costo);
        document.getElementById("footerGenerado").textContent =
          `Generado: ${U.formatearFechaHora(r.generado_en)}`;
      } else {
        const mensaje =
          resDashboard.reason?.message || "No se pudo cargar el resumen del dashboard.";
        mostrarError(mensaje);
        if (window.UI) window.UI.toast(mensaje, "error");
        tbodyError("tbodyOrdenesEstado", 2, "No se pudo cargar.");
        tbodyError("tbodyCostosTipo", 2, "No se pudo cargar.");
        tbodyError("tbodyAlertasStock", 4, "No se pudo cargar.");
      }

      if (resValorizado.status === "fulfilled") {
        pintarStockValorizado(resValorizado.value);
      } else {
        const mensaje =
          resValorizado.reason?.message || "No se pudo cargar el stock valorizado.";
        tbodyError("tbodyStockValorizado", 5, mensaje);
        if (window.UI) window.UI.toast(mensaje, "error");
      }
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    btnActualizar.addEventListener("click", cargarTodo);
    cargarTodo();
  }

  iniciar();
})();
