"""API local: contratos HTTP sobre los servicios del prototipo."""

import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictStr
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .. import __version__
from ..aplicacion.detalle import detallar_insumo
from ..aplicacion.experimento import configuracion_planificacion
from ..aplicacion.planificacion import planificar
from ..aplicacion.pronosticos import consultar_disponibilidad, consultar_pronostico
from ..aplicacion.ventas import consultar_ventas
from ..configuracion import recetario_configurado, recurso_json
from ..dominio.balance import EntradaPrevista, Escenario, Existencia
from ..dominio.pronosticos import Persistencia, ReferenciaSemanal
from ..dominio.recetas import decimal_no_negativo
from ..dominio.serializacion import normalizar
from ..infraestructura.catalogo_base import estado_base
from ..infraestructura.csv_ventas import preparar_ventas
from ..infraestructura.entorno import capturar_codigo, capturar_entorno
from ..infraestructura.random_forest import RandomForest
from ..infraestructura.respaldos import copiar_base, restaurar_base
from ..infraestructura.sqlite_ejecuciones import SQLiteEjecuciones
from ..infraestructura.sqlite_ventas import SQLiteVentas


class Cuerpo(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Consulta(Cuerpo):
    importacion: str
    origen: date
    metodo: Literal['persistencia', 'semanal', 'random_forest']
    seleccion_id: str | None = None


class Pronostico(Consulta):
    producto: str


class Stock(Cuerpo):
    insumo_id: str
    cantidad: StrictStr
    unidad: str


class Entrada(Stock):
    entrada_id: str = Field(min_length=1)
    fecha: date


class Plan(Consulta):
    nombre: str = Field(min_length=1)
    version: str = Field(min_length=1)
    existencias: list[Stock]
    entradas: list[Entrada]
    ejecucion_previa_id: str | None = None


class Carpeta(Cuerpo):
    carpeta: str


class Copia(Cuerpo):
    destino: str
    origen: str | None = None


def crear_app(base: Path | None = None, cliente: Path | None = None) -> FastAPI:
    ruta = (base or Path(os.environ.get('TFG_BASE', 'datos/prototipo.sqlite3'))).resolve()
    app = FastAPI(title='Planificación gastronómica', version=__version__, docs_url=None, redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])
    ventas, registro = SQLiteVentas(ruta), SQLiteEjecuciones(ruta)

    @app.middleware('http')
    async def origen_local(request: Request, siguiente):
        origen = request.headers.get('origin')
        permitidos = {f'http://{host}:{port}' for host in ('127.0.0.1','localhost') for port in (5173,8765)}
        if origen and origen not in permitidos:
            return JSONResponse({'mensaje':'Esta aplicación admite consultas desde su interfaz local.'},status_code=403)
        if request.method in ('POST','PUT','PATCH') and not request.headers.get('content-type','').startswith('application/json'):
            return JSONResponse({'mensaje':'La solicitud debe usar JSON.'},status_code=415)
        respuesta = await siguiente(request)
        if request.url.path.startswith('/api/'):
            respuesta.headers['Cache-Control'] = 'no-store'
        respuesta.headers['X-Content-Type-Options'] = 'nosniff'
        return respuesta

    @app.exception_handler(RequestValidationError)
    async def datos_invalidos(request, exc):
        errores = [{'campo':'.'.join(str(k) for k in e['loc']),'motivo':e['msg']} for e in exc.errors()]
        return JSONResponse({'mensaje':'Revisá los campos indicados. Las cantidades deben enviarse como texto decimal.',
                             'campos':errores},status_code=422)

    async def error_dominio(request, exc):
        estado = 404 if isinstance(exc,(LookupError,FileNotFoundError)) else 400
        return JSONResponse({'mensaje':str(exc)},status_code=estado)

    for clase in (ValueError,LookupError,FileNotFoundError,FileExistsError):
        app.add_exception_handler(clase,error_dominio)

    @app.exception_handler(sqlite3.Error)
    async def error_base(request, exc):
        return JSONResponse({'mensaje':'No se pudo consultar la base. Revisá la ruta y su integridad.'},status_code=503)

    def metadatos():
        return {'codigo':capturar_codigo(),'entorno':capturar_entorno()}

    def metodo(c: Consulta):
        referencia = None
        if c.metodo=='random_forest':
            if not c.seleccion_id:
                raise ValueError('Elegí una selección cerrada antes de usar Random Forest.')
            if c.seleccion_id not in {e['id'] for e in estado_base(ruta)[1]}:
                raise LookupError('La selección elegida no existe en esta base.')
            configuraciones, estados, referencia = configuracion_planificacion(ventas,registro,
                c.importacion,c.seleccion_id,recurso_json('protocolo_tp3_v1.json'),c.origen,metadatos())
            return RandomForest(configuraciones,estados), referencia
        if c.seleccion_id is not None:
            raise ValueError('Las referencias de selección se aplican solamente a Random Forest.')
        return (Persistencia() if c.metodo=='persistencia' else ReferenciaSemanal()), referencia

    @app.get('/api/estado')
    def estado():
        importaciones, ejecuciones = estado_base(ruta)
        return {'version':__version__, 'importaciones':importaciones,'ejecuciones':ejecuciones,
                'regla_ausencias':'Sin fila no se convierte automáticamente en cero; criterio vigente del TP3.',
                'naturaleza':{'ventas':'observadas','recetas':'modeladas','inventario':'sintético'}}

    @app.get('/api/productos')
    def productos(importacion: str):
        return normalizar(ventas.listar_productos(importacion))

    @app.get('/api/ventas')
    def historico(importacion: str, producto: str, desde: date, hasta: date):
        c = consultar_ventas(ventas,importacion,producto,desde,hasta)
        return {**normalizar(c),'dias_observados':c.dias_observados,'dias_sin_fila':c.dias_sin_fila,
                'total_observado':c.total_observado,'incompleta':c.incompleta}

    @app.get('/api/recetas')
    def recetas():
        recetario_configurado()  # Comprobar la versión antes de mostrar su descripción.
        return recurso_json('recetario_modelado_v1.json')

    @app.get('/api/disponibilidad')
    def disponibilidad(importacion: str, origen: date):
        por_producto = []
        for p in ventas.listar_productos(importacion):
            filas = consultar_disponibilidad(ventas,importacion,p.producto_id,origen)
            por_producto.append({'producto_id':p.producto_id,'nombre':p.nombre_modelado,'filas':filas})
        metodos = {}
        for nombre in ('persistencia','semanal','random_forest'):
            faltantes = [{'producto_id':p['producto_id'],'horizontes':[f['horizonte'] for f in p['filas']
                if f['metodo']==nombre and not f['disponible']],
                'causas':list(dict.fromkeys(f['causa'] for f in p['filas'] if f['metodo']==nombre and not f['disponible']))}
                for p in por_producto if any(f['metodo']==nombre and not f['disponible'] for f in p['filas'])]
            metodos[nombre] = {'completo':bool(por_producto) and not faltantes,'faltantes':faltantes}
        return {'origen':str(origen),'productos':por_producto,'metodos':metodos}

    @app.get('/api/ejecuciones/{identidad}')
    def ejecucion(identidad: str):
        if identidad not in {e['id'] for e in estado_base(ruta)[1]}:
            raise LookupError('La ejecución no existe en esta base.')
        return registro.recuperar(identidad)

    @app.get('/api/ejecuciones/{identidad}/insumos/{insumo}')
    def detalle(identidad: str, insumo: str):
        return normalizar(detallar_insumo(registro.recuperar(identidad),insumo))

    @app.post('/api/pronosticos')
    def pronostico(c: Pronostico):
        elegido, ref = metodo(c)
        return consultar_pronostico(ventas,registro,elegido,c.importacion,c.producto,c.origen,
                                   referencia_seleccion=ref,metadatos=metadatos())

    @app.post('/api/planes')
    def plan(c: Plan):
        elegido, ref = metodo(c)
        escenario = Escenario(c.nombre,c.version,
            tuple(Existencia(e.insumo_id,decimal_no_negativo(e.cantidad,'existencia'),e.unidad) for e in c.existencias),
            tuple(EntradaPrevista(e.insumo_id,e.fecha,decimal_no_negativo(e.cantidad,'entrada'),e.unidad,e.entrada_id)
                  for e in c.entradas))
        return planificar(ventas,registro,elegido,recetario_configurado(),c.importacion,c.origen,escenario,
                          referencia_seleccion=ref,ejecucion_previa_id=c.ejecucion_previa_id,metadatos=metadatos())

    @app.post('/api/importaciones')
    def importar(c: Carpeta):
        lote = preparar_ventas(Path(c.carpeta),recurso_json('manifiesto_fuentes.json'),recurso_json('protocolo_tp3_v1.json'))
        return {'importacion_id':ventas.guardar(lote)}

    @app.post('/api/copias')
    def copiar(c: Copia):
        return copiar_base(ruta,Path(c.destino))

    @app.post('/api/restauraciones')
    def restaurar(c: Copia):
        if not c.origen:
            raise ValueError('Elegí la copia que querés restaurar.')
        return restaurar_base(Path(c.origen),Path(c.destino))

    if cliente is not None and cliente.is_dir():
        app.mount('/',StaticFiles(directory=cliente,html=True),name='interfaz')
    return app


def main():
    import uvicorn
    import argparse
    p = argparse.ArgumentParser(description='Interfaz React local de planificación')
    p.add_argument('--base',type=Path,default=Path('datos/prototipo.sqlite3'))
    p.add_argument('--cliente',type=Path,default=Path('frontend/dist'))
    p.add_argument('--puerto',type=int,default=8765)
    args = p.parse_args()
    uvicorn.run(crear_app(args.base,args.cliente),host='127.0.0.1',port=args.puerto)


if __name__=='__main__':
    main()
