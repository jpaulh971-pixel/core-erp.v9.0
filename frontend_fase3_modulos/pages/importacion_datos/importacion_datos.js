/**
 * pages/importacion_datos/importacion_datos.js — Page-script del módulo
 * m21_importacion_datos (app/modules/m21_importacion_datos).
 *
 * FASE 1 (esta entrega): SOLO Frontend. Consume exactamente los endpoints
 * ya existentes en el Backend (contrato real: router.py + schemas.py), sin
 * tocar rutas, autenticación, lógica de negocio, modelos ni base de datos:
 *
 *   Saldo inicial (ETAPA 1):
 *     POST /api/importacion-datos/inventario-inicial/previsualizar
 *          ?inventario_id=<int>  (multipart: campo "archivo")
 *          -> CargaPreviewOut {carga_id, nombre_archivo, inventario_id,
 *             estado, total_filas, filas_validas, filas_con_error,
 *             errores:[{numero_fila, mensaje_error}]}
 *     GET  /api/importacion-datos/inventario-inicial            -> list[CargaOut]
 *     POST /api/importacion-datos/inventario-inicial/{id}/confirmar
 *          -> CargaConfirmarOut {carga_id, estado, filas_procesadas,
 *             filas_fallidas_en_confirmacion:[...]}
 *
 *   Compras / Ventas históricas (ETAPA 2, mismo contrato para ambas,
 *   solo cambia el segmento de la URL "compras"/"ventas"):
 *     POST /api/importacion-datos/{compras|ventas}/previsualizar?inventario_id=<int>
 *          -> Carga{Compras|Ventas}PreviewOut: igual que arriba + filas_historico
 *             + filas_operativo (clasificación HISTORICO/OPERATIVO por fila)
 *     GET  /api/importacion-datos/{compras|ventas}               -> list[...Out]
 *     POST /api/importacion-datos/{compras|ventas}/{id}/confirmar
 *          -> Carga{Compras|Ventas}ConfirmarOut: igual que Saldo Inicial +
 *             filas_historico_creadas + filas_operativas_creadas
 *
 *   Fecha de corte de inventario (usada por Compras/Ventas para clasificar
 *   HISTORICO/OPERATIVO cuando el Excel no trae la columna tipo_movimiento):
 *     GET /api/importacion-datos/{inventario_id}/fecha-corte
 *         -> 400 si no está configurada (validators.validar_corte_configurado);
 *            se trata como "no configurada" en la UI, no como error duro.
 *     PUT /api/importacion-datos/{inventario_id}/fecha-corte  body {fecha_corte}
 *
 *   El selector de almacén consume GET /api/inventario/inventarios
 *   (m03_inventario), ya usado por pages/inventario/inventario.js, para
 *   resolver `inventario_id` (obligatorio en todos los endpoints de arriba)
 *   sin pedirle al usuario que escriba un ID a mano.
 *
 * HALLAZGO DE CONTRATO / BLOQUEO REAL detectado antes de escribir el resto
 * de este archivo (documentado aquí, no en el Backend): api-client.js
 * (window.Api.request) fuerza `Content-Type: application/json` en toda
 * petición con `body` que no traiga ya un Content-Type propio. Eso rompe
 * un upload multipart (el navegador necesita fijar
 * `multipart/form-data; boundary=...` él mismo a partir de un FormData).
 * En vez de modificar ese archivo compartido por otras 18 páginas (fuera
 * del alcance de esta fase y con riesgo de regresión), este módulo define
 * su propio `apiPostArchivo()` más abajo -mismo criterio de manejo de
 * errores/401 que api-client.js, pero sin fijar Content-Type- y usa
 * `window.Api.request/get` sin cambios para el resto de llamadas (JSON).
 *
 * CargaPreviewOut/Carga{Compras|Ventas}PreviewOut NO devuelven el detalle
 * fila por fila del Excel (solo total_filas/filas_validas/filas_con_error
 * + la lista de errores): la "tabla con la información devuelta por el
 * Backend" de esta fase muestra exactamente eso (resumen numérico + tabla
 * de errores), sin inventar columnas ni adelantar la adaptación de
 * encabezados que corresponde a la Fase 2.
 */
(function () {
  const CONFIG = window.ERP_CONFIG;
  const U = window.Utils;

  const elError = document.getElementById("estadoError");
  const selectInventario = document.getElementById("selectInventario");
  const infoInventarioSeleccionado = document.getElementById("infoInventarioSeleccionado");

  let inventariosCache = [];
  let inventarioSeleccionadoId = null;

  function mostrarError(mensaje) {
    elError.textContent = mensaje;
    elError.style.display = "block";
  }
  function ocultarError() {
    elError.style.display = "none";
  }
  function mostrarErrorEn(el, mensaje) {
    el.textContent = mensaje;
    el.style.display = "block";
  }
  function ocultarErrorEn(el) {
    el.style.display = "none";
  }

  // ---------------------------------------------------------------------
  // Cliente API: JSON vía window.Api (sin cambios) + upload propio (ver
  // nota de cabecera) para los 3 endpoints de previsualizar (multipart).
  // ---------------------------------------------------------------------
  const apiGet = (path) => window.Api.request(path, { method: "GET" });
  const apiPost = (path, body) =>
    window.Api.request(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined });
  const apiPut = (path, body) =>
    window.Api.request(path, { method: "PUT", body: JSON.stringify(body) });

  async function extraerDetalle(resp) {
    let detalle = `HTTP ${resp.status}`;
    try {
      const datos = await resp.json();
      if (datos && datos.detail) {
        detalle = Array.isArray(datos.detail) ? datos.detail.map((d) => d.msg).join("; ") : datos.detail;
      }
    } catch (err) {
      /* sin cuerpo JSON */
    }
    return detalle;
  }

  async function apiPostArchivo(path, formData) {
    const token = window.Auth ? window.Auth.obtenerToken() : null;
    const headers = {};
    if (token) headers.Authorization = `Bearer ${token}`;

    let resp;
    try {
      resp = await fetch(`${CONFIG.API_BASE_URL}${path}`, { method: "POST", headers, body: formData });
    } catch (err) {
      const errorRed = new Error(
        `No se pudo conectar con el Backend (${CONFIG.API_BASE_URL}). Verifica que esté corriendo.`
      );
      errorRed.status = 0;
      throw errorRed;
    }

    if (resp.status === 401) {
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
    return resp.json();
  }

  // ---------------------------------------------------------------------
  // Selector de almacén (GET /api/inventario/inventarios)
  // ---------------------------------------------------------------------
  async function cargarInventarios() {
    selectInventario.innerHTML = `<option value="">Cargando almacenes…</option>`;
    try {
      inventariosCache = await apiGet("/api/inventario/inventarios");
      if (!inventariosCache.length) {
        selectInventario.innerHTML = `<option value="">No hay almacenes registrados</option>`;
        return;
      }
      selectInventario.innerHTML =
        `<option value="">Seleccionar…</option>` +
        inventariosCache
          .map((inv) => `<option value="${inv.id}">${U.escaparHtml(inv.codigo)} — ${U.escaparHtml(inv.nombre)}</option>`)
          .join("");
    } catch (err) {
      selectInventario.innerHTML = `<option value="">Error al cargar almacenes</option>`;
      mostrarError(err.message || "No se pudieron cargar los almacenes.");
      if (window.UI) window.UI.toast(err.message || "No se pudieron cargar los almacenes.", "error");
    }
  }

  function alCambiarInventario() {
    inventarioSeleccionadoId = selectInventario.value ? Number(selectInventario.value) : null;
    infoInventarioSeleccionado.textContent = inventarioSeleccionadoId
      ? "Almacén listo para importar."
      : "Selecciona un almacén para habilitar la importación.";
    [seccionSaldoInicial, seccionCompras, seccionVentas].forEach((s) => s.alCambiarInventario());
    cargarHistorial();
  }

  // ---------------------------------------------------------------------
  // Helpers de render compartidos por las 3 secciones de carga
  // ---------------------------------------------------------------------
  function colorEstadoCarga(estado) {
    if (estado === "PREVISUALIZADA") return "info";
    if (estado === "CON_ERRORES") return "warning";
    if (estado === "CONFIRMADA") return "success";
    return "secondary";
  }

  function renderStats(contenedorEl, items) {
    contenedorEl.innerHTML = items
      .map(
        (it) => `
        <div class="stat-box">
          <div class="stat-valor">${U.escaparHtml(String(it.valor))}</div>
          <div class="stat-etiqueta">${U.escaparHtml(it.etiqueta)}</div>
        </div>`
      )
      .join("");
  }

  function renderErrores(bloqueEl, tbodyEl, errores) {
    if (!errores || !errores.length) {
      bloqueEl.style.display = "none";
      tbodyEl.innerHTML = "";
      return;
    }
    bloqueEl.style.display = "block";
    tbodyEl.innerHTML = errores
      .map((e) => `<tr class="table-danger"><td>${U.escaparHtml(String(e.numero_fila))}</td><td>${U.escaparHtml(e.mensaje_error)}</td></tr>`)
      .join("");
  }

  // ---------------------------------------------------------------------
  // Factoría de controlador para una sección de carga (Saldo Inicial /
  // Compras / Ventas). `segmento` es el tramo de URL del Backend
  // ("inventario-inicial" | "compras" | "ventas"). `conModoCarga` agrega
  // el manejo de filas_historico/filas_operativo (solo Compras/Ventas).
  // ---------------------------------------------------------------------
  function crearSeccionCarga(cfg) {
    const inputArchivo = document.getElementById(cfg.idInputArchivo);
    const btnPrevisualizar = document.getElementById(cfg.idBtnPrevisualizar);
    const errorEl = document.getElementById(cfg.idError);
    const resumenEl = document.getElementById(cfg.idResumen);
    const statsEl = document.getElementById(cfg.idStats);
    const bloqueErroresEl = document.getElementById(cfg.idBloqueErrores);
    const tbodyErroresEl = document.getElementById(cfg.idTbodyErrores);
    const btnConfirmar = document.getElementById(cfg.idBtnConfirmar);
    const notaConfirmarEl = document.getElementById(cfg.idNotaConfirmar);
    const resultadoConfirmEl = document.getElementById(cfg.idResultadoConfirm);

    let cargaActual = null; // último CargaPreviewOut/CargaOut relevante

    function alCambiarInventario() {
      inputArchivo.value = "";
      resumenEl.style.display = "none";
      resultadoConfirmEl.style.display = "none";
      ocultarErrorEn(errorEl);
      cargaActual = null;
    }

    function pintarResumen(preview) {
      cargaActual = preview;
      resumenEl.style.display = "block";
      resultadoConfirmEl.style.display = "none";

      const items = [
        { etiqueta: "Archivo", valor: preview.nombre_archivo },
        { etiqueta: "Estado", valor: preview.estado },
        { etiqueta: "Total de filas", valor: preview.total_filas },
        { etiqueta: "Filas válidas", valor: preview.filas_validas },
        { etiqueta: "Filas con error", valor: preview.filas_con_error },
      ];
      if (cfg.conModoCarga) {
        items.push(
          { etiqueta: "Histórico", valor: preview.filas_historico },
          { etiqueta: "Operativo", valor: preview.filas_operativo }
        );
      }
      // Costo 0 es válido (ej. muestras gratuitas), por eso NO cuenta como
      // error ni bloquea la importación — pero si el Excel simplemente no
      // traía el costo, esas filas entrarán sin sumar valor a "Valor
      // Inventario", así que se avisa aparte para que sea una decisión
      // consciente y no un dato faltante que pasó desapercibido.
      if (cfg.conCostoCero && preview.filas_costo_cero > 0) {
        items.push({ etiqueta: "Filas con costo 0", valor: preview.filas_costo_cero });
      }
      renderStats(statsEl, items);
      renderErrores(bloqueErroresEl, tbodyErroresEl, preview.errores);

      btnConfirmar.disabled = false;
      let nota =
        preview.filas_validas > 0
          ? `Se procesarán las ${preview.filas_validas} fila(s) válida(s). Las filas con error se omiten.`
          : "No hay filas válidas para confirmar en este archivo.";
      if (cfg.conCostoCero && preview.filas_costo_cero > 0) {
        nota += ` Atención: ${preview.filas_costo_cero} de esas filas tienen costo unitario 0 (no sumarán valor al inventario salvo que sea intencional, ej. muestras gratuitas).`;
      }
      notaConfirmarEl.textContent = nota;
      if (preview.filas_validas === 0) btnConfirmar.disabled = true;
    }

    async function previsualizar() {
      ocultarErrorEn(errorEl);
      if (!inventarioSeleccionadoId) {
        mostrarErrorEn(errorEl, "Selecciona primero un almacén.");
        return;
      }
      const archivo = inputArchivo.files && inputArchivo.files[0];
      if (!archivo) {
        mostrarErrorEn(errorEl, "Selecciona un archivo Excel (.xlsx o .xls).");
        return;
      }

      const formData = new FormData();
      formData.append("archivo", archivo);

      if (window.UI) window.UI.mostrarCargando();
      btnPrevisualizar.disabled = true;
      try {
        const preview = await apiPostArchivo(
          `/api/importacion-datos/${cfg.segmento}/previsualizar?inventario_id=${inventarioSeleccionadoId}`,
          formData
        );
        pintarResumen(preview);
        const mensaje =
          preview.filas_con_error > 0
            ? `Vista previa lista: ${preview.filas_validas} fila(s) válida(s), ${preview.filas_con_error} con error.`
            : `Vista previa lista: ${preview.filas_validas} fila(s) válida(s), sin errores.`;
        if (window.UI) window.UI.toast(mensaje, preview.filas_con_error > 0 ? "warning" : "success");
      } catch (err) {
        mostrarErrorEn(errorEl, err.message || "No se pudo previsualizar el archivo.");
        if (window.UI) window.UI.toast(err.message || "No se pudo previsualizar el archivo.", "error");
      } finally {
        btnPrevisualizar.disabled = false;
        if (window.UI) window.UI.ocultarCargando();
      }
    }

    function pintarResultadoConfirmacion(resultado) {
      resultadoConfirmEl.style.display = "block";
      const filasFallidas = resultado.filas_fallidas_en_confirmacion || [];
      let extra = "";
      if (cfg.conModoCarga) {
        extra = `
          <div>Filas históricas creadas: <b>${U.escaparHtml(String(resultado.filas_historico_creadas))}</b></div>
          <div>Filas operativas creadas: <b>${U.escaparHtml(String(resultado.filas_operativas_creadas))}</b></div>`;
      }
      resultadoConfirmEl.innerHTML = `
        <div class="alert alert-success mb-2">
          <i class="bi bi-check-circle-fill me-1"></i>Importación confirmada. Estado: <b>${U.escaparHtml(resultado.estado)}</b>.
        </div>
        <div class="mb-2">
          <div>Filas procesadas: <b>${U.escaparHtml(String(resultado.filas_procesadas))}</b></div>
          ${extra}
        </div>
        ${
          filasFallidas.length
            ? `<div class="card-header-erp mb-0"><i class="bi bi-exclamation-triangle me-1"></i>Filas que fallaron al confirmar</div>
               <div class="table-responsive-erp mb-2">
                 <table class="table-erp"><thead><tr><th style="width:110px;">Fila</th><th>Detalle</th></tr></thead>
                 <tbody>${filasFallidas
                   .map((e) => `<tr class="table-danger"><td>${U.escaparHtml(String(e.numero_fila))}</td><td>${U.escaparHtml(e.mensaje_error)}</td></tr>`)
                   .join("")}</tbody></table>
               </div>`
            : ""
        }`;
    }

    async function confirmar() {
      if (!cargaActual) return;
      const confirmado = window.UI
        ? await window.UI.confirmar({
            titulo: "Confirmar importación",
            mensaje: `¿Confirmas la importación de "${cargaActual.nombre_archivo}"? Se crearán los registros a partir de las filas válidas. Esta acción no se puede deshacer.`,
            textoAceptar: "Confirmar importación",
            variante: "primary",
          })
        : true;
      if (!confirmado) return;

      if (window.UI) window.UI.mostrarCargando();
      btnConfirmar.disabled = true;
      try {
        const resultado = await apiPost(`/api/importacion-datos/${cfg.segmento}/${cargaActual.carga_id}/confirmar`);
        pintarResultadoConfirmacion(resultado);
        if (window.UI) window.UI.toast(`Importación confirmada: ${resultado.filas_procesadas} fila(s) procesada(s).`, "success");
        cargaActual = null;
        notaConfirmarEl.textContent = "Esta carga ya fue confirmada.";
        await cargarHistorial();
      } catch (err) {
        mostrarErrorEn(errorEl, err.message || "No se pudo confirmar la importación.");
        if (window.UI) window.UI.toast(err.message || "No se pudo confirmar la importación.", "error");
        btnConfirmar.disabled = false;
      } finally {
        if (window.UI) window.UI.ocultarCargando();
      }
    }

    btnPrevisualizar.addEventListener("click", previsualizar);
    btnConfirmar.addEventListener("click", confirmar);
    btnConfirmar.disabled = true;

    return { alCambiarInventario };
  }

  const seccionSaldoInicial = crearSeccionCarga({
    segmento: "inventario-inicial",
    conModoCarga: false,
    conCostoCero: true,
    idInputArchivo: "inputArchivoSaldoInicial",
    idBtnPrevisualizar: "btnPrevisualizarSaldoInicial",
    idError: "errorSaldoInicial",
    idResumen: "resumenSaldoInicial",
    idStats: "statsSaldoInicial",
    idBloqueErrores: "bloqueErroresSaldoInicial",
    idTbodyErrores: "tbodyErroresSaldoInicial",
    idBtnConfirmar: "btnConfirmarSaldoInicial",
    idNotaConfirmar: "notaConfirmarSaldoInicial",
    idResultadoConfirm: "resultadoConfirmSaldoInicial",
  });

  const seccionCompras = crearSeccionCarga({
    segmento: "compras",
    conModoCarga: true,
    idInputArchivo: "inputArchivoCompras",
    idBtnPrevisualizar: "btnPrevisualizarCompras",
    idError: "errorCompras",
    idResumen: "resumenCompras",
    idStats: "statsCompras",
    idBloqueErrores: "bloqueErroresCompras",
    idTbodyErrores: "tbodyErroresCompras",
    idBtnConfirmar: "btnConfirmarCompras",
    idNotaConfirmar: "notaConfirmarCompras",
    idResultadoConfirm: "resultadoConfirmCompras",
  });

  const seccionVentas = crearSeccionCarga({
    segmento: "ventas",
    conModoCarga: true,
    idInputArchivo: "inputArchivoVentas",
    idBtnPrevisualizar: "btnPrevisualizarVentas",
    idError: "errorVentas",
    idResumen: "resumenVentas",
    idStats: "statsVentas",
    idBloqueErrores: "bloqueErroresVentas",
    idTbodyErrores: "tbodyErroresVentas",
    idBtnConfirmar: "btnConfirmarVentas",
    idNotaConfirmar: "notaConfirmarVentas",
    idResultadoConfirm: "resultadoConfirmVentas",
  });

  // ---------------------------------------------------------------------
  // Fecha de corte de inventario (Compras y Ventas comparten el mismo
  // registro por inventario_id: PUT/GET /api/importacion-datos/{id}/fecha-corte)
  // ---------------------------------------------------------------------
  function crearControladorCorte(idInput, idBoton, idNota) {
    const input = document.getElementById(idInput);
    const boton = document.getElementById(idBoton);
    const nota = document.getElementById(idNota);
    const notaBase = nota.textContent;

    async function cargar() {
      input.value = "";
      if (!inventarioSeleccionadoId) return;
      try {
        const corte = await apiGet(`/api/importacion-datos/${inventarioSeleccionadoId}/fecha-corte`);
        // <input type="datetime-local"> espera "YYYY-MM-DDTHH:mm" en hora local.
        const fecha = new Date(corte.fecha_corte);
        if (!Number.isNaN(fecha.getTime())) {
          const pad = (n) => String(n).padStart(2, "0");
          input.value = `${fecha.getFullYear()}-${pad(fecha.getMonth() + 1)}-${pad(fecha.getDate())}T${pad(fecha.getHours())}:${pad(fecha.getMinutes())}`;
        }
        nota.textContent = `Fecha de corte configurada: ${U.formatearFechaHora(corte.fecha_corte)}. ${notaBase}`;
      } catch (err) {
        // El Backend devuelve 400 cuando no hay corte configurado para este
        // inventario (validators.validar_corte_configurado): no es un error
        // de conexión, es un estado válido ("aún no configurada").
        nota.textContent = `Sin fecha de corte configurada todavía. ${notaBase}`;
      }
    }

    async function guardar() {
      if (!inventarioSeleccionadoId) {
        if (window.UI) window.UI.toast("Selecciona primero un almacén.", "warning");
        return;
      }
      if (!input.value) {
        if (window.UI) window.UI.toast("Selecciona una fecha de corte.", "warning");
        return;
      }
      if (window.UI) window.UI.mostrarCargando();
      try {
        const fechaIso = new Date(input.value).toISOString();
        const corte = await apiPut(`/api/importacion-datos/${inventarioSeleccionadoId}/fecha-corte`, { fecha_corte: fechaIso });
        nota.textContent = `Fecha de corte configurada: ${U.formatearFechaHora(corte.fecha_corte)}. ${notaBase}`;
        if (window.UI) window.UI.toast("Fecha de corte guardada.", "success");
      } catch (err) {
        if (window.UI) window.UI.toast(err.message || "No se pudo guardar la fecha de corte.", "error");
      } finally {
        if (window.UI) window.UI.ocultarCargando();
      }
    }

    boton.addEventListener("click", guardar);
    return { cargar };
  }

  const corteCompras = crearControladorCorte("inputFechaCorteCompras", "btnGuardarFechaCorteCompras", "notaFechaCorteCompras");
  const corteVentas = crearControladorCorte("inputFechaCorteVentas", "btnGuardarFechaCorteVentas", "notaFechaCorteVentas");

  // ---------------------------------------------------------------------
  // Historial de Importaciones: combina los 3 listados existentes
  // (no hay un endpoint único de "historial" en el Backend).
  // ---------------------------------------------------------------------
  const selectTipoHistorial = document.getElementById("selectTipoHistorial");
  const checkSoloEsteAlmacen = document.getElementById("checkSoloEsteAlmacen");
  const btnActualizarHistorial = document.getElementById("btnActualizarHistorial");
  const tbodyHistorial = document.getElementById("tbodyHistorial");
  const errorHistorial = document.getElementById("errorHistorial");

  const ETIQUETA_TIPO = { SALDO_INICIAL: "Saldo Inicial", COMPRAS: "Compras", VENTAS: "Ventas" };
  const SEGMENTO_TIPO = { SALDO_INICIAL: "inventario-inicial", COMPRAS: "compras", VENTAS: "ventas" };

  function nombreAlmacen(inventarioId) {
    const inv = inventariosCache.find((x) => x.id === inventarioId);
    return inv ? `${inv.codigo} — ${inv.nombre}` : `#${inventarioId}`;
  }

  async function cargarHistorial() {
    ocultarErrorEn(errorHistorial);
    if (!inventarioSeleccionadoId && checkSoloEsteAlmacen.checked) {
      tbodyHistorial.innerHTML = `<tr><td colspan="9" class="text-muted-erp">Selecciona un almacén…</td></tr>`;
      return;
    }
    tbodyHistorial.innerHTML = `<tr><td colspan="9" class="text-muted-erp">Cargando…</td></tr>`;
    try {
      const [saldoInicial, compras, ventas] = await Promise.all([
        apiGet("/api/importacion-datos/inventario-inicial"),
        apiGet("/api/importacion-datos/compras"),
        apiGet("/api/importacion-datos/ventas"),
      ]);
      let filas = [
        ...saldoInicial.map((c) => ({ ...c, tipo: "SALDO_INICIAL" })),
        ...compras.map((c) => ({ ...c, tipo: "COMPRAS" })),
        ...ventas.map((c) => ({ ...c, tipo: "VENTAS" })),
      ];

      if (checkSoloEsteAlmacen.checked && inventarioSeleccionadoId) {
        filas = filas.filter((c) => c.inventario_id === inventarioSeleccionadoId);
      }
      if (selectTipoHistorial.value) {
        filas = filas.filter((c) => c.tipo === selectTipoHistorial.value);
      }
      filas.sort((a, b) => new Date(b.creado_en) - new Date(a.creado_en));

      if (!filas.length) {
        tbodyHistorial.innerHTML = `<tr><td colspan="9" class="text-muted-erp">Sin cargas registradas todavía.</td></tr>`;
        return;
      }

      tbodyHistorial.innerHTML = filas
        .map(
          (c) => `
        <tr>
          <td>${U.escaparHtml(ETIQUETA_TIPO[c.tipo])}</td>
          <td>${U.escaparHtml(c.nombre_archivo)}</td>
          <td>${U.escaparHtml(nombreAlmacen(c.inventario_id))}</td>
          <td><span class="badge text-bg-${colorEstadoCarga(c.estado)}">${U.escaparHtml(c.estado)}</span></td>
          <td class="text-end">${U.escaparHtml(String(c.total_filas))}</td>
          <td class="text-end">${U.escaparHtml(String(c.filas_validas))}</td>
          <td class="text-end">${U.escaparHtml(String(c.filas_con_error))}</td>
          <td>${U.formatearFechaHora(c.creado_en)}</td>
          <td>${c.confirmado_en ? U.formatearFechaHora(c.confirmado_en) : "—"}</td>
        </tr>`
        )
        .join("");
    } catch (err) {
      tbodyHistorial.innerHTML = `<tr><td colspan="9" class="text-muted-erp">No se pudo cargar el historial.</td></tr>`;
      mostrarErrorEn(errorHistorial, err.message || "No se pudo cargar el historial de importaciones.");
      if (window.UI) window.UI.toast(err.message || "No se pudo cargar el historial de importaciones.", "error");
    }
  }

  // ---------------------------------------------------------------------
  // Arranque
  // ---------------------------------------------------------------------
  function iniciar() {
    if (!CONFIG || !window.Auth) return;
    if (!window.Auth.haySesion()) return; // layout.js ya redirige a login.html.

    selectInventario.addEventListener("change", () => {
      alCambiarInventario();
      corteCompras.cargar();
      corteVentas.cargar();
    });
    selectTipoHistorial.addEventListener("change", cargarHistorial);
    checkSoloEsteAlmacen.addEventListener("change", cargarHistorial);
    btnActualizarHistorial.addEventListener("click", cargarHistorial);

    // Cargar la fecha de corte también al entrar por primera vez a cada
    // pestaña (por si el usuario cambia de pestaña antes de tocar el
    // selector de almacén).
    document.getElementById("tabBtnCompras").addEventListener("shown.bs.tab", () => corteCompras.cargar());
    document.getElementById("tabBtnVentas").addEventListener("shown.bs.tab", () => corteVentas.cargar());

    cargarInventarios();
    cargarHistorial();
  }

  iniciar();
})();
