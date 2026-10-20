"""Consumo, saldos y alertas de un escenario explícitamente sintético."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal

from .recetas import Recetario, calcular_consumos, decimal_no_negativo, texto


@dataclass(frozen=True)
class CantidadPlanificada:
    producto_id: str
    fecha: date
    cantidad: Decimal


@dataclass(frozen=True)
class Existencia:
    insumo_id: str
    cantidad: Decimal
    unidad: str


@dataclass(frozen=True)
class EntradaPrevista:
    insumo_id: str
    fecha: date
    cantidad: Decimal
    unidad: str


@dataclass(frozen=True)
class Escenario:
    nombre: str
    version: str
    existencias: tuple[Existencia, ...]
    entradas: tuple[EntradaPrevista, ...]
    tipo: str = "sintetico"

    @property
    def identificador(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True, ensure_ascii=False,
            default=lambda v: str(v)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ConsumoDiario:
    insumo_id: str
    fecha: date
    cantidad: Decimal
    unidad: str


@dataclass(frozen=True)
class SaldoDiario:
    insumo_id: str
    fecha: date
    existencia_antes: Decimal
    entradas: Decimal
    consumo: Decimal
    saldo: Decimal
    unidad: str


@dataclass(frozen=True)
class Alerta:
    insumo_id: str
    primera_fecha: date
    deficit_inicial: Decimal
    maximo_deficit: Decimal
    unidad: str


@dataclass(frozen=True)
class ResultadoBalance:
    recetario_sha256: str
    escenario_id: str
    consumos: tuple[ConsumoDiario, ...]
    saldos: tuple[SaldoDiario, ...]
    alertas: tuple[Alerta, ...]


def calcular_balance(recetario: Recetario, plan: tuple[CantidadPlanificada, ...],
                      escenario: Escenario, fechas: tuple[date, ...]) -> ResultadoBalance:
    if (len(fechas) != 7 or any(type(f) is not date for f in fechas)
            or any(f != fechas[0] + timedelta(days=n) for n, f in enumerate(fechas))):
        raise ValueError("El horizonte debe contener siete fechas consecutivas")
    texto(escenario.nombre, "nombre del escenario")
    texto(escenario.version, "versión del escenario")
    if escenario.tipo != "sintetico":
        raise ValueError("Se requiere un escenario identificado como sintético")
    productos = {r.producto_id for r in recetario.recetas}
    esperadas = {(pid, fecha) for pid in productos for fecha in fechas}
    cantidades = {}
    for p in plan:
        clave = (p.producto_id, p.fecha)
        if clave in cantidades:
            raise ValueError("Cantidad de producto y fecha duplicada")
        cantidades[clave] = decimal_no_negativo(p.cantidad, "cantidad planificada")
    if set(cantidades) != esperadas:
        raise ValueError("Cobertura incompleta o productos y fechas fuera del recetario y horizonte")

    controlados = {i.insumo_id: i for i in recetario.insumos if i.control_stock}
    stock = {}
    for e in escenario.existencias:
        if e.insumo_id not in controlados or e.insumo_id in stock:
            raise ValueError("Existencia de insumo desconocido, sin control o duplicado")
        if e.unidad != controlados[e.insumo_id].unidad:
            raise ValueError("Unidades de existencia incompatibles")
        stock[e.insumo_id] = decimal_no_negativo(e.cantidad, "existencia inicial")
    if set(stock) != set(controlados):
        raise ValueError("Faltan existencias iniciales explícitas de insumos controlados")
    entradas = {}
    for e in escenario.entradas:
        if (e.insumo_id not in controlados or e.fecha not in fechas
                or e.unidad != controlados[e.insumo_id].unidad):
            raise ValueError("Entrada con insumo, unidad o fecha fuera del escenario")
        q = decimal_no_negativo(e.cantidad, "entrada prevista")
        if q == 0:
            raise ValueError("La entrada prevista debe ser positiva")
        clave = (e.insumo_id, e.fecha)
        entradas[clave] = entradas.get(clave, Decimal(0)) + q

    consumos, saldos, alertas = [], [], {}
    for fecha in fechas:
        consumo = calcular_consumos(recetario, {pid: cantidades[pid, fecha] for pid in sorted(productos)})
        for i in recetario.insumos:
            consumos.append(ConsumoDiario(i.insumo_id, fecha, consumo[i.insumo_id], i.unidad))
            if not i.control_stock:
                continue
            antes = stock[i.insumo_id]
            entrada = entradas.get((i.insumo_id, fecha), Decimal(0))
            saldo = antes + entrada - consumo[i.insumo_id]
            stock[i.insumo_id] = saldo
            saldos.append(SaldoDiario(i.insumo_id, fecha, antes, entrada,
                                      consumo[i.insumo_id], saldo, i.unidad))
            if saldo < 0:
                previa = alertas.get(i.insumo_id)
                alertas[i.insumo_id] = Alerta(
                    i.insumo_id, previa.primera_fecha if previa else fecha,
                    previa.deficit_inicial if previa else -saldo,
                    max(previa.maximo_deficit, -saldo) if previa else -saldo, i.unidad)
    return ResultadoBalance(recetario.sha256, escenario.identificador, tuple(consumos),
                             tuple(saldos), tuple(alertas[k] for k in sorted(alertas)))
