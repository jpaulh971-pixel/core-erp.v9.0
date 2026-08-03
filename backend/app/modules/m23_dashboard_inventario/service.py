"""Logica de negocio del modulo m23_dashboard_inventario (Fase 4A - base).

Unica funcionalidad de esta fase: resumen_dashboard(), que arma el
resumen gerencial de inventario a partir de indicadores YA calculados
en otros modulos. Ningun indicador se recalcula aca -- este modulo
solo lee y consolida resultados que las funciones de negocio de esos
modulos ya producen. No se toca ningun stock, kardex, costo ni tabla
existente.

Origen de cada campo del resumen:

  - valor_total_inventario, cantidad_productos, productos_bajo_stock
        -> m19_reportes.service.reporte_inventario_valorizado()
  - cantidad_lotes
        -> m19_reportes.service.reporte_inventario_por_lote()
           (inventario_id=None -> todos los inventarios)
  - productos_proximos_vencer, productos_vencidos
        -> m19_reportes.service.reporte_proximos_vencer()
           (inventario_id=None -> todos los inventarios)
  - riesgo_merma_total
        -> m22_inteligencia_inventario.service.indicadores_inventario()
           sumado entre todos los inventarios (m22 calcula el riesgo
           de merma por inventario_id, no existe una version global de
           esa funcion en m22, por eso se recorre aca sin reimplementar
           su calculo interno).
"""
from sqlalchemy.orm import Session

from app.modules.m19_reportes import service as reportes_service
from app.modules.m22_inteligencia_inventario import service as inteligencia_service
from app.modules.m23_dashboard_inventario import repository, schemas


def _riesgo_merma_total(db: Session) -> int:
    """Suma, entre todos los inventarios, la cantidad de productos con
    riesgo de merma ALTO o CRITICO. Reutiliza
    m22_inteligencia_inventario.service.indicadores_inventario() tal
    cual (mismos umbrales/parametros por defecto de ese modulo); no
    reimplementa la clasificacion de riesgo."""
    total = 0
    for inventario in repository.listar_inventarios(db):
        resumen_inteligencia = inteligencia_service.indicadores_inventario(db, inventario.id)
        total += (
            resumen_inteligencia.productos_riesgo_critico
            + resumen_inteligencia.productos_riesgo_alto
        )
    return total


def resumen_dashboard(db: Session) -> schemas.ResumenDashboardInventario:
    valorizado = reportes_service.reporte_inventario_valorizado(db)
    por_lote = reportes_service.reporte_inventario_por_lote(db, inventario_id=None)
    proximos_vencer = reportes_service.reporte_proximos_vencer(db, inventario_id=None)

    return schemas.ResumenDashboardInventario(
        valor_total_inventario=valorizado.valor_total_inventario,
        cantidad_productos=valorizado.total_productos,
        cantidad_lotes=por_lote.total_lotes,
        productos_bajo_stock=valorizado.productos_bajo_stock_minimo,
        productos_proximos_vencer=proximos_vencer.proximos_a_vencer,
        productos_vencidos=proximos_vencer.vencidos,
        riesgo_merma_total=_riesgo_merma_total(db),
    )
