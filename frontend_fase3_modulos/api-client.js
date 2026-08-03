/**
 * api-client.js — Cliente HTTP centralizado del Frontend de Core ERP.
 *
 * FASE F0 — Infraestructura Base.
 *
 * Motivo de este archivo: la auditoría de F0 encontró la MISMA función
 * `apiRequest(path, opciones)` copiada y pegada, casi byte a byte, en
 * 11 page-scripts distintos (pages/clientes/clientes.js,
 * pages/comercio_exterior/*.js, pages/compras/*.js, pages/costos/*.js,
 * pages/inventario/*.js, pages/moneda/*.js,
 * pages/operacion_logistica/*.js, pages/productos/*.js,
 * pages/proveedores/*.js, pages/sunat/*.js, pages/ventas/*.js), más una
 * variante de solo-lectura `apiGet(path, params)` duplicada en otros 7
 * (balanced_scorecard, configuracion, inteligencia_comercial,
 * inteligencia_tributaria, lean_six_sigma, reportes,
 * theory_of_constraints). config.js ya avisaba en su cabecera que
 * "api-client.js" debía existir; nunca se había creado. Este archivo es
 * esa única fuente de verdad: mismo comportamiento observado en todas
 * las variantes (token Bearer, Content-Type automático en JSON, 401 ->
 * cierra sesión y redirige, mensaje de error tomado de `detail`, GET con
 * querystring, 204 -> null), sin inventar reglas nuevas ni tocar ningún
 * endpoint del Backend.
 *
 * Debe cargarse DESPUÉS de config.js y auth.js, y ANTES de
 * ui-components.js, layout.js y cualquier page-script.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  if (!CONFIG) {
    console.error("api-client.js: window.ERP_CONFIG no está definido. Carga config.js antes que api-client.js.");
    return;
  }

  // Agrega querystring a un path relativo si se pasan params (mismo
  // criterio que ya usaban apiGet(path, params) en los 7 page-scripts
  // de solo lectura: se omiten valores undefined/null/"").
  function conQuerystring(path, params) {
    if (!params) return path;
    const usp = new URLSearchParams();
    Object.entries(params).forEach(([clave, valor]) => {
      if (valor !== undefined && valor !== null && valor !== "") usp.set(clave, valor);
    });
    const qs = usp.toString();
    return qs ? `${path}${path.includes("?") ? "&" : "?"}${qs}` : path;
  }

  // Extrae un mensaje legible del cuerpo de error del Backend. FastAPI
  // devuelve `detail` como string (errores de negocio, HTTPException) o
  // como lista de objetos {msg, loc, ...} (errores de validación de
  // Pydantic, HTTP 422). Mismo criterio que ya usaban los 11
  // apiRequest() duplicados.
  async function extraerDetalle(resp) {
    let detalle = `HTTP ${resp.status}`;
    try {
      const datos = await resp.json();
      if (datos && datos.detail) {
        detalle = Array.isArray(datos.detail) ? datos.detail.map((d) => d.msg).join("; ") : datos.detail;
      }
    } catch (err) {
      /* sin cuerpo JSON: se conserva "HTTP <status>" */
    }
    return detalle;
  }

  // Petición genérica (GET/POST/PUT/PATCH/DELETE). `opciones` sigue el
  // mismo formato que el segundo argumento de fetch() (method, body,
  // headers adicionales, etc.), igual que en los apiRequest() previos.
  async function request(path, opciones) {
    const token = window.Auth ? window.Auth.obtenerToken() : null;
    const headers = Object.assign({}, opciones && opciones.headers);
    if (token) headers.Authorization = `Bearer ${token}`;
    if (opciones && opciones.body && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    let resp;
    try {
      resp = await fetch(`${CONFIG.API_BASE_URL}${path}`, { ...opciones, headers });
    } catch (err) {
      // Backend caído / CORS / sin red. Mismo mensaje ya usado en
      // auth.js para el login, para que el usuario reciba siempre el
      // mismo tipo de aviso ante un problema de conectividad.
      const errorRed = new Error(
        `No se pudo conectar con el Backend (${CONFIG.API_BASE_URL}). Verifica que esté corriendo.`
      );
      errorRed.status = 0;
      throw errorRed;
    }

    if (resp.status === 401) {
      // Token vencido/corrupto o usuario desactivado a mitad de sesión:
      // mismo comportamiento que ya tenían los 11 apiRequest() y
      // Auth.obtenerUsuarioActual().
      if (window.Auth) window.Auth.cerrarSesion();
      const error = new Error("Sesión expirada.");
      error.status = 401;
      throw error;
    }

    if (!resp.ok) {
      const detalle = await extraerDetalle(resp);
      const error = new Error(detalle);
      error.status = resp.status;
      throw error;
    }

    if (resp.status === 204) return null;
    return resp.json();
  }

  // Atajo de solo-lectura con querystring, equivalente al apiGet(path,
  // params) ya usado en los 7 page-scripts de reportes/analítica.
  async function get(path, params) {
    return request(conQuerystring(path, params), { method: "GET" });
  }

  window.Api = {
    request,
    get,
  };
})();
