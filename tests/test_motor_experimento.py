import unittest
from datetime import date

from planificacion.configuracion import recurso_json
from planificacion.dominio.parametros import CONFIGURACION_PREFIJADA
from planificacion.infraestructura.motor_experimento import ejecutar_tareas


class MotorExperimentoTests(unittest.TestCase):
    def tareas(self, accion="seleccion"):
        return [{"accion": accion, "producto_id": p, "serie": {date(2025, 11, 1): 2},
                 "protocolo": recurso_json("protocolo_tp3_v1.json"),
                 "parametros": dict(CONFIGURACION_PREFIJADA),
                 "estado": "prefijada_validacion_insuficiente"} for p in ("P02", "P01")]

    def test_procesos_y_ejecucion_secuencial_producen_los_mismos_resultados(self):
        for accion in ("seleccion", "prueba"):
            secuencial = ejecutar_tareas(self.tareas(accion), trabajadores=1)
            paralelo = ejecutar_tareas(self.tareas(accion), trabajadores=2)
            self.assertEqual(secuencial, paralelo)
            self.assertEqual([r["producto_id"] for r in paralelo], ["P01", "P02"])

    def test_progreso_informa_solo_productos_completados(self):
        eventos = []
        ejecutar_tareas(self.tareas(), trabajadores=2, progreso=lambda p, n, total: eventos.append((p, n, total)))
        self.assertEqual({e[0] for e in eventos}, {"P01", "P02"})
        self.assertEqual([e[1:] for e in eventos], [(1, 2), (2, 2)])

    def test_error_de_una_tarea_impide_un_resultado_parcial(self):
        tareas = self.tareas()
        tareas[0]["accion"] = "invalida"
        with self.assertRaisesRegex(ValueError, "Acción"):
            ejecutar_tareas(tareas, trabajadores=2)
