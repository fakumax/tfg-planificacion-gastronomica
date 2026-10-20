import unittest
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from planificacion.dominio.balance import (
    CantidadPlanificada, EntradaPrevista, Escenario, Existencia, calcular_balance,
)
from planificacion.dominio.recetas import interpretar_recetario
from test_recetas import modelo_sintetico


FECHAS = tuple(date(2025, 1, 1) + timedelta(days=n) for n in range(7))


def plan_sintetico(cantidades=(1, 0, 0, 0, 0, 0, 0)):
    return tuple(CantidadPlanificada("P01", f, Decimal(q)) for f, q in zip(FECHAS, cantidades))


def escenario_sintetico(stock="0", entradas=()):
    return Escenario("Prueba sintética", "1", (Existencia("arroz", Decimal(stock), "g"),), tuple(entradas))


class BalanceTests(unittest.TestCase):
    def setUp(self):
        self.recetario = interpretar_recetario(modelo_sintetico(), "a" * 64)

    def calcular(self, plan=None, escenario=None):
        return calcular_balance(self.recetario, plan if plan is not None else plan_sintetico(),
                                 escenario if escenario is not None else escenario_sintetico(), FECHAS)

    def test_saldo_cero_y_positivo_no_emiten_alerta(self):
        for stock, esperado in (("0.3", "0"), ("1", "0.7")):
            with self.subTest(stock=stock):
                resultado = self.calcular(escenario=escenario_sintetico(stock))
                self.assertEqual(resultado.saldos[-1].saldo, Decimal(esperado))
                self.assertEqual(resultado.alertas, ())

    def test_entrada_del_mismo_dia_se_suma_antes_del_consumo(self):
        e = EntradaPrevista("arroz", FECHAS[0], Decimal("0.3"), "g")
        resultado = self.calcular(escenario=escenario_sintetico(entradas=[e]))
        self.assertEqual(resultado.saldos[0].entradas, Decimal("0.3"))
        self.assertEqual(resultado.saldos[0].saldo, 0)
        self.assertEqual(resultado.alertas, ())

    def test_varias_entradas_mismo_dia_se_suman_con_precision_decimal(self):
        entradas = [EntradaPrevista("arroz", FECHAS[0], Decimal(q), "g") for q in ("0.1", "0.2")]
        resultado = self.calcular(escenario=escenario_sintetico(entradas=entradas))
        self.assertEqual(resultado.saldos[0].saldo, 0)

    def test_reposicion_tardia_no_borra_deficit_anterior(self):
        entrada = EntradaPrevista("arroz", FECHAS[1], Decimal("1"), "g")
        resultado = self.calcular(plan_sintetico((1, 1, 0, 0, 0, 0, 0)),
                                  escenario_sintetico(entradas=[entrada]))
        self.assertEqual(resultado.saldos[0].saldo, Decimal("-0.3"))
        self.assertEqual(resultado.saldos[1].saldo, Decimal("0.4"))
        self.assertEqual(resultado.alertas[0].primera_fecha, FECHAS[0])
        self.assertEqual(resultado.alertas[0].deficit_inicial, Decimal("0.3"))

    def test_varios_dias_de_deficit_producen_una_alerta_por_insumo(self):
        resultado = self.calcular(plan_sintetico((1,) * 7))
        self.assertEqual(len(resultado.alertas), 1)
        self.assertEqual(resultado.alertas[0].maximo_deficit, Decimal("2.1"))
        self.assertEqual(resultado.saldos[-1].saldo, Decimal("-2.1"))

    def test_insumo_sin_control_de_stock_conserva_consumo_sin_alerta(self):
        resultado = self.calcular()
        agua = [c for c in resultado.consumos if c.insumo_id == "agua"]
        self.assertEqual(agua[0].cantidad, Decimal("2.5"))
        self.assertFalse(any(s.insumo_id == "agua" for s in resultado.saldos))
        self.assertFalse(any(a.insumo_id == "agua" for a in resultado.alertas))

    def test_cobertura_incompleta_duplicada_o_producto_desconocido_bloquea(self):
        plan = plan_sintetico()
        for invalido in (plan[:-1], plan + (plan[0],),
                         (replace(plan[0], producto_id="P99"), *plan[1:])):
            with self.subTest(plan=invalido), self.assertRaises(ValueError):
                self.calcular(invalido)

    def test_plan_negativo_o_no_finito_bloquea(self):
        for q in (Decimal("-1"), Decimal("NaN"), Decimal("Infinity")):
            plan = plan_sintetico()
            with self.subTest(q=q), self.assertRaises(ValueError):
                self.calcular((replace(plan[0], cantidad=q), *plan[1:]))

    def test_stock_faltante_duplicado_negativo_o_unidad_incompatible_bloquea(self):
        bueno = escenario_sintetico()
        for existencias in ((), bueno.existencias * 2, (Existencia("arroz", Decimal(-1), "g"),),
                            (Existencia("arroz", Decimal(1), "kg"),)):
            with self.subTest(existencias=existencias), self.assertRaises(ValueError):
                self.calcular(escenario=replace(bueno, existencias=existencias))

    def test_error_de_existencia_identifica_el_insumo_faltante_o_incompatible(self):
        for existencias in ((), (Existencia('arroz', Decimal(1), 'ml'),)):
            with self.subTest(existencias=existencias), self.assertRaisesRegex(ValueError, 'arroz'):
                self.calcular(escenario=replace(escenario_sintetico(), existencias=existencias))

    def test_escenarios_de_distinto_periodo_conservan_identidades_distintas(self):
        primero = self.calcular()
        fechas = tuple(f+timedelta(days=7) for f in FECHAS)
        plan = tuple(replace(p, fecha=p.fecha+timedelta(days=7)) for p in plan_sintetico())
        segundo = calcular_balance(self.recetario, plan, escenario_sintetico(), fechas)
        self.assertNotEqual(primero.escenario_id, segundo.escenario_id)

    def test_entrada_fuera_de_horizonte_desconocida_o_con_unidad_distinta_bloquea(self):
        for entrada in (EntradaPrevista("arroz", FECHAS[-1] + timedelta(days=1), Decimal(1), "g"),
                        EntradaPrevista("otro", FECHAS[0], Decimal(1), "g"),
                        EntradaPrevista("arroz", FECHAS[0], Decimal(1), "kg")):
            with self.subTest(entrada=entrada), self.assertRaises(ValueError):
                self.calcular(escenario=escenario_sintetico(entradas=[entrada]))
