# Registro de cambios

Usar Conventional Commits con descripción corta en español:

```text
tipo: descripción
tipo(alcance): descripción
```

Tipos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `build`, `ci`
o `revert`. Agregar alcance solo cuando aclare el cambio. Escribir un verbo
concreto en presente, sin punto final y preferentemente en menos de 72 caracteres.

Ejemplos:

```text
docs: documenta la instalación
feat: verifica los originales antes de importarlos
fix: conserva el déficit previo a una reposición
test: comprueba la exclusión de información futura
```

Separar cambios independientes. Revisar lo preparado, ejecutar las comprobaciones
pertinentes y documentar los cambios de comportamiento. No confirmar datos
privados, claves, entornos, bases, respaldos ni resultados transitorios.

No cambiar huellas, resultados esperados, selección o protocolo para hacer pasar
una prueba. Una diferencia de fuente se investiga y registra como una nueva versión.
Los casos sintéticos de prueba deben indicarlo y no presentarse como mediciones
del negocio. Las traducciones de productos no sustituyen su identidad original.

## Ramas

`develop` concentra el desarrollo y `master` conserva la versión integrada.
Mantener los cambios completos, con sus comprobaciones, antes de integrarlos.

## TDD para las próximas implementaciones

Antes de implementar un comportamiento nuevo o corregir un fallo, escribir un
caso que exprese el contrato esperado y comprobar que falla por la razón prevista.
Implementar lo mínimo, comprobar el caso y después refactorizar manteniendo las
pruebas correctas. No presentar como TDD una prueba escrita después del código.

Cada cambio debe poder explicar qué caso motivó la implementación y qué
comprobaciones se ejecutaron. Mantener los commits de trabajo completos con sus
pruebas correctas; no hace falta publicar cada estado intermedio que falla.

Priorizar reglas observables y límites del negocio, en lugar de copiar la estructura
interna del código en las pruebas. Separar casos sintéticos, pruebas de integración,
instalación completa y evaluación predictiva. Las correcciones comienzan por un
caso que reproduzca el error.

## SOLID en la revisión de cambios

- Mantener una responsabilidad clara por servicio o módulo.
- Agregar métodos de pronóstico mediante contratos compatibles con los existentes.
- Conservar fechas, unidades, cobertura y errores al sustituir implementaciones.
- Definir interfaces pequeñas según lo que necesita cada caso de uso.
- Inyectar acceso a datos, archivos y modelos; evitar esas dependencias en las reglas
  de negocio. La interfaz presenta resultados y llama servicios.

Usar funciones y clases según la necesidad del problema; SOLID no exige agregar
herencia o capas sin un uso concreto. Ver [ARQUITECTURA.md](docs/ARQUITECTURA.md).
