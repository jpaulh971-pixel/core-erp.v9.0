/**
 * pages/guias_remision/guias_remision.js — Page-script del módulo
 * m17_guias_remision (app/modules/m17_guias_remision).
 *
 * FASE F7 — Contrato REAL verificado en el Backend congelado
 * (Core_ERP_Backend_B2.zip) antes de escribir esta página: router.py,
 * schemas.py, models.py, service.py, repository.py y validators.py de
 * app/modules/m17_guias_remision. No se inventa ningún endpoint, campo
 * ni transición de estado que no esté ahí.
 *
 * Endpoints reales de este módulo (todos con Bearer, vía api-client.js):
 *   GET  /api/guias-remision?estado=str|null   -> list[GuiaRemisionOut]
 *   GET  /api/guias-remision/{id}              -> GuiaRemisionOut
 *   POST /api/guias-remision                   body GuiaRemisionCrear      -> GuiaRemisionOut (201)
 *   POST /api/guias-remision/desde-venta/{orden_venta_id}
 *                                               body GuiaDesdeVentaCrear    -> GuiaRemisionOut (201)
 *
 * GuiaRemisionCrear: cliente_id, inventario_id, motivo_traslado
 * (default "VENTA", <=200), numero_guia? (<=30, autogenerado
 * "GR-NNNNNN" si se omite), detalles: [{producto_id, lote_id,
 * cantidad>0, unidad_medida<=20 (default "UND")}] (mínimo 1 renglón).
 *
 * GuiaDesdeVentaCrear: motivo_traslado (default "VENTA"), numero_guia?.
 * La orden_venta_id va en la URL. El Backend exige que la orden esté en
 * estado DESPACHADA (validators.validar_orden_despachada) y que no
 * tenga ya una guía generada (validators.validar_orden_sin_guia_previa);
 * los renglones se derivan del Kardex real del despacho (lote_id real
 * por FEFO), no se piden al cliente.
 *
 * GuiaRemisionOut: id, numero_guia, fecha_emision, estado
 * ("EMITIDA"|"ANULADA" — models.ESTADOS_GUIA_REMISION), cliente_id,
 * cliente_razon_social, orden_venta_id?, inventario_id, motivo_traslado,
 * anulado_en?, creado_en, detalles: [{id, producto_id, lote_id,
 * cantidad, unidad_medida}].
 *
 * ------------------------------------------------------------------
 * LIMITACIONES REALES DEL BACKEND (documentadas, no simuladas):
 * ------------------------------------------------------------------
 * 1) NO existe endpoint para EDITAR una guía (no hay PUT/PATCH en
 *    router.py). No se implementa edición en esta pantalla.
 * 2) NO existe endpoint para ANULAR ni para cambiar de estado una guía,
 *    a pesar de que el modelo (models.py) define el estado ANULADA y
 *    la columna anulado_en. router.py de m17 solo expone POST (x2),
 *    GET (x2). No se implementa "Anular" ni "Cambio de estado" en esta
 *    pantalla: se documenta como limitación del Backend congelado.
 * 3) GET /api/guias-remision solo acepta el querystring `estado`; no
 *    admite búsqueda de texto ni paginación (page/limit/skip). Se
 *    resuelven en el cliente sobre la lista ya cargada, igual que en
 *    F1-F6 para módulos equivalentes.
 * 4) El Backend NO expone un endpoint para listar lotes disponibles de
 *    un producto (repository.lotes_disponibles_fefo existe, pero no
 *    está montado en ningún router). Para poder elegir un lote_id real
 *    al crear una guía MANUAL, esta pantalla deriva los lotes con
 *    movimientos registrados combinando dos endpoints que sí existen:
 *    GET /api/inventario/inventarios/{inventario_id}/productos (para
 *    resolver producto_inventario_id a partir de producto_id +
 *    inventario_id) y GET /api/inventario/kardex/{producto_inventario_id}
 *    (para leer, por lote_id, el último saldo_resultante). Es una
 *    composición de LECTURA sobre endpoints ya existentes: no se crea
 *    ningún endpoint nuevo ni se inventa un catálogo de lotes.
 * 5) La creación "desde venta" no permite mandar renglones ni tocar
 *    montos/lotes: el Backend los deriva íntegramente del Kardex. Por
 *    eso el modal correspondiente solo pide orden_venta_id, motivo y
 *    número de guía.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const elError = document.getElementById("estadoError");
  const selectEstado = document.getElementById("selectEstado");
  const inputBuscarGuias = document.getElementById("inputBuscarGuias");
  const tbody = document.getElementById("tbodyGuias");
  const selectTamanioPaginaGuias = document.getElementById("selectTamanioPaginaGuias");

  const bootstrapDisponible = typeof bootstrap !== "undefined" && bootstrap.Modal;

  // ---- Modal Nueva guía manual ----
  const btnNuevaGuia = document.getElementById("btnNuevaGuia");
  const modalNuevaEl = document.getElementById("modalNuevaGuia");
  const modalNueva = bootstrapDisponible ? new bootstrap.Modal(modalNuevaEl) : null;
  const formNueva = document.getElementById("formNuevaGuia");
  const modalNuevaError = document.getElementById("modalNuevaGuiaError");
  const guiaCliente = document.getElementById("guiaCliente");
  const guiaInventario = document.getElementById("guiaInventario");
  const guiaMotivo = document.getElementById("guiaMotivo");
  const guiaNumero = document.getElementById("guiaNumero");
  const tbodyDetalleGuia = document.getElementById("tbodyDetalleGuia");
  const btnAgregarDetalle = document.getElementById("btnAgregarDetalle");

  // ---- Modal Nueva guía desde venta ----
  const btnGuiaDesdeVenta = document.getElementById("btnGuiaDesdeVenta");
  const modalVentaEl = document.getElementById("modalGuiaDesdeVenta");
  const modalVenta = bootstrapDisponible ? new bootstrap.Modal(modalVentaEl) : null;
  const formVenta = document.getElementById("formGuiaDesdeVenta");
  const modalVentaError = document.getElementById("modalGuiaDesdeVentaError");
  const ventaOrden = document.getElementById("ventaOrden");
  const ventaMotivo = document.getElementById("ventaMotivo");
  const ventaNumero = document.getElementById("ventaNumero");

  // ---- Modal Detalle ----
  const modalDetalleEl = document.getElementById("modalDetalleGuia");
  const modalDetalle = bootstrapDisponible ? new bootstrap.Modal(modalDetalleEl) : null;
  const detalleTitulo = document.getElementById("detalleGuiaTitulo");
  const modalDetalleError = document.getElementById("modalDetalleGuiaError");
  const detalleInfo = document.getElementById("detalleGuiaInfo");
  const tbodyDetalleVerGuia = document.getElementById("tbodyDetalleVerGuia");

  let clientesCache = [];
  let inventariosCache = [];
  let productosCache = [];
  let guiasCache = [];
  let contadorFilaDetalle = 0;
  // Cache de productos-por-inventario, para no repetir la llamada al
  // resolver producto_inventario_id (ver limitación 4 del cabezal).
  const productosPorInventarioCache = {};

  function mostrarError(mensaje) {
    elError.textContent = mensaje;
    elError.style.display = "block";
  }

  function ocultarError() {
    elError.style.display = "none";
  }

  function mostrarErrorModal(el, mensaje) {
    el.textContent = mensaje;
    el.style.display = "block";
  }

  function ocultarErrorModal(el) {
    el.style.display = "none";
  }

  async function apiRequest(path, opciones) {
    return window.Api.request(path, opciones);
  }

  const apiGet = (path) => apiRequest(path);
  const apiPost = (path, body) =>
    apiRequest(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined });

  function filaVacia(colspan, texto) {
    return `<tr><td colspan="${colspan}" class="text-muted-erp">${texto}</td></tr>`;
  }

  function colorEstado(estado) {
    const colores = { EMITIDA: "success", ANULADA: "dark" };
    return colores[estado] || "secondary";
  }

  // ---------- Paginador genérico reutilizable (mismo criterio que
  // inventario.js/compras.js/ventas.js/comercio_exterior.js/
  // operacion_logistica.js: el Backend no expone page/limit en
  // /api/guias-remision, así que la paginación de la tabla se resuelve
  // en el cliente sobre la lista ya cargada) ----------
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

  const paginadorGuias = crearPaginador(
    selectTamanioPaginaGuias,
    document.getElementById("paginacionResumenGuias"),
    document.getElementById("paginacionControlesGuias"),
    () => pintarGuias()
  );

  // ---------- Búsqueda (cliente, ya que /api/guias-remision solo
  // filtra por "estado" en el Backend) ----------
  function filtrarGuias(lista) {
    const q = inputBuscarGuias.value.trim().toLowerCase();
    if (!q) return lista;
    return lista.filter((g) => {
      const numero = (g.numero_guia || "").toLowerCase();
      const cliente = (g.cliente_razon_social || "").toLowerCase();
      const motivo = (g.motivo_traslado || "").toLowerCase();
      const origen = g.orden_venta_id ? `orden de venta #${g.orden_venta_id}` : "manual";
      return numero.includes(q) || cliente.includes(q) || motivo.includes(q) || origen.includes(q);
    });
  }

  function origenTexto(g) {
    return g.orden_venta_id ? `Orden de venta #${g.orden_venta_id}` : "Manual";
  }

  // ---------- Listado ----------
  function pintarGuias() {
    const filtradas = filtrarGuias(guiasCache);
    const info = paginadorGuias.calcular(filtradas);

    tbody.innerHTML = info.pagina.length
      ? info.pagina
          .map(
            (g) => `
        <tr>
          <td>${U.escaparHtml(g.numero_guia)}</td>
          <td>${U.formatearFechaHora(g.fecha_emision)}</td>
          <td>${U.escaparHtml(g.cliente_razon_social)}</td>
          <td>${U.escaparHtml(origenTexto(g))}</td>
          <td>${U.escaparHtml(g.motivo_traslado)}</td>
          <td><span class="badge text-bg-${colorEstado(g.estado)}">${U.escaparHtml(g.estado)}</span></td>
          <td class="text-end">
            <button type="button" class="btn btn-sm btn-outline-secondary btn-ver-detalle" data-id="${g.id}">
              <i class="bi bi-eye"></i> Ver
            </button>
          </td>
        </tr>`
          )
          .join("")
      : filaVacia(
          7,
          guiasCache.length === 0
            ? "No hay guías de remisión registradas."
            : "Ninguna guía coincide con la búsqueda/filtro."
        );

    tbody.querySelectorAll(".btn-ver-detalle").forEach((btn) => {
      btn.addEventListener("click", () => abrirModalDetalle(Number(btn.dataset.id)));
    });
  }

  async function cargarGuias() {
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      const query = selectEstado.value ? `?estado=${encodeURIComponent(selectEstado.value)}` : "";
      guiasCache = await apiGet(`/api/guias-remision${query}`);
      paginadorGuias.reiniciar();
      pintarGuias();
    } catch (err) {
      mostrarError(err.message || "Ocurrió un error al cargar las guías de remisión.");
      if (window.UI) window.UI.toast(err.message || "Ocurrió un error al cargar las guías de remisión.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Catálogos (clientes, inventarios, productos) ----------
  async function cargarClientesCache() {
    clientesCache = await apiGet("/api/clientes?solo_activos=true");
  }

  async function cargarInventariosCache() {
    inventariosCache = await apiGet("/api/inventario/inventarios");
  }

  async function cargarProductosCache() {
    productosCache = await apiGet("/api/productos?solo_activos=true");
  }

  function opcionesClienteHtml() {
    return (
      '<option value="">Seleccionar…</option>' +
      clientesCache.map((c) => `<option value="${c.id}">${U.escaparHtml(c.razon_social)} (${U.escaparHtml(c.ruc)})</option>`).join("")
    );
  }

  function opcionesInventarioHtml() {
    return (
      '<option value="">Seleccionar…</option>' +
      inventariosCache.map((i) => `<option value="${i.id}">${U.escaparHtml(i.codigo)} — ${U.escaparHtml(i.nombre)}</option>`).join("")
    );
  }

  function opcionesProductoHtml() {
    return (
      '<option value="">Seleccionar…</option>' +
      productosCache.map((p) => `<option value="${p.id}" data-unidad="${U.escaparHtml(p.unidad_medida)}">${U.escaparHtml(p.codigo)} — ${U.escaparHtml(p.nombre)}</option>`).join("")
    );
  }

  // ---------- Limitación 4: derivar lotes con movimientos reales para
  // un producto dentro de un inventario, combinando dos endpoints ya
  // existentes (no hay endpoint de catálogo de lotes en el Backend) ----------
  async function resolverProductoInventarioId(inventarioId, productoId) {
    if (!productosPorInventarioCache[inventarioId]) {
      productosPorInventarioCache[inventarioId] = await apiGet(`/api/inventario/inventarios/${inventarioId}/productos`);
    }
    const encontrado = productosPorInventarioCache[inventarioId].find((pi) => pi.producto_id === productoId);
    return encontrado ? encontrado.id : null;
  }

  async function obtenerLotesConMovimiento(inventarioId, productoId) {
    const productoInventarioId = await resolverProductoInventarioId(inventarioId, productoId);
    if (!productoInventarioId) return [];
    const movimientos = await apiGet(`/api/inventario/kardex/${productoInventarioId}`);
    // El Backend devuelve el kardex ordenado por creado_en DESC
    // (repository.kardex_por_producto_inventario): el primer movimiento
    // que aparece para cada lote_id ya trae su saldo_resultante más
    // reciente, así que basta con quedarnos con el primero por lote.
    const porLote = new Map();
    for (const m of movimientos) {
      if (!porLote.has(m.lote_id)) porLote.set(m.lote_id, m.saldo_resultante);
    }
    return Array.from(porLote.entries()).map(([lote_id, saldo]) => ({ lote_id, saldo }));
  }

  // ---------- Filas dinámicas de detalle (creación manual) ----------
  function agregarFilaDetalle() {
    contadorFilaDetalle += 1;
    const fila = document.createElement("tr");
    fila.dataset.fila = String(contadorFilaDetalle);
    fila.innerHTML = `
      <td><select class="form-select form-select-sm item-producto" required>${opcionesProductoHtml()}</select></td>
      <td>
        <select class="form-select form-select-sm item-lote" required disabled>
          <option value="">Selecciona inventario y producto…</option>
        </select>
      </td>
      <td><input type="number" class="form-control form-control-sm item-cantidad" min="0.001" step="0.001" required /></td>
      <td><input type="text" class="form-control form-control-sm item-unidad" maxlength="20" value="UND" required /></td>
      <td class="text-end">
        <button type="button" class="btn btn-sm btn-outline-danger btn-quitar-detalle"><i class="bi bi-trash"></i></button>
      </td>`;
    tbodyDetalleGuia.appendChild(fila);

    const selectProducto = fila.querySelector(".item-producto");
    const selectLote = fila.querySelector(".item-lote");
    const inputUnidad = fila.querySelector(".item-unidad");

    selectProducto.addEventListener("change", async () => {
      const opcion = selectProducto.selectedOptions[0];
      if (opcion && opcion.dataset.unidad) inputUnidad.value = opcion.dataset.unidad;
      await refrescarLotesFila(fila);
    });

    fila.querySelector(".btn-quitar-detalle").addEventListener("click", () => {
      // GuiaRemisionCrear.detalles exige mínimo 1 renglón: no se deja
      // quitar el último.
      if (tbodyDetalleGuia.querySelectorAll("tr").length <= 1) {
        if (window.UI) window.UI.toast("Debe quedar al menos un renglón en la guía.", "warning");
        return;
      }
      fila.remove();
    });

    return fila;
  }

  async function refrescarLotesFila(fila) {
    const selectLote = fila.querySelector(".item-lote");
    const productoId = Number(fila.querySelector(".item-producto").value) || null;
    const inventarioId = Number(guiaInventario.value) || null;

    selectLote.disabled = true;
    if (!productoId || !inventarioId) {
      selectLote.innerHTML = '<option value="">Selecciona inventario y producto…</option>';
      return;
    }

    selectLote.innerHTML = '<option value="">Cargando lotes…</option>';
    try {
      const lotes = await obtenerLotesConMovimiento(inventarioId, productoId);
      if (!lotes.length) {
        selectLote.innerHTML = '<option value="">Sin lotes con movimientos en este inventario</option>';
        return;
      }
      selectLote.innerHTML =
        '<option value="">Seleccionar…</option>' +
        lotes
          .map((l) => `<option value="${l.lote_id}">Lote #${l.lote_id} — stock actual: ${U.formatearNumero(l.saldo, 3)}</option>`)
          .join("");
      selectLote.disabled = false;
    } catch (err) {
      selectLote.innerHTML = '<option value="">No se pudieron cargar los lotes</option>';
      if (window.UI) window.UI.toast(err.message || "No se pudieron cargar los lotes disponibles.", "error");
    }
  }

  function reiniciarDetalleGuia() {
    tbodyDetalleGuia.innerHTML = "";
    contadorFilaDetalle = 0;
    agregarFilaDetalle();
  }

  guiaInventario.addEventListener("change", () => {
    // Cambiar de inventario invalida los lotes ya cargados por fila.
    tbodyDetalleGuia.querySelectorAll("tr").forEach((fila) => refrescarLotesFila(fila));
  });

  btnAgregarDetalle.addEventListener("click", agregarFilaDetalle);

  // ---------- Validaciones cliente (obligatorios, formatos, cantidades) ----------
  function leerDetallesFormulario() {
    const detalles = [];
    const errores = [];
    tbodyDetalleGuia.querySelectorAll("tr").forEach((fila, idx) => {
      const productoId = fila.querySelector(".item-producto").value;
      const loteId = fila.querySelector(".item-lote").value;
      const cantidad = fila.querySelector(".item-cantidad").value;
      const unidad = fila.querySelector(".item-unidad").value.trim();

      if (!productoId) errores.push(`Renglón ${idx + 1}: selecciona un producto.`);
      if (!loteId) errores.push(`Renglón ${idx + 1}: selecciona un lote.`);
      if (!(Number(cantidad) > 0)) errores.push(`Renglón ${idx + 1}: la cantidad debe ser mayor a 0.`);
      if (!unidad) errores.push(`Renglón ${idx + 1}: la unidad de medida es obligatoria.`);

      if (productoId && loteId && Number(cantidad) > 0 && unidad) {
        detalles.push({
          producto_id: Number(productoId),
          lote_id: Number(loteId),
          cantidad: Number(cantidad),
          unidad_medida: unidad,
        });
      }
    });
    return { detalles, errores };
  }

  function validarFormularioNuevaGuia() {
    const errores = [];
    if (!guiaCliente.value) errores.push("Selecciona un cliente.");
    if (!guiaInventario.value) errores.push("Selecciona un inventario de origen.");
    if (!guiaMotivo.value.trim()) errores.push("El motivo de traslado es obligatorio.");
    if (guiaNumero.value.trim().length > 30) errores.push('El número de guía no puede superar los 30 caracteres.');

    const { detalles, errores: erroresDetalle } = leerDetallesFormulario();
    errores.push(...erroresDetalle);
    if (!detalles.length && !erroresDetalle.length) errores.push("Agrega al menos un renglón a la guía.");

    return { valido: errores.length === 0, errores, detalles };
  }

  async function abrirModalNuevaGuia() {
    if (!modalNueva) {
      if (window.UI) window.UI.toast("No se pudo abrir el formulario: Bootstrap no está disponible.", "error");
      return;
    }
    ocultarErrorModal(modalNuevaError);
    formNueva.reset();
    guiaMotivo.value = "VENTA";
    reiniciarDetalleGuia();

    if (!clientesCache.length || !inventariosCache.length || !productosCache.length) {
      if (window.UI) window.UI.mostrarCargando();
      try {
        await Promise.all([cargarClientesCache(), cargarInventariosCache(), cargarProductosCache()]);
      } catch (err) {
        mostrarErrorModal(modalNuevaError, err.message || "No se pudieron cargar los catálogos (clientes/inventarios/productos).");
        if (window.UI) window.UI.toast(err.message || "No se pudieron cargar los catálogos.", "error");
      } finally {
        if (window.UI) window.UI.ocultarCargando();
      }
    }
    guiaCliente.innerHTML = opcionesClienteHtml();
    guiaInventario.innerHTML = opcionesInventarioHtml();
    reiniciarDetalleGuia();
    modalNueva.show();
  }

  async function guardarNuevaGuia(ev) {
    ev.preventDefault();
    ocultarErrorModal(modalNuevaError);

    const { valido, errores, detalles } = validarFormularioNuevaGuia();
    if (!valido) {
      mostrarErrorModal(modalNuevaError, errores.join(" "));
      return;
    }

    const payload = {
      cliente_id: Number(guiaCliente.value),
      inventario_id: Number(guiaInventario.value),
      motivo_traslado: guiaMotivo.value.trim(),
      numero_guia: guiaNumero.value.trim() || null,
      detalles,
    };

    if (window.UI) window.UI.mostrarCargando();
    try {
      const guia = await apiPost("/api/guias-remision", payload);
      if (window.UI) window.UI.toast(`Guía de remisión ${guia.numero_guia} registrada correctamente.`, "success");
      modalNueva.hide();
      await cargarGuias();
    } catch (err) {
      mostrarErrorModal(modalNuevaError, err.message || "No se pudo registrar la guía de remisión.");
      if (window.UI) window.UI.toast(err.message || "No se pudo registrar la guía de remisión.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Creación desde orden de venta despachada ----------
  async function cargarOrdenesDespachadasCache() {
    return apiGet("/api/ventas?estado=DESPACHADA");
  }

  async function abrirModalDesdeVenta() {
    if (!modalVenta) {
      if (window.UI) window.UI.toast("No se pudo abrir el formulario: Bootstrap no está disponible.", "error");
      return;
    }
    ocultarErrorModal(modalVentaError);
    formVenta.reset();
    ventaMotivo.value = "VENTA";
    ventaOrden.innerHTML = '<option value="">Cargando órdenes despachadas…</option>';
    modalVenta.show();

    if (window.UI) window.UI.mostrarCargando();
    try {
      const ordenes = await cargarOrdenesDespachadasCache();
      ventaOrden.innerHTML = ordenes.length
        ? '<option value="">Seleccionar…</option>' +
          ordenes
            .map((o) => `<option value="${o.id}">#${o.id} — ${U.escaparHtml(o.cliente_razon_social)} (${U.formatearFecha(o.despachado_en)})</option>`)
            .join("")
        : '<option value="">No hay órdenes de venta en estado DESPACHADA</option>';
    } catch (err) {
      ventaOrden.innerHTML = '<option value="">No se pudieron cargar las órdenes de venta</option>';
      mostrarErrorModal(modalVentaError, err.message || "No se pudieron cargar las órdenes de venta despachadas.");
      if (window.UI) window.UI.toast(err.message || "No se pudieron cargar las órdenes de venta despachadas.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  async function guardarGuiaDesdeVenta(ev) {
    ev.preventDefault();
    ocultarErrorModal(modalVentaError);

    const errores = [];
    if (!ventaOrden.value) errores.push("Selecciona una orden de venta despachada.");
    if (!ventaMotivo.value.trim()) errores.push("El motivo de traslado es obligatorio.");
    if (ventaNumero.value.trim().length > 30) errores.push("El número de guía no puede superar los 30 caracteres.");
    if (errores.length) {
      mostrarErrorModal(modalVentaError, errores.join(" "));
      return;
    }

    const ordenVentaId = Number(ventaOrden.value);
    const payload = {
      motivo_traslado: ventaMotivo.value.trim(),
      numero_guia: ventaNumero.value.trim() || null,
    };

    const confirmado = window.UI
      ? await window.UI.confirmar({
          titulo: "Generar guía de remisión",
          mensaje: `¿Deseas generar la guía de remisión para la orden de venta #${ordenVentaId}? Los renglones se derivarán automáticamente del Kardex de este despacho.`,
          textoAceptar: "Generar",
          variante: "primary",
        })
      : true;
    if (!confirmado) return;

    if (window.UI) window.UI.mostrarCargando();
    try {
      const guia = await apiPost(`/api/guias-remision/desde-venta/${ordenVentaId}`, payload);
      if (window.UI) window.UI.toast(`Guía de remisión ${guia.numero_guia} generada correctamente.`, "success");
      modalVenta.hide();
      await cargarGuias();
    } catch (err) {
      mostrarErrorModal(modalVentaError, err.message || "No se pudo generar la guía de remisión desde la orden de venta.");
      if (window.UI) window.UI.toast(err.message || "No se pudo generar la guía de remisión.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Detalle ----------
  function pintarDetalleInfo(g) {
    const filas = [
      ["N.º de guía", U.escaparHtml(g.numero_guia)],
      ["Estado", `<span class="badge text-bg-${colorEstado(g.estado)}">${U.escaparHtml(g.estado)}</span>`],
      ["Cliente", U.escaparHtml(g.cliente_razon_social)],
      ["Origen", U.escaparHtml(origenTexto(g))],
      ["Motivo de traslado", U.escaparHtml(g.motivo_traslado)],
      ["Fecha de emisión", U.formatearFechaHora(g.fecha_emision)],
      ["Creada", U.formatearFechaHora(g.creado_en)],
      ["Anulada", g.anulado_en ? U.formatearFechaHora(g.anulado_en) : "—"],
    ];
    detalleInfo.innerHTML = filas
      .map(([label, valor]) => `<div class="col-6"><div class="text-muted-erp" style="font-size:12px;">${label}</div><div>${valor}</div></div>`)
      .join("");
  }

  function pintarDetalleRenglones(g) {
    tbodyDetalleVerGuia.innerHTML = g.detalles.length
      ? g.detalles
          .map(
            (d) => `
        <tr>
          <td>#${d.producto_id}</td>
          <td>#${d.lote_id}</td>
          <td class="text-end">${U.formatearNumero(d.cantidad, 3)}</td>
          <td>${U.escaparHtml(d.unidad_medida)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(4, "Esta guía no tiene renglones.");
  }

  async function abrirModalDetalle(id) {
    if (!modalDetalle) {
      mostrarError("No se pudo abrir el detalle de la guía: Bootstrap no está disponible.");
      if (window.UI) window.UI.toast("No se pudo abrir el detalle de la guía: Bootstrap no está disponible.", "error");
      return;
    }
    ocultarErrorModal(modalDetalleError);
    detalleTitulo.textContent = `Guía de remisión #${id}`;
    detalleInfo.innerHTML = "";
    tbodyDetalleVerGuia.innerHTML = filaVacia(4, "Cargando…");
    modalDetalle.show();

    if (window.UI) window.UI.mostrarCargando();
    try {
      const guia = await apiGet(`/api/guias-remision/${id}`);
      pintarDetalleInfo(guia);
      pintarDetalleRenglones(guia);
    } catch (err) {
      mostrarErrorModal(modalDetalleError, err.message || "No se pudo cargar la guía de remisión.");
      if (window.UI) window.UI.toast(err.message || "No se pudo cargar la guía de remisión.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    selectEstado.addEventListener("change", cargarGuias);
    inputBuscarGuias.addEventListener(
      "input",
      U.debounce(() => {
        paginadorGuias.reiniciar();
        pintarGuias();
      }, 200)
    );
    selectTamanioPaginaGuias.addEventListener("change", () => {
      paginadorGuias.reiniciar();
      pintarGuias();
    });

    btnNuevaGuia.addEventListener("click", abrirModalNuevaGuia);
    formNueva.addEventListener("submit", guardarNuevaGuia);

    btnGuiaDesdeVenta.addEventListener("click", abrirModalDesdeVenta);
    formVenta.addEventListener("submit", guardarGuiaDesdeVenta);

    cargarGuias();
  }

  iniciar();
})();
