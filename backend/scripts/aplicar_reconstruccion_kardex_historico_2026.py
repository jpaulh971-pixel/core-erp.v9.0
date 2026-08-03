"""FASE 2 (aplicacion) — Ejecuta el plan de reconstruccion de Kardex
historico calculado por `reconstruccion_kardex_historico_2026.armar_plan`
(script ya aprobado, importado tal cual -- NO se duplica su logica de
deteccion/PEPS aca).

QUE HACE:
-----------------------------------------------------------------------
Para cada Lote/MovimientoKardex que el plan marco como faltante
(`ya_existe=False`), lo crea usando EXCLUSIVAMENTE las funciones que ya
existen en el sistema para eso:

  - `m03_inventario.service.registrar_ingreso()` para cada Lote nuevo
    (mismo codigo `HIST-OC-{orden_compra_id}` deterministico que ya
    calculo el plan), con `fecha_movimiento` = fecha real de la compra
    para que el Lote/Kardex nazcan con esa fecha (no con "ahora").

  - `m03_inventario.service.registrar_salida()` para cada porcion PEPS
    consumida, indicando explicitamente `lote_id` (el lote reconstruido
    de origen): esto es intencional y evita FEFO automatico, que
    mezclaria esta reconstruccion documental con el stock/lotes VIGENTES
    de operacion real. `referencia` es la MISMA que ya usa el flujo real
    de despacho (`_referencia_despacho_item`, importada del plan
    aprobado), asi que el costo que ya expone
    `ventas_service.obtener_orden()/listar_ordenes()` empieza a
    resolverse solo en cuanto este script corre -- no se toca m10_ventas
    ni el frontend.

No crea ordenes nuevas, no recarga Excel, no cambia modo_carga, no
modifica ningun modelo ni servicio existente: unicamente invoca, con los
datos que el plan ya valido, las 2 funciones de escritura que el propio
ERP usa siempre para el flujo OPERATIVO real.

IDEMPOTENCIA / SEGURIDAD:
  - Antes de escribir, vuelve a llamar `armar_plan()` (fuente unica de
    verdad, no se recalcula nada por separado) para tomar el plan MAS
    RECIENTE contra el estado actual de la base. Si se corre 2 veces,
    la segunda corrida encuentra los items ya con Kardex (excluidos por
    `ubicar_ventas_historico_sin_kardex`) y los Lotes ya creados
    (`ya_existe=True`), asi que no duplica nada.
  - Cada Lote y cada Salida se escribe en su propio try/except (mismo
    patron que ya usa `m21_importacion_datos.service.confirmar_compras/
    confirmar_ventas` para procesar filas): un fallo puntual no aborta
    el resto ni deja transacciones a medias (cada
    registrar_ingreso/registrar_salida hace su propio commit atomico).
  - Por defecto corre en modo de solo verificacion (reimprime el resumen
    del plan y NO escribe nada) salvo que se pase `--confirmar`
    explicitamente. Este flag no es un nuevo "diagnostico": es la misma
    doble confirmacion que ya exige, por ejemplo, cualquier operacion
    destructiva del sistema (ver ETAPA 3 de reemplazo de cargas).
  - Escribe un reporte de RESULTADOS (json+md) en el mismo directorio que
    el dry-run, con prefijo `aplicado_`, documentando exactamente que se
    creo, que se reuso y que fallo.

Uso:
    cd backend
    # 1) revisar que el plan sea el esperado (no escribe nada):
    python -m scripts.aplicar_reconstruccion_kardex_historico_2026 --anio 2026

    # 2) ejecutar la escritura real:
    python -m scripts.aplicar_reconstruccion_kardex_historico_2026 --anio 2026 --confirmar

CORRECCIONES DE AUDITORIA (Fase 2 final, sobre la version ya aprobada;
ninguna toca m03_inventario, modelos, APIs ni frontend):

  1. Guardia --permitir-parcial-multianio / existen_anios_pendientes_fuera_de_rango():
     antes de escribir, verifica si existen otros anios con ventas
     HISTORICO sin Kardex todavia pendientes del mismo pool de compras.
     Si los hay, se detiene (o solo advierte si se pasa el flag
     explicito). Corrige el riesgo de que el remanente de un lote
     reconstruido quede expuesto al FEFO real de ventas en curso mientras
     otros anios del mismo pool no fueron procesados aun.

  2. Limpieza compensatoria en aplicar_plan(): registrar_ingreso() de
     m03_inventario hace 2 commits internos (Lote, luego Kardex) y no es
     atomico. Si el 2do falla tras persistirse el 1ro, ahora se detecta y
     se elimina el Lote huerfano antes de reportar el fallo, en vez de
     dejarlo en la base sin respaldo de Kardex.
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
from app.modules.m03_inventario import schemas as inventario_schemas  # noqa: E402
from app.modules.m03_inventario import service as inventario_service  # noqa: E402
from app.modules.m03_inventario.models import Lote  # noqa: E402
from app.modules.m10_ventas.models import OrdenVenta  # noqa: E402

# Reuso explicito (NO modificacion) del script de plan ya aprobado: misma
# deteccion/PEPS, mismas referencias/codigos deterministicos.
from scripts.reconstruccion_kardex_historico_2026 import (  # noqa: E402
    armar_plan,
    escribir_reporte as escribir_reporte_plan,
    ubicar_ventas_historico_sin_kardex,
)


def existen_anios_pendientes_fuera_de_rango(
    db, anio_actual: int, inventario_id: int | None
) -> set[int]:
    """Devuelve el conjunto de anios (distintos de anio_actual) que
    TODAVIA tienen ventas HISTORICO sin Kardex pendientes de reconstruir,
    usando la MISMA deteccion ya aprobada (ubicar_ventas_historico_sin_kardex,
    importada tal cual, sin duplicar su logica), esta vez sin filtro de
    anio (anio=None) para ver el universo completo.

    Motivo (hallazgo CRITICO de la auditoria anterior): un Lote
    reconstruido queda disponible para el FEFO REAL de ventas en curso en
    cuanto se crea. Si se aplica la reconstruccion de un solo anio
    mientras compras HISTORICO del mismo producto/inventario todavia
    respaldan ventas HISTORICO de OTROS anios sin procesar, el remanente
    de esos lotes (la porcion que en realidad esta reservada para esas
    otras ventas, solo que aun no se calculo) queda expuesto a ser
    consumido por una venta real cualquiera antes de que le toque su
    turno -- dejando esa venta historica futura sin respaldo y
    contaminando el costo de la venta real que la consumio antes de
    tiempo. Este chequeo es la salvaguarda minima para esa ventana."""
    todos = ubicar_ventas_historico_sin_kardex(db, anio=None, inventario_id=inventario_id)
    anios = {
        orden.despachado_en.year
        for orden, _item, _referencia in todos
        if orden.despachado_en is not None
    }
    anios.discard(anio_actual)
    return anios


@dataclass
class ResultadoIngreso:
    orden_compra_id: int
    codigo_lote: str
    ok: bool
    lote_id: int | None = None
    error: str | None = None


@dataclass
class ResultadoSalida:
    orden_venta_id: int
    item_id: int
    codigo_lote_origen: str
    cantidad: float
    ok: bool
    error: str | None = None


def _fecha(dt_iso: str | None):
    return datetime.fromisoformat(dt_iso) if dt_iso else None


def aplicar_plan(db, items_plan, lotes_planeados, ingresos_planeados):
    """Escribe en la base los Lotes/MovimientoKardex que el plan marco
    como faltantes. Devuelve (resultados_ingreso, resultados_salida)."""

    resultados_ingreso: list[ResultadoIngreso] = []
    lote_id_por_orden_compra: dict[int, int] = {}

    # --- 1) Lotes / INGRESO ---
    for oc_id, lote_plan in lotes_planeados.items():
        if lote_plan.ya_existe:
            lote_bd = (
                db.query(Lote).filter(Lote.codigo_lote == lote_plan.codigo_lote).first()
            )
            if lote_bd is not None:
                lote_id_por_orden_compra[oc_id] = lote_bd.id
            continue

        ingreso_plan = ingresos_planeados[oc_id]
        try:
            movimiento = inventario_service.registrar_ingreso(
                db,
                inventario_schemas.IngresoInventarioCrear(
                    producto_id=lote_plan.producto_id,
                    inventario_id=lote_plan.inventario_id,
                    codigo_lote=lote_plan.codigo_lote,
                    cantidad=lote_plan.cantidad_inicial,
                    costo_unitario=lote_plan.costo_unitario,
                    referencia=ingreso_plan.referencia,
                    fecha_movimiento=_fecha(lote_plan.fecha_ingreso),
                ),
            )
            lote_id_por_orden_compra[oc_id] = movimiento.lote_id
            resultados_ingreso.append(
                ResultadoIngreso(
                    orden_compra_id=oc_id, codigo_lote=lote_plan.codigo_lote,
                    ok=True, lote_id=movimiento.lote_id,
                )
            )
        except Exception as exc:  # noqa: BLE001 - se documenta y se sigue con el resto
            db.rollback()
            # registrar_ingreso() no es atomico (2 commits internos: Lote y
            # luego MovimientoKardex). db.rollback() aca solo limpia la
            # sesion en memoria, NO deshace un 1er commit que ya se haya
            # persistido. Se verifica y se limpia ese huerfano explicitamente
            # para no dejar stock reconstruido sin respaldo de Kardex.
            error_extra = ""
            huerfano = (
                db.query(Lote).filter(Lote.codigo_lote == lote_plan.codigo_lote).first()
            )
            if huerfano is not None:
                try:
                    db.delete(huerfano)
                    db.commit()
                    error_extra = " [lote huerfano detectado tras fallo parcial y eliminado automaticamente]"
                except Exception as exc_cleanup:  # noqa: BLE001
                    db.rollback()
                    error_extra = (
                        f" [ADVERTENCIA: lote huerfano id={huerfano.id} codigo="
                        f"'{lote_plan.codigo_lote}' NO pudo eliminarse ({exc_cleanup}); "
                        "requiere limpieza manual antes de reintentar]"
                    )
            resultados_ingreso.append(
                ResultadoIngreso(
                    orden_compra_id=oc_id, codigo_lote=lote_plan.codigo_lote,
                    ok=False, error=str(exc) + error_extra,
                )
            )

    # --- 2) Salidas por item (solo items PLANIFICADO / PARCIAL_PLANIFICADO) ---
    resultados_salida: list[ResultadoSalida] = []
    cache_inventario_por_orden: dict[int, int] = {}

    for item in items_plan:
        if item.estado not in ("PLANIFICADO", "PARCIAL_PLANIFICADO") or not item.salidas:
            continue

        if item.orden_venta_id not in cache_inventario_por_orden:
            orden_venta = db.query(OrdenVenta).filter(OrdenVenta.id == item.orden_venta_id).first()
            cache_inventario_por_orden[item.orden_venta_id] = orden_venta.inventario_salida_id
        inventario_id = cache_inventario_por_orden[item.orden_venta_id]

        for salida in item.salidas:
            lote_id = lote_id_por_orden_compra.get(salida.orden_compra_id_origen)
            if lote_id is None:
                resultados_salida.append(
                    ResultadoSalida(
                        orden_venta_id=item.orden_venta_id, item_id=item.item_id,
                        codigo_lote_origen=salida.codigo_lote_origen, cantidad=salida.cantidad,
                        ok=False,
                        error=(
                            "No se pudo resolver el lote_id de origen (el ingreso de su lote "
                            "fallo arriba); se omite esta salida para no dejar Kardex sin lote."
                        ),
                    )
                )
                continue
            try:
                inventario_service.registrar_salida(
                    db,
                    inventario_schemas.SalidaInventarioCrear(
                        producto_id=item.producto_id,
                        inventario_id=inventario_id,
                        cantidad=salida.cantidad,
                        lote_id=lote_id,
                        referencia=salida.referencia,
                        fecha_movimiento=_fecha(salida.fecha),
                    ),
                )
                resultados_salida.append(
                    ResultadoSalida(
                        orden_venta_id=item.orden_venta_id, item_id=item.item_id,
                        codigo_lote_origen=salida.codigo_lote_origen, cantidad=salida.cantidad,
                        ok=True,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                resultados_salida.append(
                    ResultadoSalida(
                        orden_venta_id=item.orden_venta_id, item_id=item.item_id,
                        codigo_lote_origen=salida.codigo_lote_origen, cantidad=salida.cantidad,
                        ok=False, error=str(exc),
                    )
                )

    return resultados_ingreso, resultados_salida


def escribir_reporte_resultados(resultados_ingreso, resultados_salida, anio, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(output_dir, f"aplicado_reconstruccion_kardex_{anio}_{timestamp}.json")
    md_path = os.path.join(output_dir, f"aplicado_reconstruccion_kardex_{anio}_{timestamp}.md")

    resumen = {
        "ingresos_ok": sum(1 for r in resultados_ingreso if r.ok),
        "ingresos_fallidos": sum(1 for r in resultados_ingreso if not r.ok),
        "salidas_ok": sum(1 for r in resultados_salida if r.ok),
        "salidas_fallidas": sum(1 for r in resultados_salida if not r.ok),
    }

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "anio": anio,
                "generado_en": datetime.now().isoformat(),
                "modo": "APLICADO (se escribio en la base de datos)",
                "resumen": resumen,
                "ingresos": [r.__dict__ for r in resultados_ingreso],
                "salidas": [r.__dict__ for r in resultados_salida],
            },
            fh, ensure_ascii=False, indent=2, default=str,
        )

    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(f"# Resultado de aplicacion — reconstruccion Kardex {anio}\n\n")
        fh.write(f"Generado: {datetime.now().isoformat()}\n\n")
        for k, v in resumen.items():
            fh.write(f"- {k}: **{v}**\n")
        if any(not r.ok for r in resultados_ingreso):
            fh.write("\n## Ingresos fallidos\n\n")
            for r in resultados_ingreso:
                if not r.ok:
                    fh.write(f"- Orden compra #{r.orden_compra_id} (`{r.codigo_lote}`): {r.error}\n")
        if any(not r.ok for r in resultados_salida):
            fh.write("\n## Salidas fallidas\n\n")
            for r in resultados_salida:
                if not r.ok:
                    fh.write(
                        f"- Orden venta #{r.orden_venta_id} / item #{r.item_id} "
                        f"(lote `{r.codigo_lote_origen}`): {r.error}\n"
                    )

    return json_path, md_path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--anio", type=int, default=2026)
    parser.add_argument("--inventario-id", type=int, default=None)
    parser.add_argument("--output-dir", type=str, default="./reportes_reconstruccion_historico")
    parser.add_argument(
        "--confirmar", action="store_true",
        help="Sin este flag, solo recalcula y muestra el resumen del plan (no escribe nada).",
    )
    parser.add_argument(
        "--permitir-parcial-multianio", action="store_true",
        help=(
            "Permite aplicar el plan de --anio aunque existan otros anios con "
            "ventas HISTORICO sin Kardex todavia pendientes (mismo pool de "
            "compras). Sin este flag, el script se detiene por seguridad antes "
            "de escribir: aplicar un solo anio mientras otros quedan pendientes "
            "puede exponer el remanente de un lote reconstruido al FEFO real "
            "de ventas en curso antes de que le corresponda a esa venta "
            "historica todavia no procesada."
        ),
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print(f"[reconstruccion][aplicacion] Recalculando plan actual para {args.anio}...")
        items_plan, lotes_planeados, ingresos_planeados = armar_plan(db, args.anio, args.inventario_id)

        if not items_plan:
            print("[reconstruccion][aplicacion] No hay items pendientes. Nada que aplicar.")
            return

        pendientes_lote = sum(1 for l in lotes_planeados.values() if not l.ya_existe)
        pendientes_salida = sum(
            len(i.salidas) for i in items_plan if i.estado in ("PLANIFICADO", "PARCIAL_PLANIFICADO")
        )
        print(
            f"[reconstruccion][aplicacion] Plan actual: {pendientes_lote} lote(s)/ingreso(s) "
            f"nuevos, {pendientes_salida} salida(s) a crear."
        )

        anios_pendientes = existen_anios_pendientes_fuera_de_rango(db, args.anio, args.inventario_id)
        if anios_pendientes:
            print(
                f"[reconstruccion][aplicacion] AVISO: hay ventas HISTORICO sin Kardex "
                f"pendientes en otro(s) anio(s) {sorted(anios_pendientes)} ademas de "
                f"{args.anio}."
            )

        if not args.confirmar:
            print(
                "[reconstruccion][aplicacion] Modo verificacion (sin --confirmar): "
                "NO se escribio nada. Vuelva a correr con --confirmar para aplicar."
            )
            return

        if anios_pendientes and not args.permitir_parcial_multianio:
            print(
                "[reconstruccion][aplicacion] DETENIDO: no se escribio nada. Aplicar "
                f"solo {args.anio} mientras quedan pendientes {sorted(anios_pendientes)} "
                "puede dejar remanente de lotes reconstruidos expuesto al FEFO real "
                "antes de que esas ventas historicas se procesen. Corra la "
                "reconstruccion para TODOS los anios pendientes en la misma sesion, o "
                "repita este comando agregando --permitir-parcial-multianio si asume "
                "ese riesgo conscientemente."
            )
            return
        if anios_pendientes:
            print(
                "[reconstruccion][aplicacion] Continuando pese a anios pendientes "
                "(--permitir-parcial-multianio activo)."
            )

        resultados_ingreso, resultados_salida = aplicar_plan(
            db, items_plan, lotes_planeados, ingresos_planeados
        )
        json_path, md_path = escribir_reporte_resultados(
            resultados_ingreso, resultados_salida, args.anio, args.output_dir
        )
        print(f"[reconstruccion][aplicacion] Reporte de resultados: {json_path} / {md_path}")
        print(
            f"[reconstruccion][aplicacion] Ingresos OK={sum(1 for r in resultados_ingreso if r.ok)} "
            f"fallidos={sum(1 for r in resultados_ingreso if not r.ok)} | "
            f"Salidas OK={sum(1 for r in resultados_salida if r.ok)} "
            f"fallidas={sum(1 for r in resultados_salida if not r.ok)}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
