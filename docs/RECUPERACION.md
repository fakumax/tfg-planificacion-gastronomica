# Copias y recuperación local

Cerrar una operación de la aplicación antes de copiar. Desde la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe -m planificacion respaldar-base --destino respaldos/copia_01.sqlite3
.\.venv\Scripts\python.exe -m planificacion restaurar-base --copia respaldos/copia_01.sqlite3 --destino datos/restaurada_01.sqlite3
.\.venv\Scripts\python.exe -m planificacion listar-importaciones --base datos/restaurada_01.sqlite3
.\.venv\Scripts\python.exe -m planificacion listar-ejecuciones --base datos/restaurada_01.sqlite3
```

La copia y restauración requieren destinos nuevos. La base activa no se reemplaza.
Se usa `Connection.backup`, que incorpora los datos confirmados aunque estén en
WAL; no se copia únicamente el archivo principal de una base abierta.

Conservar juntos la copia y su archivo `.sqlite3.json`. El manifiesto contiene
fecha, huella y recuentos. Una copia sin manifiesto está incompleta. Antes y después
se comprueban integridad SQLite, relaciones y huellas del contenido del prototipo.
La huella detecta cambios accidentales; no es una firma de autenticidad.

Conservar al menos una copia fuera de la carpeta activa, con los mismos permisos
de acceso que la base original. No se implementa eliminación automática ni se
promete tolerancia a fallos del mismo disco. El autor decide su retención.

Para usar la restaurada, iniciar los comandos con `--base` o arrancar el servidor React con
`herramientas/iniciar_interfaz.py --base datos/restaurada_01.sqlite3`. Comprobar primero una consulta y una ejecución conocida. Conservar
la base previa hasta terminar la revisión.
