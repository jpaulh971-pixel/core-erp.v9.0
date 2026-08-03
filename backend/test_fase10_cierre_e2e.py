"""Prueba E2E rapida (no pytest) de cierre de Fase 10 - Importacion de
Ventas del almacen.

Flujo verificado, tal como lo pide el objetivo de este turno:

    Excel Venta -> previsualizar() -> confirmar() (crea, confirma y
    despacha la orden internamente) -> Salida de Inventario -> Kardex
    actualizado -> Reporte de Ventas (m19_reportes).

No ejercita ningun endpoint HTTP nuevo ni modifica ningun modulo de
costeo/inventario: usa los services reales ya existentes, mismo patron
que test_flujo_guia.py y test_costo_unitario_ventas_frontend.py.
"""
import io
import os

os.environ["SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = "sqlite:///./_test_fase10_cierre_e2e.db"

import openpyxl  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.modules.m02_productos import schemas as productos_schemas  # noqa: E402
from app.modules.m02_productos import service as productos_service  # noqa: E402
from app.modules.m03_inventario import schemas as inventario_schemas  # noqa: E402
from app.modules.m03_inventario import service as inventario_service  # noqa: E402
from app.modules.m03_inventario.models import MovimientoKardex  # noqa: E402
from app.modules.m10_ventas import importacion_service  # noqa: E402
from app.modules.m11_clientes import schemas as clientes_schemas  # noqa: E402
from app.modules.m11_clientes import service as clientes_service  # noqa: E402
from app.modules.m19_reportes import service as reportes_service  # noqa: E402
from app.modules.m20_configuracion import models as configuracion_models  # noqa: E402,F401

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # --- Setup: 1 inventario, 1 producto, 1 cliente ---
    inventario = inventario_service.crear_inventario(
        db, inventario_schemas.InventarioCrear(codigo="INV-E2E", nombre="Almacen E2E Cierre")
    )
    producto = productos_service.crear_producto(
        db,
        productos_schemas.ProductoCrear(
            codigo="EXP-E2E", nombre="Producto E2E Cierre", unidad_medida="KG", stock_minimo=0
        ),
    )
    cliente = clientes_service.crear_cliente(
        db, clientes_schemas.ClienteCrear(ruc="20111111111", razon_social="Cliente E2E SAC")
    )

    # --- Stock inicial real vía m03 (motor PEPS/FEFO real, intacto):
    #     100 kg a costo_unitario=10 ---
    inventario_service.registrar_ingreso(
        db,
        inventario_schemas.IngresoInventarioCrear(
            producto_id=producto.id,
            inventario_id=inventario.id,
            codigo_lote="LOTE-E2E-1",
            cantidad=100,
            costo_unitario=10,
            referencia="Recepcion E2E cierre ventas almacen",
        ),
    )
    saldo_antes = next(
        s["stock_total"] for s in inventario_service.saldos(db, inventario.id) if s["producto_id"] == producto.id
    )
    kardex_antes = db.query(MovimientoKardex).count()
    assert saldo_antes == 100, f"Saldo inicial inesperado: {saldo_antes}"

    # --- Construir Excel real de Ventas con el encabezado soportado ---
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "Orden de Venta", "Vendedor", "Moneda", "Cantidad", "Unidad de Medida",
        "Descripcion", "Precio Venta", "Subtotal", "IGV", "Total",
        "Fecha de Emision", "Dias de Credito", "Fecha de Vencimiento",
        "Factura", "Estado", "RUC", "Cliente", "Anio", "Mes",
        "Guia de Remision", "Cultivo", "Fundo",
    ])
    ws.append([
        "OV-E2E-001", "Vendedor Prueba", "USD", 20, "KG",
        "Producto E2E Cierre", 15, 300, 54, 354,
        "01/08/2026", 30, "31/08/2026",
        "F001-E2E", "", "20111111111", "Cliente E2E SAC", 2026, "Agosto",
        "", "", "",
    ])
    buffer = io.BytesIO()
    wb.save(buffer)
    contenido = buffer.getvalue()

    # --- previsualizar(): NO debe escribir nada ---
    preview = importacion_service.previsualizar(db, inventario.id, "ventas_e2e.xlsx", contenido)
    assert preview.total_filas == 1
    assert preview.filas_validas == 1
    assert preview.filas_con_error == 0
    assert preview.ordenes_a_crear == 1
    saldo_tras_preview = next(
        s["stock_total"] for s in inventario_service.saldos(db, inventario.id)
        if s["producto_id"] == producto.id
    )
    assert saldo_tras_preview == 100, "previsualizar() NO debe tocar el inventario."
    print(f"PREVISUALIZAR OK: {preview.filas_validas} fila(s) valida(s), inventario intacto (100).")

    # --- confirmar(): crea -> confirma -> despacha la orden ---
    resultado = importacion_service.confirmar(db, inventario.id, "ventas_e2e.xlsx", contenido)
    assert len(resultado.ordenes_creadas) == 1
    orden_creada = resultado.ordenes_creadas[0]
    assert orden_creada.estado == "DESPACHADA", f"Estado inesperado: {orden_creada.estado}"
    print(f"CONFIRMAR OK: orden {orden_creada.orden_venta_id} estado {orden_creada.estado}")

    # --- Verificar Inventario: salida real, sin duplicar stock ---
    saldo_despues = next(
        s["stock_total"] for s in inventario_service.saldos(db, inventario.id)
        if s["producto_id"] == producto.id
    )
    assert saldo_despues == 80, f"Saldo esperado 80 (100-20), obtenido {saldo_despues}"
    print(f"INVENTARIO OK: saldo 100 -> {saldo_despues} (salida de 20, sin duplicar).")

    # --- Verificar Kardex: 1 movimiento nuevo de SALIDA, FEFO (mismo lote) ---
    kardex_despues = db.query(MovimientoKardex).count()
    assert kardex_despues == kardex_antes + 1, "Debe haber exactamente 1 movimiento nuevo de Kardex."
    ultimo_mov = (
        db.query(MovimientoKardex)
        .order_by(MovimientoKardex.id.desc())
        .first()
    )
    assert ultimo_mov.tipo_movimiento == "SALIDA"
    assert float(ultimo_mov.cantidad) == 20
    print(f"KARDEX OK: 1 movimiento SALIDA nuevo, cantidad {ultimo_mov.cantidad}, lote {ultimo_mov.lote_id} (FEFO automatico).")

    # --- Verificar Reporte de Ventas (m19_reportes), ya existente ---
    reporte = reportes_service.reporte_ventas(db, None, None)
    assert reporte.total_ordenes >= 1
    fila_producto = next((p for p in reporte.por_producto if p.producto_id == producto.id), None)
    assert fila_producto is not None, "El producto importado debe aparecer en el reporte de ventas."
    assert fila_producto.cantidad == 20
    print(
        f"REPORTE OK: por_producto incluye '{fila_producto.nombre}' con cantidad {fila_producto.cantidad}; "
        f"total_ordenes={reporte.total_ordenes}, total_vendido={reporte.total_vendido}."
    )

    print("\nE2E CIERRE FASE 10 (VENTAS ALMACEN): TODO OK.")

finally:
    db.close()
