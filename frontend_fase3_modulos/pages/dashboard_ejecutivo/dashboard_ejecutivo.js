/**
 * dashboard_ejecutivo.js — Page-script del módulo nuevo de FRONTEND
 * "Dashboard Ejecutivo Consolidado" (FASE 4E). No crea módulo de
 * Backend nuevo: consolida en una sola pantalla lo que YA exponen
 *
 *   GET /api/dashboard-inventario/resumen                (m23, Fase 4B)
 *   GET /api/reportes-gerenciales-inventario/resumen      (m24, Fase 4D)
 *   GET /api/reportes-gerenciales-inventario/top-valor
 *   GET /api/reportes-gerenciales-inventario/productos-criticos
 *   GET /api/reportes-gerenciales-inventario/sin-rotacion
 *
 * y reutiliza, para las exportaciones, los 4 endpoints ya existentes de
 * m19_reportes (inventario-por-lote y proximos-vencer, Excel/PDF). No se
 * agrega ningún endpoint nuevo, no se duplica ningún cálculo del
 * Backend: todo lo que esta pantalla muestra ya lo devuelve alguno de
 * los 5 GET de arriba; lo único que se calcula aquí es PRESENTACIÓN
 * (semáforos, agrupaciones para gráficos, filtros en cliente), igual
 * que ya documentan dashboard_inventario.js y
 * reportes_gerenciales_inventario.js para sus propias pantallas.
 *
 * SECCIÓN 1 (Resumen Ejecutivo): usa exclusivamente
 * /dashboard-inventario/resumen (m23), salvo la tarjeta "Productos
 * críticos", que toma total_productos de
 * /reportes-gerenciales-inventario/productos-criticos (m24) en lugar de
 * productos_bajo_stock (m23), porque "críticos" en esta pantalla agrupa
 * bajo stock + riesgo de merma + vencimiento (criterio real del
 * Backend en ese endpoint), no solo bajo stock.
 *
 * SECCIÓN 3 (Panel Ejecutivo): Riesgo Alto = productos con nivel_riesgo
 * ALTO o CRITICO; Riesgo Medio = nivel_riesgo MEDIO (ambos contados
 * sobre la lista que ya devuelve /productos-criticos, sin llamada
 * adicional); Riesgo Bajo = cantidad_productos (m23) menos el total de
 * /productos-criticos (m24). Es una resta de dos totales que el
 * Backend ya calculó por separado, no una fórmula de negocio nueva.
 *
 * SECCIÓN 4 (Filtros globales): "Buscar" filtra las 3 tablas (Top
 * valor, Críticos, Sin rotación) por producto/código. "Criticidad"
 * (nivel_riesgo) y "Estado / tipo de riesgo" (tipo_riesgo) solo existen
 * como campos en /productos-criticos, así que solo filtran esa tabla:
 * Top valor y Sin rotación no tienen esos campos en el contrato real.
 *
 * SECCIÓN 6 (Exportaciones): reutiliza tal cual el helper de descarga
 * protegida ya usado en pages/inventario/inventario.js contra los
 * mismos 4 endpoints de m19_reportes (no hay endpoint de exportación
 * propio de m23/m24 en el Backend).
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
  async function apiGet(path, params) {
    return window.Api.get(path, params);
  }
  function filaVacia(colspan, texto) {
    return `<tr><td colspan="${colspan}" class="text-muted-erp">${U.escaparHtml(texto)}</td></tr>`;
  }
  function badgeNivel(nivel, colorClase) {
    return `<span class="badge text-bg-${colorClase}">${U.escaparHtml(nivel)}</span>`;
  }
  function dotSemaforo(estado) {
    return `<span class="semaforo-dot-sm ${estado}"></span>${estado}`;
  }
  function marcarSeveridadCard(id, clase) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("kpi-ok", "kpi-alerta", "kpi-critico");
    el.classList.add(clase);
  }

  const COLOR_BARRA = "#2f6fed";
  const COLOR_ACTIVO = "#1b8a5a";
  const COLOR_PROXIMO = "#e0a300";
  const COLOR_VENCIDO = "#d64545";

  // Caches en memoria de la última respuesta de cada endpoint, para que
  // los filtros globales en cliente no vuelvan a pedir nada al Backend.
  let cacheResumenDashboard = null; // m23
  let cacheTopValor = [];
  let cacheCriticos = [];
  let cacheSinRotacion = [];

  // ---------- SECCIÓN 1: Resumen ejecutivo ----------
  function pintarResumenEjecutivo(rDash, totalCriticos) {
    document.getElementById("kpiValorTotal").textContent = U.formatearMoneda(rDash.valor_total_inventario);
    document.getElementById("kpiProductosActivos").textContent = U.formatearNumero(rDash.cantidad_productos);
    document.getElementById("kpiLotes").textContent = U.formatearNumero(rDash.cantidad_lotes);
    document.getElementById("kpiProductosCriticos").textContent = U.formatearNumero(totalCriticos);
    document.getElementById("kpiProximosVencer").textContent = U.formatearNumero(rDash.productos_proximos_vencer);
    document.getElementById("kpiVencidos").textContent = U.formatearNumero(rDash.productos_vencidos);
    document.getElementById("kpiRiesgoMerma").textContent = U.formatearNumero(rDash.riesgo_merma_total);

    marcarSeveridadCard("cardProductosCriticos", totalCriticos > 0 ? "kpi-critico" : "kpi-ok");
    marcarSeveridadCard("cardProximosVencer", rDash.productos_proximos_vencer > 0 ? "kpi-alerta" : "kpi-ok");
    marcarSeveridadCard("cardVencidos", rDash.productos_vencidos > 0 ? "kpi-critico" : "kpi-ok");
    marcarSeveridadCard("cardRiesgoMerma", rDash.riesgo_merma_total > 0 ? "kpi-alerta" : "kpi-ok");
  }

  // ---------- SECCIÓN 3: Panel ejecutivo (semáforo Alto/Medio/Bajo) ----------
  function pintarPanelEjecutivo(rDash, criticos) {
    const alto = criticos.filter((p) => p.nivel_riesgo === "ALTO" || p.nivel_riesgo === "CRITICO").length;
    const medio = criticos.filter((p) => p.nivel_riesgo === "MEDIO").length;
    const bajo = Math.max(0, (rDash.cantidad_productos || 0) - criticos.length);

    document.getElementById("panelRiesgoAlto").textContent = U.formatearNumero(alto);
    document.getElementById("panelRiesgoMedio").textContent = U.formatearNumero(medio);
    document.getElementById("panelRiesgoBajo").textContent = U.formatearNumero(bajo);
  }

  // ---------- SECCIÓN 2: Gráficos ejecutivos (HTML/CSS, sin librería nueva) ----------

  // 2.1 Distribución del valor del inventario (Top valor, hasta 8 filas)
  function pintarChartTopValor(productos) {
    const cont = document.getElementById("chartTopValor");
    if (!productos.length) {
      cont.innerHTML = '<div class="text-muted-erp">No hay productos con valor de inventario registrado.</div>';
      return;
    }
    const top = [...productos].sort((a, b) => b.valor_total - a.valor_total).slice(0, 8);
    const maximo = Math.max(1, ...top.map((p) => p.valor_total));
    cont.innerHTML = top
      .map((p) => {
        const ancho = Math.round((p.valor_total / maximo) * 100);
        return `
      <div class="bar-row">
        <div class="bar-label" title="${U.escaparHtml(p.producto)}">${U.escaparHtml(p.producto)}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${ancho}%; background:${COLOR_BARRA};"></div></div>
        <div class="bar-value">${U.formatearMoneda(p.valor_total)}</div>
      </div>`;
      })
      .join("");
  }

  // 2.2 Estado de productos críticos: donut por nivel_riesgo
  function pintarChartEstadoCriticos(criticos) {
    const cont = document.getElementById("chartEstadoCriticos");
    const total = criticos.length;
    if (total <= 0) {
      cont.innerHTML = '<div class="text-muted-erp">No hay productos críticos registrados.</div>';
      return;
    }
    const alto = criticos.filter((p) => p.nivel_riesgo === "ALTO" || p.nivel_riesgo === "CRITICO").length;
    const medio = total - alto;
    const pctAlto = (alto / total) * 100;
    const gradiente = `conic-gradient(${COLOR_VENCIDO} 0% ${pctAlto}%, ${COLOR_PROXIMO} ${pctAlto}% 100%)`;
    cont.innerHTML = `
      <div class="donut-wrap">
        <div class="donut-circle" style="background:${gradiente};">
          <div class="donut-center"><div class="n">${U.formatearNumero(total)}</div><div class="t">Críticos</div></div>
        </div>
        <div class="donut-legend">
          <div class="item"><span class="swatch" style="background:${COLOR_VENCIDO};"></span>Alto/Crítico: ${U.formatearNumero(alto)}</div>
          <div class="item"><span class="swatch" style="background:${COLOR_PROXIMO};"></span>Medio: ${U.formatearNumero(medio)}</div>
        </div>
      </div>`;
  }

  // 2.3 Riesgo de merma: barra proporcional sobre productos activos
  function pintarChartRiesgoMerma(rDash) {
    const cont = document.getElementById("chartRiesgoMerma");
    const total = Math.max(1, rDash.cantidad_productos || 0);
    const riesgo = rDash.riesgo_merma_total || 0;
    if (riesgo <= 0) {
      cont.innerHTML = '<div class="text-muted-erp">Sin productos en riesgo de merma.</div>';
      return;
    }
    const ancho = Math.min(100, Math.round((riesgo / total) * 100));
    cont.innerHTML = `
      <div class="bar-row">
        <div class="bar-label">Riesgo de merma</div>
        <div class="bar-track"><div class="bar-fill" style="width:${ancho}%; background:${COLOR_VENCIDO};"></div></div>
        <div class="bar-value">${U.formatearNumero(riesgo)}</div>
      </div>
      <div class="text-muted-erp nota-contrato mt-2">${U.formatearNumero(riesgo)} de ${U.formatearNumero(rDash.cantidad_productos)} productos activos (m23 · riesgo_merma_total).</div>`;
  }

  // 2.4 Productos sin rotación: barra por producto (hasta 8, mayor días primero)
  function pintarChartSinRotacion(productos) {
    const cont = document.getElementById("chartSinRotacion");
    if (!productos.length) {
      cont.innerHTML = '<div class="text-muted-erp">No hay productos sin rotación para el umbral aplicado.</div>';
      return;
    }
    const top = [...productos]
      .sort((a, b) => (b.dias_sin_movimiento ?? Number.MAX_SAFE_INTEGER) - (a.dias_sin_movimiento ?? Number.MAX_SAFE_INTEGER))
      .slice(0, 8);
    const maximo = Math.max(1, ...top.map((p) => p.dias_sin_movimiento ?? 0));
    cont.innerHTML = top
      .map((p) => {
        const dias = p.dias_sin_movimiento ?? 0;
        const ancho = p.dias_sin_movimiento === null || p.dias_sin_movimiento === undefined ? 100 : Math.round((dias / maximo) * 100);
        const etiqueta = p.dias_sin_movimiento === null || p.dias_sin_movimiento === undefined ? "Sin movimiento" : `${U.formatearNumero(dias)} d.`;
        return `
      <div class="bar-row">
        <div class="bar-label" title="${U.escaparHtml(p.producto)}">${U.escaparHtml(p.producto)}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${ancho}%; background:${COLOR_PROXIMO};"></div></div>
        <div class="bar-value">${etiqueta}</div>
      </div>`;
      })
      .join("");
  }

  // 2.5 Próximos a vencer: donut Activos/Próximos/Vencidos (mismo criterio que dashboard_inventario.js)
  function pintarChartProximosVencer(rDash) {
    const cont = document.getElementById("chartProximosVencer");
    const totalLotes = rDash.cantidad_lotes || 0;
    const vencidos = rDash.productos_vencidos || 0;
    const proximos = rDash.productos_proximos_vencer || 0;
    const activos = Math.max(0, totalLotes - vencidos - proximos);
    if (totalLotes <= 0) {
      cont.innerHTML = '<div class="text-muted-erp">Sin lotes registrados.</div>';
      return;
    }
    const pctActivos = (activos / totalLotes) * 100;
    const pctProximos = (proximos / totalLotes) * 100;
    const corte1 = pctActivos;
    const corte2 = pctActivos + pctProximos;
    const gradiente = `conic-gradient(${COLOR_ACTIVO} 0% ${corte1}%, ${COLOR_PROXIMO} ${corte1}% ${corte2}%, ${COLOR_VENCIDO} ${corte2}% 100%)`;
    cont.innerHTML = `
      <div class="donut-wrap">
        <div class="donut-circle" style="background:${gradiente};">
          <div class="donut-center"><div class="n">${U.formatearNumero(totalLotes)}</div><div class="t">Lotes</div></div>
        </div>
        <div class="donut-legend">
          <div class="item"><span class="swatch" style="background:${COLOR_ACTIVO};"></span>Activos: ${U.formatearNumero(activos)}</div>
          <div class="item"><span class="swatch" style="background:${COLOR_PROXIMO};"></span>Próximos: ${U.formatearNumero(proximos)}</div>
          <div class="item"><span class="swatch" style="background:${COLOR_VENCIDO};"></span>Vencidos: ${U.formatearNumero(vencidos)}</div>
        </div>
      </div>`;
  }

  // ---------- SECCIÓN 4: Filtros globales + tablas ----------
  const inputBuscarGlobal = document.getElementById("inputBuscarGlobal");
  const selectCriticidadGlobal = document.getElementById("selectCriticidadGlobal");
  const selectEstadoGlobal = document.getElementById("selectEstadoGlobal");

  const ETIQUETA_TIPO_RIESGO = { BAJO_STOCK: "Bajo stock", RIESGO_MERMA: "Riesgo de merma", VENCIMIENTO: "Vencimiento" };
  const SEMAFORO_POR_NIVEL = { MEDIO: "AMARILLO", ALTO: "ROJO", CRITICO: "ROJO" };
  const COLOR_BADGE_POR_NIVEL = { MEDIO: "warning", ALTO: "danger", CRITICO: "danger" };

  function terminoGlobal() {
    return (inputBuscarGlobal.value || "").trim().toLowerCase();
  }
  function coincideTermino(p, termino) {
    return !termino || p.producto.toLowerCase().includes(termino) || p.codigo_producto.toLowerCase().includes(termino);
  }

  function pintarTopValor() {
    const termino = terminoGlobal();
    const filas = cacheTopValor.filter((p) => coincideTermino(p, termino)).sort((a, b) => b.valor_total - a.valor_total);
    document.getElementById("tbodyTopValor").innerHTML = filas.length
      ? filas
          .map(
            (p) => `
      <tr>
        <td>${U.escaparHtml(p.producto)}</td>
        <td><code>${U.escaparHtml(p.codigo_producto)}</code></td>
        <td class="text-end">${U.formatearNumero(p.stock_actual, 2)}</td>
        <td class="text-end">${U.formatearMoneda(p.costo_unitario)}</td>
        <td class="text-end">${U.formatearMoneda(p.valor_total)}</td>
        <td class="text-end">${U.formatearPorcentaje(p.porcentaje_participacion)}</td>
      </tr>`
          )
          .join("")
      : filaVacia(6, cacheTopValor.length === 0 ? "No hay productos con valor de inventario registrado." : "Ningún producto coincide con el filtro.");
    document.getElementById("countTopValor").textContent = `(${U.formatearNumero(filas.length)})`;
  }

  function pintarCriticos() {
    const termino = terminoGlobal();
    const nivel = selectCriticidadGlobal.value;
    const tipo = selectEstadoGlobal.value;
    const filas = cacheCriticos.filter((p) => {
      return coincideTermino(p, termino) && (!nivel || p.nivel_riesgo === nivel) && (!tipo || p.tipo_riesgo === tipo);
    });
    document.getElementById("tbodyCriticos").innerHTML = filas.length
      ? filas
          .map((p) => {
            const semaforo = SEMAFORO_POR_NIVEL[p.nivel_riesgo] || "AMARILLO";
            const colorBadge = COLOR_BADGE_POR_NIVEL[p.nivel_riesgo] || "warning";
            return `
      <tr class="${semaforo === "ROJO" ? "table-danger" : ""}">
        <td>${U.escaparHtml(p.producto)}</td>
        <td><code>${U.escaparHtml(p.codigo_producto)}</code></td>
        <td>${U.escaparHtml(ETIQUETA_TIPO_RIESGO[p.tipo_riesgo] || p.tipo_riesgo)}</td>
        <td class="text-end">${U.formatearNumero(p.stock_actual, 2)}</td>
        <td class="text-end">${U.formatearMoneda(p.valor_comprometido)}</td>
        <td>${dotSemaforo(semaforo)} ${badgeNivel(p.nivel_riesgo, colorBadge)}</td>
      </tr>`;
          })
          .join("")
      : filaVacia(6, cacheCriticos.length === 0 ? "No hay productos críticos registrados." : "Ningún producto coincide con el filtro.");
    document.getElementById("countCriticos").textContent = `(${U.formatearNumero(filas.length)})`;
  }

  function pintarSinRotacion() {
    const termino = terminoGlobal();
    const filas = cacheSinRotacion.filter((p) => coincideTermino(p, termino));
    document.getElementById("tbodySinRotacion").innerHTML = filas.length
      ? filas
          .map((p) => {
            const dias = p.dias_sin_movimiento;
            const semaforo = dias === null || dias === undefined ? "ROJO" : dias >= 60 ? "ROJO" : "AMARILLO";
            const colorBadge = semaforo === "ROJO" ? "danger" : "warning";
            const textoDias = dias === null || dias === undefined ? "Sin movimiento registrado" : U.formatearNumero(dias);
            return `
      <tr class="${semaforo === "ROJO" ? "table-danger" : ""}">
        <td>${U.escaparHtml(p.producto)}</td>
        <td><code>${U.escaparHtml(p.codigo_producto)}</code></td>
        <td class="text-end">${textoDias}</td>
        <td class="text-end">${U.formatearNumero(p.stock_actual, 2)}</td>
        <td class="text-end">${U.formatearMoneda(p.valor_inventario)}</td>
        <td>${dotSemaforo(semaforo)} ${badgeNivel(semaforo, colorBadge)}</td>
      </tr>`;
          })
          .join("")
      : filaVacia(6, cacheSinRotacion.length === 0 ? "No hay productos sin rotación registrados." : "Ningún producto coincide con el filtro.");
    document.getElementById("countSinRotacion").textContent = `(${U.formatearNumero(filas.length)})`;
  }

  function aplicarFiltrosGlobales() {
    pintarTopValor();
    pintarCriticos();
    pintarSinRotacion();
  }

  // ---------- SECCIÓN 6: Exportaciones (reutiliza m19_reportes) ----------
  // Mismo helper que ya usa pages/inventario/inventario.js: api-client.js
  // siempre hace resp.json(), así que no sirve para descargar binarios;
  // este helper local hace su propio fetch con el mismo Bearer, y no
  // agrega ningún endpoint nuevo, solo consume los 4 ya existentes.
  async function descargarArchivoProtegido(path, nombreSugerido) {
    const token = window.Auth ? window.Auth.obtenerToken() : null;
    const headers = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    let resp;
    try {
      resp = await fetch(`${CONFIG.API_BASE_URL}${path}`, { headers });
    } catch (err) {
      throw new Error(`No se pudo conectar con el Backend (${CONFIG.API_BASE_URL}). Verifica que esté corriendo.`);
    }
    if (resp.status === 401) {
      if (window.Auth) window.Auth.cerrarSesion();
      throw new Error("Sesión expirada.");
    }
    if (!resp.ok) {
      let detalle = `HTTP ${resp.status}`;
      try {
        const datos = await resp.json();
        if (datos && datos.detail) detalle = Array.isArray(datos.detail) ? datos.detail.map((d) => d.msg).join("; ") : datos.detail;
      } catch (err) {
        /* sin cuerpo JSON: se conserva "HTTP <status>" */
      }
      throw new Error(detalle);
    }
    const blob = await resp.blob();
    let nombreArchivo = nombreSugerido;
    const disposicion = resp.headers.get("Content-Disposition");
    if (disposicion) {
      const match = /filename="?([^"]+)"?/.exec(disposicion);
      if (match) nombreArchivo = match[1];
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = nombreArchivo;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  async function descargarSeguro(path, nombreSugerido) {
    ocultarError();
    try {
      await descargarArchivoProtegido(path, nombreSugerido);
    } catch (err) {
      mostrarError(err.message || "No se pudo descargar el archivo.");
      if (window.UI) window.UI.toast(err.message || "No se pudo descargar el archivo.", "error");
    }
  }

  function inicializarExportaciones() {
    document.getElementById("lnkExportarLotesExcel").addEventListener("click", (e) => {
      e.preventDefault();
      descargarSeguro("/api/reportes/inventario-por-lote/exportar/excel", "inventario_por_lote.xlsx");
    });
    document.getElementById("lnkExportarLotesPdf").addEventListener("click", (e) => {
      e.preventDefault();
      descargarSeguro("/api/reportes/inventario-por-lote/exportar/pdf", "inventario_por_lote.pdf");
    });
    document.getElementById("lnkExportarProximosVencerExcel").addEventListener("click", (e) => {
      e.preventDefault();
      descargarSeguro("/api/reportes/proximos-vencer/exportar/excel", "proximos_vencer.xlsx");
    });
    document.getElementById("lnkExportarProximosVencerPdf").addEventListener("click", (e) => {
      e.preventDefault();
      descargarSeguro("/api/reportes/proximos-vencer/exportar/pdf", "proximos_vencer.pdf");
    });
  }

  // ---------- Carga principal (Sección 5: Actualizar Dashboard) ----------
  async function cargarTodo() {
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    btnActualizar.disabled = true;
    try {
      const [rDash, rTop, rCriticos, rSinRotacion] = await Promise.all([
        apiGet("/api/dashboard-inventario/resumen"),
        apiGet("/api/reportes-gerenciales-inventario/top-valor"),
        apiGet("/api/reportes-gerenciales-inventario/productos-criticos"),
        apiGet("/api/reportes-gerenciales-inventario/sin-rotacion"),
      ]);

      cacheResumenDashboard = rDash;
      cacheTopValor = rTop.productos;
      cacheCriticos = rCriticos.productos;
      cacheSinRotacion = rSinRotacion.productos;

      pintarResumenEjecutivo(rDash, rCriticos.total_productos);
      pintarPanelEjecutivo(rDash, cacheCriticos);

      pintarChartTopValor(cacheTopValor);
      pintarChartEstadoCriticos(cacheCriticos);
      pintarChartRiesgoMerma(rDash);
      pintarChartSinRotacion(cacheSinRotacion);
      pintarChartProximosVencer(rDash);

      aplicarFiltrosGlobales();

      document.getElementById("infoActualizado").textContent = `Actualizado: ${U.formatearFechaHora(rCriticos.generado_en)}`;
    } catch (err) {
      const mensaje = err?.message || "No se pudo cargar el Dashboard Ejecutivo Consolidado.";
      mostrarError(mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
      document.getElementById("infoActualizado").textContent = "No se pudo actualizar.";
    } finally {
      btnActualizar.disabled = false;
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    btnActualizar.addEventListener("click", cargarTodo);
    inputBuscarGlobal.addEventListener("input", U.debounce(aplicarFiltrosGlobales, 200));
    selectCriticidadGlobal.addEventListener("change", aplicarFiltrosGlobales);
    selectEstadoGlobal.addEventListener("change", aplicarFiltrosGlobales);

    inicializarExportaciones();
    cargarTodo();
  }

  iniciar();
})();
