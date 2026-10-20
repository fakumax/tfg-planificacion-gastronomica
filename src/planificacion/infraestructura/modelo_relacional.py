"""Modelo del TP3 y actualización transaccional desde los registros originales.

Las seis tablas anteriores se conservan como registro de importación y de
instantáneas firmadas. Las dieciocho entidades del diseño tienen tablas propias;
Alerta se deriva de BalanceDiario. No se reescribe una ejecución histórica.
"""

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from ..dominio.serializacion import canonico
from .base_sqlite import conexion_sqlite


ESQUEMA = """
CREATE TABLE IF NOT EXISTS FuenteArchivo (
 id_fuente TEXT PRIMARY KEY, archivo TEXT NOT NULL, sha256 TEXT NOT NULL CHECK(length(sha256)=64),
 anio INTEGER NOT NULL, fecha_publicacion TEXT, fecha_descarga TEXT, metadata_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS Local (
 id_local TEXT PRIMARY KEY, id_fuente TEXT NOT NULL REFERENCES FuenteArchivo,
 nombre_original TEXT NOT NULL, UNIQUE(id_fuente,nombre_original));
CREATE TABLE IF NOT EXISTS Producto (
 id_producto TEXT PRIMARY KEY, id_local TEXT NOT NULL REFERENCES Local,
 nombre_original TEXT NOT NULL, ingles_fuente TEXT, UNIQUE(id_local,nombre_original));
CREATE TABLE IF NOT EXISTS Preparacion (
 id_preparacion TEXT PRIMARY KEY REFERENCES importaciones_ventas(id),
 version TEXT NOT NULL, protocolo_sha256 TEXT NOT NULL, catalogo_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS VentaDiaria (
 id_venta TEXT PRIMARY KEY, id_preparacion TEXT NOT NULL REFERENCES Preparacion,
 id_producto TEXT NOT NULL REFERENCES Producto, fecha TEXT NOT NULL, unidades INTEGER,
 estado_dato TEXT NOT NULL CHECK(estado_dato IN ('observado','ausente','bloqueado')),
 rastro_origen_json TEXT NOT NULL,
 CHECK((estado_dato='observado' AND unidades IS NOT NULL AND unidades>=0)
    OR (estado_dato<>'observado' AND unidades IS NULL)),
 UNIQUE(id_preparacion,id_producto,fecha));
CREATE TABLE IF NOT EXISTS Insumo (
 id_insumo TEXT PRIMARY KEY, nombre TEXT NOT NULL,
 unidad_base TEXT NOT NULL CHECK(unidad_base IN ('g','ml')),
 controla_stock INTEGER NOT NULL CHECK(controla_stock IN (0,1)));
CREATE TABLE IF NOT EXISTS Recetario (
 id_recetario TEXT PRIMARY KEY, version TEXT NOT NULL, sha256 TEXT NOT NULL,
 tipo TEXT NOT NULL CHECK(tipo='modelado'), contenido_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS Receta (
 id_receta TEXT PRIMARY KEY, id_recetario TEXT NOT NULL REFERENCES Recetario,
 id_producto TEXT REFERENCES Producto, codigo_producto TEXT NOT NULL,
 rendimiento TEXT NOT NULL CHECK(CAST(rendimiento AS REAL)>0),
 UNIQUE(id_recetario,codigo_producto));
CREATE TABLE IF NOT EXISTS RecetaInsumo (
 id_receta TEXT NOT NULL REFERENCES Receta, renglon INTEGER NOT NULL CHECK(renglon>0),
 id_insumo TEXT NOT NULL REFERENCES Insumo, componente TEXT NOT NULL,
 cantidad_base TEXT NOT NULL CHECK(CAST(cantidad_base AS REAL)>0), unidad TEXT NOT NULL,
 PRIMARY KEY(id_receta,renglon));
CREATE TABLE IF NOT EXISTS Escenario (
 id_escenario TEXT PRIMARY KEY, id_recetario TEXT NOT NULL REFERENCES Recetario,
 id_escenario_previo TEXT REFERENCES Escenario, nombre TEXT NOT NULL, version TEXT NOT NULL,
 tipo TEXT NOT NULL CHECK(tipo='sintetico'), fecha_inicial TEXT NOT NULL, contenido_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS Existencia (
 id_escenario TEXT NOT NULL REFERENCES Escenario, id_insumo TEXT NOT NULL REFERENCES Insumo,
 cantidad_base TEXT NOT NULL CHECK(CAST(cantidad_base AS REAL)>=0), unidad TEXT NOT NULL,
 PRIMARY KEY(id_escenario,id_insumo));
CREATE TABLE IF NOT EXISTS Entrada (
 id_entrada TEXT PRIMARY KEY, id_escenario TEXT NOT NULL REFERENCES Escenario,
 id_insumo TEXT NOT NULL REFERENCES Insumo, id_reposicion TEXT NOT NULL,
 fecha TEXT NOT NULL, cantidad_base TEXT NOT NULL CHECK(CAST(cantidad_base AS REAL)>0),
 unidad TEXT NOT NULL, UNIQUE(id_escenario,id_reposicion));
CREATE TABLE IF NOT EXISTS Configuracion (
 id_configuracion TEXT PRIMARY KEY, metodo TEXT NOT NULL
 CHECK(metodo IN ('persistencia','semanal','random_forest')), contenido_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS Ejecucion (
 id_ejecucion TEXT PRIMARY KEY REFERENCES ejecuciones(id),
 id_preparacion TEXT REFERENCES Preparacion, id_escenario TEXT REFERENCES Escenario,
 id_ejecucion_previa TEXT REFERENCES Ejecucion, tipo TEXT NOT NULL,
 seleccion_modelos_json TEXT NOT NULL, huella_contenido TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS Pronostico (
 id_pronostico TEXT PRIMARY KEY, id_ejecucion TEXT NOT NULL REFERENCES Ejecucion,
 id_producto TEXT NOT NULL REFERENCES Producto, id_configuracion TEXT NOT NULL REFERENCES Configuracion,
 origen TEXT NOT NULL, horizonte INTEGER NOT NULL CHECK(horizonte BETWEEN 1 AND 7),
 fecha_objetivo TEXT NOT NULL, unidades TEXT NOT NULL CHECK(CAST(unidades AS REAL)>=0),
 corte_entrenamiento TEXT NOT NULL, n_entrenamiento INTEGER, contenido_json TEXT NOT NULL,
 CHECK(fecha_objetivo=date(origen,'+' || horizonte || ' days')),
 CHECK(corte_entrenamiento<=origen),
 UNIQUE(id_ejecucion,id_producto,id_configuracion,origen,horizonte));
CREATE TABLE IF NOT EXISTS CasoEvaluacion (
 id_caso TEXT PRIMARY KEY, id_ejecucion TEXT NOT NULL REFERENCES Ejecucion,
 id_producto TEXT NOT NULL REFERENCES Producto, id_venta_objetivo TEXT REFERENCES VentaDiaria,
 origen TEXT NOT NULL, horizonte INTEGER NOT NULL CHECK(horizonte BETWEEN 1 AND 7),
 admitido_comun INTEGER NOT NULL CHECK(admitido_comun IN (0,1)),
 escala_mase REAL, pares_escala INTEGER NOT NULL, resultados_metodos_json TEXT NOT NULL,
 contenido_json TEXT NOT NULL, UNIQUE(id_ejecucion,id_producto,origen,horizonte));
CREATE TABLE IF NOT EXISTS Evaluacion (
 id_evaluacion TEXT PRIMARY KEY, id_ejecucion TEXT NOT NULL REFERENCES Ejecucion,
 id_producto TEXT NOT NULL REFERENCES Producto, id_configuracion TEXT NOT NULL REFERENCES Configuracion,
 horizonte INTEGER NOT NULL CHECK(horizonte BETWEEN 1 AND 7), tipo_muestra TEXT NOT NULL,
 bloque TEXT NOT NULL, n_mase_calculable INTEGER NOT NULL, contenido_json TEXT NOT NULL,
 UNIQUE(id_ejecucion,id_producto,id_configuracion,horizonte,tipo_muestra,bloque));
CREATE TABLE IF NOT EXISTS BalanceDiario (
 id_ejecucion TEXT NOT NULL REFERENCES Ejecucion, id_insumo TEXT NOT NULL REFERENCES Insumo,
 fecha TEXT NOT NULL, existencia_antes TEXT, entradas TEXT, consumo TEXT NOT NULL,
 saldo_final TEXT, unidad TEXT NOT NULL, PRIMARY KEY(id_ejecucion,id_insumo,fecha));
CREATE VIEW IF NOT EXISTS Alerta AS
 SELECT b.id_ejecucion,b.id_insumo,b.fecha AS primera_fecha,
 -CAST(b.saldo_final AS REAL) AS deficit_primera_fecha,b.unidad
 FROM BalanceDiario b JOIN Insumo i USING(id_insumo)
 WHERE i.controla_stock=1 AND CAST(b.saldo_final AS REAL)<0
 AND b.fecha=(SELECT min(s.fecha) FROM BalanceDiario s
   WHERE s.id_ejecucion=b.id_ejecucion AND s.id_insumo=b.id_insumo
   AND CAST(s.saldo_final AS REAL)<0);
"""


def clave(*valores):
    return hashlib.sha256(canonico(valores).encode('utf-8')).hexdigest()


def _insertar(c, tabla, valores):
    # Los nombres provienen exclusivamente de llamadas internas, nunca del usuario.
    c.execute(f"INSERT INTO {tabla} VALUES ({','.join('?' for _ in valores)})", valores)


def _insertar_inmutable(c, tabla, pk, valores):
    actual = c.execute(f'SELECT * FROM {tabla} WHERE {pk}=?', (valores[0],)).fetchone()
    if actual is None:
        _insertar(c, tabla, valores)
    elif tuple(actual) != tuple(valores):
        raise ValueError(f'Integridad: identidad de {tabla} con contenido diferente')


def proyectar_importacion(c, identidad):
    if c.execute('SELECT 1 FROM Preparacion WHERE id_preparacion=?', (identidad,)).fetchone():
        return
    imp = c.execute('SELECT * FROM importaciones_ventas WHERE id=?', (identidad,)).fetchone()
    for f in c.execute('SELECT * FROM fuentes_ventas WHERE importacion_id=?', (identidad,)).fetchall():
        _insertar_inmutable(c, 'FuenteArchivo', 'id_fuente',
            (f['sha256'], f['archivo'], f['sha256'], f['anio'], None, None,
             canonico({k: f[k] for k in ('filas', 'cantidad_total')})))
    catalogo = {}
    for p in c.execute('SELECT * FROM productos_ventas WHERE importacion_id=?', (identidad,)).fetchall():
        archivos = c.execute('''SELECT DISTINCT archivo_origen FROM ventas_diarias
            WHERE importacion_id=? AND producto_id=?''', (identidad, p['producto_id'])).fetchall()
        if len(archivos) != 1:
            raise ValueError('La identidad de producto requiere exactamente un archivo de origen')
        fuente = c.execute('SELECT sha256 FROM fuentes_ventas WHERE importacion_id=? AND archivo=?',
                           (identidad, archivos[0][0])).fetchone()[0]
        local = clave(fuente, p['local_original'])
        producto = clave(local, p['producto_original'])
        _insertar_inmutable(c, 'Local', 'id_local', (local, fuente, p['local_original']))
        _insertar_inmutable(c, 'Producto', 'id_producto', (producto, local, p['producto_original'], None))
        catalogo[p['producto_id']] = {'id_producto': producto, 'nombre_modelado': p['nombre_modelado']}
    _insertar(c, 'Preparacion', (identidad, imp['version_preparacion'], imp['protocolo_sha256'], canonico(catalogo)))
    for d in c.execute('SELECT * FROM ventas_diarias WHERE importacion_id=?', (identidad,)).fetchall():
        pid = catalogo[d['producto_id']]['id_producto']
        rastro = [dict(f) for f in c.execute('''SELECT archivo_origen,fila_origen,descuento,ingles_fuente
            FROM filas_ventas WHERE importacion_id=? AND producto_id=? AND fecha=? ORDER BY fila_origen''',
            (identidad, d['producto_id'], d['fecha']))]
        _insertar(c, 'VentaDiaria', (clave(identidad, pid, d['fecha']), identidad, pid, d['fecha'],
            d['cantidad'], 'ausente' if d['cantidad'] is None else 'observado', canonico(rastro)))


def _configuracion(c, metodo, parametros, contexto):
    datos = {'metodo': metodo, 'parametros': parametros,
             'protocolo_sha256': contexto.get('protocolo_sha256'),
             'nucleo': contexto.get('codigo', {}).get('huella_nucleo_numerico')}
    identidad = clave(datos)
    _insertar_inmutable(c, 'Configuracion', 'id_configuracion', (identidad, metodo, canonico(datos)))
    return identidad


def _escenario(c, entradas, resultado, catalogo, previo):
    r, s = entradas['recetario'], entradas['escenario']
    rid = clave(r, catalogo)
    _insertar_inmutable(c, 'Recetario', 'id_recetario', (rid, r['version'], r['sha256'], 'modelado', canonico(r)))
    for i in r['insumos']:
        _insertar_inmutable(c, 'Insumo', 'id_insumo', (i['insumo_id'], i['nombre'], i['unidad'], int(i['control_stock'])))
    for receta in r['recetas']:
        rcid = clave(rid, receta['producto_id'])
        if c.execute('SELECT 1 FROM Receta WHERE id_receta=?', (rcid,)).fetchone():
            continue
        # Un plan manual sin importación no acredita identidad de una venta original.
        producto = catalogo.get(receta['producto_id'], {}).get('id_producto')
        _insertar(c, 'Receta', (rcid, rid, producto, receta['producto_id'], receta['rendimiento']))
        for n, l in enumerate(receta['lineas'], 1):
            _insertar(c, 'RecetaInsumo', (rcid, n, l['insumo_id'], l['componente'], l['cantidad'], l['unidad']))
    sid = clave(rid, resultado['escenario_id'])
    padre = None
    if previo:
        fila = c.execute('SELECT id_escenario FROM Ejecucion WHERE id_ejecucion=?', (previo,)).fetchone()
        if fila is None or fila[0] is None:
            raise ValueError('El antecedente del escenario no existe')
        padre = fila[0]
    valores = (sid, rid, padre, s['nombre'], s['version'], s['tipo'], entradas['fechas'][0], canonico(s))
    if c.execute('SELECT 1 FROM Escenario WHERE id_escenario=?', (sid,)).fetchone():
        _insertar_inmutable(c, 'Escenario', 'id_escenario', valores)
        return sid
    _insertar(c, 'Escenario', valores)
    for e in s['existencias']:
        _insertar(c, 'Existencia', (sid, e['insumo_id'], e['cantidad'], e['unidad']))
    for n, e in enumerate(s['entradas'], 1):
        eid = e.get('entrada_id') or f'legado-{n}'
        if e['fecha'] < entradas['fechas'][0]:
            raise ValueError('Entrada anterior al comienzo del escenario')
        _insertar(c, 'Entrada', (clave(sid, eid), sid, e['insumo_id'], eid, e['fecha'], e['cantidad'], e['unidad']))
    return sid


def proyectar_ejecucion(c, fila):
    identidad = fila['id']
    if c.execute('SELECT 1 FROM Ejecucion WHERE id_ejecucion=?', (identidad,)).fetchone():
        return
    raw = fila['contenido_json']
    if hashlib.sha256(raw.encode('utf-8')).hexdigest() != fila['huella_contenido']:
        raise ValueError('La integridad de la ejecución no coincide con su huella')
    d = json.loads(raw)
    entrada = canonico({'entradas': d['entradas'], 'contexto': d.get('contexto', {})})
    if (hashlib.sha256(entrada.encode('utf-8')).hexdigest() != fila['huella_entrada']
            or d['tipo'] != fila['tipo'] or d['version_codigo'] != fila['version_codigo']):
        raise ValueError('La integridad de los metadatos de ejecución no coincide')
    ctx, entradas, res = d.get('contexto', {}), d['entradas'], d['resultado']
    imp = ctx.get('importacion_id')
    catalogo = {}
    if imp:
        p = c.execute('SELECT catalogo_json FROM Preparacion WHERE id_preparacion=?', (imp,)).fetchone()
        if p is None:
            raise ValueError('La ejecución refiere una preparación inexistente')
        catalogo = json.loads(p[0])
    previo = ctx.get('revision', {}).get('ejecucion_previa_id')
    sid = _escenario(c, entradas, res, catalogo, previo) if 'recetario' in entradas else None
    _insertar(c, 'Ejecucion', (identidad, imp, sid, previo, d['tipo'],
        canonico(ctx.get('seleccion_modelos', entradas.get('seleccion_id'))), fila['huella_contenido']))
    if sid:
        saldos = {(s['insumo_id'], s['fecha']): s for s in res['saldos']}
        for consumo in res['consumos']:
            s = saldos.get((consumo['insumo_id'], consumo['fecha']), {})
            _insertar(c, 'BalanceDiario', (identidad, consumo['insumo_id'], consumo['fecha'],
                s.get('existencia_antes'), s.get('entradas'), consumo['cantidad'], s.get('saldo'), consumo['unidad']))
    for p in ctx.get('pronosticos', []):
        _pronostico(c, identidad, catalogo, p, ctx)
    for producto in res.get('productos', []):
        codigo = producto['producto_id']
        if codigo not in catalogo:
            raise ValueError('Producto de evaluación fuera de la preparación')
        pid = catalogo[codigo]['id_producto']
        parametros = producto['parametros']
        predicciones = producto.get('predicciones', [])
        por_caso = {}
        for p in predicciones:
            por_caso.setdefault((p['origen'], p['horizonte']), []).append(p)
            _pronostico(c, identidad, catalogo, {**p, 'parametros': parametros if p['metodo']=='random_forest' else {}}, ctx)
        for caso in producto.get('casos', []):
            origen, h = caso['origen'], caso['horizonte']
            venta = c.execute('''SELECT id_venta FROM VentaDiaria
                WHERE id_preparacion=? AND id_producto=? AND fecha=?''',
                (imp, pid, caso['fecha_objetivo'])).fetchone()
            _insertar(c, 'CasoEvaluacion', (clave(identidad, pid, origen, h), identidad, pid,
                venta[0] if venta else None, origen, h, int(caso['evaluable']), caso.get('escala'),
                caso.get('pares_escala', 0), canonico(por_caso.get((origen,h), [])), canonico(caso)))
        for n, m in enumerate(producto.get('metricas', []) + producto.get('sensibilidad', [])):
            config = _configuracion(c, m['metodo'], parametros if m['metodo']=='random_forest' else {}, ctx)
            _insertar(c, 'Evaluacion', (clave(identidad, pid, n), identidad, pid, config, m['horizonte'],
                m['muestra'], '', m['n_mase_calculable'], canonico(m)))
        if d['tipo']=='seleccion_modelos':
            _configuracion(c, 'random_forest', parametros, ctx)


def _pronostico(c, ejecucion, catalogo, p, contexto):
    pid = catalogo[p['producto_id']]['id_producto']
    config = _configuracion(c, p['metodo'], p.get('parametros', {}), contexto)
    origen, h = p['origen'], p['horizonte']
    _insertar(c, 'Pronostico', (clave(ejecucion,pid,config,origen,h), ejecucion,pid,config,
        origen,h,p.get('fecha',p.get('fecha_objetivo')),str(p.get('cantidad',p.get('estimado'))),
        origen,p.get('ejemplos_entrenamiento'),canonico(p)))


def crear_modelo(c):
    for sentencia in ESQUEMA.split(';'):
        if sentencia.strip():
            c.execute(sentencia)


def actualizar_en_conexion(c):
    crear_modelo(c)
    tablas = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'importaciones_ventas' in tablas:
        for fila in c.execute('SELECT id FROM importaciones_ventas ORDER BY fecha_utc,id').fetchall():
            proyectar_importacion(c, fila[0])
    if 'ejecuciones' in tablas:
        for fila in c.execute('SELECT * FROM ejecuciones ORDER BY fecha_utc,id').fetchall():
            proyectar_ejecucion(c, fila)
    c.execute('PRAGMA user_version=2')


def actualizar_modelo(ruta: Path):
    if not ruta.is_file():
        raise FileNotFoundError('No existe la base que se desea actualizar')
    with conexion_sqlite(ruta, escritura=True) as c:
        c.execute('BEGIN IMMEDIATE')
        actualizar_en_conexion(c)
        if c.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('La actualización dejó referencias inválidas')


def verificar_modelo(c):
    """Contrastar las entidades con las instantáneas sin escribir en el origen."""
    if c.execute('PRAGMA user_version').fetchone()[0] != 2:
        return
    with closing(sqlite3.connect(':memory:', isolation_level=None)) as esperado:
        esperado.row_factory = sqlite3.Row
        esperado.execute('PRAGMA foreign_keys=ON')
        anteriores = ('importaciones_ventas', 'fuentes_ventas', 'productos_ventas',
                      'filas_ventas', 'ventas_diarias', 'ejecuciones')
        for nombre in anteriores:
            sql = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (nombre,)).fetchone()
            if sql is None:
                continue
            esperado.execute(sql[0])
            filas = c.execute(f'SELECT * FROM {nombre}').fetchall()
            if filas:
                esperado.executemany(f"INSERT INTO {nombre} VALUES ({','.join('?' for _ in filas[0])})", filas)
        esperado.execute('BEGIN')
        actualizar_en_conexion(esperado)
        for fila in esperado.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            nombre = fila[0]
            if nombre in anteriores:
                continue
            columnas = len(esperado.execute(f'PRAGMA table_info({nombre})').fetchall())
            orden = ','.join(str(n) for n in range(1, columnas+1))
            consulta = f'SELECT * FROM {nombre} ORDER BY {orden}'
            if [tuple(r) for r in c.execute(consulta)] != [tuple(r) for r in esperado.execute(consulta)]:
                raise ValueError(f'La integridad relacional de {nombre} difiere de las instantáneas')
