import os
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from planificacion.infraestructura.sqlite_ejecuciones import SQLiteEjecuciones
from soporte_experimentos import importacion_sintetica

APP = Path(__file__).resolve().parents[1] / "app.py"


class InterfazTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.base = self.raiz / "prototipo.sqlite3"
        entorno = patch.dict(os.environ, {"TFG_BASE": str(self.base)})
        entorno.start()
        self.addCleanup(entorno.stop)

    def app(self):
        return AppTest.from_file(APP, default_timeout=30).run()

    def test_inicio_sin_base_no_crea_datos_y_explica_como_importar(self):
        app = self.app()
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Planificación gastronómica")
        self.assertFalse(self.base.exists())
        app.radio(key="pagina").set_value("Ventas").run()
        self.assertTrue(app.info)

    def test_consulta_muestra_ausencias_sin_convertirlas_en_cero(self):
        importacion_sintetica(self.raiz)
        app = self.app()
        app.radio(key="pagina").set_value("Ventas").run()
        app.button(key="consultar").click().run()
        self.assertFalse(app.exception)
        tabla = app.dataframe[0].value
        self.assertTrue(tabla["cantidad"].isna().any())
        self.assertEqual(tabla["cantidad"].dropna().tolist(), [1])

    def test_plan_completo_se_guarda_y_origen_ausente_no_crea_otro(self):
        importacion_sintetica(self.raiz)
        app = self.app()
        app.radio(key="pagina").set_value("Planificación").run()
        app.button(key="planificar").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        ejecuciones = SQLiteEjecuciones(self.base).listar()
        self.assertEqual(len(ejecuciones), 1)
        resultado = SQLiteEjecuciones(self.base).recuperar(ejecuciones[0]["id"])
        self.assertEqual(len(resultado["entradas"]["plan"]), 49)
        app.date_input(key="origen").set_value(__import__('datetime').date(2025, 10, 31)).run()
        app.button(key="planificar").click().run()
        self.assertTrue(app.error)
        self.assertEqual(len(SQLiteEjecuciones(self.base).listar()), 1)
        app.radio(key="pagina").set_value("Historial").run()
        self.assertFalse(app.exception)
        self.assertTrue(app.download_button)

    def test_importacion_invalida_se_rechaza_antes_de_crear_la_base(self):
        app = self.app()
        app.text_input(key="originales").set_value(str(self.raiz)).run()
        app.button(key="importar").click().run()
        self.assertTrue(app.error)
        self.assertFalse(self.base.exists())

    def test_recupera_escenario_editable_y_guarda_revision_vinculada(self):
        importacion_sintetica(self.raiz)
        app = self.app()
        app.radio(key='pagina').set_value('Planificación').run()
        app.button(key='planificar').click().run()
        original = SQLiteEjecuciones(self.base).listar()[0]['id']
        app.selectbox(key='revision').set_value(original).run()
        self.assertTrue(app.date_input(key='origen').disabled)
        app.button(key='planificar').click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        filas = SQLiteEjecuciones(self.base).listar()
        self.assertEqual(len(filas), 2)
        segunda = SQLiteEjecuciones(self.base).recuperar(filas[-1]['id'])
        self.assertEqual(segunda['contexto']['revision']['ejecucion_previa_id'], original)

    def test_un_proceso_de_modelos_no_arranca_la_pantalla(self):
        with patch("planificacion.presentacion.web.mostrar_app") as mostrar:
            runpy.run_path(str(APP), run_name="__mp_main__")
        mostrar.assert_not_called()
