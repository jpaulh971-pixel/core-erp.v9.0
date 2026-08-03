/**
 * utils.js — Utilidades genéricas de formato para el Frontend de Core ERP.
 *
 * Sigue el mismo criterio de formato que ya usan los scripts de página
 * (balanced_scorecard.js, lean_six_sigma.js, theory_of_constraints.js,
 * reportes.js, dashboard.js, inventario.js, etc.): locale "es-PE".
 *
 * FASE — Corrección de presentación de moneda: `formatearMoneda()` ya
 * NO usa "PEN" como moneda fija. Cuando no se pasa `moneda` explícita
 * (caso de KPIs/totales agregados que no tienen una moneda propia por
 * registro), usa `window.ERP_MONEDA_BASE`, que carga moneda-config.js
 * una sola vez por sesión desde MONEDA_BASE (GET
 * /api/configuracion/parametros). Si esa variable todavía no está
 * disponible, el único fallback permitido es "USD" (nunca "PEN"). Las
 * pantallas que ya pasan su propia moneda por registro (`c.moneda`,
 * `o.moneda`, `decl.moneda`, etc.) no cambian: ese argumento explícito
 * sigue teniendo prioridad, tal como antes.
 */
(function () {
  function formatearNumero(valor, decimales) {
    if (valor === null || valor === undefined || Number.isNaN(Number(valor))) return "—";
    return Number(valor).toLocaleString("es-PE", {
      minimumFractionDigits: decimales ?? 0,
      maximumFractionDigits: decimales ?? 2,
    });
  }

  function formatearMoneda(valor, moneda) {
    if (valor === null || valor === undefined || Number.isNaN(Number(valor))) return "—";
    // Prioridad: moneda explícita del registro (si se pasó) > moneda
    // base configurada en el sistema (window.ERP_MONEDA_BASE, cargada
    // por moneda-config.js desde MONEDA_BASE) > "USD" como último
    // fallback si esa variable aún no respondió. Nunca "PEN" fijo.
    return Number(valor).toLocaleString("es-PE", {
      style: "currency",
      currency: moneda || window.ERP_MONEDA_BASE || "USD",
    });
  }

  function formatearPorcentaje(valor, decimales) {
    if (valor === null || valor === undefined || Number.isNaN(Number(valor))) return "—";
    return `${formatearNumero(valor, decimales ?? 1)}%`;
  }

  function formatearFecha(valor) {
    if (!valor) return "—";
    const fecha = new Date(valor);
    if (Number.isNaN(fecha.getTime())) return "—";
    return fecha.toLocaleDateString("es-PE");
  }

  function formatearFechaHora(valor) {
    if (!valor) return "—";
    const fecha = new Date(valor);
    if (Number.isNaN(fecha.getTime())) return "—";
    return fecha.toLocaleString("es-PE");
  }

  function escaparHtml(texto) {
    if (texto === null || texto === undefined) return "";
    return String(texto)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function debounce(fn, esperaMs) {
    let temporizador = null;
    return function debounced(...args) {
      clearTimeout(temporizador);
      temporizador = setTimeout(() => fn.apply(this, args), esperaMs ?? 300);
    };
  }

  window.Utils = {
    formatearNumero,
    formatearMoneda,
    formatearPorcentaje,
    formatearFecha,
    formatearFechaHora,
    escaparHtml,
    debounce,
  };
})();
