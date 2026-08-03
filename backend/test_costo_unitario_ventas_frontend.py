"""Smoke test funcional (no pytest) — FASE 4, frontend Ventas.

Reproduce el ejemplo del enunciado: producto TEST-001, costo oficial 450,
precio de venta 600. Valida:

  1. `OrdenVentaItemOut.costo_unitario` (lo que ahora pinta el modal
     "Detalle de orden" de ventas.js como "Costo Unitario") = 450, SOLO
     después de despachar (antes debe ser None, a propósito).
  2. Margen = precio_unitario_venta - costo_unitario = 600 - 450 = 150,
     y su porcentaje = 150 / 600 * 100 = 25% -- misma fórmula que ya usa
     el Backend en m08_costos/m13_inteligencia_comercial, replicada aquí
     solo para verificar que coincide (no se está probando un cálculo
     nuevo de costeo).
  3. Comparación cruzada con Kardex (m03, fuente original PEPS/FEFO),
     Inventario/saldos (m03) y Reportes (m19, inventario-valorizado):
     las 4 fuentes deben coincidir en 450 para el costo unitario del
     producto restante en stock.

No se llama a ningún endpoint HTTP nuevo ni se modifica ningún módulo de
costeo: solo se ejercitan los services ya existentes, igual patrón que
test_flujo_guia.py y test_costo_unitario_inventario_frontend.py.
"""
import os

os.environ["SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = "sqlite:///./_test_costo_unitario_ventas_frontend.db"

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.modules.m02_productos import schemas as productos_schemas  # noqa: E402
from app.modules.m02_productos import service as productos_service  # noqa: E402
from app.modules.m03_inventario import schemas as inventario_schemas  # noqa: E402
from app.modules.m03_inventario import service as inventario_service  # noqa: E402
from app.modules.m10_ventas import schemas as ventas_schemas  # noqa: E402
from app.modules.m10_ventas import service as ventas_service  # noqa: E402
from app.modules.m11_clientes import schemas as clientes_schemas  # noqa: E402
from app.modules.m11_clientes import service as clientes_service  # noqa: E402
from app.modules.m19_reportes import service as reportes_service  # noqa: E402

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # --- Setup: inventario, producto TEST-001, cliente ---
    inventario = inventario_service.crear_inventario(
        db, inventario_schemas.InventarioCrear(codigo="INV-001", nombre="Inventario Central")
    )
    producto = productos_service.crear_producto(
        db,
        productos_schemas.ProductoCrear(
            codigo="TEST-001", nombre="Producto de prueba", unidad_medida="UND", stock_minimo=0
        ),
    )
    cliente = clientes_service.crear_cliente(
        db, clientes_schemas.ClienteCrear(ruc="20123456789", razon_social="Cliente Prueba SAC")
    )

    # --- Ingreso real vía m03_inventario (motor PEPS/FEFO real, intacto):
    #     4 unidades a costo_unitario=450 ---
    inventario_service.registrar_ingreso(
        db,
        inventario_schemas.IngresoInventarioCrear(
            producto_id=producto.id,
            inventario_id=inventario.id,
            codigo_lote="LOTE-TEST-001",
            cantidad=4,
            costo_unitario=450,
            referencia="Recepcion de prueba (smoke test FASE 4)",
        ),
    )

    # --- Orden de venta: 1 unidad a precio_unitario_venta=600 ---
    orden = ventas_service.crear_orden(
        db,
        ventas_schemas.OrdenVentaCrear(
            cliente_id=cliente.id,
            inventario_salida_id=inventario.id,
            items=[
                ventas_schemas.OrdenVentaItemCrear(
                    producto_id=producto.id, cantidad=1, precio_unitario_venta=600
                )
            ],
        ),
    )

    # 1a) ANTES de despachar: costo_unitario debe ser None a propósito
    #     (el costo real aún no se conoce) -- lo que ventas.js pinta como "—".
    orden_borrador = ventas_service.obtener_orden(db, orden.id)
    assert orden_borrador.items[0].costo_unitario is None
    print("1a) orden BORRADOR -> costo_unitario=None (correcto: ventas.js mostrará \"—\")")

    orden = ventas_service.confirmar_orden(db, orden.id)
    orden = ventas_service.despachar_orden(db, orden.id)  # dispara salida real por FEFO (m03)

    # 1b) DESPUÉS de despachar: costo_unitario = 450 (lo que ahora pinta
    #     la columna "Costo Unitario" del modal Detalle de orden).
    orden_despachada = ventas_service.obtener_orden(db, orden.id)
    item = orden_despachada.items[0]
    assert item.costo_unitario == 450.0
    print(f"1b) orden DESPACHADA -> costo_unitario={item.costo_unitario}")

    # 2) Margen (misma fórmula que ventas.js: margenItem()).
    # NOTA: al llamar al service directamente (sin pasar por Pydantic/FastAPI
    # como hace la API real), `precio_unitario_venta` llega como Decimal
    # (columna Numeric del ORM); en el JSON real que consume ventas.js ya
    # llega como float (FastAPI lo serializa vía OrdenVentaItemOut). Se
    # convierte aquí solo para poder comparar, sin tocar ningún valor.
    precio_venta = float(item.precio_unitario_venta)
    margen_unitario = precio_venta - item.costo_unitario
    margen_pct = (margen_unitario / precio_venta) * 100
    assert precio_venta == 600.0
    assert margen_unitario == 150.0
    assert round(margen_pct, 2) == 25.0
    print(f"2) precio_unitario_venta={precio_venta} margen={margen_unitario} margen_pct={margen_pct}%")

    # 3) Comparación cruzada: Kardex, Saldos (Inventario) y Reporte
    #    valorizado deben seguir mostrando 450 para el costo del producto
    #    (el lote restante, 3 unidades, sigue costeado a 450 -- PEPS con
    #    un solo lote no cambia el costo unitario al vender parte de él).
    producto_inventario = inventario_service.obtener_o_crear_producto_inventario(
        db, producto_id=producto.id, inventario_id=inventario.id
    )
    kardex = inventario_service.kardex_producto_inventario(db, producto_inventario.id)
    costo_kardex_salida = next(m.costo_unitario for m in kardex if m.tipo_movimiento == "SALIDA")
    assert costo_kardex_salida == 450.0
    print(f"3a) kardex (SALIDA) -> costo_unitario={costo_kardex_salida}")

    saldo = inventario_service.saldos(db, inventario.id)[0]
    assert saldo["costo_unitario_promedio"] == 450.0
    assert saldo["stock_total"] == 3.0  # 4 ingresadas - 1 despachada
    print(f"3b) saldos() -> costo_unitario_promedio={saldo['costo_unitario_promedio']} stock_total={saldo['stock_total']}")

    reporte = reportes_service.reporte_inventario_valorizado(db)
    fila_valorizada = next(p for p in reporte.productos if p.producto_id == producto.id)
    assert fila_valorizada.valor_promedio_unitario == 450.0
    print(f"3c) inventario_valorizado() -> valor_promedio_unitario={fila_valorizada.valor_promedio_unitario}")

    print(
        "\nOK: Ventas (item.costo_unitario) = Kardex = Inventario (saldos) = "
        "Reporte valorizado = 450.0  |  Margen del ítem = 150.0 (25.0%)"
    )
finally:
    db.close()
    try:
        os.remove("./_test_costo_unitario_ventas_frontend.db")
    except OSError:
        pass
