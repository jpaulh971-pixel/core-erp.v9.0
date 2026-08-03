/**
 * pages/balanced_scorecard/balanced_scorecard.js — Page-script del
 * módulo m18_balanced_scorecard (app/modules/m18_balanced_scorecard).
 *
 * Usa el endpoint combinado recomendado por el contrato
 * (contrato_api_modulos.md, sección 1) en vez de 4 llamadas sueltas:
 *   GET /api/balanced-scorecard/tablero?desde&hasta -> TableroBalancedScorecard
 *     { desde, hasta, financiera, clientes, procesos_internos, aprendizaje_crecimiento }
 *
 * El módulo no tiene tabla propia (agrega en solo lectura Ventas, Costos,
 * Inventario, Clientes, Proveedores, Productos, Lean Six Sigma y Theory
 * of Constraints), así que este script solo pinta lo que el tablero ya
 * calcula: no inventa campos ni ratios adicionales.
 *
 * FASE F11 — Verificación de contrato y limitaciones documentadas:
 * - No se recibió el .zip del Backend adjunto a este encargo (igual que
 *   en F8/F9/F10). El contrato de `m18_balanced_scorecard` se verificó a
 *   partir de este mismo archivo (heredado desde F0, con la ruta y forma
 *   de la respuesta ya documentadas) y de una revisión cruzada del
 *   proyecto (`grep -rn "exportar|excel|export" pages/`) que confirma que
 *   este módulo no consume ningún endpoint de exportación. Si en una fase
 *   futura se dispone del .zip real del Backend, se recomienda
 *   re-verificar router.py/schemas.py/service.py/models.py de
 *   `m18_balanced_scorecard` directamente antes de asumir que las
 *   limitaciones aquí documentadas siguen vigentes.
 * - Solo existe el GET listado arriba en este módulo. No hay ningún
 *   endpoint de escritura (POST/PUT/DELETE): es 100% de solo lectura
 *   (agregación de otros módulos), por lo que no corresponde
 *   `UI.confirmar()` (no hay ninguna acción que modifique información).
 * - No existe ningún endpoint de exportación a Excel/PDF, ni gráficos,
 *   KPIs o filtros adicionales a `desde`/`hasta`. No se agregan pantallas,
 *   indicadores ni parámetros que el Backend no entregue.
 * - El módulo no expone ninguna tabla/listado (el tablero devuelve un
 *   objeto agregado por perspectiva, no arreglos de filas), por lo que no
 *   corresponde el badge de "cantidad de registros" usado en
 *   pages/reportes/, pages/inteligencia_comercial/ e
 *   pages/inteligencia_tributaria/ (esos módulos sí devuelven listas).
 * - La perspectiva "Aprendizaje y crecimiento" no acepta `desde`/`hasta`
 *   en el Backend (es una foto del catálogo activo, no una serie por
 *   periodo); ese comportamiento ya estaba documentado en el HTML desde
 *   F0 y no se modificó.
 * - F11 agrega la integración de `UI.toast()`/`UI.mostrarCargando()`/
 *   `UI.ocultarCargando()` (ausente hasta ahora en este módulo, mismo
 *   patrón ya aplicado en F8/F9/F10) y validación de rango de fechas, sin
 *   tocar el endpoint ni inventar ningún filtro/KPI/gráfico nuevo.
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
  // aplicado en F8 (pages/reportes/), F9 (pages/inteligencia_comercial/)
  // y F10 (pages/inteligencia_tributaria/).
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

  function pintarFinanciera(f) {
    document.getElementById("finIngreso").textContent = U.formatearMoneda(f.ingreso_ventas_despachadas);
    document.getElementById("finCosto").textContent = U.formatearMoneda(f.costo_mercaderia_vendida);
    document.getElementById("finCostosAd").textContent = U.formatearMoneda(f.costos_adicionales_operacion);
    document.getElementById("finUtilidad").textContent = U.formatearMoneda(f.utilidad_neta);
    document.getElementById("finMargen").textContent = U.formatearPorcentaje(f.margen_neto_pct);
  }

  function pintarClientes(c) {
    document.getElementById("cliActivos").textContent = U.formatearNumero(c.clientes_activos_total);
    document.getElementById("cliConCompra").textContent = U.formatearNumero(c.clientes_con_compra_en_periodo);
    document.getElementById("cliPct").textContent = U.formatearPorcentaje(c.pct_clientes_activos_con_compra);
    document.getElementById("cliTicket").textContent = U.formatearMoneda(c.ticket_promedio_venta);
    document.getElementById("cliConcentracion").textContent = U.formatearPorcentaje(c.concentracion_top3_clientes_pct);
  }

  function pintarProcesosInternos(p) {
    document.getElementById("procDpmo").textContent = U.formatearNumero(p.dpmo_mermas, 1);
    document.getElementById("procSigma").textContent = U.formatearNumero(p.nivel_sigma, 2);
    document.getElementById("procCicloCompras").textContent =
      p.dias_promedio_ciclo_compras === null ? "—" : `${U.formatearNumero(p.dias_promedio_ciclo_compras, 1)} días`;
    document.getElementById("procCicloVentas").textContent =
      p.dias_promedio_ciclo_ventas === null ? "—" : `${U.formatearNumero(p.dias_promedio_ciclo_ventas, 1)} días`;
    document.getElementById("procRestriccion").textContent = U.formatearNumero(p.productos_en_restriccion_stock);
  }

  function pintarAprendizajeCrecimiento(a) {
    document.getElementById("apreProductos").textContent = U.formatearNumero(a.productos_activos_total);
    document.getElementById("apreProveedores").textContent = U.formatearNumero(a.proveedores_activos_total);
    document.getElementById("apreSinMovimiento").textContent = U.formatearNumero(a.productos_sin_movimiento);
  }

  async function cargarTablero() {
    ocultarError();
    if (!filtrosValidos()) return; // Rango de fechas inconsistente: no se envía ninguna solicitud.

    btnAplicar.disabled = true;
    if (window.UI) window.UI.mostrarCargando();
    try {
      const params = { desde: inputDesde.value || undefined, hasta: inputHasta.value || undefined };
      const tablero = await apiGet("/api/balanced-scorecard/tablero", params);
      pintarFinanciera(tablero.financiera);
      pintarClientes(tablero.clientes);
      pintarProcesosInternos(tablero.procesos_internos);
      pintarAprendizajeCrecimiento(tablero.aprendizaje_crecimiento);
    } catch (err) {
      mostrarError(err.message || "Ocurrió un error al cargar el tablero.");
      if (window.UI) window.UI.toast(err.message || "Ocurrió un error al cargar el tablero.", "error");
    } finally {
      btnAplicar.disabled = false;
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return;
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    btnAplicar.addEventListener("click", cargarTablero);
    [inputDesde, inputHasta].forEach((input) =>
      input.addEventListener("change", () => {
        marcarInvalido(inputDesde, false);
        marcarInvalido(inputHasta, false);
      })
    );
    cargarTablero();
  }

  iniciar();
})();
