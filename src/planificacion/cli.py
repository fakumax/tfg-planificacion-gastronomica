"""Comandos disponibles en la base del prototipo."""

import argparse
import json
import platform
import sqlite3
import sys
from dataclasses import asdict
from datetime import date, datetime, timezone
from importlib.resources import files
from pathlib import Path

from . import __version__
from .entradas import verificar_entradas
from .aplicacion.ventas import consultar_ventas
from .infraestructura.csv_ventas import preparar_ventas
from .infraestructura.sqlite_ventas import SQLiteVentas
from .aplicacion.balance import ejecutar_balance
from .dominio.calendario import fecha_iso
from .dominio.serializacion import convertir
from .infraestructura.escenarios import leer_escenario, leer_plan
from .infraestructura.recetario import cargar_recetario
from .infraestructura.sqlite_ejecuciones import SQLiteEjecuciones


def recurso_json(nombre: str) -> dict:
    return json.loads(files("planificacion").joinpath("recursos", nombre).read_text(encoding="utf-8"))


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
    ejecuciones = comandos.add_parser("listar-ejecuciones", help="Listar balances y consultas conservados")
    ejecuciones.add_argument("--base", type=Path, default=Path("datos/prototipo.sqlite3"))
    ejecucion = comandos.add_parser("ver-ejecucion", help="Recuperar entradas y resultados de una ejecución")
    ejecucion.add_argument("--base", type=Path, default=Path("datos/prototipo.sqlite3"))
    ejecucion.add_argument("--ejecucion", required=True)
    args = parser.parse_args(argv)
    try:
        if args.comando == "estado":
            salida = {
                "version": __version__,
                "python": platform.python_version(),
                "implementado": ["verificación de originales en modo lectura",
                                 "preparación diaria", "importación SQLite", "consulta histórica",
                                 "recetario versionado", "balance y alertas", "historial de ejecuciones"],
                "pendiente": ["pronósticos", "interfaz", "evaluación"],
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
            ruta = args.recetario or files("planificacion").joinpath("recursos", "recetario_modelado_v1.json")
            huella = recurso_json("protocolo_tp3_v1.json")["recetario"]["archivos"]["recetario_modelado_v1.json"]
            recetario = cargar_recetario(ruta, huella)
            plan, fechas = leer_plan(args.plan)
            salida = ejecutar_balance(SQLiteEjecuciones(args.base), recetario, plan,
                                       leer_escenario(args.escenario), fechas)
        elif args.comando == "listar-ejecuciones":
            salida = {"ejecuciones": SQLiteEjecuciones(args.base).listar()}
        else:
            salida = SQLiteEjecuciones(args.base).recuperar(args.ejecucion)
    except (OSError, ValueError, TypeError, LookupError, sqlite3.Error) as exc:
        print(f"No se completó la operación: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(salida, ensure_ascii=False, indent=2, default=convertir))
    return 0
