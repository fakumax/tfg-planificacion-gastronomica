"""Lectura de planes manuales y escenarios sintéticos de demostración."""

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from ..dominio.balance import CantidadPlanificada, EntradaPrevista, Escenario, Existencia
from ..dominio.calendario import fecha_iso
from ..dominio.recetas import decimal_no_negativo, texto


def _objeto(ruta: Path) -> dict:
    datos = json.loads(ruta.read_text(encoding="utf-8-sig"), parse_float=Decimal)
    if not isinstance(datos, dict):
        raise ValueError("El archivo debe contener un objeto JSON")
    return datos


def _filas(datos, campo):
    filas = datos.get(campo)
    if not isinstance(filas, list) or any(not isinstance(f, dict) for f in filas):
        raise ValueError(f"{campo}: se requiere una lista de registros")
    return filas


def leer_plan(ruta: Path) -> tuple[tuple[CantidadPlanificada, ...], tuple[date, ...]]:
    datos = _objeto(ruta)
    if datos.get("tipo") != "modelado":
        raise ValueError("El plan manual debe identificarse como modelado")
    inicio = fecha_iso(datos.get("desde"))
    if inicio > date.max - timedelta(days=6):
        raise ValueError("El horizonte supera el calendario admitido")
    fechas = tuple(inicio + timedelta(days=n) for n in range(7))
    plan = tuple(CantidadPlanificada(texto(p.get("producto_id"), "producto"),
                                     fecha_iso(p.get("fecha")),
                                     decimal_no_negativo(p.get("cantidad"), "cantidad planificada"))
                 for p in _filas(datos, "cantidades"))
    return plan, fechas


def leer_escenario(ruta: Path) -> Escenario:
    datos = _objeto(ruta)
    if datos.get("tipo") != "sintetico":
        raise ValueError("El escenario debe identificarse como sintético")
    existencias = tuple(Existencia(texto(e.get("insumo_id"), "insumo"),
                                  decimal_no_negativo(e.get("cantidad"), "existencia"),
                                  texto(e.get("unidad"), "unidad")) for e in _filas(datos, "existencias"))
    entradas = tuple(EntradaPrevista(texto(e.get("insumo_id"), "insumo"), fecha_iso(e.get("fecha")),
                                    decimal_no_negativo(e.get("cantidad"), "entrada"),
                                    texto(e.get("unidad"), "unidad")) for e in _filas(datos, "entradas"))
    return Escenario(texto(datos.get("nombre"), "nombre del escenario"),
                      texto(datos.get("version"), "versión del escenario"), existencias, entradas)
