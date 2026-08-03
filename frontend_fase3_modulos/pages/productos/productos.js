/**
 * pages/productos/productos.js — Page-script del módulo m02_productos
 * (app/modules/m02_productos).
 *
 * Endpoints (contrato real: router.py + schemas.py), todos con Bearer:
 *   GET   /api/productos?solo_activos=bool     -> list[ProductoOut]
 *   GET   /api/productos/{id}                  -> ProductoOut
 *   POST  /api/productos      body ProductoCrear      -> ProductoOut (201)
 *   PATCH /api/productos/{id} body ProductoActualizar -> ProductoOut
 *
 * ProductoCrear: codigo, nombre, descripcion?, unidad_medida (default "UND"),
 * partida_arancelaria?, stock_minimo (default 0). El código es inmutable:
 * ProductoActualizar NO incluye "codigo", así que el modal de edición lo
 * muestra deshabilitado (no se inventa un endpoint para renombrarlo).
 * ProductoActualizar sí incluye "activo": por eso "activar/desactivar" es
 * un PATCH normal, no un endpoint aparte.
 *
 * FASE 2 — Costo Unitario en Productos (m02_productos, backend intacto).
 * m02_productos (ProductoOut) NO tiene ni tendrá campo de costo: ese dato
 * ya lo calcula el motor de costeo y ya lo expone, de solo lectura,
 *   GET /api/reportes/inventario-valorizado (m19_reportes, sin params)
 *     -> ReporteInventarioValorizado.productos[]: { producto_id, codigo,
 *        nombre, cantidad_actual, valor_promedio_unitario, valor_total,
 *        stock_minimo, bajo_stock_minimo }
 * Es el MISMO endpoint que ya consume pages/reportes/reportes.js (pestaña
 * "Inventario valorizado") y la MISMA fuente que ya usa
 * pages/inventario/inventario.js para el costo unitario del Kardex — así
 * que un producto muestra el mismo costo unitario en Productos,
 * Inventario y Reportes porque los tres leen, sin transformarlo, el mismo
 * campo `valor_promedio_unitario` / `costo_unitario` ya calculado por el
 * motor de costeo (m03 PEPS/FEFO). Esta pantalla NO calcula
 * "Costo Unitario = Valor / Cantidad": solo pinta los 3 campos que el
 * Backend ya entrega tal cual, cruzados en memoria por `producto_id` con
 * la lista de `GET /api/productos` (join de solo lectura, cero
 * aritmética de costeo). Si un producto no aparece en el inventario
 * valorizado (inactivo, o activo pero sin ningún lote/movimiento
 * registrado todavía), las 3 columnas nuevas muestran "—" en vez de un 0
 * engañoso, mismo criterio que ya usa el resto del sistema para "sin
 * dato" (ver p.ej. balanced_scorecard.js).
 *
 * FASE F1 — CRUD Maestros.
 * El Backend no expone DELETE /api/productos/{id} (no está en router.py,
 * mismo contrato ya documentado arriba: solo GET/POST/PATCH). Por eso
 * "Eliminar" en esta pantalla hace lo mismo que ya hacía el switch
 * "Activo" del modal de edición: un PATCH con activo=false (baja lógica),
 * no un borrado físico — no se inventa un endpoint que el Backend no
 * tiene. El botón queda deshabilitado para productos ya inactivos.
 *
 * Tampoco hay paginación ni búsqueda por texto en el Backend (router.py
 * solo acepta "solo_activos"), así que -igual que ya hacían
 * clientes.js/proveedores.js con su "Buscar"- la búsqueda y la
 * paginación de esta pantalla se resuelven en el cliente sobre la lista
 * ya cargada, sin inventar parámetros nuevos.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const elError = document.getElementById("estadoError");
  const checkSoloActivos = document.getElementById("checkSoloActivos");
  const inputBuscar = document.getElementById("inputBuscar");
  const btnNuevo = document.getElementById("btnNuevoProducto");
  const tbody = document.getElementById("tbodyProductos");
  const selectTamanioPagina = document.getElementById("selectTamanioPagina");
  const paginacionResumen = document.getElementById("paginacionResumen");
  const paginacionControles = document.getElementById("paginacionControles");

  const modalEl = document.getElementById("modalProducto");
  // Protección mínima: si el CDN de Bootstrap no cargó, bootstrap no existe
  // y "new bootstrap.Modal(...)" rompería toda la página. En ese caso
  // "modal" queda en null y abrirModalNuevo/abrirModalEditar avisan el
  // error en vez de lanzar un TypeError.
  const modal =
    typeof bootstrap !== "undefined" && bootstrap.Modal
      ? new bootstrap.Modal(modalEl)
      : null;
  const form = document.getElementById("formProducto");
  const modalTitulo = document.getElementById("modalProductoTitulo");
  const modalError = document.getElementById("modalProductoError");

  const campoId = document.getElementById("campoId");
  const campoCodigo = document.getElementById("campoCodigo");
  const campoNombre = document.getElementById("campoNombre");
  const campoDescripcion = document.getElementById("campoDescripcion");
  const campoUnidad = document.getElementById("campoUnidad");
  const campoPartida = document.getElementById("campoPartida");
  const campoStockMinimo = document.getElementById("campoStockMinimo");
  const filaActivo = document.getElementById("filaActivo");
  const campoActivo = document.getElementById("campoActivo");

  let productosCache = [];
  let paginaActual = 1;
  // Map<producto_id, {cantidad_actual, valor_promedio_unitario, valor_total}>
  // poblado desde GET /api/reportes/inventario-valorizado (m19_reportes).
  // Nunca se recalcula nada aquí: son los 3 campos que ya trae el Backend.
  let valorizadoPorProducto = new Map();

  function mostrarError(mensaje) {
    elError.textContent = mensaje;
    elError.style.display = "block";
  }

  function ocultarError() {
    elError.style.display = "none";
  }

  function mostrarErrorModal(mensaje) {
    modalError.textContent = mensaje;
    modalError.style.display = "block";
  }

  function ocultarErrorModal() {
    modalError.style.display = "none";
  }

  async function apiRequest(path, opciones) {
    // FASE F0: delega en el cliente API centralizado (api-client.js).
    // Se conserva esta función local -mismo nombre y firma- para no
    // tocar ningún call-site existente en este archivo.
    return window.Api.request(path, opciones);
  }

  const apiGet = (path) => apiRequest(path);
  const apiPost = (path, body) => apiRequest(path, { method: "POST", body: JSON.stringify(body) });
  const apiPatch = (path, body) => apiRequest(path, { method: "PATCH", body: JSON.stringify(body) });

  function filaVacia(colspan, texto) {
    return `<tr><td colspan="${colspan}" class="text-muted-erp">${texto}</td></tr>`;
  }

  function filtrarProductos() {
    const q = inputBuscar.value.trim().toLowerCase();
    if (!q) return productosCache;
    return productosCache.filter(
      (p) => p.codigo.toLowerCase().includes(q) || p.nombre.toLowerCase().includes(q)
    );
  }

  // Paginación en cliente: el Backend no expone "page"/"limit" en
  // GET /api/productos (solo "solo_activos"), así que se pagina sobre
  // el arreglo ya filtrado, igual criterio que la búsqueda.
  function paginar(lista) {
    const tamanio = Number(selectTamanioPagina.value) || 10;
    const totalPaginas = Math.max(1, Math.ceil(lista.length / tamanio));
    if (paginaActual > totalPaginas) paginaActual = totalPaginas;
    if (paginaActual < 1) paginaActual = 1;
    const inicio = (paginaActual - 1) * tamanio;
    const pagina = lista.slice(inicio, inicio + tamanio);
    return { pagina, totalPaginas, inicio, tamanio, total: lista.length };
  }

  function pintarPaginacion(info) {
    const { totalPaginas, inicio, pagina, total } = info;
    if (total === 0) {
      paginacionResumen.textContent = "Sin resultados";
    } else {
      paginacionResumen.textContent = `Mostrando ${inicio + 1}–${inicio + pagina.length} de ${total}`;
    }

    paginacionControles.innerHTML = "";
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
          pintarProductos();
        });
      }
      li.appendChild(a);
      return li;
    }

    paginacionControles.appendChild(itemPagina("«", paginaActual - 1, paginaActual === 1, false));
    for (let n = 1; n <= totalPaginas; n += 1) {
      paginacionControles.appendChild(itemPagina(String(n), n, false, n === paginaActual));
    }
    paginacionControles.appendChild(itemPagina("»", paginaActual + 1, paginaActual === totalPaginas, false));
  }

  function pintarProductos() {
    const filtrados = filtrarProductos();
    const info = paginar(filtrados);

    tbody.innerHTML = info.pagina.length
      ? info.pagina
          .map((p) => {
            // Union de solo lectura por producto_id contra el Map ya
            // poblado desde GET /api/reportes/inventario-valorizado.
            // Si el producto no tiene fila ahi (inactivo, o activo sin
            // lotes/movimientos todavia), las 3 columnas nuevas muestran
            // "—": no se calcula ni se asume 0.
            const v = valorizadoPorProducto.get(p.id);
            const stockActual = v ? U.formatearNumero(v.cantidad_actual, 2) : "—";
            const costoUnitario = v ? U.formatearMoneda(v.valor_promedio_unitario) : "—";
            const valorInventario = v ? U.formatearMoneda(v.valor_total) : "—";
            return `
        <tr>
          <td><code>${U.escaparHtml(p.codigo)}</code></td>
          <td>${U.escaparHtml(p.nombre)}</td>
          <td>${U.escaparHtml(p.unidad_medida)}</td>
          <td>${U.escaparHtml(p.partida_arancelaria || "—")}</td>
          <td class="text-end">${U.formatearNumero(p.stock_minimo, 2)}</td>
          <td>${p.activo ? '<span class="badge text-bg-success">Activo</span>' : '<span class="badge text-bg-secondary">Inactivo</span>'}</td>
          <td class="text-end">${stockActual}</td>
          <td class="text-end">${costoUnitario}</td>
          <td class="text-end">${valorInventario}</td>
          <td class="text-end">
            <button type="button" class="btn btn-sm btn-outline-secondary btn-editar" data-id="${p.id}" title="Editar">
              <i class="bi bi-pencil"></i>
            </button>
            <a class="btn btn-sm btn-outline-secondary" href="../inventario/index.html?producto_id=${p.id}" title="Ver kardex en Inventario">
              <i class="bi bi-boxes"></i>
            </a>
            <button type="button" class="btn btn-sm btn-outline-danger btn-eliminar" data-id="${p.id}" data-nombre="${U.escaparHtml(p.nombre)}" title="Eliminar" ${p.activo ? "" : "disabled"}>
              <i class="bi bi-trash"></i>
            </button>
          </td>
        </tr>`;
          })
          .join("")
      : filaVacia(10, mensajeVacio(filtrados));

    tbody.querySelectorAll(".btn-editar").forEach((btn) => {
      btn.addEventListener("click", () => abrirModalEditar(Number(btn.dataset.id)));
    });
    tbody.querySelectorAll(".btn-eliminar").forEach((btn) => {
      btn.addEventListener("click", () => eliminarProducto(Number(btn.dataset.id), btn.dataset.nombre));
    });

    pintarPaginacion(info);
  }

  function mensajeVacio(filtrados) {
    if (productosCache.length === 0) return "No hay productos registrados.";
    if (filtrados.length === 0) return "Ningún producto coincide con la búsqueda.";
    return "No hay productos registrados.";
  }

  // GET /api/reportes/inventario-valorizado no acepta parametros (foto
  // del inventario actual, mismo contrato que ya usa reportes.js). Se
  // pide aparte de /api/productos porque son dos recursos distintos
  // (catalogo vs. valorizacion); un fallo aqui no debe romper el listado
  // de productos, solo deja las columnas de costo en "—".
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
      console.error("productos.js: no se pudo cargar /api/reportes/inventario-valorizado.", err);
    }
  }

  async function cargarProductos() {
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      const [productos] = await Promise.all([
        apiGet(`/api/productos?solo_activos=${checkSoloActivos.checked}`),
        cargarValorizado(),
      ]);
      productosCache = productos;
      paginaActual = 1;
      pintarProductos();
    } catch (err) {
      mostrarError(err.message || "Ocurrió un error al cargar los productos.");
      if (window.UI) window.UI.toast(err.message || "Ocurrió un error al cargar los productos.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function limpiarFormulario() {
    form.reset();
    campoId.value = "";
    campoCodigo.disabled = false;
    ocultarErrorModal();
  }

  function abrirModalNuevo() {
    if (!modal) {
      mostrarError("No se pudo abrir la ventana de nuevo producto: Bootstrap no está disponible.");
      return;
    }
    limpiarFormulario();
    modalTitulo.textContent = "Nuevo producto";
    filaActivo.style.display = "none";
    campoUnidad.value = "UND";
    campoStockMinimo.value = "0";
    modal.show();
  }

  async function abrirModalEditar(id) {
    if (!modal) {
      mostrarError("No se pudo abrir la ventana de edición: Bootstrap no está disponible.");
      return;
    }
    limpiarFormulario();
    modalTitulo.textContent = "Editar producto";
    filaActivo.style.display = "";
    if (window.UI) window.UI.mostrarCargando();
    try {
      const p = await apiGet(`/api/productos/${id}`);
      campoId.value = p.id;
      campoCodigo.value = p.codigo;
      campoCodigo.disabled = true; // el código es inmutable (no está en ProductoActualizar)
      campoNombre.value = p.nombre;
      campoDescripcion.value = p.descripcion || "";
      campoUnidad.value = p.unidad_medida;
      campoPartida.value = p.partida_arancelaria || "";
      campoStockMinimo.value = p.stock_minimo;
      campoActivo.checked = p.activo;
      modal.show();
    } catch (err) {
      mostrarError(err.message || "No se pudo cargar el producto.");
      if (window.UI) window.UI.toast(err.message || "No se pudo cargar el producto.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // Validaciones propias de este formulario que HTML5 (required/min) no
  // cubre: campos de texto con solo espacios en blanco, y stock mínimo
  // negativo escrito a mano (el navegador ya bloquea "-" en un input
  // number con min="0" en la mayoría de casos, pero no en todos).
  function validarFormulario() {
    if (!campoCodigo.value.trim()) {
      mostrarErrorModal("El código no puede estar vacío ni contener solo espacios.");
      campoCodigo.focus();
      return false;
    }
    if (!campoNombre.value.trim()) {
      mostrarErrorModal("El nombre no puede estar vacío ni contener solo espacios.");
      campoNombre.focus();
      return false;
    }
    if (campoStockMinimo.value !== "" && Number(campoStockMinimo.value) < 0) {
      mostrarErrorModal("El stock mínimo no puede ser negativo.");
      campoStockMinimo.focus();
      return false;
    }
    return true;
  }

  async function guardarProducto(ev) {
    ev.preventDefault();
    ocultarErrorModal();
    if (!validarFormulario()) return;
    const id = campoId.value;

    if (window.UI) window.UI.mostrarCargando();
    try {
      if (id) {
        const datos = {
          nombre: campoNombre.value.trim(),
          descripcion: campoDescripcion.value.trim() || null,
          unidad_medida: campoUnidad.value.trim(),
          partida_arancelaria: campoPartida.value.trim() || null,
          stock_minimo: Number(campoStockMinimo.value),
          activo: campoActivo.checked,
        };
        await apiPatch(`/api/productos/${id}`, datos);
        if (window.UI) window.UI.toast("Producto actualizado correctamente.", "success");
      } else {
        const datos = {
          codigo: campoCodigo.value.trim(),
          nombre: campoNombre.value.trim(),
          descripcion: campoDescripcion.value.trim() || null,
          unidad_medida: campoUnidad.value.trim() || "UND",
          partida_arancelaria: campoPartida.value.trim() || null,
          stock_minimo: Number(campoStockMinimo.value) || 0,
        };
        await apiPost("/api/productos", datos);
        if (window.UI) window.UI.toast("Producto creado correctamente.", "success");
      }
      if (modal) modal.hide();
      await cargarProductos();
    } catch (err) {
      mostrarErrorModal(err.message || "No se pudo guardar el producto.");
      if (window.UI) window.UI.toast(err.message || "No se pudo guardar el producto.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // "Eliminar" = baja lógica (PATCH activo=false): ver nota de cabecera
  // sobre por qué no hay un DELETE físico en el Backend.
  async function eliminarProducto(id, nombre) {
    if (!window.UI) return;
    const confirmado = await window.UI.confirmar({
      titulo: "Eliminar producto",
      mensaje: `¿Deseas eliminar el producto "${nombre}"? Quedará marcado como inactivo y podrás reactivarlo luego editándolo.`,
      textoAceptar: "Eliminar",
      variante: "danger",
    });
    if (!confirmado) return;

    window.UI.mostrarCargando();
    try {
      await apiPatch(`/api/productos/${id}`, { activo: false });
      window.UI.toast("Producto eliminado correctamente.", "success");
      await cargarProductos();
    } catch (err) {
      window.UI.toast(err.message || "No se pudo eliminar el producto.", "error");
    } finally {
      window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    checkSoloActivos.addEventListener("change", cargarProductos);
    inputBuscar.addEventListener("input", U.debounce(() => {
      paginaActual = 1;
      pintarProductos();
    }, 200));
    selectTamanioPagina.addEventListener("change", () => {
      paginaActual = 1;
      pintarProductos();
    });
    btnNuevo.addEventListener("click", abrirModalNuevo);
    form.addEventListener("submit", guardarProducto);
    modalEl.addEventListener("hidden.bs.modal", limpiarFormulario);

    cargarProductos();
  }

  iniciar();
})();
