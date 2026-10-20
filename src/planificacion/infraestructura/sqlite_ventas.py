"""Persistencia transaccional de importaciones de ventas."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

from .. import __version__
from ..dominio.ventas import FuenteVentas, LoteVentas, Producto, VentaDiaria

ESQUEMA = """
CREATE TABLE IF NOT EXISTS importaciones_ventas (
    id TEXT PRIMARY KEY,
    protocolo_id TEXT NOT NULL,
    protocolo_sha256 TEXT NOT NULL,
    version_preparacion TEXT NOT NULL,
    version_codigo TEXT NOT NULL,
    fecha_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fuentes_ventas (
    importacion_id TEXT NOT NULL REFERENCES importaciones_ventas(id),
    archivo TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    anio INTEGER NOT NULL,
    filas INTEGER NOT NULL CHECK(filas > 0),
    cantidad_total INTEGER NOT NULL CHECK(cantidad_total > 0),
    PRIMARY KEY(importacion_id, archivo)
);
CREATE TABLE IF NOT EXISTS productos_ventas (
    importacion_id TEXT NOT NULL REFERENCES importaciones_ventas(id),
    producto_id TEXT NOT NULL,
    producto_original TEXT NOT NULL CHECK(length(producto_original) > 0),
    nombre_modelado TEXT NOT NULL CHECK(length(nombre_modelado) > 0),
    local_original TEXT NOT NULL CHECK(length(local_original) > 0),
    anio INTEGER NOT NULL,
    PRIMARY KEY(importacion_id, producto_id),
    UNIQUE(importacion_id, local_original, producto_original, anio)
);
CREATE TABLE IF NOT EXISTS filas_ventas (
    importacion_id TEXT NOT NULL,
    archivo_origen TEXT NOT NULL,
    fila_origen INTEGER NOT NULL CHECK(fila_origen >= 2),
    producto_id TEXT NOT NULL,
    fecha TEXT NOT NULL,
    cantidad INTEGER NOT NULL CHECK(typeof(cantidad) = 'integer' AND cantidad > 0),
    descuento TEXT NOT NULL CHECK(descuento IN ('Y','N')),
    ingles_fuente TEXT NOT NULL,
    PRIMARY KEY(importacion_id, archivo_origen, fila_origen),
    UNIQUE(importacion_id, archivo_origen, producto_id, fecha, descuento),
    FOREIGN KEY(importacion_id, producto_id) REFERENCES productos_ventas(importacion_id, producto_id),
    FOREIGN KEY(importacion_id, archivo_origen) REFERENCES fuentes_ventas(importacion_id, archivo)
);
CREATE TABLE IF NOT EXISTS ventas_diarias (
    importacion_id TEXT NOT NULL,
    producto_id TEXT NOT NULL,
    fecha TEXT NOT NULL,
    cantidad INTEGER,
    filas_origen TEXT NOT NULL,
    archivo_origen TEXT NOT NULL,
    CHECK((cantidad IS NULL AND filas_origen = '[]') OR
          (typeof(cantidad) = 'integer' AND cantidad > 0 AND filas_origen <> '[]')),
    PRIMARY KEY(importacion_id, producto_id, fecha),
    FOREIGN KEY(importacion_id, producto_id) REFERENCES productos_ventas(importacion_id, producto_id),
    FOREIGN KEY(importacion_id, archivo_origen) REFERENCES fuentes_ventas(importacion_id, archivo)
);
"""


class SQLiteVentas:
    def __init__(self, ruta: Path):
        self.ruta = ruta.resolve()

    @contextmanager
    def _conexion(self, escritura=False):
        if escritura:
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            conexion = sqlite3.connect(self.ruta, isolation_level=None)
        else:
            if not self.ruta.is_file():
                raise FileNotFoundError("No existe la base de ventas indicada")
            conexion = sqlite3.connect(self.ruta.as_uri() + "?mode=ro", uri=True,
                                       isolation_level=None)
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON")
        try:
            version = conexion.execute("PRAGMA user_version").fetchone()[0]
            if version not in ((0, 1) if escritura else (1,)):
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

    def guardar(self, lote: LoteVentas) -> str:
        identidad = lote.identificador
        with self._conexion(escritura=True) as c:
            c.executescript(ESQUEMA)
            c.execute("PRAGMA user_version = 1")
            c.execute("BEGIN IMMEDIATE")
            if c.execute("SELECT id FROM importaciones_ventas WHERE id = ?", (identidad,)).fetchone():
                return identidad
            c.execute("INSERT INTO importaciones_ventas VALUES (?, ?, ?, ?, ?, ?)",
                      (identidad, lote.protocolo_id, lote.protocolo_sha256,
                       lote.version_preparacion, __version__,
                       datetime.now(timezone.utc).isoformat(timespec="seconds")))
            c.executemany("INSERT INTO fuentes_ventas VALUES (?, ?, ?, ?, ?, ?)",
                          ((identidad, f.archivo, f.sha256, f.anio, f.filas, f.cantidad_total)
                           for f in lote.fuentes))
            c.executemany("INSERT INTO productos_ventas VALUES (?, ?, ?, ?, ?, ?)",
                          ((identidad, p.producto_id, p.producto_original, p.nombre_modelado,
                            p.local_original, p.anio) for p in lote.productos))
            c.executemany("INSERT INTO filas_ventas VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          ((identidad, f.archivo_origen, f.fila_origen, f.producto_id,
                            f.fecha.isoformat(), f.cantidad, f.descuento, f.ingles_fuente)
                           for f in lote.filas))
            c.executemany("INSERT INTO ventas_diarias VALUES (?, ?, ?, ?, ?, ?)",
                          ((identidad, d.producto_id, d.fecha.isoformat(), d.cantidad,
                            json.dumps(d.filas_origen), d.archivo_origen) for d in lote.diarias))
        return identidad

    def listar_importaciones(self) -> list[dict]:
        with self._conexion() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM importaciones_ventas ORDER BY fecha_utc, id")]

    def obtener_producto(self, importacion_id: str, producto_id: str) -> Producto:
        with self._conexion() as c:
            r = c.execute("""SELECT producto_id, producto_original, nombre_modelado,
                             local_original, anio FROM productos_ventas
                             WHERE importacion_id = ? AND producto_id = ?""",
                          (importacion_id, producto_id)).fetchone()
            if r is None:
                raise LookupError("Producto o importación inexistente")
            return Producto(**dict(r))

    def listar_productos(self, importacion_id: str) -> tuple[Producto, ...]:
        with self._conexion() as c:
            filas = c.execute("""SELECT producto_id, producto_original, nombre_modelado,
                                 local_original, anio FROM productos_ventas
                                 WHERE importacion_id = ? ORDER BY producto_id""", (importacion_id,))
            return tuple(Producto(**dict(r)) for r in filas)

    def obtener_fuentes(self, importacion_id: str) -> tuple[FuenteVentas, ...]:
        with self._conexion() as c:
            filas = c.execute("""SELECT archivo, sha256, anio, filas, cantidad_total
                                 FROM fuentes_ventas WHERE importacion_id = ? ORDER BY anio, archivo""",
                              (importacion_id,))
            return tuple(FuenteVentas(**dict(r)) for r in filas)

    def obtener_diarias(self, importacion_id: str, producto_id: str,
                        inicio: date, fin: date) -> tuple[VentaDiaria, ...]:
        with self._conexion() as c:
            filas = c.execute("""SELECT producto_id, fecha, cantidad, filas_origen, archivo_origen
                                 FROM ventas_diarias WHERE importacion_id = ? AND producto_id = ?
                                 AND fecha BETWEEN ? AND ? ORDER BY fecha""",
                              (importacion_id, producto_id, inicio.isoformat(), fin.isoformat()))
            return tuple(VentaDiaria(r["producto_id"], date.fromisoformat(r["fecha"]),
                                     r["cantidad"], tuple(json.loads(r["filas_origen"])),
                                     r["archivo_origen"]) for r in filas)
