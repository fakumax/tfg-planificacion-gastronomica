# Arquitectura del prototipo

## Componentes

Aplicación local con cliente React y TypeScript, API FastAPI, servicios Python
y persistencia SQLite. La interfaz Streamlit anterior permanece disponible.

Los servicios de negocio deben poder ejecutarse sin la interfaz para comprobarlos
con entradas conocidas. Los resultados se identifican por ejecución y no se
sobrescriben cuando cambia el escenario.

| Componente | Responsabilidad | Estado |
| --- | --- | --- |
| `src/planificacion/cli.py` | Comandos de importación, consulta, planificación, evaluación y recuperación | Implementado |
| `src/planificacion/entradas.py` | Huellas, esquema, fechas, cantidades, claves y cobertura | Implementado |
| `src/planificacion/recursos/` | Manifiesto y protocolo experimental versionados | Registrado |
| `dominio/ventas.py` | Tipos inmutables y procedencia de ventas | Implementado |
| `infraestructura/csv_ventas.py` | Preparación diaria sin imputación de ausencias | Implementado |
| `infraestructura/sqlite_ventas.py` | Importaciones atómicas e historial en SQLite | Implementado |
| `aplicacion/ventas.py` | Consulta y cobertura mediante un contrato de lectura | Implementado |
| `dominio/recetas.py` y `dominio/balance.py` | Consumo decimal, cobertura, entradas, saldos y alertas | Implementado |
| `dominio/pronosticos.py` | Contrato sustituible y persistencia | Implementado |
| `aplicacion/planificacion.py` | Ventas hasta el origen → pronóstico → balance → historial | Implementado |
| `dominio/temporal.py` e `infraestructura/random_forest.py` | Ejemplos conocidos en cada origen, referencia semanal y Random Forest | Implementado |
| `aplicacion/seleccion.py`, `comparacion.py` y `experimento.py` | Selección conservada antes de prueba, casos comunes, métricas y sensibilidad | Implementado |
| `aplicacion/balance.py` y `infraestructura/sqlite_ejecuciones.py` | Entradas, versiones y resultados recuperables por contrato | Implementado |
| `presentacion/web.py` | Consulta, escenarios, balance, historial y comparación en Streamlit | Implementado |
| `presentacion/api.py` | Contratos HTTP locales, validación de solicitudes y composición de los servicios existentes | Implementado y probado |
| `frontend/src/` | Pantallas React, presentación de cantidades, gráficos y temas | Primer incremento conectado |
| `infraestructura/respaldos.py` | Copia consistente de la base y comprobación | Implementado |
| `infraestructura/exportacion.py` | Evidencia completa en una carpeta nueva y manifiesto de huellas | Implementado |
| `aplicacion/pronosticos.py` | Consulta individual y disponibilidad sin completar un balance | Implementado |
| `aplicacion/revisiones.py` y `aplicacion/detalle.py` | Escenario recuperable y explicación con sus entradas conservadas | Implementado |
| `infraestructura/modelo_relacional.py` | Dieciocho entidades, vista de alertas, proyección transaccional y actualización con conservación | Implementado |
| `presentacion/consultas.py` | Gráfico con cortes y causas de exclusión o métrica no calculable | Implementado |

El esquema físico conserva las seis tablas previas junto con las dieciocho del
modelo y la relación de estados por recetario: 25 tablas y una vista.
`EstadoInsumo` vincula el estado utilizable con la versión exacta del recetario;
si una instantánea anterior no lo registraba, se conserva como no informado.
Las anteriores mantienen procedencia e instantáneas
identificadas por huellas; las nuevas agregan las claves, relaciones y consultas del
diseño. La verificación contrasta la proyección contra una reconstrucción en memoria.
No se presenta esta extensión de compatibilidad como una copia física exacta del DER.

## Flujo implementado

Originales de solo lectura → verificación → preparación con ausencias explícitas →
SQLite → consulta de un origen → pronóstico identificado → cantidades por receta →
balance con escenario sintético → alertas y ejecución conservada.

La evaluación temporal se ejecuta por separado y comparte reglas con el pronóstico.
Seleccionar parámetros por validación y reportar prueba son operaciones distintas.
La interfaz no debe introducir una lógica de fechas o balance diferente de los servicios.

## Aplicación de SOLID

| Principio | Regla para este proyecto |
| --- | --- |
| S: responsabilidad única | Separar lectura y escritura, preparación, cálculo de consumo, balance, pronóstico y presentación. Cada componente tiene una razón concreta para cambiar. |
| O: abierto a extensión | Incorporar métodos de pronóstico a través de un contrato común. La integración del balance y la presentación no dependen del algoritmo elegido. |
| L: sustitución | Cada implementación respeta el mismo significado de origen, horizonte, cantidades, cobertura y resultado no calculable. Una sustitución no convierte ausencia o error en cero. |
| I: segregación de interfaces | Definir contratos pequeños para consultar ventas, conservar ejecuciones o pronosticar; evitar un repositorio general que obligue a implementar operaciones ajenas. |
| D: inversión de dependencias | Los casos de uso dependen de contratos y reciben implementaciones. Los adaptadores CSV, SQLite y scikit-learn satisfacen esos contratos; las reglas de negocio no importan Streamlit o SQLite. |

Las interfaces se expresan con `typing.Protocol` cuando existe la dependencia
concreta. No es necesario crear jerarquías de clases para cada cálculo. Las
funciones de reglas de negocio pueden permanecer independientes y recibir sus
datos explícitamente.

### Separación vigente

- **Dominio:** cantidades, fechas, consumo, saldo y reglas de aceptación, sin acceso
  a archivos, base de datos o interfaz.
- **Aplicación:** casos de uso que coordinan importación, consulta, planificación y
  evaluación, recibiendo las dependencias que necesitan.
- **Infraestructura:** lectura de CSV, SQLite, archivos de resultados y adaptadores
  de modelos.
- **Presentación:** CLI, API, React y Streamlit, que validan la interacción y llaman a los casos
  de uso sin duplicar sus cálculos.

La composición de CLI, API y Streamlit elige los adaptadores. Los casos de uso no
importan SQLite, scikit-learn ni Streamlit; el dominio no importa adaptadores.
Los trabajos numéricos por producto reciben datos explícitos y devuelven resultados
completos. La orquestación impide conservar un experimento parcial como terminado.

## Comprobación con TDD

El ciclo es caso que falla → implementación mínima → refactorización con pruebas
correctas. Las reglas se prueban sin Streamlit y, cuando corresponde, con repositorios
en memoria. SQLite se prueba además con una base temporal real, y la interfaz
se comprueba con AppTest sobre los mismos servicios y adaptadores.

Antes de modificar el código existente, fijar con pruebas los comportamientos que
deben conservarse. La existencia de pruebas anteriores no demuestra que se hayan
escrito antes de la implementación. Ver [CONTRIBUTING.md](../CONTRIBUTING.md).

## Directorios

- `src/`: paquete instalable y recursos versionados.
- `tests/`: casos sintéticos de comprobación.
- `docs/`: documentación técnica.
- `datos/originales/`: archivos locales excluidos de Git.
- `datos/derivados/`: preparación reproducible excluida de Git.
- `resultados/`: exportaciones y salidas locales excluidas de Git.
- `respaldos/`: copias locales excluidas de Git.

Las restricciones e incidencias pendientes se describen en [LIMITACIONES.md](LIMITACIONES.md).
