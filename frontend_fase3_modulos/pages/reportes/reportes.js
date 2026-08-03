/**
 * pages/reportes/reportes.js — Page-script del módulo m19_reportes
 * (app/modules/m19_reportes).
 *
 * Endpoints (contrato_api_modulos.md, sección 4), todos con Bearer:
 *   GET /api/reportes/resumen-general?desde&hasta       -> ResumenGeneral (KPIs superiores)
 *   GET /api/reportes/ventas?desde&hasta                -> ReporteVentas   (tab "Ventas")
 *   GET /api/reportes/compras?desde&hasta               -> ReporteCompras  (tab "Compras")
 *   GET /api/reportes/inventario-valorizado (sin params) -> ReporteInventarioValorizado (tab "Inventario")
 *
 * `desde`/`hasta` son opcionales: si el usuario no toca los filtros, se
 * envían vacíos y el Backend trae todo el histórico (igual que el resto
 * de módulos de este contrato).
 *
 * FASE F8 — Verificación de contrato y limitaciones documentadas:
 * - El Backend congelado (`Core_ERP_Backend_B2.zip`, m19_reportes) solo
 *   expone los 4 GET listados arriba. No existe ningún otro endpoint en
 *   ese módulo (ni en ningún otro módulo del proyecto, revisado en F0-F7)
 *   para exportar a Excel o PDF. Por lo tanto, F8 NO agrega botones de
 *   "Exportar": no hay ningún endpoint del Backend que los respalde y
 *   este proyecto no genera archivos de exportación desde el cliente.
 *   Si en una fase futura el Backend libera endpoints de exportación,
 *   se deben integrar contra esos endpoints reales (nunca generando el
 *   archivo en JavaScript).
 * - El único filtro que aceptan estos endpoints es el rango de fechas
 *   (`desde`/`hasta`), y únicamente en resumen-general/ventas/compras.
 *   `inventario-valorizado` no acepta ningún parámetro: es una foto del
 *   inventario actual. No se agregan filtros de cliente, proveedor,
 *   producto ni estado porque el Backend no los admite en este módulo
 *   (a diferencia de otros módulos del proyecto, como m10_ventas, que sí
 *   admiten `estado` en su propio listado).
 * - F8 se limita a completar la calidad de UX de esta pantalla que ya
 *   existía desde F0 (integración de UI.toast()/UI.mostrarCargando()/
 *   UI.ocultarCargando(), cantidad de registros por tabla y validación
 *   de rango de fechas en el cliente) sin tocar ningún endpoint nuevo.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const elError = document.getElementById("estadoError");
  const inputDesde = document.getElementById("filtroDesde");
  const inputHasta = document.getElementById("filtroHasta");
  const btnAplicar = document.getElementById("btnAplicarFiltros");

  function mostrarError(mensaje) {
    elError.textContent = mensaje;
    elError.style.display = "block";
  }

  function ocultarError() {
    elError.style.display = "none";
  }

  async function apiGet(path, params) {
    // FASE F0: delega en el cliente API centralizado (api-client.js).
    return window.Api.get(path, params);
  }

  function filtrosActuales() {
    return { desde: inputDesde.value || undefined, hasta: inputHasta.value || undefined };
  }

  function filaVacia(colspan, texto) {
    return `<tr><td colspan="${colspan}" class="text-muted-erp">${texto}</td></tr>`;
  }

  function marcarInvalido(input, invalido) {
    input.classList.toggle("is-invalid", !!invalido);
  }

  // Validación en el cliente (el Backend no documenta que valide esto,
  // pero enviar un rango invertido no tiene ningún sentido de negocio):
  // ambas fechas son opcionales, pero si están las dos, "Desde" no puede
  // ser posterior a "Hasta". No se envía ninguna solicitud si el rango
  // es inconsistente.
  function filtrosValidos() {
    marcarInvalido(inputDesde, false);
    marcarInvalido(inputHasta, false);

    const desde = inputDesde.value;
    const hasta = inputHasta.value;

    if (desde && hasta && desde > hasta) {
      marcarInvalido(inputDesde, true);
      marcarInvalido(inputHasta, true);
      const mensaje = "La fecha 'Desde' no puede ser posterior a la fecha 'Hasta'.";
      mostrarError(mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
      return false;
    }
    return true;
  }

  async function cargarResumenGeneral() {
    const r = await apiGet("/api/reportes/resumen-general", filtrosActuales());
    document.getElementById("kpiTotalVendido").textContent = U.formatearMoneda(r.total_vendido_periodo);
    document.getElementById("kpiTotalComprado").textContent = U.formatearMoneda(r.total_comprado_periodo);
    document.getElementById("kpiOrdenesVenta").textContent = U.formatearNumero(r.ordenes_venta_periodo);
    document.getElementById("kpiOrdenesCompra").textContent = U.formatearNumero(r.ordenes_compra_periodo);
    document.getElementById("kpiValorInventario").textContent = U.formatearMoneda(r.valor_inventario_actual);
    document.getElementById("kpiBajoStock").textContent = U.formatearNumero(r.productos_bajo_stock_minimo);
  }

  async function cargarVentas() {
    const r = await apiGet("/api/reportes/ventas", filtrosActuales());
    const tbodyProducto = document.getElementById("tbodyVentasProducto");
    const tbodyCliente = document.getElementById("tbodyVentasCliente");

    tbodyProducto.innerHTML = r.por_producto.length
      ? r.por_producto
          .map(
            (p) => `
        <tr>
          <td><code>${U.escaparHtml(p.codigo)}</code></td>
          <td>${U.escaparHtml(p.nombre)}</td>
          <td class="text-end">${U.formatearNumero(p.cantidad, 2)}</td>
          <td class="text-end">${U.formatearMoneda(p.total)}</td>
          <td class="text-end">${U.formatearMoneda(p.costo_unitario_promedio)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(5, "Sin ventas en el periodo.");
    document.getElementById("countVentasProducto").textContent = `(${U.formatearNumero(r.por_producto.length)})`;

    tbodyCliente.innerHTML = r.por_cliente.length
      ? r.por_cliente
          .map(
            (c) => `
        <tr>
          <td>${U.escaparHtml(c.razon_social)}</td>
          <td class="text-end">${U.formatearNumero(c.cantidad_ordenes)}</td>
          <td class="text-end">${U.formatearMoneda(c.total)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(3, "Sin clientes en el periodo.");
    document.getElementById("countVentasCliente").textContent = `(${U.formatearNumero(r.por_cliente.length)})`;

    document.getElementById("resumenVentas").textContent =
      `${U.formatearNumero(r.total_ordenes)} órdenes despachadas · Total vendido: ${U.formatearMoneda(r.total_vendido)}`;
  }

  async function cargarCompras() {
    const r = await apiGet("/api/reportes/compras", filtrosActuales());
    const tbodyProducto = document.getElementById("tbodyComprasProducto");
    const tbodyProveedor = document.getElementById("tbodyComprasProveedor");

    tbodyProducto.innerHTML = r.por_producto.length
      ? r.por_producto
          .map(
            (p) => `
        <tr>
          <td><code>${U.escaparHtml(p.codigo)}</code></td>
          <td>${U.escaparHtml(p.nombre)}</td>
          <td class="text-end">${U.formatearNumero(p.cantidad, 2)}</td>
          <td class="text-end">${U.formatearMoneda(p.total)}</td>
          <td class="text-end">${U.formatearMoneda(p.costo_unitario_promedio)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(5, "Sin compras en el periodo.");
    document.getElementById("countComprasProducto").textContent = `(${U.formatearNumero(r.por_producto.length)})`;

    tbodyProveedor.innerHTML = r.por_proveedor.length
      ? r.por_proveedor
          .map(
            (p) => `
        <tr>
          <td>${U.escaparHtml(p.razon_social)}</td>
          <td class="text-end">${U.formatearNumero(p.cantidad_ordenes)}</td>
          <td class="text-end">${U.formatearMoneda(p.total)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(3, "Sin proveedores en el periodo.");
    document.getElementById("countComprasProveedor").textContent = `(${U.formatearNumero(r.por_proveedor.length)})`;

    document.getElementById("resumenCompras").textContent =
      `${U.formatearNumero(r.total_ordenes)} órdenes recibidas · Total comprado: ${U.formatearMoneda(r.total_comprado)}`;
  }

  // No depende de desde/hasta: es una foto del inventario actual. Se
  // recarga junto con el resto por simplicidad, aunque los filtros de
  // fecha no le apliquen (el propio Backend no expone params para este
  // endpoint).
  async function cargarInventarioValorizado() {
    const r = await apiGet("/api/reportes/inventario-valorizado");
    const tbody = document.getElementById("tbodyInventario");

    tbody.innerHTML = r.productos.length
      ? r.productos
          .map(
            (p) => `
        <tr class="${p.bajo_stock_minimo ? "table-danger" : ""}">
          <td><code>${U.escaparHtml(p.codigo)}</code></td>
          <td>${U.escaparHtml(p.nombre)}</td>
          <td class="text-end">${U.formatearNumero(p.cantidad_actual, 2)}</td>
          <td class="text-end">${U.formatearMoneda(p.valor_promedio_unitario)}</td>
          <td class="text-end">${U.formatearMoneda(p.valor_total)}</td>
          <td class="text-end">${U.formatearNumero(p.stock_minimo, 2)}</td>
          <td>${p.bajo_stock_minimo ? '<span class="text-danger fw-bold">Bajo mínimo</span>' : '<span class="text-muted-erp">OK</span>'}</td>
        </tr>`
          )
          .join("")
      : filaVacia(7, "No hay productos registrados.");
    document.getElementById("countInventario").textContent = `${U.formatearNumero(r.productos.length)} registro(s)`;

    document.getElementById("resumenInventario").textContent =
      `${U.formatearNumero(r.total_productos)} productos · Valor total: ${U.formatearMoneda(r.valor_total_inventario)} · ` +
      `${U.formatearNumero(r.productos_bajo_stock_minimo)} bajo stock mínimo · Generado: ${U.formatearFechaHora(r.generado_en)}`;
  }

  async function cargarTodo() {
    ocultarError();
    if (!filtrosValidos()) return; // Rango de fechas inconsistente: no se envía ninguna solicitud.

    btnAplicar.disabled = true;
    if (window.UI) window.UI.mostrarCargando();
    try {
      await Promise.all([
        cargarResumenGeneral(),
        cargarVentas(),
        cargarCompras(),
        cargarInventarioValorizado(),
      ]);
    } catch (err) {
      mostrarError(err.message || "Ocurrió un error al cargar los reportes.");
      if (window.UI) window.UI.toast(err.message || "Ocurrió un error al cargar los reportes.", "error");
    } finally {
      btnAplicar.disabled = false;
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    btnAplicar.addEventListener("click", cargarTodo);
    [inputDesde, inputHasta].forEach((input) =>
      input.addEventListener("change", () => {
        marcarInvalido(inputDesde, false);
        marcarInvalido(inputHasta, false);
      })
    );
    cargarTodo();
  }

  // FASE 9B — Importar Compras Nacionalizadas (frontend de m04_compras):
  // al confirmar una importación, compras.js escribe una señal en
  // localStorage (sin backend, sin SPA) para que esta página, si está
  // abierta en otra pestaña, se refresque sola. Reutiliza la función de
  // carga ya existente (cargarTodo()); no agrega endpoints ni lógica de
  // negocio nueva.
  // FASE 10A — Importar Ventas (frontend de m10_ventas): ventas.js escribe
  // la misma señal con modulo: "ventas". Este listener se amplía para
  // aceptar también ese valor y reutilizar exactamente la misma función
  // de carga (cargarTodo()), que ya trae la pestaña "Ventas" (por
  // producto/por cliente, GET /api/reportes/ventas) y "Inventario
  // valorizado" — ambas ya reflejan una importación de ventas sin
  // necesitar ningún endpoint ni pestaña nueva.
  window.addEventListener("storage", (ev) => {
    if (ev.key !== "erp_datos_actualizados" || !ev.newValue) return;
    try {
      const datos = JSON.parse(ev.newValue);
      if (datos && (datos.modulo === "compras" || datos.modulo === "ventas")) cargarTodo();
    } catch (err) {
      /* señal mal formada: se ignora, no es crítico. */
    }
  });

  iniciar();
})();
