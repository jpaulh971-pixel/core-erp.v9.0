/**
 * pages/inteligencia_comercial/inteligencia_comercial.js — Page-script del
 * módulo m13_inteligencia_comercial (app/modules/m13_inteligencia_comercial).
 *
 * Endpoints (contrato real: router.py + schemas.py del módulo, todos con
 * Bearer y de solo lectura):
 *   GET /api/inteligencia-comercial/productos-mas-vendidos?limit&desde&hasta
 *     -> list[ProductoMasVendido{producto_id, codigo, nombre,
 *        cantidad_vendida, monto_vendido}]
 *   GET /api/inteligencia-comercial/clientes-top?limit&desde&hasta
 *     -> list[ClienteTop{cliente_id, ruc, razon_social, monto_comprado,
 *        cantidad_ordenes}]
 *   GET /api/inteligencia-comercial/rotacion-inventario (sin parámetros)
 *     -> list[RotacionProducto{producto_id, codigo, nombre,
 *        cantidad_vendida_historica, stock_actual, indice_rotacion,
 *        sin_movimiento}]
 *
 * `desde`/`hasta` filtran por fecha de despacho y solo aplican a
 * productos-mas-vendidos y clientes-top (rotacion-inventario no acepta
 * parámetros en el Backend, así que se recarga igual pero sin filtros).
 * `limit` es el mismo parámetro `limit` del Backend (Query gt=0, le=100).
 * No se inventan métricas ni endpoints: solo se pinta lo que el Backend
 * ya devuelve.
 *
 * FASE F9 — Verificación de contrato y limitaciones documentadas:
 * - Solo existen los 3 GET listados arriba en `m13_inteligencia_comercial`.
 *   No hay ningún endpoint de escritura (POST/PUT/DELETE) en este módulo:
 *   es 100% de solo lectura, por lo que no corresponde `UI.confirmar()`
 *   (no hay ninguna acción que modifique información).
 * - No existe ningún endpoint de exportación a Excel/PDF en este módulo
 *   ni en ningún otro módulo del proyecto (verificado en F8 sobre los 18
 *   módulos de `pages/`, y reconfirmado aquí). No se agregan botones de
 *   exportar.
 * - Los únicos filtros que el Backend admite son `desde`, `hasta` (solo
 *   para productos-mas-vendidos y clientes-top) y `limit` (Query
 *   `gt=0, le=100`, ya acotado en el `<select>` a 5/10/20/50). No se
 *   agregan filtros de Cliente, Producto, Categoría ni Estado porque el
 *   Backend no los admite en ninguno de los 3 endpoints de este módulo.
 * - `rotacion-inventario` no acepta ningún parámetro: es una foto actual
 *   de la rotación, igual que `inventario-valorizado` en
 *   `pages/reportes/reportes.js`.
 * - F9 agrega la integración de `UI.toast()`/`UI.mostrarCargando()`/
 *   `UI.ocultarCargando()` (ausente hasta ahora en este módulo), cantidad
 *   de registros por tabla y validación de rango de fechas, sin tocar
 *   ningún endpoint ni inventar ningún filtro/KPI/gráfico nuevo.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const elError = document.getElementById("estadoError");
  const inputDesde = document.getElementById("filtroDesde");
  const inputHasta = document.getElementById("filtroHasta");
  const selectLimit = document.getElementById("filtroLimit");
  const btnAplicar = document.getElementById("btnAplicarFiltros");

  function mostrarError(mensaje) {
    elError.textContent = mensaje;
    elError.style.display = "block";
  }

  function ocultarError() {
    elError.style.display = "none";
  }

  async function apiGet(path, params) {
    // FASE F0: delega en el cliente API centralizado (api-client.js).
    return window.Api.get(path, params);
  }

  function filtrosFecha() {
    return { desde: inputDesde.value || undefined, hasta: inputHasta.value || undefined };
  }

  function filaVacia(colspan, texto) {
    return `<tr><td colspan="${colspan}" class="text-muted-erp">${texto}</td></tr>`;
  }

  function marcarInvalido(input, invalido) {
    input.classList.toggle("is-invalid", !!invalido);
  }

  // Validación en el cliente: ambas fechas son opcionales, pero si están
  // las dos, "Desde" no puede ser posterior a "Hasta". `limit` no se
  // valida aquí porque ya es un <select> acotado a los valores permitidos
  // por el Backend (5/10/20/50, dentro del rango gt=0,le=100).
  function filtrosValidos() {
    marcarInvalido(inputDesde, false);
    marcarInvalido(inputHasta, false);

    const desde = inputDesde.value;
    const hasta = inputHasta.value;

    if (desde && hasta && desde > hasta) {
      marcarInvalido(inputDesde, true);
      marcarInvalido(inputHasta, true);
      const mensaje = "La fecha 'Desde' no puede ser posterior a la fecha 'Hasta'.";
      mostrarError(mensaje);
      if (window.UI) window.UI.toast(mensaje, "error");
      return false;
    }
    return true;
  }

  async function cargarProductosMasVendidos() {
    const filas = await apiGet("/api/inteligencia-comercial/productos-mas-vendidos", {
      ...filtrosFecha(),
      limit: selectLimit.value,
    });
    const tbody = document.getElementById("tbodyProductosTop");
    tbody.innerHTML = filas.length
      ? filas
          .map(
            (p) => `
        <tr>
          <td><code>${U.escaparHtml(p.codigo)}</code></td>
          <td>${U.escaparHtml(p.nombre)}</td>
          <td class="text-end">${U.formatearNumero(p.cantidad_vendida, 2)}</td>
          <td class="text-end">${U.formatearMoneda(p.monto_vendido)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(4, "Sin ventas despachadas en el periodo.");
    document.getElementById("countProductosTop").textContent = `(${U.formatearNumero(filas.length)})`;
  }

  async function cargarClientesTop() {
    const filas = await apiGet("/api/inteligencia-comercial/clientes-top", {
      ...filtrosFecha(),
      limit: selectLimit.value,
    });
    const tbody = document.getElementById("tbodyClientesTop");
    tbody.innerHTML = filas.length
      ? filas
          .map(
            (c) => `
        <tr>
          <td><code>${U.escaparHtml(c.ruc)}</code></td>
          <td>${U.escaparHtml(c.razon_social)}</td>
          <td class="text-end">${U.formatearMoneda(c.monto_comprado)}</td>
          <td class="text-end">${U.formatearNumero(c.cantidad_ordenes)}</td>
        </tr>`
          )
          .join("")
      : filaVacia(4, "Sin clientes con compras en el periodo.");
    document.getElementById("countClientesTop").textContent = `(${U.formatearNumero(filas.length)})`;
  }

  // No acepta desde/hasta/limit en el Backend: es una foto de la
  // rotación actual. Se recarga junto con el resto por simplicidad,
  // igual que inventario-valorizado en pages/reportes/reportes.js.
  async function cargarRotacionInventario() {
    const filas = await apiGet("/api/inteligencia-comercial/rotacion-inventario");
    const tbody = document.getElementById("tbodyRotacion");
    tbody.innerHTML = filas.length
      ? filas
          .map((r) => {
            const indice =
              r.indice_rotacion === null || r.indice_rotacion === undefined
                ? "—"
                : U.formatearNumero(r.indice_rotacion, 2);
            const estadoBadge = r.sin_movimiento
              ? '<span class="badge text-bg-danger">Sin movimiento</span>'
              : '<span class="badge text-bg-success">Con movimiento</span>';
            return `
        <tr class="${r.sin_movimiento ? "table-danger" : ""}">
          <td><code>${U.escaparHtml(r.codigo)}</code></td>
          <td>${U.escaparHtml(r.nombre)}</td>
          <td class="text-end">${U.formatearNumero(r.cantidad_vendida_historica, 2)}</td>
          <td class="text-end">${U.formatearNumero(r.stock_actual, 2)}</td>
          <td class="text-end">${indice}</td>
          <td>${estadoBadge}</td>
        </tr>`;
          })
          .join("")
      : filaVacia(6, "No hay productos registrados en inventario.");
    document.getElementById("countRotacion").textContent = `(${U.formatearNumero(filas.length)})`;
  }

  async function cargarTodo() {
    ocultarError();
    if (!filtrosValidos()) return; // Rango de fechas inconsistente: no se envía ninguna solicitud.

    btnAplicar.disabled = true;
    if (window.UI) window.UI.mostrarCargando();
    try {
      await Promise.all([
        cargarProductosMasVendidos(),
        cargarClientesTop(),
        cargarRotacionInventario(),
      ]);
    } catch (err) {
      mostrarError(err.message || "Ocurrió un error al cargar la inteligencia comercial.");
      if (window.UI) window.UI.toast(err.message || "Ocurrió un error al cargar la inteligencia comercial.", "error");
    } finally {
      btnAplicar.disabled = false;
      if (window.UI) window.UI.ocultarCargando();
    }
  }

  function iniciar() {
    if (!CONFIG || !window.Auth) return; // config.js/auth.js no cargados: nada que hacer.
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    btnAplicar.addEventListener("click", cargarTodo);
    [inputDesde, inputHasta].forEach((input) =>
      input.addEventListener("change", () => {
        marcarInvalido(inputDesde, false);
        marcarInvalido(inputHasta, false);
      })
    );
    cargarTodo();
  }

  iniciar();
})();
