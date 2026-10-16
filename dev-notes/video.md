# Vídeos: lo pendiente

Nota de desarrollo: se borra cuando lo que recoge esté hecho, validado y publicado.

## Grabar el propio curso (el 4): hecho

Perfil incorporado `course` (`start: unit:N`: paquete html servido en local o enlace de revisión de creator) y perfiles con
`login: false`. Falta probarlo a mano con un enlace de revisión real de creator.

## Montaje en datos (el 6)

Pasar los vídeos de Remotion de "el agente escribe React para cada vídeo" a un montaje en datos: un fichero por vídeo
(escenas, locución, capas) y una biblioteca de escenas que usan los tokens del tema, con una escena `libre` (un componente a
medida con un contrato fijo de props) como vía de escape.

- Ventajas: vídeos coherentes con el tema, más baratos (el agente rellena datos), revisables y editables sin tocar código;
  la duración de cada escena sale de su voz (cambiar un texto reajusta los tiempos); las comprobaciones (texto que desborda,
  texto que no se dice, anclajes a palabras que no se dicen) se pueden hacer sobre los datos, antes del render.
- Piezas: esquema del montaje (versionado y con migraciones), resolución de tiempos a partir de `<audio>.words.json`,
  escenas de la biblioteca (texto con medio, cifra con fuente, comparación, cierre, `Screencast`), capas ancladas a palabras,
  `coursekit media check` sobre el montaje, previsualización por fotogramas (`media sheet`) antes del render.
- Opcional: exportar la línea de tiempo a DaVinci (FCPXML 1.10 y OTIO) para retocar a mano.
