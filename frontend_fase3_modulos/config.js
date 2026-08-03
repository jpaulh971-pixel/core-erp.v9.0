/**
 * config.js — Configuración global del Frontend de Core ERP.
 *
 * Debe cargarse ANTES que cualquier otro script. api-client.js y auth.js
 * leen `window.ERP_CONFIG` y `window.ERP_BASE_PATH` de forma síncrona,
 * en el momento en que se cargan (no dentro de una función), así que si
 * este archivo no se carga primero, esos dos scripts fallan de inmediato.
 *
 * No crea endpoints nuevos ni modifica el Backend: solo declara las
 * constantes de configuración que api-client.js y auth.js ya esperaban
 * encontrar en window.ERP_CONFIG / window.ERP_BASE_PATH.
 */
(function () {
  // URL base del Backend (FastAPI). main.py no monta StaticFiles para
  // servir el Frontend (y habilita CORS con allow_origins=["*"]), lo que
  // indica que el Frontend se abre por separado del Backend y necesita la
  // URL completa para llamar a la API. Ajustar aquí si el Backend corre
  // en otro host o puerto.
  const API_BASE_URL = "http://127.0.0.1:8000";

  // Clave usada en localStorage para guardar el JWT (la usa auth.js).
  const TOKEN_STORAGE_KEY = "erp_token";

  // Rutas (relativas a la raíz del Frontend) del login y del dashboard.
  // Coinciden con el enlace ya existente en components/sidebar.html
  // ("__ROOT__dashboard.html") y con la lógica de redirección de auth.js.
  const LOGIN_PATH = "login.html";
  const DASHBOARD_PATH = "dashboard.html";

  window.ERP_CONFIG = {
    API_BASE_URL,
    TOKEN_STORAGE_KEY,
    LOGIN_PATH,
    DASHBOARD_PATH,
  };

  // Prefijo relativo hacia la raíz del Frontend, según la profundidad de
  // la página actual. Lo usa auth.js para construir las redirecciones
  // (irALogin / irADashboard) y layout.js para resolver el token
  // "__ROOT__" dentro de components/sidebar.html.
  //
  // Las páginas de módulo viven en frontend/pages/<modulo>/index.html
  // (dos niveles bajo la raíz del Frontend); login.html y dashboard.html
  // viven en la raíz. Se detecta automáticamente por la URL para no
  // depender de configurarlo a mano en cada página.
  window.ERP_BASE_PATH = window.location.pathname.includes("/pages/") ? "../../" : "";
})();
