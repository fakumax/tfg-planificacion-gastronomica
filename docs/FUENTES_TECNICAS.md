# Referencias técnicas de implementación

Consultadas el 19/10/2026. Estas referencias describen APIs; el protocolo
experimental y sus umbrales se fijan en el recurso versionado, no de los valores predeterminados
de una biblioteca.

- [RandomForestRegressor, documentación de scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html).
  La página consultada corresponde a 1.9.1. Se fijan semilla y parámetros; se conserva
  el listado efectivo del estimador. Cada ajuste utiliza un solo trabajo.
- [ProcessPoolExecutor, Python 3.12](https://docs.python.org/3.12/library/concurrent.futures.html#processpoolexecutor).
  La ejecución por procesos requiere funciones importables y protección del punto
  de entrada. Se tendrá en cuenta al ejecutar productos en paralelo.
- [Paquete scikit-learn en PyPI](https://pypi.org/project/scikit-learn/).
  La dependencia se instaló desde el índice oficial con versión 1.9.1. Las versiones
  efectivamente utilizadas quedan en el archivo de restricciones del repositorio.

Consultadas el 20/10/2026 para la interfaz y recuperación:

- [Configuración de Streamlit](https://docs.streamlit.io/develop/api-reference/configuration/config.toml).
  Servidor limitado a `127.0.0.1`, protecciones CORS y XSRF activas, estadísticas de
  uso desactivadas. Esto no constituye autenticación para un alojamiento público.
- [Editor de datos](https://docs.streamlit.io/develop/api-reference/data/st.data_editor).
  Existencias y entradas se editan en la pantalla; los servicios vuelven a validar
  cantidades, unidades, fechas y cobertura antes de guardar.
- [AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
  Pruebas de pantallas con Streamlit 1.66.0 y adaptadores reales, además de revisión
  en navegador. No sustituyen una prueba de usabilidad con participantes.
- [Respaldo de SQLite en Python](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup).
  Copia consistente que incluye los datos confirmados de una base abierta.
