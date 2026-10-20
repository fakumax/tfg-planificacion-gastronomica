"""Comandos disponibles en la base del prototipo."""

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from . import __version__
from .entradas import verificar_entradas


def recurso_json(nombre: str) -> dict:
    return json.loads(files("planificacion").joinpath("recursos", nombre).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preparación del prototipo de planificación")
    parser.add_argument("--version", action="version", version=__version__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("estado", help="Mostrar el alcance implementado y el protocolo")
    verificar = comandos.add_parser("verificar-entradas", help="Comprobar originales sin modificarlos")
    verificar.add_argument("--directorio", type=Path, required=True, help="Carpeta de los CSV originales")
    verificar.add_argument("--manifiesto", type=Path, help="Otra versión de manifiesto revisada explícitamente")
    args = parser.parse_args(argv)
    try:
        if args.comando == "estado":
            salida = {
                "version": __version__,
                "python": platform.python_version(),
                "implementado": ["verificación de originales en modo lectura"],
                "pendiente": ["importación y consulta", "balance", "modelos", "interfaz", "evaluación"],
                "protocolo": recurso_json("protocolo_tp3_v1.json"),
            }
        else:
            manifiesto = (json.loads(args.manifiesto.read_text(encoding="utf-8-sig"))
                          if args.manifiesto else recurso_json("manifiesto_fuentes.json"))
            archivos = verificar_entradas(args.directorio, manifiesto)
            salida = {
                "estado": "correcto",
                "version_codigo": __version__,
                "python": platform.python_version(),
                "fecha_control_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "archivos": archivos,
                "limite": "Integridad y propiedades de entradas; no acredita calidad predictiva ni aplicación terminada",
            }
    except (OSError, ValueError, TypeError) as exc:
        print(f"No se completó el control: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(salida, ensure_ascii=False, indent=2))
    return 0
