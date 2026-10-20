import contextlib
import copy
import csv
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from planificacion.cli import main
from planificacion.entradas import (
    CANTIDAD, DESCUENTO, FECHA, INGLES, LOCAL, PRODUCTO,
    EntradaInvalida, inspeccionar_csv, verificar_entradas,
)


def fila(**cambios):
    registro = {FECHA: "2025-01-01", LOCAL: "Local", PRODUCTO: "Plato",
                INGLES: "", DESCUENTO: "N", CANTIDAD: "2"}
    registro.update(cambios)
    return registro


def csv_sintetico(filas):
    salida = io.StringIO(newline="")
    escritor = csv.DictWriter(salida, fieldnames=list(fila()))
    escritor.writeheader()
    escritor.writerows(filas)
    return salida.getvalue().encode("cp949")


def manifiesto_sintetico(raw):
    return {"archivos_csv": [{
        "archivo": "prueba.csv", "anio_publicado": 2025,
        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
        "codificacion": "cp949", "filas": 1, "fechas_distintas": 1,
        "fecha_min": "2025-01-01", "fecha_max": "2025-01-01",
        "productos": 1, "cantidad_total": 2, "locales": ["Local"],
        "faltantes": {"producto_ingles_fuente": 1},
    }]}


class InspeccionTests(unittest.TestCase):
    def test_descuentos_distintos_no_se_descartan_como_duplicados(self):
        raw = csv_sintetico([fila(), fila(**{DESCUENTO: "Y", CANTIDAD: "3"})])
        resumen = inspeccionar_csv(raw, 2025)
        self.assertEqual(resumen["filas"], 2)
        self.assertEqual(resumen["cantidad_total"], 5)
        self.assertEqual(resumen["descuentos"], {"Y": 1, "N": 1})

    def test_fechas_sin_fila_no_se_convierten_en_ceros(self):
        raw = csv_sintetico([fila(), fila(**{FECHA: "2025-01-03"})])
        resumen = inspeccionar_csv(raw, 2025)
        self.assertEqual(resumen["fechas_distintas"], 2)
        self.assertEqual(resumen["cantidad_total"], 4)

    def test_clave_duplicada_incluye_descuento(self):
        with self.assertRaisesRegex(EntradaInvalida, "clave duplicada"):
            inspeccionar_csv(csv_sintetico([fila(), fila()]), 2025)

    def test_rechaza_cantidades_no_admitidas(self):
        for valor in ("0", "-1", "1.5", "NaN", "sNaN", "Infinity", "texto", ""):
            with self.subTest(valor=valor), self.assertRaises(EntradaInvalida):
                inspeccionar_csv(csv_sintetico([fila(**{CANTIDAD: valor})]), 2025)

    def test_rechaza_fecha_invalida_otro_anio_y_formato_ambiguo(self):
        for valor in ("2025-02-30", "2024-01-01", "20250101"):
            with self.subTest(valor=valor), self.assertRaises(EntradaInvalida):
                inspeccionar_csv(csv_sintetico([fila(**{FECHA: valor})]), 2025)

    def test_exige_identidad_y_categoria_de_descuento(self):
        for campo, valor in ((LOCAL, ""), (PRODUCTO, " "), (DESCUENTO, "X")):
            with self.subTest(campo=campo), self.assertRaises(EntradaInvalida):
                inspeccionar_csv(csv_sintetico([fila(**{campo: valor})]), 2025)

    def test_nombre_ingles_vacio_no_elimina_venta_observada(self):
        resumen = inspeccionar_csv(csv_sintetico([fila()]), 2025)
        self.assertEqual(resumen["vacios_ingles"], 1)
        self.assertEqual(resumen["cantidad_total"], 2)

    def test_rechaza_esquema_distinto_y_campos_sobrantes_o_faltantes(self):
        raw = csv_sintetico([fila()])
        textos = raw.decode("cp949").splitlines()
        variantes = [
            "fecha,cantidad\n2025-01-01,2\n".encode("cp949"),
            (textos[0] + "\n" + textos[1] + ",extra\n").encode("cp949"),
            (textos[0] + "\n" + textos[1].rsplit(",", 1)[0] + "\n").encode("cp949"),
        ]
        for variante in variantes:
            with self.subTest(raw=variante), self.assertRaises(EntradaInvalida):
                inspeccionar_csv(variante, 2025)

    def test_rechaza_csv_sin_registros(self):
        with self.assertRaisesRegex(EntradaInvalida, "no contiene registros"):
            inspeccionar_csv(csv_sintetico([]), 2025)

    def test_rechaza_csv_mal_formado_y_codificacion_invalida(self):
        for raw in (b'"encabezado sin cierre', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises(EntradaInvalida):
                inspeccionar_csv(raw, 2025)


class VerificacionTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.directorio = Path(self.temporal.name)
        self.raw = csv_sintetico([fila()])
        self.ruta = self.directorio / "prueba.csv"
        self.ruta.write_bytes(self.raw)
        self.manifiesto = manifiesto_sintetico(self.raw)

    def test_control_valido_no_modifica_original(self):
        antes = self.ruta.stat().st_mtime_ns
        resumen = verificar_entradas(self.directorio, self.manifiesto)
        self.assertEqual(resumen[0]["cantidad_total"], 2)
        self.assertEqual(self.ruta.read_bytes(), self.raw)
        self.assertEqual(self.ruta.stat().st_mtime_ns, antes)

    def test_archivo_cambiado_falla_sin_reescribir_expectativas(self):
        antes = copy.deepcopy(self.manifiesto)
        self.ruta.write_bytes(self.raw + b"\n")
        with self.assertRaisesRegex(EntradaInvalida, "SHA-256 diferente"):
            verificar_entradas(self.directorio, self.manifiesto)
        self.assertEqual(self.manifiesto, antes)
        self.assertEqual(self.ruta.read_bytes(), self.raw + b"\n")

    def test_archivo_ausente_no_se_crea(self):
        manifiesto = copy.deepcopy(self.manifiesto)
        manifiesto["archivos_csv"][0]["archivo"] = "ausente.csv"
        with self.assertRaisesRegex(EntradaInvalida, "Falta el original"):
            verificar_entradas(self.directorio, manifiesto)
        self.assertFalse((self.directorio / "ausente.csv").exists())

    def test_rechaza_expectativas_que_no_coinciden(self):
        for campo, valor in (("bytes", 1), ("filas", 9), ("cantidad_total", 8),
                             ("locales", ["Otro local"]), ("productos", 2)):
            manifiesto = copy.deepcopy(self.manifiesto)
            manifiesto["archivos_csv"][0][campo] = valor
            with self.subTest(campo=campo), self.assertRaises(EntradaInvalida):
                verificar_entradas(self.directorio, manifiesto)

    def test_no_admite_rutas_fuera_del_directorio(self):
        for nombre in ("../prueba.csv", "..\\prueba.csv", "C:prueba.csv", "/prueba.csv"):
            manifiesto = copy.deepcopy(self.manifiesto)
            manifiesto["archivos_csv"][0]["archivo"] = nombre
            with self.subTest(nombre=nombre), self.assertRaisesRegex(EntradaInvalida, "sin rutas"):
                verificar_entradas(self.directorio, manifiesto)

    def test_manifiesto_vacio_o_archivo_repetido_se_rechaza(self):
        for manifiesto in ({}, {"archivos_csv": []},
                           {"archivos_csv": self.manifiesto["archivos_csv"] * 2}):
            with self.subTest(manifiesto=manifiesto), self.assertRaises(EntradaInvalida):
                verificar_entradas(self.directorio, manifiesto)

    def test_cli_control_valido_devuelve_json(self):
        ruta = self.directorio / "manifiesto.json"
        ruta.write_text(json.dumps(self.manifiesto), encoding="utf-8")
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = main(["verificar-entradas", "--directorio", str(self.directorio),
                           "--manifiesto", str(ruta)])
        self.assertEqual(codigo, 0)
        self.assertEqual(json.loads(salida.getvalue())["estado"], "correcto")

    def test_cli_error_no_emite_un_informe_parcial_correcto(self):
        salida, errores = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(errores):
            codigo = main(["verificar-entradas", "--directorio", str(self.directorio)])
        self.assertEqual(codigo, 2)
        self.assertEqual(salida.getvalue(), "")
        self.assertIn("Falta el original", errores.getvalue())


if __name__ == "__main__":
    unittest.main()
