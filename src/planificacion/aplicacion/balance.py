"""Ejecución de un balance y registro por un contrato sustituible."""

import hashlib
from dataclasses import replace
from datetime import date
from typing import Protocol

from .. import __version__
from ..dominio.balance import CantidadPlanificada, Escenario, calcular_balance
from ..dominio.recetas import Recetario, recetarios_compatibles
from ..dominio.serializacion import canonico, normalizar


class RegistroEjecuciones(Protocol):
    def guardar(self, contenido: dict) -> str: ...
    def recuperar(self, identidad: str) -> dict: ...


def ejecutar_balance(repo: RegistroEjecuciones, recetario: Recetario,
                      plan: tuple[CantidadPlanificada, ...], escenario: Escenario,
                      fechas: tuple[date, ...], contexto: dict | None = None,
                      tipo: str = "balance", ejecucion_previa_id: str | None = None) -> dict:
    if tipo not in ("balance", "planificacion"):
        raise ValueError("Tipo de ejecución de balance no admitido")
    contexto = dict(contexto) if contexto is not None else {"metodo": "plan_manual", "naturaleza_plan": "modelado"}
    if 'revision' in contexto:
        raise ValueError('El vínculo de revisión se obtiene de una ejecución conservada')
    if ejecucion_previa_id is not None:
        previa = repo.recuperar(ejecucion_previa_id)
        if (previa['tipo'] not in ('balance', 'planificacion')
                or not recetarios_compatibles(previa['entradas']['recetario'], normalizar(recetario))
                or previa['entradas']['fechas'] != normalizar(fechas)
                or previa.get('contexto', {}).get('importacion_id') != contexto.get('importacion_id')):
            raise ValueError('El antecedente debe conservar importación, recetario y fechas del escenario')
        contexto['revision'] = {'ejecucion_previa_id': ejecucion_previa_id,
                               'escenario_previo_id': previa['resultado']['escenario_id']}
    resultado = calcular_balance(recetario, plan, escenario, fechas)
    if ejecucion_previa_id is not None:
        identidad_revision = hashlib.sha256(canonico({
            'escenario': resultado.escenario_id, 'ejecucion_previa': ejecucion_previa_id,
        }).encode('utf-8')).hexdigest()
        resultado = replace(resultado, escenario_id=identidad_revision)
    contenido = normalizar({
        "tipo": tipo, "version_codigo": __version__,
        "contexto": contexto,
        "entradas": {"recetario": recetario, "plan": plan, "escenario": escenario, "fechas": fechas},
        "resultado": resultado,
    })
    identidad = repo.guardar(contenido)
    return repo.recuperar(identidad)
