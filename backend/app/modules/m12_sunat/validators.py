import re

from fastapi import HTTPException, status

from app.modules.m12_sunat.models import TIPOS_COMPROBANTE

RUC_REGEX = re.compile(r"^\d{11}$")
DNI_REGEX = re.compile(r"^\d{8}$")

TRANSICIONES_VALIDAS = {
    "EMITIDO": {"ACEPTADO", "RECHAZADO", "ANULADO"},
    "ACEPTADO": {"ANULADO"},
    "RECHAZADO": set(),
    "ANULADO": set(),
}


def validar_tipo_comprobante(tipo_comprobante: str) -> None:
    if tipo_comprobante not in TIPOS_COMPROBANTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"tipo_comprobante invalido. Validos: {', '.join(TIPOS_COMPROBANTE)}",
        )


def validar_comprobante_existe(comprobante):
    if comprobante is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comprobante no encontrado"
        )
    return comprobante


def validar_orden_despachada(orden) -> None:
    if orden.estado != "DESPACHADA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La orden de venta #{orden.id} esta en estado {orden.estado}; "
                "solo se puede emitir un comprobante para ordenes DESPACHADAS "
                "(mercaderia ya entregada)."
            ),
        )


def validar_no_duplicado(existente) -> None:
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Ya existe el comprobante {existente.numero_completo} para esta orden de venta"
            ),
        )


def validar_documento_cliente(tipo_comprobante: str, cliente_ruc: str) -> None:
    if tipo_comprobante == "FACTURA" and not RUC_REGEX.match(cliente_ruc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"FACTURA requiere RUC valido de 11 digitos. El cliente tiene "
                f"'{cliente_ruc}', que no cumple el formato."
            ),
        )
    if tipo_comprobante == "BOLETA" and not (RUC_REGEX.match(cliente_ruc) or DNI_REGEX.match(cliente_ruc)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"BOLETA requiere DNI (8 digitos) o RUC (11 digitos) valido. El cliente "
                f"tiene '{cliente_ruc}', que no cumple ningun formato."
            ),
        )


def validar_transicion(estado_actual: str, estado_destino: str) -> None:
    permitidos = TRANSICIONES_VALIDAS.get(estado_actual, set())
    if estado_destino not in permitidos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No se puede pasar de {estado_actual} a {estado_destino}. "
                f"Transiciones validas desde {estado_actual}: {sorted(permitidos) or 'ninguna'}"
            ),
        )
