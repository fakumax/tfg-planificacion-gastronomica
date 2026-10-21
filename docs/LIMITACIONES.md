# Alcance y limitaciones

## Datos y evaluación

El protocolo vigente conserva como no disponibles las combinaciones sin fila.
Esa decisión no prueba que la fuente tenga errores ni que una ausencia signifique
venta cero. Adoptar otra interpretación requiere registrar una preparación
distinta y evaluarla por separado, conservando los originales y los resultados
anteriores.

El plan completo necesita entradas para todos los productos y horizontes. La
cobertura de cada producto no equivale a disponibilidad conjunta de un plan.
La interfaz comprueba esa condición antes de guardar.

Random Forest no tiene garantizado superar a las referencias. Las comparaciones
con pocos casos se marcan exploratorias. Los horizontes solapados y el análisis
por bloques no acreditan independencia estadística ni intervalos de confianza.
No se midieron ahorros ni beneficios de una operación gastronómica real.

## Incidencias conocidas

- El estado del ingrediente se conserva en el recurso completo del recetario y
  se muestra en React, pero no se proyecta todavía en todos los registros
  normalizados e instantáneas de dominio.

Estas incidencias requieren correcciones y pruebas de regresión específicas.
No se consideran resueltas por el hecho de que las pruebas actuales pasen.

## Aplicación local

El cliente utiliza la última importación de la base elegida al iniciar. No ofrece
todavía un selector de base en pantalla. La instalación se ha comprobado en
Windows; las instrucciones para otros sistemas no equivalen a pruebas realizadas
en ellos. No se implementaron autenticación de red, roles ni despliegue para
varios usuarios. La revisión visual local no sustituye una prueba de usabilidad
externa o una certificación de accesibilidad.
