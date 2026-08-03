/**
 * pages/sunat/sunat.js — Page-script del módulo m12_sunat
 * (app/modules/m12_sunat).
 *
 * Endpoints (contrato real: router.py + schemas.py), todos con Bearer:
 *   POST /api/sunat/comprobantes                body ComprobanteCrear -> ComprobanteOut (201)
 *   GET  /api/sunat/comprobantes?estado=str|null                      -> list[ComprobanteOut]
 *   GET  /api/sunat/comprobantes/{id}                                 -> ComprobanteOut
 *   GET  /api/sunat/ordenes/{orden_venta_id}/comprobante              -> ComprobanteOut
 *   POST /api/sunat/comprobantes/{id}/anular     body AnulacionCrear  -> ComprobanteOut
 *
 * ComprobanteCrear: orden_venta_id, tipo_comprobante ("FACTURA"|"BOLETA").
 * AnulacionCrear: motivo (1-300 caracteres).
 * ComprobanteOut trae ya el snapshot completo (cliente_ruc,
 * cliente_razon_social, serie, correlativo, numero_completo, subtotal,
 * igv, total, estado, motivo_anulacion, emitido_en, anulado_en): no hace
 * falta cruzar con m11_clientes para mostrar el listado.
 *
 * No existe un endpoint para "editar" ni para forzar ACEPTADO/RECHAZADO:
 * el Backend define esos estados en TRANSICIONES_VALIDAS
 * (m12_sunat/validators.py) pero el router SOLO expone crear, listar,
 * obtener y anular. Por eso el frontend solo ofrece "Emitir" y "Anular"
 * (ningún botón "Aceptar"/"Rechazar", porque ese endpoint no existe).
 * TRANSICIONES_VALIDAS real:
 *   EMITIDO  -> ACEPTADO | RECHAZADO | ANULADO
 *   ACEPTADO -> ANULADO
 *   RECHAZADO / ANULADO -> (estados finales)
 * El botón "Anular comprobante" solo se muestra si el estado actual tiene
 * "ANULADO" como transición permitida (EMITIDO o ACEPTADO).
 *
 * El Backend exige que la orden de venta esté DESPACHADA para emitir
 * (validar_orden_despachada) y que no exista ya un comprobante para esa
 * orden (validar_no_duplicado, UNIQUE en BD): el selector de "Nueva
 * orden" se llena con GET /api/ventas?estado=DESPACHADA; si el usuario
 * elige una que ya tiene comprobante, el Backend responde 409 y el
 * mensaje se muestra tal cual (no se filtra localmente para no inventar
 * un endpoint de "ordenes sin comprobante" que no existe).
 *
 * Soporta el deep-link que arma ventas.js: pages/sunat/index.html
 * ?orden_venta_id=<id>. Al cargar, si el parámetro está presente:
 *   - si esa orden YA tiene comprobante (GET .../comprobante = 200), abre
 *     directamente su detalle;
 *   - si no tiene (404), abre el modal de emisión con esa orden
 *     preseleccionada.
 *
 * FASE F15 — Corrección de deuda técnica (hallazgo F14 #1): se integra
 * UI.mostrarCargando()/UI.ocultarCargando()/UI.toast() (ausentes hasta
 * ahora en este módulo, mismo patrón ya aplicado en F10-F13). Además, la
 * acción destructiva "Anular comprobante" ahora pasa por
 * UI.confirmar() antes de ejecutarse (el módulo no usaba window.confirm()
 * nativo ni ningún tipo de confirmación previa: el motivo se pedía en el
 * propio bloque `#bloqueAnular` y el botón "Confirmar anulación" disparaba
 * la petición directamente). No se toca ningún endpoint ni el flujo de
 * transiciones de estado.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const TRANSICIONES_VALIDAS = {
    EMITIDO: new Set(["ACEPTADO", "RECHAZADO", "ANULADO"]),
    ACEPTADO: new Set(["ANULADO"]),
    RECHAZADO: new Set(),
    ANULADO: new Set(),
  };

  const elError = document.getElementById("estadoError");
  const selectEstado = document.getElementById("selectEstado");
  const btnNuevoComprobante = document.getElementById("btnNuevoComprobante");
  const tbody = document.getElementById("tbodyComprobantes");

  const modalNuevoEl = document.getElementById("modalNuevoComprobante");
  // Protección mínima: si el CDN de Bootstrap no cargó, bootstrap no existe
  // y "new bootstrap.Modal(...)" rompería toda la página. En ese caso el
  // modal queda en null y las funciones que lo usan avisan el error en vez
  // de lanzar un TypeError.
  const bootstrapDisponible = typeof bootstrap !== "undefined" && bootstrap.Modal;
  const modalNuevo = bootstrapDisponible ? new bootstrap.Modal(modalNuevoEl) : null;
  const formNuevoComprobante = document.getElementById("formNuevoComprobante");
  const modalNuevoComprobanteError = document.getElementById("modalNuevoComprobanteError");
  const comprobanteOrden = document.getElementById("comprobanteOrden");
  const comprobanteTipo = document.getElementById("comprobanteTipo");

  const modalDetalleEl = document.getElementById("modalDetalleComprobante");
  const modalDetalle = bootstrapDisponible ? new bootstrap.Modal(modalDetalleEl) : null;
  const detalleComprobanteTitulo = document.getElementById("detalleComprobanteTitulo");
  const modalDetalleComprobanteError = document.getElementById("modalDetalleComprobanteError");
  const detalleComprobanteInfo = document.getElementById("detalleComprobanteInfo");
  const bloqueAnular = document.getElementById("bloqueAnular");
  const motivoAnulacion = document.getElementById("motivoAnulacion");
  const btnMostrarAnular = document.getElementById("btnMostrarAnular");
  const btnConfirmarAnular = document.getElementById("btnConfirmarAnular");

  let comprobantesCache = [];
  let ordenesDespachadasCache = [];
  let comprobanteDetalleActualId = null;

  function mostrarError(mensaje) {
    elError.textContent = mensaje;
    elError.style.display = "block";
  }

  function ocultarError() {
    elError.style.display = "none";
  }

  function mostrarErrorModal(el, mensaje) {
    el.textContent = mensaje;
    el.style.display = "block";
  }

  function ocultarErrorModal(el) {
    el.style.display = "none";
  }

  async function apiRequest(path, opciones) {
    // FASE F0: delega en el cliente API centralizado (api-client.js).
    // Se conserva esta función local -mismo nombre y firma- para no
    // tocar ningún call-site existente en este archivo.
    return window.Api.request(path, opciones);
  }

  const apiGet = (path) => apiRequest(path);
  const apiPost = (path, body) => apiRequest(path, { method: "POST", body: JSON.stringify(body) });

  function filaVacia(colspan, texto) {
    return `<tr><td colspan="${colspan}" class="text-muted-erp">${texto}</td></tr>`;
  }

  function colorEstado(estado) {
    if (estado === "EMITIDO") return "info";
    if (estado === "ACEPTADO") return "success";
    if (estado === "RECHAZADO") return "danger";
    if (estado === "ANULADO") return "secondary";
    return "secondary";
  }

  // ---------- Listado ----------
  function pintarComprobantes() {
    tbody.innerHTML = comprobantesCache.length
      ? comprobantesCache
          .map(
            (c) => `
        <tr>
          <td><code>${U.escaparHtml(c.numero_completo)}</code></td>
          <td>${U.escaparHtml(c.tipo_comprobante)}</td>
          <td>${U.escaparHtml(c.cliente_razon_social)}</td>
          <td>#${c.orden_venta_id}</td>
          <td class="text-end">${U.formatearMoneda(c.total, c.moneda)}</td>
          <td><span class="badge text-bg-${colorEstado(c.estado)}">${U.escaparHtml(c.estado)}</span></td>
          <td>${U.formatearFechaHora(c.emitido_en)}</td>
          <td class="text-end">
            <button type="button" class="btn btn-sm btn-outline-secondary btn-ver-detalle" data-id="${c.id}">
              <i class="bi bi-eye"></i> Ver
            </button>
          </td>
        </tr>`
          )
          .join("")
      : filaVacia(8, "No hay comprobantes emitidos.");

    tbody.querySelectorAll(".btn-ver-detalle").forEach((btn) => {
      btn.addEventListener("click", () => abrirModalDetalle(Number(btn.dataset.id)));
    });
  }

  async function cargarComprobantes() {
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      const query = selectEstado.value ? `?estado=${encodeURIComponent(selectEstado.value)}` : "";
      comprobantesCache = await apiGet(`/api/sunat/comprobantes${query}`);
      pintarComprobantes();
    } catch (err) {
      const mensaje = err.message || "Ocurrió un error al cargar los comprobantes.";
      mostrarError(mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Cache de órdenes de venta DESPACHADAS (para emitir) ----------
  async function cargarOrdenesDespachadasCache() {
    ordenesDespachadasCache = await apiGet("/api/ventas?estado=DESPACHADA");
    comprobanteOrden.innerHTML =
      '<option value="">Seleccionar…</option>' +
      ordenesDespachadasCache
        .map((o) => `<option value="${o.id}">#${o.id} — ${U.escaparHtml(o.cliente_razon_social)}</option>`)
        .join("");
  }

  // ---------- Modal Emitir comprobante ----------
  function limpiarFormularioNuevo() {
    formNuevoComprobante.reset();
    ocultarErrorModal(modalNuevoComprobanteError);
  }

  function abrirModalNuevo(ordenPreseleccionada) {
    if (!modalNuevo) {
      mostrarError("No se pudo abrir la ventana de nuevo comprobante: Bootstrap no está disponible.");
      return;
    }
    limpiarFormularioNuevo();
    if (ordenPreseleccionada) comprobanteOrden.value = String(ordenPreseleccionada);
    modalNuevo.show();
  }

  async function guardarNuevoComprobante(ev) {
    ev.preventDefault();
    ocultarErrorModal(modalNuevoComprobanteError);

    const datos = {
      orden_venta_id: Number(comprobanteOrden.value),
      tipo_comprobante: comprobanteTipo.value,
    };

    if (window.UI) window.UI.mostrarCargando();
    try {
      await apiPost("/api/sunat/comprobantes", datos);
      if (modalNuevo) modalNuevo.hide();
      if (window.UI) window.UI.toast("Comprobante emitido correctamente.", "success");
      await Promise.all([cargarComprobantes(), cargarOrdenesDespachadasCache()]);
    } catch (err) {
      const mensaje = err.message || "No se pudo emitir el comprobante.";
      mostrarErrorModal(modalNuevoComprobanteError, mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Modal Detalle + Anular ----------
  function pintarDetalle(c) {
    detalleComprobanteTitulo.textContent = c.numero_completo;
    detalleComprobanteInfo.innerHTML = `
      <div class="col-6"><span class="text-muted-erp">Cliente</span><br>${U.escaparHtml(c.cliente_razon_social)}</div>
      <div class="col-6"><span class="text-muted-erp">RUC / doc. cliente</span><br>${U.escaparHtml(c.cliente_ruc)}</div>
      <div class="col-4"><span class="text-muted-erp">Tipo</span><br>${U.escaparHtml(c.tipo_comprobante)}</div>
      <div class="col-4"><span class="text-muted-erp">Estado</span><br><span class="badge text-bg-${colorEstado(c.estado)}">${U.escaparHtml(c.estado)}</span></div>
      <div class="col-4"><span class="text-muted-erp">Orden de venta</span><br>#${c.orden_venta_id}</div>
      <div class="col-4"><span class="text-muted-erp">Subtotal</span><br>${U.formatearMoneda(c.subtotal, c.moneda)}</div>
      <div class="col-4"><span class="text-muted-erp">IGV</span><br>${U.formatearMoneda(c.igv, c.moneda)}</div>
      <div class="col-4"><span class="text-muted-erp">Total</span><br><b>${U.formatearMoneda(c.total, c.moneda)}</b></div>
      <div class="col-6"><span class="text-muted-erp">Emitido</span><br>${U.formatearFechaHora(c.emitido_en)}</div>
      <div class="col-6"><span class="text-muted-erp">Anulado</span><br>${U.formatearFechaHora(c.anulado_en)}</div>
      ${c.motivo_anulacion ? `<div class="col-12"><span class="text-muted-erp">Motivo de anulación</span><br>${U.escaparHtml(c.motivo_anulacion)}</div>` : ""}
    `;

    const puedeAnular = (TRANSICIONES_VALIDAS[c.estado] || new Set()).has("ANULADO");
    btnMostrarAnular.style.display = puedeAnular ? "" : "none";
    btnConfirmarAnular.style.display = "none";
    bloqueAnular.style.display = "none";
    motivoAnulacion.value = "";
  }

  async function abrirModalDetalle(id) {
    if (!modalDetalle) {
      mostrarError("No se pudo abrir el detalle del comprobante: Bootstrap no está disponible.");
      return;
    }
    comprobanteDetalleActualId = id;
    ocultarErrorModal(modalDetalleComprobanteError);
    detalleComprobanteTitulo.textContent = "Comprobante";
    detalleComprobanteInfo.innerHTML = "";
    btnMostrarAnular.style.display = "none";
    btnConfirmarAnular.style.display = "none";
    bloqueAnular.style.display = "none";
    modalDetalle.show();

    if (window.UI) window.UI.mostrarCargando();
    try {
      const c = await apiGet(`/api/sunat/comprobantes/${id}`);
      pintarDetalle(c);
    } catch (err) {
      const mensaje = err.message || "No se pudo cargar el comprobante.";
      mostrarErrorModal(modalDetalleComprobanteError, mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function mostrarBloqueAnular() {
    bloqueAnular.style.display = "";
    btnMostrarAnular.style.display = "none";
    btnConfirmarAnular.style.display = "";
  }

  async function confirmarAnulacion() {
    if (!comprobanteDetalleActualId) return;
    ocultarErrorModal(modalDetalleComprobanteError);
    const motivo = motivoAnulacion.value.trim();
    if (!motivo) {
      mostrarErrorModal(modalDetalleComprobanteError, "Ingresa el motivo de anulación.");
      return;
    }

    // Acción destructiva: se confirma con UI.confirmar() (modal Bootstrap
    // reutilizable) en vez de ejecutar la anulación directamente. No se usa
    // window.confirm() nativo, igual que el resto del proyecto.
    const confirmado = window.UI
      ? await window.UI.confirmar({
          titulo: "Anular comprobante",
          mensaje: `¿Confirmas la anulación de este comprobante? Esta acción es definitiva y no se puede deshacer. Motivo: "${motivo}"`,
          textoAceptar: "Anular comprobante",
          variante: "danger",
        })
      : true;
    if (!confirmado) return;

    if (window.UI) window.UI.mostrarCargando();
    try {
      const c = await apiPost(`/api/sunat/comprobantes/${comprobanteDetalleActualId}/anular`, { motivo });
      pintarDetalle(c);
      if (window.UI) window.UI.toast("Comprobante anulado correctamente.", "success");
      await cargarComprobantes();
    } catch (err) {
      const mensaje = err.message || "No se pudo anular el comprobante.";
      mostrarErrorModal(modalDetalleComprobanteError, mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Deep-link desde Ventas: ?orden_venta_id=<id> ----------
  async function atenderDeepLink() {
    const params = new URLSearchParams(window.location.search);
    const ordenVentaId = params.get("orden_venta_id");
    if (!ordenVentaId) return;

    try {
      const c = await apiGet(`/api/sunat/ordenes/${ordenVentaId}/comprobante`);
      await abrirModalDetalle(c.id);
    } catch (err) {
      if (err.status === 404) {
        abrirModalNuevo(ordenVentaId);
      } else {
        mostrarError(err.message || "No se pudo verificar el comprobante de esa orden.");
      }
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    selectEstado.addEventListener("change", cargarComprobantes);
    btnNuevoComprobante.addEventListener("click", () => abrirModalNuevo(null));
    formNuevoComprobante.addEventListener("submit", guardarNuevoComprobante);
    btnMostrarAnular.addEventListener("click", mostrarBloqueAnular);
    btnConfirmarAnular.addEventListener("click", confirmarAnulacion);

    (async () => {
      if (window.UI) window.UI.mostrarCargando();
      try {
        await cargarOrdenesDespachadasCache();
      } catch (err) {
        const mensaje = err.message || "No se pudieron cargar las órdenes de venta despachadas.";
        mostrarError(mensaje);
        if (window.UI) window.UI.toast(mensaje, "error");
      } finally {
        if (window.UI) window.UI.ocultarCargando();
      }
      await cargarComprobantes();
      await atenderDeepLink();
    })();
  }

  iniciar();
})();
