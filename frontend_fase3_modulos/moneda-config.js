/**
 * moneda-config.js — Moneda base del ERP, para presentación en el Frontend.
 *
 * FASE — Corrección de presentación de moneda.
 *
 * Motivo: `utils.js` (`formatearMoneda`) usaba `"PEN"` como moneda fija
 * cada vez que un page-script pedía formatear un monto sin indicar su
 * propia moneda (KPIs/totales agregados, que no tienen moneda por
 * registro). Este archivo reemplaza ese valor fijo por el parámetro
 * `MONEDA_BASE` que ya existe en el Backend (app/modules/m20_configuracion,
 * tabla `parametros_sistema`, mismo parámetro que ya usa
 * m08_costos/service.py para convertir costos adicionales).
 *
 * Qué hace:
 *   1. Deja `window.ERP_MONEDA_BASE = "USD"` de inmediato (fallback
 *      temporal síncrono, nunca "PEN", por si algún formateo ocurre
 *      antes de que responda la API).
 *   2. Si hay sesión iniciada, consulta UNA sola vez
 *      GET /api/configuracion/parametros (Bearer; mismo endpoint que ya
 *      usa pages/configuracion/configuracion.js) y busca la fila con
 *      clave "MONEDA_BASE".
 *   3. Si la encuentra, sobrescribe `window.ERP_MONEDA_BASE` con su
 *      `valor` (en mayúsculas). El resultado queda cacheado en memoria
 *      para el resto de la página: no se vuelve a pedir.
 *   4. Si no hay sesión, si la llamada falla, o si el parámetro no
 *      existe todavía en la base de datos, se conserva el fallback
 *      "USD" del paso 1 (nunca "PEN").
 *
 * No crea endpoints nuevos, no modifica el Backend, no toca m09_moneda
 * (tipos de cambio) ni ninguna lógica de negocio: es solo la fuente
 * centralizada que consulta utils.js para saber qué moneda mostrar
 * cuando un valor no trae la suya propia.
 *
 * Debe cargarse DESPUÉS de config.js, auth.js y api-client.js (usa
 * `window.Auth` y `window.Api`) y ANTES de layout.js y cualquier
 * page-script, mismo patrón ya usado por esos archivos.
 */
(function () {
  // Fallback síncrono inmediato: nunca "PEN". Si todo lo demás falla,
  // el ERP sigue mostrando USD, que es la moneda real de trabajo del
  // cliente (ver seed.py: MONEDA_BASE = "USD" por defecto).
  window.ERP_MONEDA_BASE = "USD";

  const CONFIG = window.ERP_CONFIG;
  if (!CONFIG) {
    console.error("moneda-config.js: window.ERP_CONFIG no está definido. Carga config.js antes que moneda-config.js.");
    return;
  }

  async function cargarMonedaBase() {
    if (!window.Auth || !window.Auth.haySesion()) return; // login.html u otra página sin sesión: nada que consultar.
    if (!window.Api) {
      console.error("moneda-config.js: window.Api no está definido. Carga api-client.js antes que moneda-config.js.");
      return;
    }

    try {
      const parametros = await window.Api.get("/api/configuracion/parametros");
      const parametroMoneda = (parametros || []).find((p) => p.clave === "MONEDA_BASE");
      if (parametroMoneda && parametroMoneda.valor) {
        window.ERP_MONEDA_BASE = String(parametroMoneda.valor).trim().toUpperCase();
      }
      // Si el parámetro no existe todavía en parametros_sistema, se
      // conserva el fallback "USD" ya asignado arriba.
    } catch (err) {
      // Backend caído, sin red, o sesión vencida (Api.get ya cierra
      // sesión sola en un 401): se conserva "USD" como fallback. No se
      // interrumpe la carga de la página por esto.
      console.error("moneda-config.js: no se pudo obtener MONEDA_BASE desde /api/configuracion/parametros. Se usa USD como fallback.", err);
    }
  }

  cargarMonedaBase();
})();
