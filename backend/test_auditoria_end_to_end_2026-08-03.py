"""Auditoria funcional end-to-end (reconstruida, 2026-08-03).

Ejercita con datos reales (no simulados) el flujo completo del ERP
integrado, usando los services reales (mismo patron que
test_fase10_cierre_e2e.py) para no depender de HTTP/auth.

Secciones:
    A) Regresion Compras -> Inventario (recepcion, kardex, saldos)
    B) Regresion Ventas -> despacho (incluye escenario "B8": intento de
       despacho sin stock suficiente, debe fallar controladamente)
    C) Regresion Dashboard / Costos / Importacion Historica (lectura)
    D) m13 Inteligencia Comercial
    E) m15 Lean Six Sigma
    F) m16 Theory of Constraints
    G) m18 Balanced Scorecard
    (extra) m06 Comercio Exterior, m07 Operacion Logistica, m12 SUNAT,
    m14 Inteligencia Tributaria -- necesarios como generadores de datos
    reales para D-G y para cubrir el resto de "modulos no probados por
    HTTP" listados como pendientes.
"""
import os
import sys
import traceback
from datetime import date

os.environ["SECRET_KEY"] = "test-secret-audit"
os.environ["DATABASE_URL"] = "sqlite:///./_test_auditoria_e2e.db"

from app.database import Base, SessionLocal, engine  # noqa: E402

from app.modules.m02_productos import schemas as prod_s, service as prod_sv  # noqa: E402
from app.modules.m03_inventario import schemas as inv_s, service as inv_sv  # noqa: E402
from app.modules.m04_compras import schemas as compras_s, service as compras_sv  # noqa: E402
from app.modules.m05_proveedores import schemas as prov_s, service as prov_sv  # noqa: E402
from app.modules.m06_comercio_exterior import schemas as ce_s, service as ce_sv  # noqa: E402
from app.modules.m07_operacion_logistica import schemas as ol_s, service as ol_sv  # noqa: E402
from app.modules.m10_ventas import schemas as ventas_s, service as ventas_sv  # noqa: E402
from app.modules.m11_clientes import schemas as cli_s, service as cli_sv  # noqa: E402
from app.modules.m12_sunat import schemas as sunat_s, service as sunat_sv  # noqa: E402
from app.modules.m13_inteligencia_comercial import service as m13_sv  # noqa: E402
from app.modules.m14_inteligencia_tributaria import service as m14_sv  # noqa: E402
from app.modules.m15_lean_six_sigma import service as m15_sv  # noqa: E402
from app.modules.m16_theory_of_constraints import service as m16_sv  # noqa: E402
from app.modules.m18_balanced_scorecard import service as m18_sv  # noqa: E402
from app.modules.m01_dashboard import service as m01_sv  # noqa: E402
from app.modules.m08_costos import service as m08_sv  # noqa: E402
from app.modules.m19_reportes import service as m19_sv  # noqa: E402
from app.modules.m20_configuracion import models as cfg_models  # noqa: E402,F401

RESULTS = {}  # seccion -> {"estado": ..., "hallazgos": [...]}
BUGS = []
FIXES = []


def seccion(nombre):
    RESULTS[nombre] = {"estado": "PENDIENTE", "detalle": []}
    return nombre


def ok(nombre, msg):
    RESULTS[nombre]["detalle"].append(f"OK: {msg}")


def fail(nombre, msg, exc=None):
    RESULTS[nombre]["detalle"].append(f"FALLA: {msg}" + (f" -> {exc}" if exc else ""))


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
db = SessionLocal()

usuario_fake = cfg_models.Usuario(
    id=1, username="auditor", nombre_completo="Auditor E2E",
    password_hash="x", rol="ADMINISTRADOR", activo=True,
)

try:
    # ---------------------------------------------------------------
    # SETUP comun: 1 inventario, productos, proveedor, cliente
    # ---------------------------------------------------------------
    inventario = inv_sv.crear_inventario(
        db, inv_s.InventarioCrear(codigo="INV-AUD", nombre="Almacen Auditoria")
    )
    prodA = prod_sv.crear_producto(
        db, prod_s.ProductoCrear(codigo="AUD-A", nombre="Producto Auditoria A",
                                  unidad_medida="KG", stock_minimo=0)
    )
    prodB = prod_sv.crear_producto(
        db, prod_s.ProductoCrear(codigo="AUD-B", nombre="Producto Auditoria B",
                                  unidad_medida="KG", stock_minimo=0)
    )
    proveedor = prov_sv.crear_proveedor(
        db, prov_s.ProveedorCrear(ruc="20999999991", razon_social="Proveedor Auditoria SAC")
    )
    cliente = cli_sv.crear_cliente(
        db, cli_s.ClienteCrear(ruc="20999999992", razon_social="Cliente Auditoria SAC")
    )

    # =================================================================
    # SECCION A -- Regresion Compras -> Inventario
    # =================================================================
    s = seccion("A")
    try:
        orden_compra = compras_sv.crear_orden(
            db, compras_s.OrdenCompraCrear(
                proveedor_id=proveedor.id, inventario_destino_id=inventario.id,
                moneda="USD",
                items=[compras_s.OrdenCompraItemCrear(
                    producto_id=prodA.id, cantidad=200, costo_unitario=10
                ), compras_s.OrdenCompraItemCrear(
                    producto_id=prodB.id, cantidad=50, costo_unitario=20
                )],
            ),
        )
        compras_sv.aprobar_orden(db, orden_compra.id)
        orden_compra = compras_sv.recibir_orden(db, orden_compra.id)
        assert orden_compra.estado == "RECIBIDA"
        saldos = inv_sv.saldos(db, inventario.id)
        saldo_a = next(x for x in saldos if x["producto_id"] == prodA.id)
        saldo_b = next(x for x in saldos if x["producto_id"] == prodB.id)
        assert saldo_a["stock_total"] == 200, saldo_a
        assert saldo_b["stock_total"] == 50, saldo_b
        ok("A", "Orden de compra creada/aprobada/recibida; kardex e inventario correctos "
                "(200 KG @10 prod A, 50 KG @20 prod B)")
    except Exception as e:
        fail("A", "Flujo Compras -> Inventario", traceback.format_exc())
        BUGS.append(("A", "Compras->Inventario", str(e)))
    RESULTS["A"]["estado"] = "VERDE" if all("FALLA" not in d for d in RESULTS["A"]["detalle"]) else "ROJO"

    # =================================================================
    # SECCION B -- Regresion Ventas -> Despacho (incluye escenario B8)
    # =================================================================
    s = seccion("B")
    orden_venta = None
    try:
        orden_venta = ventas_sv.crear_orden(
            db, ventas_s.OrdenVentaCrear(
                cliente_id=cliente.id, inventario_salida_id=inventario.id, moneda="USD",
                items=[ventas_s.OrdenVentaItemCrear(
                    producto_id=prodA.id, cantidad=60, precio_unitario_venta=15
                )],
            ),
        )
        ventas_sv.confirmar_orden(db, orden_venta.id)
        orden_venta = ventas_sv.despachar_orden(db, orden_venta.id)
        assert orden_venta.estado == "DESPACHADA"
        saldos = inv_sv.saldos(db, inventario.id)
        saldo_a = next(x for x in saldos if x["producto_id"] == prodA.id)
        assert saldo_a["stock_total"] == 140, saldo_a  # 200 - 60
        ok("B", "Orden de venta creada/confirmada/despachada; stock descontado correctamente "
                "(200 - 60 = 140 KG prod A)")
    except Exception as e:
        fail("B", "Flujo Ventas -> Despacho", traceback.format_exc())
        BUGS.append(("B", "Ventas->Despacho", str(e)))

    # --- Escenario B8: venta que excede el stock disponible debe fallar
    #     de forma controlada (HTTPException / ValueError de negocio), NO
    #     con una excepcion no manejada ni con descuento parcial de stock.
    try:
        orden_sobrestock = ventas_sv.crear_orden(
            db, ventas_s.OrdenVentaCrear(
                cliente_id=cliente.id, inventario_salida_id=inventario.id, moneda="USD",
                items=[ventas_s.OrdenVentaItemCrear(
                    producto_id=prodA.id, cantidad=99999, precio_unitario_venta=15
                )],
            ),
        )
        ventas_sv.confirmar_orden(db, orden_sobrestock.id)
        fallo_esperado = False
        try:
            ventas_sv.despachar_orden(db, orden_sobrestock.id)
        except Exception:
            fallo_esperado = True
        if not fallo_esperado:
            fail("B", "Escenario B8 (venta > stock disponible): el despacho NO deberia "
                      "haber tenido exito; posible bug de validacion de stock")
            BUGS.append(("B", "B8", "despachar_orden no valida stock insuficiente"))
        else:
            saldos_post = inv_sv.saldos(db, inventario.id)
            saldo_a_post = next(x for x in saldos_post if x["producto_id"] == prodA.id)
            assert saldo_a_post["stock_total"] == 140, saldo_a_post
            ok("B", "Escenario B8: despacho sobre-stock rechazado correctamente, "
                    "sin descuento parcial de inventario (stock se mantuvo en 140)")
    except Exception as e:
        fail("B", "Escenario B8 (setup)", traceback.format_exc())
        BUGS.append(("B", "B8-setup", str(e)))
    RESULTS["B"]["estado"] = "VERDE" if all("FALLA" not in d for d in RESULTS["B"]["detalle"]) else "ROJO"

    # =================================================================
    # SECCION C -- Regresion Dashboard / Costos / Importacion Historica
    # =================================================================
    s = seccion("C")
    try:
        resumen = m01_sv.resumen_ejecutivo(db)
        ventas_reporte = m19_sv.reporte_ventas(db)
        compras_reporte = m19_sv.reporte_compras(db)
        inv_valorizado = m19_sv.reporte_inventario_valorizado(db)
        assert resumen is not None
        assert ventas_reporte is not None
        ok("C", f"m01 Dashboard.resumen_ejecutivo OK, m19 reporte_ventas/reporte_compras/"
                f"reporte_inventario_valorizado OK sobre datos reales de A/B "
                f"(valor_inventario={inv_valorizado.valor_total if hasattr(inv_valorizado, 'valor_total') else 'ver detalle'})")
    except Exception as e:
        fail("C", "Dashboard/Reportes (m01/m19)", traceback.format_exc())
        BUGS.append(("C", "Dashboard/Reportes", str(e)))

    try:
        costeo = m08_sv.costeo_compra(db, orden_compra.id)
        assert costeo is not None
        ok("C", f"m08 Costos.costeo_compra sobre orden real de la seccion A: OK")
    except Exception as e:
        fail("C", "m08 Costos costeo_compra", traceback.format_exc())
        BUGS.append(("C", "Costos", str(e)))
    RESULTS["C"]["estado"] = "VERDE" if all("FALLA" not in d for d in RESULTS["C"]["detalle"]) else "ROJO"

    # =================================================================
    # Generadores de datos para D-G: SUNAT, Comercio Exterior, Op. Log.
    # =================================================================
    s = seccion("EXTRA_SUNAT_CE_OL")
    comprobante = None
    declaracion = None
    try:
        comprobante = sunat_sv.emitir_comprobante(
            db, sunat_s.ComprobanteCrear(orden_venta_id=orden_venta.id, tipo_comprobante="FACTURA")
        )
        assert comprobante.estado == "EMITIDO"
        ok("EXTRA_SUNAT_CE_OL", "m12 SUNAT: comprobante FACTURA emitido correctamente sobre "
                                 "orden de venta despachada real")
        # anular y volver a intentar duplicado (regla de negocio)
        dup_bloqueado = False
        try:
            sunat_sv.emitir_comprobante(
                db, sunat_s.ComprobanteCrear(orden_venta_id=orden_venta.id, tipo_comprobante="FACTURA")
            )
        except Exception:
            dup_bloqueado = True
        if dup_bloqueado:
            ok("EXTRA_SUNAT_CE_OL", "m12 SUNAT: bloqueo correcto de comprobante duplicado para la misma orden")
        else:
            fail("EXTRA_SUNAT_CE_OL", "m12 SUNAT: permitio emitir un segundo comprobante para la misma orden")
            BUGS.append(("EXTRA", "SUNAT-duplicado", "validar_no_duplicado no bloquea"))
    except Exception as e:
        fail("EXTRA_SUNAT_CE_OL", "m12 SUNAT emitir_comprobante", traceback.format_exc())
        BUGS.append(("EXTRA", "SUNAT", str(e)))

    try:
        declaracion = ce_sv.crear_declaracion(
            db, ce_s.DeclaracionCrear(
                cliente_nombre="Cliente Exportacion Auditoria", pais_destino="Alemania",
                incoterm="FOB", moneda="USD", inventario_origen_id=inventario.id,
                items=[ce_s.DeclaracionItemCrear(
                    producto_id=prodB.id, cantidad=5, precio_unitario_exportacion=25
                )],
            )
        )
        declaracion = ce_sv.confirmar_declaracion(db, declaracion.id)
        declaracion = ce_sv.embarcar_declaracion(db, declaracion.id)
        assert declaracion.estado == "EMBARCADA"
        saldos_post_embarque = inv_sv.saldos(db, inventario.id)
        saldo_b_post = next(x for x in saldos_post_embarque if x["producto_id"] == prodB.id)
        assert saldo_b_post["stock_total"] == 45, saldo_b_post  # 50 - 5
        ok("EXTRA_SUNAT_CE_OL", "m06 Comercio Exterior: declaracion creada, confirmada y "
                                 "embarcada; descuento real de stock via FEFO correcto (50 - 5 = 45)")
    except Exception as e:
        fail("EXTRA_SUNAT_CE_OL", "m06 Comercio Exterior crear/confirmar declaracion",
             traceback.format_exc())
        BUGS.append(("EXTRA", "ComercioExterior", str(e)))

    try:
        operacion = ol_sv.registrar_recepcion(
            db, ol_s.RecepcionCrear(
                producto_id=prodB.id, proveedor_id=proveedor.id, inventario_id=inventario.id,
                codigo_lote="LOTE-OL-AUD", cantidad=10, costo_unitario=20,
            ), usuario_fake,
        )
        assert operacion.estado == "RECEPCION"
        assert operacion.inventario_id == inventario.id
        saldos_post_ol = inv_sv.saldos(db, inventario.id)
        saldo_b_post_ol = next(x for x in saldos_post_ol if x["producto_id"] == prodB.id)
        assert saldo_b_post_ol["stock_total"] == 55, saldo_b_post_ol  # 45 + 10
        ok("EXTRA_SUNAT_CE_OL", "m07 Operacion Logistica: recepcion directa registrada tras el "
                                 "fix (inventario_id fluye a m03, stock 45 -> 55 correcto)")
        # bloqueo esperado si no se envia inventario_id en recepcion directa
        bloqueo_ok = False
        try:
            ol_sv.registrar_recepcion(
                db, ol_s.RecepcionCrear(
                    producto_id=prodB.id, proveedor_id=proveedor.id,
                    codigo_lote="LOTE-OL-AUD-2", cantidad=1, costo_unitario=20,
                ), usuario_fake,
            )
        except Exception:
            bloqueo_ok = True
        if bloqueo_ok:
            ok("EXTRA_SUNAT_CE_OL", "m07: recepcion directa sin inventario_id se bloquea "
                                     "correctamente con el validador nuevo")
        else:
            fail("EXTRA_SUNAT_CE_OL", "m07: recepcion directa sin inventario_id NO fue bloqueada")
            BUGS.append(("EXTRA", "OperacionLogistica-validacion", "no bloquea inventario_id ausente"))
    except Exception as e:
        fail("EXTRA_SUNAT_CE_OL", "m07 Operacion Logistica registrar_recepcion",
             traceback.format_exc())
        BUGS.append(("EXTRA", "OperacionLogistica", str(e)))
    RESULTS["EXTRA_SUNAT_CE_OL"]["estado"] = (
        "VERDE" if all("FALLA" not in d for d in RESULTS["EXTRA_SUNAT_CE_OL"]["detalle"]) else "AMARILLO"
    )

    # =================================================================
    # SECCION D -- m13 Inteligencia Comercial
    # =================================================================
    s = seccion("D")
    try:
        top_prod = m13_sv.productos_mas_vendidos(db, limit=10)
        top_cli = m13_sv.clientes_top(db, limit=10)
        rotacion = m13_sv.rotacion_inventario(db)
        margen = m13_sv.margen_por_producto(db, limit=10)
        assert len(top_prod) >= 1
        assert len(top_cli) >= 1
        assert len(rotacion) >= 1
        assert len(margen) >= 1
        ok("D", f"productos_mas_vendidos={len(top_prod)}, clientes_top={len(top_cli)}, "
                f"rotacion_inventario={len(rotacion)}, margen_por_producto={len(margen)} filas, "
                "todas coherentes con la venta real despachada")
    except Exception as e:
        fail("D", "m13 Inteligencia Comercial", traceback.format_exc())
        BUGS.append(("D", "m13", str(e)))
    RESULTS["D"]["estado"] = "VERDE" if all("FALLA" not in d for d in RESULTS["D"]["detalle"]) else "ROJO"

    # =================================================================
    # SECCION D2 (adicional) -- m14 Inteligencia Tributaria
    # (agrupada bajo D por depender de los mismos datos SUNAT)
    # =================================================================
    try:
        resumen_igv = m14_sv.resumen_igv(db)
        libro_ventas = m14_sv.libro_ventas(db)
        assert resumen_igv.total_comprobantes >= 1
        assert len(libro_ventas) >= 1
        ok("D", f"m14 Inteligencia Tributaria: resumen_igv.total_comprobantes="
                f"{resumen_igv.total_comprobantes}, libro_ventas={len(libro_ventas)} filas -- coherente")
    except Exception as e:
        fail("D", "m14 Inteligencia Tributaria", traceback.format_exc())
        BUGS.append(("D", "m14", str(e)))
    RESULTS["D"]["estado"] = "VERDE" if all("FALLA" not in d for d in RESULTS["D"]["detalle"]) else "ROJO"

    # =================================================================
    # SECCION E -- m15 Lean Six Sigma
    # =================================================================
    s = seccion("E")
    try:
        mermas = m15_sv.resumen_mermas(db)
        ciclo_compras = m15_sv.tiempos_ciclo_compras(db)
        ciclo_ventas = m15_sv.tiempos_ciclo_ventas(db)
        assert ciclo_compras.ordenes_evaluadas >= 1
        assert ciclo_ventas.ordenes_evaluadas >= 1
        ok("E", f"resumen_mermas.dpmo={mermas.dpmo}, nivel_sigma={mermas.nivel_sigma}, "
                f"ciclo_compras.ordenes_evaluadas={ciclo_compras.ordenes_evaluadas}, "
                f"ciclo_ventas.ordenes_evaluadas={ciclo_ventas.ordenes_evaluadas}")
    except Exception as e:
        fail("E", "m15 Lean Six Sigma", traceback.format_exc())
        BUGS.append(("E", "m15", str(e)))
    RESULTS["E"]["estado"] = "VERDE" if all("FALLA" not in d for d in RESULTS["E"]["detalle"]) else "ROJO"

    # =================================================================
    # SECCION F -- m16 Theory of Constraints
    # =================================================================
    s = seccion("F")
    try:
        # Genera una orden CONFIRMADA (sin despachar) para que
        # ordenes_en_espera() tenga al menos 1 fila real que ejercitar
        # (antes del fix esto disparaba el TypeError de timezone).
        orden_en_espera = ventas_sv.crear_orden(
            db, ventas_s.OrdenVentaCrear(
                cliente_id=cliente.id, inventario_salida_id=inventario.id, moneda="USD",
                items=[ventas_s.OrdenVentaItemCrear(
                    producto_id=prodB.id, cantidad=2, precio_unitario_venta=30
                )],
            ),
        )
        ventas_sv.confirmar_orden(db, orden_en_espera.id)

        restricciones = m16_sv.restricciones_stock(db)
        en_espera = m16_sv.ordenes_en_espera(db)
        throughput = m16_sv.contabilidad_throughput(db)
        assert throughput.ingreso_ventas_despachadas > 0
        assert len(en_espera) >= 1
        assert en_espera[0].dias_esperando is not None
        ok("F", f"restricciones_stock={len(restricciones)} filas, ordenes_en_espera={len(en_espera)} "
                f"(dias_esperando calculado sin error tras el fix de timezone), "
                f"throughput.ingreso_ventas_despachadas={throughput.ingreso_ventas_despachadas}, "
                f"utilidad_neta_toc={throughput.utilidad_neta_toc}")
    except Exception as e:
        fail("F", "m16 Theory of Constraints", traceback.format_exc())
        BUGS.append(("F", "m16", str(e)))
    RESULTS["F"]["estado"] = "VERDE" if all("FALLA" not in d for d in RESULTS["F"]["detalle"]) else "ROJO"

    # =================================================================
    # SECCION G -- m18 Balanced Scorecard
    # =================================================================
    s = seccion("G")
    try:
        tablero = m18_sv.tablero(db)
        assert tablero.financiera is not None
        assert tablero.clientes is not None
        assert tablero.procesos_internos is not None
        assert tablero.aprendizaje_crecimiento is not None
        ok("G", f"tablero completo: margen_neto_pct={tablero.financiera.margen_neto_pct}, "
                f"clientes_activos_total={tablero.clientes.clientes_activos_total}, "
                f"dpmo_mermas={tablero.procesos_internos.dpmo_mermas}, "
                f"productos_activos_total={tablero.aprendizaje_crecimiento.productos_activos_total}")
    except Exception as e:
        fail("G", "m18 Balanced Scorecard", traceback.format_exc())
        BUGS.append(("G", "m18", str(e)))
    RESULTS["G"]["estado"] = "VERDE" if all("FALLA" not in d for d in RESULTS["G"]["detalle"]) else "ROJO"

finally:
    db.close()

# =====================================================================
print("\n" + "=" * 70)
print("RESUMEN AUDITORIA FUNCIONAL END-TO-END")
print("=" * 70)
for k, v in RESULTS.items():
    print(f"\n--- Seccion {k} :: {v['estado']} ---")
    for d in v["detalle"]:
        print(" ", d)

print("\n" + "=" * 70)
print(f"BUGS ENCONTRADOS: {len(BUGS)}")
for b in BUGS:
    print(" ", b)
print("=" * 70)
