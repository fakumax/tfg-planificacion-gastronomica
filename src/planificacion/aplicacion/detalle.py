"""Explicación de un insumo usando exclusivamente las entradas de su ejecución."""

from decimal import Decimal

from ..dominio.recetas import decimal_no_negativo


def detallar_insumo(registro: dict, insumo_id: str) -> dict:
    if registro['tipo'] not in ('balance', 'planificacion'):
        raise ValueError('La ejecución no contiene un balance')
    entradas, resultado = registro['entradas'], registro['resultado']
    recetario = entradas['recetario']
    insumos = {i['insumo_id']: i for i in recetario['insumos']}
    if insumo_id not in insumos:
        raise LookupError('El insumo no pertenece al recetario de esta ejecución')
    recetas = {r['producto_id']: r for r in recetario['recetas']}
    aportes = []
    for p in entradas['plan']:
        receta = recetas[p['producto_id']]
        cantidad = decimal_no_negativo(p['cantidad'], 'cantidad planificada')
        rendimiento = decimal_no_negativo(receta['rendimiento'], 'rendimiento')
        for linea in receta['lineas']:
            if linea['insumo_id'] == insumo_id:
                base = decimal_no_negativo(linea['cantidad'], 'cantidad de receta')
                aportes.append({'producto_id': p['producto_id'], 'fecha': p['fecha'],
                    'cantidad_producto': cantidad, 'rendimiento': rendimiento,
                    'componente': linea['componente'], 'cantidad_receta': base,
                    'consumo': cantidad * base / rendimiento, 'unidad': linea['unidad']})
    saldos = {s['fecha']: s for s in resultado['saldos'] if s['insumo_id']==insumo_id}
    balance = []
    for consumo in resultado['consumos']:
        if consumo['insumo_id'] != insumo_id:
            continue
        fecha = consumo['fecha']
        explicado = sum((a['consumo'] for a in aportes if a['fecha']==fecha), Decimal(0))
        if explicado != Decimal(consumo['cantidad']):
            raise ValueError('Los aportes no coinciden con el consumo conservado')
        balance.append(saldos.get(fecha, {'fecha': fecha, 'consumo': consumo['cantidad'],
                                         'saldo': None, 'unidad': consumo['unidad']}))
    return {'insumo': insumos[insumo_id], 'aportes': aportes, 'balance': balance,
            'entradas': [e for e in entradas['escenario']['entradas'] if e['insumo_id']==insumo_id],
            'alerta': next((a for a in resultado['alertas'] if a['insumo_id']==insumo_id), None),
            'dias_deficit': [s['fecha'] for s in balance if s['saldo'] is not None and Decimal(s['saldo'])<0]}
