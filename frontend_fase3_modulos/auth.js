/**
 * auth.js — Autenticación del Frontend de Core ERP.
 *
 * Debe cargarse DESPUÉS de config.js (lee `window.ERP_CONFIG` y
 * `window.ERP_BASE_PATH` de forma síncrona) y ANTES de layout.js, que ya
 * espera encontrar `window.Auth` con: `requerirSesion()`,
 * `cerrarSesion()`, `obtenerUsuarioActual()` (usa GET /api/auth/me) e
 * `iniciarVigilanciaExpiracion()`.
 *
 * Contrato real del Backend (app/modules/m20_configuracion):
 *   POST /api/auth/login  { username, password } -> { access_token, token_type }
 *   GET  /api/auth/me     (Bearer <token>)        -> { id, username, nombre_completo, rol, activo }
 * El token es un JWT (HS256) con claim `exp` en segundos UTC
 * (app/security.py, expira a las ACCESS_TOKEN_EXPIRE_MINUTES = 12h). No
 * hay endpoint de refresh: al expirar, la única salida es volver a
 * iniciar sesión.
 *
 * No inventa endpoints ni reglas nuevas: solo guarda el token en
 * localStorage (clave `ERP_CONFIG.TOKEN_STORAGE_KEY`), arma el header
 * `Authorization: Bearer <token>` y redirige entre `LOGIN_PATH` y
 * `DASHBOARD_PATH` según corresponda.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  if (!CONFIG) {
    console.error("auth.js: window.ERP_CONFIG no está definido. Carga config.js antes que auth.js.");
    return;
  }

  const BASE = window.ERP_BASE_PATH || "";
  const TOKEN_KEY = CONFIG.TOKEN_STORAGE_KEY;

  // Margen de seguridad para considerar "expirado" un token que está a
  // punto de vencer (evita disparar una petición con un token que
  // caduca a mitad de vuelo). No cambia la duración real del token, que
  // la define solo el Backend.
  const MARGEN_EXPIRACION_MS = 10 * 1000;

  // Frecuencia con la que iniciarVigilanciaExpiracion() revisa si el
  // token ya venció, para cerrar sesión sola sin esperar a la próxima
  // llamada a la API.
  const INTERVALO_VIGILANCIA_MS = 30 * 1000;

  let idIntervaloVigilancia = null;

  function obtenerToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function guardarToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  }

  function eliminarToken() {
    localStorage.removeItem(TOKEN_KEY);
  }

  // Decodifica el payload de un JWT (sin verificar la firma: eso ya lo
  // hace el Backend en cada request; aquí solo se lee el claim `exp`
  // para poder redirigir al login sin esperar un 401).
  function decodificarPayload(token) {
    try {
      const base64Url = token.split(".")[1];
      if (!base64Url) return null;
      const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
      const json = decodeURIComponent(
        atob(base64)
          .split("")
          .map((c) => "%" + c.charCodeAt(0).toString(16).padStart(2, "0"))
          .join("")
      );
      return JSON.parse(json);
    } catch (err) {
      return null;
    }
  }

  function tokenValido(token) {
    if (!token) return false;
    const payload = decodificarPayload(token);
    if (!payload || !payload.exp) return false;
    const expiraEnMs = payload.exp * 1000;
    return expiraEnMs - MARGEN_EXPIRACION_MS > Date.now();
  }

  function haySesion() {
    const token = obtenerToken();
    if (!tokenValido(token)) {
      if (token) eliminarToken(); // token presente pero vencido/corrupto: se limpia
      return false;
    }
    return true;
  }

  // Evita loops de redirección si por algún motivo se llama estando ya
  // en login.html (p.ej. requerirSesion() invocado desde una página que
  // se abrió por error con ese nombre).
  function enPaginaDeLogin() {
    const archivo = window.location.pathname.split("/").pop() || "";
    return archivo.toLowerCase() === CONFIG.LOGIN_PATH.toLowerCase();
  }

  function irALogin() {
    detenerVigilanciaExpiracion();
    if (enPaginaDeLogin()) return;
    window.location.href = `${BASE}${CONFIG.LOGIN_PATH}`;
  }

  function irADashboard() {
    window.location.href = `${BASE}${CONFIG.DASHBOARD_PATH}`;
  }

  // POST /api/auth/login. Lanza un Error con un mensaje ya listo para
  // mostrar al usuario (toma el `detail` que devuelve el Backend en 401
  // "Usuario o contrasena incorrectos" / 403 "Usuario inactivo", o arma
  // uno propio si el Backend no respondió).
  async function iniciarSesion(username, password) {
    let respuesta;
    try {
      respuesta = await fetch(`${CONFIG.API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
    } catch (err) {
      throw new Error(
        `No se pudo conectar con el Backend (${CONFIG.API_BASE_URL}). Verifica que esté corriendo.`
      );
    }

    let datos = null;
    try {
      datos = await respuesta.json();
    } catch (err) {
      datos = null;
    }

    if (!respuesta.ok) {
      const detalle = (datos && datos.detail) || "No se pudo iniciar sesión.";
      throw new Error(detalle);
    }
    if (!datos || !datos.access_token) {
      throw new Error("El Backend no devolvió un token válido.");
    }

    guardarToken(datos.access_token);
    return datos;
  }

  function cerrarSesion() {
    eliminarToken();
    irALogin();
  }

  // GET /api/auth/me con el token guardado. Si el Backend responde 401
  // (token vencido, corrupto, o usuario inactivo — ver deps.py), cierra
  // la sesión local y redirige, igual que si hubiera expirado sola.
  async function obtenerUsuarioActual() {
    const token = obtenerToken();
    if (!tokenValido(token)) {
      cerrarSesion();
      throw new Error("Sesión no válida.");
    }

    const respuesta = await fetch(`${CONFIG.API_BASE_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (respuesta.status === 401) {
      cerrarSesion();
      throw new Error("Sesión expirada.");
    }
    if (!respuesta.ok) {
      throw new Error(`No se pudo obtener el usuario actual (HTTP ${respuesta.status}).`);
    }
    return respuesta.json();
  }

  // Usado por layout.js al entrar a cualquier página protegida: si no
  // hay sesión válida, redirige a LOGIN_PATH y devuelve false para que
  // la página no siga inicializando (no pinta sidebar/navbar ni pide
  // datos que requieren token).
  function requerirSesion() {
    if (!haySesion()) {
      irALogin();
      return false;
    }
    return true;
  }

  // Revisa cada INTERVALO_VIGILANCIA_MS si el token ya venció, para
  // cerrar la sesión sola en vez de esperar a que la próxima llamada a
  // la API devuelva 401. Solo la usan las páginas protegidas (layout.js
  // la llama tras requerirSesion()); login.html no la necesita.
  function iniciarVigilanciaExpiracion() {
    detenerVigilanciaExpiracion();
    idIntervaloVigilancia = window.setInterval(() => {
      if (!haySesion()) irALogin();
    }, INTERVALO_VIGILANCIA_MS);
  }

  function detenerVigilanciaExpiracion() {
    if (idIntervaloVigilancia !== null) {
      window.clearInterval(idIntervaloVigilancia);
      idIntervaloVigilancia = null;
    }
  }

  window.Auth = {
    iniciarSesion,
    cerrarSesion,
    obtenerUsuarioActual,
    requerirSesion,
    haySesion,
    irALogin,
    irADashboard,
    obtenerToken,
    iniciarVigilanciaExpiracion,
    detenerVigilanciaExpiracion,
  };
})();
