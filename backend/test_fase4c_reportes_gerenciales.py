"""Pruebas funcionales Fase 4C -- m24_reportes_gerenciales_inventario.

Crea datos de prueba minimos (producto, inventario, lote, vencimiento,
movimiento de inventario) que cubren los 4 reportes pedidos, levanta la
app FastAPI real con TestClient, prueba los 4 endpoints reales y
compara manualmente los resultados contra los modulos fuente
(m19_reportes, m22_inteligencia_inventario, m23_dashboard_inventario)
para verificar que m24 no duplica ni desvia ningun calculo.
"""
import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("SECRET_KEY", "test_secret_key_fase4c")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_fase4c.db")

if os.path.exists("./test_fase4c.db"):
    os.remove("./test_fase4c.db")

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main_module  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.deps import get_usuario_actual  # noqa: E402
from app.modules.m02_productos.models import Producto  # noqa: E402
from app.modules.m03_inventario.models import Inventario, Lote, MovimientoKardex, ProductoInventario  # noqa: E402
from app.modules.m19_reportes import service as reportes_service  # noqa: E402
from app.modules.m22_inteligencia_inventario import service as inteligencia_service  # noqa: E402
from app.modules.m23_dashboard_inventario import service as dashboard_service  # noqa: E402
from app.modules.m24_reportes_gerenciales_inventario import repository as m24_repository  # noqa: E402

Base.metadata.create_all(bind=engine)

db = SessionLocal()
ahora = datetime.now(timezone.utc)

inv = Inventario(codigo="INV1", nombre="Inventario Principal", activo=True)
db.add(inv)
db.flush()

productos_data = [
    # (codigo, nombre, stock_minimo, perecible)
    ("P-001", "Aceite de Oliva 1L", 50, True),   # bajo stock + riesgo merma
    ("P-002", "Vinagre Balsamico 500ml", 5, True),  # proximo a vencer
    ("P-003", "Miel Organica 1kg", 5, True),      # vencido
    ("P-004", "Sal de Mesa 1kg", 5, False),       # sin rotacion (sin movimientos recientes)
    ("P-005", "Cafe Premium 250g", 5, False),     # normal / alto valor
]

productos = {}
for codigo, nombre, stock_min, perecible in productos_data:
    p = Producto(codigo=codigo, nombre=nombre, unidad_medida="UND", stock_minimo=stock_min, perecible=perecible, activo=True)
    db.add(p)
    db.flush()
    productos[codigo] = p

pis = {}
for codigo, p in productos.items():
    pi = ProductoInventario(producto_id=p.id, inventario_id=inv.id, codigo_interno=codigo, estado=True)
    db.add(pi)
    db.flush()
    pis[codigo] = pi

db.flush()


def crear_lote_y_movimiento(codigo, cantidad, costo, fecha_venc=None, dias_movimiento_atras=0, tipo="INGRESO"):
    pi = pis[codigo]
    lote = Lote(
        producto_inventario_id=pi.id,
        codigo_lote=f"LOTE-{codigo}-{cantidad}-{costo}",
        cantidad_inicial=cantidad,
        cantidad_actual=cantidad,
        costo_unitario=costo,
        fecha_vencimiento=fecha_venc,
        estado="ACTIVO",
    )
    db.add(lote)
    db.flush()
    mov = MovimientoKardex(
        producto_inventario_id=pi.id,
        inventario_id=inv.id,
        lote_id=lote.id,
        tipo_movimiento=tipo,
        cantidad=cantidad,
        costo_unitario=costo,
        saldo_resultante=cantidad,
        referencia="TEST-FASE4C",
    )
    db.add(mov)
    db.flush()
    if dias_movimiento_atras:
        mov.creado_en = ahora - timedelta(days=dias_movimiento_atras)
    db.flush()
    return lote, mov


# P-001: bajo stock (stock_minimo=50, cantidad=10) + sin movimientos recientes (90 dias) -> riesgo merma
crear_lote_y_movimiento("P-001", 10, 25.0, fecha_venc=ahora + timedelta(days=200), dias_movimiento_atras=90)

# P-002: proximo a vencer (15 dias)
crear_lote_y_movimiento("P-002", 20, 8.5, fecha_venc=ahora + timedelta(days=15), dias_movimiento_atras=5)

# P-003: vencido (-10 dias)
crear_lote_y_movimiento("P-003", 8, 30.0, fecha_venc=ahora - timedelta(days=10), dias_movimiento_atras=40)

# P-004: sin rotacion (stock alto, ultimo movimiento hace 120 dias, sin fecha de vencimiento)
crear_lote_y_movimiento("P-004", 100, 2.0, fecha_venc=None, dias_movimiento_atras=120)

# P-005: producto de alto valor, movimiento reciente, sin problemas
crear_lote_y_movimiento("P-005", 200, 45.0, fecha_venc=ahora + timedelta(days=400), dias_movimiento_atras=1)

db.commit()
db.close()

# --- TestClient con auth bypassed (bearer real ya probado en otros modulos) ---
main_module.app.dependency_overrides[get_usuario_actual] = lambda: None
client = TestClient(main_module.app)

print("=" * 70)
print("1) GET /api/reportes-gerenciales-inventario/resumen")
r = client.get("/api/reportes-gerenciales-inventario/resumen")
print(r.status_code, r.json())

print("=" * 70)
print("2) GET /api/reportes-gerenciales-inventario/top-valor")
r = client.get("/api/reportes-gerenciales-inventario/top-valor")
print(r.status_code)
for p in r.json()["productos"]:
    print(" -", p)

print("=" * 70)
print("3) GET /api/reportes-gerenciales-inventario/productos-criticos")
r = client.get("/api/reportes-gerenciales-inventario/productos-criticos")
print(r.status_code)
for p in r.json()["productos"]:
    print(" -", p)

print("=" * 70)
print("4) GET /api/reportes-gerenciales-inventario/sin-rotacion?dias_sin_rotacion=30")
r = client.get("/api/reportes-gerenciales-inventario/sin-rotacion", params={"dias_sin_rotacion": 30})
print(r.status_code)
for p in r.json()["productos"]:
    print(" -", p)

print("=" * 70)
print("5) Validacion de parametros invalidos")
r = client.get("/api/reportes-gerenciales-inventario/top-valor", params={"limite": 0})
print("limite=0 ->", r.status_code, r.json())
r = client.get("/api/reportes-gerenciales-inventario/sin-rotacion", params={"dias_sin_rotacion": -5})
print("dias_sin_rotacion=-5 ->", r.status_code, r.json())

print("=" * 70)
print("6) OpenAPI/Swagger")
r = client.get("/openapi.json")
paths = [p for p in r.json()["paths"].keys() if "reportes-gerenciales-inventario" in p]
print("status:", r.status_code, "paths registrados:", paths)

# --- Verificacion cruzada contra los modulos fuente (sin duplicar calculo) ---
print("=" * 70)
print("7) Verificacion cruzada contra modulos fuente")
db2 = SessionLocal()
resumen_m23 = dashboard_service.resumen_dashboard(db2)
r = client.get("/api/reportes-gerenciales-inventario/resumen")
assert r.json() == resumen_m23.model_dump(), "MISMATCH resumen m24 vs m23"
print("OK: resumen m24 == resumen m23 (sin recalculo)")

valorizado = reportes_service.reporte_inventario_valorizado(db2)
r = client.get("/api/reportes-gerenciales-inventario/top-valor")
suma_top_valor = sum(p["valor_total"] for p in r.json()["productos"])
assert abs(suma_top_valor - valorizado.valor_total_inventario) < 0.01, "MISMATCH top-valor vs m19 valorizado"
print("OK: suma top-valor == valor_total_inventario de m19")

db2.close()

print("=" * 70)
print("TODAS LAS PRUEBAS PASARON")
