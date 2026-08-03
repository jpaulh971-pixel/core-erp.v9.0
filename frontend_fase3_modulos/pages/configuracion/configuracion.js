/**
 * pages/configuracion/configuracion.js — Page-script del módulo
 * m20_configuracion (app/modules/m20_configuracion).
 *
 * Es la primera página de la Fase 3 porque valida las 3 cosas de las que
 * dependen las demás páginas de módulo:
 *   1. window.Auth (auth.js) ya cargado y con sesión vigente.
 *   2. El token se puede usar para armar `Authorization: Bearer <token>`
 *      contra el Backend real.
 *   3. window.ERP_CONFIG.API_BASE_URL apunta a un Backend que responde.
 *
 * Endpoints que consume (contrato en contrato_api_modulos.md, sección 5):
 *   GET /api/configuracion/status      (sin auth)
 *   GET /api/auth/me                   (Bearer)  -> UsuarioOut
 *   GET /api/configuracion/parametros  (Bearer)  -> list[ParametroOut]
 *
 * No inventa endpoints ni campos: solo pinta lo que estos 3 ya devuelven.
 *
 * FASE F15 — Corrección de deuda técnica (hallazgo F14 #1): se integra
 * UI.mostrarCargando()/UI.ocultarCargando()/UI.toast() (ausentes hasta
 * ahora en este módulo, mismo patrón ya aplicado en F10-F13 al resto de
 * módulos de solo lectura). No se toca ningún endpoint ni cálculo; el
 * mensaje inline `#estadoError` se conserva igual que antes, y UI.toast()
 * se agrega como notificación adicional, no como reemplazo.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;

  const elError = document.getElementById("estadoError");
  const elBaseUrl = document.getElementById("kpiBaseUrl");
  const elBadgeBackend = document.getElementById("badgeBackend");
  const elToken = document.getElementById("kpiToken");
  const elBadgeToken = document.getElementById("badgeToken");
  const elModulo = document.getElementById("kpiModulo");
  const elModuloSub = document.getElementById("kpiModuloSub");
  const elCardUsuario = document.getElementById("cardUsuario");
  const elTbodyParametros = document.getElementById("tbodyParametros");

  function mostrarError(mensaje) {
    elError.textContent = mensaje;
    elError.style.display = "block";
  }

  function marcarBadge(el, ok, textoOk, textoBad) {
    el.textContent = ok ? textoOk : textoBad;
    el.classList.toggle("badge-ok", ok);
    el.classList.toggle("badge-bad", !ok);
  }

  // GET sin Authorization (usado solo para /api/configuracion/status, que
  // el propio Backend expone sin get_usuario_actual).
  async function apiGetPublico(path) {
    const resp = await fetch(`${CONFIG.API_BASE_URL}${path}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  // GET con Authorization: Bearer <token>, leyendo el token con
  // Auth.obtenerToken() (auth.js). Ante 401, deja que Auth.cerrarSesion()
  // cierre la sesión y redirija a login.html, igual que hace auth.js en
  // obtenerUsuarioActual().
  async function apiGet(path, params) {
    // FASE F0: delega en el cliente API centralizado (api-client.js).
    return window.Api.get(path, params);
  }

  async function validarBackend() {
    elBaseUrl.textContent = CONFIG.API_BASE_URL;
    try {
      const status = await apiGetPublico("/api/configuracion/status");
      marcarBadge(elBadgeBackend, true, "Backend accesible", "Backend no responde");
      elModulo.textContent = status.estado || "—";
      elModuloSub.textContent = `Módulo: ${status.modulo || "m20_configuracion"}`;
    } catch (err) {
      marcarBadge(elBadgeBackend, false, "Backend accesible", "Backend no responde");
      elModulo.textContent = "Sin respuesta";
      elModuloSub.textContent = `No se pudo conectar a ${CONFIG.API_BASE_URL}`;
    }
  }

  function validarToken() {
    const token = window.Auth.obtenerToken();
    const valido = window.Auth.haySesion();
    elToken.textContent = valido ? "Token presente y vigente" : "Sin token válido";
    marcarBadge(elBadgeToken, valido, "Sesión vigente", "Sesión inválida");
    return valido && !!token;
  }

  async function cargarUsuario() {
    try {
      const usuario = await apiGet("/api/auth/me");
      const nombre = usuario.nombre_completo || usuario.username || "—";
      elCardUsuario.innerHTML = `
        <div class="d-flex align-items-center gap-3 mb-3">
          <div class="avatar" style="width:48px;height:48px;font-size:16px;">
            ${window.Utils.escaparHtml(nombre.trim().charAt(0).toUpperCase() || "U")}
          </div>
          <div>
            <div style="font-weight:800; font-size:15px;">${window.Utils.escaparHtml(nombre)}</div>
            <div class="text-muted-erp">@${window.Utils.escaparHtml(usuario.username || "—")}</div>
          </div>
        </div>
        <table class="table-erp">
          <tbody>
            <tr><td class="text-muted-erp" style="width:40%;">ID</td><td>${usuario.id ?? "—"}</td></tr>
            <tr><td class="text-muted-erp">Rol</td><td>${window.Utils.escaparHtml(usuario.rol || "—")}</td></tr>
            <tr>
              <td class="text-muted-erp">Estado</td>
              <td>
                <span class="badge-diag ${usuario.activo ? "badge-ok" : "badge-bad"}">
                  ${usuario.activo ? "Activo" : "Inactivo"}
                </span>
              </td>
            </tr>
          </tbody>
        </table>`;
    } catch (err) {
      elCardUsuario.innerHTML = `<div class="text-muted-erp">No se pudo cargar el usuario actual.</div>`;
      throw err;
    }
  }

  async function cargarParametros() {
    try {
      const parametros = await apiGet("/api/configuracion/parametros");
      if (!parametros || parametros.length === 0) {
        elTbodyParametros.innerHTML = `<tr><td colspan="3" class="text-muted-erp">No hay parámetros registrados.</td></tr>`;
        return;
      }
      elTbodyParametros.innerHTML = parametros
        .map(
          (p) => `
        <tr>
          <td><code>${window.Utils.escaparHtml(p.clave)}</code></td>
          <td>${window.Utils.escaparHtml(p.valor)}</td>
          <td class="text-muted-erp">${window.Utils.escaparHtml(p.descripcion || "—")}</td>
        </tr>`
        )
        .join("");
    } catch (err) {
      elTbodyParametros.innerHTML = `<tr><td colspan="3" class="text-muted-erp">No se pudieron cargar los parámetros.</td></tr>`;
      throw err;
    }
  }

  async function iniciar() {
    if (!CONFIG) {
      mostrarError("config.js no se cargó correctamente (window.ERP_CONFIG no está definido).");
      return;
    }
    if (!window.Auth) {
      mostrarError("auth.js no se cargó correctamente (window.Auth no está definido).");
      return;
    }

    // requerirSesion() ya lo valida layout.js al inyectar el chrome; aquí
    // se repite la verificación porque esta página es, además, la que
    // muestra el diagnóstico de sesión/token al usuario.
    const tokenOk = validarToken();
    if (window.UI) window.UI.mostrarCargando();
    try {
      await validarBackend();

      if (!tokenOk) {
        const mensaje = "No hay una sesión válida: no se pueden cargar los datos protegidos.";
        mostrarError(mensaje);
        if (window.UI) window.UI.toast(mensaje, "error");
        return;
      }

      await Promise.all([cargarUsuario(), cargarParametros()]);
    } catch (err) {
      const mensaje = err.message || "Ocurrió un error al cargar la configuración.";
      mostrarError(mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
    } finally {
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  iniciar();
})();
