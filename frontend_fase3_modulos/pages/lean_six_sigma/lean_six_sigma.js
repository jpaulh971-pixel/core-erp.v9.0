/**
 * pages/lean_six_sigma/lean_six_sigma.js — Page-script del módulo
 * m15_lean_six_sigma (app/modules/m15_lean_six_sigma).
 *
 * Endpoints (contrato_api_modulos.md, sección 2), todos con Bearer:
 *   GET /api/lean-six-sigma/mermas?desde&hasta
 *     -> ResumenMermas { ..., dpmo, nivel_sigma, top_productos[] }
 *   GET /api/lean-six-sigma/tiempos-ciclo/compras?desde&hasta
 *     -> TiemposCicloCompras (puede traer todos los dias_* en null si
 *        no hay órdenes evaluadas en el rango)
 *   GET /api/lean-six-sigma/tiempos-ciclo/ventas?desde&hasta
 *     -> TiemposCicloVentas
 *
 * El módulo mide en solo lectura Inventario (kardex), Compras y Ventas;
 * no tiene tabla propia salvo el top de productos con mermas que ya
 * entrega /mermas (top_productos[]).
 *
 * FASE F12 — Verificación de contrato y limitaciones documentadas:
 * - No se recibió el .zip del Backend adjunto a este encargo (igual que
 *   en F8/F9/F10/F11). El contrato de `m15_lean_six_sigma` se verificó a
 *   partir de este mismo archivo (heredado desde F0, con las 3 rutas,
 *   parámetros `desde`/`hasta` y forma de cada respuesta ya
 *   documentadas con cita a `contrato_api_modulos.md`, sección 2) y de
 *   una revisión cruzada del proyecto (`grep -rn "exportar|excel|export"
 *   pages/`) que confirma que este módulo no consume ningún endpoint de
 *   exportación — mismo hallazgo ya reportado en F8, F9, F10 y F11 para
 *   sus respectivos módulos. Si en una fase futura se dispone del .zip
 *   real del Backend, se recomienda re-verificar
 *   router.py/schemas.py/service.py/models.py de `m15_lean_six_sigma`
 *   directamente antes de asumir que las limitaciones aquí documentadas
 *   siguen vigentes.
 * - Solo existen los 3 GET listados arriba en este módulo. No hay ningún
 *   endpoint de escritura (POST/PUT/DELETE): es 100% de solo lectura
 *   (mide kardex/compras/ventas ya registrados en otros módulos), por lo
 *   que no corresponde `UI.confirmar()` (no hay ninguna acción que
 *   modifique información).
 * - No existe ningún endpoint de exportación a Excel/PDF, ni gráficos,
 *   KPIs, tiempos de ciclo adicionales ni filtros distintos a
 *   `desde`/`hasta`. No se agregan pantallas, indicadores ni parámetros
 *   que el Backend no entregue.
 * - `/mermas` sí entrega una lista (`top_productos[]`), a diferencia de
 *   `m18_balanced_scorecard` (F11): por eso, y solo para esa tabla, F12
 *   agrega el badge `countTopMermas` con la cantidad de filas devueltas,
 *   mismo patrón ya usado en `pages/reportes/` (F8),
 *   `pages/inteligencia_comercial/` (F9) e
 *   `pages/inteligencia_tributaria/` (F10). Las respuestas de
 *   `/tiempos-ciclo/compras` y `/tiempos-ciclo/ventas` son objetos
 *   agregados sin listas, así que no aplica ningún badge a esas tarjetas.
 * - F12 agrega la integración de `UI.toast()`/`UI.mostrarCargando()`/
 *   `UI.ocultarCargando()` (ausente hasta ahora en este módulo, mismo
 *   patrón ya aplicado en F8/F9/F10/F11) y validación de rango de fechas,
 *   sin tocar ningún endpoint ni inventar ningún filtro/KPI/gráfico
 *   nuevo.
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

  function marcarInvalido(input, invalido) {
    input.classList.toggle("is-invalid", !!invalido);
  }

  // Validación en el cliente: ambas fechas son opcionales, pero si están
  // las dos, "Desde" no puede ser posterior a "Hasta". Mismo patrón ya
  // aplicado en F8 (pages/reportes/), F9 (pages/inteligencia_comercial/),
  // F10 (pages/inteligencia_tributaria/) y F11 (pages/balanced_scorecard/).
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

  function diasOTexto(valor) {
    return valor === null || valor === undefined ? "—" : `${U.formatearNumero(valor, 1)} días`;
  }

  async function cargarMermas(params) {
    const r = await apiGet("/api/lean-six-sigma/mermas", params);
    document.getElementById("kpiMovimientos").textContent = U.formatearNumero(r.total_movimientos_kardex);
    document.getElementById("kpiEventos").textContent = U.formatearNumero(r.total_eventos_merma);
    document.getElementById("kpiCantidadMermada").textContent = U.formatearNumero(r.cantidad_total_mermada, 2);
    document.getElementById("kpiDpmo").textContent = U.formatearNumero(r.dpmo, 1);
    document.getElementById("kpiSigma").textContent = U.formatearNumero(r.nivel_sigma, 2);

    const tbody = document.getElementById("tbodyTopMermas");
    tbody.innerHTML = r.top_productos.length
      ? r.top_productos
          .map(
            (p) => `
        <tr>
          <td><code>${U.escaparHtml(p.codigo)}</code></td>
          <td>${U.escaparHtml(p.nombre)}</td>
          <td class="text-end">${U.formatearNumero(p.eventos)}</td>
          <td class="text-end">${U.formatearNumero(p.cantidad_mermada, 2)}</td>
        </tr>`
          )
          .join("")
      : `<tr><td colspan="4" class="text-muted-erp">Sin eventos de merma en el periodo.</td></tr>`;
    document.getElementById("countTopMermas").textContent = `(${U.formatearNumero(r.top_productos.length)})`;
  }

  async function cargarTiemposCompras(params) {
    const r = await apiGet("/api/lean-six-sigma/tiempos-ciclo/compras", params);
    document.getElementById("comprasOrdenes").textContent = U.formatearNumero(r.ordenes_evaluadas);
    document.getElementById("comprasDiasTotal").textContent = diasOTexto(r.dias_promedio_total);
    document.getElementById("comprasSolAprob").textContent = diasOTexto(r.dias_promedio_solicitud_a_aprobacion);
    document.getElementById("comprasAprobRecep").textContent = diasOTexto(r.dias_promedio_aprobacion_a_recepcion);
    document.getElementById("comprasDiasMin").textContent = diasOTexto(r.dias_min_total);
    document.getElementById("comprasDiasMax").textContent = diasOTexto(r.dias_max_total);
  }

  async function cargarTiemposVentas(params) {
    const r = await apiGet("/api/lean-six-sigma/tiempos-ciclo/ventas", params);
    document.getElementById("ventasOrdenes").textContent = U.formatearNumero(r.ordenes_evaluadas);
    document.getElementById("ventasConfDesp").textContent = diasOTexto(r.dias_promedio_confirmacion_a_despacho);
    document.getElementById("ventasDiasMin").textContent = diasOTexto(r.dias_min);
    document.getElementById("ventasDiasMax").textContent = diasOTexto(r.dias_max);
  }

  async function cargarTodo() {
    ocultarError();
    if (!filtrosValidos()) return; // Rango de fechas inconsistente: no se envía ninguna solicitud.

    btnAplicar.disabled = true;
    if (window.UI) window.UI.mostrarCargando();
    try {
      const params = { desde: inputDesde.value || undefined, hasta: inputHasta.value || undefined };
      await Promise.all([
        cargarMermas(params),
        cargarTiemposCompras(params),
        cargarTiemposVentas(params),
      ]);
    } catch (err) {
      const mensaje = err.message || "Ocurrió un error al cargar los indicadores de Lean Six Sigma.";
      mostrarError(mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
    } finally {
      btnAplicar.disabled = false;
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return;
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
