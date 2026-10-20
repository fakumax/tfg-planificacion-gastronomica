import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from planificacion.aplicacion.balance import ejecutar_balance
from planificacion.infraestructura.sqlite_ejecuciones import SQLiteEjecuciones
from planificacion.dominio.recetas import interpretar_recetario
from test_balance import FECHAS, escenario_sintetico, plan_sintetico
from test_recetas import modelo_sintetico


class EjecucionesTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.base = Path(self.temporal.name) / "ejecuciones.sqlite3"
        self.repo = SQLiteEjecuciones(self.base)
        self.recetario = interpretar_recetario(modelo_sintetico(), "a" * 64)

    def ejecutar(self, escenario=None):
        return ejecutar_balance(self.repo, self.recetario, plan_sintetico(),
                                 escenario or escenario_sintetico(), FECHAS)

    def test_repetir_entradas_crea_dos_ejecuciones_con_mismos_calculos(self):
        uno, dos = self.ejecutar(), self.ejecutar()
        self.assertNotEqual(uno["ejecucion_id"], dos["ejecucion_id"])
        self.assertEqual(uno["huella_entrada"], dos["huella_entrada"])
        self.assertEqual(uno["resultado"], dos["resultado"])
        self.assertEqual(len(self.repo.listar()), 2)

    def test_cambiar_escenario_conserva_la_ejecucion_anterior(self):
        uno = self.ejecutar()
        dos = self.ejecutar(escenario_sintetico("1"))
        self.assertEqual(len(uno["resultado"]["alertas"]), 1)
        self.assertEqual(dos["resultado"]["alertas"], [])
        self.assertEqual(self.repo.recuperar(uno["ejecucion_id"]), uno)
        self.assertNotEqual(uno["huella_entrada"], dos["huella_entrada"])

    def test_nueva_instancia_recupera_cantidades_fechas_y_versiones(self):
        original = self.ejecutar()
        recuperado = SQLiteEjecuciones(self.base).recuperar(original["ejecucion_id"])
        self.assertEqual(recuperado["entradas"]["plan"][0]["fecha"], "2025-01-01")
        self.assertEqual(recuperado["resultado"]["saldos"][0]["saldo"], "-0.3")
        self.assertEqual(recuperado["entradas"]["escenario"]["tipo"], "sintetico")
        self.assertEqual(recuperado["entradas"]["recetario"]["sha256"], "a" * 64)

    def test_contenido_modificado_se_detecta_al_recuperar(self):
        original = self.ejecutar()
        with closing(sqlite3.connect(self.base)) as c, c:
            c.execute("UPDATE ejecuciones SET contenido_json = '{}' WHERE id = ?",
                      (original["ejecucion_id"],))
        with self.assertRaisesRegex(ValueError, "integridad"):
            self.repo.recuperar(original["ejecucion_id"])

    def test_balance_invalido_no_se_guarda_ni_crea_base(self):
        with self.assertRaises(ValueError):
            ejecutar_balance(self.repo, self.recetario, plan_sintetico()[:-1],
                              escenario_sintetico(), FECHAS)
        self.assertFalse(self.base.exists())

    def test_metadatos_cambiados_no_ocultan_diferencias_de_version_o_entrada(self):
        for campo, valor in (("version_codigo", "falsa"), ("huella_entrada", "b" * 64), ("tipo", "otro")):
            original = self.ejecutar()
            with closing(sqlite3.connect(self.base)) as c, c:
                c.execute(f"UPDATE ejecuciones SET {campo} = ? WHERE id = ?", (valor, original["ejecucion_id"]))
            with self.subTest(campo=campo), self.assertRaisesRegex(ValueError, "integridad"):
                self.repo.recuperar(original["ejecucion_id"])

    def test_lectura_ausente_no_crea_base(self):
        with self.assertRaises(FileNotFoundError):
            self.repo.listar()
        self.assertFalse(self.base.exists())

    def test_identidad_desconocida_no_se_interpreta_como_sql(self):
        self.ejecutar()
        with self.assertRaises(LookupError):
            self.repo.recuperar("' OR 1=1 --")

    def test_aplicacion_funciona_con_dependencia_en_memoria(self):
        class Memoria:
            def __init__(self): self.contenido = None
            def guardar(self, contenido): self.contenido = contenido; return "memoria"
            def recuperar(self, identidad): return {"ejecucion_id": identidad, **self.contenido}
        memoria = Memoria()
        resultado = ejecutar_balance(memoria, self.recetario, plan_sintetico(),
                                      escenario_sintetico(), FECHAS)
        self.assertEqual(resultado["ejecucion_id"], "memoria")
        self.assertEqual(memoria.contenido["tipo"], "balance")
