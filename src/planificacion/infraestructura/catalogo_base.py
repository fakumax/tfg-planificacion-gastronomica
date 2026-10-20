"""Consulta del catálogo disponible sin crear una base vacía."""

from pathlib import Path

from .base_sqlite import conexion_sqlite
from .sqlite_ejecuciones import SQLiteEjecuciones
from .sqlite_ventas import SQLiteVentas


def estado_base(ruta: Path) -> tuple[list[dict], list[dict]]:
    if not ruta.exists():
        return [], []
    with conexion_sqlite(ruta) as c:
        tablas = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return (SQLiteVentas(ruta).listar_importaciones() if "importaciones_ventas" in tablas else [],
            SQLiteEjecuciones(ruta).listar() if "ejecuciones" in tablas else [])
