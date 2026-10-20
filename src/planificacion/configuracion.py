"""Recursos versionados y composición de sus adaptadores de lectura."""

import json
from importlib.resources import files
from pathlib import Path

from .infraestructura.recetario import cargar_recetario


def recurso_json(nombre: str) -> dict:
    return json.loads(files("planificacion").joinpath("recursos", nombre).read_text(encoding="utf-8"))


def recetario_configurado(ruta: Path | None = None):
    recurso = ruta or files("planificacion").joinpath("recursos", "recetario_modelado_v1.json")
    huella = recurso_json("protocolo_tp3_v1.json")["recetario"]["archivos"]["recetario_modelado_v1.json"]
    return cargar_recetario(recurso, huella)
