"""Comparación final con configuración recibida y los mismos casos por método."""

from collections.abc import Callable, Mapping
from dataclasses import asdict
from math import fsum

from .seleccion import casos_periodo
from ..dominio.calendario import fecha_iso
from ..dominio.evaluacion import PrediccionEvaluada, metricas, seleccionar_no_solapados
from ..dominio.parametros import validar_configuracion
from ..dominio.pronosticos import Persistencia, ReferenciaSemanal
from ..dominio.protocolo import validar_protocolo

METODOS = ("persistencia", "semanal", "random_forest")


def _promedios_horizontes(registros: list[PrediccionEvaluada]) -> dict:
    promedios = {}
    for metodo in METODOS:
        errores = [metricas([p for p in registros if p.metodo == metodo and p.horizonte == h])["mae"]
                   for h in range(1, 8)]
        promedios[metodo] = fsum(errores) / 7 if all(e is not None for e in errores) else None
    return promedios


def _diferencias(promedios: dict) -> dict:
    rf = promedios["random_forest"]
    return {"mae_promedio_horizontes": promedios,
            "diferencia_rf_persistencia": rf - promedios["persistencia"] if rf is not None else None,
            "diferencia_rf_semanal": rf - promedios["semanal"] if rf is not None else None}


def sensibilidad_bloques(registros: list[PrediccionEvaluada]) -> dict:
    claves = {(p.origen, p.horizonte, p.metodo) for p in registros}
    completas = [o for o in sorted({p.origen for p in registros})
                 if all((o, h, m) in claves for h in range(1, 8) for m in METODOS)]
    origenes = []
    for o in completas:
        if not origenes or (o - origenes[-1]).days >= 7:
            origenes.append(o)
    seleccion = [p for p in registros if p.origen in origenes]
    por_bloque = [{"origen": o, **_diferencias(_promedios_horizontes(
        [p for p in seleccion if p.origen == o]))} for o in origenes]
    retiro = [{"origen_retirado": o, "n_bloques_restantes": len(origenes) - 1,
               **_diferencias(_promedios_horizontes([p for p in seleccion if p.origen != o]))}
              for o in origenes]
    return {"n_bloques_completos": len(origenes), "por_bloque": por_bloque,
            "retiro_de_bloque": retiro, "conjunto_completo": _diferencias(_promedios_horizontes(seleccion)),
            "criterio": "Orígenes comunes H1–H7, cronológicos, separados al menos siete días",
            "limite": "Descripción de sensibilidad; los bloques no acreditan independencia ni superioridad general"}


def evaluar_producto(producto_id: str, serie: Mapping, parametros: dict, estado: str,
                       fabrica: Callable, protocolo: dict) -> dict:
    validar_protocolo(protocolo)
    configuracion = validar_configuracion(parametros)
    limites = protocolo["particion"]["origenes_prueba"]
    casos = casos_periodo(serie, fecha_iso(limites[0]), fecha_iso(limites[1]))
    metodos = (Persistencia(), ReferenciaSemanal(), fabrica({producto_id: configuracion}, {producto_id: estado}))
    predicciones = []
    for c in casos:
        if not c.evaluable:
            continue
        pasado = {f: q for f, q in serie.items() if f <= c.origen}
        for metodo in metodos:
            estimacion = metodo.estimar(producto_id, pasado, c.origen, c.horizonte)
            predicciones.append(PrediccionEvaluada(
                producto_id, metodo.nombre, c.origen, c.fecha_objetivo, c.horizonte,
                float(serie[c.fecha_objetivo]), float(estimacion.cantidad), c.escala, c.pares_escala))
    resumenes, sensibilidad = [], []
    for h in range(1, 8):
        for metodo in METODOS:
            grupo = [p for p in predicciones if p.horizonte == h and p.metodo == metodo]
            resumenes.append({"producto_id": producto_id, "horizonte": h, "metodo": metodo,
                              "muestra": "completa", **metricas(grupo)})
            elegidos = seleccionar_no_solapados(grupo)
            sensibilidad.append({"producto_id": producto_id, "horizonte": h, "metodo": metodo,
                                 "muestra": "no_solapada", **metricas(elegidos),
                                 "origenes": [p.origen for p in elegidos]})
    return {"producto_id": producto_id, "parametros": configuracion, "estado_configuracion": estado,
            "predicciones": predicciones, "metricas": resumenes, "sensibilidad": sensibilidad,
            "casos": [{**asdict(c), "evaluable": c.evaluable} for c in casos],
            "bloques_p07": sensibilidad_bloques(predicciones) if producto_id == "P07" else None}
