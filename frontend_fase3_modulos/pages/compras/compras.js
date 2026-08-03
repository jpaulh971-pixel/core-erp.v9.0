/**
 * pages/compras/compras.js — Page-script del módulo m04_compras
 * (app/modules/m04_compras).
 *
 * Endpoints (contrato real: router.py + schemas.py), todos con Bearer:
 *   GET  /api/compras?estado=str|null              -> list[OrdenCompraOut]
 *   GET  /api/compras/{id}                         -> OrdenCompraOut
 *   POST /api/compras            body OrdenCompraCrear -> OrdenCompraOut (201)
 *   POST /api/compras/{id}/aprobar                  -> OrdenCompraOut
 *   POST /api/compras/{id}/recibir                  -> OrdenCompraOut
 *   POST /api/compras/{id}/cancelar                 -> OrdenCompraOut
 *
 * OrdenCompraCrear: proveedor_id, moneda (default "USD"), observaciones?,
 * items: [{producto_id, cantidad>0, costo_unitario>=0}] (mínimo 1 ítem).
 * OrdenCompraOut: id, proveedor_id, estado, moneda, observaciones,
 * creado_en, aprobado_en, recibido_en, cancelado_en, items[].
 *
 * No hay endpoint para "editar" una orden ni para cambiar su estado
 * manualmente: solo existen los 3 POST de transición de arriba (aprobar /
 * recibir / cancelar), reflejando exactamente TRANSICIONES_VALIDAS del
 * Backend (app/modules/m04_compras/validators.py):
 *   SOLICITADA -> APROBADA | CANCELADA
 *   APROBADA   -> RECIBIDA | CANCELADA
 *   RECIBIDA / CANCELADA -> (estados finales, sin transición)
 * El botón correspondiente se oculta si el estado actual no tiene esa
 * transición habilitada (validado en el cliente solo para UX; el Backend
 * es quien realmente la exige y devuelve 400 si no corresponde).
 *
 * Dependen de m05_proveedores (GET /api/proveedores) para el selector de
 * proveedor y para mostrar la razón social en el listado (OrdenCompraOut
 * solo trae proveedor_id), y de m02_productos (GET /api/productos) para
 * el selector de producto de cada ítem.
 *
 * FASE F3 — Hallazgos de contrato de esta fase (compras), a tener
 * presentes en fases futuras, en línea con el mismo criterio ya aplicado
 * en F2 para Inventario:
 * - "Editar orden" (del objetivo de fase) NO se implementa como llamada
 *   al Backend: no existe ningún endpoint PUT/PATCH sobre
 *   /api/compras/{id} en router.py. Se documenta la limitación en la
 *   propia pantalla (nota bajo el historial de estados) en vez de
 *   inventar un endpoint que el Backend no expone.
 * - "Confirmar orden" (del objetivo de fase) tampoco es una transición
 *   independiente: el contrato solo define 3 transiciones (aprobar /
 *   recibir / cancelar). No hay un estado "CONFIRMADA" en
 *   TRANSICIONES_VALIDAS, así que no se agrega un botón/endpoint
 *   ficticio para eso.
 * - "Anular orden" (del objetivo de fase) SÍ existe en el Backend, pero
 *   con el nombre "cancelar" (POST /api/compras/{id}/cancelar): se
 *   etiqueta el botón como "Anular orden" en la UI (término de negocio
 *   pedido) sin cambiar la acción real que dispara.
 * - El listado (GET /api/compras) solo admite el filtro `estado` en el
 *   Backend: no hay parámetros de búsqueda por texto ni de paginación
 *   (page/limit) en el contrato. Por eso, igual que en productos.js/
 *   clientes.js/proveedores.js (F1) e inventario.js (F2), la búsqueda por
 *   texto y la paginación de esta fase se resuelven en el cliente sobre
 *   la lista ya cargada (que sí se sigue filtrando por estado contra el
 *   Backend, vía el mismo querystring que ya usaba F2).
 * - El "historial de estados" se arma con los 4 timestamps que ya trae
 *   OrdenCompraOut (creado_en/aprobado_en/recibido_en/cancelado_en): no
 *   se agrega un endpoint de auditoría/historial que el Backend no
 *   expone. F2 mostraba 3 de los 4 (le faltaba cancelado_en); se corrige
 *   aquí como parte del propio historial, no como refactor de F2.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const TRANSICIONES_VALIDAS = {
    SOLICITADA: new Set(["APROBADA", "CANCELADA"]),
    APROBADA: new Set(["RECIBIDA", "CANCELADA"]),
    RECIBIDA: new Set(),
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
  const ordenProveedor = document.getElementById("ordenProveedor");
  const ordenMoneda = document.getElementById("ordenMoneda");
  const ordenObservaciones = document.getElementById("ordenObservaciones");
  const ordenDiasCredito = document.getElementById("ordenDiasCredito");
  const btnAgregarItem = document.getElementById("btnAgregarItem");
  const tbodyItemsOrden = document.getElementById("tbodyItemsOrden");
  const totalOrdenEl = document.getElementById("totalOrden");

  const btnImportarCompras = document.getElementById("btnImportarCompras");
  const modalImportarComprasEl = document.getElementById("modalImportarCompras");
  const modalImportarCompras = bootstrapDisponible ? new bootstrap.Modal(modalImportarComprasEl) : null;
  const errorImportarCompras = document.getElementById("errorImportarCompras");
  const selectInventarioImportarCompras = document.getElementById("selectInventarioImportarCompras");
  const inputArchivoImportarCompras = document.getElementById("inputArchivoImportarCompras");
  const btnPrevisualizarImportarCompras = document.getElementById("btnPrevisualizarImportarCompras");
  const resumenImportarCompras = document.getElementById("resumenImportarCompras");
  const statsImportarCompras = document.getElementById("statsImportarCompras");
  const bloqueErroresImportarCompras = document.getElementById("bloqueErroresImportarCompras");
  const tbodyErroresImportarCompras = document.getElementById("tbodyErroresImportarCompras");
  const resultadoImportarCompras = document.getElementById("resultadoImportarCompras");
  const notaImportarCompras = document.getElementById("notaImportarCompras");
  const btnConfirmarImportarCompras = document.getElementById("btnConfirmarImportarCompras");

  const modalDetalleEl = document.getElementById("modalDetalleOrden");
  const modalDetalle = bootstrapDisponible ? new bootstrap.Modal(modalDetalleEl) : null;
  const detalleOrdenTitulo = document.getElementById("detalleOrdenTitulo");
  const modalDetalleOrdenError = document.getElementById("modalDetalleOrdenError");
  const detalleOrdenInfo = document.getElementById("detalleOrdenInfo");
  const tbodyDetalleItems = document.getElementById("tbodyDetalleItems");
  const historialEstadosOrden = document.getElementById("historialEstadosOrden");
  const btnAprobarOrden = document.getElementById("btnAprobarOrden");
  const btnRecibirOrden = document.getElementById("btnRecibirOrden");
  const btnCancelarOrden = document.getElementById("btnCancelarOrden");

  let proveedoresCache = [];
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
    if (estado === "SOLICITADA") return "warning";
    if (estado === "APROBADA") return "info";
    if (estado === "RECIBIDA") return "success";
    if (estado === "CANCELADA") return "danger";
    return "secondary";
  }

  function nombreProveedor(proveedorId) {
    const p = proveedoresCache.find((x) => x.id === proveedorId);
    return p ? p.razon_social : `#${proveedorId}`;
  }

  function nombreProducto(productoId) {
    const p = productosCache.find((x) => x.id === productoId);
    return p ? `${p.codigo} — ${p.nombre}` : `#${productoId}`;
  }

  function totalOrden(orden) {
    return orden.items.reduce((acc, it) => acc + Number(it.cantidad) * Number(it.costo_unitario), 0);
  }

  // Resume "Presentación / Unidad" de TODA la orden para la columna del
  // listado principal (a diferencia del modal de detalle, que la muestra
  // por ítem). Si todos los ítems comparten la misma combinación, se
  // muestra una sola vez; si hay más de una distinta, se listan todas
  // separadas por coma para no ocultar información al auditar.
  function presentacionUnidadOrden(orden) {
    const combinaciones = orden.items
      .map((it) => [it.presentacion, it.unidad_medida].filter(Boolean).join(" / "))
      .filter(Boolean);
    if (!combinaciones.length) return "—";
    const unicas = [...new Set(combinaciones)];
    return unicas.join(", ");
  }

  // ---------- Paginador genérico reutilizable (mismo criterio que
  // inventario.js de F2: el Backend no expone page/limit en /api/compras,
  // así que la paginación de la tabla se resuelve en el cliente sobre la
  // lista ya cargada) ----------
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

  // ---------- Búsqueda (cliente, ya que /api/compras solo filtra por
  // "estado" en el Backend) ----------
  function filtrarOrdenes(lista) {
    const q = inputBuscarOrdenes.value.trim().toLowerCase();
    if (!q) return lista;
    return lista.filter((o) => {
      const numero = `#${o.id}`.toLowerCase();
      const proveedor = nombreProveedor(o.proveedor_id).toLowerCase();
      const observaciones = (o.observaciones || "").toLowerCase();
      return numero.includes(q) || proveedor.includes(q) || observaciones.includes(q);
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
          <td>${U.escaparHtml(nombreProveedor(o.proveedor_id))}</td>
          <td><span class="badge text-bg-${colorEstado(o.estado)}">${U.escaparHtml(o.estado)}</span></td>
          <td>${U.escaparHtml(o.moneda)}</td>
          <td>${U.escaparHtml(presentacionUnidadOrden(o))}</td>
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
            ? "No hay órdenes de compra registradas."
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
      ordenesCache = await apiGet(`/api/compras${query}`);
      paginadorOrdenes.reiniciar();
      pintarOrdenes();
    } catch (err) {
      mostrarError(err.message || "Ocurrió un error al cargar las órdenes de compra.");
      if (window.UI) window.UI.toast(err.message || "Ocurrió un error al cargar las órdenes de compra.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Caches de proveedores y productos ----------
  async function cargarProveedoresCache() {
    // solo_activos=false: el listado necesita poder mostrar el nombre de
    // proveedores de órdenes antiguas aunque hoy estén inactivos.
    proveedoresCache = await apiGet("/api/proveedores?solo_activos=false");
    ordenProveedor.innerHTML =
      '<option value="">Seleccionar…</option>' +
      proveedoresCache
        .filter((p) => p.activo)
        .map((p) => `<option value="${p.id}">${U.escaparHtml(p.ruc)} — ${U.escaparHtml(p.razon_social)}</option>`)
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
    const costo = Number(fila.querySelector(".item-costo").value) || 0;
    fila.querySelector(".item-subtotal").textContent = U.formatearNumero(cantidad * costo, 2);
    recalcularTotalOrden();
  }

  function recalcularTotalOrden() {
    let total = 0;
    tbodyItemsOrden.querySelectorAll("tr").forEach((fila) => {
      const cantidad = Number(fila.querySelector(".item-cantidad").value) || 0;
      const costo = Number(fila.querySelector(".item-costo").value) || 0;
      total += cantidad * costo;
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
      <td><input type="number" class="form-control form-control-sm item-costo" min="0" step="0.0001" required /></td>
      <td><input type="text" class="form-control form-control-sm item-presentacion" placeholder="Bidón, Cilindro…" maxlength="50" /></td>
      <td><input type="text" class="form-control form-control-sm item-unidad" placeholder="Litros, Kg…" maxlength="30" /></td>
      <td><input type="number" class="form-control form-control-sm item-cantidad-unidad" min="0" step="0.001" /></td>
      <td class="text-end item-subtotal">0.00</td>
      <td class="text-end">
        <button type="button" class="btn btn-sm btn-outline-danger btn-quitar-item"><i class="bi bi-trash"></i></button>
      </td>`;
    tbodyItemsOrden.appendChild(fila);

    fila.querySelector(".item-cantidad").addEventListener("input", () => recalcularSubtotalFila(fila));
    fila.querySelector(".item-costo").addEventListener("input", () => recalcularSubtotalFila(fila));
    fila.querySelector(".btn-quitar-item").addEventListener("click", () => {
      // Al menos un ítem es obligatorio (mínimo 1 exigido por
      // OrdenCompraCrear en el Backend): no se deja quitar la última fila.
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
      const costo = fila.querySelector(".item-costo").value;
      const presentacion = fila.querySelector(".item-presentacion").value.trim();
      const unidadMedida = fila.querySelector(".item-unidad").value.trim();
      const cantidadPorUnidad = fila.querySelector(".item-cantidad-unidad").value;
      if (productoId && cantidad && costo !== "") {
        items.push({
          producto_id: Number(productoId),
          cantidad: Number(cantidad),
          costo_unitario: Number(costo),
          presentacion: presentacion || null,
          unidad_medida: unidadMedida || null,
          cantidad_por_unidad: cantidadPorUnidad !== "" ? Number(cantidadPorUnidad) : null,
        });
      }
    });
    return items;
  }

  function validarFormularioNuevaOrden(items) {
    if (!ordenProveedor.value) {
      mostrarErrorModal(modalNuevaOrdenError, "Selecciona un proveedor.");
      ordenProveedor.focus();
      return false;
    }
    if (!items.length) {
      mostrarErrorModal(modalNuevaOrdenError, "Agrega al menos un ítem con producto, cantidad y costo unitario.");
      return false;
    }
    for (const item of items) {
      if (!(item.cantidad > 0)) {
        mostrarErrorModal(modalNuevaOrdenError, "La cantidad de cada ítem debe ser mayor a cero.");
        return false;
      }
      if (!(item.costo_unitario >= 0)) {
        mostrarErrorModal(modalNuevaOrdenError, "El costo unitario de cada ítem no puede ser negativo.");
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

    const diasCredito = ordenDiasCredito && ordenDiasCredito.value !== "" ? Number(ordenDiasCredito.value) : null;
    const datos = {
      proveedor_id: Number(ordenProveedor.value),
      moneda: ordenMoneda.value,
      observaciones: ordenObservaciones.value || null,
      dias_credito: diasCredito,
      items,
    };

    if (window.UI) window.UI.mostrarCargando();
    try {
      await apiPost("/api/compras", datos);
      if (modalNuevaOrden) modalNuevaOrden.hide();
      if (window.UI) window.UI.toast("Orden de compra creada correctamente.", "success");
      await cargarOrdenes();
    } catch (err) {
      mostrarErrorModal(modalNuevaOrdenError, err.message || "No se pudo crear la orden de compra.");
      if (window.UI) window.UI.toast(err.message || "No se pudo crear la orden de compra.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Modal Detalle: información + historial + cambio de estado ----------
  function pintarDetalleInfo(orden) {
    detalleOrdenInfo.innerHTML = `
      <div class="col-6"><span class="text-muted-erp">Proveedor</span><br>${U.escaparHtml(nombreProveedor(orden.proveedor_id))}</div>
      <div class="col-3"><span class="text-muted-erp">Estado</span><br><span class="badge text-bg-${colorEstado(orden.estado)}">${U.escaparHtml(orden.estado)}</span></div>
      <div class="col-3"><span class="text-muted-erp">Moneda</span><br>${U.escaparHtml(orden.moneda)}</div>
      ${orden.numero_orden_externo ? `<div class="col-4"><span class="text-muted-erp">Pedido / Orden Compra</span><br>${U.escaparHtml(orden.numero_orden_externo)}</div>` : ""}
      ${orden.invoice ? `<div class="col-4"><span class="text-muted-erp">Factura</span><br>${U.escaparHtml(orden.invoice)}</div>` : ""}
      ${orden.dias_credito != null ? `<div class="col-4"><span class="text-muted-erp">Días de crédito</span><br>${U.escaparHtml(String(orden.dias_credito))}</div>` : ""}
      ${orden.fecha_vencimiento_factura ? `<div class="col-4"><span class="text-muted-erp">Vencimiento factura</span><br>${U.formatearFecha ? U.formatearFecha(orden.fecha_vencimiento_factura) : U.escaparHtml(orden.fecha_vencimiento_factura)}</div>` : ""}
      ${orden.observaciones ? `<div class="col-12"><span class="text-muted-erp">Observaciones</span><br>${U.escaparHtml(orden.observaciones)}</div>` : ""}
    `;
  }

  function pintarDetalleItems(orden) {
    tbodyDetalleItems.innerHTML = orden.items.length
      ? orden.items
          .map((it) => {
            const presentacionUnidad = [it.presentacion, it.unidad_medida].filter(Boolean).join(" / ");
            return `
        <tr>
          <td>${U.escaparHtml(nombreProducto(it.producto_id))}${it.concepto ? `<br><small class="text-muted-erp">${U.escaparHtml(it.concepto)}</small>` : ""}</td>
          <td>${presentacionUnidad ? U.escaparHtml(presentacionUnidad) : "—"}${it.cantidad_por_unidad != null ? ` (${U.formatearNumero(it.cantidad_por_unidad, 3)}/u)` : ""}</td>
          <td class="text-end">${U.formatearNumero(it.cantidad, 3)}</td>
          <td class="text-end">${U.formatearMoneda(it.costo_unitario, orden.moneda)}</td>
          <td class="text-end">${U.formatearMoneda(it.cantidad * it.costo_unitario, orden.moneda)}</td>
        </tr>`;
          })
          .join("")
      : filaVacia(5, "Esta orden no tiene ítems.");
  }

  // Historial de estados: se arma en el cliente con los 4 timestamps que
  // ya trae OrdenCompraOut (no hay endpoint de auditoría/historial en el
  // Backend). Solo se listan los hitos que aplican según el estado actual
  // (una orden CANCELADA nunca tendrá recibido_en, por ejemplo).
  function pintarHistorialEstados(orden) {
    const hitos = [
      { etiqueta: "Solicitada (creada)", fecha: orden.creado_en, icono: "bi-plus-circle-fill", color: "text-warning" },
      { etiqueta: "Aprobada", fecha: orden.aprobado_en, icono: "bi-check-circle-fill", color: "text-info" },
      { etiqueta: "Recibida", fecha: orden.recibido_en, icono: "bi-box-seam-fill", color: "text-success" },
      { etiqueta: "Anulada (cancelada)", fecha: orden.cancelado_en, icono: "bi-x-circle-fill", color: "text-danger" },
    ];

    // Si la orden fue cancelada, "Recibida" ya no puede ocurrir: se omite
    // en vez de mostrar un hito "pendiente" que no tiene sentido en ese
    // camino. Si aún no fue cancelada, se omite "Anulada" hasta que ocurra.
    const hitosVisibles = hitos.filter((h) => {
      if (h.etiqueta === "Recibida" && orden.estado === "CANCELADA" && !h.fecha) return false;
      if (h.etiqueta === "Anulada (cancelada)" && orden.estado !== "CANCELADA" && !h.fecha) return false;
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

  function actualizarBotonesTransicion(estado) {
    const permitidas = TRANSICIONES_VALIDAS[estado] || new Set();
    btnAprobarOrden.style.display = permitidas.has("APROBADA") ? "" : "none";
    btnRecibirOrden.style.display = permitidas.has("RECIBIDA") ? "" : "none";
    btnCancelarOrden.style.display = permitidas.has("CANCELADA") ? "" : "none";
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
    detalleOrdenTitulo.textContent = `Orden de compra #${id}`;
    tbodyDetalleItems.innerHTML = filaVacia(5, "Cargando…");
    detalleOrdenInfo.innerHTML = "";
    historialEstadosOrden.innerHTML = "";
    actualizarBotonesTransicion("");
    modalDetalle.show();

    if (window.UI) window.UI.mostrarCargando();
    try {
      const orden = await apiGet(`/api/compras/${id}`);
      ordenDetalleActual = orden;
      pintarDetalleInfo(orden);
      pintarDetalleItems(orden);
      pintarHistorialEstados(orden);
      actualizarBotonesTransicion(orden.estado);
    } catch (err) {
      mostrarErrorModal(modalDetalleOrdenError, err.message || "No se pudo cargar la orden de compra.");
      if (window.UI) window.UI.toast(err.message || "No se pudo cargar la orden de compra.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  const CONFIRMACION_TRANSICION = {
    aprobar: {
      titulo: "Aprobar orden de compra",
      mensaje: (id) => `¿Deseas aprobar la orden de compra #${id}? Esta acción avanza su estado y no se puede deshacer desde aquí.`,
      textoAceptar: "Aprobar",
      variante: "primary",
      mensajeExito: (id) => `Orden de compra #${id} aprobada correctamente.`,
      mensajeError: "No se pudo aprobar la orden de compra.",
    },
    recibir: {
      titulo: "Recibir orden de compra",
      mensaje: (id) => `¿Confirmas la recepción de la orden de compra #${id}? Esta acción marca la orden como recibida y no se puede deshacer desde aquí.`,
      textoAceptar: "Recibir",
      variante: "primary",
      mensajeExito: (id) => `Orden de compra #${id} marcada como recibida.`,
      mensajeError: "No se pudo registrar la recepción de la orden de compra.",
    },
    cancelar: {
      titulo: "Anular orden de compra",
      mensaje: (id) => `¿Deseas anular la orden de compra #${id}? Esta acción es definitiva: la orden quedará en estado CANCELADA y no podrá aprobarse ni recibirse.`,
      textoAceptar: "Anular orden",
      variante: "danger",
      mensajeExito: (id) => `Orden de compra #${id} anulada correctamente.`,
      mensajeError: "No se pudo anular la orden de compra.",
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
      const orden = await apiPost(`/api/compras/${ordenDetalleActualId}/${accion}`);
      ordenDetalleActual = orden;
      pintarDetalleInfo(orden);
      pintarDetalleItems(orden);
      pintarHistorialEstados(orden);
      actualizarBotonesTransicion(orden.estado);
      if (window.UI) window.UI.toast(cfg.mensajeExito(ordenDetalleActualId), "success");
      await cargarOrdenes();
    } catch (err) {
      mostrarErrorModal(modalDetalleOrdenError, err.message || cfg.mensajeError);
      if (window.UI) window.UI.toast(err.message || cfg.mensajeError, "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // =====================================================================
  // FASE 9B — Importar Compras Nacionalizadas (SOLO Frontend).
  //
  // Consume exactamente los 2 endpoints ya existentes en el Backend
  // congelado (m04_compras/router.py + importacion_schemas.py), sin
  // tocar rutas, modelos, schemas ni importacion_service.py:
  //
  //   POST /api/compras/importar/previsualizar?inventario_destino_id=<int>
  //        (multipart, campo "archivo") -> PreviewImportacionComprasOut
  //        {nombre_archivo, inventario_destino_id, total_filas,
  //         filas_validas, filas_con_error, ordenes_a_crear,
  //         filas:[{numero_fila, ..., valida, mensaje_error}]}. No
  //         escribe en BD.
  //   POST /api/compras/importar/confirmar?inventario_destino_id=<int>
  //        (multipart, mismo campo "archivo": el Backend no persiste la
  //        vista previa, así que se reenvía el mismo archivo)
  //        -> ConfirmarImportacionComprasOut {ordenes_creadas[],
  //           filas_procesadas, filas_fallidas[]}.
  //
  // Mismo hallazgo de contrato que documentó m21_importacion_datos.js:
  // window.Api.request fuerza Content-Type: application/json, lo que
  // rompe un upload multipart. Se reutiliza aquí el mismo patrón
  // apiPostArchivo() (no se toca api-client.js, usado por otras 18
  // páginas).
  //
  // "cantidad de productos" (pedido en el objetivo de fase) no es un
  // campo propio de PreviewImportacionComprasOut: se calcula en el
  // cliente contando valores distintos de "producto" entre las filas
  // válidas devueltas, sin inventar un campo nuevo en el Backend.
  // "Advertencias": el contrato solo distingue fila válida/inválida
  // (no hay una categoría de advertencia separada); la tabla de
  // detalle muestra las filas inválidas con su mensaje_error tal cual
  // las devuelve el Backend.
  // =====================================================================

  let inventariosImportarComprasCache = [];
  let previewImportarComprasActual = null;

  async function apiPostArchivoCompras(path, formData) {
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

  async function cargarInventariosImportarCompras() {
    selectInventarioImportarCompras.innerHTML = `<option value="">Cargando almacenes…</option>`;
    try {
      inventariosImportarComprasCache = await apiGet("/api/inventario/inventarios");
      if (!inventariosImportarComprasCache.length) {
        selectInventarioImportarCompras.innerHTML = `<option value="">No hay almacenes registrados</option>`;
        return;
      }
      selectInventarioImportarCompras.innerHTML =
        `<option value="">Seleccionar…</option>` +
        inventariosImportarComprasCache
          .map((inv) => `<option value="${inv.id}">${U.escaparHtml(inv.codigo)} — ${U.escaparHtml(inv.nombre)}</option>`)
          .join("");
    } catch (err) {
      selectInventarioImportarCompras.innerHTML = `<option value="">Error al cargar almacenes</option>`;
      mostrarErrorModal(errorImportarCompras, err.message || "No se pudieron cargar los almacenes.");
      if (window.UI) window.UI.toast(err.message || "No se pudieron cargar los almacenes.", "error");
    }
  }

  function reiniciarModalImportarCompras() {
    ocultarErrorModal(errorImportarCompras);
    inputArchivoImportarCompras.value = "";
    resumenImportarCompras.style.display = "none";
    resultadoImportarCompras.style.display = "none";
    resultadoImportarCompras.innerHTML = "";
    statsImportarCompras.innerHTML = "";
    bloqueErroresImportarCompras.style.display = "none";
    tbodyErroresImportarCompras.innerHTML = "";
    notaImportarCompras.textContent = "";
    btnConfirmarImportarCompras.disabled = true;
    previewImportarComprasActual = null;
  }

  function abrirModalImportarCompras() {
    if (!modalImportarCompras) {
      mostrarError("No se pudo abrir la importación de compras: Bootstrap no está disponible.");
      if (window.UI) window.UI.toast("No se pudo abrir la importación de compras: Bootstrap no está disponible.", "error");
      return;
    }
    reiniciarModalImportarCompras();
    cargarInventariosImportarCompras();
    modalImportarCompras.show();
  }

  function renderStatsImportarCompras(items) {
    statsImportarCompras.innerHTML = items
      .map(
        (it) => `
        <div class="stat-box">
          <div class="stat-valor">${U.escaparHtml(String(it.valor))}</div>
          <div class="stat-etiqueta">${U.escaparHtml(it.etiqueta)}</div>
        </div>`
      )
      .join("");
  }

  function pintarPreviewImportarCompras(preview) {
    previewImportarComprasActual = preview;
    resumenImportarCompras.style.display = "block";
    resultadoImportarCompras.style.display = "none";
    resultadoImportarCompras.innerHTML = "";

    const filas = preview.filas || [];
    const filasInvalidas = filas.filter((f) => !f.valida);
    const productosDistintos = new Set(
      filas.filter((f) => f.valida && f.producto).map((f) => f.producto)
    ).size;

    renderStatsImportarCompras([
      { etiqueta: "Órdenes a crear", valor: preview.ordenes_a_crear },
      { etiqueta: "Productos distintos", valor: productosDistintos },
      { etiqueta: "Total de filas", valor: preview.total_filas },
      { etiqueta: "Filas válidas", valor: preview.filas_validas },
      { etiqueta: "Errores/advertencias", valor: preview.filas_con_error },
    ]);

    if (!filasInvalidas.length) {
      bloqueErroresImportarCompras.style.display = "none";
      tbodyErroresImportarCompras.innerHTML = "";
    } else {
      bloqueErroresImportarCompras.style.display = "block";
      tbodyErroresImportarCompras.innerHTML = filasInvalidas
        .map(
          (f) =>
            `<tr class="table-danger"><td>${U.escaparHtml(String(f.numero_fila))}</td><td>${U.escaparHtml(f.mensaje_error || "Fila inválida.")}</td></tr>`
        )
        .join("");
    }

    // Regla del objetivo de fase: si existen errores, se bloquea Confirmar.
    if (preview.filas_con_error > 0) {
      btnConfirmarImportarCompras.disabled = true;
      notaImportarCompras.textContent = "Corrige los errores del archivo antes de importar.";
    } else if (preview.filas_validas === 0) {
      btnConfirmarImportarCompras.disabled = true;
      notaImportarCompras.textContent = "No hay filas válidas para importar en este archivo.";
    } else {
      btnConfirmarImportarCompras.disabled = false;
      notaImportarCompras.textContent = `Se crearán ${preview.ordenes_a_crear} orden(es) a partir de ${preview.filas_validas} fila(s) válida(s).`;
    }
  }

  async function previsualizarImportarCompras() {
    ocultarErrorModal(errorImportarCompras);
    resumenImportarCompras.style.display = "none";
    btnConfirmarImportarCompras.disabled = true;

    const inventarioDestinoId = Number(selectInventarioImportarCompras.value) || null;
    if (!inventarioDestinoId) {
      mostrarErrorModal(errorImportarCompras, "Selecciona primero un almacén / inventario destino.");
      return;
    }
    const archivo = inputArchivoImportarCompras.files && inputArchivoImportarCompras.files[0];
    if (!archivo) {
      mostrarErrorModal(errorImportarCompras, "Selecciona un archivo Excel (.xlsx o .xls).");
      return;
    }

    const formData = new FormData();
    formData.append("archivo", archivo);

    if (window.UI) window.UI.mostrarCargando();
    btnPrevisualizarImportarCompras.disabled = true;
    try {
      const preview = await apiPostArchivoCompras(
        `/api/compras/importar/previsualizar?inventario_destino_id=${inventarioDestinoId}`,
        formData
      );
      pintarPreviewImportarCompras(preview);
      const mensaje =
        preview.filas_con_error > 0
          ? `Vista previa lista: ${preview.filas_validas} fila(s) válida(s), ${preview.filas_con_error} con error/advertencia.`
          : `Vista previa lista: ${preview.filas_validas} fila(s) válida(s), sin errores.`;
      if (window.UI) window.UI.toast(mensaje, preview.filas_con_error > 0 ? "warning" : "success");
    } catch (err) {
      mostrarErrorModal(errorImportarCompras, err.message || "No se pudo previsualizar el archivo.");
      if (window.UI) window.UI.toast(err.message || "No se pudo previsualizar el archivo.", "error");
    } finally {
      btnPrevisualizarImportarCompras.disabled = false;
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function pintarResultadoConfirmarImportarCompras(resultado) {
    resultadoImportarCompras.style.display = "block";
    const ordenesCreadas = resultado.ordenes_creadas || [];
    const filasFallidas = resultado.filas_fallidas || [];
    resultadoImportarCompras.innerHTML = `
      <div class="alert alert-success mb-2">
        <i class="bi bi-check-circle-fill me-1"></i>Importación confirmada:
        ${U.escaparHtml(String(ordenesCreadas.length))} orden(es) creada(s),
        ${U.escaparHtml(String(resultado.filas_procesadas))} fila(s) procesada(s).
      </div>
      ${
        filasFallidas.length
          ? `<div class="card-header-erp mb-0"><i class="bi bi-exclamation-triangle me-1"></i>Filas que fallaron al confirmar</div>
             <div class="table-responsive-erp mb-2">
               <table class="table-erp"><thead><tr><th style="width:80px;">Fila</th><th>Detalle</th></tr></thead>
               <tbody>${filasFallidas
                 .map((f) => `<tr class="table-danger"><td>${U.escaparHtml(String(f.numero_fila))}</td><td>${U.escaparHtml(f.mensaje_error || "Fila inválida.")}</td></tr>`)
                 .join("")}</tbody></table>
             </div>`
          : ""
      }`;
  }

  // Señal ligera (sin backend, sin recargar la app) para que Inventario y
  // Reportes -páginas independientes en esta arquitectura multi-página, no
  // un SPA con todos los módulos montados a la vez- se refresquen solos si
  // están abiertos en otra pestaña. Cada uno de esos page-scripts escucha
  // este evento "storage" y vuelve a llamar a su propia función de carga ya
  // existente (refrescarTodo()/cargarTodo()); no crea endpoints ni lógica
  // de negocio nueva.
  function notificarDatosActualizados() {
    try {
      localStorage.setItem(
        "erp_datos_actualizados",
        JSON.stringify({ modulo: "compras", ts: Date.now() })
      );
    } catch (err) {
      /* localStorage no disponible (modo privado, etc.): no es crítico. */
    }
  }

  async function confirmarImportarCompras() {
    if (!previewImportarComprasActual || previewImportarComprasActual.filas_con_error > 0) return;

    const inventarioDestinoId = Number(selectInventarioImportarCompras.value) || null;
    const archivo = inputArchivoImportarCompras.files && inputArchivoImportarCompras.files[0];
    if (!inventarioDestinoId || !archivo) {
      mostrarErrorModal(errorImportarCompras, "Selecciona nuevamente el almacén y el archivo antes de importar.");
      return;
    }

    const confirmado = window.UI
      ? await window.UI.confirmar({
          titulo: "Importar compras nacionalizadas",
          mensaje: `¿Confirmas la importación de "${archivo.name}"? Se crearán ${previewImportarComprasActual.ordenes_a_crear} orden(es) de compra a partir de las filas válidas. Esta acción no se puede deshacer.`,
          textoAceptar: "Importar",
          variante: "primary",
        })
      : true;
    if (!confirmado) return;

    const formData = new FormData();
    formData.append("archivo", archivo);

    ocultarErrorModal(errorImportarCompras);
    if (window.UI) window.UI.mostrarCargando();
    btnConfirmarImportarCompras.disabled = true;
    try {
      const resultado = await apiPostArchivoCompras(
        `/api/compras/importar/confirmar?inventario_destino_id=${inventarioDestinoId}`,
        formData
      );
      pintarResultadoConfirmarImportarCompras(resultado);
      if (window.UI) {
        window.UI.toast(
          `Importación confirmada: ${resultado.ordenes_creadas.length} orden(es) creada(s).`,
          "success"
        );
      }

      // Al finalizar: cerrar modal, refrescar Compras (esta página) y
      // avisar a Inventario/Reportes -sin recargar toda la aplicación.
      if (modalImportarCompras) modalImportarCompras.hide();
      await cargarOrdenes();
      notificarDatosActualizados();
    } catch (err) {
      mostrarErrorModal(errorImportarCompras, err.message || "No se pudo confirmar la importación.");
      if (window.UI) window.UI.toast(err.message || "No se pudo confirmar la importación.", "error");
      btnConfirmarImportarCompras.disabled = false;
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

    btnImportarCompras.addEventListener("click", abrirModalImportarCompras);
    btnPrevisualizarImportarCompras.addEventListener("click", previsualizarImportarCompras);
    btnConfirmarImportarCompras.addEventListener("click", confirmarImportarCompras);

    btnAprobarOrden.addEventListener("click", () => ejecutarTransicion("aprobar"));
    btnRecibirOrden.addEventListener("click", () => ejecutarTransicion("recibir"));
    btnCancelarOrden.addEventListener("click", () => ejecutarTransicion("cancelar"));

    (async () => {
      if (window.UI) window.UI.mostrarCargando();
      try {
        await Promise.all([cargarProveedoresCache(), cargarProductosCache()]);
      } catch (err) {
        mostrarError(err.message || "No se pudieron cargar proveedores/productos.");
        if (window.UI) window.UI.toast(err.message || "No se pudieron cargar proveedores/productos.", "error");
      } finally {
        if (window.UI) window.UI.ocultarCargando();
      }
      await cargarOrdenes();
    })();
  }

  iniciar();
})();
