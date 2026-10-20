import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from planificacion.cli import main, recurso_json
from planificacion.entradas import CANTIDAD, FECHA, LOCAL, PRODUCTO
from test_entradas import csv_sintetico, fila


class CLIPlanificacionTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.base = self.raiz / "ventas.sqlite3"
        self.manifiesto = self.raiz / "manifiesto.json"
        self.escenario = self.raiz / "escenario.json"
        seleccion = recurso_json("protocolo_tp3_v1.json")["seleccion"]
        self.filas = [fila(**{FECHA: fecha, LOCAL: seleccion["local_original"],
                              PRODUCTO: p["producto_original"], CANTIDAD: str(n if fecha == "2025-10-31" else 999)})
                      for n, p in enumerate(seleccion["productos"], 1)
                      for fecha in ("2025-10-31", "2025-11-01")]
        receta = recurso_json("recetario_modelado_v1.json")
        modelo = {"tipo": "sintetico", "nombre": "Plan de prueba", "version": "1",
                  "existencias": [{"insumo_id": i["ingrediente_id"], "cantidad": 0, "unidad": i["unidad"]}
                                  for i in receta["ingredientes"] if i["control_stock"]], "entradas": []}
        self.escenario.write_text(json.dumps(modelo), encoding="utf-8")

    def importar(self):
        raw = csv_sintetico(self.filas)
        (self.raiz / "prueba.csv").write_bytes(raw)
        m = {"archivos_csv": [{"archivo": "prueba.csv", "anio_publicado": 2025,
             "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "codificacion": "cp949",
             "filas": len(self.filas), "fechas_distintas": 2, "fecha_min": "2025-10-31", "fecha_max": "2025-11-01",
             "productos": 7, "cantidad_total": sum(int(r[CANTIDAD]) for r in self.filas),
             "locales": [self.filas[0][LOCAL]], "faltantes": {"producto_ingles_fuente": len(self.filas)}}]}
        self.manifiesto.write_text(json.dumps(m), encoding="utf-8")
        codigo, resultado, errores = self.ejecutar(["importar-ventas", "--directorio", str(self.raiz),
                "--manifiesto", str(self.manifiesto), "--base", str(self.base)])
        self.assertEqual((codigo, errores), (0, ""))
        return resultado["importacion_id"]

    def ejecutar(self, args):
        salida, errores = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(errores):
            codigo = main(args)
        return codigo, json.loads(salida.getvalue()) if salida.getvalue() else None, errores.getvalue()

    def planificar(self, identidad):
        return self.ejecutar(["planificar", "--base", str(self.base), "--importacion", identidad,
            "--origen", "2025-10-31", "--metodo", "persistencia", "--escenario", str(self.escenario)])

    def test_recorrido_real_con_adaptadores_y_sin_lectura_del_futuro(self):
        identidad = self.importar()
        codigo, resultado, errores = self.planificar(identidad)
        self.assertEqual((codigo, errores), (0, ""))
        self.assertEqual(resultado["tipo"], "planificacion")
        self.assertEqual(resultado["contexto"]["metodo"], "persistencia")
        self.assertEqual(len(resultado["entradas"]["plan"]), 49)
        p01 = [p for p in resultado["entradas"]["plan"] if p["producto_id"] == "P01"]
        self.assertEqual([p["cantidad"] for p in p01], ["1"] * 7)
        for serie in resultado["contexto"]["historico"]:
            self.assertLessEqual(max(d["fecha"] for d in serie["datos_disponibles"]), "2025-10-31")

    def test_origen_incompleto_no_guarda_ejecucion_parcial(self):
        self.filas = [f for n, f in enumerate(self.filas) if n != 12]
        identidad = self.importar()
        codigo, resultado, errores = self.planificar(identidad)
        self.assertEqual(codigo, 2)
        self.assertIsNone(resultado)
        self.assertIn("observación", errores)

    def test_recalculo_recuperable_conserva_configuracion_y_entrada(self):
        identidad = self.importar()
        _, uno, _ = self.planificar(identidad)
        _, dos, _ = self.planificar(identidad)
        self.assertNotEqual(uno["ejecucion_id"], dos["ejecucion_id"])
        self.assertEqual(uno["resultado"], dos["resultado"])
        _, recuperado, _ = self.ejecutar(["ver-ejecucion", "--base", str(self.base),
                                          "--ejecucion", uno["ejecucion_id"]])
        self.assertEqual(recuperado["contexto"], uno["contexto"])

    def test_importacion_desconocida_no_aplica_otra_automaticamente(self):
        self.importar()
        codigo, resultado, errores = self.planificar("inexistente")
        self.assertEqual(codigo, 2)
        self.assertIsNone(resultado)
        self.assertIn("catálogo", errores)
