/**
 * pages/clientes/clientes.js — Page-script del módulo m11_clientes
 * (app/modules/m11_clientes).
 *
 * Endpoints (contrato real: router.py + schemas.py), todos con Bearer:
 *   GET   /api/clientes?solo_activos=bool     -> list[ClienteOut]
 *   GET   /api/clientes/{id}                  -> ClienteOut
 *   POST  /api/clientes      body ClienteCrear      -> ClienteOut (201)
 *   PATCH /api/clientes/{id} body ClienteActualizar -> ClienteOut
 *
 * ClienteCrear: ruc, razon_social, contacto?, telefono?, email?, pais?.
 * ClienteActualizar: razon_social?, contacto?, telefono?, email?, pais?,
 * activo?. El RUC es inmutable (no está en ClienteActualizar, y el
 * Backend valida unicidad de RUC al crear con validar_ruc_disponible), así
 * que el modal de edición lo muestra deshabilitado, igual que en
 * proveedores.js. "Activar/desactivar" es un PATCH normal con "activo",
 * no un endpoint aparte (no existe en router.py).
 *
 * El Backend no expone búsqueda por texto (no hay parámetro "q" en
 * router.py), así que el campo "Buscar" filtra en el cliente sobre la
 * lista ya cargada (por RUC o razón social), sin inventar un endpoint.
 * Mismo patrón exacto que pages/proveedores/proveedores.js.
 *
 * FASE F1 — CRUD Maestros.
 * Tampoco hay paginación en el Backend (router.py solo acepta
 * "solo_activos"): la paginación de esta pantalla se resuelve en el
 * cliente sobre la lista ya filtrada, mismo criterio que la búsqueda.
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
  const btnNuevo = document.getElementById("btnNuevoCliente");
  const tbody = document.getElementById("tbodyClientes");
  const selectTamanioPagina = document.getElementById("selectTamanioPagina");
  const paginacionResumen = document.getElementById("paginacionResumen");
  const paginacionControles = document.getElementById("paginacionControles");

  const modalEl = document.getElementById("modalCliente");
  // Protección mínima: si el CDN de Bootstrap no cargó, bootstrap no existe
  // y "new bootstrap.Modal(...)" rompería toda la página. En ese caso
  // "modal" queda en null y abrirModalNuevo/abrirModalEditar avisan el
  // error en vez de lanzar un TypeError.
  const modal =
    typeof bootstrap !== "undefined" && bootstrap.Modal
      ? new bootstrap.Modal(modalEl)
      : null;
  const form = document.getElementById("formCliente");
  const modalTitulo = document.getElementById("modalClienteTitulo");
  const modalError = document.getElementById("modalClienteError");

  const campoId = document.getElementById("campoId");
  const campoRuc = document.getElementById("campoRuc");
  const campoRazonSocial = document.getElementById("campoRazonSocial");
  const campoContacto = document.getElementById("campoContacto");
  const campoTelefono = document.getElementById("campoTelefono");
  const campoEmail = document.getElementById("campoEmail");
  const campoPais = document.getElementById("campoPais");
  const filaActivo = document.getElementById("filaActivo");
  const campoActivo = document.getElementById("campoActivo");

  let clientesCache = [];
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

  function filtrarClientes() {
    const q = inputBuscar.value.trim().toLowerCase();
    if (!q) return clientesCache;
    return clientesCache.filter(
      (c) => c.ruc.toLowerCase().includes(q) || c.razon_social.toLowerCase().includes(q)
    );
  }

  // Paginación en cliente: el Backend no expone "page"/"limit" en
  // GET /api/clientes (solo "solo_activos"), así que se pagina sobre el
  // arreglo ya filtrado por la búsqueda, mismo criterio que esta última.
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
          pintarClientes();
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

  function pintarClientes() {
    const filtrados = filtrarClientes();
    const info = paginar(filtrados);

    tbody.innerHTML = info.pagina.length
      ? info.pagina
          .map(
            (c) => `
        <tr>
          <td><code>${U.escaparHtml(c.ruc)}</code></td>
          <td>${U.escaparHtml(c.razon_social)}</td>
          <td>${U.escaparHtml(c.contacto || "—")}</td>
          <td>${U.escaparHtml(c.telefono || "—")}</td>
          <td>${U.escaparHtml(c.pais || "—")}</td>
          <td>${c.activo ? '<span class="badge text-bg-success">Activo</span>' : '<span class="badge text-bg-secondary">Inactivo</span>'}</td>
          <td class="text-end">
            <button type="button" class="btn btn-sm btn-outline-secondary btn-editar" data-id="${c.id}" title="Editar">
              <i class="bi bi-pencil"></i>
            </button>
            <button type="button" class="btn btn-sm btn-outline-danger btn-eliminar" data-id="${c.id}" data-nombre="${U.escaparHtml(c.razon_social)}" title="Eliminar" ${c.activo ? "" : "disabled"}>
              <i class="bi bi-trash"></i>
            </button>
          </td>
        </tr>`
          )
          .join("")
      : filaVacia(7, clientesCache.length === 0 ? "No hay clientes registrados." : "Ningún cliente coincide con la búsqueda.");

    tbody.querySelectorAll(".btn-editar").forEach((btn) => {
      btn.addEventListener("click", () => abrirModalEditar(Number(btn.dataset.id)));
    });
    tbody.querySelectorAll(".btn-eliminar").forEach((btn) => {
      btn.addEventListener("click", () => eliminarCliente(Number(btn.dataset.id), btn.dataset.nombre));
    });

    pintarPaginacion(info);
  }

  async function cargarClientes() {
    ocultarError();
    if (window.UI) window.UI.mostrarCargando();
    try {
      clientesCache = await apiGet(`/api/clientes?solo_activos=${checkSoloActivos.checked}`);
      paginaActual = 1;
      pintarClientes();
    } catch (err) {
      mostrarError(err.message || "Ocurrió un error al cargar los clientes.");
      if (window.UI) window.UI.toast(err.message || "Ocurrió un error al cargar los clientes.", "error");
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
      mostrarError("No se pudo abrir la ventana de nuevo cliente: Bootstrap no está disponible.");
      return;
    }
    limpiarFormulario();
    modalTitulo.textContent = "Nuevo cliente";
    filaActivo.style.display = "none";
    modal.show();
  }

  async function abrirModalEditar(id) {
    if (!modal) {
      mostrarError("No se pudo abrir la ventana de edición: Bootstrap no está disponible.");
      return;
    }
    limpiarFormulario();
    modalTitulo.textContent = "Editar cliente";
    filaActivo.style.display = "";
    if (window.UI) window.UI.mostrarCargando();
    try {
      const c = await apiGet(`/api/clientes/${id}`);
      campoId.value = c.id;
      campoRuc.value = c.ruc;
      campoRuc.disabled = true; // el RUC es inmutable (no está en ClienteActualizar)
      campoRazonSocial.value = c.razon_social;
      campoContacto.value = c.contacto || "";
      campoTelefono.value = c.telefono || "";
      campoEmail.value = c.email || "";
      campoPais.value = c.pais || "";
      campoActivo.checked = c.activo;
      modal.show();
    } catch (err) {
      mostrarError(err.message || "No se pudo cargar el cliente.");
      if (window.UI) window.UI.toast(err.message || "No se pudo cargar el cliente.", "error");
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

  async function guardarCliente(ev) {
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
        await apiPatch(`/api/clientes/${id}`, datos);
        if (window.UI) window.UI.toast("Cliente actualizado correctamente.", "success");
      } else {
        const datos = {
          ruc: campoRuc.value.trim(),
          razon_social: campoRazonSocial.value.trim(),
          contacto: campoContacto.value.trim() || null,
          telefono: campoTelefono.value.trim() || null,
          email: campoEmail.value.trim() || null,
          pais: campoPais.value.trim() || null,
        };
        await apiPost("/api/clientes", datos);
        if (window.UI) window.UI.toast("Cliente creado correctamente.", "success");
      }
      if (modal) modal.hide();
      await cargarClientes();
    } catch (err) {
      mostrarErrorModal(err.message || "No se pudo guardar el cliente.");
      if (window.UI) window.UI.toast(err.message || "No se pudo guardar el cliente.", "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  // "Eliminar" = baja lógica (PATCH activo=false): ver nota de cabecera
  // sobre por qué no hay un DELETE físico en el Backend.
  async function eliminarCliente(id, nombre) {
    if (!window.UI) return;
    const confirmado = await window.UI.confirmar({
      titulo: "Eliminar cliente",
      mensaje: `¿Deseas eliminar al cliente "${nombre}"? Quedará marcado como inactivo y podrás reactivarlo luego editándolo.`,
      textoAceptar: "Eliminar",
      variante: "danger",
    });
    if (!confirmado) return;

    window.UI.mostrarCargando();
    try {
      await apiPatch(`/api/clientes/${id}`, { activo: false });
      window.UI.toast("Cliente eliminado correctamente.", "success");
      await cargarClientes();
    } catch (err) {
      window.UI.toast(err.message || "No se pudo eliminar el cliente.", "error");
    } finally {
      window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    checkSoloActivos.addEventListener("change", cargarClientes);
    inputBuscar.addEventListener("input", U.debounce(() => {
      paginaActual = 1;
      pintarClientes();
    }, 200));
    selectTamanioPagina.addEventListener("change", () => {
      paginaActual = 1;
      pintarClientes();
    });
    btnNuevo.addEventListener("click", abrirModalNuevo);
    form.addEventListener("submit", guardarCliente);
    modalEl.addEventListener("hidden.bs.modal", limpiarFormulario);

    cargarClientes();
  }

  iniciar();
})();
