"""Recuperación de un escenario conservado como punto de partida editable."""

from ..dominio.balance import EntradaPrevista, Escenario, Existencia
from ..dominio.calendario import fecha_iso
from ..dominio.recetas import decimal_no_negativo
from .balance import RegistroEjecuciones


def recuperar_escenario(repo: RegistroEjecuciones, ejecucion_id: str) -> Escenario:
    registro = repo.recuperar(ejecucion_id)
    if registro['tipo'] not in ('balance', 'planificacion'):
        raise ValueError('La ejecución no contiene un escenario de balance')
    datos = registro['entradas']['escenario']
    existencias = tuple(Existencia(e['insumo_id'], decimal_no_negativo(e['cantidad'], 'existencia'), e['unidad'])
                        for e in datos['existencias'])
    entradas = tuple(EntradaPrevista(e['insumo_id'], fecha_iso(e['fecha']),
        decimal_no_negativo(e['cantidad'], 'entrada'), e['unidad'], e.get('entrada_id') or f'legado-{n}')
        for n, e in enumerate(datos['entradas'], 1))
    return Escenario(datos['nombre'], datos['version'], existencias, entradas, datos['tipo'])
