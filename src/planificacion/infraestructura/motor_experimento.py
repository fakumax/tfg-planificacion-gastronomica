"""Trabajos independientes por producto; cada bosque usa un solo trabajo."""

from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context

from ..aplicacion.comparacion import evaluar_producto
from ..aplicacion.seleccion import seleccionar_producto
from .random_forest import RandomForest


def resolver_producto(tarea: dict) -> dict:
    if tarea["accion"] == "seleccion":
        return seleccionar_producto(tarea["producto_id"], tarea["serie"], RandomForest, tarea["protocolo"])
    if tarea["accion"] == "prueba":
        return evaluar_producto(tarea["producto_id"], tarea["serie"], tarea["parametros"],
                                tarea["estado"], RandomForest, tarea["protocolo"])
    raise ValueError("Acción experimental desconocida")


def ejecutar_tareas(tareas: list[dict], trabajadores: int = 1, progreso=None) -> list[dict]:
    if type(trabajadores) is not int or not 1 <= trabajadores <= 4:
        raise ValueError("Elegir entre uno y cuatro trabajadores")
    resultados = []

    def conservar(resultado):
        resultados.append(resultado)
        if progreso:
            progreso(resultado["producto_id"], len(resultados), len(tareas))

    if trabajadores == 1:
        for tarea in tareas:
            conservar(resolver_producto(tarea))
    else:
        with ProcessPoolExecutor(max_workers=trabajadores, mp_context=get_context("spawn")) as grupo:
            futuros = [grupo.submit(resolver_producto, tarea) for tarea in tareas]
            try:
                for futuro in as_completed(futuros):
                    conservar(futuro.result())
            except BaseException:
                for futuro in futuros:
                    futuro.cancel()
                raise
    return sorted(resultados, key=lambda r: r["producto_id"])
