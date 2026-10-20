import hashlib
import unittest
from importlib.resources import files


class ProtocoloDistribuidoTests(unittest.TestCase):
    def test_protocolo_conserva_los_bytes_de_la_seleccion_cerrada(self):
        # Huella registrada antes del experimento, selección 9b652e51effb4b79ad073ec264d21aa6.
        original = "93296ef1fbd62edcc1557eb3da8822c861b04ede73d2a16b9faaf07630a41bb7"
        datos = files("planificacion").joinpath("recursos/protocolo_tp3_v1.json").read_bytes()
        self.assertEqual(hashlib.sha256(datos).hexdigest(), original)
