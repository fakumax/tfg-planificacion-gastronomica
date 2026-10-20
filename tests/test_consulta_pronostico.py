import unittest
from datetime import date

from planificacion.aplicacion.pronosticos import consultar_disponibilidad, consultar_pronostico
from planificacion.dominio.pronosticos import Persistencia, ReferenciaSemanal
from test_planificacion import RegistroEnMemoria, VentasParaPlan


class ConsultaPronosticoTests(unittest.TestCase):
    def setUp(self):
        self.ventas = VentasParaPlan([2])
        self.repo = RegistroEnMemoria()
        self.origen = date(2025,1,1)

    def test_consulta_individual_no_exige_el_catalogo_completo_y_conserva_procedencia(self):
        self.ventas.listar_productos = lambda i: self.fail('La consulta individual no debe exigir otros productos')
        r = consultar_pronostico(self.ventas, self.repo, Persistencia(), 'lote', 'P01', self.origen)
        self.assertTrue(r['resultado']['completo'])
        self.assertEqual(len(r['resultado']['pronosticos']), 7)
        self.assertTrue(all(p['cantidad']=='2' for p in r['resultado']['pronosticos']))
        self.assertEqual(self.ventas.fines_consultados, [self.origen])
        self.assertEqual(r['entradas']['consulta']['fuentes'][0]['sha256'], 'a'*64)

    def test_indisponible_muestra_producto_objetivo_metodo_y_causa_sin_cero(self):
        r = consultar_pronostico(self.ventas, self.repo, ReferenciaSemanal(), 'lote', 'P01', self.origen)
        self.assertFalse(r['resultado']['completo'])
        primero = r['resultado']['pronosticos'][0]
        self.assertIsNone(primero['cantidad'])
        self.assertEqual(primero['producto_id'], 'P01')
        self.assertEqual(primero['fecha'], '2025-01-02')
        self.assertEqual(primero['metodo'], 'semanal')
        self.assertIn('2024-12-26', primero['causa'])
        self.assertTrue(r['resultado']['pronosticos'][-1]['disponible'])

    def test_disponibilidad_diferencia_metodos_y_detalla_fechas_ausentes(self):
        filas = consultar_disponibilidad(self.ventas, 'lote', 'P01', self.origen)
        self.assertEqual(len(filas), 21)
        p = next(f for f in filas if f['metodo']=='persistencia')
        rf = next(f for f in filas if f['metodo']=='random_forest')
        self.assertTrue(p['disponible'])
        self.assertFalse(rf['disponible'])
        self.assertIn('2024-12-31', rf['causa'])
        self.assertIn('60', rf['causa'])

    def test_origen_ausente_no_inventa_pronosticos(self):
        self.ventas.cantidades = [None]
        r = consultar_pronostico(self.ventas, self.repo, Persistencia(), 'lote', 'P01', self.origen)
        self.assertTrue(all(p['cantidad'] is None and p['causa'] for p in r['resultado']['pronosticos']))
