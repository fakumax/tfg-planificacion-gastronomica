"""Versiones y huellas de código sin rutas personales ni credenciales."""

import hashlib
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from ..dominio.serializacion import canonico


def capturar_entorno() -> dict:
    bibliotecas = {}
    for nombre in ("numpy", "scikit-learn", "scipy", "joblib", "narwhals", "cloudpickle", "threadpoolctl"):
        try:
            bibliotecas[nombre] = version(nombre)
        except PackageNotFoundError:
            bibliotecas[nombre] = None
    return {"python": platform.python_version(), "sistema": platform.system(),
            "arquitectura": platform.machine(), "bibliotecas": bibliotecas}


def capturar_codigo() -> dict:
    raiz = Path(__file__).resolve().parents[1]
    archivos = {p.relative_to(raiz).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(raiz.rglob("*")) if p.is_file() and p.suffix in (".py", ".json")}
    carpetas_nucleo = ("dominio/", "aplicacion/")
    adaptadores_nucleo = {"infraestructura/random_forest.py", "infraestructura/motor_experimento.py",
                         "recursos/protocolo_tp3_v1.json"}
    nucleo = {p: h for p, h in archivos.items() if p.startswith(carpetas_nucleo) or p in adaptadores_nucleo}
    return {"archivos": archivos, "huella_conjunto": hashlib.sha256(canonico(archivos).encode()).hexdigest(),
            "huella_nucleo_numerico": hashlib.sha256(canonico(nucleo).encode()).hexdigest()}
