/**
 * layout.js — Ensambla el "chrome" común de cada página del ERP:
 * inyecta components/sidebar.html, components/navbar.html y
 * components/footer.html alrededor de #erpApp, resuelve el token
 * "__ROOT__" que ya usa sidebar.html, exige sesión iniciada (reutilizando
 * Auth.requerirSesion(), ya expuesto por auth.js) y conecta los
 * controles que sidebar.html/navbar.html/footer.html ya traen
 * (toggle del sidebar, cerrar sesión, buscador, reloj/año, datos del
 * usuario en la navbar vía GET /api/auth/me, que ya usa configuracion.js).
 *
 * Carga los 3 componentes con fetch() (no los duplica embebidos aquí)
 * para que sigan siendo la única fuente de verdad. Si el Frontend se
 * abre directamente como archivo (file://) en vez de sobre un servidor
 * local, el navegador puede bloquear ese fetch por CORS; en ese caso
 * queda un aviso claro en consola.
 *
 * No agrega módulos, endpoints ni funcionalidades: solo cablea lo que
 * ya está declarado en sidebar.html, navbar.html y footer.html.
 */
(function () {
  const BASE = window.ERP_BASE_PATH || "";

  function resolverRoot(html) {
    return html.split("__ROOT__").join(BASE);
  }

  async function cargarComponente(nombreArchivo) {
    const resp = await fetch(`${BASE}components/${nombreArchivo}`);
    if (!resp.ok) {
      throw new Error(`No se pudo cargar components/${nombreArchivo} (HTTP ${resp.status})`);
    }
    const html = await resp.text();
    return resolverRoot(html);
  }

  function primerElemento(html) {
    const contenedor = document.createElement("div");
    contenedor.innerHTML = html.trim();
    return contenedor.firstElementChild;
  }

  function paginaActual() {
    // "/frontend/pages/reportes/index.html" -> "reportes"
    const partes = window.location.pathname.split("/").filter(Boolean);
    const idxPages = partes.lastIndexOf("pages");
    if (idxPages !== -1 && partes[idxPages + 1]) return partes[idxPages + 1];
    const archivo = (partes[partes.length - 1] || "").toLowerCase();
    if (archivo.startsWith("dashboard")) return "dashboard";
    return null;
  }

  function marcarLinkActivo() {
    const actual = paginaActual();
    if (!actual) return;
    document.querySelectorAll(".erp-nav .nav-link[data-page]").forEach((link) => {
      if (link.dataset.page === actual) link.classList.add("active");
    });
  }

  function inicializarToggleSidebar() {
    const boton = document.getElementById("btnToggleSidebar");
    if (!boton) return;
    if (window.matchMedia && window.matchMedia("(max-width: 991.98px)").matches) {
      document.body.classList.add("erp-sidebar-hidden");
    }
    boton.addEventListener("click", () => {
      document.body.classList.toggle("erp-sidebar-hidden");
    });
  }

  function inicializarCerrarSesion() {
    const boton = document.getElementById("btnCerrarSesion");
    if (!boton || !window.Auth) return;
    boton.addEventListener("click", (ev) => {
      ev.preventDefault();
      window.Auth.cerrarSesion();
    });
  }

  function inicializarBuscadorGlobal() {
    // El Backend no expone todavía un endpoint de búsqueda global, así
    // que aquí solo se evita que el campo quede roto (sin resultados
    // fantasma abiertos); no se inventa un endpoint ni una búsqueda real.
    const input = document.getElementById("buscadorGlobal");
    const resultados = document.getElementById("buscadorResultados");
    if (!input || !resultados) return;
    input.addEventListener("input", () => {
      resultados.style.display = "none";
    });
    input.addEventListener("blur", () => {
      setTimeout(() => {
        resultados.style.display = "none";
      }, 150);
    });
  }

  function pintarFechaYAnio() {
    const chipFecha = document.querySelector("#chipFecha span");
    if (chipFecha) {
      chipFecha.textContent = new Date().toLocaleDateString("es-PE", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
    }
    const anio = document.getElementById("footerAnio");
    if (anio) anio.textContent = String(new Date().getFullYear());
  }

  async function pintarUsuarioNavbar() {
    if (!window.Auth) return;
    try {
      // Reutiliza GET /api/auth/me, el mismo endpoint que ya consume
      // pages/configuracion.js. No se agrega ningún endpoint nuevo.
      const usuario = await window.Auth.obtenerUsuarioActual();
      const nombreEl = document.getElementById("userNombre");
      const rolEl = document.getElementById("userRol");
      const avatarEl = document.getElementById("userAvatar");
      const nombre = usuario.nombre_completo || usuario.username || "Usuario";
      if (nombreEl) nombreEl.textContent = nombre;
      if (rolEl) rolEl.textContent = usuario.rol || "—";
      if (avatarEl) avatarEl.textContent = nombre.trim().charAt(0).toUpperCase() || "U";
    } catch (err) {
      console.error("layout.js: no se pudo cargar el usuario actual para la navbar.", err);
      // Auth.obtenerUsuarioActual() ya maneja el caso de sesión
      // vencida/401 (cierra sesión y redirige antes de llegar a este
      // catch: ver auth.js, lanza "Sesión expirada." / "Sesión no
      // válida."). Si el mensaje es otro, es un problema de
      // Backend/red, y ahí sí conviene avisar en vez de dejar la
      // navbar con "—" sin explicación.
      if (window.UI && err && err.message !== "Sesión expirada." && err.message !== "Sesión no válida.") {
        window.UI.toast("No se pudo cargar la información del usuario.", "warning");
      }
    }
  }

  async function inyectarLayout() {
    const app = document.getElementById("erpApp");
    if (!app) {
      console.error("layout.js: no se encontró #erpApp en esta página.");
      return;
    }

    try {
      const [sidebarHtml, navbarHtml, footerHtml] = await Promise.all([
        cargarComponente("sidebar.html"),
        cargarComponente("navbar.html"),
        cargarComponente("footer.html"),
      ]);

      const sidebarEl = primerElemento(sidebarHtml);
      const navbarEl = primerElemento(navbarHtml);
      const footerEl = primerElemento(footerHtml);

      document.body.insertBefore(sidebarEl, app);
      document.body.insertBefore(navbarEl, app);
      app.insertAdjacentElement("afterend", footerEl);
    } catch (err) {
      console.error(
        "layout.js: no se pudo cargar el menú lateral, la barra superior o el " +
          "pie de página (components/*.html). Si abriste esta página " +
          "directamente como archivo (file://), sírvela desde un servidor " +
          "local (por ejemplo: python -m http.server) para que el fetch de " +
          "components/*.html funcione.",
        err
      );
      // FASE F0: además del log en consola, se avisa visualmente con el
      // toast centralizado (ui-components.js) en vez de dejar la página
      // sin ningún indicio del error para el usuario.
      if (window.UI) {
        window.UI.toast("No se pudo cargar el menú del ERP. Revisa la consola o recarga la página.", "error");
      }
      return;
    }

    marcarLinkActivo();
    inicializarToggleSidebar();
    inicializarCerrarSesion();
    inicializarBuscadorGlobal();
    pintarFechaYAnio();
    pintarUsuarioNavbar();
  }

  function iniciar() {
    if (window.Auth) {
      const autenticado = window.Auth.requerirSesion();
      if (!autenticado) return; // requerirSesion() ya redirige a LOGIN_PATH.
      window.Auth.iniciarVigilanciaExpiracion();
    }
    inyectarLayout();
  }

  iniciar();
})();
