# Planificación gastronómica

Aplicación local para consultar ventas, generar pronósticos y calcular las
necesidades de insumos a partir de recetas, existencias y reposiciones.

La interfaz usa React, TypeScript y Recharts. Una API FastAPI conecta las
pantallas con los servicios Python y la base SQLite. Los métodos de pronóstico
disponibles son persistencia, referencia semanal y Random Forest.

## Funciones

- Consulta de ventas por producto y fecha, con cobertura y procedencia.
- Pronósticos por producto para un horizonte de siete días.
- Planificación de insumos y alertas de faltantes con detalle de consumo.
- Recetas versionadas, escenarios identificados e historial de ejecuciones.
- Comparación temporal de métodos con MAE, RMSE, MASE y causas de exclusión.
- Exportación de resultados, copias y restauración de bases locales.
- Interfaz con temas claro y oscuro.

Las ventas proceden de archivos externos; las recetas son modeladas y el
inventario de los ejemplos es sintético. Las ausencias de registros se conservan
como no disponibles según el protocolo vigente. Ver [datos](docs/DATOS.md) y
[limitaciones](docs/LIMITACIONES.md) antes de interpretar los resultados.

## Requisitos

- Python 3.12 o posterior.
- Node.js 20.19+ o 22.12+ y npm para construir la interfaz.
- Windows para los lanzadores `.bat`; los comandos Python también pueden
  ejecutarse directamente.

## Instalación y arranque

Desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock -e .
.\.venv\Scripts\python.exe herramientas/iniciar_interfaz.py
```

Abrir `http://127.0.0.1:8765` y mantener el proceso activo. En Windows también se
puede usar `iniciar_interfaz.bat`. El primer arranque instala y construye el
cliente en una carpeta temporal; los siguientes reutilizan esa construcción
mientras no cambien los fuentes. Ver [instalación](docs/INSTALACION.md).

Los CSV no se distribuyen con el código. Para preparar una base con los archivos
originales, seguir [procedencia y preparación](docs/DATOS.md) y ejecutar:

```powershell
.\.venv\Scripts\python.exe -m planificacion verificar-entradas --directorio datos/originales
.\.venv\Scripts\python.exe -m planificacion importar-ventas --directorio datos/originales
```

## Ejemplo sin archivos de ventas

El ejemplo incluido permite calcular un balance con cantidades conocidas:

```powershell
.\.venv\Scripts\python.exe -m planificacion calcular-balance --plan ejemplos/plan_manual.json --escenario ejemplos/escenario_sintetico.json
.\.venv\Scripts\python.exe -m planificacion listar-ejecuciones
```

El plan y el inventario de ese ejemplo son de demostración. Ver
[balance y formatos](docs/BALANCE.md).

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe herramientas/iniciar_interfaz.py --comprobar --solo-construir
```

La segunda orden ejecuta las pruebas del cliente y construye la interfaz.
Los tests comprueban comportamientos concretos; la calidad predictiva se evalúa
por separado con los datos y el protocolo registrados.

## Documentación

- [Instalación](docs/INSTALACION.md).
- [Uso de la interfaz](docs/INTERFAZ_REACT.md).
- [Datos y preparación](docs/DATOS.md).
- [Arquitectura](docs/ARQUITECTURA.md).
- [Balance de insumos](docs/BALANCE.md).
- [Evaluación de pronósticos](docs/EVALUACION.md).
- [Copias y recuperación](docs/RECUPERACION.md).
- [Pruebas](docs/PRUEBAS_ACEPTACION.md).
- [Limitaciones conocidas](docs/LIMITACIONES.md).
- [Referencias técnicas](docs/FUENTES_TECNICAS.md).
- [Contribución](CONTRIBUTING.md).
