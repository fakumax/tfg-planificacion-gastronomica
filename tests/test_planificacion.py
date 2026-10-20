import unittest
from datetime import date
from decimal import Decimal

from planificacion.aplicacion.planificacion import planificar
from planificacion.dominio.pronosticos import Estimacion, Persistencia
from planificacion.dominio.recetas import interpretar_recetario
from test_consulta_ventas import VentasEnMemoria
from test_balance import escenario_sintetico
from test_recetas import modelo_sintetico


class VentasParaPlan(VentasEnMemoria):
    def __init__(self, cantidades):
        super().__init__(cantidades)
        self.fines_consultados = []

    def listar_productos(self, identidad):
        return (self.obtener_producto(identidad, "P01"),)

    def obtener_diarias(self, identidad, pid, inicio, fin):
        self.fines_consultados.append(fin)
        return super().obtener_diarias(identidad, pid, inicio, fin)


class RegistroEnMemoria:
    def __init__(self): self.contenidos = []
    def guardar(self, contenido): self.contenidos.append(contenido); return "ejecucion"
    def recuperar(self, identidad): return {"ejecucion_id": identidad, **self.contenidos[-1]}


class PlanificacionTests(unittest.TestCase):
    def setUp(self):
        self.recetario = interpretar_recetario(modelo_sintetico(), "a" * 64)
        self.ventas = VentasParaPlan([2])
        self.registro = RegistroEnMemoria()
        self.origen = date(2025, 1, 1)

    def ejecutar(self, metodo=None):
        return planificar(self.ventas, self.registro, metodo or Persistencia(), self.recetario,
                           "lote", self.origen, escenario_sintetico())

    def test_conecta_ventas_pronostico_consumo_saldo_y_alerta(self):
        resultado = self.ejecutar()
        self.assertEqual(resultado["tipo"], "planificacion")
        self.assertEqual(resultado["contexto"]["metodo"], "persistencia")
        plan = resultado["entradas"]["plan"]
        self.assertEqual(len(plan), 7)
        self.assertEqual(plan[0]["fecha"], "2025-01-02")
        self.assertEqual(plan[0]["cantidad"], "2")
        alerta = resultado["resultado"]["alertas"][0]
        self.assertEqual(alerta["deficit_inicial"], "0.6")
        self.assertEqual(alerta["maximo_deficit"], "4.2")

    def test_lectura_historica_no_solicita_fechas_posteriores_al_origen(self):
        self.ejecutar()
        self.assertEqual(self.ventas.fines_consultados, [self.origen])

    def test_origen_ausente_bloquea_y_no_registra_un_resultado_parcial(self):
        self.ventas.cantidades = [None]
        with self.assertRaisesRegex(ValueError, "observación"):
            self.ejecutar()
        self.assertEqual(self.registro.contenidos, [])

    def test_catalogo_y_recetario_deben_cubrir_los_mismos_productos(self):
        self.ventas.listar_productos = lambda identidad: ()
        with self.assertRaisesRegex(ValueError, "catálogo"):
            self.ejecutar()
        self.assertEqual(self.registro.contenidos, [])

    def test_metodo_sustituible_declara_el_metodo_que_realmente_se_usa(self):
        class MetodoDePrueba:
            nombre = "prueba"
            def estimar(self, producto_id, serie, origen, horizonte):
                return Estimacion(Decimal(3), {"motivo": "caso sintético"})
        resultado = self.ejecutar(MetodoDePrueba())
        self.assertEqual(resultado["contexto"]["metodo"], "prueba")
        self.assertEqual(resultado["entradas"]["plan"][0]["cantidad"], "3")

    def test_registra_procedencia_y_configuracion_de_pronostico(self):
        resultado = self.ejecutar()
        contexto = resultado["contexto"]
        self.assertEqual(contexto["importacion_id"], "lote")
        self.assertEqual(contexto["origen"], "2025-01-01")
        self.assertEqual(contexto["historico"][0]["fuentes"][0]["sha256"], "a" * 64)
        self.assertEqual(len(contexto["pronosticos"]), 7)
        self.assertIsNone(contexto["pronosticos"][0]["ejemplos_entrenamiento"])
