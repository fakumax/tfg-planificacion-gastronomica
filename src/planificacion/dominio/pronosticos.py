"""Contrato de pronóstico y referencia inicial de persistencia."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Protocol

from .recetas import decimal_no_negativo


@dataclass(frozen=True)
class Estimacion:
    cantidad: Decimal
    parametros: dict = field(default_factory=dict)
    ejemplos_entrenamiento: int | None = None


class Pronosticador(Protocol):
    nombre: str
    def estimar(self, producto_id: str, serie: Mapping[date, int | None],
                origen: date, horizonte: int) -> Estimacion: ...


def validar_origen_horizonte(origen: date, horizonte: int) -> None:
    if type(origen) is not date or type(horizonte) is not int or not 1 <= horizonte <= 7:
        raise ValueError("Se requiere un origen válido y un horizonte entero de 1 a 7")


class Persistencia:
    nombre = "persistencia"

    def estimar(self, producto_id: str, serie: Mapping[date, int | None],
                origen: date, horizonte: int) -> Estimacion:
        validar_origen_horizonte(origen, horizonte)
        if serie.get(origen) is None:
            raise ValueError(f"{producto_id}: no hay observación en el origen {origen.isoformat()}")
        return Estimacion(decimal_no_negativo(serie[origen], "observación del origen"))


class ReferenciaSemanal:
    nombre = "semanal"

    def estimar(self, producto_id: str, serie: Mapping[date, int | None],
                origen: date, horizonte: int) -> Estimacion:
        validar_origen_horizonte(origen, horizonte)
        referencia = origen + timedelta(days=horizonte - 7)
        if serie.get(referencia) is None:
            raise ValueError(f"{producto_id}: falta la referencia semanal del {referencia.isoformat()}")
        return Estimacion(decimal_no_negativo(serie[referencia], "referencia semanal"))
