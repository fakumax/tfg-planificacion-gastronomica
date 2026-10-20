"""Ejemplos supervisados con calendario real y corte de conocimiento explícito."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from math import fsum

from .pronosticos import validar_origen_horizonte
from .recetas import decimal_no_negativo

NOMBRES_VARIABLES = ("venta_origen", "rezago_1", "rezago_7", "promedio_7", "dia_semana_objetivo", "mes_objetivo")


@dataclass(frozen=True)
class Ejemplo:
    origen: date
    fecha_objetivo: date
    x: tuple[float, ...]
    y: float


def entradas_completas(serie: Mapping, origen: date) -> bool:
    return all(serie.get(origen - timedelta(days=k)) is not None for k in range(8))


def caracteristicas(serie: Mapping, origen: date, horizonte: int) -> tuple[float, ...]:
    validar_origen_horizonte(origen, horizonte)
    if not entradas_completas(serie, origen):
        raise ValueError("Las entradas temporales están incompletas")
    valores = [float(decimal_no_negativo(serie[origen - timedelta(days=k)], "venta histórica"))
               for k in range(8)]
    objetivo = origen + timedelta(days=horizonte)
    return (valores[0], valores[1], valores[7], fsum(valores[:7]) / 7,
            float(objetivo.weekday()), float(objetivo.month))


def ejemplos_entrenamiento(serie: Mapping, origen: date, horizonte: int) -> tuple[Ejemplo, ...]:
    validar_origen_horizonte(origen, horizonte)
    ejemplos = []
    for u in sorted(serie):
        if u > origen:
            break
        objetivo = u + timedelta(days=horizonte)
        if objetivo > origen or serie.get(objetivo) is None or not entradas_completas(serie, u):
            continue
        y = float(decimal_no_negativo(serie[objetivo], "respuesta de entrenamiento"))
        ejemplos.append(Ejemplo(u, objetivo, caracteristicas(serie, u, horizonte), y))
    return tuple(ejemplos)
