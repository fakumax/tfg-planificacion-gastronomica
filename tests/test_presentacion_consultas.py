import unittest

from planificacion.presentacion.consultas import explicar_metricas, preparar_grafico, casos_presentados


class PresentacionConsultasTests(unittest.TestCase):
    def test_grafico_conserva_ausencias_y_corta_la_linea(self):
        grafico = preparar_grafico([{'fecha':'2025-01-01','cantidad':2},
            {'fecha':'2025-01-02','cantidad':None}, {'fecha':'2025-01-03','cantidad':0}]).to_dict()
        self.assertEqual(grafico['mark']['invalid'], 'break-paths-show-domains')
        valores = next(iter(grafico['datasets'].values()))
        self.assertEqual([v['cantidad'] for v in valores], [2,None,0])

    def test_metrica_no_aplicable_explica_denominador_y_escala_nula(self):
        base = {'horizonte':1, 'metodo':'persistencia', 'muestra':'completa',
                'n_predicciones':2, 'n_mase_calculable':0, 'mae':1, 'rmse':1, 'mase':None}
        producto = {'metricas':[base], 'predicciones':[
            {'horizonte':1,'metodo':'persistencia','escala':None,'pares_escala':7},
            {'horizonte':1,'metodo':'persistencia','escala':None,'pares_escala':0}]}
        filas = explicar_metricas(producto)
        self.assertEqual(filas[0]['mase'], 'No aplicable')
        self.assertIn('escala cero', filas[0]['causa_mase'])
        self.assertIn('sin pares', filas[0]['causa_mase'])
        self.assertEqual(filas[0]['mae'], 1)

    def test_sin_casos_comunes_no_se_muestra_cero_como_error(self):
        p = {'metricas':[{'metodo':'semanal','horizonte':2,'n_predicciones':0,
             'n_mase_calculable':0,'mae':None,'rmse':None,'mase':None}], 'predicciones':[]}
        m = explicar_metricas(p)[0]
        self.assertEqual(m['mae'], 'No aplicable')
        self.assertIn('Sin casos comunes', m['causa_mae'])

    def test_exclusion_identifica_producto_origen_fecha_y_motivos(self):
        filas = casos_presentados({'producto_id':'P01','casos':[{'origen':'2025-10-31',
            'fecha_objetivo':'2025-11-01','horizonte':1,'evaluable':False,
            'motivos':['respuesta_ausente'], 'pares_escala':3,'ejemplos_entrenamiento':65}]})
        self.assertEqual(filas[0]['producto_id'], 'P01')
        self.assertEqual(filas[0]['estado'], 'Excluido')
        self.assertIn('venta observada', filas[0]['causa'])
