"""Adaptador de scikit-learn con configuración explícita y corte temporal."""

from collections.abc import Mapping
from datetime import date
from decimal import Decimal

from ..dominio.parametros import validar_configuracion
from ..dominio.pronosticos import Estimacion
from ..dominio.temporal import NOMBRES_VARIABLES, caracteristicas, ejemplos_entrenamiento


class RandomForest:
    nombre = "random_forest"

    def __init__(self, configuraciones: dict[str, dict], estados: dict[str, str] | None = None):
        self.configuraciones = {p: dict(c) for p, c in configuraciones.items()}
        self.estados = dict(estados or {})

    def estimar(self, producto_id: str, serie: Mapping[date, int | None],
                origen: date, horizonte: int) -> Estimacion:
        configuracion = validar_configuracion(self.configuraciones.get(producto_id))
        x = caracteristicas(serie, origen, horizonte)
        ejemplos = ejemplos_entrenamiento(serie, origen, horizonte)
        if len(ejemplos) < 60:
            raise ValueError(f"{producto_id}: menos de 60 ejemplos completos; modelo no ajustable")
        import numpy
        import sklearn
        from sklearn.ensemble import RandomForestRegressor

        modelo = RandomForestRegressor(**configuracion, n_jobs=1)
        modelo.fit([e.x for e in ejemplos], [e.y for e in ejemplos])
        cantidad = Decimal(str(float(modelo.predict([x])[0])))
        parametros = {**configuracion, "n_jobs": 1,
                      "seleccion": self.estados.get(producto_id, "configuracion_explicita"),
                      "variables": list(NOMBRES_VARIABLES), "version_sklearn": sklearn.__version__,
                      "version_numpy": numpy.__version__, "parametros_efectivos": modelo.get_params(),
                      "fecha_primera_respuesta": min(e.fecha_objetivo for e in ejemplos).isoformat(),
                      "fecha_ultima_respuesta": max(e.fecha_objetivo for e in ejemplos).isoformat()}
        return Estimacion(cantidad, parametros, len(ejemplos))
