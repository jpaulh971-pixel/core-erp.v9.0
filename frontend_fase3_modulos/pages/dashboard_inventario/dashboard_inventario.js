/**
 * dashboard_inventario.js — Page-script del módulo m23_dashboard_inventario
 * (app/modules/m23_dashboard_inventario). FASE 4B — Frontend.
 *
 * Endpoint (contrato real: app/modules/m23_dashboard_inventario/router.py +
 * schemas.py):
 *   GET /api/dashboard-inventario/resumen  (Bearer, sin parámetros)
 *     -> ResumenDashboardInventario:
 *        valor_total_inventario: float
 *        cantidad_productos: int
 *        cantidad_lotes: int
 *        productos_bajo_stock: int
 *        productos_proximos_vencer: int   (lotes en estado PROXIMOS_A_VENCER)
 *        productos_vencidos: int          (lotes vencidos)
 *        riesgo_merma_total: int
 *
 * Panel de solo lectura: un único GET, botón "Actualizar" para repetirlo.
 * Mismo patrón que dashboard.js (raíz) y pages/inventario/inventario.js:
 * usa window.Api.get (api-client.js), window.Utils (utils.js) para
 * formateo y window.UI (ui-components.js) para toasts/loader. No se
 * agrega ningún endpoint nuevo ni se recalcula nada que el Backend ya
 * resuelve: este script solo pinta la respuesta.
 *
 * Semáforo gerencial y severidad de las tarjetas KPI: el endpoint NO
 * devuelve un campo de semáforo (a diferencia de semaforo_stock /
 * semaforo_vencimiento que sí expone m03/m19 por lote o por producto
 * individual, ver pages/inventario/inventario.js). Este resumen es
 * agregado (conteos totales), así que el color VERDE/AMARILLO/ROJO y
 * ACTIVO/PROXIMO_A_VENCER/VENCIDO se derivan aquí, en el Frontend, a
 * partir de esos conteos, con las reglas simples documentadas en
 * cada función de abajo. Es una regla de presentación (Fase 4B), no
 * un cálculo de negocio: no reemplaza ni reinterpreta el semáforo por
 * lote/producto que ya pinta Inventario, solo resume la foto gerencial
 * completa en un único indicador por bloque.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const elError = document.getElementById("estadoError");
  const btnActualizar = document.getElementById("btnActualizar");

  function mostrarError(mensaje) {
    elError.textContent = mensaje;
    elError.style.display = "block";
  }

  function ocultarError() {
    elError.style.display = "none";
  }

  async function apiGet(path) {
    return window.Api.get(path);
  }

  // ---------- KPIs ----------

  function pintarKpis(r) {
    document.getElementById("kpiValorTotal").textContent = U.formatearMoneda(r.valor_total_inventario);
    document.getElementById("kpiCantidadProductos").textContent = U.formatearNumero(r.cantidad_productos);
    document.getElementById("kpiCantidadLotes").textContent = U.formatearNumero(r.cantidad_lotes);
    document.getElementById("kpiBajoStock").textContent = U.formatearNumero(r.productos_bajo_stock);
    document.getElementById("kpiProximosVencer").textContent = U.formatearNumero(r.productos_proximos_vencer);
    document.getElementById("kpiVencidos").textContent = U.formatearNumero(r.productos_vencidos);
    document.getElementById("kpiRiesgoMerma").textContent = U.formatearNumero(r.riesgo_merma_total);

    // Acento de color en el borde de cada tarjeta KPI (kpi-ok/kpi-alerta/
    // kpi-critico, definidas en index.html): 0 -> ok; > 0 -> alerta;
    // solo "vencidos" se marca directamente como crítico por ser el caso
    // más severo (mismo criterio que la fila roja de alertas en
    // pages/inventario/inventario.js).
    marcarSeveridadCard("cardBajoStock", r.productos_bajo_stock > 0 ? "kpi-alerta" : "kpi-ok");
    marcarSeveridadCard("cardProximosVencer", r.productos_proximos_vencer > 0 ? "kpi-alerta" : "kpi-ok");
    marcarSeveridadCard("cardVencidos", r.productos_vencidos > 0 ? "kpi-critico" : "kpi-ok");
    marcarSeveridadCard("cardRiesgoMerma", r.riesgo_merma_total > 0 ? "kpi-alerta" : "kpi-ok");
  }

  function marcarSeveridadCard(id, clase) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("kpi-ok", "kpi-alerta", "kpi-critico");
    el.classList.add(clase);
  }

  // ---------- Semáforo gerencial ----------

  // Semáforo de stock (agregado): regla de presentación del Frontend,
  // no un campo del Backend. 0 productos bajo stock -> VERDE. Si hay
  // alguno, se gradúa por proporción sobre el total de productos:
  // hasta 10% -> AMARILLO, más de 10% -> ROJO.
  function calcularSemaforoStock(r) {
    if (r.productos_bajo_stock <= 0) {
      return { estado: "VERDE", detalle: "Ningún producto está bajo su stock mínimo." };
    }
    const total = r.cantidad_productos > 0 ? r.cantidad_productos : 1;
    const proporcion = r.productos_bajo_stock / total;
    if (proporcion <= 0.10) {
      return {
        estado: "AMARILLO",
        detalle: `${U.formatearNumero(r.productos_bajo_stock)} de ${U.formatearNumero(r.cantidad_productos)} productos bajo stock mínimo.`,
      };
    }
    return {
      estado: "ROJO",
      detalle: `${U.formatearNumero(r.productos_bajo_stock)} de ${U.formatearNumero(r.cantidad_productos)} productos bajo stock mínimo.`,
    };
  }

  // Semáforo de vencimiento (agregado): regla de presentación del
  // Frontend. Prioriza el caso más severo: si hay lotes vencidos ->
  // VENCIDO; si no hay vencidos pero sí próximos a vencer ->
  // PROXIMO_A_VENCER; si no hay ninguno de los dos -> ACTIVO.
  function calcularSemaforoVencimiento(r) {
    if (r.productos_vencidos > 0) {
      return {
        estado: "VENCIDO",
        detalle: `${U.formatearNumero(r.productos_vencidos)} lote(s) vencido(s).`,
      };
    }
    if (r.productos_proximos_vencer > 0) {
      return {
        estado: "PROXIMO_A_VENCER",
        detalle: `${U.formatearNumero(r.productos_proximos_vencer)} lote(s) próximo(s) a vencer.`,
      };
    }
    return { estado: "ACTIVO", detalle: "Sin lotes vencidos ni próximos a vencer." };
  }

  const ETIQUETA_SEMAFORO = {
    VERDE: "VERDE",
    AMARILLO: "AMARILLO",
    ROJO: "ROJO",
    ACTIVO: "ACTIVO",
    PROXIMO_A_VENCER: "PRÓXIMO A VENCER",
    VENCIDO: "VENCIDO",
  };

  function pintarSemaforo(prefijo, resultado) {
    document.getElementById(`${prefijo}Dot`).className = `semaforo-dot ${resultado.estado}`;
    document.getElementById(`${prefijo}Estado`).textContent = ETIQUETA_SEMAFORO[resultado.estado] || resultado.estado;
    document.getElementById(`${prefijo}Detalle`).textContent = resultado.detalle;
  }

  // ---------- 3) Gráficos gerenciales (HTML/CSS, sin librería nueva) ----------

  const COLOR_BARRA = "#2f6fed";
  const COLOR_ACTIVO = "#1b8a5a";
  const COLOR_PROXIMO = "#e0a300";
  const COLOR_VENCIDO = "#d64545";

  // "Distribución de riesgos": barras horizontales comparando los 4
  // conteos de riesgo del resumen. Cada barra se dimensiona en
  // proporción al valor máximo del conjunto (no requiere Chart.js ni
  // ninguna librería nueva: son <div> con width en %).
  function pintarDistribucionRiesgos(r) {
    const cont = document.getElementById("chartDistribucionRiesgos");
    const items = [
      { etiqueta: "Bajo stock mínimo", valor: r.productos_bajo_stock, color: COLOR_PROXIMO },
      { etiqueta: "Próximos a vencer", valor: r.productos_proximos_vencer, color: COLOR_PROXIMO },
      { etiqueta: "Vencidos", valor: r.productos_vencidos, color: COLOR_VENCIDO },
      { etiqueta: "Riesgo de merma", valor: r.riesgo_merma_total, color: COLOR_BARRA },
    ];
    const maximo = Math.max(1, ...items.map((i) => i.valor));

    if (items.every((i) => i.valor === 0)) {
      cont.innerHTML = '<div class="text-muted-erp">Sin riesgos registrados: todos los indicadores están en cero.</div>';
      return;
    }

    cont.innerHTML = items
      .map((i) => {
        const ancho = Math.round((i.valor / maximo) * 100);
        return `
      <div class="bar-row">
        <div class="bar-label">${U.escaparHtml(i.etiqueta)}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${ancho}%; background:${i.color};"></div></div>
        <div class="bar-value">${U.formatearNumero(i.valor)}</div>
      </div>`;
      })
      .join("");
  }

  // "Estado del inventario (lotes)": donut con conic-gradient (CSS puro)
  // sobre cantidad_lotes, repartido en Activos / Próximos a vencer /
  // Vencidos — los mismos 3 estados que pide el semáforo de vencimiento.
  function pintarEstadoInventario(r) {
    const cont = document.getElementById("chartEstadoInventario");
    const totalLotes = r.cantidad_lotes || 0;
    const vencidos = r.productos_vencidos || 0;
    const proximos = r.productos_proximos_vencer || 0;
    const activos = Math.max(0, totalLotes - vencidos - proximos);

    if (totalLotes <= 0) {
      cont.innerHTML = '<div class="text-muted-erp">Sin lotes registrados.</div>';
      return;
    }

    const pctActivos = (activos / totalLotes) * 100;
    const pctProximos = (proximos / totalLotes) * 100;
    // El resto (100 - pctActivos - pctProximos) queda para vencidos.
    const corte1 = pctActivos;
    const corte2 = pctActivos + pctProximos;

    const gradiente = `conic-gradient(${COLOR_ACTIVO} 0% ${corte1}%, ${COLOR_PROXIMO} ${corte1}% ${corte2}%, ${COLOR_VENCIDO} ${corte2}% 100%)`;

    cont.innerHTML = `
      <div class="donut-wrap">
        <div class="donut-circle" style="background:${gradiente};">
          <div class="donut-center">
            <div class="n">${U.formatearNumero(totalLotes)}</div>
            <div class="t">Lotes</div>
          </div>
        </div>
        <div class="donut-legend">
          <div class="item"><span class="swatch" style="background:${COLOR_ACTIVO};"></span>Activos: ${U.formatearNumero(activos)}</div>
          <div class="item"><span class="swatch" style="background:${COLOR_PROXIMO};"></span>Próximos a vencer: ${U.formatearNumero(proximos)}</div>
          <div class="item"><span class="swatch" style="background:${COLOR_VENCIDO};"></span>Vencidos: ${U.formatearNumero(vencidos)}</div>
        </div>
      </div>`;
  }

  // "Alertas principales": lista textual derivada de los mismos 4
  // conteos de riesgo, ordenada por severidad (vencidos primero). No
  // es un listado de productos/lotes individuales (el endpoint no lo
  // expone, solo agrega), sino el resumen de qué tipos de alerta están
  // activos y cuántos casos tiene cada uno.
  function pintarAlertasPrincipales(r) {
    const cont = document.getElementById("listaAlertas");
    const alertas = [
      { valor: r.productos_vencidos, texto: `${U.formatearNumero(r.productos_vencidos)} lote(s) vencido(s)`, sev: "sev-critico", icono: "bi-x-octagon-fill" },
      { valor: r.riesgo_merma_total, texto: `${U.formatearNumero(r.riesgo_merma_total)} producto(s) en riesgo de merma`, sev: "sev-alerta", icono: "bi-shield-exclamation" },
      { valor: r.productos_bajo_stock, texto: `${U.formatearNumero(r.productos_bajo_stock)} producto(s) bajo stock mínimo`, sev: "sev-alerta", icono: "bi-exclamation-triangle-fill" },
      { valor: r.productos_proximos_vencer, texto: `${U.formatearNumero(r.productos_proximos_vencer)} lote(s) próximo(s) a vencer`, sev: "sev-alerta", icono: "bi-hourglass-split" },
    ].filter((a) => a.valor > 0);

    if (!alertas.length) {
      cont.innerHTML = `
        <div class="alerta-item sev-ok">
          <i class="bi bi-check-circle-fill"></i>
          <div class="alerta-texto">Sin alertas activas.</div>
        </div>`;
      return;
    }

    cont.innerHTML = alertas
      .map(
        (a) => `
        <div class="alerta-item ${a.sev}">
          <i class="bi ${a.icono}"></i>
          <div class="alerta-texto">${U.escaparHtml(a.texto)}</div>
        </div>`
      )
      .join("");
  }

  // ---------- 4) Tabla resumen gerencial ----------

  function badgeEstado(texto, color) {
    return `<span class="badge text-bg-${color}">${U.escaparHtml(texto)}</span>`;
  }

  function pintarTablaResumen(r, semaforoStock, semaforoVencimiento) {
    const tbody = document.getElementById("tbodyResumenGerencial");
    const colorSemaforo = { VERDE: "success", AMARILLO: "warning", ROJO: "danger" };
    const colorRiesgoMerma = r.riesgo_merma_total > 0 ? badgeEstado("ALERTA", "warning") : badgeEstado("SIN RIESGO", "success");
    const colorVencidos = r.productos_vencidos > 0 ? badgeEstado("VENCIDO", "danger") : badgeEstado("SIN VENCIDOS", "success");
    const colorProximos = r.productos_proximos_vencer > 0 ? badgeEstado("PRÓXIMO A VENCER", "warning") : badgeEstado("SIN ALERTA", "success");

    const filas = [
      { indicador: "Valor total del inventario", valor: U.formatearMoneda(r.valor_total_inventario), estado: "—" },
      { indicador: "Cantidad de productos", valor: U.formatearNumero(r.cantidad_productos), estado: "—" },
      { indicador: "Cantidad de lotes", valor: U.formatearNumero(r.cantidad_lotes), estado: "—" },
      {
        indicador: "Stock crítico (bajo stock mínimo)",
        valor: U.formatearNumero(r.productos_bajo_stock),
        estado: badgeEstado(ETIQUETA_SEMAFORO[semaforoStock.estado], colorSemaforo[semaforoStock.estado]),
      },
      { indicador: "Productos próximos a vencer", valor: U.formatearNumero(r.productos_proximos_vencer), estado: colorProximos },
      { indicador: "Productos vencidos", valor: U.formatearNumero(r.productos_vencidos), estado: colorVencidos },
      { indicador: "Riesgo total de merma", valor: U.formatearNumero(r.riesgo_merma_total), estado: colorRiesgoMerma },
    ];

    tbody.innerHTML = filas
      .map(
        (f) => `
      <tr>
        <td>${U.escaparHtml(f.indicador)}</td>
        <td class="text-end">${f.valor}</td>
        <td>${f.estado}</td>
      </tr>`
      )
      .join("");
  }

  // ---------- Carga principal ----------

  async function cargarTodo() {
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      const r = await apiGet("/api/dashboard-inventario/resumen");

      pintarKpis(r);

      const semaforoStock = calcularSemaforoStock(r);
      const semaforoVencimiento = calcularSemaforoVencimiento(r);
      pintarSemaforo("semaforoStock", semaforoStock);
      pintarSemaforo("semaforoVencimiento", semaforoVencimiento);

      pintarDistribucionRiesgos(r);
      pintarEstadoInventario(r);
      pintarAlertasPrincipales(r);

      pintarTablaResumen(r, semaforoStock, semaforoVencimiento);

      // "Actualizado" es la hora del navegador en el momento de la
      // respuesta (el Backend no devuelve un campo generado_en en este
      // endpoint, a diferencia de m01_dashboard/resumen): se etiqueta
      // explícitamente como hora local para no sugerir que viene del
      // Backend.
      document.getElementById("infoActualizado").textContent =
        `Actualizado (hora local): ${U.formatearFechaHora(new Date())}`;
    } catch (err) {
      const mensaje = err?.message || "No se pudo cargar el resumen del Dashboard Gerencial de Inventario.";
      mostrarError(mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
      document.getElementById("infoActualizado").textContent = "No se pudo actualizar.";
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    btnActualizar.addEventListener("click", cargarTodo);
    cargarTodo();
  }

  iniciar();
})();
