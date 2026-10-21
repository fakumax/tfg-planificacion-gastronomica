# Validación y resultados medidos

Evaluación reproducida el 21/10/2026 con el código `d364c99`, Python 3.12.14 y
las dependencias de `requirements.lock`. Se utilizó el catálogo de siete
productos de In Room Dining(K), 2025, definido en el protocolo versionado.
Las ausencias de filas se conservaron como no disponibles.

## Identificación del experimento

- Núcleo: `19425b8d3a5a1f8685d8f0f28f8de9f1964832acd983cd17b82830fbf9ad57dd`.
- Selección: `4e47d03913484549bcebfce8110d6bea`.
- Evaluación: `26b64664f1e14fd5a2d2bbfe7a66a3b5`.
- Validación: orígenes del 30/09 al 24/10/2025.
- Prueba: 55 orígenes, del 31/10 al 24/12/2025, con horizontes de uno a siete días.

La configuración se conservó antes de ejecutar la prueba. Cada ajuste emplea
solo ejemplos cuya respuesta ya se conoce al cierre del origen correspondiente.
La nueva selección y evaluación reprodujeron exactamente los resultados
numéricos anteriores; sus identificadores y huellas se conservaron por separado.

## Cobertura y errores

De 2.695 casos producto–origen–horizonte, 1.931 fueron admisibles en común para
los tres métodos: 5.793 predicciones evaluadas. Los 764 casos restantes conservaron
sus causas de exclusión. No se completaron con ceros.

| Producto | Orígenes evaluables por horizonte | Árboles | Estado de configuración | MAE de RF: mínimo–máximo entre H1 y H7 |
| --- | ---: | ---: | --- | ---: |
| P01 | 55 | 300 | Seleccionada por validación | 3,611–4,086 |
| P02 | 42 | 100 | Seleccionada por validación | 2,655–3,141 |
| P03 | 50–51 | 300 | Seleccionada por validación | 2,449–2,877 |
| P04 | 31 | 100 | Prefijada por validación insuficiente | 1,415–1,778 |
| P05 | 44–45 | 100 | Seleccionada por validación | 1,445–1,681 |
| P06 | 38 | 300 | Seleccionada por validación | 1,308–1,654 |
| P07 | 13–16 | 100 | Prefijada por validación insuficiente | 0,792–1,261 |

Todas las configuraciones usan profundidad máxima 5, mínimo de dos ejemplos
por hoja y semilla 42. El MAE está expresado en unidades vendidas. El rango
de la tabla resume los siete errores por horizonte; no es un intervalo de
confianza ni una métrica agregada entre productos.

Por MAE, RF obtuvo un error menor que persistencia en 48 de las 49 combinaciones
producto–horizonte y menor que la referencia semanal en 44 de 49. También se
conservaron los resultados en los que RF fue inferior:

- Frente a persistencia: P05, H7.
- Frente a la referencia semanal: P05, H6–H7; P07, H1–H3.

Estos conteos describen esta muestra; no demuestran superioridad estadística
ni sustituyen la lectura de MAE, RMSE y MASE de cada grupo.

## Comprobación independiente

Se leyeron directamente las ventas del CSV original y se reconstruyeron
agregación diaria, características temporales, ejemplos disponibles, respuestas,
referencias y escalas MASE, sin importar esos cálculos del programa.

Se comprobaron los 2.695 casos y las 5.793 predicciones; se recalcularon MAE,
RMSE y MASE para 147 grupos de evaluación y 147 de sensibilidad. Se reajustaron
además 14 bosques independientes, tomando el primer y último registro RF de
cada producto: las predicciones coincidieron exactamente. Se verificaron
las huellas de los ocho archivos de la exportación.

## Disponibilidad del plan completo

Con este protocolo, el plan RF conjunto estuvo disponible en 10 de los 55
orígenes de prueba: 18,2 %. Este porcentaje mide disponibilidad de entradas y
ejemplos de entrenamiento para planificar los siete productos; no mide precisión.
La condición se calcula con información conocida al cierre de cada origen.

El origen de demostración `2025-11-13` se eligió previamente por disponibilidad,
sin utilizar los errores para escogerlo. El sistema debe rechazar un plan
incompleto y explicar su causa.

P07/H3 dispone de 13 orígenes y se marca exploratorio. El análisis conjunto de
bloques de P07 contiene un solo bloque completo; retirarlo deja cero bloques,
por lo que no permite afirmar robustez. Los horizontes solapados tampoco
acreditan independencia.

Las recetas son modeladas y el inventario y las reposiciones son sintéticos.
No se midieron ahorros ni beneficios operativos en un establecimiento.

## Recorrido funcional e instalación

Se comprobaron por HTTP las consultas de ventas, recetas y disponibilidad; los
tres métodos generaron 49 cantidades para el origen de demostración. El
escenario inicial produjo 37 alertas, coherentes con sus existencias sintéticas.
Se revisaron los desgloses de los 38 insumos de cada uno de los tres planes.

Una revisión con existencias suficientes quedó sin alertas y conservó el
antecedente. Una reposición tardía mantuvo el primer déficit. El origen no
disponible y la selección anterior incompatible fueron rechazados sin guardar
planes parciales. La copia en un destino existente también se rechazó.

El respaldo y la restauración conservaron las 33 ejecuciones de la base de
ensayo, incluidas las anteriores. La base habitual permaneció intacta. Esta
comprobación corresponde a un recorrido local y secuencial.

Se instaló el paquete desde el árbol de Git y las versiones fijadas en un
entorno nuevo, fuera del repositorio. La reproducción del plan RF produjo
idénticos resultados, huella de entrada y huella de contenido en otro ID de
ejecución.

| Operación observada | Segundos |
| --- | ---: |
| Selección por validación, cuatro procesos | 374,20 |
| Evaluación de prueba, cuatro procesos | 272,94 |
| Instalación en el entorno nuevo | 200,30 |
| Plan RF en la instalación aislada | 8,19 |
| Respaldo integral por HTTP | 338,25 |
| Restauración por HTTP | 70,55 |

Son mediciones de este equipo durante la comprobación, con otras tareas
locales. El respaldo y la restauración incluyen controles de integridad; sus
carpetas estaban en una unidad sincronizada. No constituyen un ensayo de carga
ni garantizan tiempos de respuesta en otras instalaciones.

## Reproducción

Seguir [la instalación](INSTALACION.md), [la preparación de datos](DATOS.md) y
[el orden de selección, prueba y exportación](EVALUACION.md). Los identificadores
de una ejecución nueva serán distintos; la comparación debe considerar
entradas, configuración, entorno, núcleo y resultados conservados.
