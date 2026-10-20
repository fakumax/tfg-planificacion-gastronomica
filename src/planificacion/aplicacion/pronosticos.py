"""Consulta individual y disponibilidad de datos, separadas del balance completo."""

from datetime import date, timedelta

from .. import __version__
from ..dominio.pronosticos import Pronosticador
from ..dominio.serializacion import normalizar
from ..dominio.temporal import ejemplos_entrenamiento
from .balance import RegistroEjecuciones
from .ventas import LecturaVentas, consultar_ventas


def _historico(ventas, importacion_id, producto_id, origen):
    if type(origen) is not date or origen > date.max-timedelta(days=7):
        raise ValueError('Origen fuera del calendario admitido')
    producto = ventas.obtener_producto(importacion_id, producto_id)
    return consultar_ventas(ventas, importacion_id, producto_id, date(producto.anio,1,1), origen)


def consultar_disponibilidad(ventas: LecturaVentas, importacion_id: str,
                             producto_id: str, origen: date) -> list[dict]:
    consulta = _historico(ventas, importacion_id, producto_id, origen)
    serie = {d.fecha: d.cantidad for d in consulta.diarias}
    faltantes = [origen-timedelta(days=n) for n in range(8) if serie.get(origen-timedelta(days=n)) is None]
    filas = []
    for h in range(1,8):
        referencia = origen+timedelta(days=h-7)
        n = len(ejemplos_entrenamiento(serie, origen, h))
        causas = {
            'persistencia': '' if serie.get(origen) is not None else f'Falta observación del {origen}',
            'semanal': '' if serie.get(referencia) is not None else f'Falta referencia del {referencia}',
            'random_forest': '; '.join([
                *(['Entradas ausentes: '+', '.join(str(f) for f in faltantes)] if faltantes else []),
                *([f'{n} ejemplos completos; se requieren 60'] if n<60 else [])]),
        }
        for metodo, causa in causas.items():
            filas.append({'producto_id': producto_id, 'origen': origen, 'fecha': origen+timedelta(days=h),
                'horizonte': h, 'metodo': metodo, 'disponible': not causa, 'causa': causa or 'Datos disponibles',
                'ejemplos_entrenamiento': n if metodo=='random_forest' else None})
    return normalizar(filas)


def consultar_pronostico(ventas: LecturaVentas, registro: RegistroEjecuciones, metodo: Pronosticador,
                         importacion_id: str, producto_id: str, origen: date,
                         referencia_seleccion: dict | None = None, metadatos: dict | None = None) -> dict:
    consulta = _historico(ventas, importacion_id, producto_id, origen)
    serie = {d.fecha: d.cantidad for d in consulta.diarias}
    filas = []
    for h in range(1,8):
        fila = {'producto_id': producto_id, 'origen': origen, 'fecha': origen+timedelta(days=h),
                'horizonte': h, 'metodo': metodo.nombre}
        try:
            estimacion = metodo.estimar(producto_id, serie, origen, h)
            fila.update(disponible=True, cantidad=estimacion.cantidad, causa=None,
                        parametros=estimacion.parametros, ejemplos_entrenamiento=estimacion.ejemplos_entrenamiento)
        except ValueError as exc:
            fila.update(disponible=False, cantidad=None, causa=str(exc))
        filas.append(fila)
    contexto = {**(metadatos or {}), 'importacion_id': importacion_id, 'metodo': metodo.nombre, 'origen': origen,
                'pronosticos': [p for p in filas if p['disponible']]}
    if referencia_seleccion is not None:
        contexto['seleccion_modelos'] = referencia_seleccion
    contenido = normalizar({'tipo': 'consulta_pronostico', 'version_codigo': __version__, 'contexto': contexto,
        'entradas': {'consulta': consulta}, 'resultado': {'producto_id': producto_id,
        'completo': all(p['disponible'] for p in filas), 'pronosticos': filas}})
    identidad = registro.guardar(contenido)
    return registro.recuperar(identidad)
