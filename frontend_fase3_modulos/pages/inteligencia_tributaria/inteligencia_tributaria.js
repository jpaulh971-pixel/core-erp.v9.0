/**
 * pages/inteligencia_tributaria/inteligencia_tributaria.js — Page-script del
 * módulo m14_inteligencia_tributaria (app/modules/m14_inteligencia_tributaria).
 *
 * Endpoints (contrato real: router.py + schemas.py del módulo, todos con
 * Bearer y de solo lectura sobre los comprobantes ya emitidos por SUNAT,
 * módulo m12_sunat):
 *   GET /api/inteligencia-tributaria/resumen-igv?desde&hasta
 *     -> ResumenIGV{desde, hasta, por_tipo_comprobante: [{tipo_comprobante,
 *        cantidad, subtotal, igv, total}], total_comprobantes,
 *        total_subtotal, total_igv, total_general}
 *   GET /api/inteligencia-tributaria/libro-ventas?desde&hasta
 *     -> list[ComprobanteLibroVentas{id, numero_completo, tipo_comprobante,
 *        estado, cliente_ruc, cliente_razon_social, moneda, subtotal, igv,
 *        total, emitido_en}]
 *   GET /api/inteligencia-tributaria/comprobantes-anulados?desde&hasta
 *     -> list[ComprobanteAnulado{id, numero_completo, tipo_comprobante,
 *        cliente_ruc, cliente_razon_social, total, motivo_anulacion,
 *        emitido_en, anulado_en}]
 *
 * `desde`/`hasta` filtran por fecha de emisión y aplican a los tres
 * endpoints. No se inventan estados ni tipos de comprobante: el color del
 * badge de `estado` cae a "secondary" para cualquier valor que el Backend
 * devuelva y que no esté en el mapa de abajo (igual criterio que
 * dashboard.js con las órdenes de venta).
 *
 * FASE F10 — Verificación de contrato y limitaciones documentadas:
 * - No se recibió el .zip del Backend adjunto a este encargo (igual que en
 *   F8/F9). El contrato de `m14_inteligencia_tributaria` se verificó a
 *   partir del propio código heredado del Frontend (este mismo archivo, con
 *   las rutas/parámetros/forma de respuesta ya documentados desde F0) y de
 *   una revisión cruzada del proyecto (`grep -rn "exportar|excel|export"`
 *   sobre pages/) que confirma que este módulo no consume ningún endpoint
 *   de exportación. Si en una fase futura se dispone del .zip real del
 *   Backend, se recomienda re-verificar router.py/schemas.py/service.py/
 *   models.py de `m14_inteligencia_tributaria` directamente antes de asumir
 *   que las limitaciones aquí documentadas siguen vigentes.
 * - Solo existen los 3 GET listados arriba en este módulo. No hay ningún
 *   endpoint de escritura (POST/PUT/DELETE): es 100% de solo lectura, por
 *   lo que no corresponde `UI.confirmar()` (no hay ninguna acción que
 *   modifique información).
 * - No existe ningún endpoint de exportación a Excel/PDF, ni de alertas
 *   fiscales, indicadores SUNAT, observaciones o controles/riesgos
 *   tributarios independientes de estos 3 endpoints. No se agregan
 *   pantallas, KPIs ni tablas para datos que el Backend no entrega.
 * - Los únicos filtros que el Backend admite son `desde` y `hasta` (fecha
 *   de emisión), y aplican igual a los 3 endpoints. No existe filtro de
 *   Empresa, Estado ni Tipo a nivel de parámetros de consulta: el "Estado"
 *   y "Tipo" que se ven en el Libro de ventas son columnas informativas de
 *   cada fila, no parámetros que el Backend acepte para filtrar la
 *   consulta. No se agrega ningún <select> de filtro que el Backend no
 *   soporte.
 * - No se inventan gráficos: el Backend entrega un resumen agregado por
 *   tipo de comprobante y dos listados tabulares (libro de ventas y
 *   anulados), no series temporales pensadas para graficar. Se mantienen
 *   los KPIs y las tablas ya existentes desde F0.
 * - F10 agrega la integración de `UI.toast()`/`UI.mostrarCargando()`/
 *   `UI.ocultarCargando()` (ausente hasta ahora en este módulo, igual que
 *   en Reportes antes de F8 e Inteligencia Comercial antes de F9), cantidad
 *   de registros por tabla y validación de rango de fechas, sin tocar
 *   ningún endpoint ni inventar ningún filtro/KPI/gráfico nuevo.
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

  function filtrosFecha() {
    return { desde: inputDesde.value || undefined, hasta: inputHasta.value || undefined };
  }

  function filaVacia(colspan, texto) {
    return `<tr><td colspan="${colspan}" class="text-muted-erp">${texto}</td></tr>`;
  }

  function marcarInvalido(input, invalido) {
    input.classList.toggle("is-invalid", !!invalido);
  }

  // Validación en el cliente: ambas fechas son opcionales, pero si están
  // las dos, "Desde" no puede ser posterior a "Hasta". Igual patrón ya
  // aplicado en F8 (pages/reportes/) y F9 (pages/inteligencia_comercial/).
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

  const COLOR_ESTADO = {
    EMITIDA: "success",
    ACEPTADA: "success",
    PENDIENTE: "secondary",
    ANULADA: "danger",
    RECHAZADA: "danger",
  };

  async function cargarResumenIgv() {
    const r = await apiGet("/api/inteligencia-tributaria/resumen-igv", filtrosFecha());

    document.getElementById("kpiTotalComprobantes").textContent = U.formatearNumero(r.total_comprobantes);
    document.getElementById("kpiTotalSubtotal").textContent = U.formatearMoneda(r.total_subtotal);
    document.getElementById("kpiTotalIgv").textContent = U.formatearMoneda(r.total_igv);
    document.getElementById("kpiTotalGeneral").textContent = U.formatearMoneda(r.total_general);

    const tbody = document.getElementById("tbodyResumenTipo");
    const filas = r.por_tipo_comprobante || [];
    tbody.innerHTML = filas.length
      ? filas
          .map(
            (f) => `
        <tr>
          <td>${U.escaparHtml(f.tipo_comprobante)}</td>
          <td class="text-end">${U.formatearNumero(f.cantidad)}</td>
          <td class="text-end">${U.formatearMoneda(f.subtotal)}</td>
          <td class="text-end">${U.formatearMoneda(f.igv)}</td>
          <td class="text-end">${U.formatearMoneda(f.total)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(5, "Sin comprobantes en el periodo.");
    document.getElementById("countResumenTipo").textContent = `(${U.formatearNumero(filas.length)})`;
  }

  async function cargarLibroVentas() {
    const filas = await apiGet("/api/inteligencia-tributaria/libro-ventas", filtrosFecha());
    const tbody = document.getElementById("tbodyLibroVentas");
    tbody.innerHTML = filas.length
      ? filas
          .map((c) => {
            const color = COLOR_ESTADO[c.estado] || "secondary";
            return `
        <tr>
          <td><code>${U.escaparHtml(c.numero_completo)}</code></td>
          <td>${U.escaparHtml(c.tipo_comprobante)}</td>
          <td><span class="badge text-bg-${color}">${U.escaparHtml(c.estado)}</span></td>
          <td>${U.escaparHtml(c.cliente_ruc)} — ${U.escaparHtml(c.cliente_razon_social)}</td>
          <td class="text-end">${U.formatearMoneda(c.subtotal, c.moneda)}</td>
          <td class="text-end">${U.formatearMoneda(c.igv, c.moneda)}</td>
          <td class="text-end">${U.formatearMoneda(c.total, c.moneda)}</td>
          <td>${U.formatearFecha(c.emitido_en)}</td>
        </tr>`;
          })
          .join("")
      : filaVacia(8, "Sin comprobantes en el periodo.");
    document.getElementById("countLibroVentas").textContent = `(${U.formatearNumero(filas.length)})`;
  }

  async function cargarAnulados() {
    const filas = await apiGet("/api/inteligencia-tributaria/comprobantes-anulados", filtrosFecha());
    const tbody = document.getElementById("tbodyAnulados");
    tbody.innerHTML = filas.length
      ? filas
          .map(
            (c) => `
        <tr class="table-danger">
          <td><code>${U.escaparHtml(c.numero_completo)}</code></td>
          <td>${U.escaparHtml(c.tipo_comprobante)}</td>
          <td>${U.escaparHtml(c.cliente_ruc)} — ${U.escaparHtml(c.cliente_razon_social)}</td>
          <td class="text-end">${U.formatearMoneda(c.total)}</td>
          <td>${U.escaparHtml(c.motivo_anulacion || "—")}</td>
          <td>${U.formatearFecha(c.emitido_en)}</td>
          <td>${U.formatearFecha(c.anulado_en)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(7, "Sin comprobantes anulados en el periodo.");
    document.getElementById("countAnulados").textContent = `(${U.formatearNumero(filas.length)})`;
  }

  async function cargarTodo() {
    ocultarError();
    if (!filtrosValidos()) return; // Rango de fechas inconsistente: no se envía ninguna solicitud.

    btnAplicar.disabled = true;
    if (window.UI) window.UI.mostrarCargando();
    try {
      await Promise.all([cargarResumenIgv(), cargarLibroVentas(), cargarAnulados()]);
    } catch (err) {
      mostrarError(err.message || "Ocurrió un error al cargar la inteligencia tributaria.");
      if (window.UI) window.UI.toast(err.message || "Ocurrió un error al cargar la inteligencia tributaria.", "error");
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

  iniciar();
})();
