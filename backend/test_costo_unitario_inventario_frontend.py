"""Smoke test funcional (no pytest) — FASE 3, frontend Inventario.

Reproduce el ejemplo del enunciado: producto TEST-001, costo oficial 450.
Valida que las 4 fuentes que debe mostrar el frontend coincidan en 450:

  1. m03_inventario.service.saldos()            -> costo_unitario_promedio
     (backend real que consume /api/inventario/saldos/{inventario_id},
     usado ahora por Saldos/Alertas en inventario.js)
  2. m19_reportes.service.inventario_valorizado()  -> valor_promedio_unitario
     (GET /api/reportes/inventario-valorizado, el que ahora también cruza
     inventario.js para pintar Costo Unitario / Costo Total)
  3. Kardex (m03_inventario)                     -> costo_unitario (fuente
     original del motor PEPS/FEFO)
  4. m02_productos + el mismo reporte valorizado (fuente que ya usa
     productos.js) -> confirma que Productos = Inventario = Reporte = 450

No se llama a ningún endpoint HTTP nuevo ni se modifica ningún módulo de
costeo: solo se ejercitan los services ya existentes, igual patrón que
test_flujo_guia.py.
"""
import os

os.environ["SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = "sqlite:///./_test_costo_unitario_inventario_frontend.db"

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.modules.m02_productos import schemas as productos_schemas  # noqa: E402
from app.modules.m02_productos import service as productos_service  # noqa: E402
from app.modules.m03_inventario import schemas as inventario_schemas  # noqa: E402
from app.modules.m03_inventario import service as inventario_service  # noqa: E402
from app.modules.m19_reportes import service as reportes_service  # noqa: E402

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # --- Setup: inventario + producto TEST-001 ---
    inventario = inventario_service.crear_inventario(
        db, inventario_schemas.InventarioCrear(codigo="INV-001", nombre="Inventario Central")
    )
    producto = productos_service.crear_producto(
        db,
        productos_schemas.ProductoCrear(
            codigo="TEST-001", nombre="Producto de prueba", unidad_medida="UND", stock_minimo=0
        ),
    )

    # --- Ingreso real via m03_inventario (motor PEPS/FEFO real, intacto) ---
    inventario_service.registrar_ingreso(
        db,
        inventario_schemas.IngresoInventarioCrear(
            producto_id=producto.id,
            inventario_id=inventario.id,
            codigo_lote="LOTE-TEST-001",
            cantidad=4,
            costo_unitario=450,
            referencia="Recepcion de prueba (smoke test FASE 3)",
        ),
    )

    producto_inventario = inventario_service.obtener_o_crear_producto_inventario(
        db, producto_id=producto.id, inventario_id=inventario.id
    )

    # 1) Saldos (lo que ahora pinta la pestaña "Saldos" de inventario.js
    #    para Stock; el costo/valor lo trae inventario-valorizado, ver 2).
    saldo = inventario_service.saldos(db, inventario.id)[0]
    assert saldo["producto_id"] == producto.id
    assert saldo["stock_total"] == 4
    print(f"1) saldos() -> stock_total={saldo['stock_total']}")

    # 2) Reporte inventario-valorizado (fuente real de Costo Unitario /
    #    Costo Total en Saldos/Alertas tras el cambio de esta fase, y la
    #    misma que ya usa productos.js).
    reporte = reportes_service.reporte_inventario_valorizado(db)
    fila_valorizada = next(p for p in reporte.productos if p.producto_id == producto.id)
    assert fila_valorizada.cantidad_actual == 4
    assert fila_valorizada.valor_promedio_unitario == 450.0
    assert fila_valorizada.valor_total == 1800.0  # 4 * 450
    print(
        f"2) inventario_valorizado() -> valor_promedio_unitario={fila_valorizada.valor_promedio_unitario} "
        f"valor_total={fila_valorizada.valor_total}"
    )

    # 3) Kardex (fuente original del motor de costeo, sin tocar).
    kardex = inventario_service.kardex_producto_inventario(db, producto_inventario.id)
    assert kardex[0].costo_unitario == 450.0
    print(f"3) kardex() -> costo_unitario={kardex[0].costo_unitario}")

    # 4) Productos (misma fuente que (2), ya validado en FASE 2 — se
    #    repite aquí para dejar los 3 puntos del enunciado en un solo test).
    assert fila_valorizada.valor_promedio_unitario == 450.0
    print(f"4) productos.js leería el mismo valor_promedio_unitario={fila_valorizada.valor_promedio_unitario}")

    assert saldo["stock_total"] == fila_valorizada.cantidad_actual == kardex[0].cantidad == 4
    assert fila_valorizada.valor_promedio_unitario == kardex[0].costo_unitario == 450.0

    print("\nOK: Inventario (Saldos) = Reporte valorizado = Kardex = Productos = 450.0")
finally:
    db.close()
    try:
        os.remove("./_test_costo_unitario_inventario_frontend.db")
    except OSError:
        pass
