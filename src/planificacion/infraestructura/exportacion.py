"""Exportación a una carpeta nueva; manifiesto de cierre con hashes de cada archivo."""

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from ..aplicacion.balance import RegistroEjecuciones
from ..dominio.serializacion import convertir


def _json(ruta: Path, contenido) -> None:
    with ruta.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2, allow_nan=False, default=convertir)
        f.write("\n")


def _csv(ruta: Path, filas: list[dict]) -> None:
    campos = list(dict.fromkeys(k for fila in filas for k in fila))
    with ruta.open("x", encoding="utf-8-sig", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({k: json.dumps(v, ensure_ascii=False, allow_nan=False)
                               if isinstance(v, (list, dict)) else v for k, v in fila.items()})


def exportar_evaluacion(registro: RegistroEjecuciones, identidad: str, destino: Path) -> dict:
    evaluacion = registro.recuperar(identidad)
    if evaluacion["tipo"] != "evaluacion_predictiva":
        raise ValueError("Se requiere una evaluación predictiva completa")
    seleccion = registro.recuperar(evaluacion["entradas"]["seleccion_id"])
    if (seleccion["tipo"] != "seleccion_modelos"
            or seleccion["huella_contenido"] != evaluacion["entradas"]["huella_seleccion"]):
        raise ValueError("La selección no coincide con la evaluación")
    destino = destino.resolve()
    destino.mkdir(parents=True, exist_ok=False)
    _json(destino / "ejecucion.json", evaluacion)
    _json(destino / "seleccion.json", seleccion)
    productos = evaluacion["resultado"]["productos"]
    for archivo, campo in (("predicciones", "predicciones"), ("metricas", "metricas"),
                            ("sensibilidad", "sensibilidad"), ("casos", "casos")):
        filas = [{"producto_id": p["producto_id"], **fila} for p in productos for fila in p[campo]]
        _csv(destino / f"{archivo}.csv", filas)
    _csv(destino / "configuraciones.csv", [{"producto_id": p["producto_id"],
        "estado": p["estado_configuracion"], **p["parametros"]} for p in productos])
    _json(destino / "bloques_p07.json", next((p["bloques_p07"] for p in productos if p["producto_id"] == "P07"), None))
    manifiesto = {"ejecucion_id": identidad, "seleccion_id": seleccion["ejecucion_id"],
        "huella_contenido": evaluacion["huella_contenido"],
        "fecha_exportacion_utc": datetime.now(timezone.utc).isoformat(),
        "archivos": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destino.iterdir())},
        "limite": "Resultados del protocolo registrado; no acreditan beneficios operativos ni independencia de ventanas"}
    _json(destino / "manifiesto_exportacion.json", manifiesto)
    return manifiesto
