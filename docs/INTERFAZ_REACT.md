# Uso de la interfaz

El cliente React consulta una API FastAPI local. Los pronósticos y balances se
calculan en Python y se conservan en SQLite. La pantalla de evaluación lee las
ejecuciones guardadas; navegar por sus gráficos no vuelve a entrenar los modelos.

## Pantallas

| Pantalla | Uso |
| --- | --- |
| Ventas | Elegir producto y período; consultar cobertura, gráfico, tabla y descarga. |
| Pronósticos | Consultar un producto, origen y método; revisar las causas si no puede calcularse. |
| Planificación | Comprobar disponibilidad conjunta, ingresar existencias y reposiciones, calcular y guardar el resultado. |
| Recetas | Consultar ingredientes, cantidades, estado, composición y referencias. |
| Evaluación | Filtrar métricas y comparaciones por producto y horizonte; revisar sensibilidad y exclusiones. |
| Historial | Recuperar una ejecución, descargarla y consultar el consumo por ingrediente. |
| Datos y copias | Importar archivos, crear una copia o restaurar en un destino nuevo. |

El tema claro u oscuro se conserva en el navegador. Los gráficos distinguen una
fecha sin observación de una cantidad cero.

## Planificación

Elegir el método y la fecha de origen antes de cargar el escenario. La comprobación
de disponibilidad no guarda un plan. Para el balance completo deben estar
disponibles todos los productos y horizontes requeridos.

Las existencias y reposiciones del escenario no se consideran inventario real.
Cada reposición necesita un identificador distinto. Las cantidades viajan como
texto decimal para conservar su precisión y se validan nuevamente en Python.

Un resultado con faltantes de insumos es un balance válido con alertas. Una
consulta sin datos suficientes no produce un plan completo. El resultado indica
el método utilizado; no se sustituye automáticamente por otro.

Desde el historial se puede tomar una ejecución como antecedente de un escenario
nuevo. La revisión conserva el resultado anterior y su vínculo con la nueva
ejecución.

## Arranque

Seguir [INSTALACION.md](INSTALACION.md) y abrir `http://127.0.0.1:8765`.
La base se elige con `--base` al arrancar el servidor y el cliente utiliza su
última importación. Cambiar a otra base requiere reiniciar el proceso.

Los experimentos de selección y evaluación se ejecutan por comandos siguiendo
[EVALUACION.md](EVALUACION.md). Las restricciones y pendientes técnicos están en
[LIMITACIONES.md](LIMITACIONES.md).
