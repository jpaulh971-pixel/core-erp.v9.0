/**
 * reportes_gerenciales_inventario.js — Page-script del módulo
 * m24_reportes_gerenciales_inventario (app/modules/m24_reportes_gerenciales_inventario).
 * FASE 4D — Frontend.
 *
 * Endpoints (contrato real: app/modules/m24_reportes_gerenciales_inventario/
 * router.py + schemas.py), todos Bearer, todos de solo lectura:
 *
 *   GET /api/reportes-gerenciales-inventario/resumen
 *     -> ResumenEjecutivoInventario: valor_total_inventario, cantidad_productos,
 *        cantidad_lotes, productos_bajo_stock, productos_proximos_vencer,
 *        productos_vencidos, riesgo_merma_total.
 *
 *   GET /api/reportes-gerenciales-inventario/top-valor?limite=
 *     -> ReporteTopValorInventario: generado_en, total_productos,
 *        valor_total_inventario, productos[]: { producto, codigo_producto,
 *        stock_actual, costo_unitario, valor_total, porcentaje_participacion }.
 *
 *   GET /api/reportes-gerenciales-inventario/productos-criticos
 *     -> ReporteProductosCriticos: generado_en, total_productos,
 *        productos[]: { producto, codigo_producto, tipo_riesgo
 *        (BAJO_STOCK|RIESGO_MERMA|VENCIMIENTO), nivel_riesgo
 *        (MEDIO|ALTO|CRITICO), stock_actual, valor_comprometido }.
 *
 *   GET /api/reportes-gerenciales-inventario/sin-rotacion?dias_sin_rotacion=
 *     -> ReporteProductosSinRotacion: generado_en, total_productos,
 *        productos[]: { producto, codigo_producto, stock_actual,
 *        valor_inventario, dias_sin_movimiento (int | null) }.
 *
 * Panel de solo lectura, mismo patrón que pages/dashboard_inventario/
 * dashboard_inventario.js: usa window.Api.get (api-client.js),
 * window.Utils (utils.js) para formateo y window.UI (ui-components.js)
 * para toasts/loader. No se agrega ningún endpoint nuevo ni se recalcula
 * nada que el Backend ya resuelve: este script solo pinta las 4
 * respuestas, deriva las 2 tarjetas KPI que el Backend no agrega
 * (Productos críticos / Productos sin rotación, tomadas de los propios
 * total_productos que sus secciones ya cargan) y agrega
 * búsqueda/ordenamiento/filtro EN EL CLIENTE, porque estos 4 endpoints
 * no aceptan más parámetros que "limite" (top-valor) y
 * "dias_sin_rotacion" (sin-rotacion).
 *
 * Semáforo por fila (Secciones 3 y 4): el Backend expone nivel_riesgo
 * (MEDIO/ALTO/CRITICO) para Productos críticos, pero no expone ningún
 * campo de semáforo para Sin rotación. Igual que
 * dashboard_inventario.js documenta para su propio semáforo agregado,
 * el mapeo VERDE/AMARILLO/ROJO de esta pantalla es una regla de
 * PRESENTACIÓN del Frontend (Fase 4D), no un cálculo de negocio: no
 * reemplaza ni reinterpreta ningún semáforo que el Backend sí calcula
 * en otros módulos (p. ej. semaforo_stock/semaforo_vencimiento de
 * pages/inventario/inventario.js).
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

  // Caches en memoria de la última respuesta de cada endpoint, para que
  // búsqueda/orden/filtro en cliente no vuelvan a pedir nada al Backend.
  let cacheTopValor = [];
  let cacheCriticos = [];
  let cacheSinRotacion = [];

  // ---------- 1) KPIs ----------
  function marcarSeveridadCard(id, clase) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("kpi-ok", "kpi-alerta", "kpi-critico");
    el.classList.add(clase);
  }

  function pintarKpisResumen(r) {
    document.getElementById("kpiValorTotal").textContent = U.formatearMoneda(r.valor_total_inventario);
    document.getElementById("kpiProductosActivos").textContent = U.formatearNumero(r.cantidad_productos);
    document.getElementById("kpiLotes").textContent = U.formatearNumero(r.cantidad_lotes);
    document.getElementById("kpiRiesgoInventario").textContent = U.formatearNumero(r.riesgo_merma_total);
    marcarSeveridadCard("cardRiesgoInventario", r.riesgo_merma_total > 0 ? "kpi-alerta" : "kpi-ok");
  }

  // Las tarjetas "Productos críticos" y "Productos sin rotación" no
  // vienen en /resumen: se pintan con total_productos de las respuestas
  // de /productos-criticos y /sin-rotacion, que la página ya carga para
  // sus propias tablas (Secciones 3 y 4). No se agrega ninguna llamada
  // adicional al Backend solo para estas 2 tarjetas.
  function pintarKpiCriticos(totalProductos) {
    document.getElementById("kpiProductosCriticos").textContent = U.formatearNumero(totalProductos);
    marcarSeveridadCard("cardProductosCriticos", totalProductos > 0 ? "kpi-critico" : "kpi-ok");
  }
  function pintarKpiSinRotacion(totalProductos) {
    document.getElementById("kpiSinRotacion").textContent = U.formatearNumero(totalProductos);
    marcarSeveridadCard("cardSinRotacion", totalProductos > 0 ? "kpi-alerta" : "kpi-ok");
  }

  // ---------- 2) Top valor inventario (búsqueda + ordenamiento en cliente) ----------
  const inputBuscarTopValor = document.getElementById("inputBuscarTopValor");
  const selectLimiteTopValor = document.getElementById("selectLimiteTopValor");
  const tbodyTopValor = document.getElementById("tbodyTopValor");
  let ordenTopValor = { campo: "valor_total", asc: false }; // por defecto: igual criterio que el Backend (valor_total desc).

  function filaTopValor(p) {
    return `
      <tr>
        <td>${U.escaparHtml(p.producto)}</td>
        <td><code>${U.escaparHtml(p.codigo_producto)}</code></td>
        <td class="text-end">${U.formatearNumero(p.stock_actual, 2)}</td>
        <td class="text-end">${U.formatearMoneda(p.costo_unitario)}</td>
        <td class="text-end">${U.formatearMoneda(p.valor_total)}</td>
        <td class="text-end">${U.formatearPorcentaje(p.porcentaje_participacion)}</td>
      </tr>`;
  }

  function pintarTopValor() {
    const termino = (inputBuscarTopValor.value || "").trim().toLowerCase();
    let filas = cacheTopValor.filter(
      (p) =>
        !termino ||
        p.producto.toLowerCase().includes(termino) ||
        p.codigo_producto.toLowerCase().includes(termino)
    );

    const { campo, asc } = ordenTopValor;
    filas = [...filas].sort((a, b) => {
      const va = a[campo];
      const vb = b[campo];
      let cmp;
      if (typeof va === "string") cmp = va.localeCompare(vb, "es");
      else cmp = va - vb;
      return asc ? cmp : -cmp;
    });

    tbodyTopValor.innerHTML = filas.length
      ? filas.map(filaTopValor).join("")
      : filaVacia(6, cacheTopValor.length === 0 ? "No hay productos con valor de inventario registrado." : "Ningún producto coincide con la búsqueda.");
  }

  function inicializarOrdenamientoTopValor() {
    document.querySelectorAll('#tbodyTopValor').length; // noop, mantiene el bloque documentado
    document.querySelectorAll("th.th-ordenable").forEach((th) => {
      th.addEventListener("click", () => {
        const campo = th.dataset.campo;
        if (ordenTopValor.campo === campo) {
          ordenTopValor.asc = !ordenTopValor.asc;
        } else {
          ordenTopValor = { campo, asc: true };
        }
        document.querySelectorAll("th.th-ordenable").forEach((otro) => {
          otro.classList.toggle("activo", otro === th);
          const icono = otro.querySelector(".bi");
          if (!icono) return;
          if (otro === th) {
            icono.className = ordenTopValor.asc ? "bi bi-sort-up" : "bi bi-sort-down";
          } else {
            icono.className = "bi bi-arrow-down-up";
          }
        });
        pintarTopValor();
      });
    });
  }

  async function cargarTopValor() {
    const limite = selectLimiteTopValor.value ? Number(selectLimiteTopValor.value) : undefined;
    const r = await apiGet("/api/reportes-gerenciales-inventario/top-valor", { limite });
    cacheTopValor = r.productos;
    pintarTopValor();
    return r;
  }

  // ---------- 3) Productos críticos ----------
  const inputBuscarCriticos = document.getElementById("inputBuscarCriticos");
  const selectTipoRiesgo = document.getElementById("selectTipoRiesgo");
  const tbodyCriticos = document.getElementById("tbodyCriticos");

  const ETIQUETA_TIPO_RIESGO = {
    BAJO_STOCK: "Bajo stock",
    RIESGO_MERMA: "Riesgo de merma",
    VENCIMIENTO: "Vencimiento",
  };
  // nivel_riesgo (Backend) -> semáforo de presentación (Frontend, ver
  // cabecera del archivo). MEDIO ya es el nivel más bajo que devuelve
  // este endpoint (no expone un caso "sin riesgo" en esta lista, porque
  // solo lista productos que SÍ son críticos), así que no hay VERDE aquí.
  const SEMAFORO_POR_NIVEL = { MEDIO: "AMARILLO", ALTO: "ROJO", CRITICO: "ROJO" };
  const COLOR_BADGE_POR_NIVEL = { MEDIO: "warning", ALTO: "danger", CRITICO: "danger" };

  function filaCritico(p) {
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
  }

  function pintarCriticos() {
    const termino = (inputBuscarCriticos.value || "").trim().toLowerCase();
    const tipo = selectTipoRiesgo.value;
    const filas = cacheCriticos.filter((p) => {
      const coincideTermino =
        !termino || p.producto.toLowerCase().includes(termino) || p.codigo_producto.toLowerCase().includes(termino);
      const coincideTipo = !tipo || p.tipo_riesgo === tipo;
      return coincideTermino && coincideTipo;
    });
    tbodyCriticos.innerHTML = filas.length
      ? filas.map(filaCritico).join("")
      : filaVacia(6, cacheCriticos.length === 0 ? "No hay productos críticos registrados." : "Ningún producto coincide con la búsqueda/filtro.");
    document.getElementById("countCriticos").textContent = `(${U.formatearNumero(cacheCriticos.length)})`;
  }

  async function cargarCriticos() {
    const r = await apiGet("/api/reportes-gerenciales-inventario/productos-criticos");
    cacheCriticos = r.productos;
    pintarCriticos();
    return r;
  }

  // ---------- 4) Productos sin rotación ----------
  const inputBuscarSinRotacion = document.getElementById("inputBuscarSinRotacion");
  const inputDiasSinRotacion = document.getElementById("inputDiasSinRotacion");
  const btnAplicarSinRotacion = document.getElementById("btnAplicarSinRotacion");
  const tbodySinRotacion = document.getElementById("tbodySinRotacion");

  // Semáforo de presentación (Frontend): todo lo que llega en esta lista
  // ya superó el umbral de días sin rotación del Backend (o nunca tuvo
  // movimiento), así que no hay VERDE. "Nunca tuvo movimiento" (null) se
  // trata como el caso más severo (ROJO): no hay forma de saber desde
  // cuándo está inmovilizado. Si sí hay dato, se gradúa sobre el doble
  // del umbral aplicado (mismo umbral que ya se envió al Backend).
  function calcularSemaforoSinRotacion(dias, umbralAplicado) {
    if (dias === null || dias === undefined) return "ROJO";
    const referencia = umbralAplicado && umbralAplicado > 0 ? umbralAplicado : 30;
    return dias >= referencia * 2 ? "ROJO" : "AMARILLO";
  }

  let umbralSinRotacionAplicado = null; // se fija con el valor real que devuelva el Backend (generado_en no lo trae, pero el input sí queda como referencia).

  function filaSinRotacion(p) {
    const semaforo = calcularSemaforoSinRotacion(p.dias_sin_movimiento, umbralSinRotacionAplicado);
    const colorBadge = semaforo === "ROJO" ? "danger" : "warning";
    const dias = p.dias_sin_movimiento === null || p.dias_sin_movimiento === undefined
      ? "Sin movimiento registrado"
      : U.formatearNumero(p.dias_sin_movimiento);
    return `
      <tr class="${semaforo === "ROJO" ? "table-danger" : ""}">
        <td>${U.escaparHtml(p.producto)}</td>
        <td><code>${U.escaparHtml(p.codigo_producto)}</code></td>
        <td class="text-end">${dias}</td>
        <td class="text-end">${U.formatearNumero(p.stock_actual, 2)}</td>
        <td class="text-end">${U.formatearMoneda(p.valor_inventario)}</td>
        <td>${dotSemaforo(semaforo)} ${badgeNivel(semaforo, colorBadge)}</td>
      </tr>`;
  }

  function pintarSinRotacion() {
    const termino = (inputBuscarSinRotacion.value || "").trim().toLowerCase();
    const filas = cacheSinRotacion.filter(
      (p) =>
        !termino ||
        p.producto.toLowerCase().includes(termino) ||
        p.codigo_producto.toLowerCase().includes(termino)
    );
    tbodySinRotacion.innerHTML = filas.length
      ? filas.map(filaSinRotacion).join("")
      : filaVacia(6, cacheSinRotacion.length === 0 ? "No hay productos sin rotación para el umbral aplicado." : "Ningún producto coincide con la búsqueda.");
    document.getElementById("countSinRotacion").textContent = `(${U.formatearNumero(cacheSinRotacion.length)})`;
  }

  async function cargarSinRotacion() {
    const diasStr = inputDiasSinRotacion.value;
    const dias = diasStr ? Number(diasStr) : undefined;
    if (dias !== undefined && dias <= 0) {
      const mensaje = "'Días mínimos sin movimiento' debe ser un número entero mayor a 0.";
      mostrarError(mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
      throw new Error(mensaje);
    }
    umbralSinRotacionAplicado = dias ?? null;
    const r = await apiGet("/api/reportes-gerenciales-inventario/sin-rotacion", { dias_sin_rotacion: dias });
    cacheSinRotacion = r.productos;
    pintarSinRotacion();
    return r;
  }

  // ---------- Carga principal ----------
  async function cargarTodo() {
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    btnActualizar.disabled = true;
    try {
      const [resumen, , criticos, sinRotacion] = await Promise.all([
        apiGet("/api/reportes-gerenciales-inventario/resumen"),
        cargarTopValor(),
        cargarCriticos(),
        cargarSinRotacion(),
      ]);
      pintarKpisResumen(resumen);
      pintarKpiCriticos(criticos.total_productos);
      pintarKpiSinRotacion(sinRotacion.total_productos);

      document.getElementById("infoActualizado").textContent =
        `Actualizado: ${U.formatearFechaHora(criticos.generado_en)}`;
    } catch (err) {
      const mensaje = err?.message || "No se pudo cargar los Reportes Gerenciales de Inventario.";
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

    inicializarOrdenamientoTopValor();

    btnActualizar.addEventListener("click", cargarTodo);
    inputBuscarTopValor.addEventListener("input", U.debounce(pintarTopValor, 200));
    selectLimiteTopValor.addEventListener("change", () => {
      cargarTopValor().catch((err) => {
        mostrarError(err.message || "No se pudo cargar el Top valor inventario.");
        if (window.UI) window.UI.toast(err.message || "No se pudo cargar el Top valor inventario.", "error");
      });
    });

    inputBuscarCriticos.addEventListener("input", U.debounce(pintarCriticos, 200));
    selectTipoRiesgo.addEventListener("change", pintarCriticos);

    inputBuscarSinRotacion.addEventListener("input", U.debounce(pintarSinRotacion, 200));
    btnAplicarSinRotacion.addEventListener("click", () => {
      cargarSinRotacion().catch((err) => {
        mostrarError(err.message || "No se pudo cargar Productos sin rotación.");
        if (window.UI) window.UI.toast(err.message || "No se pudo cargar Productos sin rotación.", "error");
      });
    });

    cargarTodo();
  }

  iniciar();
})();
