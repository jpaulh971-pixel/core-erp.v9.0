/**
 * pages/comercio_exterior/comercio_exterior.js — Page-script del módulo
 * m06_comercio_exterior (app/modules/m06_comercio_exterior).
 *
 * Endpoints (contrato real: router.py + schemas.py), todos con Bearer:
 *   GET  /api/comercio-exterior/declaraciones?estado=str|null   -> list[DeclaracionOut]
 *   GET  /api/comercio-exterior/declaraciones/{id}              -> DeclaracionOut
 *   POST /api/comercio-exterior/declaraciones     body DeclaracionCrear -> DeclaracionOut (201)
 *   POST /api/comercio-exterior/declaraciones/{id}/confirmar    -> DeclaracionOut
 *   POST /api/comercio-exterior/declaraciones/{id}/embarcar     -> DeclaracionOut
 *   POST /api/comercio-exterior/declaraciones/{id}/cancelar     -> DeclaracionOut
 *
 * DeclaracionCrear: cliente_nombre, pais_destino, incoterm (default "FOB",
 * validado contra INCOTERMS_VALIDOS: EXW/FOB/CIF/CFR/FCA/DAP/DDP), moneda
 * (default "USD"), numero_dua?, observaciones?, items: [{producto_id,
 * cantidad>0, precio_unitario_exportacion>=0}] (mínimo 1 ítem).
 *
 * No hay endpoint para "editar" una declaración ni para cambiar su estado
 * manualmente: solo existen los 3 POST de transición de arriba (confirmar /
 * embarcar / cancelar), reflejando exactamente TRANSICIONES_VALIDAS del
 * Backend (app/modules/m06_comercio_exterior/validators.py):
 *   BORRADOR   -> CONFIRMADA | CANCELADA
 *   CONFIRMADA -> EMBARCADA | CANCELADA
 *   EMBARCADA / CANCELADA -> (estados finales, sin transición)
 * El botón correspondiente se oculta si el estado actual no tiene esa
 * transición habilitada (validado en el cliente solo para UX; el Backend
 * es quien realmente la exige y devuelve 400 si no corresponde). Nota: al
 * "embarcar", el Backend descuenta stock real vía FEFO (m03_inventario)
 * por cada ítem, así que ese POST puede devolver 400 si el stock no
 * alcanza para algún ítem.
 *
 * Depende de m02_productos (GET /api/productos) para el selector de
 * producto de cada ítem y para mostrar código/nombre en el detalle
 * (DeclaracionItemOut solo trae producto_id).
 *
 * FASE F5 — Hallazgos de contrato de esta fase (comercio exterior), a
 * tener presentes en fases futuras, en línea con el mismo criterio ya
 * aplicado en F2 (Inventario), F3 (Compras) y F4 (Ventas):
 * - "Editar declaración" (del objetivo de fase) NO se implementa como
 *   llamada al Backend: no existe ningún endpoint PUT/PATCH sobre
 *   /api/comercio-exterior/declaraciones/{id} en router.py. Se documenta
 *   la limitación en la propia pantalla (nota bajo el historial de
 *   estados), igual que se hizo en F3/F4.
 * - "Aduana" (mencionada en el objetivo de fase) NO existe como campo en
 *   DeclaracionCrear/DeclaracionOut (confirmado contra el comentario de
 *   contrato ya documentado en este archivo desde antes de F5): no se
 *   agrega ningún input ni columna para ese dato porque el Backend no lo
 *   soporta. Documentado también en la nota de la pantalla de detalle.
 * - "País origen" (del objetivo de fase) tampoco existe en el contrato:
 *   DeclaracionOut solo trae "pais_destino". No se inventa un segundo
 *   campo de país origen.
 * - "Documentación asociada" (del objetivo de fase) no tiene soporte en
 *   el Backend: no hay endpoints de subida/consulta de archivos en
 *   router.py para este módulo. No se implementa ningún selector de
 *   archivos ni llamada simulada.
 * - El listado (GET /api/comercio-exterior/declaraciones) solo admite el
 *   filtro `estado` en el Backend: no hay parámetros de búsqueda por
 *   texto ni de paginación (page/limit). La búsqueda por texto y la
 *   paginación de esta fase se resuelven en el cliente sobre la lista ya
 *   cargada (mismo criterio que F1/F2/F3/F4 para sus propios módulos).
 * - El "historial de estados" se arma en el cliente con los 4 timestamps
 *   que ya trae DeclaracionOut (creado_en/confirmado_en/embarcado_en/
 *   cancelado_en); no hay un endpoint de auditoría/historial separado.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const TRANSICIONES_VALIDAS = {
    BORRADOR: new Set(["CONFIRMADA", "CANCELADA"]),
    CONFIRMADA: new Set(["EMBARCADA", "CANCELADA"]),
    EMBARCADA: new Set(),
    CANCELADA: new Set(),
  };

  const elError = document.getElementById("estadoError");
  const selectEstado = document.getElementById("selectEstado");
  const inputBuscarDeclaraciones = document.getElementById("inputBuscarDeclaraciones");
  const btnNuevaDeclaracion = document.getElementById("btnNuevaDeclaracion");
  const tbody = document.getElementById("tbodyDeclaraciones");
  const selectTamanioPaginaDeclaraciones = document.getElementById("selectTamanioPaginaDeclaraciones");

  const modalNuevaEl = document.getElementById("modalNuevaDeclaracion");
  // Protección mínima: si el CDN de Bootstrap no cargó, bootstrap no existe
  // y "new bootstrap.Modal(...)" rompería toda la página. En ese caso el
  // modal queda en null y las funciones que lo usan avisan el error en vez
  // de lanzar un TypeError.
  const bootstrapDisponible = typeof bootstrap !== "undefined" && bootstrap.Modal;
  const modalNueva = bootstrapDisponible ? new bootstrap.Modal(modalNuevaEl) : null;
  const formNueva = document.getElementById("formNuevaDeclaracion");
  const modalNuevaError = document.getElementById("modalNuevaDeclaracionError");
  const declCliente = document.getElementById("declCliente");
  const declNumeroDua = document.getElementById("declNumeroDua");
  const declPaisDestino = document.getElementById("declPaisDestino");
  const declIncoterm = document.getElementById("declIncoterm");
  const declMoneda = document.getElementById("declMoneda");
  const declObservaciones = document.getElementById("declObservaciones");
  const btnAgregarItemDecl = document.getElementById("btnAgregarItemDecl");
  const tbodyItemsDecl = document.getElementById("tbodyItemsDecl");
  const totalDeclEl = document.getElementById("totalDecl");

  const modalDetalleEl = document.getElementById("modalDetalleDeclaracion");
  const modalDetalle = bootstrapDisponible ? new bootstrap.Modal(modalDetalleEl) : null;
  const detalleTitulo = document.getElementById("detalleDeclaracionTitulo");
  const modalDetalleError = document.getElementById("modalDetalleDeclaracionError");
  const detalleInfo = document.getElementById("detalleDeclaracionInfo");
  const tbodyDetalleItems = document.getElementById("tbodyDetalleItemsDecl");
  const historialEstadosDecl = document.getElementById("historialEstadosDecl");
  const btnConfirmar = document.getElementById("btnConfirmarDeclaracion");
  const btnEmbarcar = document.getElementById("btnEmbarcarDeclaracion");
  const btnCancelar = document.getElementById("btnCancelarDeclaracion");

  let productosCache = [];
  let declaracionesCache = [];
  let declaracionDetalleActualId = null;
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
    if (estado === "EMBARCADA") return "success";
    if (estado === "CANCELADA") return "danger";
    return "secondary";
  }

  function nombreProducto(productoId) {
    const p = productosCache.find((x) => x.id === productoId);
    return p ? `${p.codigo} — ${p.nombre}` : `#${productoId}`;
  }

  function totalDeclaracion(decl) {
    return decl.items.reduce(
      (acc, it) => acc + Number(it.cantidad) * Number(it.precio_unitario_exportacion),
      0
    );
  }

  // ---------- Paginador genérico reutilizable (mismo criterio que
  // inventario.js de F2, compras.js de F3 y ventas.js de F4: el Backend
  // no expone page/limit en /api/comercio-exterior/declaraciones, así
  // que la paginación de la tabla se resuelve en el cliente sobre la
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

  const paginadorDeclaraciones = crearPaginador(
    selectTamanioPaginaDeclaraciones,
    document.getElementById("paginacionResumenDeclaraciones"),
    document.getElementById("paginacionControlesDeclaraciones"),
    () => pintarDeclaraciones()
  );

  // ---------- Búsqueda (cliente, ya que /api/comercio-exterior/declaraciones
  // solo filtra por "estado" en el Backend) ----------
  function filtrarDeclaraciones(lista) {
    const q = inputBuscarDeclaraciones.value.trim().toLowerCase();
    if (!q) return lista;
    return lista.filter((d) => {
      const numero = `#${d.id}`.toLowerCase();
      const cliente = (d.cliente_nombre || "").toLowerCase();
      const paisDestino = (d.pais_destino || "").toLowerCase();
      const numeroDua = (d.numero_dua || "").toLowerCase();
      const observaciones = (d.observaciones || "").toLowerCase();
      return (
        numero.includes(q) ||
        cliente.includes(q) ||
        paisDestino.includes(q) ||
        numeroDua.includes(q) ||
        observaciones.includes(q)
      );
    });
  }

  // ---------- Listado ----------
  function pintarDeclaraciones() {
    const filtradas = filtrarDeclaraciones(declaracionesCache);
    const info = paginadorDeclaraciones.calcular(filtradas);

    tbody.innerHTML = info.pagina.length
      ? info.pagina
          .map(
            (d) => `
        <tr>
          <td>#${d.id}</td>
          <td>${U.escaparHtml(d.numero_dua || "—")}</td>
          <td>${U.escaparHtml(d.cliente_nombre)}</td>
          <td>${U.escaparHtml(d.pais_destino)}</td>
          <td>${U.escaparHtml(d.incoterm)}</td>
          <td><span class="badge text-bg-${colorEstado(d.estado)}">${U.escaparHtml(d.estado)}</span></td>
          <td>${U.escaparHtml(d.moneda)}</td>
          <td>${U.formatearFechaHora(d.creado_en)}</td>
          <td class="text-end">
            <button type="button" class="btn btn-sm btn-outline-secondary btn-ver-detalle" data-id="${d.id}">
              <i class="bi bi-eye"></i> Ver
            </button>
          </td>
        </tr>`
          )
          .join("")
      : filaVacia(
          9,
          declaracionesCache.length === 0
            ? "No hay declaraciones de exportación registradas."
            : "Ninguna declaración coincide con la búsqueda/filtro."
        );

    tbody.querySelectorAll(".btn-ver-detalle").forEach((btn) => {
      btn.addEventListener("click", () => abrirModalDetalle(Number(btn.dataset.id)));
    });
  }

  async function cargarDeclaraciones() {
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      const query = selectEstado.value ? `?estado=${encodeURIComponent(selectEstado.value)}` : "";
      declaracionesCache = await apiGet(`/api/comercio-exterior/declaraciones${query}`);
      paginadorDeclaraciones.reiniciar();
      pintarDeclaraciones();
    } catch (err) {
      mostrarError(err.message || "Ocurrió un error al cargar las declaraciones de exportación.");
      if (window.UI) window.UI.toast(err.message || "Ocurrió un error al cargar las declaraciones de exportación.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  async function cargarProductosCache() {
    productosCache = await apiGet("/api/productos?solo_activos=true");
  }

  // ---------- Modal Nueva declaración: ítems dinámicos ----------
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
    recalcularTotalDecl();
  }

  function recalcularTotalDecl() {
    let total = 0;
    tbodyItemsDecl.querySelectorAll("tr").forEach((fila) => {
      const cantidad = Number(fila.querySelector(".item-cantidad").value) || 0;
      const precio = Number(fila.querySelector(".item-precio").value) || 0;
      total += cantidad * precio;
    });
    totalDeclEl.textContent = U.formatearNumero(total, 2);
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
    tbodyItemsDecl.appendChild(fila);

    fila.querySelector(".item-cantidad").addEventListener("input", () => recalcularSubtotalFila(fila));
    fila.querySelector(".item-precio").addEventListener("input", () => recalcularSubtotalFila(fila));
    fila.querySelector(".btn-quitar-item").addEventListener("click", () => {
      // Al menos un ítem es obligatorio (mínimo 1 exigido por
      // DeclaracionCrear en el Backend): no se deja quitar la última fila.
      if (tbodyItemsDecl.querySelectorAll("tr").length <= 1) {
        mostrarErrorModal(modalNuevaError, "La declaración debe tener al menos un ítem: agrega otro antes de quitar este.");
        return;
      }
      fila.remove();
      recalcularTotalDecl();
    });
  }

  function limpiarFormularioNueva() {
    formNueva.reset();
    declIncoterm.value = "FOB";
    declMoneda.value = "USD";
    tbodyItemsDecl.innerHTML = "";
    totalDeclEl.textContent = "0.00";
    ocultarErrorModal(modalNuevaError);
    agregarFilaItem();
  }

  function abrirModalNueva() {
    if (!modalNueva) {
      mostrarError("No se pudo abrir la ventana de nueva declaración: Bootstrap no está disponible.");
      if (window.UI) window.UI.toast("No se pudo abrir la ventana de nueva declaración: Bootstrap no está disponible.", "error");
      return;
    }
    limpiarFormularioNueva();
    modalNueva.show();
  }

  function leerItemsFormulario() {
    const items = [];
    tbodyItemsDecl.querySelectorAll("tr").forEach((fila) => {
      const productoId = fila.querySelector(".item-producto").value;
      const cantidad = fila.querySelector(".item-cantidad").value;
      const precio = fila.querySelector(".item-precio").value;
      if (productoId && cantidad && precio !== "") {
        items.push({
          producto_id: Number(productoId),
          cantidad: Number(cantidad),
          precio_unitario_exportacion: Number(precio),
        });
      }
    });
    return items;
  }

  function validarFormularioNuevaDeclaracion(items) {
    if (!declCliente.value.trim()) {
      mostrarErrorModal(modalNuevaError, "Ingresa el nombre del cliente.");
      declCliente.focus();
      return false;
    }
    if (!declPaisDestino.value.trim()) {
      mostrarErrorModal(modalNuevaError, "Ingresa el país destino.");
      declPaisDestino.focus();
      return false;
    }
    if (!items.length) {
      mostrarErrorModal(modalNuevaError, "Agrega al menos un ítem con producto, cantidad y precio de exportación.");
      return false;
    }
    for (const item of items) {
      if (!(item.cantidad > 0)) {
        mostrarErrorModal(modalNuevaError, "La cantidad de cada ítem debe ser mayor a cero.");
        return false;
      }
      if (!(item.precio_unitario_exportacion >= 0)) {
        mostrarErrorModal(modalNuevaError, "El precio de exportación de cada ítem no puede ser negativo.");
        return false;
      }
    }
    return true;
  }

  async function guardarNuevaDeclaracion(ev) {
    ev.preventDefault();
    ocultarErrorModal(modalNuevaError);

    const items = leerItemsFormulario();
    if (!validarFormularioNuevaDeclaracion(items)) return;

    const datos = {
      cliente_nombre: declCliente.value.trim(),
      pais_destino: declPaisDestino.value.trim(),
      incoterm: declIncoterm.value,
      moneda: declMoneda.value,
      numero_dua: declNumeroDua.value || null,
      observaciones: declObservaciones.value || null,
      items,
    };

    if (window.UI) window.UI.mostrarCargando();
    try {
      await apiPost("/api/comercio-exterior/declaraciones", datos);
      if (modalNueva) modalNueva.hide();
      if (window.UI) window.UI.toast("Declaración de exportación creada correctamente.", "success");
      await cargarDeclaraciones();
    } catch (err) {
      mostrarErrorModal(modalNuevaError, err.message || "No se pudo crear la declaración de exportación.");
      if (window.UI) window.UI.toast(err.message || "No se pudo crear la declaración de exportación.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // ---------- Modal Detalle: información + historial + cambio de estado ----------
  function pintarDetalleInfo(decl) {
    detalleInfo.innerHTML = `
      <div class="col-6"><span class="text-muted-erp">Cliente</span><br>${U.escaparHtml(decl.cliente_nombre)}</div>
      <div class="col-3"><span class="text-muted-erp">Estado</span><br><span class="badge text-bg-${colorEstado(decl.estado)}">${U.escaparHtml(decl.estado)}</span></div>
      <div class="col-3"><span class="text-muted-erp">Moneda</span><br>${U.escaparHtml(decl.moneda)}</div>
      <div class="col-4"><span class="text-muted-erp">País destino</span><br>${U.escaparHtml(decl.pais_destino)}</div>
      <div class="col-4"><span class="text-muted-erp">Incoterm</span><br>${U.escaparHtml(decl.incoterm)}</div>
      <div class="col-4"><span class="text-muted-erp">N.º DUA</span><br>${U.escaparHtml(decl.numero_dua || "—")}</div>
      ${decl.observaciones ? `<div class="col-12"><span class="text-muted-erp">Observaciones</span><br>${U.escaparHtml(decl.observaciones)}</div>` : ""}
    `;
  }

  function pintarDetalleItems(decl) {
    tbodyDetalleItems.innerHTML = decl.items.length
      ? decl.items
          .map(
            (it) => `
        <tr>
          <td>${U.escaparHtml(nombreProducto(it.producto_id))}</td>
          <td class="text-end">${U.formatearNumero(it.cantidad, 3)}</td>
          <td class="text-end">${U.formatearMoneda(it.precio_unitario_exportacion, decl.moneda)}</td>
          <td class="text-end">${U.formatearMoneda(it.cantidad * it.precio_unitario_exportacion, decl.moneda)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(4, "Esta declaración no tiene ítems.");
  }

  // Historial de estados: se arma en el cliente con los 4 timestamps que
  // ya trae DeclaracionOut (no hay endpoint de auditoría/historial en el
  // Backend). Solo se listan los hitos que aplican según el estado actual
  // (una declaración CANCELADA nunca tendrá embarcado_en, por ejemplo).
  function pintarHistorialEstados(decl) {
    const hitos = [
      { etiqueta: "Creada (borrador)", fecha: decl.creado_en, icono: "bi-plus-circle-fill", color: "text-secondary" },
      { etiqueta: "Confirmada", fecha: decl.confirmado_en, icono: "bi-check-circle-fill", color: "text-info" },
      { etiqueta: "Embarcada", fecha: decl.embarcado_en, icono: "bi-send-fill", color: "text-success" },
      { etiqueta: "Cancelada", fecha: decl.cancelado_en, icono: "bi-x-circle-fill", color: "text-danger" },
    ];

    // Si la declaración fue cancelada, "Embarcada" ya no puede ocurrir: se
    // omite en vez de mostrar un hito "pendiente" que no tiene sentido en
    // ese camino. Si aún no fue cancelada, se omite "Cancelada" hasta que
    // ocurra.
    const hitosVisibles = hitos.filter((h) => {
      if (h.etiqueta === "Embarcada" && decl.estado === "CANCELADA" && !h.fecha) return false;
      if (h.etiqueta === "Cancelada" && decl.estado !== "CANCELADA" && !h.fecha) return false;
      return true;
    });

    historialEstadosDecl.innerHTML = hitosVisibles
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
    btnConfirmar.style.display = permitidas.has("CONFIRMADA") ? "" : "none";
    btnEmbarcar.style.display = permitidas.has("EMBARCADA") ? "" : "none";
    btnCancelar.style.display = permitidas.has("CANCELADA") ? "" : "none";
  }

  async function abrirModalDetalle(id) {
    if (!modalDetalle) {
      mostrarError("No se pudo abrir el detalle de la declaración: Bootstrap no está disponible.");
      if (window.UI) window.UI.toast("No se pudo abrir el detalle de la declaración: Bootstrap no está disponible.", "error");
      return;
    }
    declaracionDetalleActualId = id;
    ocultarErrorModal(modalDetalleError);
    detalleTitulo.textContent = `Declaración de exportación #${id}`;
    tbodyDetalleItems.innerHTML = filaVacia(4, "Cargando…");
    detalleInfo.innerHTML = "";
    historialEstadosDecl.innerHTML = "";
    actualizarBotonesTransicion("");
    modalDetalle.show();

    if (window.UI) window.UI.mostrarCargando();
    try {
      const decl = await apiGet(`/api/comercio-exterior/declaraciones/${id}`);
      pintarDetalleInfo(decl);
      pintarDetalleItems(decl);
      pintarHistorialEstados(decl);
      actualizarBotonesTransicion(decl.estado);
    } catch (err) {
      mostrarErrorModal(modalDetalleError, err.message || "No se pudo cargar la declaración de exportación.");
      if (window.UI) window.UI.toast(err.message || "No se pudo cargar la declaración de exportación.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  const CONFIRMACION_TRANSICION = {
    confirmar: {
      titulo: "Confirmar declaración de exportación",
      mensaje: (id) => `¿Deseas confirmar la declaración de exportación #${id}? Esta acción avanza su estado y no se puede deshacer desde aquí.`,
      textoAceptar: "Confirmar",
      variante: "primary",
      mensajeExito: (id) => `Declaración de exportación #${id} confirmada correctamente.`,
      mensajeError: "No se pudo confirmar la declaración de exportación.",
    },
    embarcar: {
      titulo: "Embarcar declaración de exportación",
      mensaje: (id) =>
        `¿Confirmas el embarque de la declaración #${id}? Esta acción descuenta el stock real de cada ítem (FEFO) y no se puede deshacer desde aquí.`,
      textoAceptar: "Embarcar",
      variante: "primary",
      mensajeExito: (id) => `Declaración de exportación #${id} marcada como embarcada.`,
      mensajeError: "No se pudo registrar el embarque de la declaración de exportación.",
    },
    cancelar: {
      titulo: "Cancelar declaración de exportación",
      mensaje: (id) =>
        `¿Deseas cancelar la declaración de exportación #${id}? Esta acción es definitiva: la declaración quedará en estado CANCELADA y no podrá confirmarse ni embarcarse.`,
      textoAceptar: "Cancelar declaración",
      variante: "danger",
      mensajeExito: (id) => `Declaración de exportación #${id} cancelada correctamente.`,
      mensajeError: "No se pudo cancelar la declaración de exportación.",
    },
  };

  async function ejecutarTransicion(accion) {
    if (!declaracionDetalleActualId) return;
    const cfg = CONFIRMACION_TRANSICION[accion];

    const confirmado = window.UI
      ? await window.UI.confirmar({
          titulo: cfg.titulo,
          mensaje: cfg.mensaje(declaracionDetalleActualId),
          textoAceptar: cfg.textoAceptar,
          variante: cfg.variante,
        })
      : true;
    if (!confirmado) return;

    ocultarErrorModal(modalDetalleError);
    if (window.UI) window.UI.mostrarCargando();
    try {
      const decl = await apiPost(`/api/comercio-exterior/declaraciones/${declaracionDetalleActualId}/${accion}`);
      pintarDetalleInfo(decl);
      pintarDetalleItems(decl);
      pintarHistorialEstados(decl);
      actualizarBotonesTransicion(decl.estado);
      if (window.UI) window.UI.toast(cfg.mensajeExito(declaracionDetalleActualId), "success");
      await cargarDeclaraciones();
    } catch (err) {
      mostrarErrorModal(modalDetalleError, err.message || cfg.mensajeError);
      if (window.UI) window.UI.toast(err.message || cfg.mensajeError, "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    selectEstado.addEventListener("change", cargarDeclaraciones);
    inputBuscarDeclaraciones.addEventListener(
      "input",
      U.debounce(() => {
        paginadorDeclaraciones.reiniciar();
        pintarDeclaraciones();
      }, 200)
    );
    selectTamanioPaginaDeclaraciones.addEventListener("change", () => {
      paginadorDeclaraciones.reiniciar();
      pintarDeclaraciones();
    });

    btnNuevaDeclaracion.addEventListener("click", abrirModalNueva);
    btnAgregarItemDecl.addEventListener("click", agregarFilaItem);
    formNueva.addEventListener("submit", guardarNuevaDeclaracion);

    btnConfirmar.addEventListener("click", () => ejecutarTransicion("confirmar"));
    btnEmbarcar.addEventListener("click", () => ejecutarTransicion("embarcar"));
    btnCancelar.addEventListener("click", () => ejecutarTransicion("cancelar"));

    (async () => {
      if (window.UI) window.UI.mostrarCargando();
      try {
        await cargarProductosCache();
      } catch (err) {
        mostrarError(err.message || "No se pudieron cargar los productos.");
        if (window.UI) window.UI.toast(err.message || "No se pudieron cargar los productos.", "error");
      } finally {
        if (window.UI) window.UI.ocultarCargando();
      }
      await cargarDeclaraciones();
    })();
  }

  iniciar();
})();
