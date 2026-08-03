/**
 * pages/moneda/moneda.js — Page-script del módulo m09_moneda
 * (app/modules/m09_moneda).
 *
 * Endpoints (contrato real: router.py + schemas.py), todos con Bearer:
 *   POST /api/moneda/tipos-cambio
 *        body TipoCambioCrear -> TipoCambioOut (201)
 *   GET  /api/moneda/tipos-cambio/{moneda_origen}/{moneda_destino}
 *        -> list[TipoCambioOut]                         (historial del par)
 *   GET  /api/moneda/tipos-cambio/{moneda_origen}/{moneda_destino}/vigente?fecha=
 *        -> TipoCambioVigenteOut                         (default fecha: hoy)
 *   GET  /api/moneda/convertir?monto&moneda_origen&moneda_destino&fecha=
 *        -> ConversionOut                                (default fecha: hoy)
 *
 * TipoCambioCrear: moneda_origen, moneda_destino (ambos 3 letras),
 * fecha, valor (>0, unidades de destino por 1 de origen). Si ya existe
 * un tipo de cambio para ese par+fecha, service.py lo actualiza en vez
 * de duplicarlo (registrar_tipo_cambio hace upsert); por eso el texto
 * de ayuda del formulario lo aclara y no hay botón "editar" aparte.
 *
 * "/vigente" busca primero el par directo y, si no existe, el inverso
 * (1/valor) según service._buscar_vigente_directo_o_inverso; el campo
 * "invertido" de TipoCambioVigenteOut indica cuál de los dos casos
 * ocurrió, y esta página lo muestra tal cual lo informa el Backend.
 * Si moneda_origen == moneda_destino, el Backend responde valor=1.0
 * sin consultar la tabla (no hace falta que el par exista registrado).
 *
 * El historial (GET /tipos-cambio/{origen}/{destino}) no acepta
 * parámetro de fecha ni orden: se pinta tal como llega y se ordena en
 * el cliente por fecha descendente solo para lectura (no se inventa un
 * parámetro de orden que el Backend no tiene).
 *
 * No hay conexión a ninguna API externa de tipos de cambio: todo sale
 * del Backend propio (tabla tipos_cambio), como pide la consigna.
 *
 * FASE F15 — Corrección de deuda técnica (hallazgo F14 #1): se integra
 * UI.mostrarCargando()/UI.ocultarCargando()/UI.toast() (ausentes hasta
 * ahora en este módulo, mismo patrón ya aplicado en F10-F13). No se
 * modifica ninguna conversión ni endpoint.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const elError = document.getElementById("estadoError");

  // ---- Consulta de par (historial + vigente) ----
  const formConsultaPar = document.getElementById("formConsultaPar");
  const inputParOrigen = document.getElementById("inputParOrigen");
  const inputParDestino = document.getElementById("inputParDestino");
  const inputParFecha = document.getElementById("inputParFecha");
  const estadoConsultaPar = document.getElementById("estadoConsultaPar");
  const errorConsultaPar = document.getElementById("errorConsultaPar");
  const resultadoVigente = document.getElementById("resultadoVigente");
  const kpiValorVigente = document.getElementById("kpiValorVigente");
  const detalleVigente = document.getElementById("detalleVigente");
  const tbodyHistorial = document.getElementById("tbodyHistorial");

  // ---- Conversor ----
  const formConvertir = document.getElementById("formConvertir");
  const inputMonto = document.getElementById("inputMonto");
  const inputConvOrigen = document.getElementById("inputConvOrigen");
  const inputConvDestino = document.getElementById("inputConvDestino");
  const inputConvFecha = document.getElementById("inputConvFecha");
  const estadoConvertir = document.getElementById("estadoConvertir");
  const errorConvertir = document.getElementById("errorConvertir");
  const resultadoConvertir = document.getElementById("resultadoConvertir");
  const kpiMontoConvertido = document.getElementById("kpiMontoConvertido");
  const detalleConversion = document.getElementById("detalleConversion");

  // ---- Registrar tipo de cambio ----
  const formTipoCambio = document.getElementById("formTipoCambio");
  const errorTipoCambio = document.getElementById("errorTipoCambio");
  const campoMonedaOrigen = document.getElementById("campoMonedaOrigen");
  const campoMonedaDestino = document.getElementById("campoMonedaDestino");
  const campoFecha = document.getElementById("campoFecha");
  const campoValor = document.getElementById("campoValor");

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

  // ---------- Consulta de par: historial + vigente ----------
  async function consultarPar(ev) {
    ev.preventDefault();
    ocultarError();
    ocultarErrorEn(errorConsultaPar);
    const origen = inputParOrigen.value.trim().toUpperCase();
    const destino = inputParDestino.value.trim().toUpperCase();
    if (!origen || !destino) return;

    resultadoVigente.style.display = "none";
    estadoConsultaPar.style.display = "block";
    if (window.UI) window.UI.mostrarCargando();
    try {
      const qsFecha = inputParFecha.value ? `?fecha=${inputParFecha.value}` : "";
      const [historial, vigente] = await Promise.all([
        apiGet(`/api/moneda/tipos-cambio/${origen}/${destino}`),
        apiGet(`/api/moneda/tipos-cambio/${origen}/${destino}/vigente${qsFecha}`),
      ]);
      pintarHistorial(historial);
      pintarVigente(vigente);
    } catch (err) {
      const mensaje = err.message || "No se pudo consultar el par de monedas.";
      mostrarErrorEn(errorConsultaPar, mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
      tbodyHistorial.innerHTML = `<tr><td colspan="3" class="text-muted-erp">Sin datos.</td></tr>`;
    } finally {
      estadoConsultaPar.style.display = "none";
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function pintarHistorial(historial) {
    const ordenado = [...historial].sort((a, b) => (a.fecha < b.fecha ? 1 : -1));
    tbodyHistorial.innerHTML = ordenado.length
      ? ordenado
          .map(
            (h) => `
        <tr>
          <td>${U.formatearFecha(h.fecha)}</td>
          <td class="text-end">${U.formatearNumero(h.valor, 6)}</td>
          <td>${U.formatearFechaHora(h.creado_en)}</td>
        </tr>`
          )
          .join("")
      : `<tr><td colspan="3" class="text-muted-erp">No hay tipos de cambio registrados para este par.</td></tr>`;
  }

  function pintarVigente(vigente) {
    kpiValorVigente.textContent = U.formatearNumero(vigente.valor, 6);
    const partes = [
      `${vigente.moneda_origen} → ${vigente.moneda_destino}`,
      `vigente al ${U.formatearFecha(vigente.fecha_tipo_cambio)}`,
    ];
    if (vigente.fecha_solicitada !== vigente.fecha_tipo_cambio) {
      partes.push(`(solicitado: ${U.formatearFecha(vigente.fecha_solicitada)})`);
    }
    if (vigente.invertido) {
      partes.push("— calculado como inverso del par registrado");
    }
    detalleVigente.textContent = partes.join(" ");
    resultadoVigente.style.display = "block";
  }

  // ---------- Conversor ----------
  async function convertir(ev) {
    ev.preventDefault();
    ocultarError();
    ocultarErrorEn(errorConvertir);
    resultadoConvertir.style.display = "none";

    const monto = Number(inputMonto.value);
    const origen = inputConvOrigen.value.trim().toUpperCase();
    const destino = inputConvDestino.value.trim().toUpperCase();
    if (!monto || !origen || !destino) return;

    const params = new URLSearchParams({
      monto: String(monto),
      moneda_origen: origen,
      moneda_destino: destino,
    });
    if (inputConvFecha.value) params.set("fecha", inputConvFecha.value);

    estadoConvertir.style.display = "block";
    if (window.UI) window.UI.mostrarCargando();
    try {
      const resultado = await apiGet(`/api/moneda/convertir?${params.toString()}`);
      kpiMontoConvertido.textContent = `${U.formatearNumero(resultado.monto_convertido, 2)} ${resultado.moneda_destino}`;
      detalleConversion.textContent =
        `Tipo de cambio aplicado: ${U.formatearNumero(resultado.tipo_cambio_aplicado, 6)} ` +
        `(vigente al ${U.formatearFecha(resultado.fecha_tipo_cambio)})`;
      resultadoConvertir.style.display = "block";
    } catch (err) {
      const mensaje = err.message || "No se pudo realizar la conversión.";
      mostrarErrorEn(errorConvertir, mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
    } finally {
      estadoConvertir.style.display = "none";
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Registrar tipo de cambio ----------
  async function registrarTipoCambio(ev) {
    ev.preventDefault();
    ocultarErrorEn(errorTipoCambio);

    const datos = {
      moneda_origen: campoMonedaOrigen.value.trim().toUpperCase(),
      moneda_destino: campoMonedaDestino.value.trim().toUpperCase(),
      fecha: campoFecha.value,
      valor: Number(campoValor.value),
    };

    if (window.UI) window.UI.mostrarCargando();
    try {
      await apiPost("/api/moneda/tipos-cambio", datos);
      formTipoCambio.reset();
      if (window.UI) window.UI.toast("Tipo de cambio registrado correctamente.", "success");

      // Si el par recién registrado coincide con el que está mostrando
      // el panel de consulta, se refresca para reflejar el cambio.
      if (
        inputParOrigen.value.trim().toUpperCase() === datos.moneda_origen &&
        inputParDestino.value.trim().toUpperCase() === datos.moneda_destino
      ) {
        formConsultaPar.dispatchEvent(new Event("submit"));
      }
    } catch (err) {
      const mensaje = err.message || "No se pudo registrar el tipo de cambio.";
      mostrarErrorEn(errorTipoCambio, mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    formConsultaPar.addEventListener("submit", consultarPar);
    formConvertir.addEventListener("submit", convertir);
    formTipoCambio.addEventListener("submit", registrarTipoCambio);
  }

  iniciar();
})();
