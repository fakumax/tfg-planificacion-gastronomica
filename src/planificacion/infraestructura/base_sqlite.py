"""Ciclo de vida de conexiones SQLite para los adaptadores locales."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def conexion_sqlite(ruta: Path, escritura=False):
    ruta = ruta.resolve()
    if escritura:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        conexion = sqlite3.connect(ruta, isolation_level=None)
    else:
        if not ruta.is_file():
            raise FileNotFoundError("No existe la base indicada")
        conexion = sqlite3.connect(ruta.as_uri() + "?mode=ro", uri=True, isolation_level=None)
    try:
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON")
        version = conexion.execute("PRAGMA user_version").fetchone()[0]
        if version not in ((0, 1, 2) if escritura else (1, 2)):
            raise ValueError("La versión de la base no es compatible con este programa")
        yield conexion
        if conexion.in_transaction:
            conexion.commit()
    except Exception:
        if conexion.in_transaction:
            conexion.rollback()
        raise
    finally:
        conexion.close()
