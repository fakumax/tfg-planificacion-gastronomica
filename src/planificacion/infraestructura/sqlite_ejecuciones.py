"""Historial de ejecuciones sin sobrescritura y con comprobación de integridad."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..dominio.serializacion import canonico, normalizar
from ..aplicacion.referencias import comprobar_referencias
from .base_sqlite import conexion_sqlite
from .modelo_relacional import actualizar_en_conexion, proyectar_ejecucion

ESQUEMA = """
CREATE TABLE IF NOT EXISTS ejecuciones (
    id TEXT PRIMARY KEY,
    fecha_utc TEXT NOT NULL,
    tipo TEXT NOT NULL,
    version_codigo TEXT NOT NULL,
    huella_entrada TEXT NOT NULL CHECK(length(huella_entrada) = 64),
    huella_contenido TEXT NOT NULL CHECK(length(huella_contenido) = 64),
    contenido_json TEXT NOT NULL
);
"""


class SQLiteEjecuciones:
    def __init__(self, ruta: Path):
        self.ruta = ruta.resolve()

    def guardar(self, contenido: dict) -> str:
        contenido = normalizar(contenido)
        comprobar_referencias(self, contenido)
        cuerpo = canonico(contenido)
        entrada = canonico({"entradas": contenido["entradas"],
                            "contexto": contenido.get("contexto", {})})
        identidad = uuid4().hex
        with conexion_sqlite(self.ruta, escritura=True) as c:
            c.executescript(ESQUEMA)
            version = c.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                c.execute("PRAGMA user_version = 1")
            c.execute("BEGIN IMMEDIATE")
            if version in (2, 3):
                actualizar_en_conexion(c)
            c.execute("INSERT INTO ejecuciones VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (identidad, datetime.now(timezone.utc).isoformat(timespec="microseconds"),
                       contenido["tipo"], contenido["version_codigo"],
                       hashlib.sha256(entrada.encode("utf-8")).hexdigest(),
                       hashlib.sha256(cuerpo.encode("utf-8")).hexdigest(), cuerpo))
            if version == 0:
                actualizar_en_conexion(c)
            elif version in (2, 3):
                proyectar_ejecucion(c, c.execute('SELECT * FROM ejecuciones WHERE id=?', (identidad,)).fetchone())
        return identidad

    def recuperar(self, identidad: str) -> dict:
        with conexion_sqlite(self.ruta) as c:
            fila = c.execute("SELECT * FROM ejecuciones WHERE id = ?", (identidad,)).fetchone()
            if fila is None:
                raise LookupError("Ejecución inexistente")
            r = dict(fila)
        cuerpo = r.pop("contenido_json")
        if hashlib.sha256(cuerpo.encode("utf-8")).hexdigest() != r["huella_contenido"]:
            raise ValueError("La integridad de la ejecución no coincide con su huella")
        contenido = json.loads(cuerpo)
        entrada = canonico({"entradas": contenido["entradas"],
                            "contexto": contenido.get("contexto", {})})
        if (hashlib.sha256(entrada.encode("utf-8")).hexdigest() != r["huella_entrada"]
                or contenido["version_codigo"] != r["version_codigo"]
                or contenido["tipo"] != r["tipo"]):
            raise ValueError("La integridad de los metadatos de ejecución no coincide")
        r["ejecucion_id"] = r.pop("id")
        recuperado = {**contenido, **r}
        importacion = contenido.get('contexto', {}).get('importacion_id')
        if importacion:
            from .sqlite_ventas import SQLiteVentas
            lote = SQLiteVentas(self.ruta).recuperar_lote(importacion)
            recuperado['procedencia_preparacion'] = {'id': importacion,
                'version_preparacion': lote.version_preparacion, 'protocolo_id': lote.protocolo_id,
                'protocolo_sha256': lote.protocolo_sha256,
                'productos': normalizar(lote.productos), 'fuentes': normalizar(lote.fuentes)}
        return recuperado

    def listar(self) -> list[dict]:
        with conexion_sqlite(self.ruta) as c:
            return [dict(r) for r in c.execute("""SELECT id, fecha_utc, tipo, version_codigo,
                huella_entrada, huella_contenido FROM ejecuciones ORDER BY fecha_utc, id""")]
