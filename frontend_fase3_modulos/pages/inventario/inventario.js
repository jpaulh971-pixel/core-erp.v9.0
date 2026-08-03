/**
 * pages/inventario/inventario.js — Page-script del módulo m03_inventario
 * (app/modules/m03_inventario).
 *
 * FASE F2 — se parte del contrato ya confirmado en F1 (comentario
 * heredado abajo) y NO se agrega ningún endpoint nuevo. Todo lo nuevo de
 * esta fase (búsqueda, filtros, paginación, Alertas, Movimientos) se
 * construye en el cliente sobre las mismas 8 llamadas de siempre.
 *
 * Endpoints (contrato REAL confirmado contra router.py + schemas.py de
 * m03_inventario, sin endpoints "puente" ni cambios de modelo):
 *   GET  /api/inventario/inventarios                      -> list[InventarioOut]
 *   POST /api/inventario/inventarios  body InventarioCrear (codigo, nombre) -> InventarioOut (201)
 *   GET  /api/inventario/inventarios/{inventario_id}/productos -> list[ProductoInventarioOut]
 *   GET  /api/inventario/saldos/{inventario_id}            -> list[SaldoProductoOut]
 *   POST /api/inventario/ingresos  body IngresoInventarioCrear (incluye inventario_id) -> MovimientoKardexOut (201)
 *   POST /api/inventario/salidas   body SalidaInventarioCrear  (incluye inventario_id) -> list[MovimientoKardexOut] (201, FEFO)
 *   POST /api/inventario/ajustes   body AjusteInventarioCrear  -> MovimientoKardexOut (201)
 *   GET  /api/inventario/kardex/{producto_inventario_id}  -> list[MovimientoKardexOut]
 *   GET  /api/productos?solo_activos=true                  -> list[ProductoOut] (para los <select> de Ingreso/Salida)
 *
 * Notas de compatibilidad (heredadas de F1, 2026-07-26): el Backend no
 * tiene "almacén" como concepto propio (es "Inventario"), no expone
 * /saldos sin {inventario_id}, y el Kardex se consulta por
 * producto_inventario_id, no por producto_id directo.
 *
 * Actualización (multi-inventario): el Backend ya soportaba varios
 * Inventarios (GET/POST /api/inventario/inventarios); esta pantalla
 * ahora expone un selector para elegir cuál está activo y un botón
 * "Nuevo Inventario" que usa el mismo POST ya existente. No se agrega
 * ningún endpoint nuevo.
 *
 * El Backend NO expone un endpoint para listar lotes de forma directa:
 * el lote_id de cada movimiento sale de su propia fila de kardex. Por
 * eso "Movimientos"/"Lotes" en esta fase se resuelven leyendo el kardex
 * de cada producto con saldo y uniendo el resultado en el cliente (ver
 * cargarMovimientosGlobales), no inventando un endpoint agregado ni un
 * selector de lotes aparte.
 *
 * Hallazgos de contrato para esta fase (F2 — Inventario):
 * - SaldoProductoOut no trae costo ni valor: no hay "stock valorizado"
 *   que mostrar sin inventar un cálculo que el Backend no respalda. (Ver
 *   FASE 3 más abajo: esto se resolvió cruzando con otro endpoint ya
 *   existente, no agregando un cálculo nuevo.)
 * - No existe el concepto de stock reservado/comprometido: "Disponible"
 *   se muestra igual a "Stock total" (documentado en pantalla), no como
 *   una resta que el Backend no calcula.
 * - Puede haber varios Inventarios: no hay "stock por almacén" que
 *   desglosar dentro de uno mismo; el selector de la cabecera cambia
 *   cuál inventario está activo y recarga Saldos/Alertas/Kardex/
 *   Movimientos para ese inventario.
 * - MovimientoKardexOut no trae fecha_vencimiento en la lectura (solo se
 *   envía como entrada opcional en /ingresos): no se agrega una columna
 *   de vencimiento en Kardex/Movimientos que el Backend no devuelve.
 *
 * FASE 3 — Costo Unitario en Saldos/Alertas (backend intacto, mismo
 * patrón ya usado en pages/productos/productos.js).
 * SaldoProductoOut (GET /api/inventario/saldos/{inventario_id}) sigue sin
 * traer costo ni valor — ese contrato no cambió y no se tocó. Lo que sí
 * ya existe, de solo lectura, es:
 *   GET /api/reportes/inventario-valorizado (m19_reportes, sin params)
 *     -> ReporteInventarioValorizado.productos[]: { producto_id, codigo,
 *        nombre, cantidad_actual, valor_promedio_unitario, valor_total,
 *        stock_minimo, bajo_stock_minimo }
 * Es el MISMO endpoint que ya usan pages/reportes/reportes.js (pestaña
 * "Inventario valorizado") y pages/productos/productos.js. Saldos y
 * Alertas ahora cruzan cada fila (por `producto_id`, no por
 * `producto_inventario_id`) contra ese resultado y pintan "Costo
 * Unitario" (`valor_promedio_unitario`) y "Costo Total" (`valor_total`)
 * tal cual los entrega el Backend — NO se calcula
 * "Costo Unitario = Valor / Cantidad" ni ninguna otra aritmética de
 * costeo en este archivo. Si el producto no aparece en ese resultado
 * (sin lotes/movimientos todavía) las 2 columnas muestran "—".
 * CAVEAT documentado (no es un bug, es el contrato real del endpoint):
 * `inventario-valorizado` agrega el costo/valor de un producto sumando
 * TODOS los Inventarios en los que tenga lotes (no filtra por
 * inventario_id), mientras que Saldos/Alertas de esta pantalla sí están
 * acotados al Inventario activo del selector. Si un producto solo existe
 * en un Inventario esto no se nota; si llegara a tener lotes en más de
 * uno, "Costo Total" reflejaría la suma de todos, no solo la del
 * Inventario activo. Se documenta en pantalla (nota bajo el filtro de
 * Saldos) en vez de intentar filtrar por inventario_id, que el Backend
 * no expone en este endpoint.
 *
 * FASE FRONTEND — INVENTARIO (KPIs, semáforo, Lotes, Próximos a vencer,
 * Inteligencia de inventario, exportación). 100% aditivo sobre lo de
 * arriba: no se elimina ni renombra ninguna función existente, no se
 * agrega ningún endpoint nuevo. Endpoints reales adicionales que consume
 * esta fase (verificados contra el ZIP real, no inventados):
 *   GET /api/dashboard/resumen (m01_dashboard, ya usado por dashboard.js)
 *     -> r.inventario.total_productos_activos / valor_total_inventario /
 *        productos_bajo_stock_minimo — mismos 3 campos que pinta
 *        dashboard.js, mismo caveat de alcance global (no filtra por
 *        inventario_id) ya documentado ahí.
 *   GET /api/inteligencia-inventario/{inventario_id}?dias_analisis=N
 *     (m22_inteligencia_inventario) -> ResumenInteligenciaInventario:
 *     { inventario_id, dias_analisis, total_productos,
 *       productos_riesgo_critico, productos_riesgo_alto,
 *       indicadores: [IndicadorInventario, ...] }, cada uno con
 *     stock_actual, rotacion_inventario, dias_inventario,
 *     consumo_promedio_diario/semanal/mensual, dias_restantes_vencimiento,
 *     riesgo_merma. Estos valores NUNCA se recalculan aquí: las 3
 *     tarjetas KPI de rotación/días/consumo son un promedio simple (en el
 *     cliente) de los valores por-producto que ya trae el Backend, y el
 *     KPI de riesgo de merma es la suma de productos_riesgo_alto +
 *     productos_riesgo_critico que el propio Backend ya cuenta.
 *   GET /api/reportes/inventario-por-lote?inventario_id=N (m19_reportes)
 *     -> ReporteInventarioPorLote { generado_en, total_lotes, valor_total,
 *        lotes: [LotePorProducto, ...] }.
 *   GET /api/reportes/proximos-vencer?inventario_id=N (m19_reportes)
 *     -> ReporteProximosVencer { generado_en, total_lotes, activos,
 *        proximos_a_vencer, vencidos, valor_total_comprometido,
 *        lotes: [LoteProximoVencer, ...] }.
 *   GET /api/reportes/inventario-por-lote/exportar/{excel|pdf}
 *   GET /api/reportes/proximos-vencer/exportar/{excel|pdf}
 *     — mismos 2 reportes de arriba, en binario; se descargan con un
 *     helper local (descargarArchivoProtegido) porque api-client.js solo
 *     sabe hacer resp.json() y esta fase no debe tocar api-client.js (es
 *     compartido por otras 18 páginas, fuera del alcance declarado).
 *   Campo `semaforo_stock` de SaldoProductoOut (GET
 *     /api/inventario/saldos/{inventario_id}, endpoint que esta pantalla
 *     YA consumía desde F2): VERDE/AMARILLO/ROJO, ya calculado por el
 *     Backend — solo se pinta como badge, no se deriva de bajo_stock_minimo.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const elError = document.getElementById("estadoError");
  const elAlmacen = document.getElementById("infoAlmacen");

  const btnNuevoIngreso = document.getElementById("btnNuevoIngreso");
  const btnNuevaSalida = document.getElementById("btnNuevaSalida");
  const btnNuevoAjuste = document.getElementById("btnNuevoAjuste");

  const selectInventarioActivo = document.getElementById("selectInventarioActivo");
  const btnNuevoInventario = document.getElementById("btnNuevoInventario");

  let productosCache = [];
  let inventariosCache = []; // list[InventarioOut] (GET /api/inventario/inventarios)
  let inventarioIdActual = null; // id del Inventario elegido en selectInventarioActivo
  let mapaProductoAProductoInventario = {}; // producto_id -> producto_inventario_id
  let mapaProductoInventarioAProducto = {}; // producto_inventario_id -> {id, codigo, nombre}
  // Map<producto_id, {cantidad_actual, valor_promedio_unitario, valor_total}>
  // poblado desde GET /api/reportes/inventario-valorizado (m19_reportes).
  // Mismo patrón que pages/productos/productos.js: nunca se recalcula
  // nada aquí, son los campos que ya trae el Backend.
  let valorizadoPorProducto = new Map();

  function mostrarError(mensaje) {
    elError.textContent = mensaje;
    elError.style.display = "block";
  }

  function ocultarError() {
    elError.style.display = "none";
  }

  async function apiRequest(path, opciones) {
    // FASE F0: delega en el cliente API centralizado (api-client.js).
    return window.Api.request(path, opciones);
  }

  const apiGet = (path) => apiRequest(path);
  const apiPost = (path, body) => apiRequest(path, { method: "POST", body: JSON.stringify(body) });

  function filaVacia(colspan, texto) {
    return `<tr><td colspan="${colspan}" class="text-muted-erp">${texto}</td></tr>`;
  }

  function colorTipoMovimiento(tipo) {
    if (tipo === "INGRESO" || tipo === "AJUSTE_POSITIVO") return "success";
    if (tipo === "SALIDA" || tipo === "AJUSTE_NEGATIVO") return "danger";
    return "secondary";
  }

  function etiquetaTipoMovimiento(tipo) {
    const etiquetas = {
      INGRESO: "Ingreso",
      SALIDA: "Salida",
      AJUSTE_POSITIVO: "Ajuste positivo",
      AJUSTE_NEGATIVO: "Ajuste negativo",
    };
    return etiquetas[tipo] || tipo;
  }

  // ---------- Semáforo (VERDE/AMARILLO/ROJO) ----------
  // Vocabulario compartido por semaforo_stock (m03) y semaforo_vencimiento
  // (m19): ambos son un string VERDE/AMARILLO/ROJO ya calculado por el
  // Backend, esta pantalla solo lo traduce a un badge de Bootstrap. NEGRO
  // se contempla por si el semáforo de vencimiento llega a marcar un lote
  // ya vencido con un color más severo que ROJO (mismo criterio defensivo
  // que "|| tipo" en etiquetaTipoMovimiento: si aparece un valor no
  // mapeado, no se rompe, se muestra tal cual con color neutro).
  function colorSemaforo(valor) {
    const mapa = { VERDE: "success", AMARILLO: "warning", ROJO: "danger", NEGRO: "dark" };
    return mapa[valor] || "secondary";
  }

  function badgeSemaforo(valor) {
    if (!valor) return '<span class="text-muted-erp">—</span>';
    return `<span class="badge text-bg-${colorSemaforo(valor)}">${U.escaparHtml(valor)}</span>`;
  }

  // ---------- Riesgo de merma (BAJO/MEDIO/ALTO/CRITICO, m22) ----------
  function colorRiesgoMerma(valor) {
    const mapa = { BAJO: "success", MEDIO: "warning", ALTO: "danger", CRITICO: "dark" };
    return mapa[valor] || "secondary";
  }

  function badgeRiesgoMerma(valor) {
    if (!valor) return '<span class="text-muted-erp">—</span>';
    return `<span class="badge text-bg-${colorRiesgoMerma(valor)}">${U.escaparHtml(valor)}</span>`;
  }

  // ---------- Paginador genérico reutilizable (Saldos/Alertas/Kardex/Movimientos) ----------
  // El Backend no expone "page"/"limit" en ninguno de los 8 endpoints de
  // arriba, así que -mismo criterio ya usado en productos.js/clientes.js/
  // proveedores.js de F1- la paginación de las 4 tablas de esta pantalla
  // se resuelve en el cliente sobre listas ya cargadas.
  function crearPaginador(selectTamanio, resumenEl, controlesEl, onRepintar) {
    let paginaActual = 1;

    function paginar(lista) {
      const tamanio = Number(selectTamanio.value) || 10;
      const totalPaginas = Math.max(1, Math.ceil(lista.length / tamanio));
      if (paginaActual > totalPaginas) paginaActual = totalPaginas;
      if (paginaActual < 1) paginaActual = 1;
      const inicio = (paginaActual - 1) * tamanio;
      const pagina = lista.slice(inicio, inicio + tamanio);
      return { pagina, totalPaginas, inicio, total: lista.length };
    }

    function pintarControles(info) {
      const { totalPaginas, inicio, pagina, total } = info;
      resumenEl.textContent = total === 0 ? "Sin resultados" : `Mostrando ${inicio + 1}–${inicio + pagina.length} de ${total}`;

      controlesEl.innerHTML = "";
      if (totalPaginas <= 1) return;

      function itemPagina(etiqueta, pagDestino, deshabilitado, activo) {
        const li = document.createElement("li");
        li.className = `page-item${deshabilitado ? " disabled" : ""}${activo ? " active" : ""}`;
        const a = document.createElement("a");
        a.className = "page-link";
        a.href = "#";
        a.textContent = etiqueta;
        if (!deshabilitado && !activo) {
          a.addEventListener("click", (ev) => {
            ev.preventDefault();
            paginaActual = pagDestino;
            onRepintar();
          });
        }
        li.appendChild(a);
        return li;
      }

      controlesEl.appendChild(itemPagina("«", paginaActual - 1, paginaActual === 1, false));
      for (let n = 1; n <= totalPaginas; n += 1) {
        controlesEl.appendChild(itemPagina(String(n), n, false, n === paginaActual));
      }
      controlesEl.appendChild(itemPagina("»", paginaActual + 1, paginaActual === totalPaginas, false));
    }

    return {
      calcular(lista) {
        const info = paginar(lista);
        pintarControles(info);
        return info;
      },
      reiniciar() {
        paginaActual = 1;
      },
    };
  }

  // ---------- Inventario (el Backend usa "Inventario", no "Almacén") ----------
  // Carga la lista de inventarios y pinta el <select> de la cabecera.
  // Si `idAConservar` sigue existiendo en la lista nueva, se mantiene
  // seleccionado (por ejemplo, tras crear un inventario nuevo se pasa su
  // propio id para que quede activo de inmediato).
  async function cargarInventarios(idAConservar) {
    inventariosCache = await apiGet("/api/inventario/inventarios");
    if (!inventariosCache.length) {
      selectInventarioActivo.innerHTML = `<option value="">Sin inventarios</option>`;
      inventarioIdActual = null;
      elAlmacen.textContent = "No hay ningún inventario creado todavía. Usa \"Nuevo Inventario\" para crear el primero.";
      throw new Error("No hay ningún inventario creado todavía.");
    }

    const idsDisponibles = inventariosCache.map((i) => i.id);
    let idSeleccionado = null;
    if (idAConservar !== undefined && idAConservar !== null && idsDisponibles.includes(idAConservar)) {
      idSeleccionado = idAConservar;
    } else if (inventarioIdActual !== null && idsDisponibles.includes(inventarioIdActual)) {
      idSeleccionado = inventarioIdActual;
    } else {
      const porDefecto = inventariosCache.find((i) => i.codigo === "INV-001") || inventariosCache[0];
      idSeleccionado = porDefecto.id;
    }

    selectInventarioActivo.innerHTML = inventariosCache
      .map((inv) => `<option value="${inv.id}">${U.escaparHtml(inv.codigo)} — ${U.escaparHtml(inv.nombre)}</option>`)
      .join("");
    selectInventarioActivo.value = String(idSeleccionado);
    inventarioIdActual = idSeleccionado;

    const seleccionado = inventariosCache.find((i) => i.id === inventarioIdActual);
    elAlmacen.textContent = seleccionado
      ? `Almacén activo: ${seleccionado.nombre} (${seleccionado.codigo}) — ${inventariosCache.length} inventario(s) registrado(s)`
      : "";
    return inventarioIdActual;
  }

  async function obtenerInventarioIdActual() {
    if (inventarioIdActual !== null) return inventarioIdActual;
    return cargarInventarios();
  }

  // =====================================================================
  // SALDOS
  // =====================================================================
  const inputBuscarSaldos = document.getElementById("inputBuscarSaldos");
  const selectEstadoSaldos = document.getElementById("selectEstadoSaldos");
  const tbodySaldos = document.getElementById("tbodySaldos");
  const selectTamanioPaginaSaldos = document.getElementById("selectTamanioPaginaSaldos");
  const paginadorSaldos = crearPaginador(
    selectTamanioPaginaSaldos,
    document.getElementById("paginacionResumenSaldos"),
    document.getElementById("paginacionControlesSaldos"),
    () => pintarSaldos()
  );

  let saldosCache = [];

  // Consume el mismo endpoint ya usado por productos.js y reportes.js.
  // No es un endpoint nuevo ni un cálculo nuevo: solo se lee y se cruza
  // en memoria por producto_id. Si falla, no rompe Saldos/Alertas: el Map
  // queda vacío y las columnas de costo muestran "—" (mismo criterio que
  // productos.js).
  async function cargarValorizado() {
    try {
      const r = await apiGet("/api/reportes/inventario-valorizado");
      valorizadoPorProducto = new Map(
        (r.productos || []).map((p) => [
          p.producto_id,
          {
            cantidad_actual: p.cantidad_actual,
            valor_promedio_unitario: p.valor_promedio_unitario,
            valor_total: p.valor_total,
          },
        ])
      );
    } catch (err) {
      valorizadoPorProducto = new Map();
      console.error("inventario.js: no se pudo cargar /api/reportes/inventario-valorizado.", err);
    }
  }

  // Un producto con stock > 0 pero stock_minimo = 0 (no configurado en la
  // ficha del producto) NUNCA puede disparar "bajo_stock_minimo" (0 < 0 es
  // falso), así que sin esto la pestaña Alertas se queda vacía en
  // silencio aunque el producto nunca haya tenido un umbral definido. Se
  // trata como categoría propia (advertencia de configuración), distinta
  // de "bajo mínimo" real, para no confundir ambos casos.
  function sinMinimoConfigurado(s) {
    return s.stock_minimo <= 0 && s.stock_total > 0;
  }

  function filtrarSaldos(lista, { soloAlertas } = {}) {
    let resultado = lista;
    if (soloAlertas) resultado = resultado.filter((s) => s.bajo_stock_minimo || sinMinimoConfigurado(s));

    const inputActivo = soloAlertas ? document.getElementById("inputBuscarAlertas") : inputBuscarSaldos;
    const q = inputActivo.value.trim().toLowerCase();
    if (q) {
      resultado = resultado.filter(
        (s) => (s.codigo_interno || "").toLowerCase().includes(q) || s.nombre.toLowerCase().includes(q)
      );
    }

    if (!soloAlertas) {
      const estado = selectEstadoSaldos.value;
      if (estado === "ok") resultado = resultado.filter((s) => !s.bajo_stock_minimo);
      if (estado === "bajo") resultado = resultado.filter((s) => s.bajo_stock_minimo);
    }

    return resultado;
  }

  function filaSaldo(s, { conEstado }) {
    // Cruce de solo lectura por producto_id contra el Map ya poblado
    // desde GET /api/reportes/inventario-valorizado. Si el producto no
    // tiene fila ahí (sin lotes/movimientos todavía) se muestra "—" en
    // vez de un 0 engañoso o un cálculo inventado. Ningún valor se
    // recalcula: se leen tal cual del Backend.
    const v = valorizadoPorProducto.get(s.producto_id);
    const costoUnitario = v ? U.formatearMoneda(v.valor_promedio_unitario) : "—";
    const costoTotal = v ? U.formatearMoneda(v.valor_total) : "—";
    const sinMinimo = sinMinimoConfigurado(s);
    let estadoHtml = '<span class="text-muted-erp">OK</span>';
    if (s.bajo_stock_minimo) estadoHtml = '<span class="text-danger fw-bold">Bajo mínimo</span>';
    else if (sinMinimo) estadoHtml = '<span class="text-warning fw-bold">Sin mínimo configurado</span>';
    return `
      <tr class="${s.bajo_stock_minimo ? "table-danger" : sinMinimo ? "table-warning" : ""}">
        <td><code>${U.escaparHtml(s.codigo_interno || "—")}</code></td>
        <td>${U.escaparHtml(s.nombre)}</td>
        <td class="text-end">${U.formatearNumero(s.stock_total, 2)}</td>
        <td class="text-end">${U.formatearNumero(s.stock_total, 2)}</td>
        <td class="text-end">${U.formatearNumero(s.stock_minimo, 2)}</td>
        <td class="text-end">${costoUnitario}</td>
        <td class="text-end">${costoTotal}</td>
        <td>${badgeSemaforo(s.semaforo_stock)}</td>
        ${conEstado ? `<td>${estadoHtml}</td>` : ""}
        <td class="text-end">
          <button type="button" class="btn btn-sm btn-outline-secondary btn-ver-kardex" data-id="${s.producto_inventario_id}" title="Ver kardex">
            <i class="bi bi-clock-history"></i>
          </button>
          <button type="button" class="btn btn-sm btn-outline-secondary btn-ingreso-rapido" data-producto-id="${s.producto_id}" title="Nuevo ingreso">
            <i class="bi bi-box-arrow-in-down"></i>
          </button>
        </td>
      </tr>`;
  }

  function enlazarAccionesFila(tbody) {
    tbody.querySelectorAll(".btn-ver-kardex").forEach((btn) => {
      btn.addEventListener("click", () => irAKardexPorProductoInventario(Number(btn.dataset.id)));
    });
    tbody.querySelectorAll(".btn-ingreso-rapido").forEach((btn) => {
      btn.addEventListener("click", () => abrirModalIngresoConProducto(Number(btn.dataset.productoId)));
    });
  }

  function pintarSaldos() {
    const filtrados = filtrarSaldos(saldosCache, { soloAlertas: false });
    const info = paginadorSaldos.calcular(filtrados);

    tbodySaldos.innerHTML = info.pagina.length
      ? info.pagina.map((s) => filaSaldo(s, { conEstado: true })).join("")
      : filaVacia(
          10,
          saldosCache.length === 0 ? "No hay productos con saldo registrado." : "Ningún producto coincide con la búsqueda/filtro."
        );

    enlazarAccionesFila(tbodySaldos);
    pintarAlertasBadge();
  }

  // =====================================================================
  // ALERTAS (stock bajo mínimo) — mismo dato de Saldos, filtrado en cliente
  // =====================================================================
  const inputBuscarAlertas = document.getElementById("inputBuscarAlertas");
  const tbodyAlertas = document.getElementById("tbodyAlertas");
  const selectTamanioPaginaAlertas = document.getElementById("selectTamanioPaginaAlertas");
  const badgeAlertas = document.getElementById("badgeAlertas");
  const paginadorAlertas = crearPaginador(
    selectTamanioPaginaAlertas,
    document.getElementById("paginacionResumenAlertas"),
    document.getElementById("paginacionControlesAlertas"),
    () => pintarAlertas()
  );

  function pintarAlertas() {
    const filtrados = filtrarSaldos(saldosCache, { soloAlertas: true });
    const info = paginadorAlertas.calcular(filtrados);

    tbodyAlertas.innerHTML = info.pagina.length
      ? info.pagina.map((s) => filaSaldo(s, { conEstado: true })).join("")
      : filaVacia(10, "No hay productos por debajo de su stock mínimo ni sin configurar.");

    enlazarAccionesFila(tbodyAlertas);
  }

  function pintarAlertasBadge() {
    const total = saldosCache.filter((s) => s.bajo_stock_minimo || sinMinimoConfigurado(s)).length;
    if (total > 0) {
      badgeAlertas.textContent = String(total);
      badgeAlertas.style.display = "";
    } else {
      badgeAlertas.style.display = "none";
    }
  }

  async function cargarSaldos() {
    const inventarioId = await obtenerInventarioIdActual();
    // cargarValorizado() es de solo lectura y no depende del inventario_id
    // (GET /api/reportes/inventario-valorizado no acepta parámetros); se
    // pide en paralelo con los saldos y se espera a que ambas resuelvan
    // antes de pintar, para que la primera pintada ya traiga el costo.
    const [saldos] = await Promise.all([apiGet(`/api/inventario/saldos/${inventarioId}`), cargarValorizado()]);
    saldosCache = saldos;
    mapaProductoAProductoInventario = Object.fromEntries(saldosCache.map((s) => [s.producto_id, s.producto_inventario_id]));
    mapaProductoInventarioAProducto = Object.fromEntries(
      saldosCache.map((s) => [
        s.producto_inventario_id,
        { producto_id: s.producto_id, codigo: s.codigo_interno, nombre: s.nombre },
      ])
    );
    paginadorSaldos.reiniciar();
    paginadorAlertas.reiniciar();
    pintarSaldos();
    pintarAlertas();
  }

  // =====================================================================
  // KPIs — mismo diseño del Dashboard, sin cálculos nuevos
  // =====================================================================
  const kpiProductosActivos = document.getElementById("kpiProductosActivos");
  const kpiValorInventario = document.getElementById("kpiValorInventario");
  const kpiBajoStock = document.getElementById("kpiBajoStock");
  const kpiRotacionPromedio = document.getElementById("kpiRotacionPromedio");
  const kpiDiasInventario = document.getElementById("kpiDiasInventario");
  const kpiConsumoPromedio = document.getElementById("kpiConsumoPromedio");
  const kpiRiesgoMerma = document.getElementById("kpiRiesgoMerma");

  // Promedio simple ignorando null/None (mismo criterio que el Backend usa
  // para dias_inventario/rotacion_inventario cuando la división no es
  // válida: se excluyen, no se fuerzan a 0). No es un cálculo de negocio
  // nuevo, es una agregación de UI sobre valores que el Backend ya calculó.
  function promedioSimple(valores) {
    const nums = valores.filter((v) => typeof v === "number" && Number.isFinite(v));
    if (!nums.length) return null;
    return nums.reduce((a, b) => a + b, 0) / nums.length;
  }

  // GET /api/dashboard/resumen — mismo endpoint y mismos 3 campos que ya
  // pinta dashboard.js (r.inventario.total_productos_activos /
  // valor_total_inventario / productos_bajo_stock_minimo). Alcance global
  // (no filtra por inventario_id), igual que /inventario-valorizado.
  async function cargarKpisDashboard() {
    try {
      const r = await apiGet("/api/dashboard/resumen");
      kpiProductosActivos.textContent = U.formatearNumero(r.inventario.total_productos_activos);
      kpiValorInventario.textContent = U.formatearMoneda(r.inventario.valor_total_inventario);
      kpiBajoStock.textContent = U.formatearNumero(r.inventario.productos_bajo_stock_minimo);
    } catch (err) {
      kpiProductosActivos.textContent = "—";
      kpiValorInventario.textContent = "—";
      kpiBajoStock.textContent = "—";
      console.error("inventario.js: no se pudo cargar /api/dashboard/resumen.", err);
    }
  }

  // GET /api/inteligencia-inventario/{inventario_id} — filtrado por el
  // Inventario activo. Repobla también inteligenciaCache para que la
  // pestaña "Inteligencia de inventario" no tenga que repetir el request
  // si el usuario la abre justo después.
  async function cargarKpisInteligencia() {
    if (!inventarioIdActual) return;
    try {
      const dias = leerDiasAnalisisInteligencia();
      const r = await apiGet(
        `/api/inteligencia-inventario/${inventarioIdActual}${dias ? `?dias_analisis=${dias}` : ""}`
      );
      inteligenciaCache = r.indicadores || [];
      const rotaciones = inteligenciaCache.map((i) => i.rotacion_inventario);
      const dias_inv = inteligenciaCache.map((i) => i.dias_inventario);
      const consumos = inteligenciaCache.map((i) => i.consumo_promedio_diario);
      const promRotacion = promedioSimple(rotaciones);
      const promDias = promedioSimple(dias_inv);
      const promConsumo = promedioSimple(consumos);

      kpiRotacionPromedio.textContent = promRotacion === null ? "—" : U.formatearNumero(promRotacion, 2);
      kpiDiasInventario.textContent = promDias === null ? "—" : U.formatearNumero(promDias, 1);
      kpiConsumoPromedio.textContent = promConsumo === null ? "—" : U.formatearNumero(promConsumo, 2);
      // Suma de productos_riesgo_alto + productos_riesgo_critico, campos
      // que el propio ResumenInteligenciaInventario ya trae calculados.
      kpiRiesgoMerma.textContent = U.formatearNumero((r.productos_riesgo_alto || 0) + (r.productos_riesgo_critico || 0));
    } catch (err) {
      kpiRotacionPromedio.textContent = "—";
      kpiDiasInventario.textContent = "—";
      kpiConsumoPromedio.textContent = "—";
      kpiRiesgoMerma.textContent = "—";
      inteligenciaCache = [];
      console.error("inventario.js: no se pudo cargar /api/inteligencia-inventario.", err);
    }
  }

  async function cargarKpis() {
    await Promise.allSettled([cargarKpisDashboard(), cargarKpisInteligencia()]);
  }

  // ---------- Selector de producto (compartido por Kardex y modales) ----------
  async function cargarProductosCache() {
    productosCache = await apiGet("/api/productos?solo_activos=true");
    const opciones = productosCache
      .map((p) => `<option value="${p.id}">${U.escaparHtml(p.codigo)} — ${U.escaparHtml(p.nombre)}</option>`)
      .join("");
    document.querySelectorAll(".select-producto").forEach((sel) => {
      sel.innerHTML = `<option value="">Seleccionar…</option>${opciones}`;
    });
  }

  // =====================================================================
  // KARDEX POR PRODUCTO
  // =====================================================================
  const selectProducto = document.getElementById("selectProductoKardex");
  const selectTipoMovimientoKardex = document.getElementById("selectTipoMovimientoKardex");
  const tbodyKardex = document.getElementById("tbodyKardex");
  const resumenKardex = document.getElementById("resumenKardex");
  const selectTamanioPaginaKardex = document.getElementById("selectTamanioPaginaKardex");
  const tabBtnKardex = document.getElementById("tabBtnKardex");
  const paginadorKardex = crearPaginador(
    selectTamanioPaginaKardex,
    document.getElementById("paginacionResumenKardex"),
    document.getElementById("paginacionControlesKardex"),
    () => pintarKardex()
  );

  let kardexCache = [];

  function filtrarKardex(lista) {
    const tipo = selectTipoMovimientoKardex.value;
    if (tipo === "todos") return lista;
    return lista.filter((m) => m.tipo_movimiento === tipo);
  }

  function pintarKardex() {
    const filtrados = filtrarKardex(kardexCache);
    const info = paginadorKardex.calcular(filtrados);

    tbodyKardex.innerHTML = info.pagina.length
      ? info.pagina
          .map(
            (m) => `
        <tr>
          <td>${U.formatearFechaHora(m.creado_en)}</td>
          <td><span class="badge text-bg-${colorTipoMovimiento(m.tipo_movimiento)}">${etiquetaTipoMovimiento(m.tipo_movimiento)}</span></td>
          <td class="text-end">${U.formatearNumero(m.cantidad, 2)}</td>
          <td class="text-end">${U.formatearMoneda(m.costo_unitario)}</td>
          <td class="text-end">${U.formatearNumero(m.saldo_resultante, 2)}</td>
          <td>${m.lote_id}</td>
          <td>${U.escaparHtml(m.referencia || "—")}</td>
          <td class="text-end">
            <button type="button" class="btn btn-sm btn-outline-secondary btn-ajustar-lote" data-lote="${m.lote_id}">
              Ajustar
            </button>
          </td>
        </tr>`
          )
          .join("")
      : filaVacia(8, kardexCache.length === 0 ? "Este producto no tiene movimientos de kardex." : "Ningún movimiento coincide con el filtro.");

    tbodyKardex.querySelectorAll(".btn-ajustar-lote").forEach((btn) => {
      btn.addEventListener("click", () => abrirModalAjuste(Number(btn.dataset.lote)));
    });
  }

  // cargarKardex recibe producto_inventario_id (lo que el Backend real
  // exige en GET /api/inventario/kardex/{producto_inventario_id}), no el
  // producto_id del catálogo — son ids de tablas distintas.
  async function cargarKardex(productoInventarioId) {
    if (!productoInventarioId) {
      kardexCache = [];
      paginadorKardex.reiniciar();
      tbodyKardex.innerHTML = filaVacia(8, "Selecciona un producto para ver su kardex.");
      document.getElementById("paginacionResumenKardex").textContent = "\u00a0";
      document.getElementById("paginacionControlesKardex").innerHTML = "";
      resumenKardex.textContent = "";
      return;
    }
    kardexCache = await apiGet(`/api/inventario/kardex/${productoInventarioId}`);
    paginadorKardex.reiniciar();
    pintarKardex();
    const productoId = Object.keys(mapaProductoAProductoInventario).find(
      (pid) => mapaProductoAProductoInventario[pid] === productoInventarioId
    );
    const producto = productoId ? productosCache.find((p) => p.id === Number(productoId)) : null;
    resumenKardex.textContent = producto
      ? `${kardexCache.length} movimiento(s) registrados para ${producto.codigo} — ${producto.nombre}.`
      : `${kardexCache.length} movimiento(s) registrados.`;
  }

  async function cargarKardexSeguro(productoInventarioId) {
    ocultarError();
    try {
      await cargarKardex(productoInventarioId);
    } catch (err) {
      mostrarError(err.message || "No se pudo cargar el kardex.");
      if (window.UI) window.UI.toast(err.message || "No se pudo cargar el kardex.", "error");
    }
  }

  // El parámetro que llega aquí es producto_id (catálogo): hay que
  // resolverlo a producto_inventario_id antes de pedir el kardex.
  async function cargarKardexPorProductoId(productoId) {
    if (!productoId) return cargarKardexSeguro(null);
    let productoInventarioId = mapaProductoAProductoInventario[productoId];
    if (!productoInventarioId) {
      // El producto existe en el catálogo pero todavía no tiene
      // presencia registrada en este inventario (sin saldo): no hay
      // producto_inventario_id que consultar todavía.
      kardexCache = [];
      paginadorKardex.reiniciar();
      tbodyKardex.innerHTML = filaVacia(8, "Este producto aún no tiene movimientos registrados en el inventario.");
      resumenKardex.textContent = "";
      return;
    }
    return cargarKardexSeguro(productoInventarioId);
  }

  function irAKardexPorProductoInventario(productoInventarioId) {
    const tab = bootstrap && bootstrap.Tab ? new bootstrap.Tab(tabBtnKardex) : null;
    if (tab) tab.show();
    else tabBtnKardex.click();
    selectTipoMovimientoKardex.value = "todos";
    selectProducto.value = String(
      Object.keys(mapaProductoAProductoInventario).find(
        (pid) => mapaProductoAProductoInventario[pid] === productoInventarioId
      ) || ""
    );
    cargarKardexSeguro(productoInventarioId);
  }

  // =====================================================================
  // MOVIMIENTOS (todos los productos) — vista consolidada en el cliente
  // =====================================================================
  const inputBuscarMovimientos = document.getElementById("inputBuscarMovimientos");
  const selectTipoMovimientoGlobal = document.getElementById("selectTipoMovimientoGlobal");
  const tbodyMovimientos = document.getElementById("tbodyMovimientos");
  const selectTamanioPaginaMovimientos = document.getElementById("selectTamanioPaginaMovimientos");
  const btnActualizarMovimientos = document.getElementById("btnActualizarMovimientos");
  const tabBtnMovimientos = document.getElementById("tabBtnMovimientos");
  const paginadorMovimientos = crearPaginador(
    selectTamanioPaginaMovimientos,
    document.getElementById("paginacionResumenMovimientos"),
    document.getElementById("paginacionControlesMovimientos"),
    () => pintarMovimientos()
  );

  let movimientosCache = [];
  let movimientosCargados = false;

  function filtrarMovimientos(lista) {
    let resultado = lista;
    const tipo = selectTipoMovimientoGlobal.value;
    if (tipo !== "todos") resultado = resultado.filter((m) => m.tipo_movimiento === tipo);

    const q = inputBuscarMovimientos.value.trim().toLowerCase();
    if (q) {
      resultado = resultado.filter(
        (m) =>
          (m._codigoProducto || "").toLowerCase().includes(q) ||
          (m._nombreProducto || "").toLowerCase().includes(q) ||
          String(m.lote_id).includes(q)
      );
    }
    return resultado;
  }

  function pintarMovimientos() {
    const filtrados = filtrarMovimientos(movimientosCache);
    const info = paginadorMovimientos.calcular(filtrados);

    tbodyMovimientos.innerHTML = info.pagina.length
      ? info.pagina
          .map(
            (m) => `
        <tr>
          <td>${U.formatearFechaHora(m.creado_en)}</td>
          <td><code>${U.escaparHtml(m._codigoProducto || "—")}</code> — ${U.escaparHtml(m._nombreProducto || "")}</td>
          <td><span class="badge text-bg-${colorTipoMovimiento(m.tipo_movimiento)}">${etiquetaTipoMovimiento(m.tipo_movimiento)}</span></td>
          <td class="text-end">${U.formatearNumero(m.cantidad, 2)}</td>
          <td class="text-end">${U.formatearMoneda(m.costo_unitario)}</td>
          <td class="text-end">${U.formatearNumero(m.saldo_resultante, 2)}</td>
          <td>${m.lote_id}</td>
          <td>${U.escaparHtml(m.referencia || "—")}</td>
        </tr>`
          )
          .join("")
      : filaVacia(
          8,
          movimientosCargados
            ? "Ningún movimiento coincide con la búsqueda/filtro."
            : "No se han cargado movimientos todavía."
        );
  }

  // Recorre todos los productos_inventario_id que tienen saldo y junta su
  // kardex (mismo endpoint por producto que ya usa la pestaña Kardex).
  // No inventa un endpoint "todos los movimientos": lo compone en el
  // cliente con llamadas repetidas al endpoint real, una por producto.
  async function cargarMovimientosGlobales(forzar) {
    if (movimientosCargados && !forzar) return;
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      const ids = Object.keys(mapaProductoInventarioAProducto).map(Number);
      const listas = await Promise.all(
        ids.map((id) =>
          apiGet(`/api/inventario/kardex/${id}`).then((movs) =>
            movs.map((m) => ({
              ...m,
              _codigoProducto: mapaProductoInventarioAProducto[id].codigo,
              _nombreProducto: mapaProductoInventarioAProducto[id].nombre,
            }))
          )
        )
      );
      movimientosCache = listas.flat().sort((a, b) => new Date(b.creado_en) - new Date(a.creado_en));
      movimientosCargados = true;
      paginadorMovimientos.reiniciar();
      pintarMovimientos();
    } catch (err) {
      mostrarError(err.message || "No se pudieron cargar los movimientos.");
      if (window.UI) window.UI.toast(err.message || "No se pudieron cargar los movimientos.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Descarga de archivos protegidos (Excel/PDF) ----------
  // api-client.js siempre hace resp.json(), así que no sirve para
  // descargar binarios; este helper local hace su propio fetch con el
  // mismo Bearer que usa Api.request, y no modifica api-client.js (fuera
  // del alcance declarado: es compartido por otras 18 páginas). Mismos
  // endpoints de exportación que ya existen en m19_reportes.router — no
  // se agrega ningún endpoint nuevo, solo se consume.
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
    // Intenta usar el nombre de archivo real que manda el Backend
    // (Content-Disposition, mismo header que ya arma _descarga() en
    // m19_reportes.router); si no está disponible, usa el sugerido.
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

  async function descargarSeguro(path, nombreSugerido, boton) {
    ocultarError();
    const textoOriginal = boton ? boton.innerHTML : null;
    if (boton) {
      boton.disabled = true;
      boton.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    }
    try {
      await descargarArchivoProtegido(path, nombreSugerido);
    } catch (err) {
      mostrarError(err.message || "No se pudo descargar el archivo.");
      if (window.UI) window.UI.toast(err.message || "No se pudo descargar el archivo.", "error");
    } finally {
      if (boton) {
        boton.disabled = false;
        boton.innerHTML = textoOriginal;
      }
    }
  }

  // =====================================================================
  // LOTES — GET /api/reportes/inventario-por-lote?inventario_id=N
  // (m19_reportes, ya existente; solo lectura, no agrega cálculos)
  // =====================================================================
  const inputBuscarLotes = document.getElementById("inputBuscarLotes");
  const tbodyLotes = document.getElementById("tbodyLotes");
  const resumenLotes = document.getElementById("resumenLotes");
  const selectTamanioPaginaLotes = document.getElementById("selectTamanioPaginaLotes");
  const btnActualizarLotes = document.getElementById("btnActualizarLotes");
  const btnExportarLotesExcel = document.getElementById("btnExportarLotesExcel");
  const btnExportarLotesPdf = document.getElementById("btnExportarLotesPdf");
  const tabBtnLotes = document.getElementById("tabBtnLotes");
  const paginadorLotes = crearPaginador(
    selectTamanioPaginaLotes,
    document.getElementById("paginacionResumenLotes"),
    document.getElementById("paginacionControlesLotes"),
    () => pintarLotes()
  );

  let lotesCache = [];
  let lotesCargados = false;

  function filtrarLotes(lista) {
    const q = inputBuscarLotes.value.trim().toLowerCase();
    if (!q) return lista;
    return lista.filter(
      (l) =>
        (l.codigo_producto || "").toLowerCase().includes(q) ||
        (l.producto || "").toLowerCase().includes(q) ||
        (l.codigo_lote || "").toLowerCase().includes(q)
    );
  }

  function pintarLotes() {
    const filtrados = filtrarLotes(lotesCache);
    const info = paginadorLotes.calcular(filtrados);

    tbodyLotes.innerHTML = info.pagina.length
      ? info.pagina
          .map(
            (l) => `
        <tr>
          <td>${U.escaparHtml(l.producto)}</td>
          <td><code>${U.escaparHtml(l.codigo_producto || "—")}</code></td>
          <td>${U.escaparHtml(l.codigo_lote || "—")}</td>
          <td>${l.fecha_ingreso ? U.formatearFecha(l.fecha_ingreso) : "—"}</td>
          <td>${l.fecha_elaboracion ? U.formatearFecha(l.fecha_elaboracion) : "—"}</td>
          <td>${l.fecha_vencimiento ? U.formatearFecha(l.fecha_vencimiento) : "—"}</td>
          <td class="text-end">${U.formatearNumero(l.cantidad_disponible, 2)}</td>
          <td class="text-end">${U.formatearMoneda(l.costo_unitario)}</td>
          <td class="text-end">${U.formatearMoneda(l.valor_total_lote)}</td>
          <td>${U.escaparHtml(l.estado_lote || "—")}</td>
          <td>${badgeSemaforo(l.semaforo_vencimiento)}</td>
          <td>${U.escaparHtml(l.proveedor || "—")}</td>
        </tr>`
          )
          .join("")
      : filaVacia(12, lotesCargados ? "Ningún lote coincide con la búsqueda." : "No hay lotes registrados para este Inventario.");
  }

  async function cargarLotes(forzar) {
    if (!inventarioIdActual) return;
    if (lotesCargados && !forzar) return;
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      const r = await apiGet(`/api/reportes/inventario-por-lote?inventario_id=${inventarioIdActual}`);
      lotesCache = r.lotes || [];
      lotesCargados = true;
      resumenLotes.textContent = `${r.total_lotes} lote(s) — valor total ${U.formatearMoneda(r.valor_total)}. Generado ${U.formatearFechaHora(r.generado_en)}.`;
      paginadorLotes.reiniciar();
      pintarLotes();
    } catch (err) {
      mostrarError(err.message || "No se pudieron cargar los lotes.");
      if (window.UI) window.UI.toast(err.message || "No se pudieron cargar los lotes.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // =====================================================================
  // PRÓXIMOS A VENCER — GET /api/reportes/proximos-vencer?inventario_id=N
  // (m19_reportes, ya existente; solo lectura, no agrega cálculos)
  // =====================================================================
  const inputBuscarProximosVencer = document.getElementById("inputBuscarProximosVencer");
  const selectCategoriaProximosVencer = document.getElementById("selectCategoriaProximosVencer");
  const tbodyProximosVencer = document.getElementById("tbodyProximosVencer");
  const resumenProximosVencer = document.getElementById("resumenProximosVencer");
  const selectTamanioPaginaProximosVencer = document.getElementById("selectTamanioPaginaProximosVencer");
  const btnActualizarProximosVencer = document.getElementById("btnActualizarProximosVencer");
  const btnExportarProximosVencerExcel = document.getElementById("btnExportarProximosVencerExcel");
  const btnExportarProximosVencerPdf = document.getElementById("btnExportarProximosVencerPdf");
  const badgeProximosVencer = document.getElementById("badgeProximosVencer");
  const tabBtnProximosVencer = document.getElementById("tabBtnProximosVencer");
  const paginadorProximosVencer = crearPaginador(
    selectTamanioPaginaProximosVencer,
    document.getElementById("paginacionResumenProximosVencer"),
    document.getElementById("paginacionControlesProximosVencer"),
    () => pintarProximosVencer()
  );

  let proximosVencerCache = [];
  let proximosVencerCargados = false;

  function filtrarProximosVencer(lista) {
    let resultado = lista;
    const categoria = selectCategoriaProximosVencer.value;
    if (categoria !== "todos") resultado = resultado.filter((l) => l.categoria === categoria);

    const q = inputBuscarProximosVencer.value.trim().toLowerCase();
    if (q) {
      resultado = resultado.filter(
        (l) =>
          (l.codigo_producto || "").toLowerCase().includes(q) ||
          (l.producto || "").toLowerCase().includes(q) ||
          (l.codigo_lote || "").toLowerCase().includes(q)
      );
    }
    return resultado;
  }

  function pintarProximosVencer() {
    const filtrados = filtrarProximosVencer(proximosVencerCache);
    const info = paginadorProximosVencer.calcular(filtrados);

    tbodyProximosVencer.innerHTML = info.pagina.length
      ? info.pagina
          .map(
            (l) => `
        <tr>
          <td><code>${U.escaparHtml(l.codigo_producto || "—")}</code> — ${U.escaparHtml(l.producto)}</td>
          <td>${U.escaparHtml(l.codigo_lote || "—")}</td>
          <td>${U.formatearFecha(l.fecha_vencimiento)}</td>
          <td class="text-end">${l.dias_restantes === null || l.dias_restantes === undefined ? "—" : U.formatearNumero(l.dias_restantes)}</td>
          <td class="text-end">${U.formatearNumero(l.cantidad_disponible, 2)}</td>
          <td class="text-end">${U.formatearMoneda(l.valor_stock_comprometido)}</td>
          <td>${U.escaparHtml(l.estado_lote || "—")}</td>
          <td>${badgeSemaforo(l.semaforo_vencimiento)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(8, proximosVencerCargados ? "Ningún lote coincide con la búsqueda/filtro." : "No hay lotes próximos a vencer para este Inventario.");
  }

  function pintarBadgeProximosVencer(r) {
    const total = (r.proximos_a_vencer || 0) + (r.vencidos || 0);
    if (total > 0) {
      badgeProximosVencer.textContent = String(total);
      badgeProximosVencer.style.display = "";
    } else {
      badgeProximosVencer.style.display = "none";
    }
  }

  async function cargarProximosVencer(forzar) {
    if (!inventarioIdActual) return;
    if (proximosVencerCargados && !forzar) return;
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      const r = await apiGet(`/api/reportes/proximos-vencer?inventario_id=${inventarioIdActual}`);
      proximosVencerCache = r.lotes || [];
      proximosVencerCargados = true;
      resumenProximosVencer.textContent = `${r.total_lotes} lote(s) — ${r.activos} activo(s), ${r.proximos_a_vencer} próximo(s) a vencer, ${r.vencidos} vencido(s). Valor comprometido: ${U.formatearMoneda(r.valor_total_comprometido)}.`;
      pintarBadgeProximosVencer(r);
      paginadorProximosVencer.reiniciar();
      pintarProximosVencer();
    } catch (err) {
      mostrarError(err.message || "No se pudieron cargar los próximos a vencer.");
      if (window.UI) window.UI.toast(err.message || "No se pudieron cargar los próximos a vencer.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // =====================================================================
  // INTELIGENCIA DE INVENTARIO (Fase 3) —
  // GET /api/inteligencia-inventario/{inventario_id}?dias_analisis=N
  // (m22_inteligencia_inventario, ya existente; solo lectura)
  // =====================================================================
  const inputBuscarInteligencia = document.getElementById("inputBuscarInteligencia");
  const selectDiasAnalisisInteligencia = document.getElementById("selectDiasAnalisisInteligencia");
  const tbodyInteligencia = document.getElementById("tbodyInteligencia");
  const resumenInteligencia = document.getElementById("resumenInteligencia");
  const selectTamanioPaginaInteligencia = document.getElementById("selectTamanioPaginaInteligencia");
  const btnActualizarInteligencia = document.getElementById("btnActualizarInteligencia");
  const tabBtnInteligencia = document.getElementById("tabBtnInteligencia");
  const paginadorInteligencia = crearPaginador(
    selectTamanioPaginaInteligencia,
    document.getElementById("paginacionResumenInteligencia"),
    document.getElementById("paginacionControlesInteligencia"),
    () => pintarInteligencia()
  );

  let inteligenciaCache = [];
  let inteligenciaCargada = false;

  function leerDiasAnalisisInteligencia() {
    const v = Number(selectDiasAnalisisInteligencia.value);
    return v > 0 ? v : null;
  }

  function filtrarInteligencia(lista) {
    const q = inputBuscarInteligencia.value.trim().toLowerCase();
    if (!q) return lista;
    return lista.filter(
      (i) => (i.codigo_interno || "").toLowerCase().includes(q) || i.nombre.toLowerCase().includes(q)
    );
  }

  function pintarInteligencia() {
    const filtrados = filtrarInteligencia(inteligenciaCache);
    const info = paginadorInteligencia.calcular(filtrados);

    tbodyInteligencia.innerHTML = info.pagina.length
      ? info.pagina
          .map(
            (i) => `
        <tr>
          <td><code>${U.escaparHtml(i.codigo_interno || "—")}</code></td>
          <td>${U.escaparHtml(i.nombre)}</td>
          <td class="text-end">${U.formatearNumero(i.stock_actual, 2)}</td>
          <td class="text-end">${i.rotacion_inventario === null || i.rotacion_inventario === undefined ? "—" : U.formatearNumero(i.rotacion_inventario, 2)}</td>
          <td class="text-end">${i.dias_inventario === null || i.dias_inventario === undefined ? "—" : U.formatearNumero(i.dias_inventario, 1)}</td>
          <td class="text-end">${U.formatearNumero(i.consumo_promedio_diario, 2)}</td>
          <td class="text-end">${U.formatearNumero(i.consumo_promedio_semanal, 2)}</td>
          <td class="text-end">${U.formatearNumero(i.consumo_promedio_mensual, 2)}</td>
          <td class="text-end">${i.dias_restantes_vencimiento === null || i.dias_restantes_vencimiento === undefined ? "—" : U.formatearNumero(i.dias_restantes_vencimiento)}</td>
          <td>${badgeRiesgoMerma(i.riesgo_merma)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(10, inteligenciaCargada ? "Ningún producto coincide con la búsqueda." : "No hay indicadores para este Inventario.");
  }

  async function cargarInteligencia(forzar) {
    if (!inventarioIdActual) return;
    if (inteligenciaCargada && !forzar && inteligenciaCache.length) {
      pintarInteligencia();
      return;
    }
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      const dias = leerDiasAnalisisInteligencia();
      const r = await apiGet(
        `/api/inteligencia-inventario/${inventarioIdActual}${dias ? `?dias_analisis=${dias}` : ""}`
      );
      inteligenciaCache = r.indicadores || [];
      inteligenciaCargada = true;
      resumenInteligencia.textContent = `${r.total_productos} producto(s) analizados (ventana de ${r.dias_analisis} día(s)) — ${r.productos_riesgo_alto} en riesgo alto, ${r.productos_riesgo_critico} en riesgo crítico.`;
      paginadorInteligencia.reiniciar();
      pintarInteligencia();
    } catch (err) {
      mostrarError(err.message || "No se pudieron cargar los indicadores de inteligencia de inventario.");
      if (window.UI) window.UI.toast(err.message || "No se pudieron cargar los indicadores de inteligencia de inventario.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Modal: Nuevo ingreso ----------
  const modalIngresoEl = document.getElementById("modalIngreso");
  const bootstrapDisponible = typeof bootstrap !== "undefined" && bootstrap.Modal;
  const modalIngreso = bootstrapDisponible ? new bootstrap.Modal(modalIngresoEl) : null;
  const formIngreso = document.getElementById("formIngreso");
  const modalIngresoError = document.getElementById("modalIngresoError");
  const campoIngresoProducto = document.getElementById("ingresoProducto");
  const campoIngresoCodigoLote = document.getElementById("ingresoCodigoLote");
  const campoIngresoCantidad = document.getElementById("ingresoCantidad");
  const campoIngresoCostoUnitario = document.getElementById("ingresoCostoUnitario");
  const campoIngresoFechaVencimiento = document.getElementById("ingresoFechaVencimiento");

  function mostrarErrorModalIngreso(mensaje) {
    modalIngresoError.textContent = mensaje;
    modalIngresoError.style.display = "block";
  }

  function validarFormularioIngreso() {
    if (!campoIngresoProducto.value) {
      mostrarErrorModalIngreso("Selecciona un producto.");
      return false;
    }
    if (!campoIngresoCodigoLote.value.trim()) {
      mostrarErrorModalIngreso("El código de lote no puede estar vacío ni contener solo espacios.");
      campoIngresoCodigoLote.focus();
      return false;
    }
    if (!(Number(campoIngresoCantidad.value) > 0)) {
      mostrarErrorModalIngreso("La cantidad debe ser mayor que cero.");
      campoIngresoCantidad.focus();
      return false;
    }
    if (Number(campoIngresoCostoUnitario.value) < 0) {
      mostrarErrorModalIngreso("El costo unitario no puede ser negativo.");
      campoIngresoCostoUnitario.focus();
      return false;
    }
    if (campoIngresoFechaVencimiento.value) {
      const hoy = new Date();
      hoy.setHours(0, 0, 0, 0);
      const fechaVenc = new Date(campoIngresoFechaVencimiento.value);
      if (fechaVenc < hoy) {
        mostrarErrorModalIngreso("La fecha de vencimiento no puede ser anterior a hoy.");
        campoIngresoFechaVencimiento.focus();
        return false;
      }
    }
    return true;
  }

  function abrirModalIngresoConProducto(productoId) {
    if (!modalIngreso) {
      mostrarError("No se pudo abrir la ventana de nuevo ingreso: Bootstrap no está disponible.");
      return;
    }
    formIngreso.reset();
    modalIngresoError.style.display = "none";
    if (productoId) campoIngresoProducto.value = String(productoId);
    modalIngreso.show();
  }

  async function guardarIngreso(ev) {
    ev.preventDefault();
    modalIngresoError.style.display = "none";
    if (!validarFormularioIngreso()) return;

    // Costo unitario en 0 es válido (ej. muestras gratuitas), pero no debe
    // quedar en 0 por un campo vacío/olvidado sin que el usuario lo note:
    // se pide confirmación explícita, porque un ingreso con costo 0 no
    // suma valor en "Valor Inventario" ni en los reportes de valorización.
    const costoUnitarioIngreso = Number(campoIngresoCostoUnitario.value);
    if (costoUnitarioIngreso === 0) {
      const confirmado = window.UI
        ? await window.UI.confirmar({
            titulo: "Ingreso sin costo unitario",
            mensaje:
              "El costo unitario es 0. Este ingreso NO sumará valor en \"Valor Inventario\" ni en los reportes de valorización (solo es correcto para casos como muestras gratuitas). ¿Confirmas continuar con costo 0?",
            textoAceptar: "Sí, continuar con costo 0",
            variante: "warning",
          })
        : true;
      if (!confirmado) {
        campoIngresoCostoUnitario.focus();
        return;
      }
    }

    const datos = {
      producto_id: Number(campoIngresoProducto.value),
      inventario_id: inventarioIdActual, // obligatorio en IngresoInventarioCrear
      codigo_lote: campoIngresoCodigoLote.value.trim(),
      cantidad: Number(campoIngresoCantidad.value),
      costo_unitario: costoUnitarioIngreso,
      referencia: document.getElementById("ingresoReferencia").value.trim() || null,
    };
    if (campoIngresoFechaVencimiento.value) datos.fecha_vencimiento = new Date(campoIngresoFechaVencimiento.value).toISOString();

    if (window.UI) window.UI.mostrarCargando();
    try {
      await apiPost("/api/inventario/ingresos", datos);
      if (modalIngreso) modalIngreso.hide();
      formIngreso.reset();
      if (window.UI) window.UI.toast("Ingreso de inventario registrado correctamente.", "success");
      await refrescarTodo();
    } catch (err) {
      mostrarErrorModalIngreso(err.message || "No se pudo registrar el ingreso.");
      if (window.UI) window.UI.toast(err.message || "No se pudo registrar el ingreso.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Modal: Registrar salida ----------
  const modalSalidaEl = document.getElementById("modalSalida");
  const modalSalida = bootstrapDisponible ? new bootstrap.Modal(modalSalidaEl) : null;
  const formSalida = document.getElementById("formSalida");
  const modalSalidaError = document.getElementById("modalSalidaError");
  const campoSalidaProducto = document.getElementById("salidaProducto");
  const campoSalidaCantidad = document.getElementById("salidaCantidad");

  function mostrarErrorModalSalida(mensaje) {
    modalSalidaError.textContent = mensaje;
    modalSalidaError.style.display = "block";
  }

  function validarFormularioSalida() {
    if (!campoSalidaProducto.value) {
      mostrarErrorModalSalida("Selecciona un producto.");
      return false;
    }
    if (!(Number(campoSalidaCantidad.value) > 0)) {
      mostrarErrorModalSalida("La cantidad debe ser mayor que cero.");
      campoSalidaCantidad.focus();
      return false;
    }
    return true;
  }

  async function guardarSalida(ev) {
    ev.preventDefault();
    modalSalidaError.style.display = "none";
    if (!validarFormularioSalida()) return;

    const productoSeleccionado = productosCache.find((p) => p.id === Number(campoSalidaProducto.value));
    const confirmado = window.UI
      ? await window.UI.confirmar({
          titulo: "Registrar salida",
          mensaje: `¿Deseas registrar una salida de ${campoSalidaCantidad.value} unidad(es) de "${
            productoSeleccionado ? productoSeleccionado.nombre : "este producto"
          }"? Se consumirá stock automáticamente vía FEFO y no se puede deshacer desde aquí.`,
          textoAceptar: "Registrar salida",
          variante: "danger",
        })
      : true;
    if (!confirmado) return;

    const datos = {
      producto_id: Number(campoSalidaProducto.value),
      inventario_id: inventarioIdActual, // obligatorio en SalidaInventarioCrear
      cantidad: Number(campoSalidaCantidad.value),
      referencia: document.getElementById("salidaReferencia").value.trim() || null,
    };

    if (window.UI) window.UI.mostrarCargando();
    try {
      const movimientos = await apiPost("/api/inventario/salidas", datos);
      if (modalSalida) modalSalida.hide();
      formSalida.reset();
      await refrescarTodo();
      if (window.UI) {
        window.UI.toast(
          `Salida registrada: ${movimientos.length} lote(s) afectado(s) vía FEFO ` +
            `(vencimiento más próximo primero).`,
          "success"
        );
      }
    } catch (err) {
      mostrarErrorModalSalida(err.message || "No se pudo registrar la salida.");
      if (window.UI) window.UI.toast(err.message || "No se pudo registrar la salida.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Modal: Ajuste ----------
  const modalAjusteEl = document.getElementById("modalAjuste");
  const modalAjuste = bootstrapDisponible ? new bootstrap.Modal(modalAjusteEl) : null;
  const formAjuste = document.getElementById("formAjuste");
  const modalAjusteError = document.getElementById("modalAjusteError");
  const ajusteLoteId = document.getElementById("ajusteLoteId");
  const ajusteCantidad = document.getElementById("ajusteCantidad");

  function mostrarErrorModalAjuste(mensaje) {
    modalAjusteError.textContent = mensaje;
    modalAjusteError.style.display = "block";
  }

  function abrirModalAjuste(loteId) {
    if (!modalAjuste) {
      mostrarError("No se pudo abrir la ventana de ajuste: Bootstrap no está disponible.");
      return;
    }
    formAjuste.reset();
    modalAjusteError.style.display = "none";
    ajusteLoteId.value = loteId || "";
    modalAjuste.show();
  }

  function validarFormularioAjuste() {
    if (!(Number(ajusteLoteId.value) > 0)) {
      mostrarErrorModalAjuste("El ID de lote debe ser un número positivo.");
      ajusteLoteId.focus();
      return false;
    }
    if (Number(ajusteCantidad.value) === 0 || ajusteCantidad.value.trim() === "") {
      mostrarErrorModalAjuste("La cantidad del ajuste no puede ser cero.");
      ajusteCantidad.focus();
      return false;
    }
    return true;
  }

  async function guardarAjuste(ev) {
    ev.preventDefault();
    modalAjusteError.style.display = "none";
    if (!validarFormularioAjuste()) return;

    const cantidad = Number(ajusteCantidad.value);
    const confirmado = window.UI
      ? await window.UI.confirmar({
          titulo: "Registrar ajuste",
          mensaje: `¿Deseas registrar un ajuste de ${cantidad > 0 ? "+" : ""}${cantidad} para el lote #${ajusteLoteId.value}? Esta acción modifica el saldo del kardex y no se puede deshacer desde aquí.`,
          textoAceptar: "Registrar ajuste",
          variante: "danger",
        })
      : true;
    if (!confirmado) return;

    const datos = {
      lote_id: Number(ajusteLoteId.value),
      cantidad,
      referencia: document.getElementById("ajusteReferencia").value.trim() || null,
    };

    if (window.UI) window.UI.mostrarCargando();
    try {
      await apiPost("/api/inventario/ajustes", datos);
      if (modalAjuste) modalAjuste.hide();
      formAjuste.reset();
      if (window.UI) window.UI.toast("Ajuste de inventario registrado correctamente.", "success");
      await refrescarTodo();
    } catch (err) {
      mostrarErrorModalAjuste(err.message || "No se pudo registrar el ajuste.");
      if (window.UI) window.UI.toast(err.message || "No se pudo registrar el ajuste.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Modal: Nuevo inventario ----------
  const modalNuevoInventarioEl = document.getElementById("modalNuevoInventario");
  const modalNuevoInventario = bootstrapDisponible ? new bootstrap.Modal(modalNuevoInventarioEl) : null;
  const formNuevoInventario = document.getElementById("formNuevoInventario");
  const modalNuevoInventarioError = document.getElementById("modalNuevoInventarioError");
  const campoNuevoInventarioCodigo = document.getElementById("nuevoInventarioCodigo");
  const campoNuevoInventarioNombre = document.getElementById("nuevoInventarioNombre");

  function mostrarErrorModalNuevoInventario(mensaje) {
    modalNuevoInventarioError.textContent = mensaje;
    modalNuevoInventarioError.style.display = "block";
  }

  function abrirModalNuevoInventario() {
    if (!modalNuevoInventario) {
      mostrarError("No se pudo abrir la ventana de nuevo inventario: Bootstrap no está disponible.");
      return;
    }
    formNuevoInventario.reset();
    modalNuevoInventarioError.style.display = "none";
    modalNuevoInventario.show();
  }

  function validarFormularioNuevoInventario() {
    if (!campoNuevoInventarioCodigo.value.trim()) {
      mostrarErrorModalNuevoInventario("El código es obligatorio.");
      campoNuevoInventarioCodigo.focus();
      return false;
    }
    if (!campoNuevoInventarioNombre.value.trim()) {
      mostrarErrorModalNuevoInventario("El nombre es obligatorio.");
      campoNuevoInventarioNombre.focus();
      return false;
    }
    return true;
  }

  async function guardarNuevoInventario(ev) {
    ev.preventDefault();
    modalNuevoInventarioError.style.display = "none";
    if (!validarFormularioNuevoInventario()) return;

    const datos = {
      codigo: campoNuevoInventarioCodigo.value.trim(),
      nombre: campoNuevoInventarioNombre.value.trim(),
    };

    if (window.UI) window.UI.mostrarCargando();
    try {
      // Mismo endpoint ya existente en el Backend, sin agregar nada nuevo.
      const nuevoInventario = await apiPost("/api/inventario/inventarios", datos);
      if (modalNuevoInventario) modalNuevoInventario.hide();
      formNuevoInventario.reset();
      if (window.UI) window.UI.toast(`Inventario "${nuevoInventario.nombre}" creado correctamente.`, "success");

      // Refresca el selector con la lista actualizada y deja el
      // inventario recién creado como activo, sin recargar la página.
      movimientosCargados = false;
      lotesCargados = false;
      proximosVencerCargados = false;
      inteligenciaCargada = false;
      await refrescarTodo(nuevoInventario.id);
    } catch (err) {
      mostrarErrorModalNuevoInventario(err.message || "No se pudo crear el inventario.");
      if (window.UI) window.UI.toast(err.message || "No se pudo crear el inventario.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Carga general ----------
  async function refrescarTodo(idInventarioAConservar) {
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      // cargarInventarios() debe resolverse antes que cargarSaldos() (la
      // necesita), así que no puede ir dentro del mismo Promise.all.
      await cargarInventarios(idInventarioAConservar !== undefined ? idInventarioAConservar : inventarioIdActual);
      await Promise.all([cargarProductosCache(), cargarSaldos(), cargarKpis()]);
      if (selectProducto.value) await cargarKardexPorProductoId(Number(selectProducto.value));
      // Si la pestaña Movimientos/Lotes/Próximos a vencer/Inteligencia ya
      // se había cargado, se refresca junto con el resto (para que un
      // ingreso/salida/ajuste recién guardado aparezca ahí también); si
      // nunca se abrió, se deja para cuando el usuario la abra (carga
      // perezosa, mismo criterio ya usado para movimientosCargados).
      if (movimientosCargados) await cargarMovimientosGlobales(true);
      if (lotesCargados) await cargarLotes(true);
      if (proximosVencerCargados) await cargarProximosVencer(true);
      if (inteligenciaCargada) await cargarInteligencia(true);
    } catch (err) {
      mostrarError(err.message || "Ocurrió un error al cargar el inventario.");
      if (window.UI) window.UI.toast(err.message || "Ocurrió un error al cargar el inventario.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function leerProductoIdDesdeUrl() {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("producto_id");
    return id ? Number(id) : null;
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    // Saldos: búsqueda/filtro/paginación.
    inputBuscarSaldos.addEventListener(
      "input",
      U.debounce(() => {
        paginadorSaldos.reiniciar();
        pintarSaldos();
      }, 200)
    );
    selectEstadoSaldos.addEventListener("change", () => {
      paginadorSaldos.reiniciar();
      pintarSaldos();
    });
    selectTamanioPaginaSaldos.addEventListener("change", () => {
      paginadorSaldos.reiniciar();
      pintarSaldos();
    });

    // Alertas: búsqueda/paginación.
    inputBuscarAlertas.addEventListener(
      "input",
      U.debounce(() => {
        paginadorAlertas.reiniciar();
        pintarAlertas();
      }, 200)
    );
    selectTamanioPaginaAlertas.addEventListener("change", () => {
      paginadorAlertas.reiniciar();
      pintarAlertas();
    });

    // Kardex: selector de producto, filtro de tipo, paginación.
    selectProducto.addEventListener("change", () => cargarKardexPorProductoId(Number(selectProducto.value) || null));
    selectTipoMovimientoKardex.addEventListener("change", () => {
      paginadorKardex.reiniciar();
      pintarKardex();
    });
    selectTamanioPaginaKardex.addEventListener("change", () => {
      paginadorKardex.reiniciar();
      pintarKardex();
    });

    // Movimientos: carga perezosa al mostrar la pestaña, búsqueda/filtro/paginación/actualizar.
    tabBtnMovimientos.addEventListener("shown.bs.tab", () => cargarMovimientosGlobales(false));
    inputBuscarMovimientos.addEventListener(
      "input",
      U.debounce(() => {
        paginadorMovimientos.reiniciar();
        pintarMovimientos();
      }, 200)
    );
    selectTipoMovimientoGlobal.addEventListener("change", () => {
      paginadorMovimientos.reiniciar();
      pintarMovimientos();
    });
    selectTamanioPaginaMovimientos.addEventListener("change", () => {
      paginadorMovimientos.reiniciar();
      pintarMovimientos();
    });
    btnActualizarMovimientos.addEventListener("click", () => cargarMovimientosGlobales(true));

    // Lotes: carga perezosa al mostrar la pestaña, búsqueda/paginación/actualizar/exportar.
    tabBtnLotes.addEventListener("shown.bs.tab", () => cargarLotes(false));
    inputBuscarLotes.addEventListener(
      "input",
      U.debounce(() => {
        paginadorLotes.reiniciar();
        pintarLotes();
      }, 200)
    );
    selectTamanioPaginaLotes.addEventListener("change", () => {
      paginadorLotes.reiniciar();
      pintarLotes();
    });
    btnActualizarLotes.addEventListener("click", () => cargarLotes(true));
    btnExportarLotesExcel.addEventListener("click", () =>
      descargarSeguro(`/api/reportes/inventario-por-lote/exportar/excel?inventario_id=${inventarioIdActual}`, "inventario_por_lote.xlsx", btnExportarLotesExcel)
    );
    btnExportarLotesPdf.addEventListener("click", () =>
      descargarSeguro(`/api/reportes/inventario-por-lote/exportar/pdf?inventario_id=${inventarioIdActual}`, "inventario_por_lote.pdf", btnExportarLotesPdf)
    );

    // Próximos a vencer: carga perezosa, búsqueda/filtro/paginación/actualizar/exportar.
    tabBtnProximosVencer.addEventListener("shown.bs.tab", () => cargarProximosVencer(false));
    inputBuscarProximosVencer.addEventListener(
      "input",
      U.debounce(() => {
        paginadorProximosVencer.reiniciar();
        pintarProximosVencer();
      }, 200)
    );
    selectCategoriaProximosVencer.addEventListener("change", () => {
      paginadorProximosVencer.reiniciar();
      pintarProximosVencer();
    });
    selectTamanioPaginaProximosVencer.addEventListener("change", () => {
      paginadorProximosVencer.reiniciar();
      pintarProximosVencer();
    });
    btnActualizarProximosVencer.addEventListener("click", () => cargarProximosVencer(true));
    btnExportarProximosVencerExcel.addEventListener("click", () =>
      descargarSeguro(`/api/reportes/proximos-vencer/exportar/excel?inventario_id=${inventarioIdActual}`, "proximos_vencer.xlsx", btnExportarProximosVencerExcel)
    );
    btnExportarProximosVencerPdf.addEventListener("click", () =>
      descargarSeguro(`/api/reportes/proximos-vencer/exportar/pdf?inventario_id=${inventarioIdActual}`, "proximos_vencer.pdf", btnExportarProximosVencerPdf)
    );

    // Inteligencia de inventario: carga perezosa, búsqueda/paginación/actualizar/días de análisis.
    tabBtnInteligencia.addEventListener("shown.bs.tab", () => cargarInteligencia(false));
    inputBuscarInteligencia.addEventListener(
      "input",
      U.debounce(() => {
        paginadorInteligencia.reiniciar();
        pintarInteligencia();
      }, 200)
    );
    selectTamanioPaginaInteligencia.addEventListener("change", () => {
      paginadorInteligencia.reiniciar();
      pintarInteligencia();
    });
    selectDiasAnalisisInteligencia.addEventListener(
      "change",
      U.debounce(() => cargarInteligencia(true), 300)
    );
    btnActualizarInteligencia.addEventListener("click", () => cargarInteligencia(true));

    // Botones de cabecera (Ingreso/Salida/Ajuste).
    btnNuevoIngreso.addEventListener("click", () => abrirModalIngresoConProducto(null));
    btnNuevaSalida.addEventListener("click", () => {
      if (!modalSalida) {
        mostrarError("No se pudo abrir la ventana de nueva salida: Bootstrap no está disponible.");
        return;
      }
      formSalida.reset();
      modalSalidaError.style.display = "none";
      modalSalida.show();
    });
    btnNuevoAjuste.addEventListener("click", () => abrirModalAjuste(null));

    formIngreso.addEventListener("submit", guardarIngreso);
    formSalida.addEventListener("submit", guardarSalida);
    formAjuste.addEventListener("submit", guardarAjuste);

    // Selector de inventario activo: cambia el almacén y recarga
    // Saldos/Alertas/Kardex/Movimientos para el inventario elegido.
    selectInventarioActivo.addEventListener("change", () => {
      const idElegido = Number(selectInventarioActivo.value) || null;
      if (!idElegido || idElegido === inventarioIdActual) return;
      inventarioIdActual = idElegido;
      // Pertenecían al Inventario anterior: se invalidan para que la
      // próxima carga (o la próxima vez que se abra cada pestaña) traiga
      // los datos del Inventario recién elegido, no los del anterior.
      movimientosCargados = false;
      lotesCargados = false;
      proximosVencerCargados = false;
      inteligenciaCargada = false;
      refrescarTodo(idElegido);
    });

    btnNuevoInventario.addEventListener("click", abrirModalNuevoInventario);
    formNuevoInventario.addEventListener("submit", guardarNuevoInventario);

    refrescarTodo().then(() => {
      const productoIdDesdeUrl = leerProductoIdDesdeUrl();
      if (productoIdDesdeUrl) {
        // El parámetro de la URL es producto_id (catálogo), no
        // producto_inventario_id, así que usa la misma ruta que el <select>.
        selectProducto.value = String(productoIdDesdeUrl);
        cargarKardexPorProductoId(productoIdDesdeUrl);
      }
    });
  }

  // FASE 9B — Importar Compras Nacionalizadas (frontend de m04_compras):
  // al confirmar una importación, compras.js escribe una señal en
  // localStorage (sin backend, sin SPA) para que esta página, si está
  // abierta en otra pestaña, se refresque sola. Reutiliza la función de
  // carga ya existente (refrescarTodo()); no agrega endpoints ni lógica
  // de negocio nueva.
  // FASE 10A — Importar Ventas (frontend de m10_ventas): ventas.js escribe
  // la misma señal con modulo: "ventas" (cada orden importada se despacha
  // de inmediato, con salida real de Kardex), así que este listener se
  // amplía para aceptar también ese valor y reutilizar exactamente la
  // misma función de recarga (refrescarTodo()); no cambia ninguna lógica
  // de inventario/Kardex/FEFO existente.
  window.addEventListener("storage", (ev) => {
    if (ev.key !== "erp_datos_actualizados" || !ev.newValue) return;
    try {
      const datos = JSON.parse(ev.newValue);
      if (datos && (datos.modulo === "compras" || datos.modulo === "ventas")) refrescarTodo(inventarioIdActual);
    } catch (err) {
      /* señal mal formada: se ignora, no es crítico. */
    }
  });

  iniciar();
})();
