import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from planificacion.infraestructura.sqlite_ejecuciones import SQLiteEjecuciones
from soporte_experimentos import importacion_sintetica


class CLIExperimentoTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.base, self.identidad = importacion_sintetica(Path(self.temporal.name))

    def comando(self, *args):
        return subprocess.run([sys.executable, "-X", "utf8", "-m", "planificacion", *args,
            "--base", str(self.base), "--importacion", self.identidad, "--trabajadores", "2"],
            capture_output=True, text=True, encoding="utf-8", timeout=90)

    def test_modulo_en_procesos_separados_guarda_seleccion_y_prueba(self):
        seleccion = self.comando("seleccionar-modelos")
        self.assertEqual(seleccion.returncode, 0, seleccion.stderr)
        s = json.loads(seleccion.stdout)
        prueba = self.comando("evaluar-modelos", "--seleccion", s["ejecucion_id"])
        self.assertEqual(prueba.returncode, 0, prueba.stderr)
        p = json.loads(prueba.stdout)
        registro = SQLiteEjecuciones(self.base).recuperar(p["ejecucion_id"])
        self.assertEqual(registro["entradas"]["seleccion_id"], s["ejecucion_id"])
        self.assertEqual(len(registro["resultado"]["productos"]), 7)
        self.assertIn("bibliotecas", registro["contexto"]["entorno"])
        self.assertIn("huella_nucleo_numerico", registro["contexto"]["codigo"])
        self.assertTrue(all(m["n_predicciones"] == 0 for r in registro["resultado"]["productos"] for m in r["metricas"]))
        self.assertIn("7/7", prueba.stderr)

    def test_seleccion_inexistente_devuelve_error_y_no_inventa_otra(self):
        resultado = self.comando("evaluar-modelos", "--seleccion", "inexistente")
        self.assertEqual(resultado.returncode, 2)
        self.assertFalse(resultado.stdout)
        self.assertIn("No se completó", resultado.stderr)
