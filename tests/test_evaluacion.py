import math
import unittest
from datetime import date, timedelta

from planificacion.dominio.evaluacion import (
    PrediccionEvaluada, evaluar_caso, escala_mase, metricas, seleccionar_no_solapados,
)
from test_temporal import serie_sintetica


def prediccion(origen, real=10, estimado=8, escala=2, pares=10, metodo="persistencia"):
    return PrediccionEvaluada("P01", metodo, origen, origen + timedelta(days=1), 1,
                              float(real), float(estimado), escala, pares)


class EvaluacionTests(unittest.TestCase):
    def test_escala_estacional_usa_pares_validos_hasta_el_origen(self):
        escala, pares = escala_mase(serie_sintetica(30), date(2025, 1, 10))
        self.assertEqual(escala, 7)
        self.assertEqual(pares, 3)

    def test_escala_no_desplaza_pares_sobre_fechas_ausentes(self):
        serie = serie_sintetica(30)
        serie[date(2025, 1, 2)] = None
        escala, pares = escala_mase(serie, date(2025, 1, 10))
        self.assertEqual((escala, pares), (7, 2))

    def test_escala_cero_o_sin_pares_es_no_aplicable(self):
        constante = {f: 5 for f in serie_sintetica(21)}
        self.assertEqual(escala_mase(constante, date(2025, 1, 21)), (None, 14))
        self.assertEqual(escala_mase(constante, date(2025, 1, 3)), (None, 0))

    def test_metricas_y_mase_se_escalan_por_cada_origen(self):
        filas = [prediccion(date(2025, 11, 1), real=10, estimado=5, escala=2),
                 prediccion(date(2025, 11, 2), real=10, estimado=8, escala=4, pares=12)]
        r = metricas(filas)
        self.assertEqual(r["mae"], 3.5)
        self.assertAlmostEqual(r["rmse"], math.sqrt(14.5))
        self.assertEqual(r["mase"], 1.5)
        self.assertEqual(r["n_mase_calculable"], 2)
        self.assertEqual(r["cuartil_1_error_absoluto"], 2.75)
        self.assertEqual(r["cuartil_3_error_absoluto"], 4.25)
        self.assertEqual(r["maximo_error_absoluto"], 5)
        self.assertTrue(r["exploratoria"])

    def test_mase_no_calculable_no_se_publica_como_cero(self):
        r = metricas([prediccion(date(2025, 11, 1), escala=None, pares=0)])
        self.assertIsNone(r["mase"])
        self.assertEqual(r["n_mase_calculable"], 0)
        self.assertEqual(r["mae"], 2)

    def test_sin_casos_no_inventa_errores(self):
        r = metricas([])
        self.assertEqual(r["n_predicciones"], 0)
        self.assertIsNone(r["mae"])
        self.assertIsNone(r["rmse"])
        self.assertIsNone(r["mase"])

    def test_metricas_no_mezclan_productos_horizontes_o_metodos(self):
        filas = [prediccion(date(2025, 11, 1)), prediccion(date(2025, 11, 2), metodo="semanal")]
        with self.assertRaises(ValueError): metricas(filas)

    def test_casos_incompletos_registran_causas_sin_imputar(self):
        caso = evaluar_caso(serie_sintetica(100), date(2025, 1, 5), 1)
        self.assertFalse(caso.evaluable)
        self.assertIn("entradas_incompletas", caso.motivos)
        self.assertIn("referencia_semanal_ausente", caso.motivos)
        self.assertIn("menos_de_60_ejemplos", caso.motivos)

    def test_caso_comun_con_respuesta_conocida_en_evaluacion(self):
        caso = evaluar_caso(serie_sintetica(120), date(2025, 4, 1), 7)
        self.assertTrue(caso.evaluable)
        self.assertEqual(caso.motivos, ())
        self.assertGreaterEqual(caso.ejemplos_entrenamiento, 60)

    def test_sensibilidad_elige_origenes_cronologicos_separados_siete_dias(self):
        filas = [prediccion(date(2025, 11, d)) for d in (2, 1, 7, 8, 9, 15)]
        elegidos = seleccionar_no_solapados(filas)
        self.assertEqual([p.origen.day for p in elegidos], [1, 8, 15])
