"""Carga de una versión conocida del recetario, en modo lectura."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

from ..dominio.recetas import Recetario, interpretar_recetario


def cargar_recetario(ruta: Path, sha256_esperado: str) -> Recetario:
    raw = ruta.read_bytes()
    huella = hashlib.sha256(raw).hexdigest()
    if huella != sha256_esperado:
        raise ValueError("La huella del recetario es diferente de la versión declarada")
    modelo = json.loads(raw.decode("utf-8-sig"), parse_float=Decimal)
    return interpretar_recetario(modelo, huella)
