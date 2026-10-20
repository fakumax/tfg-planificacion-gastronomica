"""Entradas explícitamente sintéticas, sin depender de originales locales."""

import hashlib

from planificacion.configuracion import recurso_json
from planificacion.entradas import CANTIDAD, FECHA, LOCAL, PRODUCTO
from planificacion.infraestructura.csv_ventas import preparar_ventas
from planificacion.infraestructura.sqlite_ventas import SQLiteVentas
from test_entradas import csv_sintetico, fila


def importacion_sintetica(raiz, multiplicador=1):
    protocolo = recurso_json("protocolo_tp3_v1.json")
    seleccion = protocolo["seleccion"]
    filas = [fila(**{FECHA: "2025-11-01", LOCAL: seleccion["local_original"],
                      PRODUCTO: p["producto_original"], CANTIDAD: str(n * multiplicador)})
             for n, p in enumerate(seleccion["productos"], 1)]
    raw = csv_sintetico(filas)
    (raiz / "prueba.csv").write_bytes(raw)
    manifiesto = {"archivos_csv": [{"archivo": "prueba.csv", "anio_publicado": 2025,
        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "codificacion": "cp949",
        "filas": 7, "fechas_distintas": 1, "fecha_min": "2025-11-01", "fecha_max": "2025-11-01",
        "productos": 7, "cantidad_total": 28 * multiplicador, "locales": [seleccion["local_original"]],
        "faltantes": {"producto_ingles_fuente": 7}}]}
    lote = preparar_ventas(raiz, manifiesto, protocolo)
    base = raiz / "prototipo.sqlite3"
    identidad = SQLiteVentas(base).guardar(lote)
    return base, identidad
