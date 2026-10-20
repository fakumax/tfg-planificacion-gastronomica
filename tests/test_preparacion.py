"""Escenarios sintéticos para el contrato de preparación diaria."""

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from planificacion.entradas import CANTIDAD, DESCUENTO, FECHA, LOCAL, PRODUCTO, EntradaInvalida
from planificacion.infraestructura.csv_ventas import preparar_ventas
from test_entradas import csv_sintetico, fila, manifiesto_sintetico


def protocolo_sintetico():
    return {"id": "prueba_v1", "seleccion": {
        "anio": 2025, "local_original": "Local", "productos": [
            {"producto_id": "P01", "producto_original": "Plato", "nombre_modelado": "Etiqueta"},
        ]}, "preparacion": {"version": "prueba_v1"}}


def lote_sintetico(directorio):
    raw = csv_sintetico([fila()])
    (directorio / "prueba.csv").write_bytes(raw)
    return preparar_ventas(directorio, manifiesto_sintetico(raw), protocolo_sintetico())


class PreparacionTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.directorio = Path(self.temporal.name)

    def test_agrega_descuentos_conservando_filas_y_ausencias(self):
        raw = csv_sintetico([fila(), fila(**{DESCUENTO: "Y", CANTIDAD: "3"}),
                             fila(**{FECHA: "2025-01-03", CANTIDAD: "4"})])
        ruta = self.directorio / "prueba.csv"
        ruta.write_bytes(raw)
        manifiesto = manifiesto_sintetico(raw)
        manifiesto["archivos_csv"][0].update(
            filas=3, fechas_distintas=2, fecha_max="2025-01-03", cantidad_total=9,
            faltantes={"producto_ingles_fuente": 3})
        antes = ruta.stat().st_mtime_ns
        lote = preparar_ventas(self.directorio, manifiesto, protocolo_sintetico())
        self.assertEqual(len(lote.diarias), 365)
        self.assertEqual(lote.diarias[0].cantidad, 5)
        self.assertEqual(lote.diarias[0].filas_origen, (2, 3))
        self.assertIsNone(lote.diarias[1].cantidad)
        self.assertEqual(lote.diarias[1].filas_origen, ())
        self.assertEqual(lote.diarias[2].cantidad, 4)
        self.assertEqual(sum(d.cantidad or 0 for d in lote.diarias), 9)
        self.assertEqual([f.descuento for f in lote.filas], ["N", "Y", "N"])
        self.assertEqual(ruta.read_bytes(), raw)
        self.assertEqual(ruta.stat().st_mtime_ns, antes)

    def test_no_identifica_locales_o_productos_por_etiqueta_parecida(self):
        raw = csv_sintetico([fila(), fila(**{LOCAL: "Otro local", CANTIDAD: "8"}),
                             fila(**{PRODUCTO: "Otro plato", CANTIDAD: "6"})])
        (self.directorio / "prueba.csv").write_bytes(raw)
        manifiesto = manifiesto_sintetico(raw)
        manifiesto["archivos_csv"][0].update(
            filas=3, cantidad_total=16, locales=["Local", "Otro local"], productos=2,
            faltantes={"producto_ingles_fuente": 3})
        lote = preparar_ventas(self.directorio, manifiesto, protocolo_sintetico())
        self.assertEqual(sum(d.cantidad or 0 for d in lote.diarias), 2)
        self.assertEqual(len(lote.filas), 1)
        self.assertEqual(lote.productos[0].producto_original, "Plato")
        self.assertEqual(lote.productos[0].nombre_modelado, "Etiqueta")
        self.assertEqual(lote.fuentes[0].filas, 3)

    def test_mismas_entradas_producen_misma_identidad_de_importacion(self):
        uno = lote_sintetico(self.directorio)
        dos = lote_sintetico(self.directorio)
        self.assertEqual(uno.identificador, dos.identificador)
        protocolo = protocolo_sintetico()
        protocolo["id"] = "otra_version"
        raw = (self.directorio / "prueba.csv").read_bytes()
        tres = preparar_ventas(self.directorio, manifiesto_sintetico(raw), protocolo)
        self.assertNotEqual(uno.identificador, tres.identificador)

    def test_seleccion_ambigua_o_inexistente_se_rechaza(self):
        lote_sintetico(self.directorio)
        raw = (self.directorio / "prueba.csv").read_bytes()
        for cambio in ("duplicado", "sin_observaciones", "local_distinto", "anio_distinto"):
            protocolo = copy.deepcopy(protocolo_sintetico())
            if cambio == "duplicado":
                protocolo["seleccion"]["productos"] *= 2
            elif cambio == "sin_observaciones":
                protocolo["seleccion"]["productos"][0]["producto_original"] = "Ausente"
            elif cambio == "local_distinto":
                protocolo["seleccion"]["local_original"] = "Local parecido"
            else:
                protocolo["seleccion"]["anio"] = 2024
            with self.subTest(cambio=cambio), self.assertRaises(EntradaInvalida):
                preparar_ventas(self.directorio, manifiesto_sintetico(raw), protocolo)

    def test_original_modificado_detiene_preparacion(self):
        raw = csv_sintetico([fila()])
        (self.directorio / "prueba.csv").write_bytes(raw + b"\n")
        with self.assertRaisesRegex(EntradaInvalida, "SHA-256"):
            preparar_ventas(self.directorio, manifiesto_sintetico(raw), protocolo_sintetico())


if __name__ == "__main__":
    unittest.main()
