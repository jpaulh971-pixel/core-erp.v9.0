"""Endpoints FastAPI del modulo m19_reportes."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.deps import get_db, get_usuario_actual
from app.modules.m19_reportes import exportadores, schemas, service

router = APIRouter(prefix="/api/reportes", tags=["reportes"])

MEDIA_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MEDIA_PDF = "application/pdf"


def _descarga(contenido: bytes, media_type: str, nombre_archivo: str) -> StreamingResponse:
    from io import BytesIO

    return StreamingResponse(
        BytesIO(contenido),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.get("/ventas", response_model=schemas.ReporteVentas)
def reporte_ventas(
    desde: date | None = Query(default=None, description="Filtra por fecha de despacho"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de despacho"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.reporte_ventas(db, desde, hasta)


@router.get("/compras", response_model=schemas.ReporteCompras)
def reporte_compras(
    desde: date | None = Query(default=None, description="Filtra por fecha de recepcion"),
    hasta: date | None = Query(default=None, description="Filtra por fecha de recepcion"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.reporte_compras(db, desde, hasta)


@router.get("/inventario-valorizado", response_model=schemas.ReporteInventarioValorizado)
def reporte_inventario_valorizado(
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.reporte_inventario_valorizado(db)


# ---------------------------------------------------------------------
# FASE 2 - control gerencial para inventario perecible (solo lectura).
# ---------------------------------------------------------------------


@router.get("/inventario-por-lote", response_model=schemas.ReporteInventarioPorLote)
def reporte_inventario_por_lote(
    inventario_id: int | None = Query(
        default=None, description="Si se indica, filtra solo ese Inventario"
    ),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.reporte_inventario_por_lote(db, inventario_id)


@router.get("/proximos-vencer", response_model=schemas.ReporteProximosVencer)
def reporte_proximos_vencer(
    inventario_id: int | None = Query(
        default=None, description="Si se indica, filtra solo ese Inventario"
    ),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.reporte_proximos_vencer(db, inventario_id)


@router.get("/resumen-general", response_model=schemas.ResumenGeneral)
def resumen_general(
    desde: date | None = Query(default=None, description="Filtra ventas/compras desde esta fecha"),
    hasta: date | None = Query(default=None, description="Filtra ventas/compras hasta esta fecha"),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    return service.resumen_general(db, desde, hasta)


# ---------------------------------------------------------------------
# Exportacion a Excel / PDF (mismos filtros, mismos datos que los
# endpoints JSON de arriba; no agregan ninguna consulta nueva).
# ---------------------------------------------------------------------


@router.get("/ventas/exportar/excel")
def exportar_ventas_excel(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    reporte = service.reporte_ventas(db, desde, hasta)
    return _descarga(exportadores.ventas_excel(reporte), MEDIA_XLSX, "reporte_ventas.xlsx")


@router.get("/ventas/exportar/pdf")
def exportar_ventas_pdf(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    reporte = service.reporte_ventas(db, desde, hasta)
    return _descarga(exportadores.ventas_pdf(reporte), MEDIA_PDF, "reporte_ventas.pdf")


@router.get("/compras/exportar/excel")
def exportar_compras_excel(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    reporte = service.reporte_compras(db, desde, hasta)
    return _descarga(exportadores.compras_excel(reporte), MEDIA_XLSX, "reporte_compras.xlsx")


@router.get("/compras/exportar/pdf")
def exportar_compras_pdf(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    reporte = service.reporte_compras(db, desde, hasta)
    return _descarga(exportadores.compras_pdf(reporte), MEDIA_PDF, "reporte_compras.pdf")


@router.get("/inventario-valorizado/exportar/excel")
def exportar_inventario_valorizado_excel(
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    reporte = service.reporte_inventario_valorizado(db)
    return _descarga(
        exportadores.inventario_valorizado_excel(reporte), MEDIA_XLSX, "inventario_valorizado.xlsx"
    )


@router.get("/inventario-valorizado/exportar/pdf")
def exportar_inventario_valorizado_pdf(
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    reporte = service.reporte_inventario_valorizado(db)
    return _descarga(
        exportadores.inventario_valorizado_pdf(reporte), MEDIA_PDF, "inventario_valorizado.pdf"
    )


@router.get("/resumen-general/exportar/excel")
def exportar_resumen_general_excel(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    reporte = service.resumen_general(db, desde, hasta)
    return _descarga(exportadores.resumen_general_excel(reporte), MEDIA_XLSX, "resumen_general.xlsx")


@router.get("/resumen-general/exportar/pdf")
def exportar_resumen_general_pdf(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    reporte = service.resumen_general(db, desde, hasta)
    return _descarga(exportadores.resumen_general_pdf(reporte), MEDIA_PDF, "resumen_general.pdf")


# ---------------------------------------------------------------------
# FASE 2 - control gerencial para inventario perecible: exportacion a
# Excel / PDF de los dos reportes nuevos, mismo patron (mismos filtros,
# mismos datos que los endpoints JSON de arriba; no agregan ninguna
# consulta nueva) que ya usan ventas/compras/inventario-valorizado/
# resumen-general.
# ---------------------------------------------------------------------


@router.get("/inventario-por-lote/exportar/excel")
def exportar_inventario_por_lote_excel(
    inventario_id: int | None = Query(
        default=None, description="Si se indica, filtra solo ese Inventario"
    ),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    reporte = service.reporte_inventario_por_lote(db, inventario_id)
    return _descarga(
        exportadores.inventario_por_lote_excel(reporte), MEDIA_XLSX, "inventario_por_lote.xlsx"
    )


@router.get("/inventario-por-lote/exportar/pdf")
def exportar_inventario_por_lote_pdf(
    inventario_id: int | None = Query(
        default=None, description="Si se indica, filtra solo ese Inventario"
    ),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    reporte = service.reporte_inventario_por_lote(db, inventario_id)
    return _descarga(
        exportadores.inventario_por_lote_pdf(reporte), MEDIA_PDF, "inventario_por_lote.pdf"
    )


@router.get("/proximos-vencer/exportar/excel")
def exportar_proximos_vencer_excel(
    inventario_id: int | None = Query(
        default=None, description="Si se indica, filtra solo ese Inventario"
    ),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    reporte = service.reporte_proximos_vencer(db, inventario_id)
    return _descarga(
        exportadores.proximos_vencer_excel(reporte), MEDIA_XLSX, "proximos_vencer.xlsx"
    )


@router.get("/proximos-vencer/exportar/pdf")
def exportar_proximos_vencer_pdf(
    inventario_id: int | None = Query(
        default=None, description="Si se indica, filtra solo ese Inventario"
    ),
    db: Session = Depends(get_db),
    _u=Depends(get_usuario_actual),
):
    reporte = service.reporte_proximos_vencer(db, inventario_id)
    return _descarga(
        exportadores.proximos_vencer_pdf(reporte), MEDIA_PDF, "proximos_vencer.pdf"
    )
