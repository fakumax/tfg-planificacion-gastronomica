import hashlib
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from planificacion.infraestructura.respaldos import copiar_base, restaurar_base
from planificacion.infraestructura.sqlite_ejecuciones import SQLiteEjecuciones
from planificacion.infraestructura.sqlite_ventas import SQLiteVentas
from soporte_experimentos import importacion_sintetica


class RespaldosTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.base, self.importacion = importacion_sintetica(self.raiz)
        self.registro = SQLiteEjecuciones(self.base)

    def test_copia_incluye_datos_confirmados_en_wal_sin_editar_el_origen(self):
        with closing(sqlite3.connect(self.base)) as abierta:
            abierta.execute("PRAGMA journal_mode=WAL")
            identidad = self.registro.guardar({"tipo": "balance", "version_codigo": "prueba", "entradas": {}, "resultado": {"valor": 7}})
            destino = self.raiz / "copias/copia.sqlite3"
            manifiesto = copiar_base(self.base, destino)
            self.assertEqual(SQLiteEjecuciones(destino).recuperar(identidad)["resultado"], {"valor": 7})
            self.assertEqual(SQLiteVentas(destino).recuperar_lote(self.importacion).identificador, self.importacion)
            self.assertEqual(manifiesto["sha256"], hashlib.sha256(destino.read_bytes()).hexdigest())

    def test_restauracion_crea_otra_base_y_conserva_la_copia(self):
        copia = self.raiz / "copia.sqlite3"
        copiar_base(self.base, copia)
        antes = copia.read_bytes()
        destino = self.raiz / "restaurada/prototipo.sqlite3"
        restaurar_base(copia, destino)
        self.assertEqual(SQLiteVentas(destino).recuperar_lote(self.importacion).identificador, self.importacion)
        self.assertEqual(copia.read_bytes(), antes)

    def test_no_sobrescribe_una_base_existente(self):
        with self.assertRaises(FileExistsError):
            copiar_base(self.base, self.base)

    def test_copia_alterada_no_se_restaura(self):
        copia = self.raiz / "copia.sqlite3"
        copiar_base(self.base, copia)
        with copia.open("ab") as f:
            f.write(b"cambio")
        destino = self.raiz / "rechazada.sqlite3"
        with self.assertRaisesRegex(ValueError, "huella"):
            restaurar_base(copia, destino)
        self.assertFalse(destino.exists())

    def test_base_con_contenido_alterado_no_se_declara_valida(self):
        with closing(sqlite3.connect(self.base)) as c:
            with c:
                c.execute("UPDATE ventas_diarias SET cantidad = cantidad + 1 WHERE cantidad IS NOT NULL")
        destino = self.raiz / "rechazada.sqlite3"
        with self.assertRaises(ValueError):
            copiar_base(self.base, destino)
        self.assertFalse(destino.exists())
