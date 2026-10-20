import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from planificacion.configuracion import recetario_configurado
from planificacion.infraestructura.sqlite_ejecuciones import SQLiteEjecuciones
from planificacion.infraestructura.catalogo_base import estado_base
from planificacion.presentacion.api import crear_app
from soporte_experimentos import importacion_sintetica


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.base, self.identidad = importacion_sintetica(self.raiz)
        self.cliente = TestClient(crear_app(self.base))
        self.addCleanup(self.cliente.close)

    def test_estado_y_consultas_no_escriben_ejecuciones(self):
        estado = self.cliente.get('/api/estado').json()
        self.assertEqual(len(estado['importaciones']), 1)
        consulta = self.cliente.get('/api/ventas', params={
            'importacion': self.identidad, 'producto': 'P01', 'desde': '2025-11-01', 'hasta': '2025-11-03'})
        self.assertEqual(consulta.status_code, 200)
        self.assertEqual([d['cantidad'] for d in consulta.json()['diarias']], [1, None, None])
        self.assertEqual(consulta.json()['dias_sin_fila'], 2)
        self.assertEqual(estado_base(self.base)[1], [])

    def test_base_ausente_no_se_crea_y_recetas_identifican_el_estado(self):
        destino = self.raiz/'sin_crear.sqlite3'
        with TestClient(crear_app(destino)) as c:
            self.assertEqual(c.get('/api/estado').json()['importaciones'], [])
            receta = c.get('/api/recetas').json()
            cerdo = next(i for i in receta['ingredientes'] if i['ingrediente_id']=='cerdo')
            self.assertEqual(cerdo['estado_stock'], 'Cruda, limpia, sin hueso')
        self.assertFalse(destino.exists())

    def test_errores_y_fechas_invalidas_son_respuestas_controladas(self):
        self.assertEqual(self.cliente.get('/api/ejecuciones/no-existe').status_code, 404)
        r = self.cliente.get('/api/ventas', params={'importacion':self.identidad,
            'producto':'P01','desde':'fecha','hasta':'2025-11-02'})
        self.assertEqual(r.status_code, 422)
        self.assertIsInstance(r.json()['mensaje'], str)

    def cuerpo_plan(self):
        return {'importacion':self.identidad, 'origen':'2025-11-01','metodo':'persistencia',
            'nombre':'Escenario sintético de prueba','version':'1',
            'existencias':[{'insumo_id':i.insumo_id,'cantidad':'1109.99999999999999' if i.insumo_id=='cerdo' else '1000000',
                            'unidad':i.unidad} for i in recetario_configurado().insumos if i.control_stock],
            'entradas':[]}

    def test_plan_y_revision_preservan_decimales_y_antecedente(self):
        cuerpo = self.cuerpo_plan()
        r = self.cliente.post('/api/planes',json=cuerpo)
        self.assertEqual(r.status_code, 200, r.text)
        previo = r.json()
        self.assertEqual(next(e for e in previo['entradas']['escenario']['existencias']
            if e['insumo_id']=='cerdo')['cantidad'], '1109.99999999999999')
        cuerpo.update(ejecucion_previa_id=previo['ejecucion_id'],version='2')
        nueva = self.cliente.post('/api/planes',json=cuerpo)
        self.assertEqual(nueva.status_code, 200, nueva.text)
        self.assertEqual(nueva.json()['resultado']['saldos'], previo['resultado']['saldos'])
        self.assertEqual(nueva.json()['contexto']['revision']['ejecucion_previa_id'],previo['ejecucion_id'])

    def test_un_numero_json_no_sustituye_el_decimal_como_texto(self):
        cuerpo = self.cuerpo_plan()
        cuerpo['existencias'][0]['cantidad'] = 1.5
        self.assertEqual(self.cliente.post('/api/planes',json=cuerpo).status_code, 422)
        self.assertEqual(estado_base(self.base)[1], [])

    def test_plan_incompleto_y_seleccion_inexistente_no_guardan(self):
        cuerpo = self.cuerpo_plan()
        cuerpo['existencias'] = []
        self.assertEqual(self.cliente.post('/api/planes',json=cuerpo).status_code,400)
        cuerpo = self.cuerpo_plan()
        cuerpo.update(metodo='random_forest',seleccion_id='no-existe')
        self.assertEqual(self.cliente.post('/api/planes',json=cuerpo).status_code,404)
        self.assertEqual(estado_base(self.base)[1], [])

    def test_origen_web_ajeno_no_puede_provocar_escrituras(self):
        r = self.cliente.post('/api/planes',json=self.cuerpo_plan(),headers={'Origin':'https://ajeno.example'})
        self.assertEqual(r.status_code,403)
        self.assertEqual(estado_base(self.base)[1], [])

    def test_consulta_individual_incompleta_conserva_causas(self):
        r = self.cliente.post('/api/pronosticos',json={'importacion':self.identidad,
            'producto':'P01','origen':'2025-10-31','metodo':'persistencia'})
        self.assertEqual(r.status_code,200,r.text)
        self.assertFalse(r.json()['resultado']['completo'])
        self.assertTrue(all(p['cantidad'] is None and p['causa'] for p in r.json()['resultado']['pronosticos']))

    def test_disponibilidad_conjunta_no_entrena_ni_guarda(self):
        r = self.cliente.get('/api/disponibilidad',params={'importacion':self.identidad,'origen':'2025-11-01'})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(len(r.json()['productos']),7)
        self.assertTrue(r.json()['metodos']['persistencia']['completo'])
        self.assertFalse(r.json()['metodos']['random_forest']['completo'])
        self.assertEqual(estado_base(self.base)[1], [])
