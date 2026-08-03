"""FASE 2 (dry_run) — Reconstruccion de Kardex historico faltante.

Alcance de ESTA entrega (segun lo acordado): SOLO calcula y reporta. No
escribe nada en la base de datos. No existe bandera --aplicar en este
archivo a proposito.

CAUSA RAIZ (confirmada leyendo el codigo, ver detalle en el archivo de
entrega adjunto):
    app/modules/m21_importacion_datos/service.py, funciones
    `_procesar_fila_venta` (ventas) y `_procesar_fila_compra` (compras).
    Para toda fila con modo_carga == "HISTORICO", el estado final
    (DESPACHADA / RECIBIDA) se fuerza directo por repository, SIN pasar
    por `ventas_service.despachar_orden()` / `compras_service.recibir_orden()`
    -- las unicas funciones que llaman a m03_inventario (registrar_salida /
    registrar_ingreso), que son las que crean Lote y MovimientoKardex.
    Resultado: ninguna venta ni compra HISTORICO tiene Kardex, por diseno
    del importador (no es un bug puntual de una orden). El costo si quedo
    guardado en OrdenCompraItem.costo_unitario (viene del Excel), y es el
    que reutilizamos aqui sin recalcular landed cost (m08_costos).

QUE HACE:
-----------------------------------------------------------------------
1. Ubica items de OrdenVenta con estado="DESPACHADA", originados en una
   fila de CargaVentasHistoricoFila con modo_carga="HISTORICO" y
   procesada=True, cuyo `despachado_en` cae en --anio, y que NO tienen
   ningun MovimientoKardex con referencia =
   `_referencia_despacho_item(orden_id, item_id)` (misma funcion que ya
   usa m10_ventas/service.py, importada tal cual, sin modificarla).

2. Para cada item afectado cuyo producto NO es perecible, arma un pool
   PEPS (mas antiguo primero, por OrdenCompra.recibido_en) de
   OrdenCompraItem de compras HISTORICO del MISMO producto_id +
   MISMO inventario (OrdenCompra.inventario_destino_id ==
   OrdenVenta.inventario_salida_id), tambien sin Kardex propio.

   Items de producto perecible quedan EXCLUIDOS (estado
   EXCLUIDO_PERECIBLE): crear un Lote real exige fecha_vencimiento, dato
   que el Excel de compras historico no trae. Requieren decision manual
   (fuera de este script).

3. Simula el consumo PEPS del item contra ese pool y calcula el PLAN
   fisico exacto que se ejecutaria en la fase de aplicacion (que NO esta
   incluida en esta entrega):

   a) Lote — uno por cada OrdenCompra usada como origen. codigo_lote
      deterministico "HIST-OC-{orden_compra_id}" (idempotente: si ya
      existe un Lote con ese codigo, se reutiliza su cantidad_actual en
      vez de planificar uno duplicado). cantidad_inicial = cantidad TOTAL
      de esa OrdenCompraItem (el lote representa la compra completa,
      igual que un ingreso real). costo_unitario = OrdenCompraItem.costo_unitario
      tal cual. fecha_ingreso = OrdenCompra.recibido_en.

   b) MovimientoKardex INGRESO — uno por cada Lote de (a), misma
      cantidad/costo/fecha, referencia =
      "Reconstruccion historica - Orden compra #<id>".

   c) MovimientoKardex SALIDA — uno por cada porcion PEPS consumida
      (puede haber varias por item si cruza mas de una compra), con la
      MISMA referencia que ya usa el flujo real de despacho
      (`_referencia_despacho_item`, importada de m10_ventas/service.py
      sin tocarla). Con esto, en cuanto exista el Kardex, el costo que
      YA expone `ventas_service.obtener_orden()` / `listar_ordenes()`
      (que lee por esa misma referencia) empieza a resolverse solo, sin
      modificar una sola linea de m10_ventas ni de frontend.

Items sin ninguna compra HISTORICO de respaldo quedan SIN_RESPALDO
(listados, no se planifica nada para ellos). Items con cobertura parcial
quedan PARCIAL_PLANIFICADO (se planifica lo que si tiene respaldo; el
resto queda documentado en observaciones).

Este script SOLO LEE la base de datos (no hay session.add / commit / flush
en ningun punto). Usa la misma DATABASE_URL que ya usa el backend
(app/config.py via app/database.py); no hardcodea ninguna cadena de
conexion.

Uso:
    cd backend
    python -m scripts.reconstruccion_kardex_historico_2026 --anio 2026
    python -m scripts.reconstruccion_kardex_historico_2026 --anio 2026 --inventario-id 1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app.modules.m02_productos.models import Producto  # noqa: E402
from app.modules.m03_inventario.models import Lote, MovimientoKardex  # noqa: E402
from app.modules.m04_compras.models import OrdenCompra, OrdenCompraItem  # noqa: E402
from app.modules.m10_ventas.models import OrdenVenta, OrdenVentaItem  # noqa: E402
from app.modules.m10_ventas.service import _referencia_despacho_item  # noqa: E402
from app.modules.m21_importacion_datos.models import (  # noqa: E402
    CargaComprasHistoricoFila,
    CargaVentasHistoricoFila,
)

REFERENCIA_INGRESO_RECONSTRUIDO = "Reconstruccion historica - Orden compra #{orden_compra_id}"
CODIGO_LOTE_RECONSTRUIDO = "HIST-OC-{orden_compra_id}"


# --------------------------------------------------------------------
# Estructuras del plan (solo en memoria / reporte, nunca se persisten)
# --------------------------------------------------------------------


@dataclass
class LotePlaneado:
    orden_compra_id: int
    producto_id: int
    inventario_id: int
    codigo_lote: str
    cantidad_inicial: float
    costo_unitario: float
    fecha_ingreso: str | None
    ya_existe: bool
    cantidad_disponible_para_plan: float  # lo que este plan puede seguir consumiendo
    cantidad_actual_existente: float | None = None


@dataclass
class MovimientoIngresoPlaneado:
    orden_compra_id: int
    codigo_lote: str
    cantidad: float
    costo_unitario: float
    fecha: str | None
    referencia: str
    ya_existe: bool


@dataclass
class MovimientoSalidaPlaneado:
    orden_venta_id: int
    item_id: int
    codigo_lote_origen: str
    orden_compra_id_origen: int
    cantidad: float
    costo_unitario: float
    fecha: str | None
    referencia: str


@dataclass
class ItemPlan:
    orden_venta_id: int
    item_id: int
    numero_orden_externo: str | None
    factura: str | None
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    producto_perecible: bool
    cantidad_vendida: float
    precio_unitario_venta: float
    fecha_venta: str | None
    estado: str  # PLANIFICADO | PARCIAL_PLANIFICADO | SIN_RESPALDO | EXCLUIDO_PERECIBLE | YA_TIENE_KARDEX
    costo_unitario_resultante: float | None = None
    margen_resultante: float | None = None
    margen_pct_resultante: float | None = None
    salidas: list[MovimientoSalidaPlaneado] = field(default_factory=list)
    observaciones: list[str] = field(default_factory=list)


# --------------------------------------------------------------------
# Deteccion: items de venta HISTORICO 2026 sin Kardex propio
# --------------------------------------------------------------------


def ubicar_ventas_historico_sin_kardex(db, anio: int | None, inventario_id: int | None):
    """anio=None (uso interno, solo para el guardia de seguridad de
    aplicar_reconstruccion_kardex_historico_2026.py): no filtra por año,
    devuelve el universo COMPLETO de ventas HISTORICO sin Kardex. El uso
    normal (dry-run y aplicacion por año) sigue pasando un anio explicito
    y el comportamiento no cambia."""
    q = (
        db.query(OrdenVenta, OrdenVentaItem)
        .join(OrdenVentaItem, OrdenVentaItem.orden_venta_id == OrdenVenta.id)
        .join(CargaVentasHistoricoFila, CargaVentasHistoricoFila.orden_venta_id == OrdenVenta.id)
        .filter(CargaVentasHistoricoFila.modo_carga == "HISTORICO")
        .filter(CargaVentasHistoricoFila.procesada.is_(True))
        .filter(OrdenVenta.estado == "DESPACHADA")
    )
    if inventario_id is not None:
        q = q.filter(OrdenVenta.inventario_salida_id == inventario_id)

    resultado = []
    for orden, item in q.all():
        fecha = orden.despachado_en
        if fecha is None:
            continue
        if anio is not None and fecha.year != anio:
            continue
        referencia = _referencia_despacho_item(orden.id, item.id)
        existe_kardex = (
            db.query(MovimientoKardex.id)
            .filter(MovimientoKardex.referencia == referencia)
            .first()
        )
        if existe_kardex is not None:
            continue  # ya tiene Kardex, fuera del alcance de esta reconstruccion
        resultado.append((orden, item, referencia))

    resultado.sort(key=lambda t: (t[0].despachado_en, t[0].id, t[1].id))
    return resultado


# --------------------------------------------------------------------
# Pool PEPS de compras HISTORICO (por producto_id + inventario_id)
# --------------------------------------------------------------------


def construir_pool_compras_historico(db, producto_id: int, inventario_id: int):
    q = (
        db.query(OrdenCompra, OrdenCompraItem)
        .join(OrdenCompraItem, OrdenCompraItem.orden_compra_id == OrdenCompra.id)
        .join(CargaComprasHistoricoFila, CargaComprasHistoricoFila.orden_compra_id == OrdenCompra.id)
        .filter(CargaComprasHistoricoFila.modo_carga == "HISTORICO")
        .filter(CargaComprasHistoricoFila.procesada.is_(True))
        .filter(OrdenCompra.estado == "RECIBIDA")
        .filter(OrdenCompra.inventario_destino_id == inventario_id)
        .filter(OrdenCompraItem.producto_id == producto_id)
        .order_by(OrdenCompra.recibido_en.asc(), OrdenCompra.id.asc())
    )
    return q.all()


# --------------------------------------------------------------------
# Idempotencia: lotes ya reconstruidos en corrida(s) previa(s)
# --------------------------------------------------------------------


def _lote_ya_reconstruido(db, orden_compra_id: int) -> Lote | None:
    codigo = CODIGO_LOTE_RECONSTRUIDO.format(orden_compra_id=orden_compra_id)
    return db.query(Lote).filter(Lote.codigo_lote == codigo).first()


def _fecha_iso(dt) -> str | None:
    return dt.isoformat() if dt is not None else None


# --------------------------------------------------------------------
# Armado del plan completo (solo lectura, nada se escribe)
# --------------------------------------------------------------------


def armar_plan(db, anio: int | None, inventario_id: int | None):
    afectados = ubicar_ventas_historico_sin_kardex(db, anio, inventario_id)

    lotes_planeados: dict[int, LotePlaneado] = {}
    ingresos_planeados: dict[int, MovimientoIngresoPlaneado] = {}
    items_plan: list[ItemPlan] = []

    # cache de pools por (producto_id, inventario_id) para no repetir queries
    pools_cache: dict[tuple[int, int], list] = {}

    for orden, item, referencia in afectados:
        producto = db.query(Producto).filter(Producto.id == item.producto_id).first()
        base_kwargs = dict(
            orden_venta_id=orden.id,
            item_id=item.id,
            numero_orden_externo=orden.numero_orden_externo,
            factura=orden.factura,
            producto_id=producto.id,
            producto_codigo=producto.codigo,
            producto_nombre=producto.nombre,
            producto_perecible=producto.perecible,
            cantidad_vendida=float(item.cantidad),
            precio_unitario_venta=float(item.precio_unitario_venta),
            fecha_venta=_fecha_iso(orden.despachado_en),
        )

        if producto.perecible:
            items_plan.append(
                ItemPlan(
                    **base_kwargs,
                    estado="EXCLUIDO_PERECIBLE",
                    observaciones=[
                        "Producto perecible: excluido de la reconstruccion automatica "
                        "porque no hay fecha_vencimiento en el Excel de compras historico. "
                        "Requiere decision manual (fuera de este script)."
                    ],
                )
            )
            continue

        clave_pool = (producto.id, orden.inventario_salida_id)
        if clave_pool not in pools_cache:
            pools_cache[clave_pool] = construir_pool_compras_historico(
                db, producto.id, orden.inventario_salida_id
            )
        pool = pools_cache[clave_pool]

        if not pool:
            items_plan.append(
                ItemPlan(
                    **base_kwargs,
                    estado="SIN_RESPALDO",
                    observaciones=[
                        "No se encontro ninguna compra HISTORICO del mismo producto "
                        "e inventario que respalde un costo. Requiere decision manual."
                    ],
                )
            )
            continue

        pendiente = float(item.cantidad)
        salidas: list[MovimientoSalidaPlaneado] = []
        costo_acumulado = 0.0
        cantidad_cubierta = 0.0

        for orden_compra, oc_item in pool:
            if pendiente <= 0:
                break

            if orden_compra.id not in lotes_planeados:
                lote_existente = _lote_ya_reconstruido(db, orden_compra.id)
                codigo_lote = CODIGO_LOTE_RECONSTRUIDO.format(orden_compra_id=orden_compra.id)
                if lote_existente is not None:
                    disponible = float(lote_existente.cantidad_actual)
                    lotes_planeados[orden_compra.id] = LotePlaneado(
                        orden_compra_id=orden_compra.id,
                        producto_id=producto.id,
                        inventario_id=orden_compra.inventario_destino_id,
                        codigo_lote=codigo_lote,
                        cantidad_inicial=float(oc_item.cantidad),
                        costo_unitario=float(oc_item.costo_unitario),
                        fecha_ingreso=_fecha_iso(orden_compra.recibido_en),
                        ya_existe=True,
                        cantidad_disponible_para_plan=disponible,
                        cantidad_actual_existente=disponible,
                    )
                else:
                    lotes_planeados[orden_compra.id] = LotePlaneado(
                        orden_compra_id=orden_compra.id,
                        producto_id=producto.id,
                        inventario_id=orden_compra.inventario_destino_id,
                        codigo_lote=codigo_lote,
                        cantidad_inicial=float(oc_item.cantidad),
                        costo_unitario=float(oc_item.costo_unitario),
                        fecha_ingreso=_fecha_iso(orden_compra.recibido_en),
                        ya_existe=False,
                        cantidad_disponible_para_plan=float(oc_item.cantidad),
                    )
                    ingresos_planeados[orden_compra.id] = MovimientoIngresoPlaneado(
                        orden_compra_id=orden_compra.id,
                        codigo_lote=codigo_lote,
                        cantidad=float(oc_item.cantidad),
                        costo_unitario=float(oc_item.costo_unitario),
                        fecha=_fecha_iso(orden_compra.recibido_en),
                        referencia=REFERENCIA_INGRESO_RECONSTRUIDO.format(
                            orden_compra_id=orden_compra.id
                        ),
                        ya_existe=False,
                    )

            lote_plan = lotes_planeados[orden_compra.id]
            disponible = lote_plan.cantidad_disponible_para_plan
            if disponible <= 0:
                continue

            consumo = min(disponible, pendiente)
            lote_plan.cantidad_disponible_para_plan = disponible - consumo

            salidas.append(
                MovimientoSalidaPlaneado(
                    orden_venta_id=orden.id,
                    item_id=item.id,
                    codigo_lote_origen=lote_plan.codigo_lote,
                    orden_compra_id_origen=orden_compra.id,
                    cantidad=consumo,
                    costo_unitario=lote_plan.costo_unitario,
                    fecha=_fecha_iso(orden.despachado_en),
                    referencia=referencia,
                )
            )
            costo_acumulado += consumo * lote_plan.costo_unitario
            cantidad_cubierta += consumo
            pendiente -= consumo

        if cantidad_cubierta <= 0:
            items_plan.append(
                ItemPlan(
                    **base_kwargs,
                    estado="SIN_RESPALDO",
                    observaciones=[
                        "Existen compras HISTORICO del producto/inventario, pero sin "
                        "cantidad disponible remanente (ya consumida por otro item con "
                        "fecha anterior). Requiere decision manual."
                    ],
                )
            )
            continue

        costo_unitario_resultante = costo_acumulado / cantidad_cubierta
        margen_resultante = float(item.precio_unitario_venta) - costo_unitario_resultante
        margen_pct_resultante = (
            (margen_resultante / float(item.precio_unitario_venta) * 100.0)
            if float(item.precio_unitario_venta)
            else 0.0
        )

        observaciones = []
        estado = "PLANIFICADO"
        if pendiente > 0:
            estado = "PARCIAL_PLANIFICADO"
            observaciones.append(
                f"Cobertura parcial: {cantidad_cubierta:.3f} de {float(item.cantidad):.3f} "
                f"unidades con respaldo de compra HISTORICO. Quedan {pendiente:.3f} unidades "
                "sin costo de respaldo (no se planifica Lote/Kardex para esa porcion)."
            )

        items_plan.append(
            ItemPlan(
                **base_kwargs,
                estado=estado,
                costo_unitario_resultante=costo_unitario_resultante,
                margen_resultante=margen_resultante,
                margen_pct_resultante=margen_pct_resultante,
                salidas=salidas,
                observaciones=observaciones,
            )
        )

    return items_plan, lotes_planeados, ingresos_planeados


# --------------------------------------------------------------------
# Reporte (JSON + Markdown)
# --------------------------------------------------------------------


def escribir_reporte(items_plan, lotes_planeados, ingresos_planeados, anio, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(output_dir, f"plan_reconstruccion_kardex_{anio}_{timestamp}.json")
    md_path = os.path.join(output_dir, f"plan_reconstruccion_kardex_{anio}_{timestamp}.md")

    resumen = {
        "items_total": len(items_plan),
        "planificados": sum(1 for i in items_plan if i.estado == "PLANIFICADO"),
        "parciales": sum(1 for i in items_plan if i.estado == "PARCIAL_PLANIFICADO"),
        "sin_respaldo": sum(1 for i in items_plan if i.estado == "SIN_RESPALDO"),
        "excluidos_perecible": sum(1 for i in items_plan if i.estado == "EXCLUIDO_PERECIBLE"),
        "lotes_nuevos_a_crear": sum(1 for l in lotes_planeados.values() if not l.ya_existe),
        "lotes_ya_existentes_reutilizados": sum(1 for l in lotes_planeados.values() if l.ya_existe),
        "movimientos_ingreso_a_crear": sum(1 for m in ingresos_planeados.values() if not m.ya_existe),
        "movimientos_salida_a_crear": sum(len(i.salidas) for i in items_plan),
    }

    def lote_dict(l: LotePlaneado):
        d = dict(l.__dict__)
        d.pop("cantidad_disponible_para_plan", None)
        return d

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "anio": anio,
                "generado_en": datetime.now().isoformat(),
                "modo": "DRY_RUN (plan calculado, NADA escrito en la base de datos)",
                "resumen": resumen,
                "lotes": [lote_dict(l) for l in lotes_planeados.values()],
                "movimientos_ingreso": [m.__dict__ for m in ingresos_planeados.values()],
                "items": [
                    {**i.__dict__, "salidas": [s.__dict__ for s in i.salidas]} for i in items_plan
                ],
            },
            fh,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(f"# Plan de reconstruccion de Kardex historico {anio} (DRY-RUN)\n\n")
        fh.write(f"Generado: {datetime.now().isoformat()}\n\n")
        fh.write("**Este reporte es un PLAN. No se escribio nada en la base de datos.**\n\n")
        fh.write("## Resumen\n\n")
        for k, v in resumen.items():
            fh.write(f"- {k}: **{v}**\n")

        fh.write("\n## Lotes a crear / reutilizar\n\n")
        for l in lotes_planeados.values():
            estado = "YA EXISTE (se reutiliza)" if l.ya_existe else "NUEVO"
            fh.write(
                f"- `{l.codigo_lote}` [{estado}] — Orden compra #{l.orden_compra_id}, "
                f"producto_id={l.producto_id}, inventario_id={l.inventario_id}, "
                f"cantidad_inicial={l.cantidad_inicial}, costo_unitario={l.costo_unitario}, "
                f"fecha_ingreso={l.fecha_ingreso or '-'}"
            )
            if l.ya_existe:
                fh.write(f" (cantidad_actual ya en BD: {l.cantidad_actual_existente})")
            fh.write("\n")

        fh.write("\n## Detalle por item de venta\n\n")
        for i in items_plan:
            fh.write(
                f"### Orden venta #{i.orden_venta_id} / item #{i.item_id} "
                f"(orden ext. {i.numero_orden_externo or '-'}, factura {i.factura or '-'}) "
                f"— {i.estado}\n\n"
            )
            fh.write(
                f"- Producto: `{i.producto_codigo}` - {i.producto_nombre}"
                f"{' (PERECIBLE)' if i.producto_perecible else ''}\n"
            )
            fh.write(
                f"- Fecha venta: {i.fecha_venta or '-'} — Cantidad: {i.cantidad_vendida} — "
                f"Precio venta: {i.precio_unitario_venta}\n"
            )
            if i.costo_unitario_resultante is not None:
                fh.write(f"- Costo unitario resultante tras reconstruir: {i.costo_unitario_resultante:.4f}\n")
                fh.write(f"- Margen resultante: {i.margen_resultante:.4f} ({i.margen_pct_resultante:.2f}%)\n")
            if i.salidas:
                fh.write("- MovimientoKardex SALIDA a crear:\n")
                for s in i.salidas:
                    fh.write(
                        f"  - lote `{s.codigo_lote_origen}` (orden compra #{s.orden_compra_id_origen}): "
                        f"{s.cantidad} u. a costo {s.costo_unitario}, fecha={s.fecha or '-'}, "
                        f"referencia=\"{s.referencia}\"\n"
                    )
            if i.observaciones:
                fh.write("- Observaciones:\n")
                for obs in i.observaciones:
                    fh.write(f"  - {obs}\n")
            fh.write("\n")

    return json_path, md_path


# --------------------------------------------------------------------
# main
# --------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--anio", type=int, default=2026)
    parser.add_argument("--inventario-id", type=int, default=None)
    parser.add_argument("--output-dir", type=str, default="./reportes_reconstruccion_historico")
    args = parser.parse_args()

    print("[reconstruccion][DRY_RUN] Conectando con DATABASE_URL configurada en el entorno...")
    db = SessionLocal()
    try:
        print(f"[reconstruccion][DRY_RUN] Armando plan para ventas HISTORICO {args.anio}...")
        items_plan, lotes_planeados, ingresos_planeados = armar_plan(db, args.anio, args.inventario_id)

        if not items_plan:
            print("[reconstruccion][DRY_RUN] No hay items sin Kardex para planificar. Nada que reportar.")
            return

        json_path, md_path = escribir_reporte(
            items_plan, lotes_planeados, ingresos_planeados, args.anio, args.output_dir
        )
        print(f"[reconstruccion][DRY_RUN] Reporte JSON: {json_path}")
        print(f"[reconstruccion][DRY_RUN] Reporte Markdown: {md_path}")
        print(
            "[reconstruccion][DRY_RUN] Plan calculado. NO se escribio nada en la base de datos "
            "(este script no tiene modo de aplicacion en esta entrega)."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
