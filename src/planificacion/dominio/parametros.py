"""Configuraciones admitidas por la grilla cerrada del TP3."""

CONFIGURACION_PREFIJADA = {"n_estimators": 100, "max_depth": 5, "min_samples_leaf": 2, "random_state": 42}


def validar_configuracion(configuracion: dict | None) -> dict:
    claves = set(CONFIGURACION_PREFIJADA)
    if (not isinstance(configuracion, dict) or set(configuracion) != claves
            or any(type(configuracion[k]) is not int for k in claves)
            or configuracion["n_estimators"] not in (100, 300)
            or configuracion["max_depth"] not in (5, 10)
            or configuracion["min_samples_leaf"] != 2 or configuracion["random_state"] != 42):
        raise ValueError("La configuración está ausente o fuera del protocolo cerrado")
    return dict(configuracion)


def grilla_configuraciones() -> tuple[dict, ...]:
    return tuple({**CONFIGURACION_PREFIJADA, "max_depth": profundidad, "n_estimators": arboles}
                 for profundidad in (5, 10) for arboles in (100, 300))
