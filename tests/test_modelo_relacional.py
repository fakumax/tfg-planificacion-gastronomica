import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from planificacion.aplicacion.balance import ejecutar_balance
from planificacion.configuracion import recetario_configurado
from planificacion.infraestructura.modelo_relacional import actualizar_modelo
from planificacion.infraestructura.sqlite_ejecuciones import SQLiteEjecuciones
from planificacion.infraestructura.sqlite_ventas import SQLiteVentas
from planificacion.infraestructura.respaldos import verificar_base
from soporte_experimentos import importacion_sintetica
from test_balance import FECHAS, escenario_sintetico, plan_sintetico
from test_recetas import modelo_sintetico
from planificacion.dominio.recetas import interpretar_recetario
from planificacion.dominio.evaluacion import metricas
from planificacion.aplicacion.pronosticos import consultar_pronostico
from planificacion.dominio.pronosticos import Persistencia
from datetime import date


class ModeloRelacionalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.base, self.importacion = importacion_sintetica(self.raiz, legado=True)
        self.repo = SQLiteEjecuciones(self.base)

    def guardar_balance(self):
        return ejecutar_balance(self.repo, interpretar_recetario(modelo_sintetico(), 'a' * 64),
                                plan_sintetico(), escenario_sintetico(), FECHAS)

    def test_actualizacion_conserva_registros_y_huellas_y_es_idempotente(self):
        anterior = self.guardar_balance()
        with closing(sqlite3.connect(self.base)) as c:
            raw = c.execute('SELECT * FROM ejecuciones').fetchall()
        actualizar_modelo(self.base)
        actualizar_modelo(self.base)
        self.assertEqual(self.repo.recuperar(anterior['ejecucion_id']), anterior)
        self.assertEqual(SQLiteVentas(self.base).recuperar_lote(self.importacion).identificador, self.importacion)
        with closing(sqlite3.connect(self.base)) as c:
            self.assertEqual(c.execute('SELECT * FROM ejecuciones').fetchall(), raw)
            self.assertEqual(c.execute('SELECT count(*) FROM Preparacion').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM VentaDiaria').fetchone()[0], 2555)
            self.assertEqual(c.execute('SELECT count(*) FROM Ejecucion').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM BalanceDiario').fetchone()[0], 14)
            self.assertEqual(c.execute('SELECT primera_fecha FROM Alerta').fetchone()[0], '2025-01-01')
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])
            self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0], 3)

    def test_error_de_integridad_revierte_toda_la_actualizacion(self):
        self.guardar_balance()
        with closing(sqlite3.connect(self.base)) as c, c:
            c.execute("UPDATE ejecuciones SET huella_contenido = ?", ('b' * 64,))
        with self.assertRaisesRegex(ValueError, 'integridad'):
            actualizar_modelo(self.base)
        with closing(sqlite3.connect(self.base)) as c:
            self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0], 1)
            self.assertFalse(c.execute("SELECT name FROM sqlite_master WHERE name='Escenario'").fetchall())

    def test_restricciones_impiden_huerfanos_y_alerta_no_usa_agua(self):
        self.guardar_balance()
        actualizar_modelo(self.base)
        with closing(sqlite3.connect(self.base)) as c:
            c.execute('PRAGMA foreign_keys=ON')
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("INSERT INTO Existencia VALUES ('inexistente', 'arroz', '0', 'g')")
            self.assertEqual(c.execute('SELECT id_insumo FROM Alerta').fetchall(), [('arroz',)])
            self.assertIsNone(c.execute("SELECT saldo_final FROM BalanceDiario WHERE id_insumo='agua' LIMIT 1").fetchone()[0])

    def test_escritura_posterior_actualiza_ambas_representaciones(self):
        actualizar_modelo(self.base)
        registro = self.guardar_balance()
        with closing(sqlite3.connect(self.base)) as c:
            self.assertEqual(c.execute('SELECT id_ejecucion FROM Ejecucion').fetchall(), [(registro['ejecucion_id'],)])
            self.assertEqual(c.execute('SELECT count(*) FROM Alerta').fetchone()[0], 1)

    def test_control_detecta_cambio_relacional_aunque_las_instantaneas_no_cambien(self):
        self.guardar_balance()
        actualizar_modelo(self.base)
        verificar_base(self.base)
        with closing(sqlite3.connect(self.base)) as c, c:
            c.execute("UPDATE BalanceDiario SET saldo_final='10' WHERE saldo_final IS NOT NULL")
        with self.assertRaisesRegex(ValueError, 'integridad relacional'):
            verificar_base(self.base)

    def test_control_rechaza_vista_de_alertas_vacia_con_las_mismas_columnas(self):
        self.guardar_balance()
        actualizar_modelo(self.base)
        with closing(sqlite3.connect(self.base)) as c, c:
            c.execute('DROP VIEW Alerta')
            c.execute('''CREATE VIEW Alerta AS
                SELECT id_ejecucion,id_insumo,fecha AS primera_fecha,
                       0 AS deficit_primera_fecha,unidad
                FROM BalanceDiario WHERE 0''')
        with self.assertRaisesRegex(ValueError, 'integridad relacional.*Alerta'):
            verificar_base(self.base)

    def test_control_rechaza_vista_ausente_aunque_no_haya_ejecuciones(self):
        actualizar_modelo(self.base)
        with closing(sqlite3.connect(self.base)) as c, c:
            c.execute('DROP VIEW Alerta')
        with self.assertRaisesRegex(ValueError, 'integridad relacional.*Alerta'):
            verificar_base(self.base)

    def test_base_nueva_guarda_el_modelo_completo_desde_la_primera_importacion(self):
        nueva = self.raiz / 'nueva'
        nueva.mkdir()
        base, identidad = importacion_sintetica(nueva)
        with closing(sqlite3.connect(base)) as c:
            self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0], 3)
            self.assertEqual(c.execute('SELECT id_preparacion FROM Preparacion').fetchall(), [(identidad,)])

    def test_guarda_candidatas_y_metricas_de_validacion_con_sus_configuraciones(self):
        actualizar_modelo(self.base)
        parametros = {'n_estimators':100, 'max_depth':5, 'min_samples_leaf':2, 'random_state':42}
        candidatas = [{'parametros':{**parametros,'n_estimators':n,'max_depth':d},
                       'predicciones':[], 'metricas':[{'horizonte':1, **metricas([])}]}
                      for n in (100,300) for d in (5,10)]
        self.repo.guardar({'tipo':'seleccion_modelos', 'version_codigo':'prueba_sintetica',
            'contexto':{'importacion_id':self.importacion}, 'entradas':{},
            'resultado':{'productos':[{'producto_id':'P01','parametros':parametros,
                                       'candidatas':candidatas,'casos':[]}]}})
        with closing(sqlite3.connect(self.base)) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM Configuracion').fetchone()[0], 4)
            self.assertEqual(c.execute("SELECT count(*) FROM Evaluacion WHERE tipo_muestra='validacion'").fetchone()[0], 4)

    def test_consulta_recuperada_identifica_preparacion_y_protocolo_de_su_importacion(self):
        registro = consultar_pronostico(SQLiteVentas(self.base), self.repo, Persistencia(),
            self.importacion,'P01',date(2025,11,1))
        self.assertEqual(registro['procedencia_preparacion']['id'], self.importacion)
        self.assertEqual(registro['procedencia_preparacion']['version_preparacion'], 'preparacion_e2_v1')
