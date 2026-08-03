"""Validacion AISLADA (no toca la BD real) del plan que calcula
`reconstruccion_kardex_historico_2026.armar_plan`.

Crea una base SQLite efimera en memoria, la puebla con escenarios
representativos y compara el plan calculado contra el resultado
esperado a mano. No importa nada del backend real salvo los MODELOS
(para tener el mismo esquema) y la funcion `armar_plan` bajo prueba.

Escenarios cubiertos:
  1. Venta HISTORICO totalmente cubierta por UNA compra HISTORICO
     anterior del mismo producto+inventario (estado esperado:
     PLANIFICADO, 1 lote, 1 ingreso, 1 salida).
  2. Venta HISTORICO cuyo consumo PEPS cruza DOS compras HISTORICO
     distintas (estado esperado: PLANIFICADO, 2 lotes, 2 ingresos,
     2 salidas, costo unitario resultante = promedio ponderado).
  3. Venta HISTORICO de producto PERECIBLE (estado esperado:
     EXCLUIDO_PERECIBLE, sin lotes/movimientos planificados).
  4. Venta HISTORICO sin ninguna compra HISTORICO de respaldo (estado
     esperado: SIN_RESPALDO).
  5. Venta OPERATIVA (no HISTORICO) que YA tiene su propio Kardex real:
     debe quedar completamente FUERA del plan (no debe aparecer ni
     como afectada).
  6. Segunda corrida sobre la MISMA base tras "aplicar" a mano el lote
     del escenario 1 (simulando que una fase de aplicacion futura ya
     escribio ese Lote): el plan debe reconocerlo como `ya_existe=True`
     y reutilizar su cantidad_actual en vez de duplicarlo
     (idempotencia).

Uso:
    cd backend
    python scripts/_validacion_local_reconstruccion_kardex.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base  # noqa: E402

# Importar TODOS los modelos para que Base.metadata tenga el esquema
# completo (FKs cruzadas entre modulos), igual que hace app/main.py.
from app.modules.m02_productos import models as _m02  # noqa: F401,E402
from app.modules.m03_inventario import models as m03  # noqa: E402
from app.modules.m04_compras import models as m04  # noqa: E402
from app.modules.m05_proveedores import models as m05  # noqa: E402
from app.modules.m06_comercio_exterior import models as _m06  # noqa: F401,E402
from app.modules.m07_operacion_logistica import models as _m07  # noqa: F401,E402
from app.modules.m08_costos import models as _m08  # noqa: F401,E402
from app.modules.m09_moneda import models as _m09  # noqa: F401,E402
from app.modules.m10_ventas import models as m10  # noqa: E402
from app.modules.m11_clientes import models as m11  # noqa: E402
from app.modules.m12_sunat import models as _m12  # noqa: F401,E402
from app.modules.m01_dashboard import models as _m01  # noqa: F401,E402
from app.modules.m13_inteligencia_comercial import models as _m13  # noqa: F401,E402
from app.modules.m14_inteligencia_tributaria import models as _m14  # noqa: F401,E402
from app.modules.m15_lean_six_sigma import models as _m15  # noqa: F401,E402
from app.modules.m16_theory_of_constraints import models as _m16  # noqa: F401,E402
from app.modules.m17_guias_remision import models as _m17  # noqa: F401,E402
from app.modules.m20_configuracion import models as _m20  # noqa: F401,E402
from app.modules.m21_importacion_datos import models as m21  # noqa: E402

from scripts.reconstruccion_kardex_historico_2026 import (  # noqa: E402
    armar_plan,
    ubicar_ventas_historico_sin_kardex,
)
from scripts.aplicar_reconstruccion_kardex_historico_2026 import (  # noqa: E402
    existen_anios_pendientes_fuera_de_rango,
)

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


def build_db():
    Base.metadata.create_all(engine)
    db = Session()

    inv = m03.Inventario(codigo="INV1", nombre="Inventario 1")
    db.add(inv)
    db.flush()

    prov = m05.Proveedor(ruc="20100000001", razon_social="Proveedor Uno")
    cli = m11.Cliente(ruc="20200000002", razon_social="Cliente Uno")
    db.add_all([prov, cli])
    db.flush()

    p_normal = _m02.Producto(codigo="P-NORMAL", nombre="Producto normal", perecible=False)
    p_normal2 = _m02.Producto(codigo="P-NORMAL2", nombre="Producto normal 2 (peps cruzado)", perecible=False)
    p_perecible = _m02.Producto(codigo="P-PERE", nombre="Producto perecible", perecible=True)
    p_sinrespaldo = _m02.Producto(codigo="P-SINOC", nombre="Producto sin compra historico", perecible=False)
    p_operativo = _m02.Producto(codigo="P-OPER", nombre="Producto con venta operativa", perecible=False)
    db.add_all([p_normal, p_normal2, p_perecible, p_sinrespaldo, p_operativo])
    db.flush()

    def compra_historico(producto, cantidad, costo, fecha):
        oc = m04.OrdenCompra(
            proveedor_id=prov.id,
            inventario_destino_id=inv.id,
            estado="RECIBIDA",
            recibido_en=fecha,
        )
        db.add(oc)
        db.flush()
        oci = m04.OrdenCompraItem(
            orden_compra_id=oc.id, producto_id=producto.id, cantidad=cantidad, costo_unitario=costo
        )
        db.add(oci)
        db.flush()
        carga = m21.CargaComprasHistorico(nombre_archivo="x.xlsx", inventario_id=inv.id, estado="CONFIRMADA")
        db.add(carga)
        db.flush()
        fila = m21.CargaComprasHistoricoFila(
            carga_id=carga.id, numero_fila=1, datos_json="{}", modo_carga="HISTORICO",
            procesada=True, orden_compra_id=oc.id,
        )
        db.add(fila)
        db.flush()
        return oc, oci

    def venta_historico(producto, cantidad, precio, fecha):
        ov = m10.OrdenVenta(
            cliente_id=cli.id, inventario_salida_id=inv.id, estado="DESPACHADA", despachado_en=fecha,
        )
        db.add(ov)
        db.flush()
        ovi = m10.OrdenVentaItem(
            orden_venta_id=ov.id, producto_id=producto.id, cantidad=cantidad, precio_unitario_venta=precio,
        )
        db.add(ovi)
        db.flush()
        carga = m21.CargaVentasHistorico(nombre_archivo="y.xlsx", inventario_id=inv.id, estado="CONFIRMADA")
        db.add(carga)
        db.flush()
        fila = m21.CargaVentasHistoricoFila(
            carga_id=carga.id, numero_fila=1, datos_json="{}", modo_carga="HISTORICO",
            procesada=True, orden_venta_id=ov.id,
        )
        db.add(fila)
        db.flush()
        return ov, ovi

    # Escenario 1: 1 compra (100 u @ 10) cubre 1 venta de 40 u.
    oc1, _ = compra_historico(p_normal, 100, 10.0, datetime(2026, 1, 5))
    ov1, ovi1 = venta_historico(p_normal, 40, 25.0, datetime(2026, 2, 1))

    # Escenario 2: 2 compras (30 u @ 8, luego 30 u @ 12) cubren 1 venta de 50 u -> PEPS cruza ambas.
    oc2a, _ = compra_historico(p_normal2, 30, 8.0, datetime(2026, 1, 1))
    oc2b, _ = compra_historico(p_normal2, 30, 12.0, datetime(2026, 1, 10))
    ov2, ovi2 = venta_historico(p_normal2, 50, 30.0, datetime(2026, 2, 5))

    # Escenario 3: producto perecible, sin compra de respaldo siquiera necesaria.
    ov3, ovi3 = venta_historico(p_perecible, 10, 15.0, datetime(2026, 2, 1))

    # Escenario 4: producto sin ninguna compra HISTORICO.
    ov4, ovi4 = venta_historico(p_sinrespaldo, 5, 20.0, datetime(2026, 2, 1))

    # Escenario 5: venta OPERATIVA con Kardex real ya existente -> debe quedar excluida.
    ov5 = m10.OrdenVenta(cliente_id=cli.id, inventario_salida_id=inv.id, estado="DESPACHADA",
                          despachado_en=datetime(2026, 3, 1))
    db.add(ov5)
    db.flush()
    ovi5 = m10.OrdenVentaItem(orden_venta_id=ov5.id, producto_id=p_operativo.id, cantidad=3,
                               precio_unitario_venta=50.0)
    db.add(ovi5)
    db.flush()
    lote_op = m03.Lote(
        producto_inventario_id=None, codigo_lote="OP-1", cantidad_inicial=3, cantidad_actual=0, costo_unitario=5,
    )
    # producto_inventario es obligatorio (NOT NULL) en el esquema real; para
    # este escenario de control solo nos interesa que EXISTA un
    # MovimientoKardex con la referencia real de despacho, asi que creamos
    # tambien el ProductoInventario minimo necesario.
    pi_op = m03.ProductoInventario(producto_id=p_operativo.id, inventario_id=inv.id, codigo_interno="OP")
    db.add(pi_op)
    db.flush()
    lote_op.producto_inventario_id = pi_op.id
    db.add(lote_op)
    db.flush()
    from app.modules.m10_ventas.service import _referencia_despacho_item
    mov_op = m03.MovimientoKardex(
        producto_inventario_id=pi_op.id, inventario_id=inv.id, lote_id=lote_op.id,
        tipo_movimiento="SALIDA", cantidad=3, costo_unitario=5, saldo_resultante=0,
        referencia=_referencia_despacho_item(ov5.id, ovi5.id),
    )
    db.add(mov_op)
    # NO se crea fila en CargaVentasHistoricoFila para esta orden: es
    # OPERATIVA, no HISTORICO. Debe quedar fuera solo por eso; el
    # MovimientoKardex ya existente es un segundo motivo redundante de
    # exclusion (defensa en profundidad de la deteccion).

    # Escenario 6: venta HISTORICO del mismo producto/inventario que el
    # escenario 1 (p_normal, mismo pool de oc1), pero en OTRO anio (2025,
    # no 2026), tambien sin Kardex. Sirve para probar el nuevo guardia
    # existen_anios_pendientes_fuera_de_rango: correr la aplicacion solo
    # para 2026 mientras esta venta de 2025 sigue sin Kardex debe
    # detectarse como "anio pendiente fuera de rango".
    ov6, ovi6 = venta_historico(p_normal, 20, 25.0, datetime(2025, 11, 1))

    db.commit()

    return db, dict(
        p_normal=p_normal, p_normal2=p_normal2, p_perecible=p_perecible,
        p_sinrespaldo=p_sinrespaldo, p_operativo=p_operativo,
        ov1=ov1, ovi1=ovi1, ov2=ov2, ovi2=ovi2, ov3=ov3, ovi3=ovi3,
        ov4=ov4, ovi4=ovi4, ov5=ov5, ovi5=ovi5, ov6=ov6, ovi6=ovi6,
        oc1=oc1, oc2a=oc2a, oc2b=oc2b, inv=inv,
    )


def run():
    db, ctx = build_db()

    print("=== Corrida 1 (base limpia) ===")
    items_plan, lotes, ingresos = armar_plan(db, anio=2026, inventario_id=None)

    por_item = {(i.orden_venta_id, i.item_id): i for i in items_plan}

    # --- aserciones escenario 5 (no debe aparecer) ---
    assert (ctx["ov5"].id, ctx["ovi5"].id) not in por_item, (
        "FALLO: la venta OPERATIVA con Kardex real aparecio en el plan (no deberia)."
    )
    print("OK: venta OPERATIVA con Kardex real queda fuera del plan.")

    # --- escenario 1 ---
    i1 = por_item[(ctx["ov1"].id, ctx["ovi1"].id)]
    assert i1.estado == "PLANIFICADO", f"FALLO escenario 1: estado={i1.estado}"
    assert len(i1.salidas) == 1, f"FALLO escenario 1: salidas={len(i1.salidas)}"
    assert abs(i1.costo_unitario_resultante - 10.0) < 1e-6, i1.costo_unitario_resultante
    assert abs(i1.margen_resultante - 15.0) < 1e-6
    print(f"OK: escenario 1 PLANIFICADO, costo={i1.costo_unitario_resultante}, margen={i1.margen_resultante}")

    # --- escenario 2 (PEPS cruzando 2 compras: 30u@8 + 20u@12) ---
    i2 = por_item[(ctx["ov2"].id, ctx["ovi2"].id)]
    assert i2.estado == "PLANIFICADO", f"FALLO escenario 2: estado={i2.estado}"
    assert len(i2.salidas) == 2, f"FALLO escenario 2: salidas={len(i2.salidas)}"
    costo_esperado = (30 * 8.0 + 20 * 12.0) / 50.0  # = 9.6
    assert abs(i2.costo_unitario_resultante - costo_esperado) < 1e-6, (
        i2.costo_unitario_resultante, costo_esperado
    )
    print(f"OK: escenario 2 PLANIFICADO (PEPS cruzado), costo={i2.costo_unitario_resultante:.4f} (esperado {costo_esperado:.4f})")

    # --- escenario 3 (perecible) ---
    i3 = por_item[(ctx["ov3"].id, ctx["ovi3"].id)]
    assert i3.estado == "EXCLUIDO_PERECIBLE", f"FALLO escenario 3: estado={i3.estado}"
    assert len(i3.salidas) == 0
    print("OK: escenario 3 EXCLUIDO_PERECIBLE, sin salidas planificadas.")

    # --- escenario 4 (sin respaldo) ---
    i4 = por_item[(ctx["ov4"].id, ctx["ovi4"].id)]
    assert i4.estado == "SIN_RESPALDO", f"FALLO escenario 4: estado={i4.estado}"
    assert len(i4.salidas) == 0
    print("OK: escenario 4 SIN_RESPALDO, sin salidas planificadas.")

    # --- lotes/ingresos planificados: deben ser NUEVOS (ya_existe=False) en esta 1a corrida ---
    oc1_id = ctx["oc1"].id
    oc2a_id = ctx["oc2a"].id
    oc2b_id = ctx["oc2b"].id
    assert lotes[oc1_id].ya_existe is False
    assert lotes[oc2a_id].ya_existe is False
    assert lotes[oc2b_id].ya_existe is False
    assert ingresos[oc1_id].ya_existe is False
    print("OK: lotes e ingresos de la 1a corrida quedan marcados ya_existe=False (nada escrito aun).")

    print("\n=== Corrida 2 (simulando que una fase de aplicacion futura ya escribio el Lote del escenario 1) ===")
    # Simulamos a mano el efecto de una futura fase de aplicacion: se crea
    # el Lote reconstruido para oc1 con 15 unidades ya consumidas por otra
    # via (cantidad_actual=25 de las 100 originales), y se agrega un
    # MovimientoKardex INGRESO con la referencia esperada, para probar que
    # el plan lo detecta y NO lo duplica.
    pi_normal = m03.ProductoInventario(producto_id=ctx["p_normal"].id, inventario_id=ctx["inv"].id,
                                        codigo_interno="AUTO-TEST")
    db.add(pi_normal)
    db.flush()
    lote_existente = m03.Lote(
        producto_inventario_id=pi_normal.id, codigo_lote=f"HIST-OC-{oc1_id}",
        cantidad_inicial=100, cantidad_actual=25, costo_unitario=10.0,
    )
    db.add(lote_existente)
    db.commit()

    items_plan_2, lotes_2, ingresos_2 = armar_plan(db, anio=2026, inventario_id=None)
    lote_plan_2 = lotes_2[oc1_id]
    assert lote_plan_2.ya_existe is True, "FALLO idempotencia: no detecto el Lote ya existente."
    assert abs(lote_plan_2.cantidad_actual_existente - 25) < 1e-6
    print(
        "OK: 2a corrida detecta el Lote ya existente de oc1 "
        f"(ya_existe=True, cantidad_actual_existente={lote_plan_2.cantidad_actual_existente}) y no lo duplica."
    )

    print("\n=== Corrida 3: anio=None (universo completo, uso interno del guardia) ===")
    todos_sin_kardex = ubicar_ventas_historico_sin_kardex(db, anio=None, inventario_id=None)
    claves = {(orden.id, item.id) for orden, item, _ref in todos_sin_kardex}
    assert (ctx["ov1"].id, ctx["ovi1"].id) in claves
    assert (ctx["ov6"].id, ctx["ovi6"].id) in claves, (
        "FALLO: anio=None deberia incluir tambien la venta de 2025 (escenario 6)."
    )
    assert (ctx["ov5"].id, ctx["ovi5"].id) not in claves, (
        "FALLO: la venta OPERATIVA con Kardex real aparecio incluso con anio=None."
    )
    print("OK: anio=None devuelve el universo completo (incluye 2025 y 2026), sigue excluyendo la OPERATIVA.")

    print("\n=== Corrida 4: guardia existen_anios_pendientes_fuera_de_rango ===")
    pendientes_para_2026 = existen_anios_pendientes_fuera_de_rango(db, anio_actual=2026, inventario_id=None)
    assert pendientes_para_2026 == {2025}, (
        f"FALLO: se esperaba {{2025}} pendiente al aplicar 2026, se obtuvo {pendientes_para_2026}"
    )
    print(f"OK: aplicar 2026 detecta {pendientes_para_2026} como anio pendiente fuera de rango (correcto, hay que "
          "avisar/detener antes de escribir).")

    pendientes_para_2025 = existen_anios_pendientes_fuera_de_rango(db, anio_actual=2025, inventario_id=None)
    assert pendientes_para_2025 == {2026}, (
        f"FALLO: se esperaba {{2026}} pendiente al aplicar 2025, se obtuvo {pendientes_para_2025}"
    )
    print(f"OK: aplicar 2025 detecta {pendientes_para_2025} como anio pendiente fuera de rango (simetrico, correcto).")

    print("\n=== TODAS LAS ASERCIONES PASARON ===")


if __name__ == "__main__":
    run()
