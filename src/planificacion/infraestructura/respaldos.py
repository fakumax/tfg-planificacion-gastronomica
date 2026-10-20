"""Copias consistentes y restauración exclusiva de SQLite con comprobación de contenido."""

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .base_sqlite import conexion_sqlite
from .sqlite_ejecuciones import SQLiteEjecuciones
from .sqlite_ventas import SQLiteVentas


def verificar_base(ruta: Path) -> dict:
    with conexion_sqlite(ruta) as c:
        if [r[0] for r in c.execute("PRAGMA integrity_check")] != ["ok"] or c.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("La integridad o las relaciones de la base no son válidas")
        tablas = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not tablas.intersection({"importaciones_ventas", "ejecuciones"}):
        raise ValueError("La base no contiene datos del prototipo")
    importaciones = SQLiteVentas(ruta).listar_importaciones() if "importaciones_ventas" in tablas else []
    ejecuciones = SQLiteEjecuciones(ruta).listar() if "ejecuciones" in tablas else []
    for r in importaciones:
        SQLiteVentas(ruta).recuperar_lote(r["id"])
    for r in ejecuciones:
        SQLiteEjecuciones(ruta).recuperar(r["id"])
    return {"importaciones": len(importaciones), "ejecuciones": len(ejecuciones), "integridad": "correcta"}


def _manifiesto(ruta: Path) -> Path:
    return ruta.with_suffix(ruta.suffix + ".json")


def copiar_base(origen: Path, destino: Path) -> dict:
    origen, destino = origen.resolve(), destino.resolve()
    if destino.exists() or _manifiesto(destino).exists():
        raise FileExistsError("La copia requiere un destino nuevo")
    verificar_base(origen)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("xb"):
        pass
    with conexion_sqlite(origen) as fuente:
        with closing(sqlite3.connect(destino)) as salida:
            fuente.backup(salida)
    resumen = verificar_base(destino)
    manifiesto = {**resumen, "sha256": hashlib.sha256(destino.read_bytes()).hexdigest(),
                  "fecha_utc": datetime.now(timezone.utc).isoformat(), "metodo": "sqlite3.Connection.backup"}
    with _manifiesto(destino).open("x", encoding="utf-8") as f:
        json.dump(manifiesto, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return manifiesto


def restaurar_base(copia: Path, destino: Path) -> dict:
    copia = copia.resolve()
    manifiesto = json.loads(_manifiesto(copia).read_text(encoding="utf-8"))
    if hashlib.sha256(copia.read_bytes()).hexdigest() != manifiesto["sha256"]:
        raise ValueError("La copia no coincide con su huella; no se restaura")
    return copiar_base(copia, destino)
