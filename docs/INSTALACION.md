# Instalación

## Entorno Python

Se requiere Python 3.12 o posterior. Desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock -e .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m planificacion estado
```

En macOS o Linux, reemplazar `.\.venv\Scripts\python.exe` por `.venv/bin/python`.
Los lanzadores de Windows no se usan en esos sistemas. Las comprobaciones de
instalación realizadas corresponden a Windows.

## Interfaz React

Instalar Node.js compatible con Vite: 20.19+ o 22.12+, junto con npm. Las versiones
del cliente están fijadas en `frontend/package-lock.json`.

```powershell
.\.venv\Scripts\python.exe herramientas/iniciar_interfaz.py
```

En Windows puede ejecutarse `iniciar_interfaz.bat`. Abrir
`http://127.0.0.1:8765`. Para detener el servidor, usar Ctrl+C en la terminal.

El lanzador copia los fuentes del cliente a una carpeta temporal, instala las
dependencias y construye la aplicación. Esto evita problemas de escritura de
`node_modules` en carpetas sincronizadas. El primer arranque necesita acceso a
npm; una construcción sin cambios se reutiliza. Si se vacía la caché, se vuelve
a construir.

Para utilizar otra base:

```powershell
.\.venv\Scripts\python.exe herramientas/iniciar_interfaz.py --base datos/otra_base.sqlite3
```

La base predeterminada es `datos/prototipo.sqlite3`. El cliente usa la última
importación disponible en esa base. Para cambiar de base, reiniciar el servidor
con `--base`; la pantalla todavía no ofrece ese selector.

## Preparar los datos

Obtener y conservar los originales según [DATOS.md](DATOS.md). Después:

```powershell
.\.venv\Scripts\python.exe -m planificacion verificar-entradas --directorio datos/originales
.\.venv\Scripts\python.exe -m planificacion importar-ventas --directorio datos/originales
.\.venv\Scripts\python.exe -m planificacion listar-importaciones
```

Los comandos verifican huellas y propiedades antes de importar. Una entrada
incompleta o distinta se rechaza; no se modifica el original para aceptarla.
Repetir la misma importación no duplica los registros.

## Desarrollo del cliente

Desde `frontend`, en una carpeta local sin restricciones de escritura:

```text
npm ci
npm test
npm run dev
```

En otra terminal, desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m planificacion.presentacion.api
```

Vite abre el puerto 5173 y envía las solicitudes `/api` al servidor del puerto
8765. Los cálculos se ejecutan en Python.

Para probar y construir el cliente con el mismo lanzador de producción:

```powershell
.\.venv\Scripts\python.exe herramientas/iniciar_interfaz.py --comprobar --solo-construir
```

## Interfaz Streamlit

La implementación anterior sigue disponible:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.headless true
```

Abrir `http://127.0.0.1:8501`, o ejecutar `iniciar_app.bat` en Windows.
Consultar [las limitaciones de esa interfaz](LIMITACIONES.md).

## Actualizar una base anterior

Cerrar el servidor y elegir un destino nuevo para la copia:

```powershell
.\.venv\Scripts\python.exe -m planificacion actualizar-base --base datos/prototipo.sqlite3 --respaldo respaldos/antes_actualizacion.sqlite3
```

La actualización conserva los registros anteriores y revierte la transacción si
falla. Una selección de modelos con un núcleo o entorno diferente debe volver a
registrarse siguiendo [EVALUACION.md](EVALUACION.md).

Los servidores están limitados al equipo local. No se implementaron cuentas,
roles ni autenticación para publicar la aplicación como servicio de red.
