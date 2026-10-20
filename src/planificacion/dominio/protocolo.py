"""Sello del protocolo registrado antes del entrenamiento."""

import hashlib

from .serializacion import canonico

HUELLA_PROTOCOLO_V1 = "f0de865b222f260e98f60b7cc92b298cffe2388eb9174c9f544472f549196990"


def validar_protocolo(protocolo: dict) -> str:
    huella = hashlib.sha256(canonico(protocolo).encode("utf-8")).hexdigest()
    if huella != HUELLA_PROTOCOLO_V1:
        raise ValueError("El protocolo cambió; registrar y revisar una nueva versión antes de ejecutar")
    return huella
