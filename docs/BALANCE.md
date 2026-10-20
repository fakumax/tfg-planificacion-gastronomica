# Balance con un plan manual modelado

El ejemplo permite probar recetas, entradas, saldos y alertas sin archivos de ventas.
Los valores del plan, las existencias y las reposiciones son de demostración y
no se presentan como predicciones o mediciones de una organización.

## Ejecución

```powershell
.\.venv\Scripts\python.exe -m planificacion calcular-balance --plan ejemplos/plan_manual.json --escenario ejemplos/escenario_sintetico.json
.\.venv\Scripts\python.exe -m planificacion listar-ejecuciones
.\.venv\Scripts\python.exe -m planificacion ver-ejecucion --ejecucion ID_OBTENIDO
```

La base puede elegirse con `--base ruta.sqlite3`. El recetario predeterminado es el
recurso versionado del paquete. `--recetario` admite otra ubicación de esos mismos
bytes; no habilita cambiar las recetas sin registrar una versión del protocolo.

## Cantidades conocidas del ejemplo

El 01/11/2025 se planifican diez unidades de P01 y cinco de P06; los otros productos
y fechas del horizonte tienen cantidad cero explícita. Las siete recetas modeladas
están cubiertas durante siete fechas consecutivas. Las existencias iniciales de
los insumos controlados son cero. Se prevén 600 g de cerdo para el 02/11/2025.

Según las fichas versionadas, el consumo del primer día incluye 600 g de cerdo,
500 g de vacuno, 1.050 g de arroz seco y 2.600 g de kimchi. La entrada del día
siguiente recupera el saldo de cerdo, pero no elimina su déficit del primer día.
Estas son expectativas aritméticas de un escenario, no resultados predictivos.

## Formatos

`plan_manual.json` contiene `tipo: "modelado"`, `desde` y una lista `cantidades`
con `producto_id`, `fecha` y `cantidad`. Deben figurar todos los productos y todas
las fechas, incluso cuando se planifica cero. Una combinación repetida se rechaza.

`escenario_sintetico.json` contiene `tipo: "sintetico"`, `nombre`, `version`, una
lista `existencias` y una lista `entradas`. Las existencias requieren `insumo_id`,
`cantidad` y `unidad`; las entradas agregan `fecha`. Se exigen existencias explícitas
de todos los insumos con control de stock, unidades compatibles y entradas positivas
dentro del horizonte. Los insumos de proceso sin control conservan su consumo,
pero no requieren existencias ni generan alertas de stock.

Las cantidades se operan con Decimal. En el resultado JSON se conservan como texto
para evitar perder precisión. No se aplican conversiones de unidad implícitas.

Las cantidades estimadas se conservan sin redondeo adicional. Un pronóstico
continuo representa cantidad esperada y se utiliza así para calcular insumos.
Esta es una decisión de implementación explícita; no altera las cantidades
observadas de los originales ni incorpora un redondeo implícito.

## Historial

Cada cálculo recibe un identificador nuevo y conserva plan, escenario, recetario,
fechas, versión de código, huellas y resultado. Repetir los mismos datos conserva
los mismos cálculos en otra ejecución. Recuperar un registro comprueba su contenido
y metadatos. Estas huellas no sustituyen autenticación o respaldo.
