"""Comandos disponibles en la base del prototipo."""

import argparse
import json
import platform
import sqlite3
import sys
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

from . import __version__
from .entradas import verificar_entradas
from .aplicacion.ventas import consultar_ventas
from .aplicacion.pronosticos import consultar_pronostico, consultar_disponibilidad
from .infraestructura.csv_ventas import preparar_ventas
from .infraestructura.sqlite_ventas import SQLiteVentas
from .aplicacion.balance import ejecutar_balance
from .dominio.calendario import fecha_iso
from .dominio.serializacion import convertir
from .infraestructura.escenarios import leer_escenario, leer_plan
from .infraestructura.sqlite_ejecuciones import SQLiteEjecuciones
from .aplicacion.planificacion import planificar
from .configuracion import recetario_configurado, recurso_json
from .dominio.pronosticos import Persistencia, ReferenciaSemanal
from .aplicacion.experimento import ejecutar_seleccion, ejecutar_prueba, configuracion_planificacion
from .infraestructura.random_forest import RandomForest
from .infraestructura.entorno import capturar_codigo, capturar_entorno
from .infraestructura.motor_experimento import ejecutar_tareas
from .infraestructura.exportacion import exportar_evaluacion
from .infraestructura.respaldos import copiar_base, restaurar_base
from .infraestructura.modelo_relacional import actualizar_modelo


def informar_progreso(producto: str, completados: int, total: int) -> None:
    print(f"Producto {producto} completado ({completados}/{total})", file=sys.stderr, flush=True)


def resumen_experimento(registro: dict) -> dict:
    return {"ejecucion_id": registro["ejecucion_id"], "tipo": registro["tipo"],
            "huella_contenido": registro["huella_contenido"], "rendimiento": registro["rendimiento"],
            "productos": [{k: r[k] for k in ("producto_id", "parametros", "estado", "estado_configuracion",
                                              "cobertura_validacion") if k in r}
                          for r in registro["resultado"]["productos"]]}


def fecha_argumento(valor: str) -> date:
    try:
        return fecha_iso(valor)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Usar una fecha válida AAAA-MM-DD") from exc


def cargar_manifiesto(ruta: Path | None) -> dict:
    return (json.loads(ruta.read_text(encoding="utf-8-sig")) if ruta
            else recurso_json("manifiesto_fuentes.json"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preparación del prototipo de planificación")
    parser.add_argument("--version", action="version", version=__version__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("estado", help="Mostrar el alcance implementado y el protocolo")
    verificar = comandos.add_parser("verificar-entradas", help="Comprobar originales sin modificarlos")
    verificar.add_argument("--directorio", type=Path, required=True, help="Carpeta de los CSV originales")
    verificar.add_argument("--manifiesto", type=Path, help="Otra versión de manifiesto revisada explícitamente")
    importar = comandos.add_parser("importar-ventas", help="Preparar y guardar una importación completa")
    importar.add_argument("--directorio", type=Path, required=True)
    importar.add_argument("--manifiesto", type=Path)
    importar.add_argument("--base", type=Path, default=Path("datos/prototipo.sqlite3"))
    listar = comandos.add_parser("listar-importaciones", help="Consultar las importaciones guardadas")
    listar.add_argument("--base", type=Path, default=Path("datos/prototipo.sqlite3"))
    consultar = comandos.add_parser("consultar-ventas", help="Consultar un producto y su cobertura diaria")
    consultar.add_argument("--base", type=Path, default=Path("datos/prototipo.sqlite3"))
    consultar.add_argument("--importacion", required=True)
    consultar.add_argument("--producto", required=True)
    consultar.add_argument("--desde", type=fecha_argumento, required=True)
    consultar.add_argument("--hasta", type=fecha_argumento, required=True)
    balance = comandos.add_parser("calcular-balance", help="Calcular y conservar un plan manual modelado")
    balance.add_argument("--base", type=Path, default=Path("datos/prototipo.sqlite3"))
    balance.add_argument("--plan", type=Path, required=True)
    balance.add_argument("--escenario", type=Path, required=True)
    balance.add_argument("--recetario", type=Path)
    balance.add_argument("--previa", help="Ejecución anterior del mismo escenario y horizonte")
    ejecuciones = comandos.add_parser("listar-ejecuciones", help="Listar balances y consultas conservados")
    ejecuciones.add_argument("--base", type=Path, default=Path("datos/prototipo.sqlite3"))
    ejecucion = comandos.add_parser("ver-ejecucion", help="Recuperar entradas y resultados de una ejecución")
    ejecucion.add_argument("--base", type=Path, default=Path("datos/prototipo.sqlite3"))
    ejecucion.add_argument("--ejecucion", required=True)
    planificacion = comandos.add_parser("planificar", help="Integrar pronóstico y balance desde las ventas")
    planificacion.add_argument("--base", type=Path, default=Path("datos/prototipo.sqlite3"))
    planificacion.add_argument("--importacion", required=True)
    planificacion.add_argument("--origen", type=fecha_argumento, required=True)
    planificacion.add_argument("--metodo", choices=["persistencia", "semanal", "random_forest"], default="persistencia")
    planificacion.add_argument("--seleccion", help="Selección cerrada requerida por Random Forest")
    planificacion.add_argument("--escenario", type=Path, required=True)
    planificacion.add_argument("--recetario", type=Path)
    planificacion.add_argument("--previa", help="Ejecución anterior del mismo escenario y horizonte")
    for nombre in ('pronosticar-producto', 'consultar-disponibilidad'):
        individual = comandos.add_parser(nombre, help='Consultar un producto sin exigir un balance completo')
        individual.add_argument('--base', type=Path, default=Path('datos/prototipo.sqlite3'))
        individual.add_argument('--importacion', required=True)
        individual.add_argument('--producto', required=True)
        individual.add_argument('--origen', type=fecha_argumento, required=True)
        if nombre == 'pronosticar-producto':
            individual.add_argument('--metodo', choices=['persistencia','semanal','random_forest'], default='persistencia')
            individual.add_argument('--seleccion')
    for nombre, ayuda in (("seleccionar-modelos", "Conservar la selección por validación"),
                          ("evaluar-modelos", "Comparar con una selección cerrada previamente")):
        experimento = comandos.add_parser(nombre, help=ayuda)
        experimento.add_argument("--base", type=Path, default=Path("datos/prototipo.sqlite3"))
        experimento.add_argument("--importacion", required=True)
        experimento.add_argument("--trabajadores", type=int, choices=range(1, 5), default=2)
        if nombre == "evaluar-modelos":
            experimento.add_argument("--seleccion", required=True)
    exportar = comandos.add_parser("exportar-evaluacion", help="Exportar evidencia a una carpeta nueva")
    exportar.add_argument("--base", type=Path, default=Path("datos/prototipo.sqlite3"))
    exportar.add_argument("--ejecucion", required=True)
    exportar.add_argument("--directorio", type=Path, required=True)
    respaldo = comandos.add_parser("respaldar-base", help="Crear una copia consistente en un destino nuevo")
    respaldo.add_argument("--base", type=Path, default=Path("datos/prototipo.sqlite3"))
    respaldo.add_argument("--destino", type=Path, required=True)
    restaurar = comandos.add_parser("restaurar-base", help="Restaurar una copia en otra base nueva")
    restaurar.add_argument("--copia", type=Path, required=True)
    restaurar.add_argument("--destino", type=Path, required=True)
    actualizar = comandos.add_parser("actualizar-base", help="Conservar una copia y agregar el modelo relacional del TP3")
    actualizar.add_argument("--base", type=Path, default=Path("datos/prototipo.sqlite3"))
    actualizar.add_argument("--respaldo", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.comando == "estado":
            salida = {
                "version": __version__,
                "python": platform.python_version(),
                "implementado": ["verificación de originales en modo lectura",
                                 "preparación diaria", "importación SQLite", "consulta histórica",
                                 "recetario versionado", "balance y alertas", "historial de ejecuciones",
                                 "planificación con métodos identificados", "selección y evaluación predictiva",
                                 "exportación de evidencia", "interfaz local", "copias y restauración",
                                 "pronóstico individual", "IDs de reposición", "revisiones vinculadas",
                                 "detalle por producto", "modelo relacional y migración"],
                "protocolo": recurso_json("protocolo_tp3_v1.json"),
            }
        elif args.comando == "verificar-entradas":
            manifiesto = cargar_manifiesto(args.manifiesto)
            archivos = verificar_entradas(args.directorio, manifiesto)
            salida = {
                "estado": "correcto",
                "version_codigo": __version__,
                "python": platform.python_version(),
                "fecha_control_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "archivos": archivos,
                "limite": "Integridad y propiedades de entradas; no acredita calidad predictiva ni aplicación terminada",
            }
        elif args.comando == "importar-ventas":
            lote = preparar_ventas(args.directorio, cargar_manifiesto(args.manifiesto),
                                    recurso_json("protocolo_tp3_v1.json"))
            identidad = SQLiteVentas(args.base).guardar(lote)
            salida = {"estado": "correcto", "importacion_id": identidad,
                      "productos": len(lote.productos), "filas_seleccionadas": len(lote.filas),
                      "dias_calendario": len(lote.diarias),
                      "dias_observados": sum(d.cantidad is not None for d in lote.diarias),
                      "cantidad_seleccionada": sum(f.cantidad for f in lote.filas),
                      "fuentes_auditadas": [asdict(f) for f in lote.fuentes]}
        elif args.comando == "listar-importaciones":
            salida = {"importaciones": SQLiteVentas(args.base).listar_importaciones()}
        elif args.comando == "consultar-ventas":
            consulta = consultar_ventas(SQLiteVentas(args.base), args.importacion, args.producto,
                                         args.desde, args.hasta)
            salida = {"importacion_id": args.importacion, **asdict(consulta),
                      "resumen": {"dias_observados": consulta.dias_observados,
                                  "dias_sin_fila": consulta.dias_sin_fila,
                                  "total_observado": consulta.total_observado,
                                  "incompleta": consulta.incompleta}}
        elif args.comando == "calcular-balance":
            recetario = recetario_configurado(args.recetario)
            plan, fechas = leer_plan(args.plan)
            salida = ejecutar_balance(SQLiteEjecuciones(args.base), recetario, plan,
                                       leer_escenario(args.escenario), fechas, ejecucion_previa_id=args.previa,
                                       contexto={'metodo':'plan_manual','naturaleza_plan':'modelado',
                                                 'codigo':capturar_codigo(),'entorno':capturar_entorno()})
        elif args.comando == "listar-ejecuciones":
            salida = {"ejecuciones": SQLiteEjecuciones(args.base).listar()}
        elif args.comando in ("planificar", 'pronosticar-producto'):
            referencia = None
            metodo = Persistencia() if args.metodo == "persistencia" else ReferenciaSemanal()
            if args.metodo == "random_forest":
                if not args.seleccion:
                    raise ValueError("Random Forest requiere --seleccion con una ejecución cerrada")
                configuraciones, estados, referencia = configuracion_planificacion(
                    SQLiteVentas(args.base), SQLiteEjecuciones(args.base), args.importacion, args.seleccion,
                    recurso_json("protocolo_tp3_v1.json"), args.origen,
                    {"entorno": capturar_entorno(), "codigo": capturar_codigo()})
                metodo = RandomForest(configuraciones, estados)
            if args.comando == 'pronosticar-producto':
                salida = consultar_pronostico(SQLiteVentas(args.base), SQLiteEjecuciones(args.base), metodo,
                    args.importacion, args.producto, args.origen, referencia_seleccion=referencia,
                    metadatos={'codigo':capturar_codigo(), 'entorno':capturar_entorno()})
            else:
                salida = planificar(SQLiteVentas(args.base), SQLiteEjecuciones(args.base), metodo,
                                 recetario_configurado(args.recetario), args.importacion, args.origen,
                                 leer_escenario(args.escenario), referencia_seleccion=referencia,
                                 ejecucion_previa_id=args.previa,
                                 metadatos={'codigo':capturar_codigo(), 'entorno':capturar_entorno()})
        elif args.comando == 'consultar-disponibilidad':
            salida = {'disponibilidad': consultar_disponibilidad(SQLiteVentas(args.base), args.importacion,
                args.producto, args.origen)}
        elif args.comando in ("seleccionar-modelos", "evaluar-modelos"):
            opciones = {"ventas": SQLiteVentas(args.base), "registro": SQLiteEjecuciones(args.base),
                       "importacion_id": args.importacion, "protocolo": recurso_json("protocolo_tp3_v1.json"),
                       "ejecutor": ejecutar_tareas, "trabajadores": args.trabajadores,
                       "progreso": informar_progreso,
                       "metadatos": {"entorno": capturar_entorno(), "codigo": capturar_codigo()}}
            if args.comando == "seleccionar-modelos":
                salida = resumen_experimento(ejecutar_seleccion(**opciones))
            else:
                salida = resumen_experimento(ejecutar_prueba(**opciones, seleccion_id=args.seleccion))
        elif args.comando == "exportar-evaluacion":
            salida = exportar_evaluacion(SQLiteEjecuciones(args.base), args.ejecucion, args.directorio)
        elif args.comando == "respaldar-base":
            salida = copiar_base(args.base, args.destino)
        elif args.comando == "restaurar-base":
            salida = restaurar_base(args.copia, args.destino)
        elif args.comando == "actualizar-base":
            copia = copiar_base(args.base, args.respaldo)
            actualizar_modelo(args.base)
            salida = {"estado": "correcto", "version_esquema": 2, "respaldo": copia}
        else:
            salida = SQLiteEjecuciones(args.base).recuperar(args.ejecucion)
    except (OSError, ValueError, TypeError, LookupError, sqlite3.Error) as exc:
        print(f"No se completó la operación: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(salida, ensure_ascii=False, indent=2, default=convertir))
    return 0
