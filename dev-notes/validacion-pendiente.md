# Validaciones pendientes

Funciones publicadas y documentadas a las que les falta probarse en un caso real. Cuando se prueben, se borra su línea; el
README (`Status › To prove on a whole course`) dice lo mismo para quien usa coursekit.

## Evaluaciones aparte y bancos de preguntas

Documentado en `docs/*/08-assembly.md › Where the tests go` y `03-commands.md › coursekit delivery`.

- Montaje real en creator con `placement: separate` (el contenido que crea `leccionesEvaluacion: "separadas"`) y con el
  contenido del banco.
- Importación real de los formatos en un LMS: Moodle para gift y moodle-xml, otro para qti.

## Lo aprendido en el curso piloto (0.5.0)

Documentado en `docs/*/06-content.md › Course decisions` y en las reglas de `verify`, `media`, `brief` y `approve`.

- Probarlo en un curso real entero.
- Descartado, para que no se proponga de nuevo: un comando `coursekit decide` (basta el fichero `decisions.md`; se añade si
  se echa en falta) y un aviso de `verify` para «ya no existe» o «antes se llamaba» (demasiados falsos positivos: un curso
  sobre un cambio de norma tiene que decirlo; queda como norma de las skills).

## Vídeos

Documentado en `docs/*/07-media.md › Video montage` y `03-commands.md › coursekit video` y `coursekit capture`.

- Grabar el propio curso con un enlace de revisión real de creator.
- Abrir en DaVinci Resolve de verdad la línea de tiempo de `coursekit video export` (probada de punta a punta, nunca abierta
  en el editor).
- Descartado: sustituir las piezas de la biblioteca por las del proyecto con alias de webpack; se hace sin tocar la
  configuración de Remotion del proyecto.
