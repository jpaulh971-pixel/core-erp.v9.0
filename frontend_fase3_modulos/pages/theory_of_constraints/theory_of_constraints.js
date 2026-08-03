/**
 * pages/theory_of_constraints/theory_of_constraints.js — Page-script del
 * módulo m16_theory_of_constraints (app/modules/m16_theory_of_constraints).
 *
 * Endpoints (contrato_api_modulos.md, sección 3), todos con Bearer:
 *   GET /api/theory-of-constraints/contabilidad-throughput?desde&hasta
 *     -> ContabilidadThroughput (KPIs superiores, objeto agregado)
 *   GET /api/theory-of-constraints/restricciones-stock (sin params)
 *     -> list[RestriccionProducto]
 *   GET /api/theory-of-constraints/ordenes-en-espera (sin params)
 *     -> list[OrdenEnEspera]
 *
 * restricciones-stock y ordenes-en-espera no aceptan desde/hasta (el
 * Backend no los define): se recargan junto con el resto al pulsar
 * "Aplicar" solo por consistencia visual, no porque el filtro les
 * aplique.
 *
 * FASE F13 — Verificación de contrato y limitaciones documentadas:
 * - No se recibió el .zip del Backend adjunto a este encargo (igual que
 *   en F8/F9/F10/F11/F12). El contrato de `m16_theory_of_constraints` se
 *   verificó a partir de este mismo archivo (heredado desde F0, con las
 *   3 rutas y forma de cada respuesta ya documentadas con cita a
 *   `contrato_api_modulos.md`, sección 3) y de una revisión cruzada del
 *   proyecto (`grep -rn "exportar|excel|export" pages/`) que confirma que
 *   este módulo no consume ningún endpoint de exportación — mismo
 *   hallazgo ya reportado en F8, F9, F10, F11 y F12 para sus respectivos
 *   módulos. Si en una fase futura se dispone del .zip real del Backend,
 *   se recomienda re-verificar router.py/schemas.py/service.py/models.py
 *   de `m16_theory_of_constraints` directamente antes de asumir que las
 *   limitaciones aquí documentadas siguen vigentes.
 * - Solo existen los 3 GET listados arriba en este módulo. No hay ningún
 *   endpoint de escritura (POST/PUT/DELETE): es 100% de solo lectura
 *   (mide en tiempo real Ventas/Costos/Inventario ya registrados en otros
 *   módulos), por lo que no corresponde `UI.confirmar()` (no hay ninguna
 *   acción que modifique información).
 * - No existe ningún endpoint de exportación a Excel/PDF, ni gráficos,
 *   KPIs adicionales ni filtros distintos a `desde`/`hasta` (y este único
 *   parámetro solo aplica a `/contabilidad-throughput`; el Backend no
 *   define ningún parámetro para `/restricciones-stock` ni
 *   `/ordenes-en-espera`). No se agregan pantallas, indicadores ni
 *   parámetros que el Backend no entregue.
 * - `/restricciones-stock` y `/ordenes-en-espera` sí entregan listas, a
 *   diferencia de `/contabilidad-throughput` (objeto agregado sin lista):
 *   por eso F13 agrega los badges `countRestricciones` y
 *   `countOrdenesEspera` con la cantidad de filas devueltas por cada uno,
 *   mismo patrón ya usado en `pages/reportes/` (F8),
 *   `pages/inteligencia_comercial/` (F9), `pages/inteligencia_tributaria/`
 *   (F10) y `pages/lean_six_sigma/` (F12). No se agregó ningún badge a
 *   las tarjetas KPI de contabilidad de throughput porque esa respuesta
 *   es un objeto agregado sin lista (mismo criterio que
 *   `pages/balanced_scorecard/`, F11).
 * - F13 agrega la integración de `UI.toast()`/`UI.mostrarCargando()`/
 *   `UI.ocultarCargando()` (ausente hasta ahora en este módulo, mismo
 *   patrón ya aplicado en F8/F9/F10/F11/F12) y validación de rango de
 *   fechas, sin tocar ningún endpoint ni inventar ningún filtro/KPI/
 *   gráfico nuevo. Con esta fase quedan estandarizados todos los módulos
 *   de solo lectura del proyecto.
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
  // F10 (pages/inteligencia_tributaria/), F11 (pages/balanced_scorecard/)
  // y F12 (pages/lean_six_sigma/).
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

  async function cargarThroughput(params) {
    const r = await apiGet("/api/theory-of-constraints/contabilidad-throughput", params);
    document.getElementById("tocIngreso").textContent = U.formatearMoneda(r.ingreso_ventas_despachadas);
    document.getElementById("tocCosto").textContent = U.formatearMoneda(r.costo_mercaderia_vendida);
    document.getElementById("tocThroughput").textContent = U.formatearMoneda(r.throughput);
    document.getElementById("tocOpex").textContent = U.formatearMoneda(r.operating_expense);
    document.getElementById("tocUtilidad").textContent = U.formatearMoneda(r.utilidad_neta_toc);
    document.getElementById("tocInversion").textContent = U.formatearMoneda(r.inversion_inventario);
    document.getElementById("tocRoi").textContent = U.formatearPorcentaje(r.retorno_sobre_inversion_pct);
  }

  async function cargarRestriccionesStock() {
    const tbody = document.getElementById("tbodyRestricciones");
    try {
      const restricciones = await apiGet("/api/theory-of-constraints/restricciones-stock");
      tbody.innerHTML = restricciones.length
        ? restricciones
            .map(
              (p) => `
        <tr class="${p.es_restriccion ? "table-danger" : ""}">
          <td><code>${U.escaparHtml(p.codigo)}</code></td>
          <td>${U.escaparHtml(p.nombre)}</td>
          <td class="text-end">${U.formatearNumero(p.demanda_confirmada_pendiente, 2)}</td>
          <td class="text-end">${U.formatearNumero(p.stock_disponible, 2)}</td>
          <td class="text-end">${U.formatearNumero(p.deficit, 2)}</td>
        </tr>`
            )
            .join("")
        : `<tr><td colspan="5" class="text-muted-erp">No hay productos con restricción de stock.</td></tr>`;
      document.getElementById("countRestricciones").textContent = `(${U.formatearNumero(restricciones.length)})`;
    } catch (err) {
      // F14: antes esta sección se quedaba en "Cargando…" para siempre si
      // esta petición fallaba (Promise.all cortaba todo el bloque sin
      // volver a tocar este tbody). Ahora cada sección atrapa su propio
      // error y lo muestra en su lugar, y re-lanza para que cargarTodo()
      // igual muestre el aviso general arriba.
      tbody.innerHTML = `<tr><td colspan="5" class="text-danger">No se pudo cargar: ${U.escaparHtml(err.message || "error desconocido")}</td></tr>`;
      throw err;
    }
  }

  async function cargarOrdenesEnEspera() {
    const tbody = document.getElementById("tbodyOrdenesEspera");
    try {
      const ordenes = await apiGet("/api/theory-of-constraints/ordenes-en-espera");
      tbody.innerHTML = ordenes.length
        ? ordenes
            .map(
              (o) => `
        <tr>
          <td>${U.escaparHtml(o.cliente_razon_social)}</td>
          <td>${U.formatearFechaHora(o.confirmado_en)}</td>
          <td class="text-end">${o.dias_esperando === null ? "—" : U.formatearNumero(o.dias_esperando, 1)}</td>
          <td class="text-end">${U.formatearMoneda(o.monto_estimado)}</td>
        </tr>`
            )
            .join("")
        : `<tr><td colspan="4" class="text-muted-erp">No hay órdenes en espera.</td></tr>`;
      document.getElementById("countOrdenesEspera").textContent = `(${U.formatearNumero(ordenes.length)})`;
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-danger">No se pudo cargar: ${U.escaparHtml(err.message || "error desconocido")}</td></tr>`;
      throw err;
    }
  }

  async function cargarTodo() {
    ocultarError();
    if (!filtrosValidos()) return; // Rango de fechas inconsistente: no se envía ninguna solicitud.

    btnAplicar.disabled = true;
    if (window.UI) window.UI.mostrarCargando();
    try {
      const params = { desde: inputDesde.value || undefined, hasta: inputHasta.value || undefined };
      // F14: antes era Promise.all([...]) — un solo fallo (ej. de
      // restricciones-stock) rechazaba el bloque completo e impedía que
      // ordenes-en-espera y throughput terminaran de pintarse aunque su
      // propia petición sí hubiera tenido éxito (esto es justo lo que se
      // veía en el reporte: KPIs con valores reales pero "Restricciones
      // de stock" atascado en "Cargando…" y el aviso rojo de conexión
      // arriba). Con allSettled cada sección se pinta con su propio
      // resultado (dato o error), y solo si falló al menos una se
      // muestra el aviso general.
      const resultados = await Promise.allSettled([
        cargarThroughput(params),
        cargarRestriccionesStock(),
        cargarOrdenesEnEspera(),
      ]);
      const fallidas = resultados.filter((r) => r.status === "rejected");
      if (fallidas.length) {
        const mensaje =
          fallidas[0].reason && fallidas[0].reason.message
            ? fallidas[0].reason.message
            : "Ocurrió un error al cargar los indicadores de Theory of Constraints.";
        mostrarError(mensaje);
        if (window.UI) window.UI.toast(mensaje, "error");
      }
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
