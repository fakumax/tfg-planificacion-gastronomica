import copy
import unittest
from datetime import date, timedelta
from decimal import Decimal

from planificacion.aplicacion.seleccion import elegir_configuracion, seleccionar_producto
from planificacion.configuracion import recurso_json
from planificacion.dominio.parametros import grilla_configuraciones
from planificacion.dominio.pronosticos import Estimacion


class ModeloSintetico:
    nombre = "random_forest"
    def __init__(self, configuraciones, estados=None): self.configuraciones = configuraciones
    def estimar(self, pid, serie, origen, horizonte):
        assert max(serie) <= origen, "La selección entregó datos futuros al estimador"
        c = self.configuraciones[pid]
        sesgo = {(5, 100): "2", (5, 300): "1.5", (10, 100): "0", (10, 300): "0.5"}
        return Estimacion(Decimal(10) + Decimal(sesgo[c["max_depth"], c["n_estimators"]]))


def serie_completa():
    return {date(2025, 1, 1) + timedelta(days=n): 10 for n in range(365)}


class SeleccionTests(unittest.TestCase):
    def setUp(self): self.protocolo = recurso_json("protocolo_tp3_v1.json")

    def test_validacion_elige_por_error_comun_de_los_siete_horizontes(self):
        resultado = seleccionar_producto("P01", serie_completa(), ModeloSintetico, self.protocolo)
        self.assertEqual(resultado["estado"], "seleccionada_por_validacion")
        self.assertEqual(resultado["parametros"]["max_depth"], 10)
        self.assertEqual(resultado["parametros"]["n_estimators"], 100)
        self.assertEqual(len(resultado["candidatas"]), 4)
        self.assertEqual(resultado["cobertura_validacion"], {h: 25 for h in range(1, 8)})

    def test_falta_de_cobertura_usa_configuracion_prefijada_sin_optimizar(self):
        serie = serie_completa()
        for f in serie:
            if date(2025, 10, 1) <= f <= date(2025, 10, 31): serie[f] = None
        resultado = seleccionar_producto("P07", serie, ModeloSintetico, self.protocolo)
        self.assertEqual(resultado["estado"], "prefijada_validacion_insuficiente")
        self.assertEqual(resultado["parametros"]["max_depth"], 5)
        self.assertEqual(resultado["parametros"]["n_estimators"], 100)
        self.assertEqual(len(resultado["candidatas"]), 1)

    def test_umbral_de_catorce_y_desempate_por_profundidad_y_arboles(self):
        candidatas = [{"parametros": c, "mae_promedio_horizontes": 1.0} for c in grilla_configuraciones()]
        elegida, estado = elegir_configuracion({h: 14 for h in range(1, 8)}, candidatas)
        self.assertEqual((elegida["max_depth"], elegida["n_estimators"]), (5, 100))
        self.assertEqual(estado, "seleccionada_por_validacion")
        _, estado = elegir_configuracion({**{h: 14 for h in range(1, 8)}, 7: 13}, candidatas)
        self.assertEqual(estado, "prefijada_validacion_insuficiente")

    def test_tolerancia_del_desempate_respeta_un_millonesimo(self):
        candidatas = [{"parametros": c, "mae_promedio_horizontes": 2.0} for c in grilla_configuraciones()]
        candidatas[0]["mae_promedio_horizontes"] = 1.0000005
        candidatas[2]["mae_promedio_horizontes"] = 1.0
        elegida, _ = elegir_configuracion({h: 14 for h in range(1, 8)}, candidatas)
        self.assertEqual(elegida["max_depth"], 5)
        candidatas[0]["mae_promedio_horizontes"] = 1.000002
        elegida, _ = elegir_configuracion({h: 14 for h in range(1, 8)}, candidatas)
        self.assertEqual(elegida["max_depth"], 10)

    def test_datos_de_prueba_no_cambian_la_seleccion_por_validacion(self):
        serie = serie_completa()
        uno = seleccionar_producto("P01", serie, ModeloSintetico, self.protocolo)
        for f in serie:
            if f >= date(2025, 11, 1): serie[f] = 99999
        dos = seleccionar_producto("P01", serie, ModeloSintetico, self.protocolo)
        self.assertEqual(uno, dos)

    def test_protocolo_modificado_requiere_nueva_implementacion_explicita(self):
        protocolo = copy.deepcopy(self.protocolo)
        protocolo["seleccion_configuracion"]["min_origenes_comunes_por_horizonte"] = 13
        with self.assertRaisesRegex(ValueError, "protocolo"):
            seleccionar_producto("P01", serie_completa(), ModeloSintetico, protocolo)
