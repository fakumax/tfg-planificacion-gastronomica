"""Preparación de gráficos y explicaciones sin modificar resultados guardados."""

import altair as alt
import pandas as pd


def preparar_grafico(filas):
    datos = pd.DataFrame(filas)
    datos['fecha'] = pd.to_datetime(datos['fecha'])
    return alt.Chart(datos).mark_line(point=True, invalid='break-paths-show-domains').encode(
        x=alt.X('fecha:T', title='Fecha', axis=alt.Axis(format='%d/%m')),
        y=alt.Y('cantidad:Q', title='Unidades observadas'),
        tooltip=[alt.Tooltip('fecha:T', title='Fecha', format='%d/%m/%Y'), alt.Tooltip('cantidad:Q', title='Unidades')])


def explicar_metricas(producto):
    filas = []
    for metrica in producto['metricas']:
        fila = dict(metrica)
        for campo in ('mae', 'rmse', 'mase'):
            if metrica[campo] is not None:
                continue
            fila[campo] = 'No aplicable'
            if metrica['n_predicciones']==0:
                causa = 'Sin casos comunes admitidos para este horizonte y muestra'
            elif campo=='mase' and metrica['n_mase_calculable']==0:
                grupo = [p for p in producto['predicciones']
                         if p['horizonte']==metrica['horizonte'] and p['metodo']==metrica['metodo']]
                if 'origenes' in metrica:
                    grupo = [p for p in grupo if p['origen'] in metrica['origenes']]
                sin_pares = sum(p['pares_escala']==0 for p in grupo)
                escala_cero = sum(p['pares_escala']>0 and p['escala'] is None for p in grupo)
                causa = f'Sin denominador válido: {sin_pares} casos sin pares estacionales; {escala_cero} con escala cero'
            else:
                causa = 'No consta una causa suficiente en el registro; revisar la ejecución'
            fila[f'causa_{campo}'] = causa
        filas.append(fila)
    return filas


def casos_presentados(producto):
    causas = {'entradas_incompletas': 'Faltan fechas de entrada',
              'respuesta_ausente': 'No hay venta observada en la fecha objetivo',
              'referencia_semanal_ausente': 'Falta la observación de referencia semanal',
              'menos_de_60_ejemplos': 'Menos de 60 ejemplos completos de entrenamiento'}
    return [{**c, 'producto_id': producto['producto_id'], 'estado': 'Admitido' if c['evaluable'] else 'Excluido',
             'causa': '; '.join(causas.get(m,m) for m in c['motivos']) or 'Caso común de los tres métodos'}
            for c in producto['casos']]
