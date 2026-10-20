"""Consumo por receta con unidades explícitas y cantidades decimales."""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


def decimal_no_negativo(valor, campo: str) -> Decimal:
    if isinstance(valor, bool):
        raise ValueError(f"{campo}: cantidad booleana no admitida")
    try:
        cantidad = Decimal(str(valor))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{campo}: cantidad inválida") from exc
    if not cantidad.is_finite() or cantidad < 0:
        raise ValueError(f"{campo}: se requiere una cantidad finita no negativa")
    return cantidad


def texto(valor, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{campo}: texto obligatorio")
    return valor


@dataclass(frozen=True)
class Insumo:
    insumo_id: str
    nombre: str
    unidad: str
    control_stock: bool


@dataclass(frozen=True)
class LineaReceta:
    insumo_id: str
    cantidad: Decimal
    unidad: str
    componente: str


@dataclass(frozen=True)
class Receta:
    producto_id: str
    rendimiento: Decimal
    lineas: tuple[LineaReceta, ...]


@dataclass(frozen=True)
class Recetario:
    version: str
    sha256: str
    insumos: tuple[Insumo, ...]
    recetas: tuple[Receta, ...]


def interpretar_recetario(modelo: dict, sha256: str) -> Recetario:
    if not isinstance(modelo, dict) or not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ValueError("Modelo o huella de recetario inválidos")
    version = texto(modelo.get("version"), "versión")
    if (not isinstance(modelo.get("ingredientes"), list) or not modelo["ingredientes"]
            or not isinstance(modelo.get("recetas"), list) or not modelo["recetas"]):
        raise ValueError("Recetario sin insumos o recetas")
    insumos = []
    for i in modelo["ingredientes"]:
        if not isinstance(i, dict) or type(i.get("control_stock")) is not bool:
            raise ValueError("Insumo sin control de stock explícito")
        insumos.append(Insumo(texto(i.get("ingrediente_id"), "insumo"),
                              texto(i.get("nombre"), "nombre"),
                              texto(i.get("unidad"), "unidad"), i["control_stock"]))
    por_insumo = {i.insumo_id: i for i in insumos}
    if len(por_insumo) != len(insumos):
        raise ValueError("Insumo duplicado")
    recetas = []
    for r in modelo["recetas"]:
        if not isinstance(r, dict):
            raise ValueError("Ficha de receta inválida")
        pid = texto(r.get("producto_id"), "producto de receta")
        rendimiento = decimal_no_negativo(r.get("rendimiento_unidades"), "rendimiento")
        if rendimiento == 0 or not isinstance(r.get("ingredientes"), list) or not r["ingredientes"]:
            raise ValueError("Receta sin rendimiento positivo o ingredientes")
        lineas, vistas = [], set()
        for l in r["ingredientes"]:
            if not isinstance(l, dict):
                raise ValueError("Línea de ingrediente inválida")
            iid = texto(l.get("ingrediente_id"), "insumo de receta")
            unidad = texto(l.get("unidad"), "unidad de receta")
            componente = texto(l.get("componente"), "componente")
            cantidad = decimal_no_negativo(l.get("cantidad"), "cantidad de receta")
            if iid not in por_insumo or unidad != por_insumo[iid].unidad:
                raise ValueError("Insumo desconocido o unidades incompatibles sin conversión documentada")
            if cantidad == 0 or (componente, iid) in vistas:
                raise ValueError("Cantidad de receta no positiva o ingrediente duplicado en componente")
            vistas.add((componente, iid))
            lineas.append(LineaReceta(iid, cantidad, unidad, componente))
        recetas.append(Receta(pid, rendimiento, tuple(lineas)))
    if len({r.producto_id for r in recetas}) != len(recetas):
        raise ValueError("Producto duplicado en recetario")
    return Recetario(version, sha256, tuple(insumos), tuple(recetas))


def calcular_consumos(recetario: Recetario, demanda: dict) -> dict[str, Decimal]:
    recetas = {r.producto_id: r for r in recetario.recetas}
    consumos = {i.insumo_id: Decimal(0) for i in recetario.insumos}
    for pid, valor in demanda.items():
        if pid not in recetas:
            raise ValueError(f"Falta una receta para {pid}")
        cantidad = decimal_no_negativo(valor, f"demanda de {pid}")
        receta = recetas[pid]
        for linea in receta.lineas:
            consumos[linea.insumo_id] += cantidad * linea.cantidad / receta.rendimiento
    return consumos
