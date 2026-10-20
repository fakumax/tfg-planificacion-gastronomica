import unittest
from datetime import date, timedelta
from decimal import Decimal

from planificacion.dominio.pronosticos import Persistencia


class PersistenciaTests(unittest.TestCase):
    def setUp(self):
        self.origen = date(2025, 10, 31)
        self.metodo = Persistencia()

    def test_repite_observacion_del_origen_para_los_siete_horizontes(self):
        serie = {self.origen: 3}
        for h in range(1, 8):
            estimacion = self.metodo.estimar("P01", serie, self.origen, h)
            self.assertEqual(estimacion.cantidad, Decimal(3))
            self.assertEqual(self.metodo.nombre, "persistencia")
            self.assertIsNone(estimacion.ejemplos_entrenamiento)

    def test_no_usa_observaciones_posteriores_al_origen(self):
        uno = self.metodo.estimar("P01", {self.origen: 3, self.origen + timedelta(days=1): 100}, self.origen, 1)
        dos = self.metodo.estimar("P01", {self.origen: 3, self.origen + timedelta(days=1): 999}, self.origen, 1)
        self.assertEqual(uno.cantidad, dos.cantidad)

    def test_origen_ausente_no_se_reemplaza_por_otra_fecha_o_cero(self):
        for serie in ({}, {self.origen: None}, {self.origen - timedelta(days=1): 9}):
            with self.subTest(serie=serie), self.assertRaisesRegex(ValueError, "observación"):
                self.metodo.estimar("P01", serie, self.origen, 1)

    def test_horizontes_fuera_del_contrato_se_rechazan(self):
        for h in (0, 8, 1.5, True):
            with self.subTest(h=h), self.assertRaises(ValueError):
                self.metodo.estimar("P01", {self.origen: 3}, self.origen, h)

    def test_cero_explicito_sintetico_se_conserva_sin_confundirlo_con_ausencia(self):
        estimacion = self.metodo.estimar("P01", {self.origen: 0}, self.origen, 1)
        self.assertEqual(estimacion.cantidad, 0)
