import copy
import hashlib
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from planificacion.dominio.recetas import calcular_consumos, interpretar_recetario
from planificacion.infraestructura.recetario import cargar_recetario


def modelo_sintetico():
    return {"version": "prueba_1", "ingredientes": [
        {"ingrediente_id": "arroz", "nombre": "Arroz", "unidad": "g", "control_stock": True},
        {"ingrediente_id": "agua", "nombre": "Agua", "unidad": "ml", "control_stock": False}],
        "recetas": [{"producto_id": "P01", "rendimiento_unidades": 1,
            "ingredientes": [
                {"ingrediente_id": "arroz", "cantidad": "0.1", "unidad": "g", "componente": "base"},
                {"ingrediente_id": "arroz", "cantidad": "0.2", "unidad": "g", "componente": "extra"},
                {"ingrediente_id": "agua", "cantidad": "2.5", "unidad": "ml", "componente": "base"}]}]}


class RecetasTests(unittest.TestCase):
    def test_suma_componentes_con_aritmetica_decimal(self):
        recetario = interpretar_recetario(modelo_sintetico(), "a" * 64)
        consumo = calcular_consumos(recetario, {"P01": Decimal("3")})
        self.assertEqual(consumo["arroz"], Decimal("0.9"))
        self.assertEqual(consumo["agua"], Decimal("7.5"))
        self.assertFalse(recetario.insumos[1].control_stock)

    def test_cantidad_cero_no_produce_consumo(self):
        consumo = calcular_consumos(interpretar_recetario(modelo_sintetico(), "a" * 64), {"P01": 0})
        self.assertTrue(all(q == 0 for q in consumo.values()))

    def test_rendimiento_se_aplica_sin_cambiar_ficha(self):
        modelo = modelo_sintetico()
        modelo["recetas"][0]["rendimiento_unidades"] = 2
        original = copy.deepcopy(modelo)
        consumo = calcular_consumos(interpretar_recetario(modelo, "a" * 64), {"P01": 2})
        self.assertEqual(consumo["arroz"], Decimal("0.3"))
        self.assertEqual(modelo, original)

    def test_receta_ausente_y_demanda_invalida_se_rechazan(self):
        recetario = interpretar_recetario(modelo_sintetico(), "a" * 64)
        for demanda in ({"P99": 1}, {"P01": -1}, {"P01": "NaN"}, {"P01": "Infinity"}, {"P01": True}):
            with self.subTest(demanda=demanda), self.assertRaises(ValueError):
                calcular_consumos(recetario, demanda)

    def test_ingredientes_unidades_y_duplicados_invalidos_bloquean(self):
        for cambio in ("unidad", "cantidad", "desconocido", "duplicado", "producto_duplicado", "rendimiento"):
            modelo = modelo_sintetico()
            linea = modelo["recetas"][0]["ingredientes"][0]
            if cambio == "unidad": linea["unidad"] = "kg"
            elif cambio == "cantidad": linea["cantidad"] = 0
            elif cambio == "desconocido": linea["ingrediente_id"] = "ausente"
            elif cambio == "duplicado": modelo["recetas"][0]["ingredientes"].append(copy.deepcopy(linea))
            elif cambio == "producto_duplicado": modelo["recetas"] *= 2
            else: modelo["recetas"][0]["rendimiento_unidades"] = 0
            with self.subTest(cambio=cambio), self.assertRaises(ValueError):
                interpretar_recetario(modelo, "a" * 64)

    def test_carga_versionada_exige_huella_y_no_modifica_archivo(self):
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "recetario_modelado_v1.json"
            raw = json.dumps(modelo_sintetico()).encode("utf-8")
            ruta.write_bytes(raw)
            huella = hashlib.sha256(raw).hexdigest()
            recetario = cargar_recetario(ruta, huella)
            self.assertEqual(recetario.sha256, huella)
            self.assertEqual(ruta.read_bytes(), raw)
            with self.assertRaisesRegex(ValueError, "huella"):
                cargar_recetario(ruta, "b" * 64)

    def test_estructura_de_ficha_invalida_da_error_de_validacion(self):
        for campo, valor in (("recetas", [None]), ("recetas", {}), ("ingredientes", "texto")):
            modelo = modelo_sintetico()
            modelo[campo] = valor
            with self.subTest(campo=campo, valor=valor), self.assertRaises(ValueError):
                interpretar_recetario(modelo, "a" * 64)
        modelo = modelo_sintetico()
        modelo["recetas"][0]["ingredientes"] = [None]
        with self.assertRaises(ValueError):
            interpretar_recetario(modelo, "a" * 64)
