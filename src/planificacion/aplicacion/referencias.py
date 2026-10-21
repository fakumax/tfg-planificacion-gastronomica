"""Comprobación de selecciones conservadas antes de atribuirles resultados."""

import re
from typing import Protocol

from ..dominio.calendario import fecha_iso
from ..dominio.parametros import validar_configuracion
from ..dominio.serializacion import normalizar


class LecturaSelecciones(Protocol):
    def recuperar(self, identidad: str) -> dict: ...


def comprobar_referencias(registro: LecturaSelecciones, contenido: dict) -> None:
    contenido = normalizar(contenido)
    contexto = contenido.get('contexto', {})
    referencia = contexto.get('seleccion_modelos')
    metodo = contexto.get('metodo')
    configuraciones_resultado = []
    if contenido['tipo'] == 'evaluacion_predictiva':
        entradas = contenido['entradas']
        referencia = {'seleccion_id': entradas.get('seleccion_id'),
                      'huella_contenido': entradas.get('huella_seleccion')}
        metodo = 'random_forest'
        configuraciones_resultado = contenido['resultado'].get('productos', [])
    if metodo != 'random_forest':
        if referencia is not None:
            raise ValueError('La referencia de selección no corresponde al método utilizado')
        return
    if (not isinstance(referencia, dict) or not isinstance(referencia.get('seleccion_id'), str)
            or not referencia['seleccion_id'] or not isinstance(referencia.get('huella_contenido'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', referencia['huella_contenido'])):
        raise ValueError('Random Forest requiere una referencia de selección cerrada válida')
    try:
        seleccion = registro.recuperar(referencia['seleccion_id'])
    except (LookupError, FileNotFoundError) as exc:
        raise ValueError('La selección referenciada no existe') from exc
    if seleccion['tipo'] != 'seleccion_modelos':
        raise ValueError('La referencia no identifica una selección cerrada')
    if seleccion['huella_contenido'] != referencia['huella_contenido']:
        raise ValueError('La huella de la selección referenciada no coincide')
    anterior = seleccion.get('contexto', {})
    if anterior.get('importacion_id') != contexto.get('importacion_id'):
        raise ValueError('La selección pertenece a otra importación')
    for campo in ('entorno', 'codigo'):
        actual, previo = contexto.get(campo), anterior.get(campo)
        if campo == 'codigo':
            actual = (actual or {}).get('huella_nucleo_numerico')
            previo = (previo or {}).get('huella_nucleo_numerico')
        if actual != previo:
            raise ValueError(f'El {campo} cambió respecto de la selección')
        if campo in referencia and referencia[campo] != contexto.get(campo):
            raise ValueError(f'El {campo} de la referencia no coincide con la ejecución')
    if (contexto.get('protocolo_sha256') is not None
            and contexto['protocolo_sha256'] != anterior.get('protocolo_sha256')):
        raise ValueError('La selección pertenece a otro protocolo')
    esperados = {p['producto_id'] for p in seleccion['entradas']['lote']['productos']}
    productos = seleccion['resultado']['productos']
    elegidas = {p['producto_id']: p for p in productos}
    if len(elegidas) != len(productos) or set(elegidas) != esperados:
        raise ValueError('La selección está incompleta')
    for producto in productos:
        validar_configuracion(producto['parametros'])
        if producto['estado'] not in ('seleccionada_por_validacion', 'prefijada_validacion_insuficiente'):
            raise ValueError('Estado de selección no reconocido')
    if contexto.get('origen') is not None:
        origen = fecha_iso(contexto['origen'])
        limites = seleccion['entradas']['protocolo']['particion']['origenes_prueba']
        if not fecha_iso(limites[0]) <= origen <= fecha_iso(limites[1]):
            raise ValueError('El origen no pertenece al período de prueba de la selección')
    for producto in [*contexto.get('pronosticos', []), *configuraciones_resultado]:
        pid = producto['producto_id']
        if pid not in elegidas or producto.get('metodo', metodo) != 'random_forest':
            raise ValueError('El pronóstico no corresponde a la selección referenciada')
        parametros = producto.get('parametros', {})
        if any(parametros.get(k) != v for k, v in elegidas[pid]['parametros'].items()):
            raise ValueError('El pronóstico utiliza parámetros distintos de la selección')
        if 'seleccion' in parametros and parametros['seleccion'] != elegidas[pid]['estado']:
            raise ValueError('El estado de configuración no coincide con la selección')
