import tempfile
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from planificacion.aplicacion.balance import ejecutar_balance
from planificacion.aplicacion.revisiones import recuperar_escenario
from planificacion.dominio.balance import EntradaPrevista, calcular_balance
from planificacion.dominio.recetas import interpretar_recetario
from planificacion.infraestructura.modelo_relacional import actualizar_modelo
from planificacion.infraestructura.sqlite_ejecuciones import SQLiteEjecuciones
from test_balance import FECHAS, escenario_sintetico, plan_sintetico
from test_recetas import modelo_sintetico


class RevisionesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / 'base.sqlite3'
        self.repo = SQLiteEjecuciones(self.base)
        self.recetario = interpretar_recetario(modelo_sintetico(), 'a' * 64)

    def calcular(self, escenario=None, **opciones):
        return ejecutar_balance(self.repo, self.recetario, plan_sintetico(),
                                escenario or escenario_sintetico(), FECHAS, **opciones)

    def test_id_repetido_bloquea_aunque_cambie_cantidad(self):
        entrada = EntradaPrevista('arroz', FECHAS[0], Decimal('.1'), 'g', entrada_id='entrega-1')
        escenario = escenario_sintetico(entradas=(entrada, replace(entrada, cantidad=Decimal('.2'))))
        with self.assertRaisesRegex(ValueError, 'identificador.*duplicado'):
            self.calcular(escenario)
        self.assertFalse(self.base.exists())

    def test_dos_entregas_iguales_con_ids_distintos_se_acumulan(self):
        primera = EntradaPrevista('arroz', FECHAS[0], Decimal('.15'), 'g', entrada_id='a')
        segunda = replace(primera, entrada_id='b')
        r = calcular_balance(self.recetario, plan_sintetico(), escenario_sintetico(entradas=(primera,segunda)), FECHAS)
        self.assertEqual(r.saldos[0].saldo, 0)

    def test_revision_recupera_entradas_y_conserva_antecedentes_sin_sobrescribir(self):
        original = self.calcular()
        borrador = recuperar_escenario(self.repo, original['ejecucion_id'])
        nuevo = replace(borrador, version='2', existencias=escenario_sintetico('1').existencias)
        revision = self.calcular(nuevo, ejecucion_previa_id=original['ejecucion_id'])
        self.assertNotEqual(revision['ejecucion_id'], original['ejecucion_id'])
        self.assertEqual(revision['contexto']['revision']['ejecucion_previa_id'], original['ejecucion_id'])
        self.assertEqual(revision['contexto']['revision']['escenario_previo_id'], original['resultado']['escenario_id'])
        self.assertEqual(self.repo.recuperar(original['ejecucion_id']), original)
        self.assertEqual(len(self.repo.listar()), 2)
        actualizar_modelo(self.base)

    def test_antecedente_ajeno_o_horizonte_diferente_bloquean_la_revision(self):
        original = self.calcular()
        for previo, receta in (('inexistente', self.recetario),
                              (original['ejecucion_id'], replace(self.recetario, sha256='b'*64))):
            with self.subTest(previo=previo), self.assertRaises((ValueError, LookupError)):
                ejecutar_balance(self.repo, receta, plan_sintetico(), escenario_sintetico(), FECHAS,
                                 ejecucion_previa_id=previo)
        self.assertEqual(len(self.repo.listar()), 1)

    def test_revision_sin_cambios_tambien_tiene_identidad_y_vinculo_propios(self):
        original = self.calcular()
        segunda = self.calcular(ejecucion_previa_id=original['ejecucion_id'])
        self.assertNotEqual(original['resultado']['escenario_id'], segunda['resultado']['escenario_id'])
        actualizar_modelo(self.base)
