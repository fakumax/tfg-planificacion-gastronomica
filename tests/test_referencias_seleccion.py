import copy
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from planificacion.aplicacion.experimento import ejecutar_seleccion
from planificacion.aplicacion.planificacion import planificar
from planificacion.aplicacion.pronosticos import consultar_pronostico
from planificacion.configuracion import recetario_configurado, recurso_json
from planificacion.dominio.balance import Escenario, Existencia
from planificacion.dominio.parametros import CONFIGURACION_PREFIJADA
from planificacion.dominio.pronosticos import Estimacion, Persistencia
from planificacion.infraestructura.sqlite_ejecuciones import SQLiteEjecuciones
from planificacion.infraestructura.sqlite_ventas import SQLiteVentas
from soporte_experimentos import importacion_sintetica
from test_experimento import ejecutor_sintetico


class MetodoSintetico:
    nombre = 'random_forest'

    def __init__(self, parametros=None):
        self.parametros = dict(CONFIGURACION_PREFIJADA if parametros is None else parametros)

    def estimar(self, producto_id, serie, origen, horizonte):
        return Estimacion(Decimal(1), {**self.parametros,
            'seleccion': 'prefijada_validacion_insuficiente'}, 60)


class ReferenciasSeleccionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.base, self.importacion = importacion_sintetica(self.raiz)
        self.ventas = SQLiteVentas(self.base)
        self.repo = SQLiteEjecuciones(self.base)
        self.meta = {'entorno': {'python': 'prueba'},
                     'codigo': {'huella_nucleo_numerico': 'a' * 64}}
        self.seleccion = ejecutar_seleccion(self.ventas, self.repo, self.importacion,
            recurso_json('protocolo_tp3_v1.json'), ejecutor_sintetico, metadatos=self.meta)
        self.referencia = {'seleccion_id': self.seleccion['ejecucion_id'],
            'huella_contenido': self.seleccion['huella_contenido'], **self.meta}
        self.origen = date(2025, 11, 1)

    def consultar(self, referencia=None, metodo=None, metadatos=None, importacion=None):
        return consultar_pronostico(self.ventas, self.repo, metodo or MetodoSintetico(),
            importacion or self.importacion, 'P01', self.origen,
            referencia_seleccion=referencia,
            metadatos=self.meta if metadatos is None else metadatos)

    def rechaza_sin_guardar(self, accion):
        anteriores = self.repo.listar()
        with self.assertRaises(ValueError):
            accion()
        self.assertEqual(self.repo.listar(), anteriores)

    def test_consulta_referencia_cerrada_valida_y_conserva_su_identidad(self):
        registro = self.consultar(self.referencia)
        self.assertEqual(registro['contexto']['seleccion_modelos'], self.referencia)
        self.assertTrue(registro['resultado']['completo'])

    def test_random_forest_sin_referencia_no_guarda_consulta(self):
        self.rechaza_sin_guardar(lambda: self.consultar())

    def test_referencia_inexistente_no_guarda_consulta(self):
        referencia = {**self.referencia, 'seleccion_id': 'no_existe'}
        self.rechaza_sin_guardar(lambda: self.consultar(referencia))

    def test_huella_distinta_no_guarda_consulta(self):
        referencia = {**self.referencia, 'huella_contenido': '0' * 64}
        self.rechaza_sin_guardar(lambda: self.consultar(referencia))

    def test_persistencia_no_admite_una_referencia_de_random_forest(self):
        self.rechaza_sin_guardar(lambda: self.consultar(self.referencia, Persistencia()))

    def test_planificacion_no_admite_referencia_ajena_al_metodo(self):
        recetario = recetario_configurado()
        escenario = Escenario('Sintético', '1', tuple(Existencia(i.insumo_id, Decimal(0), i.unidad)
            for i in recetario.insumos if i.control_stock), ())
        self.rechaza_sin_guardar(lambda: planificar(self.ventas, self.repo, Persistencia(), recetario,
            self.importacion, self.origen, escenario, referencia_seleccion=self.referencia,
            metadatos=self.meta))

    def test_un_registro_de_otro_tipo_no_es_una_seleccion(self):
        identidad = self.repo.guardar({'tipo': 'balance', 'version_codigo': 'prueba',
                                       'entradas': {}, 'resultado': {}})
        registro = self.repo.recuperar(identidad)
        referencia = {**self.referencia, 'seleccion_id': identidad,
                      'huella_contenido': registro['huella_contenido']}
        self.rechaza_sin_guardar(lambda: self.consultar(referencia))

    def test_importacion_diferente_no_reutiliza_la_seleccion(self):
        _, otra = importacion_sintetica(self.raiz, multiplicador=2)
        self.rechaza_sin_guardar(lambda: self.consultar(self.referencia, importacion=otra))

    def test_entorno_y_nucleo_diferentes_no_reutilizan_la_seleccion(self):
        for campo, valor in [('entorno', {'python': 'otro'}),
                              ('codigo', {'huella_nucleo_numerico': 'b' * 64})]:
            with self.subTest(campo=campo):
                self.rechaza_sin_guardar(lambda: self.consultar(self.referencia,
                    metadatos={**self.meta, campo: valor}))

    def test_pronostico_con_parametros_distintos_no_se_atribuye_a_la_seleccion(self):
        metodo = MetodoSintetico({**CONFIGURACION_PREFIJADA, 'max_depth': 10})
        self.rechaza_sin_guardar(lambda: self.consultar(self.referencia, metodo))

    def test_guardado_directo_no_admite_una_referencia_alterada(self):
        registro = self.consultar(self.referencia)
        contenido = {k: copy.deepcopy(registro[k]) for k in
                     ('tipo', 'version_codigo', 'contexto', 'entradas', 'resultado')}
        contenido['contexto']['seleccion_modelos']['huella_contenido'] = '0' * 64
        self.rechaza_sin_guardar(lambda: self.repo.guardar(contenido))

    def test_seleccion_incompleta_no_respalda_una_consulta(self):
        contenido = {k: copy.deepcopy(self.seleccion[k]) for k in
                     ('tipo', 'version_codigo', 'contexto', 'entradas', 'resultado')}
        contenido['resultado']['productos'].pop()
        identidad = self.repo.guardar(contenido)
        guardada = self.repo.recuperar(identidad)
        referencia = {**self.referencia, 'seleccion_id': identidad,
                      'huella_contenido': guardada['huella_contenido']}
        self.rechaza_sin_guardar(lambda: self.consultar(referencia))
