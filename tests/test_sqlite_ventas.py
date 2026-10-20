"""Integración con SQLite real en carpetas temporales."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from dataclasses import replace
from datetime import date
from pathlib import Path

from planificacion.infraestructura.sqlite_ventas import SQLiteVentas
from test_preparacion import lote_sintetico


class SQLiteVentasTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.lote = lote_sintetico(self.raiz)
        self.base = self.raiz / "ventas.sqlite3"
        self.repo = SQLiteVentas(self.base)

    def test_guarda_y_recupera_identidades_procedencia_y_ausencias(self):
        identidad = self.repo.guardar(self.lote)
        producto = self.repo.obtener_producto(identidad, "P01")
        self.assertEqual(producto.producto_original, "Plato")
        self.assertEqual(producto.nombre_modelado, "Etiqueta")
        diarias = self.repo.obtener_diarias(identidad, "P01", date(2025, 1, 1), date(2025, 1, 3))
        self.assertEqual([d.cantidad for d in diarias], [2, None, None])
        self.assertEqual(diarias[0].filas_origen, (2,))
        self.assertEqual(self.repo.obtener_fuentes(identidad), self.lote.fuentes)
        self.assertEqual(self.repo.listar_importaciones()[0]["id"], identidad)
        with closing(sqlite3.connect(self.base)) as conexion, conexion:
            self.assertEqual(conexion.execute("SELECT COUNT(*) FROM filas_ventas").fetchone()[0], 1)
            self.assertEqual(conexion.execute("SELECT COUNT(*) FROM ventas_diarias").fetchone()[0], 365)
            self.assertEqual(conexion.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_reimportar_no_duplica_ni_cambia_fecha(self):
        uno = self.repo.guardar(self.lote)
        antes = self.repo.listar_importaciones()
        dos = self.repo.guardar(self.lote)
        self.assertEqual(uno, dos)
        self.assertEqual(self.repo.listar_importaciones(), antes)

    def test_otra_version_conserva_importacion_anterior(self):
        uno = self.repo.guardar(self.lote)
        nuevo = replace(self.lote, protocolo_id="otra_version")
        dos = self.repo.guardar(nuevo)
        self.assertNotEqual(uno, dos)
        self.assertEqual(len(self.repo.listar_importaciones()), 2)
        self.assertEqual(self.repo.obtener_producto(uno, "P01").nombre_modelado, "Etiqueta")

    def test_fallo_en_mitad_revierte_toda_la_importacion(self):
        anterior = self.repo.guardar(self.lote)
        with closing(sqlite3.connect(self.base)) as conexion, conexion:
            conexion.executescript("""
                CREATE TRIGGER falla_simulada BEFORE INSERT ON ventas_diarias
                WHEN NEW.fecha = '2025-01-02'
                BEGIN SELECT RAISE(ABORT, 'fallo simulado'); END;
            """)
        nuevo = replace(self.lote, protocolo_id="version_con_fallo")
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.guardar(nuevo)
        self.assertEqual([r["id"] for r in self.repo.listar_importaciones()], [anterior])
        with closing(sqlite3.connect(self.base)) as conexion, conexion:
            for tabla in ("fuentes_ventas", "productos_ventas", "filas_ventas", "ventas_diarias"):
                self.assertEqual(conexion.execute(
                    f"SELECT COUNT(*) FROM {tabla} WHERE importacion_id = ?", (nuevo.identificador,)
                ).fetchone()[0], 0)

    def test_restricciones_rechazan_cantidad_negativa_y_revierten(self):
        self.repo.guardar(self.lote)
        diarias = (replace(self.lote.diarias[0], cantidad=-1), *self.lote.diarias[1:])
        malo = replace(self.lote, diarias=diarias)
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.guardar(malo)
        self.assertEqual(len(self.repo.listar_importaciones()), 1)

    def test_parametros_no_interpretan_sql_como_identificador(self):
        identidad = self.repo.guardar(self.lote)
        with self.assertRaises(LookupError):
            self.repo.obtener_producto(identidad, "P01' OR 1=1 --")
        self.assertEqual(self.repo.obtener_producto(identidad, "P01").producto_id, "P01")

    def test_consulta_no_crea_base_ausente(self):
        with self.assertRaises(FileNotFoundError):
            self.repo.listar_importaciones()
        self.assertFalse(self.base.exists())

    def test_version_de_base_futura_no_se_modifica(self):
        with closing(sqlite3.connect(self.base)) as conexion, conexion:
            conexion.execute("PRAGMA user_version = 99")
        with self.assertRaisesRegex(ValueError, "versión"):
            self.repo.guardar(self.lote)
        with closing(sqlite3.connect(self.base)) as conexion, conexion:
            self.assertEqual(conexion.execute("PRAGMA user_version").fetchone()[0], 99)

    def test_recuperar_lote_verifica_huella_de_los_datos_almacenados(self):
        identidad = self.repo.guardar(self.lote)
        recuperado = self.repo.recuperar_lote(identidad)
        self.assertEqual(recuperado, self.lote)
        self.assertEqual(recuperado.identificador, identidad)

    def test_datos_almacenados_alterados_no_aparentan_misma_importacion(self):
        identidad = self.repo.guardar(self.lote)
        with closing(sqlite3.connect(self.base)) as c, c:
            c.execute("UPDATE ventas_diarias SET cantidad = 99 WHERE cantidad IS NOT NULL")
        with self.assertRaisesRegex(ValueError, "integridad"):
            self.repo.recuperar_lote(identidad)

    def test_recuperar_importacion_inexistente_no_devuelve_otro_lote(self):
        self.repo.guardar(self.lote)
        with self.assertRaises(LookupError):
            self.repo.recuperar_lote("inexistente")


if __name__ == "__main__":
    unittest.main()
