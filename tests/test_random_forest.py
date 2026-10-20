import unittest
from datetime import date, timedelta
from decimal import Decimal

from planificacion.infraestructura.random_forest import RandomForest
from test_temporal import serie_sintetica


CONFIG = {"n_estimators": 100, "max_depth": 5, "min_samples_leaf": 2, "random_state": 42}


class RandomForestTests(unittest.TestCase):
    def test_ajuste_real_reproduce_serie_constante_y_declara_parametros(self):
        serie = {f: 10 for f in serie_sintetica(120)}
        origen = date(2025, 4, 1)
        estimacion = RandomForest({"P01": CONFIG}).estimar("P01", serie, origen, 7)
        self.assertEqual(estimacion.cantidad, Decimal(10))
        self.assertGreaterEqual(estimacion.ejemplos_entrenamiento, 60)
        self.assertLessEqual(estimacion.parametros["fecha_ultima_respuesta"], origen.isoformat())
        self.assertEqual(estimacion.parametros["random_state"], 42)
        self.assertEqual(estimacion.parametros["parametros_efectivos"]["n_jobs"], 1)

    def test_misma_semilla_e_informacion_conocida_reproducen_prediccion(self):
        serie = {f: (q % 9) + 1 for f, q in serie_sintetica(120).items()}
        origen = date(2025, 4, 1)
        modelo = RandomForest({"P01": CONFIG})
        uno = modelo.estimar("P01", serie, origen, 3)
        dos = modelo.estimar("P01", serie, origen, 3)
        for f in serie:
            if f > origen: serie[f] = 99999
        tres = modelo.estimar("P01", serie, origen, 3)
        self.assertEqual(uno.cantidad, dos.cantidad)
        self.assertEqual(uno.cantidad, tres.cantidad)
        self.assertEqual(uno.ejemplos_entrenamiento, tres.ejemplos_entrenamiento)

    def test_menos_de_sesenta_ejemplos_no_inventa_modelo_ajustado(self):
        with self.assertRaisesRegex(ValueError, "60"):
            RandomForest({"P01": CONFIG}).estimar("P01", serie_sintetica(30), date(2025, 1, 25), 7)

    def test_entradas_incompletas_en_origen_bloquean(self):
        serie = serie_sintetica(120)
        origen = date(2025, 4, 1)
        serie[origen - timedelta(days=3)] = None
        with self.assertRaisesRegex(ValueError, "entradas"):
            RandomForest({"P01": CONFIG}).estimar("P01", serie, origen, 1)

    def test_configuracion_fuera_del_protocolo_o_ausente_se_rechaza(self):
        for configuraciones in ({}, {"P01": {**CONFIG, "n_estimators": 200}},
                                 {"P01": {**CONFIG, "random_state": 7}},
                                 {"P01": {**CONFIG, "min_samples_leaf": 1}}):
            with self.subTest(configuraciones=configuraciones), self.assertRaisesRegex(ValueError, "configuración"):
                RandomForest(configuraciones).estimar("P01", serie_sintetica(120), date(2025, 4, 1), 1)
