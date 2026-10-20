# Procedencia y preparación de entradas

## Evidencia conservada

La ficha registrada es [DATA.GO.KR, conjunto 15134111](https://www.data.go.kr/data/15134111/fileData.do).
El manifiesto de `src/planificacion/recursos/manifiesto_fuentes.json` se conserva
con los bytes utilizados para registrar las entradas del experimento. Contiene URLs registradas,
huellas SHA-256, tamaños y propiedades de los tres originales anuales.

| Archivo original | Año interno | Filas del manifiesto |
| --- | --- | ---: |
| `high1_condo_2023_original.csv` | 2023 | 46.028 |
| `high1_condo_2024_original.csv` | 2024 | 41.270 |
| `high1_condo_2025_original.csv` | 2025 | 19.146 |

Las fechas históricas de auditoría y revisión del manifiesto no son fechas de
descarga nuevas. El 19/10/2026 se volvieron a ejecutar los controles locales de
datos y recetario antes de registrar esta base. No se hizo en esta operación una
nueva comprobación de disponibilidad de las URLs ni de condiciones de redistribución.

## Obtener y comprobar los archivos

1. Conservar los originales ya descargados o recuperarlos desde la ficha oficial y
   su historial. El conjunto comprende la versión actual y dos versiones históricas.
2. Usar los nombres de la tabla anterior y mantener los bytes originales. No
   volver a guardarlos desde Excel ni convertir su codificación CP949.
3. Colocarlos en `datos/originales/` o indicar otra carpeta al comando.
4. Ejecutar `planificacion verificar-entradas --directorio datos/originales` desde
   el entorno instalado, o su equivalente `python -m planificacion`.
5. Ante diferencias de huella o propiedades, detener la preparación e investigar.
   No reemplazar expectativas para que el archivo nuevo pase.

Los originales no se incluyen en el historial de Git. Las condiciones de uso se
revisarán antes de decidir su redistribución. Un fallo de descarga se informa como
acceso no verificado; no prueba que una versión no exista.

## Identidad y selección

Los tres años de la colección no son tres años acreditados de una misma serie.
En 2023 y 2024 hay cinco locales por año. En 2025 hay uno, In Room Dining(K), sin
coincidencia exacta con los nombres de los locales anteriores.

El protocolo `src/planificacion/recursos/protocolo_tp3_v1.json` registra los siete
productos de 2025 seleccionados para el experimento, sus identificadores originales y
etiquetas modeladas. No se unen locales o productos por una traducción parecida.
El archivo guarda además la huella del documento base y del catálogo utilizado.

## Ventas y escenario modelado

- Ventas: observaciones de los CSV con procedencia conservada.
- Recetas: fichas modeladas; su versión y archivos se identifican por huella.
- Existencias y entradas previstas: escenario sintético, no inventario observado.
- Resultados: solo se considerarán medidos cuando se ejecuten y registren.

La preparación conserva el calendario con ausencias explícitas. La ausencia de
una fila no se convierte en cero. Las cantidades cero explícitas u otros cambios de la fuente
requieren revisión antes de ampliar el contrato de la versión auditada.

El recurso `recetario_modelado_v1.json` conserva las fichas modeladas del proyecto,
sus supuestos y referencias, con los bytes y la huella fijados en el protocolo. Permite
ejecutar el escenario de recetas sin acceder a una carpeta personal. No contiene
un recetario observado ni un inventario real de High1. Los artículos o páginas
externas utilizados como referencia no se incorporan al repositorio.

## Consulta de condiciones de la ficha — 20/10/2026

La [ficha oficial vigente](https://www.data.go.kr/data/15134111/fileData.do), que
identifica el archivo de 2025, indica gratuidad (`무료`) y alcance de uso sin
restricciones (`이용허락범위 제한 없음`) en su apartado de condiciones. En esta
revisión no se comprobó por separado la licencia de cada versión histórica ni
se obtuvo el detalle del enlace de condiciones. No se extiende automáticamente
esa observación a otros materiales. Los CSV y las páginas de recetas siguen
excluidos de Git; su publicación requiere la revisión específica pendiente.
