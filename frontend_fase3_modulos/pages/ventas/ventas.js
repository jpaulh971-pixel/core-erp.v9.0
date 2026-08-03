/**
 * pages/ventas/ventas.js — Page-script del módulo m10_ventas
 * (app/modules/m10_ventas).
 *
 * Endpoints (contrato real: router.py + schemas.py), todos con Bearer:
 *   GET  /api/ventas?estado=str|null              -> list[OrdenVentaOut]
 *   GET  /api/ventas/{id}                         -> OrdenVentaOut
 *   POST /api/ventas             body OrdenVentaCrear -> OrdenVentaOut (201)
 *   POST /api/ventas/{id}/confirmar                -> OrdenVentaOut
 *   POST /api/ventas/{id}/despachar                -> OrdenVentaOut
 *   POST /api/ventas/{id}/cancelar                 -> OrdenVentaOut
 *
 * OrdenVentaCrear: cliente_id, moneda (default "PEN"), observaciones?,
 * items: [{producto_id, cantidad>0, precio_unitario_venta>=0}] (mínimo 1).
 * OrdenVentaOut: id, cliente_id, cliente_razon_social, moneda, estado,
 * observaciones, creado_en, confirmado_en, despachado_en, cancelado_en,
 * items[]. A diferencia de m04_compras, aquí el propio OrdenVentaOut ya
 * trae "cliente_razon_social", así que el listado NO necesita cruzar con
 * el cache de clientes para mostrar el nombre.
 *
 * Estados reales del Backend (app/modules/m10_ventas/validators.py,
 * TRANSICIONES_VALIDAS) -- OJO: es "BORRADOR", no "CREADA":
 *   BORRADOR   -> CONFIRMADA | CANCELADA
 *   CONFIRMADA -> DESPACHADA | CANCELADA
 *   DESPACHADA / CANCELADA -> (estados finales, sin transición)
 * No existe endpoint de "finalizar": DESPACHADA ya es el estado final del
 * ciclo comercial en este Backend (el comprobante SUNAT es un objeto
 * aparte, emitido desde m12_sunat una vez que la orden está DESPACHADA).
 * El botón correspondiente se oculta si el estado actual no tiene esa
 * transición habilitada (validado en el cliente solo para UX; el Backend
 * es quien realmente la exige y devuelve 400 si no corresponde).
 *
 * Dependen de m11_clientes (GET /api/clientes) para el selector de
 * cliente, y de m02_productos (GET /api/productos) para el selector de
 * producto de cada ítem. El enlace "Ver / emitir comprobante SUNAT" (solo
 * visible en DESPACHADA) navega a pages/sunat/index.html?orden_venta_id=
 * <id>, que ese módulo usa para preseleccionar la orden.
 *
 * FASE F4 — Hallazgos de contrato de esta fase (ventas), a tener
 * presentes en fases futuras, en línea con el mismo criterio ya aplicado
 * en F2 (Inventario) y F3 (Compras):
 * - A diferencia de m04_compras, aquí las 3 transiciones pedidas en el
 *   objetivo de fase ("Aprobar / Despachar / Cancelar") sí existen todas
 *   en el Backend, aunque la primera se llama "confirmar" (no "aprobar")
 *   en TRANSICIONES_VALIDAS y en el endpoint POST /api/ventas/{id}/confirmar.
 *   Se etiqueta el botón como "Confirmar" (nombre real de la transición
 *   en este módulo), sin inventar un endpoint "aprobar" que no existe
 *   aquí.
 * - "Editar orden" NO se implementa como llamada al Backend: no existe
 *   ningún endpoint PUT/PATCH sobre /api/ventas/{id} en router.py. Se
 *   documenta la limitación en la propia pantalla (nota bajo el
 *   historial de estados), igual que se hizo en F3 para Compras.
 * - El listado (GET /api/ventas) solo admite el filtro `estado` en el
 *   Backend: no hay parámetros de búsqueda por texto ni de paginación
 *   (page/limit). La búsqueda por texto y la paginación de esta fase se
 *   resuelven en el cliente sobre la lista ya cargada (mismo criterio
 *   que F1/F2/F3 para sus propios módulos).
 * - El "historial de estados" se arma en el cliente con los 4 timestamps
 *   que ya trae OrdenVentaOut (creado_en/confirmado_en/despachado_en/
 *   cancelado_en); no se creó ningún endpoint nuevo de auditoría.
 *
 * FASE 4 — Costo Unitario y Margen en el detalle de una orden (backend
 * intacto: m08_costos, m09_moneda, PEPS/FEFO, Kardex y el motor de
 * valorización no se tocaron).
 * OrdenVentaItemOut YA trae `costo_unitario` (ver schemas.py de
 * m10_ventas): lo calcula `_adjuntar_costo_unitario()` en
 * m10_ventas/service.py leyendo el kardex real
 * (`inventario_service.costo_unitario_por_referencia`, motor PEPS/FEFO,
 * m03) en el momento del despacho. Mientras la orden no está DESPACHADA
 * ese campo llega en `null` a propósito (el costo real todavía no existe,
 * no se estima). La tabla de ítems del modal "Detalle de orden"
 * (`tbodyDetalleItems`) ahora pinta ese campo tal cual, sin recalcularlo
 * ("Costo Unitario" = `it.costo_unitario`, "—" si es `null`).
 * "Margen" NO tiene un endpoint propio a nivel de ítem de una orden
 * puntual (el único cálculo de margen que expone el Backend,
 * `GET /api/inteligencia-comercial/margen-productos`, es un agregado
 * histórico "top N" por producto, no el margen de esta línea de esta
 * orden — mezclarlos habría sido incorrecto, no solo redundante). Por
 * eso, y porque la consigna de esta fase permite calcular margen en el
 * cliente cuando no existe ya en el Backend, `margenItem()` calcula
 * `precio_unitario_venta - costo_unitario` (y su porcentaje sobre el
 * precio) usando la MISMA fórmula que ya usa el Backend en
 * `m08_costos.service` y `m13_inteligencia_comercial.service`
 * (`margen_pct = (precio - costo) / precio * 100`) — no es una regla de
 * costeo nueva, es una resta/porcentaje de 2 valores que el Backend ya
 * calculó y expuso. Si `costo_unitario` es `null` (orden aún no
 * despachada), "Margen" muestra "—" en vez de un número inventado.
 * "Subtotal" no cambió: sigue siendo `cantidad * precio_unitario_venta`,
 * el mismo cálculo de ingreso (no de costeo) que ya existía en esta
 * pantalla antes de esta fase.
 * El listado de órdenes (`tbodyOrdenes`, una fila por ORDEN, no por
 * ítem) no gana columnas de costo/margen: una orden puede tener varios
 * productos con costos distintos, así que ese desglose solo tiene
 * sentido a nivel de ítem, en el modal de detalle.
 *
 * FASE 10A — Importar Ventas (frontend), patrón calcado de Compras (F3/F9B):
 *   POST /api/ventas/importar/previsualizar?inventario_salida_id=<id>  (multipart: archivo)
 *   POST /api/ventas/importar/confirmar?inventario_salida_id=<id>      (multipart: archivo)
 * `inventario_salida_id` identifica el almacén desde el que se despachará
 * (mismo rol que `inventario_destino_id` en Compras, pero de salida en vez
 * de entrada); se obtiene del mismo selector `GET /api/inventario/inventarios`
 * ya usado en Compras. A diferencia de Compras, la confirmación de Ventas es
 * todo-o-nada (ver m10_ventas/importacion_service.py): si alguna fila falla,
 * el Backend devuelve 400 y no crea ninguna orden — por eso
 * `ConfirmarImportacionVentasOut` no trae `filas_fallidas` y no hace falta
 * pintar una tabla de fallos parciales tras confirmar. Cada orden creada se
 * despacha en el mismo paso (crear -> confirmar -> despachar), así que al
 * terminar ya impactó Inventario/Kardex; por eso se notifica
 * `erp_datos_actualizados` (modulo: "ventas") igual que hace Compras.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const TRANSICIONES_VALIDAS = {
    BORRADOR: new Set(["CONFIRMADA", "CANCELADA"]),
    CONFIRMADA: new Set(["DESPACHADA", "CANCELADA"]),
    DESPACHADA: new Set(),
    CANCELADA: new Set(),
  };

  const elError = document.getElementById("estadoError");
  const selectEstado = document.getElementById("selectEstado");
  const inputBuscarOrdenes = document.getElementById("inputBuscarOrdenes");
  const btnNuevaOrden = document.getElementById("btnNuevaOrden");
  const tbody = document.getElementById("tbodyOrdenes");
  const selectTamanioPaginaOrdenes = document.getElementById("selectTamanioPaginaOrdenes");

  const modalNuevaOrdenEl = document.getElementById("modalNuevaOrden");
  // Protección mínima: si el CDN de Bootstrap no cargó, bootstrap no existe
  // y "new bootstrap.Modal(...)" rompería toda la página. En ese caso el
  // modal queda en null y las funciones que lo usan avisan el error en vez
  // de lanzar un TypeError.
  const bootstrapDisponible = typeof bootstrap !== "undefined" && bootstrap.Modal;
  const modalNuevaOrden = bootstrapDisponible ? new bootstrap.Modal(modalNuevaOrdenEl) : null;
  const formNuevaOrden = document.getElementById("formNuevaOrden");
  const modalNuevaOrdenError = document.getElementById("modalNuevaOrdenError");
  const ordenCliente = document.getElementById("ordenCliente");
  const ordenMoneda = document.getElementById("ordenMoneda");
  const ordenObservaciones = document.getElementById("ordenObservaciones");
  const btnAgregarItem = document.getElementById("btnAgregarItem");
  const tbodyItemsOrden = document.getElementById("tbodyItemsOrden");
  const totalOrdenEl = document.getElementById("totalOrden");

  const modalDetalleEl = document.getElementById("modalDetalleOrden");
  const modalDetalle = bootstrapDisponible ? new bootstrap.Modal(modalDetalleEl) : null;
  const detalleOrdenTitulo = document.getElementById("detalleOrdenTitulo");
  const modalDetalleOrdenError = document.getElementById("modalDetalleOrdenError");
  const detalleOrdenInfo = document.getElementById("detalleOrdenInfo");
  const tbodyDetalleItems = document.getElementById("tbodyDetalleItems");
  const historialEstadosOrden = document.getElementById("historialEstadosOrden");
  const bloqueComprobante = document.getElementById("bloqueComprobante");
  const linkVerSunat = document.getElementById("linkVerSunat");
  const btnConfirmarOrden = document.getElementById("btnConfirmarOrden");
  const btnDespacharOrden = document.getElementById("btnDespacharOrden");
  const btnCancelarOrden = document.getElementById("btnCancelarOrden");

  const btnImportarVentas = document.getElementById("btnImportarVentas");
  const modalImportarVentasEl = document.getElementById("modalImportarVentas");
  const modalImportarVentas = bootstrapDisponible ? new bootstrap.Modal(modalImportarVentasEl) : null;
  const errorImportarVentas = document.getElementById("errorImportarVentas");
  const selectInventarioImportarVentas = document.getElementById("selectInventarioImportarVentas");
  const inputArchivoImportarVentas = document.getElementById("inputArchivoImportarVentas");
  const btnPrevisualizarImportarVentas = document.getElementById("btnPrevisualizarImportarVentas");
  const resumenImportarVentas = document.getElementById("resumenImportarVentas");
  const statsImportarVentas = document.getElementById("statsImportarVentas");
  const bloqueErroresImportarVentas = document.getElementById("bloqueErroresImportarVentas");
  const tbodyErroresImportarVentas = document.getElementById("tbodyErroresImportarVentas");
  const resultadoImportarVentas = document.getElementById("resultadoImportarVentas");
  const notaImportarVentas = document.getElementById("notaImportarVentas");
  const btnConfirmarImportarVentas = document.getElementById("btnConfirmarImportarVentas");

  let clientesCache = [];
  let productosCache = [];
  let ordenesCache = [];
  let ordenDetalleActualId = null;
  let ordenDetalleActual = null;
  let contadorFilaItem = 0;

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
    // FASE F0: delega en el cliente API centralizado (api-client.js).
    // Se conserva esta función local -mismo nombre y firma- para no
    // tocar ningún call-site existente en este archivo.
    return window.Api.request(path, opciones);
  }

  const apiGet = (path) => apiRequest(path);
  const apiPost = (path, body) =>
    apiRequest(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined });

  function filaVacia(colspan, texto) {
    return `<tr><td colspan="${colspan}" class="text-muted-erp">${texto}</td></tr>`;
  }

  function colorEstado(estado) {
    if (estado === "BORRADOR") return "secondary";
    if (estado === "CONFIRMADA") return "info";
    if (estado === "DESPACHADA") return "success";
    if (estado === "CANCELADA") return "danger";
    return "secondary";
  }

  function nombreProducto(productoId) {
    const p = productosCache.find((x) => x.id === productoId);
    return p ? `${p.codigo} — ${p.nombre}` : `#${productoId}`;
  }

  function totalOrden(orden) {
    return orden.items.reduce((acc, it) => acc + Number(it.cantidad) * Number(it.precio_unitario_venta), 0);
  }

  // Resume "Unidad de Medida" de TODA la orden para la columna del listado
  // principal (mismo criterio que presentacionUnidadOrden() en compras.js).
  function unidadMedidaOrden(orden) {
    const unicas = [...new Set(orden.items.map((it) => it.unidad_medida).filter(Boolean))];
    return unicas.length ? unicas.join(", ") : "—";
  }

  // ---------- Paginador genérico reutilizable (mismo criterio que
  // inventario.js de F2 y compras.js de F3: el Backend no expone
  // page/limit en /api/ventas, así que la paginación de la tabla se
  // resuelve en el cliente sobre la lista ya cargada) ----------
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

  const paginadorOrdenes = crearPaginador(
    selectTamanioPaginaOrdenes,
    document.getElementById("paginacionResumenOrdenes"),
    document.getElementById("paginacionControlesOrdenes"),
    () => pintarOrdenes()
  );

  // ---------- Búsqueda (cliente, ya que /api/ventas solo filtra por
  // "estado" en el Backend) ----------
  function filtrarOrdenes(lista) {
    const q = inputBuscarOrdenes.value.trim().toLowerCase();
    if (!q) return lista;
    return lista.filter((o) => {
      const numero = `#${o.id}`.toLowerCase();
      const cliente = (o.cliente_razon_social || "").toLowerCase();
      const observaciones = (o.observaciones || "").toLowerCase();
      return numero.includes(q) || cliente.includes(q) || observaciones.includes(q);
    });
  }

  // ---------- Listado ----------
  function pintarOrdenes() {
    const filtradas = filtrarOrdenes(ordenesCache);
    const info = paginadorOrdenes.calcular(filtradas);

    tbody.innerHTML = info.pagina.length
      ? info.pagina
          .map(
            (o) => `
        <tr>
          <td>#${o.id}</td>
          <td>${U.escaparHtml(o.cliente_razon_social)}</td>
          <td><span class="badge text-bg-${colorEstado(o.estado)}">${U.escaparHtml(o.estado)}</span></td>
          <td>${U.escaparHtml(o.moneda)}</td>
          <td>${U.escaparHtml(unidadMedidaOrden(o))}</td>
          <td class="text-end">${U.formatearMoneda(totalOrden(o), o.moneda)}</td>
          <td>${U.formatearFechaHora(o.creado_en)}</td>
          <td class="text-end">
            <button type="button" class="btn btn-sm btn-outline-secondary btn-ver-detalle" data-id="${o.id}">
              <i class="bi bi-eye"></i> Ver
            </button>
          </td>
        </tr>`
          )
          .join("")
      : filaVacia(
          8,
          ordenesCache.length === 0
            ? "No hay órdenes de venta registradas."
            : "Ninguna orden coincide con la búsqueda/filtro."
        );

    tbody.querySelectorAll(".btn-ver-detalle").forEach((btn) => {
      btn.addEventListener("click", () => abrirModalDetalle(Number(btn.dataset.id)));
    });
  }

  async function cargarOrdenes() {
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      const query = selectEstado.value ? `?estado=${encodeURIComponent(selectEstado.value)}` : "";
      ordenesCache = await apiGet(`/api/ventas${query}`);
      paginadorOrdenes.reiniciar();
      pintarOrdenes();
    } catch (err) {
      mostrarError(err.message || "Ocurrió un error al cargar las órdenes de venta.");
      if (window.UI) window.UI.toast(err.message || "Ocurrió un error al cargar las órdenes de venta.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Caches de clientes y productos ----------
  async function cargarClientesCache() {
    // solo_activos=true: para crear una orden nueva solo tiene sentido
    // elegir clientes activos (el propio Backend lo exige al crear).
    clientesCache = await apiGet("/api/clientes?solo_activos=true");
    ordenCliente.innerHTML =
      '<option value="">Seleccionar…</option>' +
      clientesCache
        .map((c) => `<option value="${c.id}">${U.escaparHtml(c.ruc)} — ${U.escaparHtml(c.razon_social)}</option>`)
        .join("");
  }

  async function cargarProductosCache() {
    productosCache = await apiGet("/api/productos?solo_activos=true");
  }

  // ---------- Modal Nueva orden: ítems dinámicos ----------
  function opcionesProductoHtml() {
    return (
      '<option value="">Seleccionar…</option>' +
      productosCache.map((p) => `<option value="${p.id}">${U.escaparHtml(p.codigo)} — ${U.escaparHtml(p.nombre)}</option>`).join("")
    );
  }

  function recalcularSubtotalFila(fila) {
    const cantidad = Number(fila.querySelector(".item-cantidad").value) || 0;
    const precio = Number(fila.querySelector(".item-precio").value) || 0;
    fila.querySelector(".item-subtotal").textContent = U.formatearNumero(cantidad * precio, 2);
    recalcularTotalOrden();
  }

  function recalcularTotalOrden() {
    let total = 0;
    tbodyItemsOrden.querySelectorAll("tr").forEach((fila) => {
      const cantidad = Number(fila.querySelector(".item-cantidad").value) || 0;
      const precio = Number(fila.querySelector(".item-precio").value) || 0;
      total += cantidad * precio;
    });
    totalOrdenEl.textContent = U.formatearNumero(total, 2);
  }

  function agregarFilaItem() {
    contadorFilaItem += 1;
    const fila = document.createElement("tr");
    fila.dataset.fila = String(contadorFilaItem);
    fila.innerHTML = `
      <td><select class="form-select form-select-sm item-producto" required>${opcionesProductoHtml()}</select></td>
      <td><input type="number" class="form-control form-control-sm item-cantidad" min="0.001" step="0.001" required /></td>
      <td><input type="number" class="form-control form-control-sm item-precio" min="0" step="0.0001" required /></td>
      <td class="text-end item-subtotal">0.00</td>
      <td class="text-end">
        <button type="button" class="btn btn-sm btn-outline-danger btn-quitar-item"><i class="bi bi-trash"></i></button>
      </td>`;
    tbodyItemsOrden.appendChild(fila);

    fila.querySelector(".item-cantidad").addEventListener("input", () => recalcularSubtotalFila(fila));
    fila.querySelector(".item-precio").addEventListener("input", () => recalcularSubtotalFila(fila));
    fila.querySelector(".btn-quitar-item").addEventListener("click", () => {
      // Al menos un ítem es obligatorio (mínimo 1 exigido por
      // OrdenVentaCrear en el Backend): no se deja quitar la última fila.
      if (tbodyItemsOrden.querySelectorAll("tr").length <= 1) {
        mostrarErrorModal(modalNuevaOrdenError, "La orden debe tener al menos un ítem: agrega otro antes de quitar este.");
        return;
      }
      fila.remove();
      recalcularTotalOrden();
    });
  }

  function limpiarFormularioNuevaOrden() {
    formNuevaOrden.reset();
    tbodyItemsOrden.innerHTML = "";
    totalOrdenEl.textContent = "0.00";
    ocultarErrorModal(modalNuevaOrdenError);
    agregarFilaItem();
  }

  function abrirModalNuevaOrden() {
    if (!modalNuevaOrden) {
      mostrarError("No se pudo abrir la ventana de nueva orden: Bootstrap no está disponible.");
      if (window.UI) window.UI.toast("No se pudo abrir la ventana de nueva orden: Bootstrap no está disponible.", "error");
      return;
    }
    limpiarFormularioNuevaOrden();
    modalNuevaOrden.show();
  }

  function leerItemsFormulario() {
    const items = [];
    tbodyItemsOrden.querySelectorAll("tr").forEach((fila) => {
      const productoId = fila.querySelector(".item-producto").value;
      const cantidad = fila.querySelector(".item-cantidad").value;
      const precio = fila.querySelector(".item-precio").value;
      if (productoId && cantidad && precio !== "") {
        items.push({
          producto_id: Number(productoId),
          cantidad: Number(cantidad),
          precio_unitario_venta: Number(precio),
        });
      }
    });
    return items;
  }

  function validarFormularioNuevaOrden(items) {
    if (!ordenCliente.value) {
      mostrarErrorModal(modalNuevaOrdenError, "Selecciona un cliente.");
      ordenCliente.focus();
      return false;
    }
    if (!items.length) {
      mostrarErrorModal(modalNuevaOrdenError, "Agrega al menos un ítem con producto, cantidad y precio unitario.");
      return false;
    }
    for (const item of items) {
      if (!(item.cantidad > 0)) {
        mostrarErrorModal(modalNuevaOrdenError, "La cantidad de cada ítem debe ser mayor a cero.");
        return false;
      }
      if (!(item.precio_unitario_venta >= 0)) {
        mostrarErrorModal(modalNuevaOrdenError, "El precio unitario de cada ítem no puede ser negativo.");
        return false;
      }
    }
    return true;
  }

  async function guardarNuevaOrden(ev) {
    ev.preventDefault();
    ocultarErrorModal(modalNuevaOrdenError);

    const items = leerItemsFormulario();
    if (!validarFormularioNuevaOrden(items)) return;

    const datos = {
      cliente_id: Number(ordenCliente.value),
      moneda: ordenMoneda.value,
      observaciones: ordenObservaciones.value || null,
      items,
    };

    if (window.UI) window.UI.mostrarCargando();
    try {
      await apiPost("/api/ventas", datos);
      if (modalNuevaOrden) modalNuevaOrden.hide();
      if (window.UI) window.UI.toast("Orden de venta creada correctamente.", "success");
      await cargarOrdenes();
    } catch (err) {
      mostrarErrorModal(modalNuevaOrdenError, err.message || "No se pudo crear la orden de venta.");
      if (window.UI) window.UI.toast(err.message || "No se pudo crear la orden de venta.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Modal Detalle: información + historial + cambio de estado ----------
  function pintarDetalleInfo(orden) {
    detalleOrdenInfo.innerHTML = `
      <div class="col-6"><span class="text-muted-erp">Cliente</span><br>${U.escaparHtml(orden.cliente_razon_social)}</div>
      <div class="col-3"><span class="text-muted-erp">Estado</span><br><span class="badge text-bg-${colorEstado(orden.estado)}">${U.escaparHtml(orden.estado)}</span></div>
      <div class="col-3"><span class="text-muted-erp">Moneda</span><br>${U.escaparHtml(orden.moneda)}</div>
      ${orden.observaciones ? `<div class="col-12"><span class="text-muted-erp">Observaciones</span><br>${U.escaparHtml(orden.observaciones)}</div>` : ""}
    `;
  }

  // Margen de un ítem: NO es una recreación del motor de costeo (PEPS/FEFO
  // sigue viviendo exclusivamente en m03/m08). `it.costo_unitario` ya lo
  // calcula y expone el propio Backend (OrdenVentaItemOut, ver cabecera de
  // archivo): es el costo que el kardex registró al despachar, o `null`
  // mientras la orden no está DESPACHADA (el costo real recién se conoce
  // en ese momento, no se estima). El margen es la resta/porcentaje de 2
  // valores que YA vienen del Backend (precio de venta que puso el
  // usuario + costo que ya calculó el motor), con la misma fórmula que ya
  // usa el propio Backend en m08_costos/m13_inteligencia_comercial
  // (margen_pct = (precio - costo) / precio * 100): no existe un endpoint
  // que devuelva el margen por ítem de una orden puntual, así que -tal
  // como permite la consigna de esta fase- se muestra aquí, no se
  // recalcula ningún costo.
  function margenItem(it) {
    if (it.costo_unitario === null || it.costo_unitario === undefined) return null;
    const margenUnitario = it.precio_unitario_venta - it.costo_unitario;
    const margenPct = it.precio_unitario_venta > 0 ? (margenUnitario / it.precio_unitario_venta) * 100 : null;
    return { margenUnitario, margenPct };
  }

  function pintarDetalleItems(orden) {
    tbodyDetalleItems.innerHTML = orden.items.length
      ? orden.items
          .map((it) => {
            // costo_unitario: null mientras la orden no está DESPACHADA
            // (ver OrdenVentaItemOut/_adjuntar_costo_unitario en el
            // Backend). Se muestra "—" con un title explicativo en vez de
            // inventar un valor.
            const costoCelda =
              it.costo_unitario === null || it.costo_unitario === undefined
                ? `<span class="text-muted-erp" title="El costo se registra recién al despachar la orden (kardex FEFO).">—</span>`
                : U.formatearMoneda(it.costo_unitario, orden.moneda);

            // COGS (Cost of Goods Sold) de esta línea: costo_unitario ya
            // resuelto por el Backend × cantidad ya resuelta por el
            // Backend. No es un cálculo nuevo de costeo (eso sigue
            // viviendo solo en m03/m08): es la misma multiplicación que
            // ya se hace más abajo para "Subtotal" (cantidad × precio),
            // aplicada al costo en vez de al precio de venta.
            const cogsCelda =
              it.costo_unitario === null || it.costo_unitario === undefined
                ? `<span class="text-muted-erp" title="El costo se registra recién al despachar la orden (kardex FEFO).">—</span>`
                : U.formatearMoneda(it.cantidad * it.costo_unitario, orden.moneda);

            const m = margenItem(it);
            const margenCelda = m
              ? `${U.formatearMoneda(m.margenUnitario, orden.moneda)}${m.margenPct !== null ? ` <span class="text-muted-erp">(${U.formatearPorcentaje(m.margenPct)})</span>` : ""}`
              : `<span class="text-muted-erp" title="Sin costo todavía: el margen se calcula recién con el costo real del despacho.">—</span>`;

            return `
        <tr>
          <td>${U.escaparHtml(nombreProducto(it.producto_id))}</td>
          <td class="text-end">${U.formatearNumero(it.cantidad, 3)}</td>
          <td class="text-end">${costoCelda}</td>
          <td class="text-end">${cogsCelda}</td>
          <td class="text-end">${U.formatearMoneda(it.precio_unitario_venta, orden.moneda)}</td>
          <td class="text-end">${margenCelda}</td>
          <td class="text-end">${U.formatearMoneda(it.cantidad * it.precio_unitario_venta, orden.moneda)}</td>
        </tr>`;
          })
          .join("")
      : filaVacia(7, "Esta orden no tiene ítems.");
  }

  // Historial de estados: se arma en el cliente con los 4 timestamps que
  // ya trae OrdenVentaOut (no hay endpoint de auditoría/historial en el
  // Backend). Solo se listan los hitos que aplican según el estado actual
  // (una orden CANCELADA nunca tendrá despachado_en, por ejemplo).
  function pintarHistorialEstados(orden) {
    const hitos = [
      { etiqueta: "Creada (borrador)", fecha: orden.creado_en, icono: "bi-plus-circle-fill", color: "text-secondary" },
      { etiqueta: "Confirmada", fecha: orden.confirmado_en, icono: "bi-check-circle-fill", color: "text-info" },
      { etiqueta: "Despachada", fecha: orden.despachado_en, icono: "bi-truck", color: "text-success" },
      { etiqueta: "Cancelada", fecha: orden.cancelado_en, icono: "bi-x-circle-fill", color: "text-danger" },
    ];

    // Si la orden fue cancelada, "Despachada" ya no puede ocurrir: se omite
    // en vez de mostrar un hito "pendiente" que no tiene sentido en ese
    // camino. Si aún no fue cancelada, se omite "Cancelada" hasta que ocurra.
    const hitosVisibles = hitos.filter((h) => {
      if (h.etiqueta === "Despachada" && orden.estado === "CANCELADA" && !h.fecha) return false;
      if (h.etiqueta === "Cancelada" && orden.estado !== "CANCELADA" && !h.fecha) return false;
      return true;
    });

    historialEstadosOrden.innerHTML = hitosVisibles
      .map((h) => {
        const ocurrido = Boolean(h.fecha);
        return `
        <div class="historial-item">
          <div class="historial-icono ${ocurrido ? h.color : "pendiente"}"><i class="bi ${ocurrido ? h.icono : "bi-dash-circle"}"></i></div>
          <div>
            <div class="${ocurrido ? "" : "text-muted-erp"}">${U.escaparHtml(h.etiqueta)}</div>
            <div class="text-muted-erp" style="font-size:12px;">${ocurrido ? U.formatearFechaHora(h.fecha) : "Pendiente"}</div>
          </div>
        </div>`;
      })
      .join("");
  }

  function actualizarBotonesTransicion(orden) {
    const estado = orden.estado;
    const permitidas = TRANSICIONES_VALIDAS[estado] || new Set();
    btnConfirmarOrden.style.display = permitidas.has("CONFIRMADA") ? "" : "none";
    btnDespacharOrden.style.display = permitidas.has("DESPACHADA") ? "" : "none";
    btnCancelarOrden.style.display = permitidas.has("CANCELADA") ? "" : "none";

    // El comprobante SUNAT solo puede emitirse para órdenes DESPACHADAS
    // (validar_orden_despachada en m12_sunat/validators.py).
    if (estado === "DESPACHADA") {
      linkVerSunat.href = `../sunat/index.html?orden_venta_id=${orden.id}`;
      bloqueComprobante.style.display = "";
    } else {
      bloqueComprobante.style.display = "none";
    }
  }

  async function abrirModalDetalle(id) {
    if (!modalDetalle) {
      mostrarError("No se pudo abrir el detalle de la orden: Bootstrap no está disponible.");
      if (window.UI) window.UI.toast("No se pudo abrir el detalle de la orden: Bootstrap no está disponible.", "error");
      return;
    }
    ordenDetalleActualId = id;
    ordenDetalleActual = null;
    ocultarErrorModal(modalDetalleOrdenError);
    detalleOrdenTitulo.textContent = `Orden de venta #${id}`;
    tbodyDetalleItems.innerHTML = filaVacia(7, "Cargando…");
    detalleOrdenInfo.innerHTML = "";
    historialEstadosOrden.innerHTML = "";
    bloqueComprobante.style.display = "none";
    actualizarBotonesTransicion({ estado: "" });
    modalDetalle.show();

    if (window.UI) window.UI.mostrarCargando();
    try {
      const orden = await apiGet(`/api/ventas/${id}`);
      ordenDetalleActual = orden;
      pintarDetalleInfo(orden);
      pintarDetalleItems(orden);
      pintarHistorialEstados(orden);
      actualizarBotonesTransicion(orden);
    } catch (err) {
      mostrarErrorModal(modalDetalleOrdenError, err.message || "No se pudo cargar la orden de venta.");
      if (window.UI) window.UI.toast(err.message || "No se pudo cargar la orden de venta.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  const CONFIRMACION_TRANSICION = {
    confirmar: {
      titulo: "Confirmar orden de venta",
      mensaje: (id) => `¿Deseas confirmar la orden de venta #${id}? Esta acción avanza su estado y no se puede deshacer desde aquí.`,
      textoAceptar: "Confirmar",
      variante: "primary",
      mensajeExito: (id) => `Orden de venta #${id} confirmada correctamente.`,
      mensajeError: "No se pudo confirmar la orden de venta.",
    },
    despachar: {
      titulo: "Despachar orden de venta",
      mensaje: (id) => `¿Confirmas el despacho de la orden de venta #${id}? Esta acción marca la orden como despachada y no se puede deshacer desde aquí.`,
      textoAceptar: "Despachar",
      variante: "primary",
      mensajeExito: (id) => `Orden de venta #${id} marcada como despachada.`,
      mensajeError: "No se pudo registrar el despacho de la orden de venta.",
    },
    cancelar: {
      titulo: "Cancelar orden de venta",
      mensaje: (id) => `¿Deseas cancelar la orden de venta #${id}? Esta acción es definitiva: la orden quedará en estado CANCELADA y no podrá confirmarse ni despacharse.`,
      textoAceptar: "Cancelar orden",
      variante: "danger",
      mensajeExito: (id) => `Orden de venta #${id} cancelada correctamente.`,
      mensajeError: "No se pudo cancelar la orden de venta.",
    },
  };

  async function ejecutarTransicion(accion) {
    if (!ordenDetalleActualId) return;
    const cfg = CONFIRMACION_TRANSICION[accion];

    const confirmado = window.UI
      ? await window.UI.confirmar({
          titulo: cfg.titulo,
          mensaje: cfg.mensaje(ordenDetalleActualId),
          textoAceptar: cfg.textoAceptar,
          variante: cfg.variante,
        })
      : true;
    if (!confirmado) return;

    ocultarErrorModal(modalDetalleOrdenError);
    if (window.UI) window.UI.mostrarCargando();
    try {
      const orden = await apiPost(`/api/ventas/${ordenDetalleActualId}/${accion}`);
      ordenDetalleActual = orden;
      pintarDetalleInfo(orden);
      pintarDetalleItems(orden);
      pintarHistorialEstados(orden);
      actualizarBotonesTransicion(orden);
      if (window.UI) window.UI.toast(cfg.mensajeExito(ordenDetalleActualId), "success");
      await cargarOrdenes();
    } catch (err) {
      mostrarErrorModal(modalDetalleOrdenError, err.message || cfg.mensajeError);
      if (window.UI) window.UI.toast(err.message || cfg.mensajeError, "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Importar Ventas (Fase 10A): POST /api/ventas/importar/previsualizar
  // y POST /api/ventas/importar/confirmar, ambos con querystring
  // inventario_salida_id (obligatorio, igual que inventario_destino_id en
  // Compras) y el archivo como multipart/form-data. Patrón calcado de
  // compras.js (F3/F9B), adaptado a 2 diferencias reales del contrato de
  // m10_ventas frente a m04_compras:
  //  - Las filas de FilaImportacionVentaOut no tienen campo "producto":
  //    tienen "descripcion" (y opcionalmente "codigo_producto"), así que
  //    el conteo de "Productos distintos" del preview usa f.descripcion.
  //  - ConfirmarImportacionVentasOut NO trae "filas_fallidas": el
  //    Backend de Ventas es todo-o-nada (ver importacion_service.py), así
  //    que si algo falla al confirmar, la propia petición devuelve 400 y
  //    cae en el catch() de abajo; no hay una lista parcial que pintar.
  let inventariosImportarVentasCache = [];
  let previewImportarVentasActual = null;

  async function apiPostArchivoVentas(path, formData) {
    const token = window.Auth ? window.Auth.obtenerToken() : null;
    const headers = {};
    if (token) headers.Authorization = `Bearer ${token}`;

    let resp;
    try {
      resp = await fetch(`${CONFIG.API_BASE_URL}${path}`, { method: "POST", headers, body: formData });
    } catch (err) {
      const errorRed = new Error(
        `No se pudo conectar con el Backend (${CONFIG.API_BASE_URL}). Verifica que esté corriendo.`
      );
      errorRed.status = 0;
      throw errorRed;
    }

    if (resp.status === 401) {
      if (window.Auth) window.Auth.cerrarSesion();
      const error = new Error("Sesión expirada.");
      error.status = 401;
      throw error;
    }
    if (!resp.ok) {
      let detalle = `HTTP ${resp.status}`;
      try {
        const datos = await resp.json();
        if (datos && datos.detail) {
          detalle = Array.isArray(datos.detail) ? datos.detail.map((d) => d.msg).join("; ") : datos.detail;
        }
      } catch (err) {
        /* sin cuerpo JSON */
      }
      const error = new Error(detalle);
      error.status = resp.status;
      throw error;
    }
    return resp.json();
  }

  async function cargarInventariosImportarVentas() {
    selectInventarioImportarVentas.innerHTML = `<option value="">Cargando almacenes…</option>`;
    try {
      inventariosImportarVentasCache = await apiGet("/api/inventario/inventarios");
      if (!inventariosImportarVentasCache.length) {
        selectInventarioImportarVentas.innerHTML = `<option value="">No hay almacenes registrados</option>`;
        return;
      }
      selectInventarioImportarVentas.innerHTML =
        `<option value="">Seleccionar…</option>` +
        inventariosImportarVentasCache
          .map((inv) => `<option value="${inv.id}">${U.escaparHtml(inv.codigo)} — ${U.escaparHtml(inv.nombre)}</option>`)
          .join("");
    } catch (err) {
      selectInventarioImportarVentas.innerHTML = `<option value="">Error al cargar almacenes</option>`;
      mostrarErrorModal(errorImportarVentas, err.message || "No se pudieron cargar los almacenes.");
      if (window.UI) window.UI.toast(err.message || "No se pudieron cargar los almacenes.", "error");
    }
  }

  function reiniciarModalImportarVentas() {
    ocultarErrorModal(errorImportarVentas);
    inputArchivoImportarVentas.value = "";
    resumenImportarVentas.style.display = "none";
    resultadoImportarVentas.style.display = "none";
    resultadoImportarVentas.innerHTML = "";
    statsImportarVentas.innerHTML = "";
    bloqueErroresImportarVentas.style.display = "none";
    tbodyErroresImportarVentas.innerHTML = "";
    notaImportarVentas.textContent = "";
    btnConfirmarImportarVentas.disabled = true;
    previewImportarVentasActual = null;
  }

  function abrirModalImportarVentas() {
    if (!modalImportarVentas) {
      mostrarError("No se pudo abrir la importación de ventas: Bootstrap no está disponible.");
      if (window.UI) window.UI.toast("No se pudo abrir la importación de ventas: Bootstrap no está disponible.", "error");
      return;
    }
    reiniciarModalImportarVentas();
    cargarInventariosImportarVentas();
    modalImportarVentas.show();
  }

  function renderStatsImportarVentas(items) {
    statsImportarVentas.innerHTML = items
      .map(
        (it) => `
        <div class="stat-box">
          <div class="stat-valor">${U.escaparHtml(String(it.valor))}</div>
          <div class="stat-etiqueta">${U.escaparHtml(it.etiqueta)}</div>
        </div>`
      )
      .join("");
  }

  function pintarPreviewImportarVentas(preview) {
    previewImportarVentasActual = preview;
    resumenImportarVentas.style.display = "block";
    resultadoImportarVentas.style.display = "none";
    resultadoImportarVentas.innerHTML = "";

    const filas = preview.filas || [];
    const filasInvalidas = filas.filter((f) => !f.valida);
    const productosDistintos = new Set(
      filas.filter((f) => f.valida && f.descripcion).map((f) => f.descripcion)
    ).size;

    renderStatsImportarVentas([
      { etiqueta: "Órdenes a crear", valor: preview.ordenes_a_crear },
      { etiqueta: "Productos distintos", valor: productosDistintos },
      { etiqueta: "Total de filas", valor: preview.total_filas },
      { etiqueta: "Filas válidas", valor: preview.filas_validas },
      { etiqueta: "Errores/advertencias", valor: preview.filas_con_error },
    ]);

    if (!filasInvalidas.length) {
      bloqueErroresImportarVentas.style.display = "none";
      tbodyErroresImportarVentas.innerHTML = "";
    } else {
      bloqueErroresImportarVentas.style.display = "block";
      tbodyErroresImportarVentas.innerHTML = filasInvalidas
        .map(
          (f) =>
            `<tr class="table-danger"><td>${U.escaparHtml(String(f.numero_fila))}</td><td>${U.escaparHtml(f.mensaje_error || "Fila inválida.")}</td></tr>`
        )
        .join("");
    }

    // Igual que Compras: si existen errores, se bloquea Confirmar.
    if (preview.filas_con_error > 0) {
      btnConfirmarImportarVentas.disabled = true;
      notaImportarVentas.textContent = "Corrige los errores del archivo antes de importar.";
    } else if (preview.filas_validas === 0) {
      btnConfirmarImportarVentas.disabled = true;
      notaImportarVentas.textContent = "No hay filas válidas para importar en este archivo.";
    } else {
      btnConfirmarImportarVentas.disabled = false;
      notaImportarVentas.textContent = `Se crearán ${preview.ordenes_a_crear} orden(es) a partir de ${preview.filas_validas} fila(s) válida(s).`;
    }
  }

  async function previsualizarImportarVentas() {
    ocultarErrorModal(errorImportarVentas);
    resumenImportarVentas.style.display = "none";
    btnConfirmarImportarVentas.disabled = true;

    const inventarioSalidaId = Number(selectInventarioImportarVentas.value) || null;
    if (!inventarioSalidaId) {
      mostrarErrorModal(errorImportarVentas, "Selecciona primero un almacén / inventario de salida.");
      return;
    }
    const archivo = inputArchivoImportarVentas.files && inputArchivoImportarVentas.files[0];
    if (!archivo) {
      mostrarErrorModal(errorImportarVentas, "Selecciona un archivo Excel (.xlsx o .xls).");
      return;
    }

    const formData = new FormData();
    formData.append("archivo", archivo);

    if (window.UI) window.UI.mostrarCargando();
    btnPrevisualizarImportarVentas.disabled = true;
    try {
      const preview = await apiPostArchivoVentas(
        `/api/ventas/importar/previsualizar?inventario_salida_id=${inventarioSalidaId}`,
        formData
      );
      pintarPreviewImportarVentas(preview);
      const mensaje =
        preview.filas_con_error > 0
          ? `Vista previa lista: ${preview.filas_validas} fila(s) válida(s), ${preview.filas_con_error} con error/advertencia.`
          : `Vista previa lista: ${preview.filas_validas} fila(s) válida(s), sin errores.`;
      if (window.UI) window.UI.toast(mensaje, preview.filas_con_error > 0 ? "warning" : "success");
    } catch (err) {
      mostrarErrorModal(errorImportarVentas, err.message || "No se pudo previsualizar el archivo.");
      if (window.UI) window.UI.toast(err.message || "No se pudo previsualizar el archivo.", "error");
    } finally {
      btnPrevisualizarImportarVentas.disabled = false;
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function pintarResultadoConfirmarImportarVentas(resultado) {
    resultadoImportarVentas.style.display = "block";
    const ordenesCreadas = resultado.ordenes_creadas || [];
    resultadoImportarVentas.innerHTML = `
      <div class="alert alert-success mb-2">
        <i class="bi bi-check-circle-fill me-1"></i>Importación confirmada:
        ${U.escaparHtml(String(ordenesCreadas.length))} orden(es) creada(s) y despachada(s),
        ${U.escaparHtml(String(resultado.filas_procesadas))} fila(s) procesada(s).
      </div>`;
  }

  // Señal ligera (sin backend, sin recargar la app) para que Inventario y
  // Reportes -páginas independientes en esta arquitectura multi-página, no
  // un SPA con todos los módulos montados a la vez- se refresquen solos si
  // están abiertos en otra pestaña. Mismo mecanismo que ya usa compras.js
  // (F9B): reutiliza el evento "storage" y las funciones de carga que ya
  // existen en cada page-script; no agrega endpoints ni lógica de negocio
  // nueva. Único cambio real: el módulo que se anuncia aquí es "ventas".
  function notificarDatosActualizados() {
    try {
      localStorage.setItem(
        "erp_datos_actualizados",
        JSON.stringify({ modulo: "ventas", ts: Date.now() })
      );
    } catch (err) {
      /* localStorage no disponible (modo privado, etc.): no es crítico. */
    }
  }

  async function confirmarImportarVentas() {
    if (!previewImportarVentasActual || previewImportarVentasActual.filas_con_error > 0) return;

    const inventarioSalidaId = Number(selectInventarioImportarVentas.value) || null;
    const archivo = inputArchivoImportarVentas.files && inputArchivoImportarVentas.files[0];
    if (!inventarioSalidaId || !archivo) {
      mostrarErrorModal(errorImportarVentas, "Selecciona nuevamente el almacén y el archivo antes de importar.");
      return;
    }

    const confirmado = window.UI
      ? await window.UI.confirmar({
          titulo: "Importar ventas",
          mensaje: `¿Confirmas la importación de "${archivo.name}"? Se crearán ${previewImportarVentasActual.ordenes_a_crear} orden(es) de venta a partir de las filas válidas, y cada una se despachará de inmediato (con salida real de inventario/Kardex). Esta acción no se puede deshacer.`,
          textoAceptar: "Importar",
          variante: "primary",
        })
      : true;
    if (!confirmado) return;

    const formData = new FormData();
    formData.append("archivo", archivo);

    ocultarErrorModal(errorImportarVentas);
    if (window.UI) window.UI.mostrarCargando();
    btnConfirmarImportarVentas.disabled = true;
    try {
      const resultado = await apiPostArchivoVentas(
        `/api/ventas/importar/confirmar?inventario_salida_id=${inventarioSalidaId}`,
        formData
      );
      pintarResultadoConfirmarImportarVentas(resultado);
      if (window.UI) {
        window.UI.toast(
          `Importación confirmada: ${resultado.ordenes_creadas.length} orden(es) creada(s) y despachada(s).`,
          "success"
        );
      }

      // Al finalizar: cerrar modal, refrescar Ventas (esta página) y
      // avisar a Inventario/Reportes -sin recargar toda la aplicación.
      if (modalImportarVentas) modalImportarVentas.hide();
      await cargarOrdenes();
      notificarDatosActualizados();
    } catch (err) {
      mostrarErrorModal(errorImportarVentas, err.message || "No se pudo confirmar la importación.");
      if (window.UI) window.UI.toast(err.message || "No se pudo confirmar la importación.", "error");
      btnConfirmarImportarVentas.disabled = false;
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    selectEstado.addEventListener("change", cargarOrdenes);
    inputBuscarOrdenes.addEventListener(
      "input",
      U.debounce(() => {
        paginadorOrdenes.reiniciar();
        pintarOrdenes();
      }, 200)
    );
    selectTamanioPaginaOrdenes.addEventListener("change", () => {
      paginadorOrdenes.reiniciar();
      pintarOrdenes();
    });

    btnNuevaOrden.addEventListener("click", abrirModalNuevaOrden);
    btnAgregarItem.addEventListener("click", agregarFilaItem);
    formNuevaOrden.addEventListener("submit", guardarNuevaOrden);

    btnImportarVentas.addEventListener("click", abrirModalImportarVentas);
    btnPrevisualizarImportarVentas.addEventListener("click", previsualizarImportarVentas);
    btnConfirmarImportarVentas.addEventListener("click", confirmarImportarVentas);

    btnConfirmarOrden.addEventListener("click", () => ejecutarTransicion("confirmar"));
    btnDespacharOrden.addEventListener("click", () => ejecutarTransicion("despachar"));
    btnCancelarOrden.addEventListener("click", () => ejecutarTransicion("cancelar"));

    (async () => {
      if (window.UI) window.UI.mostrarCargando();
      try {
        await Promise.all([cargarClientesCache(), cargarProductosCache()]);
      } catch (err) {
        mostrarError(err.message || "No se pudieron cargar clientes/productos.");
        if (window.UI) window.UI.toast(err.message || "No se pudieron cargar clientes/productos.", "error");
      } finally {
        if (window.UI) window.UI.ocultarCargando();
      }
      await cargarOrdenes();
    })();
  }

  iniciar();

  // FASE 10A — Importar Ventas (frontend de m10_ventas): al confirmar una
  // importación, este mismo archivo escribe la señal "erp_datos_actualizados"
  // (modulo: "ventas") en localStorage para que Inventario y Reportes, si
  // están abiertos en otra pestaña, se refresquen solos. Aquí también se
  // escucha esa misma señal cuando la origina Compras, por si el usuario
  // tiene esta pantalla de Ventas abierta y en algún momento se agrega algo
  // que dependa de compras (hoy no aplica, pero mantiene el mismo patrón
  // simétrico que ya usan inventario.js/reportes.js).
  window.addEventListener("storage", (ev) => {
    if (ev.key !== "erp_datos_actualizados" || !ev.newValue) return;
    try {
      const datos = JSON.parse(ev.newValue);
      if (datos && datos.modulo === "ventas") cargarOrdenes();
    } catch (err) {
      /* señal mal formada: se ignora, no es crítico. */
    }
  });
})();
