"""Recorrido completo desde ventas conocidas hasta saldo y alerta conservados."""

from datetime import date, timedelta
from typing import Protocol

from .balance import RegistroEjecuciones, ejecutar_balance
from .ventas import LecturaVentas, consultar_ventas
from ..dominio.balance import CantidadPlanificada, Escenario
from ..dominio.pronosticos import Pronosticador
from ..dominio.recetas import Recetario
from ..dominio.ventas import Producto


class LecturaPlanificacion(LecturaVentas, Protocol):
    def listar_productos(self, importacion_id: str) -> tuple[Producto, ...]: ...


def planificar(ventas: LecturaPlanificacion, ejecuciones: RegistroEjecuciones,
                metodo: Pronosticador, recetario: Recetario, importacion_id: str,
                origen: date, escenario: Escenario, referencia_seleccion: dict | None = None,
                ejecucion_previa_id: str | None = None, metadatos: dict | None = None) -> dict:
    if type(origen) is not date or origen > date.max - timedelta(days=7):
        raise ValueError("Origen fuera del calendario admitido")
    productos = tuple(sorted(ventas.listar_productos(importacion_id), key=lambda p: p.producto_id))
    if {p.producto_id for p in productos} != {r.producto_id for r in recetario.recetas}:
        raise ValueError("El catálogo de ventas y el recetario no cubren los mismos productos")
    fechas = tuple(origen + timedelta(days=h) for h in range(1, 8))
    plan, historico, pronosticos = [], [], []
    for p in productos:
        consulta = consultar_ventas(ventas, importacion_id, p.producto_id,
                                     date(p.anio, 1, 1), origen)
        serie = {d.fecha: d.cantidad for d in consulta.diarias}
        historico.append({"producto": p, "datos_disponibles": consulta.diarias, "fuentes": consulta.fuentes})
        for h, fecha in enumerate(fechas, 1):
            estimacion = metodo.estimar(p.producto_id, serie, origen, h)
            plan.append(CantidadPlanificada(p.producto_id, fecha, estimacion.cantidad))
            pronosticos.append({"producto_id": p.producto_id, "origen": origen, "fecha": fecha,
                                "horizonte": h, "metodo": metodo.nombre, "cantidad": estimacion.cantidad,
                                "parametros": estimacion.parametros,
                                "ejemplos_entrenamiento": estimacion.ejemplos_entrenamiento})
    contexto = {**(metadatos or {}), "metodo": metodo.nombre, "naturaleza_plan": "estimado", "importacion_id": importacion_id,
                "origen": origen, "historico": historico, "pronosticos": pronosticos}
    if referencia_seleccion is not None:
        contexto["seleccion_modelos"] = referencia_seleccion
    return ejecutar_balance(ejecuciones, recetario, tuple(plan), escenario, fechas,
                            contexto=contexto, tipo="planificacion", ejecucion_previa_id=ejecucion_previa_id)
