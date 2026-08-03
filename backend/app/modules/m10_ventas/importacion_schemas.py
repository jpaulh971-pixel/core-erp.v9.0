"""Schemas de la Fase 10: importacion masiva de Ventas desde Excel. No
reemplaza ni toca schemas.py (ventas manuales); son tipos nuevos,
exclusivos de este flujo.
"""
from typing import Optional

from pydantic import BaseModel


class FilaImportacionVentaOut(BaseModel):
    numero_fila: int
    # Nombre de la hoja del Excel de la que proviene esta fila.
    hoja: Optional[str] = None
    orden_venta: Optional[str] = None
    vendedor: Optional[str] = None
    moneda: Optional[str] = None
    cantidad: Optional[float] = None
    unidad_medida: Optional[str] = None
    descripcion: Optional[str] = None
    codigo_producto: Optional[str] = None
    precio_venta: Optional[float] = None
    sub_total: Optional[float] = None
    igv: Optional[float] = None
    total: Optional[float] = None
    fecha_emision: Optional[str] = None
    dias_credito: Optional[int] = None
    fecha_vencimiento: Optional[str] = None
    factura: Optional[str] = None
    estado: Optional[str] = None
    ruc: Optional[str] = None
    cliente: Optional[str] = None
    anio: Optional[int] = None
    mes: Optional[str] = None
    guia_remision: Optional[str] = None
    cultivo: Optional[str] = None
    fundo: Optional[str] = None
    lote: Optional[str] = None
    observaciones: Optional[str] = None
    valida: bool
    mensaje_error: Optional[str] = None


class PreviewImportacionVentasOut(BaseModel):
    nombre_archivo: str
    inventario_salida_id: int
    total_filas: int
    filas_validas: int
    filas_con_error: int
    ordenes_a_crear: int
    # Nombres de las hojas del Excel que se reconocieron y procesaron.
    hojas_procesadas: list[str] = []
    filas: list[FilaImportacionVentaOut]


class OrdenCreadaImportacionVentaOut(BaseModel):
    numero_orden_externo: str
    orden_venta_id: int
    estado: str
    items_creados: int


class ConfirmarImportacionVentasOut(BaseModel):
    nombre_archivo: str
    inventario_salida_id: int
    ordenes_creadas: list[OrdenCreadaImportacionVentaOut]
    filas_procesadas: int
    hojas_procesadas: list[str] = []
