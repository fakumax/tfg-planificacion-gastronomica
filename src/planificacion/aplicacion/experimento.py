"""Orquestación con selección conservada antes de evaluar la prueba reservada."""

from collections.abc import Callable
from time import perf_counter
from typing import Protocol

from .balance import RegistroEjecuciones
from .. import __version__
from ..dominio.parametros import validar_configuracion
from ..dominio.protocolo import validar_protocolo
from ..dominio.serializacion import normalizar
from ..dominio.ventas import LoteVentas


class FuenteExperimento(Protocol):
    def recuperar_lote(self, importacion_id: str) -> LoteVentas: ...


def _preparar(ventas: FuenteExperimento, importacion_id: str, protocolo: dict) -> LoteVentas:
    huella = validar_protocolo(protocolo)
    lote = ventas.recuperar_lote(importacion_id)
    if lote.protocolo_sha256 != huella or lote.version_preparacion != protocolo["preparacion"]["version"]:
        raise ValueError("La importación no corresponde al protocolo y preparación cerrados")
    seleccion = protocolo["seleccion"]
    esperados = {(p["producto_id"], p["producto_original"], seleccion["local_original"], seleccion["anio"])
                 for p in seleccion["productos"]}
    obtenidos = {(p.producto_id, p.producto_original, p.local_original, p.anio) for p in lote.productos}
    if obtenidos != esperados:
        raise ValueError("La importación no contiene el catálogo exacto del protocolo")
    return lote


def _validar_resultados(resultados: list[dict], lote: LoteVentas) -> list[dict]:
    if (len(resultados) != len(lote.productos)
            or {r["producto_id"] for r in resultados} != {p.producto_id for p in lote.productos}):
        raise ValueError("Resultado incompleto o duplicado; no se guarda un experimento parcial")
    return sorted(resultados, key=lambda r: r["producto_id"])


def _contexto(lote: LoteVentas, ejecutor: Callable, trabajadores: int, metadatos: dict) -> dict:
    if type(trabajadores) is not int or not 1 <= trabajadores <= 4:
        raise ValueError("Elegir entre uno y cuatro trabajadores")
    return {"importacion_id": lote.identificador, "protocolo_sha256": lote.protocolo_sha256,
            "trabajadores": trabajadores, "ejecutor": f"{ejecutor.__module__}.{ejecutor.__qualname__}",
            **metadatos}


def _tareas(lote: LoteVentas, protocolo: dict, accion: str) -> list[dict]:
    return [{"accion": accion, "producto_id": p.producto_id, "protocolo": protocolo,
             "serie": {d.fecha: d.cantidad for d in lote.diarias if d.producto_id == p.producto_id}}
            for p in lote.productos]


def ejecutar_seleccion(ventas: FuenteExperimento, registro: RegistroEjecuciones,
                        importacion_id: str, protocolo: dict, ejecutor: Callable,
                        trabajadores: int = 1, progreso=None, metadatos: dict | None = None) -> dict:
    lote = _preparar(ventas, importacion_id, protocolo)
    contexto = _contexto(lote, ejecutor, trabajadores, metadatos or {})
    inicio = perf_counter()
    resultados = _validar_resultados(ejecutor(_tareas(lote, protocolo, "seleccion"),
                                              trabajadores=trabajadores, progreso=progreso), lote)
    for r in resultados:
        validar_configuracion(r["parametros"])
        if r["estado"] not in ("seleccionada_por_validacion", "prefijada_validacion_insuficiente"):
            raise ValueError("Estado de selección no reconocido")
    contenido = {"tipo": "seleccion_modelos", "version_codigo": __version__, "contexto": contexto,
                 "entradas": {"lote": lote, "protocolo": protocolo}, "resultado": {"productos": resultados},
                 "rendimiento": {"segundos_totales": perf_counter() - inicio}}
    identidad = registro.guardar(contenido)
    return registro.recuperar(identidad)


def ejecutar_prueba(ventas: FuenteExperimento, registro: RegistroEjecuciones, importacion_id: str,
                     seleccion_id: str, protocolo: dict, ejecutor: Callable,
                     trabajadores: int = 1, progreso=None, metadatos: dict | None = None) -> dict:
    lote = _preparar(ventas, importacion_id, protocolo)
    seleccion = registro.recuperar(seleccion_id)
    if seleccion["tipo"] != "seleccion_modelos":
        raise ValueError("Se requiere una selección cerrada previamente")
    if (seleccion["contexto"]["importacion_id"] != importacion_id
            or seleccion["entradas"]["lote"] != normalizar(lote)):
        raise ValueError("La selección pertenece a otra importación o conjunto de datos")
    if seleccion["entradas"]["protocolo"] != protocolo:
        raise ValueError("La selección utiliza otro protocolo")
    contexto = _contexto(lote, ejecutor, trabajadores, metadatos or {})
    anterior = seleccion["contexto"]
    if contexto.get("entorno") != anterior.get("entorno"):
        raise ValueError("El entorno cambió respecto de la selección; registrar una nueva selección")
    if contexto.get("codigo", {}).get("huella_nucleo_numerico") != anterior.get("codigo", {}).get("huella_nucleo_numerico"):
        raise ValueError("El núcleo numérico cambió respecto de la selección")
    configuraciones = {r["producto_id"]: r for r in seleccion["resultado"]["productos"]}
    if set(configuraciones) != {p.producto_id for p in lote.productos}:
        raise ValueError("La selección está incompleta")
    tareas = _tareas(lote, protocolo, "prueba")
    for tarea in tareas:
        elegida = configuraciones[tarea["producto_id"]]
        tarea.update(parametros=validar_configuracion(elegida["parametros"]), estado=elegida["estado"])
    inicio = perf_counter()
    resultados = _validar_resultados(ejecutor(tareas, trabajadores=trabajadores, progreso=progreso), lote)
    for r in resultados:
        if r["parametros"] != configuraciones[r["producto_id"]]["parametros"]:
            raise ValueError("La prueba cambió la configuración seleccionada")
    contenido = {"tipo": "evaluacion_predictiva", "version_codigo": __version__, "contexto": contexto,
                 "entradas": {"lote": lote, "protocolo": protocolo, "seleccion_id": seleccion_id,
                              "huella_seleccion": seleccion["huella_contenido"]},
                 "resultado": {"productos": resultados},
                 "rendimiento": {"segundos_totales": perf_counter() - inicio}}
    identidad = registro.guardar(contenido)
    return registro.recuperar(identidad)
