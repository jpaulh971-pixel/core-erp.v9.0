/**
 * pages/costos/costos.js — Page-script del módulo m08_costos
 * (app/modules/m08_costos).
 *
 * Endpoints (contrato real: router.py + schemas.py), todos con Bearer:
 *   POST /api/costos/adicionales
 *        body CostoAdicionalCrear -> CostoAdicionalOut (201)
 *   GET  /api/costos/compras/{orden_compra_id}/costeo
 *        -> CosteoCompraOut
 *   GET  /api/costos/exportaciones/{declaracion_id}/rentabilidad
 *        -> RentabilidadExportacionOut
 *
 * CostoAdicionalCrear: tipo_documento (COMPRA|EXPORTACION), documento_id,
 * tipo_costo (FLETE|SEGURO|ADUANA|ALMACENAJE|MANIPULEO|OTRO),
 * descripcion?, monto (>0), moneda (3 letras, default "USD").
 *
 * El Backend (service.py) NO expone un endpoint para listar costos
 * adicionales sueltos ni para editarlos/borrarlos: solo se crean, y se
 * ven agregados dentro de CosteoCompraOut.detalle_costos_adicionales o
 * RentabilidadExportacionOut.detalle_costos_adicionales. Por eso esta
 * página no tiene una tabla general de "costos adicionales": el detalle
 * solo aparece dentro de la consulta de costeo/rentabilidad a la que
 * pertenece, tal como lo arma el service. No se inventa un listado que
 * el Backend no tiene.
 *
 * costeo_compra calcula costo_unitario_ponderado sobre valor_mercaderia
 * (cantidad * costo_unitario de cada item de la orden) + costos
 * adicionales, tal como hace service.py; esta página solo pinta lo que
 * el Backend ya calculó, no repite el cálculo en el cliente.
 *
 * rentabilidad_exportacion usa el costo real leído del kardex (no un
 * promedio recalculado) según el comentario de service.py; esta página
 * solo muestra el campo costo_mercaderia_real que ya viene resuelto.
 *
 * Tras registrar un costo adicional, si su tipo_documento/documento_id
 * coincide con la consulta de costeo o de rentabilidad actualmente
 * abierta en pantalla, se vuelve a consultar ese endpoint para reflejar
 * el nuevo costo (no se edita el DOM a mano con datos no confirmados
 * por el Backend).
 *
 * FASE F15 — Corrección de deuda técnica (hallazgo F14 #1): se integra
 * UI.mostrarCargando()/UI.ocultarCargando()/UI.toast() (ausentes hasta
 * ahora en este módulo, mismo patrón ya aplicado en F10-F13). No se toca
 * ningún cálculo ni endpoint. Además se corrige el hallazgo de
 * accesibilidad documentado en F14 (RESUMEN_TECNICO_F14.md, sección 3):
 * los `<select required>` #campoTipoDocumento y #campoTipoCosto en
 * index.html ahora traen una primera opción vacía ("Seleccionar…"),
 * mismo patrón ya usado en el resto del proyecto (p. ej.
 * pages/compras/index.html, pages/sunat/index.html), en vez de traer
 * "Compra"/"Flete" preseleccionados sin que el usuario haya elegido
 * nada.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const elError = document.getElementById("estadoError");

  // ---- Costeo de compra ----
  const formCosteoCompra = document.getElementById("formCosteoCompra");
  const inputOrdenCompraId = document.getElementById("inputOrdenCompraId");
  const estadoCosteoCompra = document.getElementById("estadoCosteoCompra");
  const errorCosteoCompra = document.getElementById("errorCosteoCompra");
  const resultadoCosteoCompra = document.getElementById("resultadoCosteoCompra");
  const tbodyDetalleCosteoCompra = document.getElementById("tbodyDetalleCosteoCompra");

  // ---- Rentabilidad de exportación ----
  const formRentabilidad = document.getElementById("formRentabilidad");
  const inputDeclaracionId = document.getElementById("inputDeclaracionId");
  const estadoRentabilidad = document.getElementById("estadoRentabilidad");
  const errorRentabilidad = document.getElementById("errorRentabilidad");
  const resultadoRentabilidad = document.getElementById("resultadoRentabilidad");
  const tbodyDetalleRentabilidad = document.getElementById("tbodyDetalleRentabilidad");

  // ---- Registrar costo adicional ----
  const formCostoAdicional = document.getElementById("formCostoAdicional");
  const errorCostoAdicional = document.getElementById("errorCostoAdicional");
  const campoTipoDocumento = document.getElementById("campoTipoDocumento");
  const campoDocumentoId = document.getElementById("campoDocumentoId");
  const campoTipoCosto = document.getElementById("campoTipoCosto");
  const campoMonto = document.getElementById("campoMonto");
  const campoMoneda = document.getElementById("campoMoneda");
  const campoDescripcion = document.getElementById("campoDescripcion");

  // Última consulta de costeo/rentabilidad abierta, para saber si hay
  // que refrescarla después de registrar un costo adicional.
  let ultimaConsultaCosteo = null; // { ordenCompraId }
  let ultimaConsultaRentabilidad = null; // { declaracionId }

  function mostrarError(mensaje) {
    elError.textContent = mensaje;
    elError.style.display = "block";
  }

  function ocultarError() {
    elError.style.display = "none";
  }

  function mostrarErrorEn(el, mensaje) {
    el.textContent = mensaje;
    el.style.display = "block";
  }

  function ocultarErrorEn(el) {
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

  function pintarDetalleCostos(tbody, detalle) {
    tbody.innerHTML = detalle.length
      ? detalle
          .map(
            (c) => `
        <tr>
          <td>${U.escaparHtml(c.tipo_costo)}</td>
          <td>${U.escaparHtml(c.descripcion || "—")}</td>
          <td class="text-end">${U.formatearMoneda(c.monto, c.moneda)}</td>
          <td>${U.escaparHtml(c.moneda)}</td>
          <td>${U.formatearFechaHora(c.creado_en)}</td>
        </tr>`
          )
          .join("")
      : `<tr><td colspan="5" class="text-muted-erp">Sin costos adicionales registrados.</td></tr>`;
  }

  // ---------- Costeo de compra ----------
  async function consultarCosteoCompra(ev) {
    ev.preventDefault();
    ocultarError();
    ocultarErrorEn(errorCosteoCompra);
    const ordenCompraId = Number(inputOrdenCompraId.value);
    if (!ordenCompraId) return;

    resultadoCosteoCompra.style.display = "none";
    estadoCosteoCompra.style.display = "block";
    if (window.UI) window.UI.mostrarCargando();
    try {
      const costeo = await apiGet(`/api/costos/compras/${ordenCompraId}/costeo`);
      ultimaConsultaCosteo = { ordenCompraId };
      pintarCosteoCompra(costeo);
    } catch (err) {
      const mensaje = err.message || "No se pudo obtener el costeo de la compra.";
      mostrarErrorEn(errorCosteoCompra, mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
    } finally {
      estadoCosteoCompra.style.display = "none";
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function pintarCosteoCompra(costeo) {
    // CosteoCompraOut no trae campo "moneda" para sus totales (service.py
    // suma valor_mercaderia y monto de cada costo adicional tal cual, sin
    // convertir divisas), así que se muestran como número simple, sin
    // asumir una moneda que el Backend no informa.
    document.getElementById("kpiValorMercaderia").textContent = U.formatearNumero(costeo.valor_mercaderia, 2);
    document.getElementById("kpiCostosAdicCompra").textContent = U.formatearNumero(costeo.costos_adicionales, 2);
    document.getElementById("kpiCostoTotalCompra").textContent = U.formatearNumero(costeo.costo_total, 2);
    document.getElementById("kpiCostoUnitarioPonderado").textContent = U.formatearNumero(costeo.costo_unitario_ponderado, 4);
    document.getElementById("kpiCantidadTotalCompra").textContent = U.formatearNumero(costeo.cantidad_total, 2);
    pintarDetalleCostos(tbodyDetalleCosteoCompra, costeo.detalle_costos_adicionales || []);
    resultadoCosteoCompra.style.display = "block";
  }

  // ---------- Rentabilidad de exportación ----------
  async function consultarRentabilidad(ev) {
    ev.preventDefault();
    ocultarError();
    ocultarErrorEn(errorRentabilidad);
    const declaracionId = Number(inputDeclaracionId.value);
    if (!declaracionId) return;

    resultadoRentabilidad.style.display = "none";
    estadoRentabilidad.style.display = "block";
    if (window.UI) window.UI.mostrarCargando();
    try {
      const rentabilidad = await apiGet(`/api/costos/exportaciones/${declaracionId}/rentabilidad`);
      ultimaConsultaRentabilidad = { declaracionId };
      pintarRentabilidad(rentabilidad);
    } catch (err) {
      const mensaje = err.message || "No se pudo obtener la rentabilidad de la exportación.";
      mostrarErrorEn(errorRentabilidad, mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
    } finally {
      estadoRentabilidad.style.display = "none";
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function pintarRentabilidad(r) {
    // RentabilidadExportacionOut tampoco trae "moneda" para sus totales
    // (mismo motivo que en costeo de compra): número simple, no moneda.
    document.getElementById("kpiIngresoExportacion").textContent = U.formatearNumero(r.ingreso_exportacion, 2);
    document.getElementById("kpiCostoMercaderiaReal").textContent = U.formatearNumero(r.costo_mercaderia_real, 2);
    document.getElementById("kpiCostosAdicExport").textContent = U.formatearNumero(r.costos_adicionales, 2);
    document.getElementById("kpiUtilidadBruta").textContent = U.formatearNumero(r.utilidad_bruta, 2);
    document.getElementById("kpiMargenPct").textContent = U.formatearPorcentaje(r.margen_pct, 1);
    pintarDetalleCostos(tbodyDetalleRentabilidad, r.detalle_costos_adicionales || []);
    resultadoRentabilidad.style.display = "block";
  }

  // ---------- Registrar costo adicional ----------
  function limpiarFormularioCostoAdicional() {
    formCostoAdicional.reset();
    campoMoneda.value = "USD";
    ocultarErrorEn(errorCostoAdicional);
  }

  async function registrarCostoAdicional(ev) {
    ev.preventDefault();
    ocultarErrorEn(errorCostoAdicional);

    const datos = {
      tipo_documento: campoTipoDocumento.value,
      documento_id: Number(campoDocumentoId.value),
      tipo_costo: campoTipoCosto.value,
      descripcion: campoDescripcion.value || null,
      monto: Number(campoMonto.value),
      moneda: campoMoneda.value.toUpperCase(),
    };

    if (window.UI) window.UI.mostrarCargando();
    try {
      await apiPost("/api/costos/adicionales", datos);

      // Si la consulta de costeo/rentabilidad visible corresponde al
      // mismo documento, se refresca para mostrar el costo recién
      // agregado. No se toca la otra consulta si no coincide.
      if (
        datos.tipo_documento === "COMPRA" &&
        ultimaConsultaCosteo &&
        ultimaConsultaCosteo.ordenCompraId === datos.documento_id
      ) {
        const costeo = await apiGet(`/api/costos/compras/${datos.documento_id}/costeo`);
        pintarCosteoCompra(costeo);
      }
      if (
        datos.tipo_documento === "EXPORTACION" &&
        ultimaConsultaRentabilidad &&
        ultimaConsultaRentabilidad.declaracionId === datos.documento_id
      ) {
        const rentabilidad = await apiGet(`/api/costos/exportaciones/${datos.documento_id}/rentabilidad`);
        pintarRentabilidad(rentabilidad);
      }

      limpiarFormularioCostoAdicional();
      if (window.UI) window.UI.toast("Costo adicional registrado correctamente.", "success");
    } catch (err) {
      const mensaje = err.message || "No se pudo registrar el costo adicional.";
      mostrarErrorEn(errorCostoAdicional, mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    formCosteoCompra.addEventListener("submit", consultarCosteoCompra);
    formRentabilidad.addEventListener("submit", consultarRentabilidad);
    formCostoAdicional.addEventListener("submit", registrarCostoAdicional);
  }

  iniciar();
})();
