"""Logica de negocio del modulo m13_inteligencia_comercial.

Inteligencia comercial de solo lectura sobre Ventas, Clientes y
Productos ya implementados: rankings y un indice de rotacion de
inventario. No recalcula reglas de negocio de esos modulos -- para el
stock actual reutiliza directo el servicio de Inventario (mismo criterio
de "no duplicar logica" que ya aplica m01_dashboard).
"""
from datetime import date

from sqlalchemy.orm import Session

from app.modules.m03_inventario import service as inventario_service
from app.modules.m13_inteligencia_comercial import repository, schemas, validators


def productos_mas_vendidos(
    db: Session, limit: int = 10, desde: date | None = None, hasta: date | None = None
) -> list[schemas.ProductoMasVendido]:
    validators.validar_rango_fechas(desde, hasta)
    filas = repository.productos_mas_vendidos(db, limit, desde, hasta)
    return [schemas.ProductoMasVendido(**f) for f in filas]


def clientes_top(
    db: Session, limit: int = 10, desde: date | None = None, hasta: date | None = None
) -> list[schemas.ClienteTop]:
    validators.validar_rango_fechas(desde, hasta)
    filas = repository.clientes_top(db, limit, desde, hasta)
    return [schemas.ClienteTop(**f) for f in filas]


def rotacion_inventario(db: Session) -> list[schemas.RotacionProducto]:
    """Indice de rotacion = unidades vendidas (historico, DESPACHADA) /
    stock actual. Marca 'sin_movimiento' los productos con stock pero sin
    ninguna venta despachada -- candidatos a stock inmovilizado."""
    # inventario_service.saldos() exige un inventario_id: se usa el primero
    # registrado (mismo criterio ya aplicado en m01_dashboard.service).
    inventarios = inventario_service.listar_inventarios(db)
    saldos = inventario_service.saldos(db, inventarios[0].id) if inventarios else []
    vendidos = repository.cantidad_vendida_por_producto(db)

    resultado = []
    for s in saldos:
        cantidad_vendida = vendidos.get(s["producto_id"], 0.0)
        stock_actual = s["stock_total"]
        indice_rotacion = (cantidad_vendida / stock_actual) if stock_actual > 0 else None
        resultado.append(
            schemas.RotacionProducto(
                producto_id=s["producto_id"],
                codigo=s["codigo_interno"],  # el dict de saldos usa "codigo_interno", no "codigo"
                nombre=s["nombre"],
                cantidad_vendida_historica=cantidad_vendida,
                stock_actual=stock_actual,
                indice_rotacion=indice_rotacion,
                sin_movimiento=(cantidad_vendida == 0 and stock_actual > 0),
                costo_unitario_promedio=s["costo_unitario_promedio"],
            )
        )
    return resultado


def margen_por_producto(
    db: Session, limit: int = 10, desde: date | None = None, hasta: date | None = None
) -> list[schemas.MargenProducto]:
    """Cruza, solo en lectura, dos fuentes ya existentes: el costo unitario
    promedio de m03_inventario.saldos y el precio/monto vendido de
    productos_mas_vendidos (m13). margen_pct y rentabilidad son divisiones
    y restas sobre esos datos, no un calculo de costeo nuevo."""
    validators.validar_rango_fechas(desde, hasta)

    inventarios = inventario_service.listar_inventarios(db)
    saldos = inventario_service.saldos(db, inventarios[0].id) if inventarios else []
    costo_por_producto = {s["producto_id"]: s["costo_unitario_promedio"] for s in saldos}

    filas = repository.productos_mas_vendidos(db, limit, desde, hasta)

    resultado = []
    for f in filas:
        cantidad_vendida = f["cantidad_vendida"]
        precio_venta_promedio = (
            f["monto_vendido"] / cantidad_vendida if cantidad_vendida > 0 else 0.0
        )
        costo_unitario = costo_por_producto.get(f["producto_id"], 0.0)
        margen_pct = (
            (precio_venta_promedio - costo_unitario) / precio_venta_promedio * 100
            if precio_venta_promedio > 0
            else None
        )
        rentabilidad = f["monto_vendido"] - (costo_unitario * cantidad_vendida)
        resultado.append(
            schemas.MargenProducto(
                producto_id=f["producto_id"],
                codigo=f["codigo"],
                nombre=f["nombre"],
                costo_unitario=costo_unitario,
                precio_venta_promedio=precio_venta_promedio,
                margen_pct=margen_pct,
                rentabilidad=rentabilidad,
            )
        )
    return resultado
