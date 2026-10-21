"""Interfaz local; las reglas y escrituras se delegan a los servicios comprobados."""

import json
import os
import sqlite3
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st

from .. import __version__
from ..aplicacion.experimento import configuracion_planificacion
from ..aplicacion.planificacion import planificar
from ..aplicacion.revisiones import recuperar_escenario
from ..aplicacion.detalle import detallar_insumo
from ..aplicacion.ventas import consultar_ventas
from ..aplicacion.pronosticos import consultar_pronostico, consultar_disponibilidad
from .consultas import preparar_grafico, explicar_metricas, casos_presentados
from ..configuracion import recetario_configurado, recurso_json
from ..dominio.balance import EntradaPrevista, Escenario, Existencia
from ..dominio.pronosticos import Persistencia, ReferenciaSemanal
from ..dominio.recetas import decimal_no_negativo, texto, recetarios_compatibles
from ..dominio.serializacion import convertir, normalizar
from ..infraestructura.catalogo_base import estado_base
from ..infraestructura.csv_ventas import preparar_ventas
from ..infraestructura.entorno import capturar_codigo, capturar_entorno
from ..infraestructura.random_forest import RandomForest
from ..infraestructura.respaldos import copiar_base, restaurar_base
from ..infraestructura.sqlite_ejecuciones import SQLiteEjecuciones
from ..infraestructura.sqlite_ventas import SQLiteVentas


def tabla(filas):
    datos = json.loads(json.dumps(filas, default=convertir, ensure_ascii=False, allow_nan=False))
    st.dataframe(pd.DataFrame(datos), hide_index=True, width="stretch")


def descargar(registro):
    st.download_button("Descargar ejecución completa", json.dumps(registro, ensure_ascii=False,
        indent=2, default=convertir), file_name=f"ejecucion_{registro['ejecucion_id']}.json", mime="application/json")


def mostrar_resultado(registro):
    st.subheader("Ejecución guardada")
    contexto = registro.get("contexto", {})
    st.caption(f"{registro['fecha_utc']} · {registro['ejecucion_id']}")
    if contexto.get('revision'):
        st.caption(f"Revisión de la ejecución {contexto['revision']['ejecucion_previa_id']}")
    with st.expander('Trazabilidad de la consulta'):
        if registro.get('procedencia_preparacion'):
            st.json(registro['procedencia_preparacion'])
        st.json({k:contexto[k] for k in ('metodo','origen','codigo','entorno','revision','seleccion_modelos') if k in contexto})
    if registro["tipo"] in ("balance", "planificacion"):
        resultado = registro["resultado"]
        st.write(f"Método: {contexto.get('metodo', 'plan manual')} · Origen: {contexto.get('origen', 'plan modelado')}")
        st.caption("Recetas modeladas · Existencias y entradas sintéticas")
        alertas = resultado["alertas"]
        if alertas:
            st.warning(f"Se detectaron faltantes en {len(alertas)} insumos. Una entrada posterior no borra el déficit previo.")
            tabla(alertas)
        else:
            st.success("El escenario no presenta saldos negativos.")
        if contexto.get("pronosticos"):
            with st.expander("Cantidades previstas por producto", expanded=True):
                tabla([{k: p[k] for k in ("producto_id", "fecha", "horizonte", "cantidad", "metodo")}
                       for p in contexto["pronosticos"]])
        with st.expander("Saldos diarios", expanded=True):
            tabla(resultado["saldos"])
        st.subheader('Detalle de consumo y alertas')
        insumos = {i['insumo_id']: i['nombre'] for i in registro['entradas']['recetario']['insumos']}
        con_alerta = {a['insumo_id'] for a in alertas}
        orden = sorted(insumos, key=lambda i: (i not in con_alerta, insumos[i]))
        elegido = st.selectbox('Insumo para consultar', orden, key=f"detalle_{registro['ejecucion_id']}",
            format_func=lambda i: f"{insumos[i]} · faltante" if i in con_alerta else insumos[i])
        detalle = detallar_insumo(registro, elegido)
        st.caption('Estado del insumo: ' +
                   (detalle['insumo'].get('estado_stock') or 'Sin registrar en esta ejecución'))
        if detalle['alerta']:
            st.write(f"Primera insuficiencia: {detalle['alerta']['primera_fecha']} · "
                     f"Déficit: {detalle['alerta']['deficit_inicial']} {detalle['alerta']['unidad']}")
            st.caption('Días con saldo negativo: ' + ', '.join(detalle['dias_deficit']))
        elif not detalle['insumo']['control_stock']:
            st.info('Este insumo tiene consumo calculado y saldo no aplicable porque no controla stock.')
        tabla(detalle['balance'])
        if detalle['entradas']:
            st.write('Reposiciones previstas del insumo')
            tabla(detalle['entradas'])
        st.write('Aportes de consumo por producto y componente')
        tabla(detalle['aportes'])
        with st.expander("Consumos y procedencia"):
            tabla(resultado["consumos"])
            st.json(registro["entradas"])
    elif registro['tipo']=='consulta_pronostico':
        st.write(f"Producto: {registro['resultado']['producto_id']} · Método: {contexto['metodo']} · Origen: {contexto['origen']}")
        if not registro['resultado']['completo']:
            st.warning('Consulta incompleta: las fechas no disponibles conservan su causa y no representan cero.')
        tabla(registro['resultado']['pronosticos'])
    elif registro["tipo"] == "seleccion_modelos":
        tabla([{k: p[k] for k in ("producto_id", "estado", "parametros", "cobertura_validacion")}
               for p in registro["resultado"]["productos"]])
    else:
        tabla([m for p in registro["resultado"]["productos"] for m in p["metricas"]])
    descargar(registro)


def inicio(base, importaciones, ejecuciones):
    st.title("Planificación gastronómica")
    st.write("Consultá ventas y prepará un escenario de insumos para los próximos siete días.")
    a, b, c = st.columns(3)
    a.metric("Importaciones", len(importaciones))
    b.metric("Ejecuciones guardadas", len(ejecuciones))
    c.metric("Horizonte", "7 días")
    st.info("Las ventas son observadas. Las recetas son modeladas y el inventario del escenario es sintético.")
    st.subheader("Cargar ventas")
    st.caption("Elegí la carpeta local de originales. Se comprueba la colección completa antes de guardar.")
    carpeta = st.text_input("Carpeta de originales", "datos/originales", key="originales")
    if st.button("Validar e importar", key="importar", type="primary"):
        with st.spinner("Validando los archivos originales…"):
            lote = preparar_ventas(Path(carpeta), recurso_json("manifiesto_fuentes.json"), recurso_json("protocolo_tp3_v1.json"))
            identidad = SQLiteVentas(base).guardar(lote)
        st.success(f"Importación completa: {identidad}")
        st.caption("La misma entrada no se duplica. Elegila en la barra lateral al cambiar de pantalla.")


def ventas(base, identidad):
    st.title("Ventas")
    productos = SQLiteVentas(base).listar_productos(identidad)
    producto = st.selectbox("Producto", productos, format_func=lambda p: f"{p.producto_id} · {p.nombre_modelado}")
    st.caption(f"Identidad original: {producto.producto_original} · {producto.local_original}")
    with st.form("consulta"):
        a, b = st.columns(2)
        desde = a.date_input("Desde", date(producto.anio, 11, 1), key="desde")
        hasta = b.date_input("Hasta", date(producto.anio, 11, 7), key="hasta")
        consultar = st.form_submit_button("Consultar", key="consultar", type="primary")
    if consultar:
        consulta = consultar_ventas(SQLiteVentas(base), identidad, producto.producto_id, desde, hasta)
        a, b, c = st.columns(3)
        a.metric("Días observados", consulta.dias_observados)
        b.metric("Días sin fila", consulta.dias_sin_fila)
        c.metric("Total observado" + (" · parcial" if consulta.incompleta else ""),
                 consulta.total_observado if consulta.total_observado is not None else "Sin datos")
        tabla([{"fecha": d.fecha, "cantidad": d.cantidad,
                "estado": "Observado" if d.cantidad is not None else "Sin fila"} for d in consulta.diarias])
        st.altair_chart(preparar_grafico([{'fecha': d.fecha, 'cantidad': d.cantidad} for d in consulta.diarias]), width='stretch')
        st.caption('Los cortes del gráfico conservan las fechas sin fila; un cero observado sí se representa.')
        if consulta.incompleta:
            st.warning("El período está incompleto. Una fecha sin fila no representa una venta de cero.")
        with st.expander("Fuentes de la consulta"):
            st.json(normalizar(consulta.fuentes))


def recetas():
    st.title("Recetas")
    recetario = recetario_configurado()
    st.caption(f"Composición modelada para el escenario · Versión {recetario.version}")
    receta = st.selectbox("Ficha", recetario.recetas, format_func=lambda r: r.producto_id)
    nombres = {i.insumo_id: i for i in recetario.insumos}
    st.write(f"Rendimiento: {receta.rendimiento} unidad(es)")
    tabla([{**asdict(l), "insumo": nombres[l.insumo_id].nombre,
            "estado_stock": nombres[l.insumo_id].estado_stock,
            "control_de_stock": nombres[l.insumo_id].control_stock} for l in receta.lineas])
    modelo = recurso_json('recetario_modelado_v1.json')
    ficha = next(r for r in modelo['recetas'] if r['producto_id']==receta.producto_id)
    st.write('Adaptación:', ficha['adaptacion'])
    st.write('Supuesto de porción:', ficha['equivalencia_unidad'])
    fuentes = {f['fuente_id']: f for f in modelo['fuentes']}
    st.write('Referencias de composición')
    for fid in ficha['fuentes']:
        f = fuentes[fid]
        st.markdown(f"[{f['titulo']}]({f['url']}) · {f['autor']}")
    if not ficha['fuentes']:
        st.write('Composición definida para el escenario modelado; sin receta externa atribuida.')
    st.caption("Estas cantidades no son recetas observadas del establecimiento de origen de las ventas.")


def pronosticos(base, identidad, ejecuciones):
    st.title('Pronósticos por producto')
    st.caption('Esta consulta es independiente. Un balance completo sigue requiriendo todos los productos y fechas.')
    productos = SQLiteVentas(base).listar_productos(identidad)
    producto = st.selectbox('Producto', productos, key='producto_pronostico',
        format_func=lambda p: f'{p.producto_id} · {p.nombre_modelado}')
    origen = st.date_input('Origen de la consulta', date(2025,11,1), key='origen_consulta')
    elegido = st.selectbox('Método de consulta', ['Persistencia','Referencia semanal','Random Forest'], key='metodo_consulta')
    selecciones = [e['id'] for e in reversed(ejecuciones) if e['tipo']=='seleccion_modelos']
    seleccion = st.selectbox('Selección cerrada', selecciones, key='seleccion_individual') if elegido=='Random Forest' and selecciones else None
    if st.button('Revisar disponibilidad de datos', key='disponibilidad'):
        tabla(consultar_disponibilidad(SQLiteVentas(base), identidad, producto.producto_id, origen))
        st.caption('La disponibilidad comprueba entradas y cantidad de ejemplos. Random Forest requiere además una selección cerrada compatible.')
    if st.button('Consultar y guardar', key='pronosticar', type='primary'):
        referencia = None
        metodo = Persistencia() if elegido=='Persistencia' else ReferenciaSemanal()
        if elegido=='Random Forest':
            if not seleccion:
                raise ValueError('Falta una selección cerrada para Random Forest')
            configs, estados, referencia = configuracion_planificacion(SQLiteVentas(base), SQLiteEjecuciones(base),
                identidad, seleccion, recurso_json('protocolo_tp3_v1.json'), origen,
                {'entorno': capturar_entorno(), 'codigo': capturar_codigo()})
            metodo = RandomForest(configs, estados)
        with st.spinner('Consultando el producto…'):
            resultado = consultar_pronostico(SQLiteVentas(base), SQLiteEjecuciones(base), metodo,
                identidad, producto.producto_id, origen, referencia,
                metadatos={'codigo':capturar_codigo(), 'entorno':capturar_entorno()})
        st.session_state['ultima_consulta'] = {'base': str(base), 'id': resultado['ejecucion_id']}
        st.rerun()
    ultimo = st.session_state.get('ultima_consulta', {})
    if ultimo.get('base')==str(base):
        mostrar_resultado(SQLiteEjecuciones(base).recuperar(ultimo['id']))


def planificacion(base, identidad, ejecuciones):
    st.title("Planificación")
    st.caption("Siete días desde el origen elegido. Las existencias y entradas pertenecen a un escenario sintético.")
    recetario = recetario_configurado()
    controlados = {i.insumo_id: i for i in recetario.insumos if i.control_stock}
    candidatas = []
    for e in reversed(ejecuciones):
        if e['tipo'] == 'planificacion':
            r = SQLiteEjecuciones(base).recuperar(e['id'])
            if (r['contexto'].get('importacion_id') == identidad
                    and recetarios_compatibles(r['entradas']['recetario'], normalizar(recetario))):
                candidatas.append(e['id'])
    previa = st.selectbox('Escenario de partida', [None, *candidatas], key='revision',
        format_func=lambda i: 'Escenario nuevo' if i is None else f'Revisar {i[:12]}')
    borrador = recuperar_escenario(SQLiteEjecuciones(base), previa) if previa else None
    if st.session_state.get('edicion_escenario') != (str(base), previa):
        st.session_state['edicion_escenario'] = (str(base), previa)
        st.session_state['origen'] = (date.fromisoformat(SQLiteEjecuciones(base).recuperar(previa)['contexto']['origen'])
                                      if previa else date(2025, 11, 1))
    origen = st.date_input("Origen del pronóstico", key="origen", disabled=bool(previa))
    nombre_metodo = st.selectbox("Método", ["Persistencia", "Referencia semanal", "Random Forest"], key="metodo")
    selecciones = [r["id"] for r in reversed(ejecuciones) if r["tipo"] == "seleccion_modelos"]
    seleccion = st.selectbox("Selección cerrada", selecciones) if nombre_metodo == "Random Forest" and selecciones else None
    if nombre_metodo == "Random Forest" and not seleccion:
        st.info("Primero completá la selección por validación indicada en el manual de evaluación.")
    sufijo = previa or 'nuevo'
    nombre = st.text_input("Nombre del escenario", borrador.nombre if borrador else "Escenario de demostración", key=f'nombre_{sufijo}')
    version = st.text_input("Versión del escenario", f'{borrador.version}.1' if borrador else "1", key=f'version_{sufijo}')
    existencias_previas = {e.insumo_id: e.cantidad for e in borrador.existencias} if borrador else {}
    st.subheader("Existencias iniciales")
    stock = st.data_editor(pd.DataFrame([{"insumo_id": i.insumo_id, "insumo": i.nombre,
        "cantidad": str(existencias_previas.get(i.insumo_id, 0)), "unidad": i.unidad} for i in controlados.values()]), key=f"stock_{sufijo}",
        disabled=["insumo_id", "insumo", "unidad"], hide_index=True, width="stretch",
        column_config={"cantidad": st.column_config.TextColumn("Cantidad", required=True,
            help="Cantidad exacta; usá punto como separador decimal.")})
    st.subheader("Entradas previstas")
    filas_previas = [{'entrada_id': e.entrada_id, 'insumo_id': e.insumo_id,
                      'fecha': pd.Timestamp(e.fecha), 'cantidad': str(e.cantidad)} for e in borrador.entradas] if borrador else []
    entradas_iniciales = pd.DataFrame(filas_previas) if filas_previas else pd.DataFrame({
        'entrada_id': pd.Series(dtype=str), "insumo_id": pd.Series(dtype=str),
        "fecha": pd.Series(dtype="datetime64[ns]"), "cantidad": pd.Series(dtype=str)})
    entradas = st.data_editor(entradas_iniciales,
        key=f"entradas_{sufijo}", num_rows="dynamic", hide_index=True, width="stretch",
        column_config={'entrada_id': st.column_config.TextColumn('ID de reposición', required=True),
                       "insumo_id": st.column_config.SelectboxColumn("Insumo", options=list(controlados), required=True),
                       "fecha": st.column_config.DateColumn("Fecha", required=True),
                       "cantidad": st.column_config.TextColumn("Cantidad", required=True,
                           help="Cantidad exacta; usá punto como separador decimal.")})
    st.caption("Usá un ID distinto para cada entrega y la unidad de cada insumo. Las entradas se suman antes del consumo del mismo día.")
    if st.button("Calcular y guardar", key="planificar", type="primary"):
        existencias = tuple(Existencia(r["insumo_id"], decimal_no_negativo(r["cantidad"], "existencia"), r["unidad"])
                            for r in stock.to_dict("records"))
        reposiciones = []
        for r in entradas.to_dict("records"):
            if r["insumo_id"] not in controlados or pd.isna(r["fecha"]):
                raise ValueError("Cada entrada requiere un insumo y una fecha válidos")
            fecha = pd.Timestamp(r["fecha"]).date()
            reposiciones.append(EntradaPrevista(r["insumo_id"], fecha, decimal_no_negativo(r["cantidad"], "entrada"),
                                                controlados[r["insumo_id"]].unidad,
                                                texto(r['entrada_id'], 'identificador de reposición')))
        escenario = Escenario(nombre, version, existencias, tuple(reposiciones))
        referencia = None
        metodo = Persistencia() if nombre_metodo == "Persistencia" else ReferenciaSemanal()
        if nombre_metodo == "Random Forest":
            if not seleccion:
                raise ValueError("Falta una selección cerrada para Random Forest")
            configs, estados, referencia = configuracion_planificacion(SQLiteVentas(base), SQLiteEjecuciones(base),
                identidad, seleccion, recurso_json("protocolo_tp3_v1.json"), origen,
                {"entorno": capturar_entorno(), "codigo": capturar_codigo()})
            metodo = RandomForest(configs, estados)
        with st.spinner("Calculando el plan completo…"):
            resultado = planificar(SQLiteVentas(base), SQLiteEjecuciones(base), metodo, recetario,
                identidad, origen, escenario, referencia_seleccion=referencia, ejecucion_previa_id=previa,
                metadatos={'codigo':capturar_codigo(), 'entorno':capturar_entorno()})
        st.session_state["ultimo_plan"] = {"base": str(base), "id": resultado["ejecucion_id"]}
        st.rerun()
    ultimo = st.session_state.get("ultimo_plan", {})
    if ultimo.get("base") == str(base):
        mostrar_resultado(SQLiteEjecuciones(base).recuperar(ultimo["id"]))


def historial(base, ejecuciones):
    st.title("Historial")
    if not ejecuciones:
        st.info("Todavía no hay ejecuciones guardadas.")
        return
    por_id = {r["id"]: r for r in ejecuciones}
    identidad = st.selectbox("Ejecución", list(reversed(por_id)),
        format_func=lambda i: f"{por_id[i]['fecha_utc']} · {por_id[i]['tipo']} · {i[:10]}")
    mostrar_resultado(SQLiteEjecuciones(base).recuperar(identidad))


def evaluacion(base, ejecuciones):
    st.title("Evaluación predictiva")
    ids = [r["id"] for r in reversed(ejecuciones) if r["tipo"] == "evaluacion_predictiva"]
    if not ids:
        st.info("Todavía no hay una evaluación terminada. Seguí el manual de evaluación para ejecutarla.")
        return
    identidad = st.selectbox("Evaluación guardada", ids)
    registro = SQLiteEjecuciones(base).recuperar(identidad)
    productos = {p["producto_id"]: p for p in registro["resultado"]["productos"]}
    pid = st.selectbox("Producto", list(productos))
    producto = productos[pid]
    st.write("Configuración:", producto["estado_configuracion"])
    st.caption("Menor error es mejor. La precisión no demuestra ahorro ni beneficios operativos.")
    tabla(explicar_metricas(producto))
    with st.expander('Casos comunes y exclusiones', expanded=True):
        casos = casos_presentados(producto)
        solo_excluidos = st.checkbox('Mostrar solo casos excluidos', value=True)
        visibles = [c for c in casos if not c['evaluable']] if solo_excluidos else casos
        st.caption(f"{sum(c['evaluable'] for c in casos)} casos comunes · {sum(not c['evaluable'] for c in casos)} excluidos")
        if visibles:
            tabla(visibles)
        else:
            st.info('No hay casos para el filtro elegido.')
    if any(m["exploratoria"] for m in producto["metricas"]):
        st.warning("Algunos horizontes tienen menos de 14 orígenes; su comparación es exploratoria.")
    with st.expander("Sensibilidad sin solapamiento"):
        tabla(producto["sensibilidad"])
        if producto["bloques_p07"] is not None:
            st.json(producto["bloques_p07"])
        st.caption("Estas ventanas no acreditan independencia estadística.")
    descargar(registro)


def copias(base):
    st.title("Copias y recuperación")
    st.write("Creá una copia consistente o restaurala en una base nueva. Conservá juntos el archivo y su manifiesto.")
    destino = st.text_input("Destino de copia nuevo", f"respaldos/copia_{datetime.now():%Y%m%d_%H%M%S}.sqlite3", key="copia_destino")
    if st.button("Crear copia", key="copiar"):
        st.success(f"Copia comprobada: {copiar_base(base, Path(destino))}")
    copia = st.text_input("Copia para restaurar", key="copia_origen")
    nuevo = st.text_input("Destino nuevo de restauración", "datos/restaurada.sqlite3", key="restaurar_destino")
    if st.button("Restaurar en otra base", key="restaurar"):
        restaurar_base(Path(copia), Path(nuevo))
        st.success("Restauración comprobada. Elegí su ruta en la barra lateral para consultarla.")


def mostrar_app():
    st.set_page_config(page_title="Planificación gastronómica", page_icon="🍽️", layout="wide")
    st.sidebar.title("Planificación")
    st.sidebar.caption(f"Prototipo local · {__version__}")
    pagina = st.sidebar.radio("Sección", ["Inicio", "Ventas", 'Pronósticos', "Recetas", "Planificación", "Historial", "Evaluación", "Copias"], key="pagina")
    with st.sidebar.expander("Configuración local"):
        base = Path(st.text_input("Base de datos", os.environ.get("TFG_BASE", "datos/prototipo.sqlite3"), key="base")).resolve()
    try:
        importaciones, ejecuciones = estado_base(base)
        identidad = st.sidebar.selectbox("Importación activa", [r["id"] for r in importaciones],
                                         format_func=lambda i: i[:12]) if importaciones else None
        if pagina == "Inicio": inicio(base, importaciones, ejecuciones)
        elif pagina == "Recetas": recetas()
        elif pagina == "Historial": historial(base, ejecuciones)
        elif pagina == "Evaluación": evaluacion(base, ejecuciones)
        elif pagina == "Copias": copias(base)
        elif not identidad: st.info("Primero cargá los originales desde Inicio o elegí una base que ya tenga una importación.")
        elif pagina == "Ventas": ventas(base, identidad)
        elif pagina == 'Pronósticos': pronosticos(base, identidad, ejecuciones)
        else: planificacion(base, identidad, ejecuciones)
    except (OSError, ValueError, TypeError, LookupError, sqlite3.Error) as exc:
        st.error(f"No se completó la operación: {exc}")
