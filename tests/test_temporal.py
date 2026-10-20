import unittest
from datetime import date, timedelta

from planificacion.dominio.temporal import caracteristicas, ejemplos_entrenamiento
from planificacion.dominio.pronosticos import ReferenciaSemanal


def serie_sintetica(dias=100):
    return {date(2025, 1, 1) + timedelta(days=n): n + 1 for n in range(dias)}


class TemporalTests(unittest.TestCase):
    def test_variables_respetan_calendario_y_fecha_objetivo(self):
        x = caracteristicas(serie_sintetica(), date(2025, 1, 10), 2)
        self.assertEqual(x, (10.0, 9.0, 3.0, 7.0, 6.0, 1.0))

    def test_hueco_no_desplaza_rezagos_para_ocultarlo(self):
        serie = serie_sintetica()
        serie[date(2025, 1, 3)] = None
        with self.assertRaisesRegex(ValueError, "entradas"):
            caracteristicas(serie, date(2025, 1, 10), 2)

    def test_ejemplos_solo_incluyen_respuestas_conocidas_en_el_origen(self):
        ejemplos = ejemplos_entrenamiento(serie_sintetica(), date(2025, 1, 20), 3)
        self.assertEqual(len(ejemplos), 10)
        self.assertEqual(ejemplos[0].origen, date(2025, 1, 8))
        self.assertEqual(ejemplos[-1].fecha_objetivo, date(2025, 1, 20))
        self.assertTrue(all(e.fecha_objetivo <= date(2025, 1, 20) for e in ejemplos))

    def test_cambiar_el_futuro_no_cambia_el_entrenamiento_disponible(self):
        serie = serie_sintetica()
        antes = ejemplos_entrenamiento(serie, date(2025, 1, 20), 7)
        for fecha in serie:
            if fecha > date(2025, 1, 20): serie[fecha] = 999999
        despues = ejemplos_entrenamiento(serie, date(2025, 1, 20), 7)
        self.assertEqual(antes, despues)

    def test_respuesta_ausente_no_se_imputa_en_entrenamiento(self):
        serie = serie_sintetica()
        serie[date(2025, 1, 20)] = None
        ejemplos = ejemplos_entrenamiento(serie, date(2025, 1, 20), 3)
        self.assertEqual(len(ejemplos), 9)

    def test_referencia_semanal_usa_fecha_objetivo_menos_siete(self):
        metodo = ReferenciaSemanal()
        serie, origen = serie_sintetica(), date(2025, 1, 10)
        self.assertEqual(metodo.estimar("P01", serie, origen, 1).cantidad, 4)
        self.assertEqual(metodo.estimar("P01", serie, origen, 7).cantidad, 10)

    def test_referencia_semanal_ausente_no_usa_la_fila_siguiente(self):
        serie = serie_sintetica()
        serie.pop(date(2025, 1, 4))
        with self.assertRaisesRegex(ValueError, "referencia"):
            ReferenciaSemanal().estimar("P01", serie, date(2025, 1, 10), 1)
