import unittest
from datetime import date

from planificacion.aplicacion.ventas import consultar_ventas
from planificacion.dominio.ventas import FuenteVentas, Producto, VentaDiaria


class VentasEnMemoria:
    def __init__(self, cantidades):
        self.cantidades = cantidades

    def obtener_producto(self, importacion_id, producto_id):
        if (importacion_id, producto_id) != ("lote", "P01"):
            raise LookupError("Producto o importación inexistente")
        return Producto("P01", "Plato", "Etiqueta", "Local", 2025)

    def obtener_diarias(self, importacion_id, producto_id, inicio, fin):
        return tuple(VentaDiaria("P01", date(2025, 1, i), q,
                                () if q is None else (i + 1,), "prueba.csv")
                     for i, q in enumerate(self.cantidades, 1))

    def obtener_fuentes(self, importacion_id):
        return (FuenteVentas("prueba.csv", "a" * 64, 2025, 2, 7),)


class ConsultaTests(unittest.TestCase):
    def test_resumen_distingue_observaciones_ausencias_y_total_parcial(self):
        consulta = consultar_ventas(VentasEnMemoria([2, None, 5]), "lote", "P01",
                                    date(2025, 1, 1), date(2025, 1, 3))
        self.assertEqual(consulta.dias_observados, 2)
        self.assertEqual(consulta.dias_sin_fila, 1)
        self.assertEqual(consulta.total_observado, 7)
        self.assertTrue(consulta.incompleta)
        self.assertEqual(consulta.producto.producto_original, "Plato")

    def test_periodo_completamente_ausente_no_informa_total_cero(self):
        consulta = consultar_ventas(VentasEnMemoria([None, None]), "lote", "P01",
                                    date(2025, 1, 1), date(2025, 1, 2))
        self.assertIsNone(consulta.total_observado)
        self.assertEqual(consulta.dias_observados, 0)

    def test_rango_invertido_se_rechaza(self):
        with self.assertRaisesRegex(ValueError, "período"):
            consultar_ventas(VentasEnMemoria([2]), "lote", "P01",
                             date(2025, 1, 3), date(2025, 1, 1))

    def test_consulta_fuera_de_cobertura_no_se_recorta_silenciosamente(self):
        with self.assertRaisesRegex(ValueError, "año"):
            consultar_ventas(VentasEnMemoria([2]), "lote", "P01",
                             date(2024, 12, 31), date(2025, 1, 1))

    def test_calendario_incompleto_en_base_no_aparenta_cobertura_completa(self):
        with self.assertRaisesRegex(ValueError, "calendario"):
            consultar_ventas(VentasEnMemoria([2]), "lote", "P01",
                             date(2025, 1, 1), date(2025, 1, 3))

    def test_producto_inexistente_no_se_sustituye_por_otro(self):
        with self.assertRaises(LookupError):
            consultar_ventas(VentasEnMemoria([2]), "lote", "P99",
                             date(2025, 1, 1), date(2025, 1, 1))
