"""FASE 2 - Control gerencial para inventario perecible.

Pruebas obligatorias (backend, sin frontend), con datos reales sobre
SQLite (sin mocks), siguiendo el mismo patron de scripts ya existentes
en el proyecto (test_fase1_seguridad_perecibles.py, etc.).

Caso 1: lote con mas de 90 dias para vencer -> semaforo VERDE.
Caso 2: lote con 60 dias -> semaforo AMARILLO.
Caso 3: lote con 15 dias -> semaforo ROJO.
Caso 4: lote vencido -> semaforo NEGRO.
Caso 5: reporte inventario por lote -> valida costo, cantidad, valor, estado.
Caso 6: reporte proximos a vencer -> valida orden correcto.

Ademas valida (regresion, sin recalcular nada nuevo):
- El semaforo de stock (VERDE/AMARILLO/ROJO) para los 3 escenarios de la
  Fase 2 (normal, cercano al minimo, igual/menor al minimo).
- FEFO, Kardex y costo unitario NO cambian (se reutiliza el mismo flujo
  de ingreso/salida de Fase 1 y se verifica que el resultado es igual).
"""
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ.setdefault("SECRET_KEY", "test-secret-fase2")
os.environ.setdefault("ADMIN_PASSWORD", "Test123x")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_fase2.db")

if os.path.exists("test_fase2.db"):
    os.remove("test_fase2.db")

sys.path.insert(0, os.path.dirname(__file__))

from app.database import Base, engine, SessionLocal  # noqa: E402
from app.modules.m02_productos import models as _m02_models  # noqa: E402,F401
from app.modules.m03_inventario import models as _m03_models  # noqa: E402,F401
from app.modules.m02_productos.models import Producto  # noqa: E402
from app.modules.m03_inventario import schemas as inv_schemas  # noqa: E402
from app.modules.m03_inventario import service as inv_service  # noqa: E402
from app.modules.m03_inventario.models import Inventario  # noqa: E402
from app.modules.m19_reportes import service as rep_service  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()

FALLAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK" if condicion else "FALLO"
    print(f"{estado}: {nombre} {detalle}")
    if not condicion:
        FALLAS.append(nombre)


# --- Setup base ---
inventario = Inventario(codigo="INV-F2", nombre="Inventario Fase2")
db.add(inventario)
db.commit()
db.refresh(inventario)

producto = Producto(
    codigo="PER-F2-0001", nombre="Producto Perecible F2", unidad_medida="KG",
    perecible=True, stock_minimo=100,
)
db.add(producto)
db.commit()
db.refresh(producto)

ahora = datetime.now(timezone.utc)


# ============================================================
# CASO 1: lote con mas de 90 dias -> VERDE
# ============================================================
print("\n=== CASO 1: > 90 dias -> VERDE ===")
mov1 = inv_service.registrar_ingreso(
    db,
    inv_schemas.IngresoInventarioCrear(
        producto_id=producto.id,
        inventario_id=inventario.id,
        codigo_lote="LOTE-F2-VERDE",
        cantidad=50,
        costo_unitario=10,
        fecha_vencimiento=ahora + timedelta(days=120),
        referencia="Ingreso caso 1",
    ),
)
lote1 = inv_service.repository.obtener_lote(db, mov1.lote_id)
semaforo1, dias1 = inv_service.calcular_semaforo_vencimiento(lote1.fecha_vencimiento, ahora)
check("Caso 1 - semaforo VERDE (120 dias)", semaforo1 == "VERDE", f"-> {semaforo1} ({dias1} dias)")

# ============================================================
# CASO 2: lote con 60 dias -> AMARILLO
# ============================================================
print("\n=== CASO 2: 60 dias -> AMARILLO ===")
mov2 = inv_service.registrar_ingreso(
    db,
    inv_schemas.IngresoInventarioCrear(
        producto_id=producto.id,
        inventario_id=inventario.id,
        codigo_lote="LOTE-F2-AMARILLO",
        cantidad=30,
        costo_unitario=12,
        fecha_vencimiento=ahora + timedelta(days=60),
        referencia="Ingreso caso 2",
    ),
)
lote2 = inv_service.repository.obtener_lote(db, mov2.lote_id)
semaforo2, dias2 = inv_service.calcular_semaforo_vencimiento(lote2.fecha_vencimiento, ahora)
check("Caso 2 - semaforo AMARILLO (60 dias)", semaforo2 == "AMARILLO", f"-> {semaforo2} ({dias2} dias)")

# ============================================================
# CASO 3: lote con 15 dias -> ROJO
# ============================================================
print("\n=== CASO 3: 15 dias -> ROJO ===")
mov3 = inv_service.registrar_ingreso(
    db,
    inv_schemas.IngresoInventarioCrear(
        producto_id=producto.id,
        inventario_id=inventario.id,
        codigo_lote="LOTE-F2-ROJO",
        cantidad=20,
        costo_unitario=15,
        fecha_vencimiento=ahora + timedelta(days=15),
        referencia="Ingreso caso 3",
    ),
)
lote3 = inv_service.repository.obtener_lote(db, mov3.lote_id)
semaforo3, dias3 = inv_service.calcular_semaforo_vencimiento(lote3.fecha_vencimiento, ahora)
check("Caso 3 - semaforo ROJO (15 dias)", semaforo3 == "ROJO", f"-> {semaforo3} ({dias3} dias)")

# ============================================================
# CASO 4: lote vencido -> NEGRO
# ============================================================
print("\n=== CASO 4: vencido -> NEGRO ===")
# Un lote ya vencido no se puede crear via registrar_ingreso + FEFO normal
# de forma directa porque nace ya fuera de FEFO; se crea igual (ingreso
# permite fecha pasada, igual que en datos historicos) para poder leerlo
# en los reportes de solo lectura, sin afectar salidas.
mov4 = inv_service.registrar_ingreso(
    db,
    inv_schemas.IngresoInventarioCrear(
        producto_id=producto.id,
        inventario_id=inventario.id,
        codigo_lote="LOTE-F2-NEGRO",
        cantidad=10,
        costo_unitario=8,
        fecha_vencimiento=ahora - timedelta(days=5),
        referencia="Ingreso caso 4",
    ),
)
lote4 = inv_service.repository.obtener_lote(db, mov4.lote_id)
semaforo4, dias4 = inv_service.calcular_semaforo_vencimiento(lote4.fecha_vencimiento, ahora)
check("Caso 4 - semaforo NEGRO (vencido)", semaforo4 == "NEGRO", f"-> {semaforo4} ({dias4} dias)")
check("Caso 4 - dias_restantes negativo", dias4 is not None and dias4 < 0, f"-> {dias4}")

# ============================================================
# CASO 5: reporte inventario por lote -> costo, cantidad, valor, estado
# ============================================================
print("\n=== CASO 5: reporte inventario por lote ===")
reporte_lotes = rep_service.reporte_inventario_por_lote(db, inventario.id)
por_codigo = {f.codigo_lote: f for f in reporte_lotes.lotes}

check(
    "Caso 5 - reporte incluye los 4 lotes creados",
    all(c in por_codigo for c in ["LOTE-F2-VERDE", "LOTE-F2-AMARILLO", "LOTE-F2-ROJO", "LOTE-F2-NEGRO"]),
    f"-> codigos={list(por_codigo.keys())}",
)

f_verde = por_codigo.get("LOTE-F2-VERDE")
check(
    "Caso 5 - LOTE-F2-VERDE: cantidad_disponible correcta",
    f_verde is not None and f_verde.cantidad_disponible == 50.0,
    f"-> {f_verde.cantidad_disponible if f_verde else None}",
)
check(
    "Caso 5 - LOTE-F2-VERDE: costo_unitario correcto",
    f_verde is not None and f_verde.costo_unitario == 10.0,
    f"-> {f_verde.costo_unitario if f_verde else None}",
)
check(
    "Caso 5 - LOTE-F2-VERDE: valor_total_lote = cantidad * costo",
    f_verde is not None and f_verde.valor_total_lote == 500.0,
    f"-> {f_verde.valor_total_lote if f_verde else None}",
)
check(
    "Caso 5 - LOTE-F2-VERDE: estado_lote ACTIVO (calcular_estado_lote)",
    f_verde is not None and f_verde.estado_lote == "ACTIVO",
    f"-> {f_verde.estado_lote if f_verde else None}",
)
check(
    "Caso 5 - LOTE-F2-VERDE: semaforo_vencimiento VERDE",
    f_verde is not None and f_verde.semaforo_vencimiento == "VERDE",
    f"-> {f_verde.semaforo_vencimiento if f_verde else None}",
)

f_negro = por_codigo.get("LOTE-F2-NEGRO")
check(
    "Caso 5 - LOTE-F2-NEGRO: estado_lote VENCIDO",
    f_negro is not None and f_negro.estado_lote == "VENCIDO",
    f"-> {f_negro.estado_lote if f_negro else None}",
)
check(
    "Caso 5 - LOTE-F2-NEGRO: semaforo_vencimiento NEGRO",
    f_negro is not None and f_negro.semaforo_vencimiento == "NEGRO",
    f"-> {f_negro.semaforo_vencimiento if f_negro else None}",
)
check(
    "Caso 5 - valor_total del reporte = suma de valor_total_lote",
    round(reporte_lotes.valor_total, 2) == round(sum(f.valor_total_lote for f in reporte_lotes.lotes), 2),
    f"-> {reporte_lotes.valor_total}",
)

# ============================================================
# CASO 6: reporte proximos a vencer -> orden correcto
# ============================================================
print("\n=== CASO 6: reporte proximos a vencer -> orden ===")
reporte_pv = rep_service.reporte_proximos_vencer(db, inventario.id)
codigos_orden = [f.codigo_lote for f in reporte_pv.lotes]
# Orden esperado por fecha_vencimiento ascendente: NEGRO (vencido, ya
# paso) -> ROJO (15d) -> AMARILLO (60d) -> VERDE (120d)
esperado = ["LOTE-F2-NEGRO", "LOTE-F2-ROJO", "LOTE-F2-AMARILLO", "LOTE-F2-VERDE"]
check(
    "Caso 6 - orden por fecha_vencimiento ascendente",
    codigos_orden == esperado,
    f"-> obtenido={codigos_orden} esperado={esperado}",
)
categorias = {f.codigo_lote: f.categoria for f in reporte_pv.lotes}
check(
    "Caso 6 - categorias correctas",
    categorias.get("LOTE-F2-NEGRO") == "VENCIDOS"
    and categorias.get("LOTE-F2-ROJO") == "PROXIMOS_A_VENCER"
    and categorias.get("LOTE-F2-AMARILLO") == "PROXIMOS_A_VENCER"
    and categorias.get("LOTE-F2-VERDE") == "ACTIVOS",
    f"-> {categorias}",
)
check(
    "Caso 6 - contadores del reporte coinciden con las categorias",
    reporte_pv.vencidos == 1 and reporte_pv.proximos_a_vencer == 2 and reporte_pv.activos == 1,
    f"-> vencidos={reporte_pv.vencidos} proximos={reporte_pv.proximos_a_vencer} activos={reporte_pv.activos}",
)
check(
    "Caso 6 - valor_stock_comprometido de un lote = cantidad * costo",
    next(f for f in reporte_pv.lotes if f.codigo_lote == "LOTE-F2-ROJO").valor_stock_comprometido == 300.0,
    "",
)

# ============================================================
# EXTRA: semaforo de stock (seccion 2 de Fase 2)
# ============================================================
print("\n=== EXTRA: semaforo de stock ===")
check(
    "Stock normal (100 con minimo 50) -> VERDE",
    inv_service.calcular_semaforo_stock(100, 50) == "VERDE",
)
check(
    "Stock cercano al minimo (55 con minimo 50, factor 1.2) -> AMARILLO",
    inv_service.calcular_semaforo_stock(55, 50) == "AMARILLO",
)
check(
    "Stock igual al minimo (50 con minimo 50) -> ROJO",
    inv_service.calcular_semaforo_stock(50, 50) == "ROJO",
)
check(
    "Stock por debajo del minimo (30 con minimo 50) -> ROJO",
    inv_service.calcular_semaforo_stock(30, 50) == "ROJO",
)

saldos_f2 = inv_service.saldos(db, inventario.id)
fila_producto = next((f for f in saldos_f2 if f["producto_id"] == producto.id), None)
check(
    "saldos() expone semaforo_stock sin romper stock_total/bajo_stock_minimo",
    fila_producto is not None
    and fila_producto["stock_total"] == 110.0  # 50+30+20+10
    and "semaforo_stock" in fila_producto,
    f"-> {fila_producto}",
)

reporte_valorizado = rep_service.reporte_inventario_valorizado(db)
fila_valorizada = next((p for p in reporte_valorizado.productos if p.producto_id == producto.id), None)
check(
    "reporte_inventario_valorizado expone semaforo_stock sin romper bajo_stock_minimo",
    fila_valorizada is not None and hasattr(fila_valorizada, "semaforo_stock"),
    f"-> {fila_valorizada}",
)

# ============================================================
# REGRESION: FEFO / Kardex / costo unitario no cambian
# ============================================================
print("\n=== REGRESION: FEFO/Kardex/costo unitario intactos ===")
# FEFO debe seguir consumiendo primero el lote que vence antes entre los
# disponibles (LOTE-F2-ROJO, 15 dias) -- el vencido (NEGRO) queda fuera
# de FEFO igual que en Fase 1.
salida_fefo = inv_service.registrar_salida(
    db,
    inv_schemas.SalidaInventarioCrear(
        producto_id=producto.id,
        inventario_id=inventario.id,
        cantidad=5,
        referencia="Venta regresion FEFO",
    ),
)
check(
    "Regresion - FEFO consume el lote vigente que vence antes (ROJO), no el vencido",
    len(salida_fefo) == 1 and salida_fefo[0].lote_id == lote3.id,
    f"-> lote consumido={salida_fefo[0].lote_id} (esperado {lote3.id})",
)
check(
    "Regresion - costo_unitario del movimiento de salida = costo del lote consumido",
    float(salida_fefo[0].costo_unitario) == 15.0,
    f"-> {salida_fefo[0].costo_unitario}",
)
kardex_producto = inv_service.kardex_producto_inventario(db, lote3.producto_inventario_id)
check(
    "Regresion - el Kardex registro la salida (referencia intacta)",
    any(m.referencia == "Venta regresion FEFO" for m in kardex_producto),
)
lote_negro_actual = inv_service.repository.obtener_lote(db, lote4.id)
check(
    "Regresion - el lote vencido (NEGRO) no fue tocado por FEFO",
    float(lote_negro_actual.cantidad_actual) == 10.0,
    f"-> {lote_negro_actual.cantidad_actual}",
)


# ============================================================
# Resultado final
# ============================================================
print("\n" + "=" * 60)
if FALLAS:
    print(f"FASE 2 - TESTS: {len(FALLAS)} FALLA(S): {FALLAS}")
    sys.exit(1)
else:
    print("FASE 2 - CONTROL GERENCIAL PERECIBLES: TODOS LOS CASOS OK")
    sys.exit(0)
