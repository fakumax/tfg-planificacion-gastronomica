"""Selección de configuración con validación y casos comunes por horizonte."""

from collections.abc import Callable, Mapping
from dataclasses import asdict
from datetime import date, timedelta
from math import fsum

from ..dominio.calendario import fecha_iso
from ..dominio.evaluacion import PrediccionEvaluada, evaluar_caso, metricas
from ..dominio.parametros import CONFIGURACION_PREFIJADA, grilla_configuraciones
from ..dominio.protocolo import validar_protocolo


def casos_periodo(serie: Mapping, inicio: date, fin: date) -> tuple:
    return tuple(evaluar_caso(serie, inicio + timedelta(days=n), h)
                 for h in range(1, 8) for n in range((fin - inicio).days + 1))


def elegir_configuracion(cobertura: dict[int, int], candidatas: list[dict]) -> tuple[dict, str]:
    if any(cobertura.get(h, 0) < 14 for h in range(1, 8)):
        return dict(CONFIGURACION_PREFIJADA), "prefijada_validacion_insuficiente"
    if not candidatas or any(c["mae_promedio_horizontes"] is None for c in candidatas):
        raise ValueError("Hay cobertura de validación, pero faltan métricas de candidatas")
    mejor_error = min(c["mae_promedio_horizontes"] for c in candidatas)
    empatadas = [c for c in candidatas if c["mae_promedio_horizontes"] - mejor_error <= 0.000001]
    elegida = min(empatadas, key=lambda c: (c["parametros"]["max_depth"], c["parametros"]["n_estimators"]))
    return dict(elegida["parametros"]), "seleccionada_por_validacion"


def seleccionar_producto(producto_id: str, serie: Mapping, fabrica: Callable,
                          protocolo: dict) -> dict:
    validar_protocolo(protocolo)
    limites = protocolo["particion"]["origenes_validacion"]
    casos = casos_periodo(serie, fecha_iso(limites[0]), fecha_iso(limites[1]))
    cobertura = {h: sum(c.evaluable and c.horizonte == h for c in casos) for h in range(1, 8)}
    grilla = grilla_configuraciones() if all(n >= 14 for n in cobertura.values()) else (dict(CONFIGURACION_PREFIJADA),)
    candidatas = []
    for configuracion in grilla:
        modelo = fabrica({producto_id: configuracion}, {producto_id: "candidata_validacion"})
        predicciones = []
        for c in casos:
            if not c.evaluable:
                continue
            pasado = {f: q for f, q in serie.items() if f <= c.origen}
            estimacion = modelo.estimar(producto_id, pasado, c.origen, c.horizonte)
            predicciones.append(PrediccionEvaluada(
                producto_id, "random_forest", c.origen, c.fecha_objetivo, c.horizonte,
                float(serie[c.fecha_objetivo]), float(estimacion.cantidad), c.escala, c.pares_escala))
        por_horizonte = [{**metricas([p for p in predicciones if p.horizonte == h]), "horizonte": h}
                         for h in range(1, 8)]
        valores = [m["mae"] for m in por_horizonte]
        promedio = fsum(valores) / 7 if all(v is not None for v in valores) else None
        candidatas.append({"parametros": configuracion, "mae_promedio_horizontes": promedio,
                           "metricas": por_horizonte, "predicciones": predicciones})
    elegida, estado = elegir_configuracion(cobertura, candidatas)
    return {"producto_id": producto_id, "parametros": elegida, "estado": estado,
            "cobertura_validacion": cobertura, "candidatas": candidatas,
            "casos": [{**asdict(c), "evaluable": c.evaluable} for c in casos]}
