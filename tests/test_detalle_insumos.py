import copy
import unittest
from decimal import Decimal

from planificacion.aplicacion.detalle import detallar_insumo
from planificacion.aplicacion.balance import ejecutar_balance
from planificacion.dominio.recetas import interpretar_recetario
from test_balance import FECHAS, escenario_sintetico, plan_sintetico
from test_recetas import modelo_sintetico


class Memoria:
    def guardar(self, contenido): self.contenido = contenido; return 'prueba'
    def recuperar(self, identidad): return copy.deepcopy(self.contenido)


class DetalleInsumosTests(unittest.TestCase):
    def registro(self):
        return ejecutar_balance(Memoria(), interpretar_recetario(modelo_sintetico(), 'a'*64),
            plan_sintetico((3,0,0,0,0,0,0)), escenario_sintetico(), FECHAS)

    def test_aportes_conservan_componentes_y_suman_el_consumo_guardado(self):
        registro = self.registro()
        antes = copy.deepcopy(registro)
        detalle = detallar_insumo(registro, 'arroz')
        dia = [a for a in detalle['aportes'] if a['fecha']==FECHAS[0].isoformat()]
        self.assertEqual({a['componente'] for a in dia}, {'base','extra'})
        self.assertEqual(sum(a['consumo'] for a in dia), Decimal('.9'))
        self.assertTrue(all(a['producto_id']=='P01' and a['unidad']=='g' for a in dia))
        self.assertEqual(detalle['alerta']['primera_fecha'], FECHAS[0].isoformat())
        self.assertEqual(len(detalle['dias_deficit']), 7)
        self.assertEqual(registro, antes)

    def test_agua_tiene_consumo_y_saldo_no_aplicable_sin_alerta(self):
        detalle = detallar_insumo(self.registro(), 'agua')
        self.assertIsNone(detalle['alerta'])
        self.assertEqual(detalle['dias_deficit'], [])
        self.assertIsNone(detalle['balance'][0]['saldo'])
        self.assertEqual(detalle['aportes'][0]['consumo'], Decimal('7.5'))

    def test_insumo_ajeno_se_rechaza(self):
        with self.assertRaises(LookupError):
            detallar_insumo(self.registro(), 'inexistente')
