"""Control de originales en modo lectura; no prepara ni entrena series."""

import csv
import hashlib
import io
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

FECHA = "영업일자"
LOCAL = "영업장명"
PRODUCTO = "상품명"
INGLES = "상품영문명"
DESCUENTO = "할인구분여부"
CANTIDAD = "판매수량"


class EntradaInvalida(ValueError):
    """Una entrada no satisface el contrato de la versión conocida."""


def exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise EntradaInvalida(mensaje)


def inspeccionar_csv(raw: bytes, anio: int) -> dict:
    """Valida el CSV completo y conserva como distintas las categorías Y/N.

    El contrato corresponde a los originales auditados: cantidades enteras
    positivas. Un cero o una estructura nueva requieren revisar la fuente,
    en lugar de cambiar automáticamente este contrato.
    """
    exigir(type(anio) is int and 1 <= anio <= 9999, "Año de archivo inválido")
    try:
        texto = raw.decode("cp949")
    except UnicodeDecodeError as exc:
        raise EntradaInvalida("El archivo no se puede leer como CP949") from exc

    columnas = [FECHA, LOCAL, PRODUCTO]
    if anio == 2025:
        columnas.append(INGLES)
    columnas.extend([DESCUENTO, CANTIDAD])
    lector = csv.DictReader(io.StringIO(texto), strict=True)
    try:
        encabezados = lector.fieldnames
    except csv.Error as exc:
        raise EntradaInvalida("Encabezado CSV mal formado") from exc
    exigir(encabezados == columnas, "Columnas diferentes del esquema esperado")

    claves: set[tuple] = set()
    fechas: set[date] = set()
    locales: set[str] = set()
    productos: set[str] = set()
    total = 0
    filas = 0
    vacios_ingles = 0
    descuentos = {"Y": 0, "N": 0}
    try:
        for fila in lector:
            ubicacion = f"fila {lector.line_num}"
            exigir(None not in fila and all(v is not None for v in fila.values()),
                   f"{ubicacion}: cantidad de campos incorrecta")
            for campo in (FECHA, LOCAL, PRODUCTO, DESCUENTO, CANTIDAD):
                exigir(bool(fila[campo].strip()), f"{ubicacion}: campo {campo} vacío")
            try:
                fecha = date.fromisoformat(fila[FECHA])
            except ValueError as exc:
                raise EntradaInvalida(f"{ubicacion}: fecha inválida") from exc
            exigir(fecha.isoformat() == fila[FECHA],
                   f"{ubicacion}: fecha fuera del formato AAAA-MM-DD")
            exigir(fecha.year == anio, f"{ubicacion}: año interno distinto del archivo")
            try:
                cantidad = Decimal(fila[CANTIDAD])
            except InvalidOperation as exc:
                raise EntradaInvalida(f"{ubicacion}: cantidad inválida") from exc
            exigir(cantidad.is_finite() and cantidad > 0
                   and cantidad == cantidad.to_integral_value(),
                   f"{ubicacion}: la cantidad debe ser un entero positivo y finito")
            descuento = fila[DESCUENTO]
            exigir(descuento in descuentos, f"{ubicacion}: descuento distinto de Y/N")
            clave = (fecha, fila[LOCAL], fila[PRODUCTO], descuento)
            exigir(clave not in claves, f"{ubicacion}: clave duplicada incluyendo descuento")
            claves.add(clave)
            fechas.add(fecha)
            locales.add(fila[LOCAL])
            productos.add(fila[PRODUCTO])
            total += int(cantidad)
            filas += 1
            descuentos[descuento] += 1
            if INGLES in fila and not fila[INGLES].strip():
                vacios_ingles += 1
    except csv.Error as exc:
        raise EntradaInvalida(f"CSV mal formado cerca de la fila {lector.line_num}") from exc

    exigir(filas > 0, "El archivo no contiene registros")
    return {
        "filas": filas,
        "fechas_distintas": len(fechas),
        "fecha_min": min(fechas).isoformat(),
        "fecha_max": max(fechas).isoformat(),
        "locales": sorted(locales),
        "productos": len(productos),
        "cantidad_total": total,
        "descuentos": descuentos,
        "vacios_ingles": vacios_ingles,
    }


def verificar_entradas(directorio: Path, manifiesto: dict) -> list[dict]:
    """Exige todos los archivos declarados; no escribe datos ni resultados."""
    raiz = directorio.resolve()
    exigir(raiz.is_dir(), "No existe el directorio de originales indicado")
    exigir(isinstance(manifiesto, dict), "El manifiesto debe ser un objeto JSON")
    archivos = manifiesto.get("archivos_csv")
    exigir(isinstance(archivos, list) and bool(archivos), "Manifiesto sin archivos CSV")
    revisados: list[dict] = []
    nombres: set[str] = set()
    for especificacion in archivos:
        exigir(isinstance(especificacion, dict), "Especificación de archivo inválida")
        nombre = especificacion.get("archivo", "")
        exigir(isinstance(nombre, str) and bool(nombre)
               and nombre not in (".", "..")
               and "/" not in nombre and "\\" not in nombre and ":" not in nombre,
               "El manifiesto debe usar nombres de archivo sin rutas")
        exigir(nombre not in nombres, f"Archivo repetido en manifiesto: {nombre}")
        nombres.add(nombre)
        esperado = especificacion.get("sha256", "")
        exigir(isinstance(esperado, str) and re.fullmatch(r"[0-9a-f]{64}", esperado),
               f"{nombre}: SHA-256 esperado inválido")
        anio = especificacion.get("anio_publicado")
        exigir(type(anio) is int and 1 <= anio <= 9999, f"{nombre}: año inválido")
        ruta = (raiz / nombre).resolve()
        exigir(ruta.parent == raiz, f"{nombre}: ruta fuera del directorio de originales")
        exigir(ruta.is_file(), f"Falta el original: {nombre}")
        raw = ruta.read_bytes()
        exigir(hashlib.sha256(raw).hexdigest() == esperado,
               f"{nombre}: SHA-256 diferente; revisar la fuente sin cambiar expectativas")
        exigir(len(raw) == especificacion.get("bytes"), f"{nombre}: tamaño diferente")
        exigir(especificacion.get("codificacion") == "cp949",
               f"{nombre}: codificación no admitida por esta versión")
        resumen = inspeccionar_csv(raw, anio)
        for campo in ("filas", "fechas_distintas", "fecha_min", "fecha_max", "productos",
                      "cantidad_total", "locales"):
            exigir(campo in especificacion, f"{nombre}: falta expectativa {campo}")
            esperado_campo = especificacion[campo]
            if campo == "locales":
                exigir(isinstance(esperado_campo, list), f"{nombre}: locales inválidos")
                esperado_campo = sorted(esperado_campo)
            exigir(resumen[campo] == esperado_campo,
                   f"{nombre}: {campo} diferente del manifiesto")
        if anio == 2025:
            faltantes = especificacion.get("faltantes", {})
            exigir(isinstance(faltantes, dict), f"{nombre}: faltantes debe ser un objeto")
            vacios_esperados = faltantes.get("producto_ingles_fuente")
            exigir(resumen["vacios_ingles"] == vacios_esperados,
                   f"{nombre}: cobertura inglesa diferente del manifiesto")
        revisados.append({"archivo": nombre, "sha256": esperado, **resumen})
    return revisados
