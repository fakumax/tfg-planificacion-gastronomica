"""Consulta histórica independiente del almacenamiento y de la presentación."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol

from ..dominio.ventas import FuenteVentas, Producto, VentaDiaria


class LecturaVentas(Protocol):
    def obtener_producto(self, importacion_id: str, producto_id: str) -> Producto: ...
    def obtener_diarias(self, importacion_id: str, producto_id: str,
                        inicio: date, fin: date) -> tuple[VentaDiaria, ...]: ...
    def obtener_fuentes(self, importacion_id: str) -> tuple[FuenteVentas, ...]: ...


@dataclass(frozen=True)
class ConsultaVentas:
    producto: Producto
    diarias: tuple[VentaDiaria, ...]
    fuentes: tuple[FuenteVentas, ...]

    @property
    def dias_observados(self) -> int:
        return sum(d.cantidad is not None for d in self.diarias)

    @property
    def dias_sin_fila(self) -> int:
        return len(self.diarias) - self.dias_observados

    @property
    def total_observado(self) -> int | None:
        if not self.dias_observados:
            return None
        return sum(d.cantidad for d in self.diarias if d.cantidad is not None)

    @property
    def incompleta(self) -> bool:
        return self.dias_sin_fila > 0


def consultar_ventas(repo: LecturaVentas, importacion_id: str, producto_id: str,
                      inicio: date, fin: date) -> ConsultaVentas:
    if type(inicio) is not date or type(fin) is not date or inicio > fin:
        raise ValueError("El período debe contener fechas válidas en orden")
    producto = repo.obtener_producto(importacion_id, producto_id)
    if inicio.year != producto.anio or fin.year != producto.anio:
        raise ValueError("El período debe estar dentro del año importado para el producto")
    diarias = repo.obtener_diarias(importacion_id, producto_id, inicio, fin)
    esperadas = tuple(inicio + timedelta(days=n) for n in range((fin - inicio).days + 1))
    if tuple(d.fecha for d in diarias) != esperadas:
        raise ValueError("El calendario almacenado está incompleto; revisar la importación")
    archivos = {d.archivo_origen for d in diarias}
    fuentes = tuple(f for f in repo.obtener_fuentes(importacion_id) if f.archivo in archivos)
    if {f.archivo for f in fuentes} != archivos:
        raise ValueError("La consulta no tiene toda su procedencia registrada")
    return ConsultaVentas(producto, diarias, fuentes)
