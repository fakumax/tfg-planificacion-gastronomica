import contextlib
import io
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from planificacion.cli import main, recurso_json


class CLIBalanceTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.base = self.raiz / "balance.sqlite3"
        self.plan = self.raiz / "plan.json"
        self.escenario = self.raiz / "escenario.json"
        recetas = recurso_json("recetario_modelado_v1.json")
        cantidades = [{"producto_id": r["producto_id"], "fecha": (date(2025, 11, 1) + timedelta(days=n)).isoformat(),
                        "cantidad": 10 if r["producto_id"] == "P01" and n == 0 else 0}
                       for r in recetas["recetas"] for n in range(7)]
        self.modelo_plan = {"tipo": "modelado", "desde": "2025-11-01", "cantidades": cantidades}
        self.modelo_escenario = {"tipo": "sintetico", "nombre": "Caso de prueba", "version": "1",
            "existencias": [{"insumo_id": i["ingrediente_id"], "cantidad": 0, "unidad": i["unidad"]}
                            for i in recetas["ingredientes"] if i["control_stock"]], "entradas": []}
        self.escribir()

    def escribir(self):
        self.plan.write_text(json.dumps(self.modelo_plan), encoding="utf-8")
        self.escenario.write_text(json.dumps(self.modelo_escenario), encoding="utf-8")

    def ejecutar(self, args):
        salida, errores = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(errores):
            codigo = main(args)
        return codigo, json.loads(salida.getvalue()) if salida.getvalue() else None, errores.getvalue()

    def calcular(self, extra=()):
        return self.ejecutar(["calcular-balance", "--base", str(self.base), "--plan", str(self.plan),
                              "--escenario", str(self.escenario), *extra])

    def test_balance_manual_se_conserva_y_recupera_con_alerta_conocida(self):
        codigo, resultado, errores = self.calcular()
        self.assertEqual((codigo, errores), (0, ""))
        alerta = next(a for a in resultado["resultado"]["alertas"] if a["insumo_id"] == "cerdo")
        self.assertEqual(alerta["deficit_inicial"], "600")
        self.assertEqual(resultado["contexto"]["metodo"], "plan_manual")
        codigo, recuperado, _ = self.ejecutar(["ver-ejecucion", "--base", str(self.base),
                                               "--ejecucion", resultado["ejecucion_id"]])
        self.assertEqual(codigo, 0)
        self.assertEqual(recuperado, resultado)

    def test_recalculo_conserva_dos_ejecuciones(self):
        _, uno, _ = self.calcular()
        _, dos, _ = self.calcular()
        _, listado, _ = self.ejecutar(["listar-ejecuciones", "--base", str(self.base)])
        self.assertNotEqual(uno["ejecucion_id"], dos["ejecucion_id"])
        self.assertEqual(len(listado["ejecuciones"]), 2)

    def test_plan_incompleto_no_crea_base(self):
        self.modelo_plan["cantidades"].pop()
        self.escribir()
        codigo, resultado, errores = self.calcular()
        self.assertEqual(codigo, 2)
        self.assertIsNone(resultado)
        self.assertIn("Cobertura", errores)
        self.assertFalse(self.base.exists())

    def test_escenario_sin_identificacion_sintetica_se_rechaza(self):
        self.modelo_escenario["tipo"] = "observado"
        self.escribir()
        codigo, resultado, _ = self.calcular()
        self.assertEqual(codigo, 2)
        self.assertIsNone(resultado)
        self.assertFalse(self.base.exists())

    def test_recetario_modificado_se_rechaza_sin_escribir_base(self):
        ruta = self.raiz / "otro.json"
        ruta.write_text("{}", encoding="utf-8")
        codigo, resultado, errores = self.calcular(["--recetario", str(ruta)])
        self.assertEqual(codigo, 2)
        self.assertIsNone(resultado)
        self.assertIn("huella", errores)
        self.assertFalse(self.base.exists())
