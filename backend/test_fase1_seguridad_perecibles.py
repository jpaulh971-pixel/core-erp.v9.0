"""FASE 1 - Seguridad operativa para productos perecibles.

Pruebas obligatorias (backend, sin frontend), con datos reales sobre
SQLite (sin mocks), replicando el patron de los scripts de prueba ya
existentes en el proyecto (test_fase10_cierre_e2e.py, etc.).

Caso 1: producto perecible sin fecha de vencimiento -> debe rechazar
        la creacion del lote.
Caso 2: lote vencido con stock disponible -> intentar vender -> debe
        bloquearse.
Caso 3: dos lotes vigentes (A vence 30/12/2026, B vence 30/06/2026) ->
        debe consumir B primero (FEFO).
Caso 4: lote B vencido -> debe ignorarse y consumir A.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ.setdefault("SECRET_KEY", "test-secret-fase1")
os.environ.setdefault("ADMIN_PASSWORD", "Test123x")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_fase1.db")

if os.path.exists("test_fase1.db"):
    os.remove("test_fase1.db")

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import HTTPException  # noqa: E402

from app.database import Base, engine, SessionLocal  # noqa: E402
from app.modules.m02_productos import models as _m02_models  # noqa: E402,F401
from app.modules.m03_inventario import models as _m03_models  # noqa: E402,F401
from app.modules.m02_productos.models import Producto  # noqa: E402
from app.modules.m03_inventario import schemas as inv_schemas  # noqa: E402
from app.modules.m03_inventario import service as inv_service  # noqa: E402
from app.modules.m03_inventario.models import Inventario  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()

FALLAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK" if condicion else "FALLO"
    print(f"{estado}: {nombre} {detalle}")
    if not condicion:
        FALLAS.append(nombre)


# --- Setup base ---
inventario = Inventario(codigo="INV-F1", nombre="Inventario Fase1")
db.add(inventario)
db.commit()
db.refresh(inventario)

producto_perecible = Producto(
    codigo="PER-0001", nombre="Producto Perecible", unidad_medida="KG", perecible=True
)
producto_no_perecible = Producto(
    codigo="NOPER-0001", nombre="Producto No Perecible", unidad_medida="UND", perecible=False
)
db.add_all([producto_perecible, producto_no_perecible])
db.commit()
db.refresh(producto_perecible)
db.refresh(producto_no_perecible)

ahora = datetime.now(timezone.utc)


# ============================================================
# CASO 1: producto perecible SIN fecha de vencimiento -> rechazar
# ============================================================
print("\n=== CASO 1: perecible sin fecha_vencimiento ===")
try:
    inv_service.registrar_ingreso(
        db,
        inv_schemas.IngresoInventarioCrear(
            producto_id=producto_perecible.id,
            inventario_id=inventario.id,
            codigo_lote="CASO1-SIN-VENC",
            cantidad=10,
            costo_unitario=10,
            fecha_vencimiento=None,
        ),
    )
    check("Caso 1 - debe rechazar creacion", False, "(no lanzo excepcion)")
except HTTPException as e:
    check(
        "Caso 1 - debe rechazar creacion",
        e.status_code == 400 and "perecible" in e.detail.lower(),
        f"-> {e.status_code}: {e.detail}",
    )
db.rollback()

# Control: producto NO perecible sin vencimiento debe seguir funcionando igual que antes
mov_no_perecible = inv_service.registrar_ingreso(
    db,
    inv_schemas.IngresoInventarioCrear(
        producto_id=producto_no_perecible.id,
        inventario_id=inventario.id,
        codigo_lote="CONTROL-NOPER",
        cantidad=5,
        costo_unitario=1,
        fecha_vencimiento=None,
    ),
)
check(
    "Control - no perecible sin vencimiento sigue funcionando",
    mov_no_perecible.id is not None,
)

# Control: perecible CON fecha_vencimiento debe permitirse
mov_perecible_ok = inv_service.registrar_ingreso(
    db,
    inv_schemas.IngresoInventarioCrear(
        producto_id=producto_perecible.id,
        inventario_id=inventario.id,
        codigo_lote="CONTROL-PER-OK",
        cantidad=1,
        costo_unitario=1,
        fecha_vencimiento=ahora + timedelta(days=365),
    ),
)
check("Control - perecible CON vencimiento se crea normalmente", mov_perecible_ok.id is not None)


# ============================================================
# CASO 2: lote vencido con stock -> intentar vender -> bloqueado
# ============================================================
print("\n=== CASO 2: lote vencido, intentar vender ===")
mov_vencido = inv_service.registrar_ingreso(
    db,
    inv_schemas.IngresoInventarioCrear(
        producto_id=producto_perecible.id,
        inventario_id=inventario.id,
        codigo_lote="CASO2-VENCIDO",
        cantidad=20,
        costo_unitario=10,
        fecha_vencimiento=ahora - timedelta(days=5),  # ya vencido
    ),
)
lote_vencido_id = mov_vencido.lote_id

try:
    inv_service.registrar_salida(
        db,
        inv_schemas.SalidaInventarioCrear(
            producto_id=producto_perecible.id,
            inventario_id=inventario.id,
            lote_id=lote_vencido_id,  # seleccion EXPLICITA del lote vencido
            cantidad=5,
            referencia="Venta de prueba - lote vencido",
        ),
    )
    check("Caso 2 - debe bloquear venta de lote vencido", False, "(no lanzo excepcion)")
except HTTPException as e:
    check(
        "Caso 2 - debe bloquear venta de lote vencido",
        e.status_code == 400 and "vencido" in e.detail.lower(),
        f"-> {e.status_code}: {e.detail}",
    )
db.rollback()

# Tambien debe quedar excluido del FEFO automatico (sin indicar lote_id)
producto_solo_vencido = Producto(
    codigo="PER-SOLO-VENC", nombre="Producto Solo Vencido", unidad_medida="KG", perecible=True
)
db.add(producto_solo_vencido)
db.commit()
db.refresh(producto_solo_vencido)

inv_service.registrar_ingreso(
    db,
    inv_schemas.IngresoInventarioCrear(
        producto_id=producto_solo_vencido.id,
        inventario_id=inventario.id,
        codigo_lote="UNICO-VENCIDO",
        cantidad=10,
        costo_unitario=10,
        fecha_vencimiento=ahora - timedelta(days=1),
    ),
)
try:
    inv_service.registrar_salida(
        db,
        inv_schemas.SalidaInventarioCrear(
            producto_id=producto_solo_vencido.id,
            inventario_id=inventario.id,
            cantidad=1,
            referencia="Venta FEFO automatico - unico lote vencido",
        ),
    )
    check("Caso 2b - FEFO automatico no debe completar la salida con stock solo vencido", False, "(no lanzo excepcion)")
except HTTPException as e:
    check(
        "Caso 2b - FEFO automatico no debe completar la salida con stock solo vencido",
        e.status_code == 400,
        f"-> {e.status_code}: {e.detail}",
    )
db.rollback()


# ============================================================
# CASO 3: dos lotes vigentes -> debe consumir B (vence antes) primero
# ============================================================
print("\n=== CASO 3: FEFO entre dos lotes vigentes ===")
producto_fefo = Producto(codigo="PER-FEFO", nombre="Producto FEFO", unidad_medida="KG", perecible=True)
db.add(producto_fefo)
db.commit()
db.refresh(producto_fefo)

mov_a = inv_service.registrar_ingreso(
    db,
    inv_schemas.IngresoInventarioCrear(
        producto_id=producto_fefo.id,
        inventario_id=inventario.id,
        codigo_lote="LOTE-A",
        cantidad=100,
        costo_unitario=10,
        # Equivalente relativo al escenario de la Auditoria 2 (Lote A
        # vence bastante despues que B), pero con fechas siempre en el
        # futuro respecto del momento de ejecucion del test.
        fecha_vencimiento=ahora + timedelta(days=300),
    ),
)
mov_b = inv_service.registrar_ingreso(
    db,
    inv_schemas.IngresoInventarioCrear(
        producto_id=producto_fefo.id,
        inventario_id=inventario.id,
        codigo_lote="LOTE-B",
        cantidad=50,
        costo_unitario=15,
        fecha_vencimiento=ahora + timedelta(days=150),  # vence antes que A, pero sigue vigente
    ),
)
lote_a_id, lote_b_id = mov_a.lote_id, mov_b.lote_id

salida_caso3 = inv_service.registrar_salida(
    db,
    inv_schemas.SalidaInventarioCrear(
        producto_id=producto_fefo.id,
        inventario_id=inventario.id,
        cantidad=10,
        referencia="Venta FEFO caso 3",
    ),
)
check(
    "Caso 3 - consume Lote B (vence antes) primero",
    len(salida_caso3) == 1 and salida_caso3[0].lote_id == lote_b_id,
    f"-> lote consumido={salida_caso3[0].lote_id} (esperado {lote_b_id}, Lote A={lote_a_id})",
)
check(
    "Caso 3 - costo unitario del movimiento es el del Lote B (15), no un promedio",
    float(salida_caso3[0].costo_unitario) == 15.0,
    f"-> costo_unitario={salida_caso3[0].costo_unitario}",
)


# ============================================================
# CASO 4: Lote B vencido -> debe ignorarse y consumir A
# ============================================================
print("\n=== CASO 4: Lote B vencido, debe consumir A ===")
producto_fefo2 = Producto(codigo="PER-FEFO2", nombre="Producto FEFO 2", unidad_medida="KG", perecible=True)
db.add(producto_fefo2)
db.commit()
db.refresh(producto_fefo2)

mov_a2 = inv_service.registrar_ingreso(
    db,
    inv_schemas.IngresoInventarioCrear(
        producto_id=producto_fefo2.id,
        inventario_id=inventario.id,
        codigo_lote="LOTE-A2",
        cantidad=100,
        costo_unitario=10,
        fecha_vencimiento=ahora + timedelta(days=180),  # vigente
    ),
)
mov_b2 = inv_service.registrar_ingreso(
    db,
    inv_schemas.IngresoInventarioCrear(
        producto_id=producto_fefo2.id,
        inventario_id=inventario.id,
        codigo_lote="LOTE-B2",
        cantidad=50,
        costo_unitario=15,
        fecha_vencimiento=ahora - timedelta(days=3),  # ya vencido
    ),
)
lote_a2_id, lote_b2_id = mov_a2.lote_id, mov_b2.lote_id

salida_caso4 = inv_service.registrar_salida(
    db,
    inv_schemas.SalidaInventarioCrear(
        producto_id=producto_fefo2.id,
        inventario_id=inventario.id,
        cantidad=10,
        referencia="Venta FEFO caso 4",
    ),
)
check(
    "Caso 4 - ignora Lote B (vencido) y consume Lote A",
    len(salida_caso4) == 1 and salida_caso4[0].lote_id == lote_a2_id,
    f"-> lote consumido={salida_caso4[0].lote_id} (esperado {lote_a2_id}, Lote B(vencido)={lote_b2_id})",
)

lote_b2_actual = inv_service.repository.obtener_lote(db, lote_b2_id) if hasattr(inv_service, "repository") else None
from app.modules.m03_inventario import repository as inv_repo  # noqa: E402
lote_b2_actual = inv_repo.obtener_lote(db, lote_b2_id)
check(
    "Caso 4 - stock del Lote B (vencido) queda intacto, no se toco",
    float(lote_b2_actual.cantidad_actual) == 50.0,
    f"-> cantidad_actual={lote_b2_actual.cantidad_actual}",
)


# ============================================================
# Resultado final
# ============================================================
print("\n" + "=" * 60)
if FALLAS:
    print(f"FASE 1 - TESTS: {len(FALLAS)} FALLA(S): {FALLAS}")
    sys.exit(1)
else:
    print("FASE 1 - SEGURIDAD OPERATIVA PERECIBLES: TODOS LOS CASOS OK")
    sys.exit(0)
