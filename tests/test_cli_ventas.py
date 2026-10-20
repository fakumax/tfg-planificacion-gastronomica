import contextlib
import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from planificacion.cli import main
from test_entradas import csv_sintetico, fila, manifiesto_sintetico
from test_preparacion import protocolo_sintetico


class CLIVentasTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.raw = csv_sintetico([fila()])
        self.original = self.raiz / "prueba.csv"
        self.original.write_bytes(self.raw)
        self.manifiesto = self.raiz / "manifiesto.json"
        self.manifiesto.write_text(json.dumps(manifiesto_sintetico(self.raw)), encoding="utf-8")
        self.base = self.raiz / "ventas.sqlite3"

    def ejecutar(self, argumentos):
        salida, errores = io.StringIO(), io.StringIO()
        with patch("planificacion.cli.recurso_json", return_value=protocolo_sintetico()), \
                contextlib.redirect_stdout(salida), contextlib.redirect_stderr(errores):
            codigo = main(argumentos)
        return codigo, json.loads(salida.getvalue()) if salida.getvalue() else None, errores.getvalue()

    def importar(self):
        return self.ejecutar(["importar-ventas", "--directorio", str(self.raiz),
                              "--base", str(self.base), "--manifiesto", str(self.manifiesto)])

    def test_recorrido_importar_listar_y_consultar(self):
        codigo, salida, errores = self.importar()
        self.assertEqual((codigo, errores), (0, ""))
        identidad = salida["importacion_id"]
        codigo, listado, _ = self.ejecutar(["listar-importaciones", "--base", str(self.base)])
        self.assertEqual(codigo, 0)
        self.assertEqual(listado["importaciones"][0]["id"], identidad)
        codigo, consulta, errores = self.ejecutar([
            "consultar-ventas", "--base", str(self.base), "--importacion", identidad,
            "--producto", "P01", "--desde", "2025-01-01", "--hasta", "2025-01-03"])
        self.assertEqual((codigo, errores), (0, ""))
        self.assertEqual(consulta["resumen"]["dias_sin_fila"], 2)
        self.assertEqual(consulta["resumen"]["total_observado"], 2)
        self.assertEqual(consulta["diarias"][1]["cantidad"], None)

    def test_entrada_invalida_no_crea_base(self):
        self.original.write_bytes(self.raw + b"\n")
        codigo, salida, errores = self.importar()
        self.assertEqual(codigo, 2)
        self.assertIsNone(salida)
        self.assertIn("SHA-256", errores)
        self.assertFalse(self.base.exists())

    def test_reimportacion_es_idempotente(self):
        _, uno, _ = self.importar()
        _, dos, _ = self.importar()
        self.assertEqual(uno["importacion_id"], dos["importacion_id"])

    def test_producto_desconocido_emite_error_sin_informe(self):
        _, salida, _ = self.importar()
        codigo, consulta, errores = self.ejecutar([
            "consultar-ventas", "--base", str(self.base), "--importacion", salida["importacion_id"],
            "--producto", "P99", "--desde", "2025-01-01", "--hasta", "2025-01-02"])
        self.assertEqual(codigo, 2)
        self.assertIsNone(consulta)
        self.assertIn("inexistente", errores)

    def test_lectura_de_base_ausente_no_la_crea(self):
        codigo, salida, _ = self.ejecutar(["listar-importaciones", "--base", str(self.base)])
        self.assertEqual(codigo, 2)
        self.assertIsNone(salida)
        self.assertFalse(self.base.exists())
