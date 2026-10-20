# Pruebas

La suite combina casos de dominio, integración con SQLite, comandos, API e
interfaz. Los datos sintéticos expresan resultados conocidos y no son mediciones
de precisión predictiva.

## Ejecutar

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe herramientas/iniciar_interfaz.py --comprobar --solo-construir
```

Para una revisión específica de la API:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_api.py -v
```

## Cobertura de comportamiento

| Área | Comprobaciones |
| --- | --- |
| Entradas | Huellas, campos, fechas, cantidades, identidad y rechazo de lotes incompletos. |
| Importación | Transacciones, idempotencia, procedencia y calendario con ausencias explícitas. |
| Recetas y balance | Unidades, cobertura, cantidades decimales, déficits y reposiciones posteriores. |
| Pronósticos | Corte temporal, ejemplos conocidos, rezagos por fecha y mínimos de entrenamiento. |
| Evaluación | Selección previa a prueba, casos comunes, métricas no disponibles y sensibilidad. |
| Historial | Ejecuciones inmutables, revisiones vinculadas y detalle de consumo. |
| Persistencia | Proyección relacional, actualización, copias y restauración en destinos nuevos. |
| API | Validación de solicitudes, consultas sin escritura, origen web y cantidades como texto. |
| Cliente | Fechas, diferencia entre hueco y cero, decimales y mensajes de faltantes. |

Una prueba correcta valida su contrato y sus entradas. No demuestra por sí sola
que todo el modelo, la interfaz o la aplicación sean adecuados para uso real.
Los pendientes conocidos se conservan en [LIMITACIONES.md](LIMITACIONES.md).

La evaluación con ventas observadas se ejecuta por separado siguiendo
[EVALUACION.md](EVALUACION.md). Los controles de integridad de archivos no
sustituyen esa evaluación ni justifican afirmar ahorros operativos.
