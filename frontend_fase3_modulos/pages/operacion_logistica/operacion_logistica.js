/**
 * pages/operacion_logistica/operacion_logistica.js — Page-script del
 * módulo m07_operacion_logistica (app/modules/m07_operacion_logistica),
 * el módulo más grande del Backend.
 *
 * Endpoints (contrato real: router.py + schemas.py), todos con Bearer:
 *   GET  /api/operacion-logistica?estado=str|null        -> list[OperacionLogisticaOut]
 *   GET  /api/operacion-logistica/{id}                   -> OperacionLogisticaOut
 *   POST /api/operacion-logistica       body RecepcionCrear         -> OperacionLogisticaOut (201)
 *   POST /api/operacion-logistica/{id}/inspeccion  body InspeccionActualizar -> OperacionLogisticaOut
 *   POST /api/operacion-logistica/{id}/ubicacion   body UbicacionActualizar  -> OperacionLogisticaOut
 *   POST /api/operacion-logistica/{id}/disponible  body DisponibleActualizar -> OperacionLogisticaOut
 *   POST /api/operacion-logistica/{id}/reservar    body ReservaCrear         -> OperacionLogisticaOut
 *   POST /api/operacion-logistica/{id}/picking     body PickingActualizar    -> OperacionLogisticaOut
 *   POST /api/operacion-logistica/{id}/packing     body PackingActualizar    -> OperacionLogisticaOut
 *   POST /api/operacion-logistica/{id}/carga       body CargaActualizar      -> OperacionLogisticaOut
 *   POST /api/operacion-logistica/{id}/despacho    body DespachoActualizar   -> OperacionLogisticaOut
 *   POST /api/operacion-logistica/{id}/entrega     body EntregaActualizar    -> OperacionLogisticaOut
 *   POST /api/operacion-logistica/{id}/cerrar      body CierreActualizar     -> OperacionLogisticaOut
 *
 * Máquina de estados LINEAL (sin saltos, sin retrocesos — validators.py):
 *   RECEPCION -> INSPECCION -> UBICACION -> DISPONIBLE -> RESERVADO ->
 *   PICKING -> PACKING -> CARGA -> DESPACHO -> ENTREGADO -> CERRADO
 * A diferencia de Compras/Comercio Exterior (donde un estado puede tener
 * más de una transición válida), aquí cada estado tiene como máximo UNA
 * transición siguiente, así que el detalle no muestra varios botones de
 * acción: muestra un único formulario "Siguiente paso" cuyos campos
 * cambian según operacion.estado (tabla PASOS más abajo), reflejando
 * exactamente el schema *Actualizar / *Crear del endpoint que corresponde
 * a esa transición. CERRADO es estado final: no hay formulario siguiente.
 *
 * RecepcionCrear: producto_id, proveedor_id, orden_compra_id? (si se
 * referencia una OC ya RECIBIDA, esta operación NO vuelve a ingresar
 * stock, solo registra el seguimiento físico; si se omite, SÍ ingresa
 * stock directamente), codigo_lote, cantidad>0, costo_unitario>=0,
 * fecha_vencimiento?, observaciones?.
 *
 * Depende de m02_productos (GET /api/productos), m05_proveedores
 * (GET /api/proveedores) y m04_compras (GET /api/compras?estado=RECIBIDA)
 * para los selectores de la Nueva recepción, y de m10_ventas
 * (GET /api/ventas?estado=CONFIRMADA) para el selector de orden de venta
 * del paso "Reservar" (filtrado en el cliente a las órdenes que incluyen
 * el producto de la operación, tal como exige
 * validators.validar_orden_venta_para_reserva en el Backend).
 *
 * FASE F6 — Completa el Frontend de este módulo (m07) sin tocar F0-F5:
 * - GET /api/operacion-logistica solo admite el filtro `estado` en el
 *   Backend (router.py): no expone búsqueda por texto ni paginación
 *   (page/limit). Igual que en F5 (Comercio Exterior) y en F1-F4, la
 *   búsqueda y la paginación de esta pantalla se resuelven en el
 *   cliente sobre la lista ya cargada; no se inventa ningún parámetro
 *   de query nuevo contra el Backend.
 * - Se integran UI.toast/UI.mostrarCargando/UI.ocultarCargando (ya
 *   presentes en ui-components.js desde F0) en las cuatro operaciones
 *   de red de esta página (listar, crear recepción, ver detalle,
 *   registrar paso siguiente), y UI.confirmar() antes de ejecutar
 *   cualquier paso siguiente, ya que cada uno es una transición de
 *   estado que el Backend no permite deshacer (máquina lineal sin
 *   retrocesos, validators.py). No se agregan endpoints, campos ni
 *   comportamientos que el Backend no soporte.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  // Config de cada paso siguiente según el estado ACTUAL de la operación.
  // accion = segmento final del endpoint POST /api/operacion-logistica/{id}/<accion>.
  const PASOS = {
    RECEPCION: {
      accion: "inspeccion",
      titulo: "Registrar inspección",
      campos: [
        { id: "conforme", tipo: "select-bool", label: "¿Conforme?", ancho: "col-6" },
        { id: "observaciones", tipo: "textarea", label: "Observaciones", opcional: true, ancho: "col-12" },
      ],
    },
    INSPECCION: {
      accion: "ubicacion",
      titulo: "Registrar ubicación",
      campos: [
        { id: "rack", tipo: "text", label: "Rack", ancho: "col-4" },
        { id: "pasillo", tipo: "text", label: "Pasillo", ancho: "col-4" },
        { id: "ubicacion_fisica", tipo: "text", label: "Ubicación física", ancho: "col-4" },
        { id: "observaciones", tipo: "textarea", label: "Observaciones", opcional: true, ancho: "col-12" },
      ],
    },
    UBICACION: {
      accion: "disponible",
      titulo: "Marcar disponible",
      campos: [{ id: "observaciones", tipo: "textarea", label: "Observaciones", opcional: true, ancho: "col-12" }],
    },
    DISPONIBLE: {
      accion: "reservar",
      titulo: "Reservar contra orden de venta",
      campos: [
        { id: "orden_venta_id", tipo: "select-orden-venta", label: "Orden de venta (CONFIRMADA)", ancho: "col-12" },
        { id: "observaciones", tipo: "textarea", label: "Observaciones", opcional: true, ancho: "col-12" },
      ],
    },
    RESERVADO: {
      accion: "picking",
      titulo: "Registrar picking",
      campos: [
        {
          id: "observaciones",
          tipo: "textarea",
          label: "Observaciones (el lote se asigna automáticamente por FEFO/FIFO)",
          opcional: true,
          ancho: "col-12",
        },
      ],
    },
    PICKING: {
      accion: "packing",
      titulo: "Registrar packing",
      campos: [
        { id: "peso", tipo: "number", label: "Peso (kg)", ancho: "col-4" },
        { id: "cajas", tipo: "number-int", label: "Cajas", ancho: "col-4" },
        { id: "pallets", tipo: "number-int", label: "Pallets", ancho: "col-4" },
        { id: "observaciones", tipo: "textarea", label: "Observaciones", opcional: true, ancho: "col-12" },
      ],
    },
    PACKING: {
      accion: "carga",
      titulo: "Registrar carga",
      campos: [
        { id: "vehiculo", tipo: "text", label: "Vehículo (placa)", ancho: "col-4" },
        { id: "conductor", tipo: "text", label: "Conductor", ancho: "col-8" },
        { id: "fecha_carga", tipo: "datetime-local", label: "Fecha de carga (opcional)", opcional: true, ancho: "col-6" },
        { id: "observaciones", tipo: "textarea", label: "Observaciones", opcional: true, ancho: "col-12" },
      ],
    },
    CARGA: {
      accion: "despacho",
      titulo: "Registrar despacho",
      campos: [
        {
          id: "observaciones",
          tipo: "textarea",
          label: "Observaciones (requiere que la orden de venta ya esté DESPACHADA)",
          opcional: true,
          ancho: "col-12",
        },
      ],
    },
    DESPACHO: {
      accion: "entrega",
      titulo: "Registrar entrega",
      campos: [{ id: "observaciones", tipo: "textarea", label: "Observaciones", opcional: true, ancho: "col-12" }],
    },
    ENTREGADO: {
      accion: "cerrar",
      titulo: "Cerrar operación",
      campos: [{ id: "observaciones", tipo: "textarea", label: "Observaciones", opcional: true, ancho: "col-12" }],
    },
    CERRADO: null,
  };

  const elError = document.getElementById("estadoError");
  const selectEstado = document.getElementById("selectEstado");
  const inputBuscarOperaciones = document.getElementById("inputBuscarOperaciones");
  const btnNuevaRecepcion = document.getElementById("btnNuevaRecepcion");
  const tbody = document.getElementById("tbodyOperaciones");
  const selectTamanioPaginaOperaciones = document.getElementById("selectTamanioPaginaOperaciones");

  const modalNuevaEl = document.getElementById("modalNuevaRecepcion");
  // Protección mínima: si el CDN de Bootstrap no cargó, bootstrap no existe
  // y "new bootstrap.Modal(...)" rompería toda la página. En ese caso el
  // modal queda en null y las funciones que lo usan avisan el error en vez
  // de lanzar un TypeError.
  const bootstrapDisponible = typeof bootstrap !== "undefined" && bootstrap.Modal;
  const modalNueva = bootstrapDisponible ? new bootstrap.Modal(modalNuevaEl) : null;
  const formNueva = document.getElementById("formNuevaRecepcion");
  const modalNuevaError = document.getElementById("modalNuevaRecepcionError");
  const recProducto = document.getElementById("recProducto");
  const recProveedor = document.getElementById("recProveedor");
  const recOrdenCompra = document.getElementById("recOrdenCompra");
  const recCodigoLote = document.getElementById("recCodigoLote");
  const recCantidad = document.getElementById("recCantidad");
  const recCostoUnitario = document.getElementById("recCostoUnitario");
  const recFechaVencimiento = document.getElementById("recFechaVencimiento");
  const recObservaciones = document.getElementById("recObservaciones");

  const modalDetalleEl = document.getElementById("modalDetalleOperacion");
  const modalDetalle = bootstrapDisponible ? new bootstrap.Modal(modalDetalleEl) : null;
  const detalleTitulo = document.getElementById("detalleOperacionTitulo");
  const modalDetalleError = document.getElementById("modalDetalleOperacionError");
  const detalleInfo = document.getElementById("detalleOperacionInfo");
  const cardPasoSiguiente = document.getElementById("cardPasoSiguiente");
  const pasoSiguienteTitulo = document.getElementById("pasoSiguienteTitulo");
  const formPasoSiguiente = document.getElementById("formPasoSiguiente");
  const pasoSiguienteError = document.getElementById("pasoSiguienteError");
  const pasoSiguienteCampos = document.getElementById("pasoSiguienteCampos");
  const tbodyHistorial = document.getElementById("tbodyHistorial");

  let productosCache = [];
  let proveedoresCache = [];
  let operacionesCache = [];
  let operacionDetalleActual = null;

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
    const colores = {
      RECEPCION: "secondary",
      INSPECCION: "warning",
      UBICACION: "info",
      DISPONIBLE: "primary",
      RESERVADO: "info",
      PICKING: "warning",
      PACKING: "warning",
      CARGA: "info",
      DESPACHO: "primary",
      ENTREGADO: "success",
      CERRADO: "dark",
    };
    return colores[estado] || "secondary";
  }

  function nombreProducto(productoId) {
    const p = productosCache.find((x) => x.id === productoId);
    return p ? `${p.codigo} — ${p.nombre}` : `#${productoId}`;
  }

  function nombreProveedor(proveedorId) {
    const p = proveedoresCache.find((x) => x.id === proveedorId);
    return p ? p.razon_social : `#${proveedorId}`;
  }

  // ---------- Paginador genérico reutilizable (mismo criterio que
  // inventario.js de F2, compras.js de F3, ventas.js de F4 y
  // comercio_exterior.js de F5: el Backend no expone page/limit en
  // /api/operacion-logistica, así que la paginación de la tabla se
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

  const paginadorOperaciones = crearPaginador(
    selectTamanioPaginaOperaciones,
    document.getElementById("paginacionResumenOperaciones"),
    document.getElementById("paginacionControlesOperaciones"),
    () => pintarOperaciones()
  );

  // ---------- Búsqueda (cliente, ya que /api/operacion-logistica solo
  // filtra por "estado" en el Backend) ----------
  function filtrarOperaciones(lista) {
    const q = inputBuscarOperaciones.value.trim().toLowerCase();
    if (!q) return lista;
    return lista.filter((o) => {
      const numero = `#${o.id}`.toLowerCase();
      const producto = nombreProducto(o.producto_id).toLowerCase();
      const proveedor = nombreProveedor(o.proveedor_id).toLowerCase();
      const lote = (o.codigo_lote || "").toLowerCase();
      const vehiculo = (o.vehiculo || "").toLowerCase();
      const observaciones = (o.observaciones || "").toLowerCase();
      return (
        numero.includes(q) ||
        producto.includes(q) ||
        proveedor.includes(q) ||
        lote.includes(q) ||
        vehiculo.includes(q) ||
        observaciones.includes(q)
      );
    });
  }

  // ---------- Listado ----------
  function pintarOperaciones() {
    const filtradas = filtrarOperaciones(operacionesCache);
    const info = paginadorOperaciones.calcular(filtradas);

    tbody.innerHTML = info.pagina.length
      ? info.pagina
          .map(
            (o) => `
        <tr>
          <td>#${o.id}</td>
          <td>${U.escaparHtml(nombreProducto(o.producto_id))}</td>
          <td>${U.escaparHtml(nombreProveedor(o.proveedor_id))}</td>
          <td>${U.escaparHtml(o.codigo_lote)}</td>
          <td class="text-end">${U.formatearNumero(o.cantidad, 3)}</td>
          <td><span class="badge text-bg-${colorEstado(o.estado)}">${U.escaparHtml(o.estado)}</span></td>
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
          operacionesCache.length === 0
            ? "No hay operaciones logísticas registradas."
            : "Ninguna operación coincide con la búsqueda/filtro."
        );

    tbody.querySelectorAll(".btn-ver-detalle").forEach((btn) => {
      btn.addEventListener("click", () => abrirModalDetalle(Number(btn.dataset.id)));
    });
  }

  async function cargarOperaciones() {
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      const query = selectEstado.value ? `?estado=${encodeURIComponent(selectEstado.value)}` : "";
      operacionesCache = await apiGet(`/api/operacion-logistica${query}`);
      paginadorOperaciones.reiniciar();
      pintarOperaciones();
    } catch (err) {
      mostrarError(err.message || "Ocurrió un error al cargar las operaciones logísticas.");
      if (window.UI) window.UI.toast(err.message || "Ocurrió un error al cargar las operaciones logísticas.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Caches de productos, proveedores y órdenes de compra ----------
  async function cargarProductosCache() {
    productosCache = await apiGet("/api/productos?solo_activos=true");
    recProducto.innerHTML =
      '<option value="">Seleccionar…</option>' +
      productosCache.map((p) => `<option value="${p.id}">${U.escaparHtml(p.codigo)} — ${U.escaparHtml(p.nombre)}</option>`).join("");
  }

  async function cargarProveedoresCache() {
    proveedoresCache = await apiGet("/api/proveedores?solo_activos=false");
    recProveedor.innerHTML =
      '<option value="">Seleccionar…</option>' +
      proveedoresCache
        .filter((p) => p.activo)
        .map((p) => `<option value="${p.id}">${U.escaparHtml(p.ruc)} — ${U.escaparHtml(p.razon_social)}</option>`)
        .join("");
  }

  async function cargarOrdenesCompraRecibidasCache() {
    const ordenes = await apiGet("/api/compras?estado=RECIBIDA");
    recOrdenCompra.innerHTML =
      '<option value="">Ninguna (recepción directa)</option>' +
      ordenes.map((oc) => `<option value="${oc.id}">#${oc.id} — ${U.escaparHtml(nombreProveedor(oc.proveedor_id))}</option>`).join("");
  }

  // ---------- Modal Nueva recepción ----------
  function limpiarFormularioNueva() {
    formNueva.reset();
    ocultarErrorModal(modalNuevaError);
  }

  function abrirModalNueva() {
    if (!modalNueva) {
      mostrarError("No se pudo abrir la ventana de nueva recepción: Bootstrap no está disponible.");
      if (window.UI) window.UI.toast("No se pudo abrir la ventana de nueva recepción: Bootstrap no está disponible.", "error");
      return;
    }
    limpiarFormularioNueva();
    modalNueva.show();
  }

  async function guardarNuevaRecepcion(ev) {
    ev.preventDefault();
    ocultarErrorModal(modalNuevaError);

    if (!recProducto.value || !recProveedor.value) {
      mostrarErrorModal(modalNuevaError, "Selecciona producto y proveedor.");
      return;
    }

    const datos = {
      producto_id: Number(recProducto.value),
      proveedor_id: Number(recProveedor.value),
      orden_compra_id: recOrdenCompra.value ? Number(recOrdenCompra.value) : null,
      codigo_lote: recCodigoLote.value,
      cantidad: Number(recCantidad.value),
      costo_unitario: Number(recCostoUnitario.value),
      fecha_vencimiento: recFechaVencimiento.value ? new Date(recFechaVencimiento.value).toISOString() : null,
      observaciones: recObservaciones.value || null,
    };

    if (window.UI) window.UI.mostrarCargando();
    try {
      const op = await apiPost("/api/operacion-logistica", datos);
      if (modalNueva) modalNueva.hide();
      if (window.UI) window.UI.toast(`Recepción #${op.id} registrada correctamente.`, "success");
      await cargarOperaciones();
    } catch (err) {
      mostrarErrorModal(modalNuevaError, err.message || "No se pudo registrar la recepción.");
      if (window.UI) window.UI.toast(err.message || "No se pudo registrar la recepción.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Modal Detalle: información ----------
  function filaInfo(ancho, etiqueta, valorHtml) {
    return `<div class="${ancho}"><span class="text-muted-erp">${etiqueta}</span><br>${valorHtml}</div>`;
  }

  function pintarDetalleInfo(op) {
    let html = "";
    html += filaInfo("col-4", "Producto", U.escaparHtml(nombreProducto(op.producto_id)));
    html += filaInfo("col-4", "Proveedor", U.escaparHtml(nombreProveedor(op.proveedor_id)));
    html += filaInfo("col-4", "Estado", `<span class="badge text-bg-${colorEstado(op.estado)}">${U.escaparHtml(op.estado)}</span>`);
    html += filaInfo("col-4", "Lote", U.escaparHtml(op.codigo_lote));
    html += filaInfo("col-4", "Cantidad", U.formatearNumero(op.cantidad, 3));
    html += filaInfo("col-4", "Costo unitario", U.formatearNumero(op.costo_unitario, 4));
    if (op.orden_compra_id) html += filaInfo("col-4", "Orden de compra", `#${op.orden_compra_id}`);
    if (op.conforme !== null && op.conforme !== undefined) {
      html += filaInfo("col-4", "Inspección conforme", op.conforme ? "Sí" : "No");
    }
    if (op.ubicacion_fisica) {
      html += filaInfo("col-4", "Ubicación", `${U.escaparHtml(op.rack || "—")} / ${U.escaparHtml(op.pasillo || "—")} / ${U.escaparHtml(op.ubicacion_fisica)}`);
    }
    if (op.orden_venta_id) html += filaInfo("col-4", "Orden de venta", `#${op.orden_venta_id}`);
    if (op.cantidad_picking !== null && op.cantidad_picking !== undefined) {
      html += filaInfo("col-4", "Picking", `${U.formatearNumero(op.cantidad_picking, 3)} (${U.escaparHtml(op.metodo_consumo || "—")})`);
    }
    if (op.peso !== null && op.peso !== undefined) {
      html += filaInfo("col-4", "Packing", `${U.formatearNumero(op.peso, 2)} kg — ${op.cajas} caja(s) — ${op.pallets} pallet(s)`);
    }
    if (op.vehiculo) html += filaInfo("col-4", "Transporte", `${U.escaparHtml(op.vehiculo)} — ${U.escaparHtml(op.conductor || "—")}`);

    html += filaInfo("col-3", "Creada", U.formatearFechaHora(op.creado_en));
    html += filaInfo("col-3", "Recepción", U.formatearFechaHora(op.recepcion_en));
    html += filaInfo("col-3", "Inspección", U.formatearFechaHora(op.inspeccion_en));
    html += filaInfo("col-3", "Ubicación", U.formatearFechaHora(op.ubicacion_en));
    html += filaInfo("col-3", "Disponible", U.formatearFechaHora(op.disponible_en));
    html += filaInfo("col-3", "Reservado", U.formatearFechaHora(op.reservado_en));
    html += filaInfo("col-3", "Picking", U.formatearFechaHora(op.picking_en));
    html += filaInfo("col-3", "Packing", U.formatearFechaHora(op.packing_en));
    html += filaInfo("col-3", "Carga", U.formatearFechaHora(op.carga_en));
    html += filaInfo("col-3", "Despacho", U.formatearFechaHora(op.despacho_en));
    html += filaInfo("col-3", "Entregado", U.formatearFechaHora(op.entregado_en));
    html += filaInfo("col-3", "Cerrado", U.formatearFechaHora(op.cerrado_en));

    detalleInfo.innerHTML = html;
  }

  function pintarHistorial(op) {
    tbodyHistorial.innerHTML = op.historial.length
      ? op.historial
          .map(
            (h) => `
        <tr>
          <td>${U.formatearFechaHora(h.fecha_hora)}</td>
          <td>${U.escaparHtml(h.usuario_username)}</td>
          <td>${h.estado_anterior ? `<span class="badge text-bg-${colorEstado(h.estado_anterior)}">${U.escaparHtml(h.estado_anterior)}</span>` : "—"}</td>
          <td><span class="badge text-bg-${colorEstado(h.estado_nuevo)}">${U.escaparHtml(h.estado_nuevo)}</span></td>
          <td>${U.escaparHtml(h.observaciones || "—")}</td>
        </tr>`
          )
          .join("")
      : filaVacia(5, "Sin movimientos registrados.");
  }

  // ---------- Modal Detalle: formulario dinámico del siguiente paso ----------
  function campoHtml(campo) {
    const requeridoAttr = campo.opcional ? "" : "required";
    if (campo.tipo === "textarea") {
      return `<div class="${campo.ancho}"><label class="form-label-erp" for="paso_${campo.id}">${campo.label}</label>
        <textarea id="paso_${campo.id}" class="form-control form-control-sm" rows="2" maxlength="500" ${requeridoAttr}></textarea></div>`;
    }
    if (campo.tipo === "select-bool") {
      return `<div class="${campo.ancho}"><label class="form-label-erp" for="paso_${campo.id}">${campo.label}</label>
        <select id="paso_${campo.id}" class="form-select form-select-sm" ${requeridoAttr}>
          <option value="">Seleccionar…</option>
          <option value="true">Sí</option>
          <option value="false">No</option>
        </select></div>`;
    }
    if (campo.tipo === "select-orden-venta") {
      return `<div class="${campo.ancho}"><label class="form-label-erp" for="paso_${campo.id}">${campo.label}</label>
        <select id="paso_${campo.id}" class="form-select form-select-sm" ${requeridoAttr}>
          <option value="">Cargando…</option>
        </select></div>`;
    }
    if (campo.tipo === "number") {
      return `<div class="${campo.ancho}"><label class="form-label-erp" for="paso_${campo.id}">${campo.label}</label>
        <input type="number" id="paso_${campo.id}" class="form-control form-control-sm" min="0" step="0.001" ${requeridoAttr} /></div>`;
    }
    if (campo.tipo === "number-int") {
      return `<div class="${campo.ancho}"><label class="form-label-erp" for="paso_${campo.id}">${campo.label}</label>
        <input type="number" id="paso_${campo.id}" class="form-control form-control-sm" min="1" step="1" ${requeridoAttr} /></div>`;
    }
    if (campo.tipo === "datetime-local") {
      return `<div class="${campo.ancho}"><label class="form-label-erp" for="paso_${campo.id}">${campo.label}</label>
        <input type="datetime-local" id="paso_${campo.id}" class="form-control form-control-sm" ${requeridoAttr} /></div>`;
    }
    // 'text' por defecto
    return `<div class="${campo.ancho}"><label class="form-label-erp" for="paso_${campo.id}">${campo.label}</label>
      <input type="text" id="paso_${campo.id}" class="form-control form-control-sm" ${requeridoAttr} /></div>`;
  }

  async function poblarSelectOrdenVenta(productoId) {
    const select = document.getElementById("paso_orden_venta_id");
    if (!select) return;
    try {
      const ventas = await apiGet("/api/ventas?estado=CONFIRMADA");
      const candidatas = ventas.filter((v) => v.items.some((it) => it.producto_id === productoId));
      select.innerHTML = candidatas.length
        ? '<option value="">Seleccionar…</option>' +
          candidatas
            .map((v) => `<option value="${v.id}">#${v.id} — ${U.escaparHtml(v.cliente_razon_social)}</option>`)
            .join("")
        : '<option value="">No hay órdenes de venta CONFIRMADA con este producto</option>';
    } catch (err) {
      select.innerHTML = '<option value="">No se pudieron cargar las órdenes de venta</option>';
    }
  }

  function renderPasoSiguiente(op) {
    const paso = PASOS[op.estado];
    ocultarErrorModal(pasoSiguienteError);

    if (!paso) {
      cardPasoSiguiente.style.display = "none";
      return;
    }
    cardPasoSiguiente.style.display = "";
    pasoSiguienteTitulo.textContent = paso.titulo;
    pasoSiguienteCampos.innerHTML = paso.campos.map(campoHtml).join("");
    formPasoSiguiente.dataset.accion = paso.accion;

    const necesitaOrdenVenta = paso.campos.some((c) => c.tipo === "select-orden-venta");
    if (necesitaOrdenVenta) poblarSelectOrdenVenta(op.producto_id);
  }

  function leerValoresPaso() {
    const accion = formPasoSiguiente.dataset.accion;
    const paso = Object.values(PASOS).find((p) => p && p.accion === accion);
    const datos = {};
    for (const campo of paso.campos) {
      const el = document.getElementById(`paso_${campo.id}`);
      if (!el) continue;
      const valorCrudo = el.value;
      if (valorCrudo === "") {
        if (!campo.opcional) throw new Error(`El campo "${campo.label}" es obligatorio.`);
        datos[campo.id] = null;
        continue;
      }
      if (campo.tipo === "select-bool") datos[campo.id] = valorCrudo === "true";
      else if (campo.tipo === "number") datos[campo.id] = Number(valorCrudo);
      else if (campo.tipo === "number-int") datos[campo.id] = parseInt(valorCrudo, 10);
      else if (campo.tipo === "select-orden-venta") datos[campo.id] = Number(valorCrudo);
      else if (campo.tipo === "datetime-local") datos[campo.id] = new Date(valorCrudo).toISOString();
      else datos[campo.id] = valorCrudo;
    }
    return { accion, datos };
  }

  async function abrirModalDetalle(id) {
    if (!modalDetalle) {
      mostrarError("No se pudo abrir el detalle de la operación: Bootstrap no está disponible.");
      if (window.UI) window.UI.toast("No se pudo abrir el detalle de la operación: Bootstrap no está disponible.", "error");
      return;
    }
    operacionDetalleActual = null;
    ocultarErrorModal(modalDetalleError);
    detalleTitulo.textContent = `Operación logística #${id}`;
    detalleInfo.innerHTML = "";
    tbodyHistorial.innerHTML = filaVacia(5, "Cargando…");
    cardPasoSiguiente.style.display = "none";
    modalDetalle.show();

    if (window.UI) window.UI.mostrarCargando();
    try {
      const op = await apiGet(`/api/operacion-logistica/${id}`);
      operacionDetalleActual = op;
      pintarDetalleInfo(op);
      pintarHistorial(op);
      renderPasoSiguiente(op);
    } catch (err) {
      mostrarErrorModal(modalDetalleError, err.message || "No se pudo cargar la operación logística.");
      if (window.UI) window.UI.toast(err.message || "No se pudo cargar la operación logística.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  async function ejecutarPasoSiguiente(ev) {
    ev.preventDefault();
    if (!operacionDetalleActual) return;
    ocultarErrorModal(pasoSiguienteError);

    let accion, datos;
    try {
      ({ accion, datos } = leerValoresPaso());
    } catch (err) {
      mostrarErrorModal(pasoSiguienteError, err.message);
      return;
    }

    const paso = PASOS[operacionDetalleActual.estado];
    const id = operacionDetalleActual.id;
    const confirmado = window.UI
      ? await window.UI.confirmar({
          titulo: paso.titulo,
          mensaje: `¿Deseas registrar "${paso.titulo.toLowerCase()}" para la operación logística #${id}? Esta acción avanza su estado y, al ser una máquina de estados lineal, no se puede deshacer desde aquí.`,
          textoAceptar: "Confirmar",
          variante: accion === "cerrar" ? "danger" : "primary",
        })
      : true;
    if (!confirmado) return;

    if (window.UI) window.UI.mostrarCargando();
    try {
      const op = await apiPost(`/api/operacion-logistica/${id}/${accion}`, datos);
      operacionDetalleActual = op;
      pintarDetalleInfo(op);
      pintarHistorial(op);
      renderPasoSiguiente(op);
      if (window.UI) window.UI.toast(`"${paso.titulo}" registrado correctamente en la operación #${id}.`, "success");
      await cargarOperaciones();
    } catch (err) {
      mostrarErrorModal(pasoSiguienteError, err.message || "No se pudo registrar el paso.");
      if (window.UI) window.UI.toast(err.message || "No se pudo registrar el paso.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    selectEstado.addEventListener("change", cargarOperaciones);
    inputBuscarOperaciones.addEventListener(
      "input",
      U.debounce(() => {
        paginadorOperaciones.reiniciar();
        pintarOperaciones();
      }, 200)
    );
    selectTamanioPaginaOperaciones.addEventListener("change", () => {
      paginadorOperaciones.reiniciar();
      pintarOperaciones();
    });

    btnNuevaRecepcion.addEventListener("click", abrirModalNueva);
    formNueva.addEventListener("submit", guardarNuevaRecepcion);
    formPasoSiguiente.addEventListener("submit", ejecutarPasoSiguiente);

    (async () => {
      if (window.UI) window.UI.mostrarCargando();
      try {
        await cargarProductosCache();
        await cargarProveedoresCache();
        await cargarOrdenesCompraRecibidasCache();
      } catch (err) {
        mostrarError(err.message || "No se pudieron cargar productos/proveedores/órdenes de compra.");
        if (window.UI) window.UI.toast(err.message || "No se pudieron cargar productos/proveedores/órdenes de compra.", "error");
      } finally {
        if (window.UI) window.UI.ocultarCargando();
      }
      await cargarOperaciones();
    })();
  }

  iniciar();
})();
