/**
 * ui-components.js — Componentes globales de UI del Frontend de Core ERP.
 *
 * FASE F0 — Infraestructura Base.
 *
 * La auditoría de F0 no encontró NINGUNA implementación previa de estos
 * componentes en el proyecto (ni una sola coincidencia de "toast",
 * "Toast" ni de un helper de confirmación reutilizable en todo
 * frontend/): cada página que necesitaba confirmar una acción
 * destructiva simplemente no confirmaba nada (0 usos de
 * window.confirm en los 18 page-scripts), y los mensajes de éxito/error
 * se mostraban -cuando existían- como texto fijo dentro de la propia
 * página (p. ej. #estadoError en ventas.js), sin un mecanismo común.
 *
 * Este archivo expone tres utilidades sobre `window.UI`, construidas
 * únicamente con Bootstrap 5 (ya cargado por todas las páginas vía CDN)
 * y las variables de color ya definidas en erp.css, sin agregar
 * dependencias nuevas:
 *
 *   UI.toast(mensaje, tipo)        tipo: "success" | "error" | "info" | "warning"
 *   UI.confirmar(opciones)         -> Promise<boolean>
 *   UI.mostrarCargando() / UI.ocultarCargando()
 *
 * No reemplaza los mensajes inline que ya usa cada módulo (p. ej.
 * #estadoError) — esos siguen funcionando igual. UI.toast/UI.confirmar
 * quedan disponibles para que las páginas los adopten de forma
 * incremental, y layout.js los usa ya para errores de carga del
 * layout y de la sesión.
 *
 * Debe cargarse DESPUÉS de config.js y ANTES de layout.js y de
 * cualquier page-script que quiera usar UI.*.
 */
(function () {
  const ICONOS = {
    success: "bi-check-circle-fill",
    error: "bi-x-circle-fill",
    warning: "bi-exclamation-triangle-fill",
    info: "bi-info-circle-fill",
  };

  function obtenerContenedorToasts() {
    let contenedor = document.getElementById("erpToastContainer");
    if (!contenedor) {
      contenedor = document.createElement("div");
      contenedor.id = "erpToastContainer";
      contenedor.className = "toast-container position-fixed top-0 end-0 p-3";
      contenedor.style.zIndex = "1080";
      document.body.appendChild(contenedor);
    }
    return contenedor;
  }

  /**
   * Muestra una notificación temporal (toast). No bloquea la página.
   * @param {string} mensaje
   * @param {"success"|"error"|"warning"|"info"} tipo
   */
  function toast(mensaje, tipo) {
    const claseTipo = ICONOS[tipo] ? tipo : "info";
    const contenedor = obtenerContenedorToasts();

    const el = document.createElement("div");
    el.className = `toast align-items-center border-0 erp-toast erp-toast-${claseTipo}`;
    el.setAttribute("role", "alert");
    el.setAttribute("aria-live", "assertive");
    el.setAttribute("aria-atomic", "true");
    el.innerHTML =
      `<div class="d-flex">` +
      `<div class="toast-body"><i class="bi ${ICONOS[claseTipo]} me-2"></i>${window.Utils ? window.Utils.escaparHtml(mensaje) : mensaje}</div>` +
      `<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Cerrar"></button>` +
      `</div>`;
    contenedor.appendChild(el);

    if (typeof bootstrap !== "undefined" && bootstrap.Toast) {
      const instancia = new bootstrap.Toast(el, { delay: claseTipo === "error" ? 6000 : 3500 });
      el.addEventListener("hidden.bs.toast", () => el.remove());
      instancia.show();
    } else {
      // Bootstrap no cargó: se muestra igual (estático) y se auto-elimina.
      el.classList.add("show");
      setTimeout(() => el.remove(), 4000);
    }
  }

  let modalConfirmEl = null;
  let modalConfirmInstancia = null;

  function asegurarModalConfirmacion() {
    if (modalConfirmEl) return;
    modalConfirmEl = document.createElement("div");
    modalConfirmEl.className = "modal fade";
    modalConfirmEl.id = "erpModalConfirmar";
    modalConfirmEl.tabIndex = -1;
    modalConfirmEl.innerHTML = `
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="erpModalConfirmarTitulo">Confirmar</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
          </div>
          <div class="modal-body" id="erpModalConfirmarCuerpo">¿Confirmas esta acción?</div>
          <div class="modal-footer">
            <button type="button" class="btn btn-outline-secondary" id="erpModalConfirmarCancelar">Cancelar</button>
            <button type="button" class="btn btn-danger" id="erpModalConfirmarAceptar">Confirmar</button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(modalConfirmEl);
    if (typeof bootstrap !== "undefined" && bootstrap.Modal) {
      modalConfirmInstancia = new bootstrap.Modal(modalConfirmEl);
    }
  }

  /**
   * Reemplazo reutilizable de window.confirm(), en línea con el resto
   * del look & feel del ERP (modal Bootstrap en vez del diálogo nativo
   * del navegador). Devuelve una Promise<boolean>.
   * @param {{titulo?: string, mensaje: string, textoAceptar?: string, variante?: "danger"|"primary"}} opciones
   */
  function confirmar(opciones) {
    const cfg = typeof opciones === "string" ? { mensaje: opciones } : opciones || {};
    asegurarModalConfirmacion();

    if (!modalConfirmInstancia) {
      // Bootstrap no disponible: se degrada al confirm nativo para no
      // dejar la acción sin forma de confirmarse.
      return Promise.resolve(window.confirm(cfg.mensaje || "¿Confirmas esta acción?"));
    }

    document.getElementById("erpModalConfirmarTitulo").textContent = cfg.titulo || "Confirmar";
    document.getElementById("erpModalConfirmarCuerpo").textContent = cfg.mensaje || "¿Confirmas esta acción?";
    const btnAceptar = document.getElementById("erpModalConfirmarAceptar");
    btnAceptar.textContent = cfg.textoAceptar || "Confirmar";
    btnAceptar.className = `btn btn-${cfg.variante || "danger"}`;

    return new Promise((resolve) => {
      let resuelto = false;
      const finalizar = (valor) => {
        if (resuelto) return;
        resuelto = true;
        resolve(valor);
      };

      const onAceptar = () => {
        finalizar(true);
        modalConfirmInstancia.hide();
      };
      const onOculto = () => {
        finalizar(false);
        btnAceptar.removeEventListener("click", onAceptar);
        modalConfirmEl.removeEventListener("hidden.bs.modal", onOculto);
      };

      btnAceptar.addEventListener("click", onAceptar);
      modalConfirmEl.addEventListener("hidden.bs.modal", onOculto);
      modalConfirmInstancia.show();
    });
  }

  let overlayCarga = null;
  let contadorCarga = 0;

  function asegurarOverlayCarga() {
    if (overlayCarga) return;
    overlayCarga = document.createElement("div");
    overlayCarga.id = "erpLoaderOverlay";
    overlayCarga.className = "erp-loader-overlay";
    overlayCarga.innerHTML = `<div class="spinner-border text-light" role="status"><span class="visually-hidden">Cargando…</span></div>`;
    document.body.appendChild(overlayCarga);
  }

  // Loader global con contador: si dos llamadas simultáneas piden
  // cargando, solo se oculta cuando ambas terminan.
  function mostrarCargando() {
    asegurarOverlayCarga();
    contadorCarga += 1;
    overlayCarga.classList.add("visible");
  }

  function ocultarCargando() {
    if (contadorCarga > 0) contadorCarga -= 1;
    if (contadorCarga === 0 && overlayCarga) overlayCarga.classList.remove("visible");
  }

  window.UI = {
    toast,
    confirmar,
    mostrarCargando,
    ocultarCargando,
  };
})();
