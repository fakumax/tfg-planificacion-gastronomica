import csv
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from planificacion.infraestructura.exportacion import exportar_evaluacion
from planificacion.dominio.serializacion import canonico


class RegistroExportacion:
    """Doble del contrato: el exportador no depende del esquema de SQLite."""
    def __init__(self):
        self.registros = {}

    def guardar(self, contenido):
        identidad = str(len(self.registros))
        self.registros[identidad] = {**copy.deepcopy(contenido), 'ejecucion_id': identidad,
            'huella_contenido': hashlib.sha256(canonico(contenido).encode()).hexdigest()}
        return identidad

    def recuperar(self, identidad):
        return copy.deepcopy(self.registros[identidad])


class ExportacionTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.registro = RegistroExportacion()
        self.seleccion = self.registro.guardar({"tipo": "seleccion_modelos", "version_codigo": "prueba",
            "entradas": {}, "resultado": {"productos": []}})
        s = self.registro.recuperar(self.seleccion)
        self.identidad = self.registro.guardar({"tipo": "evaluacion_predictiva", "version_codigo": "prueba",
            "entradas": {"seleccion_id": self.seleccion, "huella_seleccion": s["huella_contenido"]},
            "resultado": {"productos": [{"producto_id": "P07", "parametros": {"n_estimators": 100},
                "estado_configuracion": "prefijada_validacion_insuficiente",
                "predicciones": [{"producto_id": "P07", "metodo": "persistencia", "estimado": 2.5}],
                "casos": [{"evaluable": False, "motivos": ["respuesta_ausente"], "horizonte": 1}],
                "metricas": [{"mae": None, "n_predicciones": 0}],
                "sensibilidad": [{"mae": None, "n_predicciones": 0, "origenes": []}],
                "bloques_p07": {"n_bloques_completos": 0}}]}})

    def test_exporta_evidencia_completa_csv_y_huellas_verificables(self):
        destino = self.raiz / "salida"
        manifest = exportar_evaluacion(self.registro, self.identidad, destino)
        for nombre, huella in manifest["archivos"].items():
            self.assertEqual(hashlib.sha256((destino / nombre).read_bytes()).hexdigest(), huella)
        with (destino / "predicciones.csv").open(encoding="utf-8-sig", newline="") as f:
            self.assertEqual(list(csv.DictReader(f))[0]["estimado"], "2.5")
        with (destino / "metricas.csv").open(encoding="utf-8-sig", newline="") as f:
            self.assertEqual(list(csv.DictReader(f))[0]["mae"], "")
        self.assertEqual(json.loads((destino / "seleccion.json").read_text(encoding="utf-8"))["ejecucion_id"], self.seleccion)
        self.assertTrue((destino / "manifiesto_exportacion.json").exists())

    def test_no_sobrescribe_un_directorio_existente(self):
        destino = self.raiz / "existente"
        destino.mkdir()
        (destino / "conservar.txt").write_text("previo", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            exportar_evaluacion(self.registro, self.identidad, destino)
        self.assertEqual(list(destino.iterdir()), [destino / "conservar.txt"])

    def test_no_exporta_un_tipo_incorrecto_como_resultado_predictivo(self):
        destino = self.raiz / "invalido"
        with self.assertRaisesRegex(ValueError, "evaluación"):
            exportar_evaluacion(self.registro, self.seleccion, destino)
        self.assertFalse(destino.exists())
