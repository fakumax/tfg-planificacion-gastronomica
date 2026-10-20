"""Prepara las identidades seleccionadas sin modificar ni completar originales."""

import csv
import hashlib
import io
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from ..dominio.ventas import FuenteVentas, FilaVenta, LoteVentas, Producto, VentaDiaria
from ..entradas import (CANTIDAD, DESCUENTO, FECHA, INGLES, LOCAL, PRODUCTO,
                        exigir, verificar_entradas)


def preparar_ventas(directorio: Path, manifiesto: dict, protocolo: dict) -> LoteVentas:
    informes = verificar_entradas(directorio, manifiesto)
    seleccion = protocolo["seleccion"]
    anio, local = seleccion["anio"], seleccion["local_original"]
    exigir(type(anio) is int and 1 <= anio <= 9998, "Año de selección inválido")
    exigir(isinstance(local, str) and bool(local.strip()), "Local de selección vacío")
    catalogo = seleccion["productos"]
    exigir(bool(catalogo), "Catálogo vacío")
    productos = tuple(Producto(p["producto_id"], p["producto_original"], p["nombre_modelado"],
                              local, anio) for p in catalogo)
    exigir(all(p.producto_id.strip() and p.producto_original.strip()
               and p.nombre_modelado.strip() for p in productos), "Identidad incompleta")
    exigir(len({p.producto_id for p in productos}) == len(productos)
           and len({p.producto_original for p in productos}) == len(productos),
           "Catálogo ambiguo o duplicado")
    por_nombre = {p.producto_original: p for p in productos}
    fuentes = tuple(FuenteVentas(r["archivo"], r["sha256"], e["anio_publicado"],
                                r["filas"], r["cantidad_total"])
                    for r, e in zip(informes, manifiesto["archivos_csv"], strict=True))
    elegidas = [f for f in fuentes if f.anio == anio]
    exigir(len(elegidas) == 1, "La selección requiere un único original del año indicado")
    fuente = elegidas[0]
    raw = (directorio / fuente.archivo).read_bytes()
    exigir(hashlib.sha256(raw).hexdigest() == fuente.sha256,
           "El original cambió después del control; repetir la revisión")

    lector = csv.DictReader(io.StringIO(raw.decode("cp949")), strict=True)
    filas = []
    cantidades: dict[tuple[str, date], int] = defaultdict(int)
    origenes: dict[tuple[str, date], list[int]] = defaultdict(list)
    for r in lector:
        if r[LOCAL] != local or r[PRODUCTO] not in por_nombre:
            continue
        producto = por_nombre[r[PRODUCTO]]
        fecha, cantidad = date.fromisoformat(r[FECHA]), int(Decimal(r[CANTIDAD]))
        clave = (producto.producto_id, fecha)
        cantidades[clave] += cantidad
        origenes[clave].append(lector.line_num)
        filas.append(FilaVenta(producto.producto_id, fecha, cantidad, r[DESCUENTO],
                               lector.line_num, fuente.archivo, r.get(INGLES, "")))

    exigir({f.producto_id for f in filas} == {p.producto_id for p in productos},
           "Hay productos seleccionados sin observaciones en el local y año exactos")
    inicio, fin = date(anio, 1, 1), date(anio + 1, 1, 1)
    diarias = tuple(VentaDiaria(p.producto_id, inicio + timedelta(days=n),
                                cantidades.get((p.producto_id, inicio + timedelta(days=n))),
                                tuple(origenes.get((p.producto_id, inicio + timedelta(days=n)), [])),
                                fuente.archivo)
                    for p in productos for n in range((fin - inicio).days))
    exigir(sum(f.cantidad for f in filas) == sum(d.cantidad or 0 for d in diarias),
           "La preparación no conservó las cantidades seleccionadas")
    huella = hashlib.sha256(json.dumps(protocolo, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":")).encode("utf-8")).hexdigest()
    return LoteVentas(protocolo["id"], huella, protocolo["preparacion"]["version"],
                     fuentes, productos, tuple(filas), diarias)
