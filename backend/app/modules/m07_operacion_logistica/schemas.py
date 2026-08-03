"""Esquemas Pydantic (request/response) del modulo m07_operacion_logistica."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RecepcionCrear(BaseModel):
    producto_id: int
    proveedor_id: int
    orden_compra_id: Optional[int] = Field(
        default=None,
        description=(
            "Si la mercaderia ya fue recibida formalmente por una Orden de "
            "Compra RECIBIDA, referenciarla aqui: esta operacion NO vuelve a "
            "ingresar el stock (evita duplicar Kardex), solo registra el "
            "seguimiento fisico. Si se omite, esta operacion SI ingresa el "
            "stock (recepcion directa, p. ej. importacion sin OC formal)."
        ),
    )
    inventario_id: Optional[int] = Field(
        default=None,
        description=(
            "Obligatorio solo para recepcion directa (cuando no se referencia "
            "orden_compra_id): inventario/almacen logico donde ingresa el "
            "stock, requerido por m03_inventario.IngresoInventarioCrear."
        ),
    )
    codigo_lote: str = Field(min_length=1, max_length=50)
    cantidad: float = Field(gt=0)
    costo_unitario: float = Field(ge=0)
    fecha_vencimiento: Optional[datetime] = None
    observaciones: Optional[str] = None


class InspeccionActualizar(BaseModel):
    conforme: bool
    observaciones: Optional[str] = None


class UbicacionActualizar(BaseModel):
    rack: str = Field(min_length=1, max_length=30)
    pasillo: str = Field(min_length=1, max_length=30)
    ubicacion_fisica: str = Field(min_length=1, max_length=100)
    observaciones: Optional[str] = None


class DisponibleActualizar(BaseModel):
    observaciones: Optional[str] = None


class ReservaCrear(BaseModel):
    orden_venta_id: int = Field(
        description="Orden de venta CONFIRMADA que incluya este producto entre sus items"
    )
    observaciones: Optional[str] = None


class PickingActualizar(BaseModel):
    observaciones: Optional[str] = None


class PackingActualizar(BaseModel):
    peso: float = Field(gt=0)
    cajas: int = Field(gt=0)
    pallets: int = Field(gt=0)
    observaciones: Optional[str] = None


class CargaActualizar(BaseModel):
    vehiculo: str = Field(min_length=1, max_length=30)
    conductor: str = Field(min_length=1, max_length=120)
    fecha_carga: Optional[datetime] = None
    observaciones: Optional[str] = None


class DespachoActualizar(BaseModel):
    observaciones: Optional[str] = None


class EntregaActualizar(BaseModel):
    observaciones: Optional[str] = None


class CierreActualizar(BaseModel):
    observaciones: Optional[str] = None


class HistorialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_hora: datetime
    usuario_username: str
    estado_anterior: Optional[str] = None
    estado_nuevo: str
    observaciones: Optional[str] = None


class OperacionLogisticaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado: str
    producto_id: int
    proveedor_id: int
    orden_compra_id: Optional[int] = None
    lote_id: Optional[int] = None
    codigo_lote: str
    cantidad: float
    costo_unitario: float
    conforme: Optional[bool] = None
    observaciones_inspeccion: Optional[str] = None
    rack: Optional[str] = None
    pasillo: Optional[str] = None
    ubicacion_fisica: Optional[str] = None
    orden_venta_id: Optional[int] = None
    lote_picking_id: Optional[int] = None
    cantidad_picking: Optional[float] = None
    metodo_consumo: Optional[str] = None
    peso: Optional[float] = None
    cajas: Optional[int] = None
    pallets: Optional[int] = None
    vehiculo: Optional[str] = None
    conductor: Optional[str] = None
    fecha_carga: Optional[datetime] = None
    creado_en: datetime
    recepcion_en: Optional[datetime] = None
    inspeccion_en: Optional[datetime] = None
    ubicacion_en: Optional[datetime] = None
    disponible_en: Optional[datetime] = None
    reservado_en: Optional[datetime] = None
    picking_en: Optional[datetime] = None
    packing_en: Optional[datetime] = None
    carga_en: Optional[datetime] = None
    despacho_en: Optional[datetime] = None
    entregado_en: Optional[datetime] = None
    cerrado_en: Optional[datetime] = None
    historial: list[HistorialOut] = []
