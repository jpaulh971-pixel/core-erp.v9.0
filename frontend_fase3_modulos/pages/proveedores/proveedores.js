/**
 * pages/proveedores/proveedores.js — Page-script del módulo m05_proveedores
 * (app/modules/m05_proveedores).
 *
 * Endpoints (contrato real: router.py + schemas.py), todos con Bearer:
 *   GET   /api/proveedores?solo_activos=bool     -> list[ProveedorOut]
 *   GET   /api/proveedores/{id}                  -> ProveedorOut
 *   POST  /api/proveedores      body ProveedorCrear      -> ProveedorOut (201)
 *   PATCH /api/proveedores/{id} body ProveedorActualizar -> ProveedorOut
 *
 * ProveedorCrear: ruc, razon_social, contacto?, telefono?, email?, pais?.
 * ProveedorActualizar: razon_social?, contacto?, telefono?, email?, pais?,
 * activo?. El RUC es inmutable (no está en ProveedorActualizar, y el
 * Backend valida unicidad de RUC al crear con validar_ruc_disponible), así
 * que el modal de edición lo muestra deshabilitado, igual que el "código"
 * en productos.js. "Activar/desactivar" es un PATCH normal con "activo",
 * no un endpoint aparte (no existe en router.py).
 *
 * El Backend no expone búsqueda por texto (no hay parámetro "q" en
 * router.py), así que el campo "Buscar" filtra en el cliente [navegador]
 * sobre la lista ya cargada (por RUC o razón social), sin inventar un
 * endpoint.
 *
 * FASE F1 — CRUD Maestros.
 * Tampoco hay paginación en el Backend (router.py solo acepta
 * "solo_activos"): la paginación de esta pantalla se resuelve en el
 * navegador sobre la lista ya filtrada, mismo criterio que la búsqueda.
 * "Eliminar" no tiene un DELETE físico en router.py (solo GET/POST/
 * PATCH), así que reutiliza el mismo PATCH activo=false que ya usaba el
 * switch "Activo" del modal — no se inventa un endpoint nuevo.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const elError = document.getElementById("estadoError");
  const checkSoloActivos = document.getElementById("checkSoloActivos");
  const inputBuscar = document.getElementById("inputBuscar");
  const btnNuevo = document.getElementById("btnNuevoProveedor");
  const tbody = document.getElementById("tbodyProveedores");
  const selectTamanioPagina = document.getElementById("selectTamanioPagina");
  const paginacionResumen = document.getElementById("paginacionResumen");
  const paginacionControles = document.getElementById("paginacionControles");

  const modalEl = document.getElementById("modalProveedor");
  // Protección mínima: si el CDN de Bootstrap no cargó, bootstrap no existe
  // y "new bootstrap.Modal(...)" rompería toda la página. En ese caso
  // "modal" queda en null y abrirModalNuevo/abrirModalEditar avisan el
  // error en vez de lanzar un TypeError.
  const modal =
    typeof bootstrap !== "undefined" && bootstrap.Modal
      ? new bootstrap.Modal(modalEl)
      : null;
  const form = document.getElementById("formProveedor");
  const modalTitulo = document.getElementById("modalProveedorTitulo");
  const modalError = document.getElementById("modalProveedorError");

  const campoId = document.getElementById("campoId");
  const campoRuc = document.getElementById("campoRuc");
  const campoRazonSocial = document.getElementById("campoRazonSocial");
  const campoContacto = document.getElementById("campoContacto");
  const campoTelefono = document.getElementById("campoTelefono");
  const campoEmail = document.getElementById("campoEmail");
  const campoPais = document.getElementById("campoPais");
  const filaActivo = document.getElementById("filaActivo");
  const campoActivo = document.getElementById("campoActivo");

  let proveedoresCache = [];
  let paginaActual = 1;

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

  function filtrarProveedores() {
    const q = inputBuscar.value.trim().toLowerCase();
    if (!q) return proveedoresCache;
    return proveedoresCache.filter(
      (p) => p.ruc.toLowerCase().includes(q) || p.razon_social.toLowerCase().includes(q)
    );
  }

  // Paginación en cliente: el Backend no expone "page"/"limit" en
  // GET /api/proveedores (solo "solo_activos"), así que se pagina sobre
  // el arreglo ya filtrado por la búsqueda, mismo criterio que esta última.
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
          pintarProveedores();
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

  function pintarProveedores() {
    const filtrados = filtrarProveedores();
    const info = paginar(filtrados);

    tbody.innerHTML = info.pagina.length
      ? info.pagina
          .map(
            (p) => `
        <tr>
          <td><code>${U.escaparHtml(p.ruc)}</code></td>
          <td>${U.escaparHtml(p.razon_social)}</td>
          <td>${U.escaparHtml(p.contacto || "—")}</td>
          <td>${U.escaparHtml(p.telefono || "—")}</td>
          <td>${U.escaparHtml(p.pais || "—")}</td>
          <td>${p.activo ? '<span class="badge text-bg-success">Activo</span>' : '<span class="badge text-bg-secondary">Inactivo</span>'}</td>
          <td class="text-end">
            <button type="button" class="btn btn-sm btn-outline-secondary btn-editar" data-id="${p.id}" title="Editar">
              <i class="bi bi-pencil"></i>
            </button>
            <button type="button" class="btn btn-sm btn-outline-danger btn-eliminar" data-id="${p.id}" data-nombre="${U.escaparHtml(p.razon_social)}" title="Eliminar" ${p.activo ? "" : "disabled"}>
              <i class="bi bi-trash"></i>
            </button>
          </td>
        </tr>`
          )
          .join("")
      : filaVacia(7, proveedoresCache.length === 0 ? "No hay proveedores registrados." : "Ningún proveedor coincide con la búsqueda.");

    tbody.querySelectorAll(".btn-editar").forEach((btn) => {
      btn.addEventListener("click", () => abrirModalEditar(Number(btn.dataset.id)));
    });
    tbody.querySelectorAll(".btn-eliminar").forEach((btn) => {
      btn.addEventListener("click", () => eliminarProveedor(Number(btn.dataset.id), btn.dataset.nombre));
    });

    pintarPaginacion(info);
  }

  async function cargarProveedores() {
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      proveedoresCache = await apiGet(`/api/proveedores?solo_activos=${checkSoloActivos.checked}`);
      paginaActual = 1;
      pintarProveedores();
    } catch (err) {
      mostrarError(err.message || "Ocurrió un error al cargar los proveedores.");
      if (window.UI) window.UI.toast(err.message || "Ocurrió un error al cargar los proveedores.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function limpiarFormulario() {
    form.reset();
    campoId.value = "";
    campoRuc.disabled = false;
    ocultarErrorModal();
  }

  function abrirModalNuevo() {
    if (!modal) {
      mostrarError("No se pudo abrir la ventana de nuevo proveedor: Bootstrap no está disponible.");
      return;
    }
    limpiarFormulario();
    modalTitulo.textContent = "Nuevo proveedor";
    filaActivo.style.display = "none";
    modal.show();
  }

  async function abrirModalEditar(id) {
    if (!modal) {
      mostrarError("No se pudo abrir la ventana de edición: Bootstrap no está disponible.");
      return;
    }
    limpiarFormulario();
    modalTitulo.textContent = "Editar proveedor";
    filaActivo.style.display = "";
    if (window.UI) window.UI.mostrarCargando();
    try {
      const p = await apiGet(`/api/proveedores/${id}`);
      campoId.value = p.id;
      campoRuc.value = p.ruc;
      campoRuc.disabled = true; // el RUC es inmutable (no está en ProveedorActualizar)
      campoRazonSocial.value = p.razon_social;
      campoContacto.value = p.contacto || "";
      campoTelefono.value = p.telefono || "";
      campoEmail.value = p.email || "";
      campoPais.value = p.pais || "";
      campoActivo.checked = p.activo;
      modal.show();
    } catch (err) {
      mostrarError(err.message || "No se pudo cargar el proveedor.");
      if (window.UI) window.UI.toast(err.message || "No se pudo cargar el proveedor.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // Validaciones propias de este formulario que HTML5 (required/pattern)
  // no cubre del todo: razón social con solo espacios en blanco (required
  // sí la deja pasar) y RUC con espacios sueltos antes del patrón.
  function validarFormulario() {
    const ruc = campoRuc.value.trim();
    if (!/^[0-9]{11}$/.test(ruc)) {
      mostrarErrorModal("El RUC debe tener exactamente 11 dígitos numéricos.");
      campoRuc.focus();
      return false;
    }
    if (!campoRazonSocial.value.trim()) {
      mostrarErrorModal("La razón social no puede estar vacía ni contener solo espacios.");
      campoRazonSocial.focus();
      return false;
    }
    return true;
  }

  async function guardarProveedor(ev) {
    ev.preventDefault();
    ocultarErrorModal();
    if (!validarFormulario()) return;
    const id = campoId.value;

    if (window.UI) window.UI.mostrarCargando();
    try {
      if (id) {
        const datos = {
          razon_social: campoRazonSocial.value.trim(),
          contacto: campoContacto.value.trim() || null,
          telefono: campoTelefono.value.trim() || null,
          email: campoEmail.value.trim() || null,
          pais: campoPais.value.trim() || null,
          activo: campoActivo.checked,
        };
        await apiPatch(`/api/proveedores/${id}`, datos);
        if (window.UI) window.UI.toast("Proveedor actualizado correctamente.", "success");
      } else {
        const datos = {
          ruc: campoRuc.value.trim(),
          razon_social: campoRazonSocial.value.trim(),
          contacto: campoContacto.value.trim() || null,
          telefono: campoTelefono.value.trim() || null,
          email: campoEmail.value.trim() || null,
          pais: campoPais.value.trim() || null,
        };
        await apiPost("/api/proveedores", datos);
        if (window.UI) window.UI.toast("Proveedor creado correctamente.", "success");
      }
      if (modal) modal.hide();
      await cargarProveedores();
    } catch (err) {
      mostrarErrorModal(err.message || "No se pudo guardar el proveedor.");
      if (window.UI) window.UI.toast(err.message || "No se pudo guardar el proveedor.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // "Eliminar" = baja lógica (PATCH activo=false): ver nota de cabecera
  // sobre por qué no hay un DELETE físico en el Backend.
  async function eliminarProveedor(id, nombre) {
    if (!window.UI) return;
    const confirmado = await window.UI.confirmar({
      titulo: "Eliminar proveedor",
      mensaje: `¿Deseas eliminar al proveedor "${nombre}"? Quedará marcado como inactivo y podrás reactivarlo luego editándolo.`,
      textoAceptar: "Eliminar",
      variante: "danger",
    });
    if (!confirmado) return;

    window.UI.mostrarCargando();
    try {
      await apiPatch(`/api/proveedores/${id}`, { activo: false });
      window.UI.toast("Proveedor eliminado correctamente.", "success");
      await cargarProveedores();
    } catch (err) {
      window.UI.toast(err.message || "No se pudo eliminar el proveedor.", "error");
    } finally {
      window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    checkSoloActivos.addEventListener("change", cargarProveedores);
    inputBuscar.addEventListener("input", U.debounce(() => {
      paginaActual = 1;
      pintarProveedores();
    }, 200));
    selectTamanioPagina.addEventListener("change", () => {
      paginaActual = 1;
      pintarProveedores();
    });
    btnNuevo.addEventListener("click", abrirModalNuevo);
    form.addEventListener("submit", guardarProveedor);
    modalEl.addEventListener("hidden.bs.modal", limpiarFormulario);

    cargarProveedores();
  }

  iniciar();
})();
