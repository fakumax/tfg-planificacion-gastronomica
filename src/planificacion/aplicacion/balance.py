"""Ejecución de un balance y registro por un contrato sustituible."""

from datetime import date
from typing import Protocol

from .. import __version__
from ..dominio.balance import CantidadPlanificada, Escenario, calcular_balance
from ..dominio.recetas import Recetario
from ..dominio.serializacion import normalizar


class RegistroEjecuciones(Protocol):
    def guardar(self, contenido: dict) -> str: ...
    def recuperar(self, identidad: str) -> dict: ...


def ejecutar_balance(repo: RegistroEjecuciones, recetario: Recetario,
                      plan: tuple[CantidadPlanificada, ...], escenario: Escenario,
                      fechas: tuple[date, ...], contexto: dict | None = None,
                      tipo: str = "balance") -> dict:
    if tipo not in ("balance", "planificacion"):
        raise ValueError("Tipo de ejecución de balance no admitido")
    resultado = calcular_balance(recetario, plan, escenario, fechas)
    contenido = normalizar({
        "tipo": tipo, "version_codigo": __version__,
        "contexto": contexto if contexto is not None else {"metodo": "plan_manual", "naturaleza_plan": "modelado"},
        "entradas": {"recetario": recetario, "plan": plan, "escenario": escenario, "fechas": fechas},
        "resultado": resultado,
    })
    identidad = repo.guardar(contenido)
    return repo.recuperar(identidad)
