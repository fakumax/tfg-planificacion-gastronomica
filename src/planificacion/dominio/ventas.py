"""Datos inmutables de una importación y su calendario observado."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date


@dataclass(frozen=True)
class Producto:
    producto_id: str
    producto_original: str
    nombre_modelado: str
    local_original: str
    anio: int


@dataclass(frozen=True)
class FuenteVentas:
    archivo: str
    sha256: str
    anio: int
    filas: int
    cantidad_total: int


@dataclass(frozen=True)
class FilaVenta:
    producto_id: str
    fecha: date
    cantidad: int
    descuento: str
    fila_origen: int
    archivo_origen: str
    ingles_fuente: str


@dataclass(frozen=True)
class VentaDiaria:
    producto_id: str
    fecha: date
    cantidad: int | None
    filas_origen: tuple[int, ...]
    archivo_origen: str

    @property
    def estado(self) -> str:
        return "sin_fila" if self.cantidad is None else "observado"


@dataclass(frozen=True)
class LoteVentas:
    protocolo_id: str
    protocolo_sha256: str
    version_preparacion: str
    fuentes: tuple[FuenteVentas, ...]
    productos: tuple[Producto, ...]
    filas: tuple[FilaVenta, ...]
    diarias: tuple[VentaDiaria, ...]

    @property
    def identificador(self) -> str:
        contenido = json.dumps(asdict(self), ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), default=lambda d: d.isoformat())
        return hashlib.sha256(contenido.encode("utf-8")).hexdigest()
