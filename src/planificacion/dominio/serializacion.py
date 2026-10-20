"""Representación reproducible de fechas y cantidades, sin acceso a archivos."""

import json
from dataclasses import asdict, is_dataclass
from datetime import date
from decimal import Decimal


def convertir(valor):
    if is_dataclass(valor):
        return asdict(valor)
    if isinstance(valor, Decimal):
        if not valor.is_finite():
            raise ValueError("No se puede registrar una cantidad no finita")
        return str(valor)
    if isinstance(valor, date):
        return valor.isoformat()
    raise TypeError(f"Tipo no serializable: {type(valor).__name__}")


def canonico(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, default=convertir)


def normalizar(valor):
    return json.loads(canonico(valor))
