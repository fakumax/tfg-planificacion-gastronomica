"""Admisión de casos y métricas por producto, horizonte y método."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from math import floor, fsum, isfinite, sqrt

from .pronosticos import validar_origen_horizonte
from .temporal import entradas_completas, ejemplos_entrenamiento


@dataclass(frozen=True)
class CasoEvaluacion:
    origen: date
    fecha_objetivo: date
    horizonte: int
    ejemplos_entrenamiento: int
    motivos: tuple[str, ...]
    escala: float | None
    pares_escala: int

    @property
    def evaluable(self) -> bool:
        return not self.motivos


@dataclass(frozen=True)
class PrediccionEvaluada:
    producto_id: str
    metodo: str
    origen: date
    fecha_objetivo: date
    horizonte: int
    real: float
    estimado: float
    escala: float | None
    pares_escala: int


def escala_mase(serie: Mapping, origen: date) -> tuple[float | None, int]:
    diferencias = [abs(float(serie[f]) - float(serie[f - timedelta(days=7)]))
                   for f in sorted(serie) if f <= origen and serie[f] is not None
                   and serie.get(f - timedelta(days=7)) is not None]
    if not diferencias:
        return None, 0
    escala = fsum(diferencias) / len(diferencias)
    return (escala if escala > 0 else None), len(diferencias)


def evaluar_caso(serie: Mapping, origen: date, horizonte: int) -> CasoEvaluacion:
    validar_origen_horizonte(origen, horizonte)
    motivos = []
    if not entradas_completas(serie, origen):
        motivos.append("entradas_incompletas")
    objetivo = origen + timedelta(days=horizonte)
    if serie.get(objetivo) is None:
        motivos.append("respuesta_ausente")
    if serie.get(objetivo - timedelta(days=7)) is None:
        motivos.append("referencia_semanal_ausente")
    ejemplos = len(ejemplos_entrenamiento(serie, origen, horizonte))
    if ejemplos < 60:
        motivos.append("menos_de_60_ejemplos")
    escala, pares = escala_mase(serie, origen)
    return CasoEvaluacion(origen, objetivo, horizonte, ejemplos, tuple(motivos), escala, pares)


def _cuantil(ordenados: list[float], proporcion: float) -> float:
    posicion = (len(ordenados) - 1) * proporcion
    inferior = floor(posicion)
    superior = min(inferior + 1, len(ordenados) - 1)
    return ordenados[inferior] + (ordenados[superior] - ordenados[inferior]) * (posicion - inferior)


def metricas(registros: list[PrediccionEvaluada] | tuple[PrediccionEvaluada, ...]) -> dict:
    claves = {(p.producto_id, p.horizonte, p.metodo) for p in registros}
    if len(claves) > 1:
        raise ValueError("Las métricas requieren un solo producto, horizonte y método")
    origenes = {p.origen for p in registros}
    if len(origenes) != len(registros):
        raise ValueError("Hay orígenes duplicados en el grupo de evaluación")
    n = len(registros)
    resumen = {"n_predicciones": n, "n_origenes": len(origenes),
               "n_fechas_objetivo": len({p.fecha_objetivo for p in registros}),
               "n_mase_calculable": 0, "mae": None, "rmse": None, "mase": None,
               "mediana_error_absoluto": None, "cuartil_1_error_absoluto": None,
               "cuartil_3_error_absoluto": None, "maximo_error_absoluto": None,
               "n_pares_escala_min": min((p.pares_escala for p in registros), default=0),
               "n_pares_escala_max": max((p.pares_escala for p in registros), default=0),
               "exploratoria": len(origenes) < 14}
    if not registros:
        return resumen
    if any(not isfinite(p.real) or not isfinite(p.estimado) for p in registros):
        raise ValueError("Una predicción o respuesta no es finita")
    errores = [abs(p.real - p.estimado) for p in registros]
    escalados = [abs(p.real - p.estimado) / p.escala for p in registros
                 if p.escala is not None and isfinite(p.escala) and p.escala > 0]
    ordenados = sorted(errores)
    resumen.update(mae=fsum(errores) / n, rmse=sqrt(fsum(e * e for e in errores) / n),
                   mase=fsum(escalados) / len(escalados) if escalados else None,
                   n_mase_calculable=len(escalados), mediana_error_absoluto=_cuantil(ordenados, 0.5),
                   cuartil_1_error_absoluto=_cuantil(ordenados, 0.25),
                   cuartil_3_error_absoluto=_cuantil(ordenados, 0.75),
                   maximo_error_absoluto=max(errores))
    return resumen


def seleccionar_no_solapados(registros: list[PrediccionEvaluada]) -> list[PrediccionEvaluada]:
    if len({(p.producto_id, p.horizonte, p.metodo) for p in registros}) > 1:
        raise ValueError("Seleccionar bloques por producto, horizonte y método")
    elegidos = []
    for p in sorted(registros, key=lambda r: r.origen):
        if not elegidos or (p.origen - elegidos[-1].origen).days >= 7:
            elegidos.append(p)
    return elegidos
