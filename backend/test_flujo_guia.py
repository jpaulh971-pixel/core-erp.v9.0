"""Prueba funcional simple (no pytest) del flujo:

Inventario -> Compra/Recepcion -> Lote -> Venta -> Despacho -> Kardex SALIDA -> Guia

Valida:
  1. La guia se genera y lee el lote correcto (mismo lote_id que el Kardex).
  2. El Kardex no cambia despues de crear la guia (mismo numero de filas y
     mismos saldos).
  3. El stock (suma de cantidad_actual de lotes) es igual antes y despues
     de crear la guia.
"""
import os

os.environ["SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = "sqlite:///./_test_flujo_guia.db"

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.modules.m02_productos import schemas as productos_schemas  # noqa: E402
from app.modules.m02_productos import service as productos_service  # noqa: E402
from app.modules.m03_inventario import schemas as inventario_schemas  # noqa: E402
from app.modules.m03_inventario import service as inventario_service  # noqa: E402
from app.modules.m03_inventario.models import MovimientoKardex  # noqa: E402
from app.modules.m10_ventas import schemas as ventas_schemas  # noqa: E402
from app.modules.m10_ventas import service as ventas_service  # noqa: E402
from app.modules.m11_clientes import schemas as clientes_schemas  # noqa: E402
from app.modules.m11_clientes import service as clientes_service  # noqa: E402
from app.modules.m17_guias_remision import schemas as guias_schemas  # noqa: E402
from app.modules.m17_guias_remision import service as guias_service  # noqa: E402

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # --- Setup: inventario, producto, cliente ---
    inventario = inventario_service.crear_inventario(
        db, inventario_schemas.InventarioCrear(codigo="INV-1", nombre="Inventario Central")
    )
    producto = productos_service.crear_producto(
        db,
        productos_schemas.ProductoCrear(
            codigo="P-001", nombre="Producto Prueba", unidad_medida="UND", stock_minimo=0
        ),
    )
    cliente = clientes_service.crear_cliente(
        db,
        clientes_schemas.ClienteCrear(ruc="20123456789", razon_social="Cliente Prueba SAC"),
    )

    # --- Compra / Recepcion: crea el lote real via m03 (mismo servicio que usa m04_compras) ---
    inventario_service.registrar_ingreso(
        db,
        inventario_schemas.IngresoInventarioCrear(
            producto_id=producto.id,
            inventario_id=inventario.id,
            codigo_lote="LOTE-001",
            cantidad=100,
            costo_unitario=10,
            referencia="Recepcion compra #1 (prueba)",
        ),
    )

    kardex_antes = db.query(MovimientoKardex).count()
    producto_inventario = inventario_service.obtener_o_crear_producto_inventario(
        db, producto_id=producto.id, inventario_id=inventario.id
    )
    stock_antes = inventario_service.saldos(db, inventario.id)[0]["stock_total"]

    # --- Venta: orden -> confirmar -> despachar (genera Kardex SALIDA real) ---
    orden = ventas_service.crear_orden(
        db,
        ventas_schemas.OrdenVentaCrear(
            cliente_id=cliente.id,
            inventario_salida_id=inventario.id,
            items=[
                ventas_schemas.OrdenVentaItemCrear(
                    producto_id=producto.id, cantidad=30, precio_unitario_venta=15
                )
            ],
        ),
    )
    ventas_service.confirmar_orden(db, orden.id)
    orden = ventas_service.despachar_orden(db, orden.id)

    kardex_tras_despacho = (
        db.query(MovimientoKardex)
        .filter(MovimientoKardex.producto_inventario_id == producto_inventario.id)
        .all()
    )
    lote_id_real_kardex = kardex_tras_despacho[-1].lote_id
    saldo_resultante_kardex = float(kardex_tras_despacho[-1].saldo_resultante)

    kardex_count_tras_despacho = db.query(MovimientoKardex).count()
    stock_tras_despacho = inventario_service.saldos(db, inventario.id)[0]["stock_total"]

    # --- Generar Guia de Remision desde la venta despachada ---
    guia = guias_service.crear_desde_orden_venta(
        db, orden.id, guias_schemas.GuiaDesdeVentaCrear(motivo_traslado="VENTA")
    )

    kardex_count_tras_guia = db.query(MovimientoKardex).count()
    stock_tras_guia = inventario_service.saldos(db, inventario.id)[0]["stock_total"]

    # --- Aserciones ---
    assert guia.id is not None, "La guia no se creo"
    assert len(guia.detalles) == 1, f"Se esperaba 1 detalle, hay {len(guia.detalles)}"
    detalle = guia.detalles[0]
    assert detalle.lote_id == lote_id_real_kardex, (
        f"La guia leyo lote_id={detalle.lote_id} pero el Kardex real usa "
        f"lote_id={lote_id_real_kardex}"
    )
    assert float(detalle.cantidad) == 30.0, f"Cantidad incorrecta en detalle: {detalle.cantidad}"

    assert kardex_count_tras_guia == kardex_count_tras_despacho, (
        "El Kardex cambio de filas despues de crear la guia: "
        f"{kardex_count_tras_despacho} -> {kardex_count_tras_guia}"
    )
    assert stock_tras_guia == stock_tras_despacho, (
        "El stock cambio despues de crear la guia: "
        f"{stock_tras_despacho} -> {stock_tras_guia}"
    )
    assert stock_tras_despacho == stock_antes - 30, "El despacho no descontó el stock esperado"

    print("OK - Guia creada:", guia.numero_guia, "lote_id:", detalle.lote_id)
    print("OK - Kardex sin cambios tras crear guia:", kardex_count_tras_guia, "filas")
    print("OK - Stock igual antes/despues de crear guia:", stock_tras_despacho, "==", stock_tras_guia)
    print("TODAS LAS PRUEBAS PASARON")

finally:
    db.close()
    engine.dispose()
    if os.path.exists("_test_flujo_guia.db"):
        os.remove("_test_flujo_guia.db")
