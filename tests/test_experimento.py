import tempfile
import unittest
from datetime import date
from pathlib import Path

from planificacion.aplicacion.experimento import ejecutar_prueba, ejecutar_seleccion
from planificacion.aplicacion.experimento import configuracion_planificacion
from planificacion.configuracion import recurso_json
from planificacion.dominio.parametros import CONFIGURACION_PREFIJADA
from planificacion.infraestructura.sqlite_ejecuciones import SQLiteEjecuciones
from planificacion.infraestructura.sqlite_ventas import SQLiteVentas
from soporte_experimentos import importacion_sintetica


def ejecutor_sintetico(tareas, **opciones):
    resultados = []
    for t in tareas:
        pid = t["producto_id"]
        if t["accion"] == "seleccion":
            resultados.append({"producto_id": pid, "parametros": dict(CONFIGURACION_PREFIJADA),
                "estado": "prefijada_validacion_insuficiente", "cobertura_validacion": {h: 0 for h in range(1, 8)},
                "candidatas": [], "casos": []})
        else:
            resultados.append({"producto_id": pid, "parametros": t["parametros"], "predicciones": [], "metricas": [],
                               "sensibilidad": [], "casos": [], "bloques_p07": None})
    return resultados


class ExperimentoTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.base, self.identidad = importacion_sintetica(self.raiz)
        self.ventas = SQLiteVentas(self.base)
        self.registro = SQLiteEjecuciones(self.base)
        self.protocolo = recurso_json("protocolo_tp3_v1.json")

    def seleccionar(self, ejecutor=ejecutor_sintetico):
        return ejecutar_seleccion(self.ventas, self.registro, self.identidad, self.protocolo, ejecutor)

    def test_seleccion_completa_se_conserva_antes_de_la_prueba(self):
        seleccion = self.seleccionar()
        self.assertEqual(seleccion["tipo"], "seleccion_modelos")
        self.assertEqual(len(seleccion["resultado"]["productos"]), 7)
        prueba = ejecutar_prueba(self.ventas, self.registro, self.identidad, seleccion["ejecucion_id"],
                                 self.protocolo, ejecutor_sintetico)
        self.assertEqual(prueba["tipo"], "evaluacion_predictiva")
        self.assertEqual(prueba["entradas"]["seleccion_id"], seleccion["ejecucion_id"])

    def test_prueba_no_acepta_un_balance_como_seleccion(self):
        identidad = self.registro.guardar({"tipo": "balance", "version_codigo": "prueba",
                                           "entradas": {}, "resultado": {}})
        with self.assertRaisesRegex(ValueError, "selección"):
            ejecutar_prueba(self.ventas, self.registro, self.identidad, identidad,
                             self.protocolo, ejecutor_sintetico)

    def test_seleccion_de_otra_importacion_no_se_reutiliza_silenciosamente(self):
        seleccion = self.seleccionar()
        _, otra = importacion_sintetica(self.raiz, multiplicador=2)
        with self.assertRaisesRegex(ValueError, "importación"):
            ejecutar_prueba(self.ventas, self.registro, otra, seleccion["ejecucion_id"],
                             self.protocolo, ejecutor_sintetico)

    def test_resultados_incompletos_no_crean_seleccion_parcial(self):
        def incompleto(tareas, **opciones): return ejecutor_sintetico(tareas)[:-1]
        with self.assertRaisesRegex(ValueError, "incompleto"):
            self.seleccionar(incompleto)

    def test_mismo_dato_y_configuracion_conservan_huella_de_entrada(self):
        uno, dos = self.seleccionar(), self.seleccionar()
        self.assertNotEqual(uno["ejecucion_id"], dos["ejecucion_id"])
        self.assertEqual(uno["huella_entrada"], dos["huella_entrada"])

    def test_prueba_no_acepta_otra_configuracion_que_la_cerrada(self):
        seleccion = self.seleccionar()
        def cambiar(tareas, **opciones):
            resultados = ejecutor_sintetico(tareas)
            resultados[0]["parametros"] = {**resultados[0]["parametros"], "n_estimators": 300}
            return resultados
        with self.assertRaisesRegex(ValueError, "configuración"):
            ejecutar_prueba(self.ventas, self.registro, self.identidad, seleccion["ejecucion_id"],
                             self.protocolo, cambiar)

    def test_planificacion_recupera_la_seleccion_con_su_identidad(self):
        s = self.seleccionar()
        configuraciones, estados, referencia = configuracion_planificacion(self.ventas, self.registro,
            self.identidad, s["ejecucion_id"], self.protocolo, date(2025, 11, 1), {})
        self.assertEqual(len(configuraciones), 7)
        self.assertEqual(set(estados.values()), {"prefijada_validacion_insuficiente"})
        self.assertEqual(referencia["seleccion_id"], s["ejecucion_id"])

    def test_no_usa_una_seleccion_posterior_al_origen(self):
        s = self.seleccionar()
        with self.assertRaisesRegex(ValueError, "período"):
            configuracion_planificacion(self.ventas, self.registro, self.identidad,
                s["ejecucion_id"], self.protocolo, date(2025, 9, 30), {})

    def test_entorno_y_nucleo_cambiados_no_se_reutilizan_silenciosamente(self):
        s = ejecutar_seleccion(self.ventas, self.registro, self.identidad, self.protocolo,
            ejecutor_sintetico, metadatos={"entorno": {"python": "prueba"}, "codigo": {"huella_nucleo_numerico": "a"}})
        for metadatos in ({"entorno": {"python": "otro"}},
                           {"entorno": {"python": "prueba"}, "codigo": {"huella_nucleo_numerico": "b"}}):
            with self.assertRaises(ValueError):
                configuracion_planificacion(self.ventas, self.registro, self.identidad,
                    s["ejecucion_id"], self.protocolo, date(2025, 11, 1), metadatos)
