import unittest
from datetime import date, timedelta

from planificacion.aplicacion.comparacion import evaluar_producto, sensibilidad_bloques
from planificacion.configuracion import recurso_json
from planificacion.dominio.evaluacion import PrediccionEvaluada
from planificacion.dominio.parametros import CONFIGURACION_PREFIJADA
from test_seleccion import ModeloSintetico, serie_completa


def bloques_sinteticos(dias=(1, 8, 15)):
    registros = []
    for dia in dias:
        origen = date(2025, 11, dia)
        for h in range(1, 8):
            for metodo, estimado in (("persistencia", 12), ("semanal", 13), ("random_forest", 9)):
                registros.append(PrediccionEvaluada("P07", metodo, origen, origen + timedelta(days=h),
                                                    h, 10, estimado, 2, 100))
    return registros


class ComparacionTests(unittest.TestCase):
    def test_tres_metodos_comparten_casos_y_se_informa_resultado_inferior(self):
        resultado = evaluar_producto("P01", serie_completa(), CONFIGURACION_PREFIJADA,
                                     "prefijada", ModeloSintetico, recurso_json("protocolo_tp3_v1.json"))
        self.assertEqual(len(resultado["predicciones"]), 3 * 7 * 55)
        for h in range(1, 8):
            grupos = [r for r in resultado["metricas"] if r["horizonte"] == h]
            self.assertEqual({r["n_predicciones"] for r in grupos}, {55})
            rf = next(r for r in grupos if r["metodo"] == "random_forest")
            referencia = next(r for r in grupos if r["metodo"] == "persistencia")
            self.assertEqual((rf["mae"], referencia["mae"]), (2, 0))

    def test_sin_casos_comunes_hay_cobertura_sin_errores_inventados(self):
        serie = serie_completa()
        for f in serie:
            if f >= date(2025, 11, 1): serie[f] = None
        resultado = evaluar_producto("P01", serie, CONFIGURACION_PREFIJADA, "prefijada",
                                     ModeloSintetico, recurso_json("protocolo_tp3_v1.json"))
        self.assertEqual(resultado["predicciones"], [])
        self.assertTrue(all(m["mae"] is None and m["n_predicciones"] == 0 for m in resultado["metricas"]))

    def test_bloques_p07_informan_diferencias_y_retiro_de_un_bloque(self):
        resultado = sensibilidad_bloques(bloques_sinteticos())
        self.assertEqual(resultado["n_bloques_completos"], 3)
        self.assertEqual(len(resultado["retiro_de_bloque"]), 3)
        for r in resultado["por_bloque"]:
            self.assertEqual(r["diferencia_rf_persistencia"], -1)
            self.assertEqual(r["diferencia_rf_semanal"], -2)
        for r in resultado["retiro_de_bloque"]:
            self.assertEqual(r["diferencia_rf_persistencia"], -1)
            self.assertEqual(r["n_bloques_restantes"], 2)

    def test_bloque_incompleto_no_se_presenta_como_siete_horizontes(self):
        registros = [r for r in bloques_sinteticos() if not (r.origen.day == 8 and r.horizonte == 7)]
        resultado = sensibilidad_bloques(registros)
        self.assertEqual(resultado["n_bloques_completos"], 2)
        self.assertEqual([r["origen"].day for r in resultado["por_bloque"]], [1, 15])

    def test_retiro_del_unico_bloque_no_inventa_comparacion(self):
        resultado = sensibilidad_bloques(bloques_sinteticos((1,)))
        self.assertEqual(resultado["retiro_de_bloque"][0]["n_bloques_restantes"], 0)
        self.assertIsNone(resultado["retiro_de_bloque"][0]["diferencia_rf_persistencia"])
