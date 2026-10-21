# Evaluación del protocolo cerrado

El protocolo experimental conserva el calendario,
las variables, la grilla, la semilla, las exclusiones ni los umbrales. La elección
de hasta cuatro procesos por producto es una decisión de ejecución; cada bosque
usa un solo trabajo. Las pruebas sintéticas verifican reglas y no son una medida
de precisión con las ventas observadas.

## Orden de ejecución

Importar primero los originales según el manual y reemplazar `IMPORTACION`:

```powershell
.\.venv\Scripts\python.exe -m planificacion seleccionar-modelos --importacion IMPORTACION --trabajadores 2
```

Conservar el `ejecucion_id` como `SELECCION`. Solo después:

```powershell
.\.venv\Scripts\python.exe -m planificacion evaluar-modelos --importacion IMPORTACION --seleccion SELECCION --trabajadores 2
```

Conservar el segundo identificador como `EVALUACION` y elegir una carpeta nueva:

```powershell
.\.venv\Scripts\python.exe -m planificacion exportar-evaluacion --ejecucion EVALUACION --directorio resultados/evaluacion_01
```

Se exportan la ejecución y selección completas en JSON, predicciones, métricas,
sensibilidad, todos los casos con sus causas de exclusión, configuraciones y el
retiro de bloques de P07. El manifiesto final contiene hashes. Una exportación sin
manifiesto está incompleta; repetirla en otra carpeta sin borrar la anterior.

El historial conserva entradas, protocolo, tiempos, versiones de bibliotecas y
huellas del código. La prueba exige la misma importación, entorno y núcleo
numérico de la selección. Si cambian, se registra primero una nueva selección.
El estado prefijado por validación insuficiente se informa expresamente.

Antes de guardar una planificación, consulta o evaluación, se comprueban la
existencia y huella de la selección, su importación, entorno, núcleo y parámetros.
Persistencia y referencia semanal no admiten una selección de Random Forest.

## Uso en planificación

```powershell
.\.venv\Scripts\python.exe -m planificacion planificar --importacion IMPORTACION --origen 2025-11-01 --metodo random_forest --seleccion SELECCION --escenario ejemplos/escenario_planificacion.json
```

Random Forest exige la selección cerrada y un origen del período de prueba;
si el producto no es ajustable o faltan entradas, se bloquea el plan completo.
También está disponible `--metodo semanal`; no sustituye automáticamente al
método elegido. El inventario del ejemplo sigue siendo sintético.

## Lectura de resultados

Para demostrar los tres métodos con entradas disponibles en todos los productos,
usar origen `2025-11-13` y `ejemplos/escenario_demostracion.json`. La fecha se eligió
por disponibilidad, sin usar errores. El origen del ejemplo inicial, `2025-11-01`,
puede servir a persistencia, pero no reúne las entradas necesarias para el plan
completo con Random Forest; el programa lo rechaza sin sustituir métodos.

La comparación usa los mismos casos por producto y horizonte en los tres métodos.
Se informan MAE, RMSE, MASE calculable, dispersión, cantidad de casos y pares de
escala. Sin casos, los errores quedan no disponibles. Con menos de catorce
orígenes por horizonte, la comparación se marca exploratoria. Una predicción
inferior a las referencias se conserva; no es un fallo de aceptación funcional.

Se informa sensibilidad con orígenes separados siete días por horizonte. Para
P07 se usan además bloques con los siete horizontes y métodos presentes, ordenados
cronológicamente y separados siete días, y se retira uno por vez. Esta elección de
implementación se fijó antes de medir; no acredita independencia estadística.
La precisión predictiva no demuestra ahorro ni mejoras de un comercio real.
