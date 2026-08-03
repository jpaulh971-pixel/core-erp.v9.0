"""Schemas de la Fase 9: importacion masiva de Compras Nacionalizadas
desde Excel. No reemplaza ni toca schemas.py (compras manuales); son
tipos nuevos, exclusivos de este flujo.
"""
from typing import Optional

from pydantic import BaseModel


class FilaImportacionCompraOut(BaseModel):
    numero_fila: int
    # Nombre de la hoja del Excel de la que proviene esta fila (el archivo
    # del cliente trae mas de una hoja; antes solo se leia la primera).
    hoja: Optional[str] = None
    orden_compra: Optional[str] = None
    proveedor: Optional[str] = None
    producto: Optional[str] = None
    cantidad: Optional[float] = None
    costo_unitario: Optional[float] = None
    lote: Optional[str] = None
    fecha_elaboracion: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    factura: Optional[str] = None
    dua: Optional[str] = None
    pais_origen: Optional[str] = None
    fecha_documento: Optional[str] = None
    observaciones: Optional[str] = None
    # --- Opcionales, formato Excel del cliente (COMPRAS_ECO_NEOAGROX_2026).
    moneda: Optional[str] = None
    presentacion: Optional[str] = None
    unidad_medida: Optional[str] = None
    cantidad_por_unidad: Optional[float] = None
    dias_credito: Optional[int] = None
    ruc: Optional[str] = None
    valida: bool
    mensaje_error: Optional[str] = None


class PreviewImportacionComprasOut(BaseModel):
    nombre_archivo: str
    inventario_destino_id: int
    total_filas: int
    filas_validas: int
    filas_con_error: int
    ordenes_a_crear: int
    # Nombres de las hojas del Excel que se reconocieron y procesaron (las
    # que no tenian las columnas obligatorias se ignoran y no aparecen aqui).
    hojas_procesadas: list[str] = []
    filas: list[FilaImportacionCompraOut]


class OrdenCreadaImportacionOut(BaseModel):
    numero_orden_externo: str
    orden_compra_id: int
    estado: str
    items_creados: int


class ConfirmarImportacionComprasOut(BaseModel):
    nombre_archivo: str
    inventario_destino_id: int
    ordenes_creadas: list[OrdenCreadaImportacionOut]
    filas_procesadas: int
    filas_fallidas: list[FilaImportacionCompraOut]
    hojas_procesadas: list[str] = []
