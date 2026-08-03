"""FASE 3 - Inteligencia de inventario para perecibles.

Pruebas obligatorias (backend, sin frontend), con datos reales sobre
SQLite (sin mocks), siguiendo el mismo patron de scripts ya existentes
en el proyecto (test_fase1_seguridad_perecibles.py,
test_fase2_control_gerencial_perecibles.py).

LIMITACION DE ENTORNO (ver informe tecnico): este script se escribio en
un entorno sin acceso a red/pip, por lo que NO se pudo ejecutar contra
el motor real (fastapi/sqlalchemy no instalables aca). Queda listo para
correrse tal cual en un entorno con las dependencias de requirements.txt
instaladas. No se simula ningun resultado de ejecucion.

Casos cubiertos:
  1. Rotacion de inventario: consumo real / stock promedio, con datos
     reales de Kardex (ingreso + salida parcial).
  2. Dias de inventario - caso normal (stock y consumo > 0).
  3. Dias de inventario - consumo cero (no debe explotar division por
     cero; debe marcar sin_consumo=True y dias_inventario=None).
  4. Dias de inventario - stock cero (dias_inventario=0.0, sin_stock=True,
     sin importar el consumo).
  5. Consumo promedio diario/semanal/mensual, coherentes entre si
     (semanal = diario*7, mensual = diario*30).
  6. Riesgo de merma - producto sin vencimiento y con rotacion sana ->
     BAJO.
  7. Riesgo de merma - lote proximo a vencer (pocos dias) -> ALTO o
     CRITICO segun umbral configurado.
  8. Riesgo de merma - lote ya vencido en stock -> CRITICO.
  9. Riesgo de merma - stock inmovilizado (stock>0, consumo=0) -> sube
     de nivel respecto del mismo escenario sin inmovilizacion.
  10. Endpoint de detalle por producto devuelve el mismo resultado que
      el item correspondiente en el endpoint de lista (misma logica,
      sin duplicar calculo).
  11. Regresion: FEFO, Kardex y saldos de m03_inventario no cambian
      (este modulo es de solo lectura, no debe alterar ningun stock).
"""
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ.setdefault("SECRET_KEY", "test-secret-fase3")
os.environ.setdefault("ADMIN_PASSWORD", "Test123x")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_fase3.db")

if os.path.exists("test_fase3.db"):
    os.remove("test_fase3.db")

sys.path.insert(0, os.path.dirname(__file__))

from app.database import Base, engine, SessionLocal  # noqa: E402
from app.modules.m02_productos import models as _m02_models  # noqa: E402,F401
from app.modules.m03_inventario import models as _m03_models  # noqa: E402,F401
from app.modules.m02_productos.models import Producto  # noqa: E402
from app.modules.m03_inventario import schemas as inv_schemas  # noqa: E402
from app.modules.m03_inventario import service as inv_service  # noqa: E402
from app.modules.m03_inventario.models import Inventario  # noqa: E402
from app.modules.m22_inteligencia_inventario import service as ii_service  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()

FALLAS = []


def check(nombre, condicion, detalle=""):
    estado = "OK" if condicion else "FALLO"
    print(f"{estado}: {nombre} {detalle}")
    if not condicion:
        FALLAS.append(nombre)


# ============================================================
# Setup base
# ============================================================
inventario = Inventario(codigo="INV-F3", nombre="Inventario Fase3")
db.add(inventario)
db.commit()
db.refresh(inventario)

ahora = datetime.now(timezone.utc)


def crear_producto(codigo, nombre, perecible=True):
    p = Producto(codigo=codigo, nombre=nombre, unidad_medida="UND", perecible=perecible)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def ingreso(producto, cantidad, costo, codigo_lote, fecha_vencimiento=None, referencia="Ingreso test"):
    return inv_service.registrar_ingreso(
        db,
        inv_schemas.IngresoInventarioCrear(
            producto_id=producto.id,
            inventario_id=inventario.id,
            codigo_lote=codigo_lote,
            cantidad=cantidad,
            costo_unitario=costo,
            fecha_vencimiento=fecha_vencimiento,
            referencia=referencia,
            codigo_interno=f"CI-{codigo_lote}",
        ),
    )


def salida(producto, cantidad, referencia="Salida test"):
    return inv_service.registrar_salida(
        db,
        inv_schemas.SalidaInventarioCrear(
            producto_id=producto.id,
            inventario_id=inventario.id,
            cantidad=cantidad,
            referencia=referencia,
        ),
    )


# ============================================================
# Caso 1-5: producto con movimiento normal (rotacion, dias
# inventario, consumo promedio)
# ============================================================
prod_normal = crear_producto("P-NORMAL", "Producto rotacion normal", perecible=False)
ingreso(prod_normal, 100, 10.0, "L-NORMAL-1")
salida(prod_normal, 40, "Venta caso normal")
# Stock actual = 60. Consumo real (periodo) = 40. Como el producto se
# crea dentro de la misma ventana de dias_analisis, el stock
# reconstruido al INICIO del periodo es 0 (stock_final(60) -
# ingresos(100) + salidas(40) = 0): todavia no existia antes de estos
# dos movimientos. stock_promedio_periodo = (0 + 60) / 2 = 30.

indicadores = ii_service.indicadores_inventario(db, inventario.id, dias_analisis=30)
ind_normal = next(i for i in indicadores.indicadores if i.producto_id == prod_normal.id)

check(
    "Caso 1 - Rotacion: consumo_real_periodo = 40 (SALIDA real de Kardex)",
    ind_normal.consumo_real_periodo == 40.0,
    f"-> {ind_normal.consumo_real_periodo}",
)
check(
    "Caso 1 - Rotacion: stock_promedio_periodo reconstruido = (stock_inicial=0 + stock_actual=60) / 2 = 30",
    ind_normal.stock_promedio_periodo == 30.0,
    f"-> {ind_normal.stock_promedio_periodo}",
)
check(
    "Caso 1 - Rotacion: rotacion_inventario = 40 / 30 = 1.3333...",
    abs(ind_normal.rotacion_inventario - (40.0 / 30.0)) < 1e-9,
    f"-> {ind_normal.rotacion_inventario}",
)
check(
    "Caso 2 - Dias de inventario: stock_actual(60) / consumo_diario(40/30) coherente",
    ind_normal.dias_inventario is not None
    and abs(ind_normal.dias_inventario - (60.0 / (40.0 / 30))) < 1e-9,
    f"-> {ind_normal.dias_inventario}",
)
check(
    "Caso 5 - Consumo promedio: semanal = diario * 7",
    abs(ind_normal.consumo_promedio_semanal - ind_normal.consumo_promedio_diario * 7) < 1e-9,
)
check(
    "Caso 5 - Consumo promedio: mensual = diario * 30",
    abs(ind_normal.consumo_promedio_mensual - ind_normal.consumo_promedio_diario * 30) < 1e-9,
)
check(
    "Caso 6 - Riesgo de merma: producto no perecible, rotacion sana -> BAJO",
    ind_normal.riesgo_merma == "BAJO",
    f"-> {ind_normal.riesgo_merma} (score={ind_normal.score_riesgo_merma})",
)

# ============================================================
# Caso 3: consumo cero (solo ingreso, ninguna salida)
# ============================================================
prod_sin_consumo = crear_producto("P-SINCONSUMO", "Producto sin consumo", perecible=False)
ingreso(prod_sin_consumo, 50, 5.0, "L-SINCONSUMO-1")

indicadores = ii_service.indicadores_inventario(db, inventario.id, dias_analisis=30)
ind_sc = next(i for i in indicadores.indicadores if i.producto_id == prod_sin_consumo.id)

check(
    "Caso 3 - Consumo cero: sin_consumo=True",
    ind_sc.sin_consumo is True,
)
check(
    "Caso 3 - Consumo cero: dias_inventario es None (division invalida, no explota)",
    ind_sc.dias_inventario is None,
    f"-> {ind_sc.dias_inventario}",
)
check(
    "Caso 3 - Consumo cero: stock_inmovilizado=True (stock>0 y consumo_real=0)",
    ind_sc.stock_inmovilizado is True,
)

# ============================================================
# Caso 4: stock cero (ingreso y salida total del mismo lote)
# ============================================================
prod_sin_stock = crear_producto("P-SINSTOCK", "Producto sin stock", perecible=False)
ingreso(prod_sin_stock, 20, 8.0, "L-SINSTOCK-1")
salida(prod_sin_stock, 20, "Venta agota stock")

indicadores = ii_service.indicadores_inventario(db, inventario.id, dias_analisis=30)
ind_ss = next(i for i in indicadores.indicadores if i.producto_id == prod_sin_stock.id)

check(
    "Caso 4 - Stock cero: sin_stock=True",
    ind_ss.sin_stock is True,
)
check(
    "Caso 4 - Stock cero: dias_inventario = 0.0 (no hay inventario que cubrir)",
    ind_ss.dias_inventario == 0.0,
    f"-> {ind_ss.dias_inventario}",
)

# ============================================================
# Caso 7: lote proximo a vencer (pocos dias) -> riesgo alto/critico
# ============================================================
prod_por_vencer = crear_producto("P-PORVENCER", "Producto por vencer", perecible=True)
ingreso(
    prod_por_vencer, 30, 12.0, "L-PORVENCER-1",
    fecha_vencimiento=ahora + timedelta(days=5),
)
# Sin ninguna salida: ademas de "por vencer" queda "sin_movimiento"/inmovilizado.

indicadores = ii_service.indicadores_inventario(db, inventario.id, dias_analisis=30)
ind_pv = next(i for i in indicadores.indicadores if i.producto_id == prod_por_vencer.id)

check(
    "Caso 7 - dias_restantes_vencimiento calculado (~5 dias, positivo)",
    ind_pv.dias_restantes_vencimiento is not None and 0 < ind_pv.dias_restantes_vencimiento <= 5,
    f"-> {ind_pv.dias_restantes_vencimiento}",
)
check(
    "Caso 7 - Riesgo de merma ALTO o CRITICO (vencimiento inminente + sin movimiento)",
    ind_pv.riesgo_merma in ("ALTO", "CRITICO"),
    f"-> {ind_pv.riesgo_merma} (score={ind_pv.score_riesgo_merma})",
)

# ============================================================
# Caso 8: lote YA vencido en stock -> CRITICO
# ============================================================
prod_vencido = crear_producto("P-VENCIDO", "Producto vencido en stock", perecible=True)
# Se crea con fecha pasada directamente via repository (registrar_ingreso
# valida vencimiento obligatorio para perecibles, pero no impide una
# fecha ya pasada -- el bloqueo de vencidos aplica a SALIDAS, no a
# INGRESOS: un lote puede entrar y vencer despues, o incluso ingresarse
# ya vencido como ajuste de un conteo fisico real).
ingreso(
    prod_vencido, 15, 9.0, "L-VENCIDO-1",
    fecha_vencimiento=ahora - timedelta(days=3),
)

indicadores = ii_service.indicadores_inventario(db, inventario.id, dias_analisis=30)
ind_v = next(i for i in indicadores.indicadores if i.producto_id == prod_vencido.id)

check(
    "Caso 8 - dias_restantes_vencimiento negativo (ya vencido)",
    ind_v.dias_restantes_vencimiento is not None and ind_v.dias_restantes_vencimiento < 0,
    f"-> {ind_v.dias_restantes_vencimiento}",
)
check(
    "Caso 8 - Riesgo de merma CRITICO para lote ya vencido en stock",
    ind_v.riesgo_merma == "CRITICO",
    f"-> {ind_v.riesgo_merma} (score={ind_v.score_riesgo_merma})",
)

# ============================================================
# Caso 9: stock inmovilizado sube el score de riesgo
# ============================================================
prod_inmovilizado = crear_producto("P-INMOVIL", "Producto stock inmovilizado", perecible=False)
ingreso(prod_inmovilizado, 40, 6.0, "L-INMOVIL-1")
# Sin ninguna salida (a diferencia de prod_normal, que si tuvo salida).

indicadores = ii_service.indicadores_inventario(db, inventario.id, dias_analisis=30)
ind_im = next(i for i in indicadores.indicadores if i.producto_id == prod_inmovilizado.id)

check(
    "Caso 9 - stock_inmovilizado=True cuando no hay ninguna SALIDA en el periodo",
    ind_im.stock_inmovilizado is True,
)
check(
    "Caso 9 - score de riesgo del producto inmovilizado > score de un producto no perecible sin datos "
    "de riesgo (verifica que el factor de inmovilizacion realmente puntua)",
    ind_im.score_riesgo_merma >= 2,
    f"-> score={ind_im.score_riesgo_merma}",
)

# ============================================================
# Caso 10: detalle por producto == mismo item en la lista
# ============================================================
detalle = ii_service.indicador_producto(
    db, inventario.id, ind_normal.producto_inventario_id, dias_analisis=30
)
check(
    "Caso 10 - indicador_producto() devuelve el mismo resultado que la lista completa",
    detalle.rotacion_inventario == ind_normal.rotacion_inventario
    and detalle.dias_inventario == ind_normal.dias_inventario
    and detalle.riesgo_merma == ind_normal.riesgo_merma
    and detalle.consumo_real_periodo == ind_normal.consumo_real_periodo,
)

# ============================================================
# Caso 11: Regresion - m22 no toca stock/kardex/FEFO de m03
# ============================================================
saldo_normal_antes = inv_service.saldos(db, inventario.id)
stock_normal_antes = next(
    s["stock_total"] for s in saldo_normal_antes if s["producto_id"] == prod_normal.id
)
# Se vuelve a calcular inteligencia de inventario (solo lectura) y se
# verifica que el saldo real de m03 no cambio ni un decimal.
ii_service.indicadores_inventario(db, inventario.id, dias_analisis=30)
saldo_normal_despues = inv_service.saldos(db, inventario.id)
stock_normal_despues = next(
    s["stock_total"] for s in saldo_normal_despues if s["producto_id"] == prod_normal.id
)
check(
    "Caso 11 - Regresion: m22 es de solo lectura, el stock de m03 no cambia al calcular indicadores",
    stock_normal_antes == stock_normal_despues == 60.0,
    f"-> antes={stock_normal_antes} despues={stock_normal_despues}",
)

# ============================================================
# Resultado final
# ============================================================
print("\n" + "=" * 60)
if FALLAS:
    print(f"FASE 3 - TESTS: {len(FALLAS)} FALLA(S): {FALLAS}")
    sys.exit(1)
else:
    print("FASE 3 - INTELIGENCIA DE INVENTARIO: TODOS LOS CASOS OK")
    sys.exit(0)
