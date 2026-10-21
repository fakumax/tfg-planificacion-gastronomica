import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from planificacion.aplicacion.balance import ejecutar_balance
from planificacion.dominio.balance import calcular_balance
from planificacion.dominio.recetas import interpretar_recetario, recetarios_compatibles
from planificacion.dominio.serializacion import normalizar
from planificacion.infraestructura.modelo_relacional import actualizar_modelo
from planificacion.infraestructura.respaldos import verificar_base
from planificacion.infraestructura.sqlite_ejecuciones import SQLiteEjecuciones
from test_balance import FECHAS, escenario_sintetico, plan_sintetico
from test_recetas import modelo_sintetico


def recetario_con_estado():
    modelo = modelo_sintetico()
    modelo['ingredientes'][0]['estado_stock'] = 'Seco, limpio'
    modelo['ingredientes'][1]['estado_stock'] = 'Potable'
    return interpretar_recetario(modelo, 'a' * 64)


class EstadoInsumosTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / 'base.sqlite3'
        self.repo = SQLiteEjecuciones(self.base)

    def guardar(self, **opciones):
        return ejecutar_balance(self.repo, recetario_con_estado(), plan_sintetico(),
            escenario_sintetico(), FECHAS, **opciones)

    def legado(self):
        recetario = recetario_con_estado()
        guardado = normalizar(recetario)
        for insumo in guardado['insumos']:
            insumo.pop('estado_stock', None)
        identidad = self.repo.guardar({'tipo': 'balance', 'version_codigo': '0.7.0',
            'contexto': {'metodo': 'plan_manual', 'naturaleza_plan': 'modelado'},
            'entradas': {'recetario': guardado, 'plan': normalizar(plan_sintetico()),
                         'escenario': normalizar(escenario_sintetico()), 'fechas': normalizar(FECHAS)},
            'resultado': normalizar(calcular_balance(recetario, plan_sintetico(), escenario_sintetico(), FECHAS))})
        # Base de versión 2: el estado todavía no se conservaba por recetario.
        with closing(sqlite3.connect(self.base)) as c, c:
            c.execute('DROP TABLE IF EXISTS EstadoInsumo')
            c.execute('PRAGMA user_version=2')
        return self.repo.recuperar(identidad)

    def test_interpretacion_conserva_el_estado_de_la_misma_ficha(self):
        arroz = normalizar(recetario_con_estado())['insumos'][0]
        self.assertEqual(arroz.get('estado_stock'), 'Seco, limpio')

    def test_estado_presente_no_puede_ser_texto_vacio_o_invalido(self):
        for valor in ('', '   ', 17):
            with self.subTest(valor=valor):
                modelo = modelo_sintetico()
                modelo['ingredientes'][0]['estado_stock'] = valor
                with self.assertRaises(ValueError):
                    interpretar_recetario(modelo, 'a' * 64)

    def test_nueva_ejecucion_conserva_estado_en_instantanea_y_proyeccion(self):
        registro = self.guardar()
        self.assertEqual(registro['entradas']['recetario']['insumos'][0].get('estado_stock'), 'Seco, limpio')
        with closing(sqlite3.connect(self.base)) as c:
            self.assertEqual(c.execute("SELECT estado_stock FROM EstadoInsumo WHERE id_insumo='arroz'").fetchall(),
                             [('Seco, limpio',)])
        verificar_base(self.base)

    def test_actualizar_base_anterior_no_reescribe_ni_infiere_estados_historicos(self):
        original = self.legado()
        verificar_base(self.base)
        with closing(sqlite3.connect(self.base)) as c:
            anteriores = c.execute('SELECT * FROM ejecuciones').fetchall()
        actualizar_modelo(self.base)
        self.assertEqual(self.repo.recuperar(original['ejecucion_id']), original)
        with closing(sqlite3.connect(self.base)) as c:
            self.assertEqual(c.execute('SELECT * FROM ejecuciones').fetchall(), anteriores)
            self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0], 3)
            self.assertEqual(c.execute("SELECT estado_stock FROM EstadoInsumo WHERE id_insumo='arroz'").fetchall(), [(None,)])
        verificar_base(self.base)

    def test_revision_de_un_registro_anterior_conserva_el_estado_de_cada_version(self):
        original = self.legado()
        actualizar_modelo(self.base)
        revision = self.guardar(ejecucion_previa_id=original['ejecucion_id'])
        self.assertEqual(revision['entradas']['recetario']['insumos'][0]['estado_stock'], 'Seco, limpio')
        self.assertNotIn('estado_stock', self.repo.recuperar(original['ejecucion_id'])['entradas']['recetario']['insumos'][0])
        with closing(sqlite3.connect(self.base)) as c:
            estados = c.execute("SELECT estado_stock FROM EstadoInsumo WHERE id_insumo='arroz'").fetchall()
            self.assertCountEqual(estados, [(None,), ('Seco, limpio',)])
        verificar_base(self.base)

    def test_compatibilidad_no_permite_cambiar_un_estado_ya_registrado_ni_la_receta(self):
        guardado = normalizar(recetario_con_estado())
        for cambio in ('estado', 'cantidad', 'huella'):
            actual = normalizar(recetario_con_estado())
            if cambio == 'estado':
                actual['insumos'][0]['estado_stock'] = 'Otro estado'
            elif cambio == 'cantidad':
                actual['recetas'][0]['lineas'][0]['cantidad'] = '5'
            else:
                actual['sha256'] = 'b' * 64
            with self.subTest(cambio=cambio):
                self.assertFalse(recetarios_compatibles(guardado, actual))

    def test_control_detecta_estado_relacional_alterado(self):
        self.guardar()
        with closing(sqlite3.connect(self.base)) as c, c:
            c.execute("UPDATE EstadoInsumo SET estado_stock='Otro estado' WHERE id_insumo='arroz'")
        with self.assertRaisesRegex(ValueError, 'integridad relacional.*EstadoInsumo'):
            verificar_base(self.base)
