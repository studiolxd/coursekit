# Vídeos: lo pendiente

Nota de desarrollo: se borra cuando lo que recoge esté hecho, validado y publicado.

## Grabar el propio curso (el 4)

Vídeos que enseñan el curso que produce coursekit ("cómo se navega este curso", una demo para el cliente), con el modo
navegador de `coursekit capture`, sin red de terceros ni credenciales y sin datos personales (el contenido es nuestro).

- **Backend html:** servir en local (`127.0.0.1`, un puerto libre) el paquete construido (`courses/<CODE>/assembly/html/…`)
  y abrirlo como una captura más. El perfil sería implícito (`local`), con el dominio `127.0.0.1` permitido.
- **Backend creator:** el enlace de revisión de cada unidad (`units[N].links.review`, el que usa `coursekit client`).
  - Perfil sin inicio de sesión: `login: false` en `capture.yaml › profiles` (sin `capture login`; el permiso de `allow`
    no exige sesión).
  - `start: unit:2` en el bloque `capture` del guion → coursekit pone el enlace de revisión de esa unidad.
  - Si la página de revisión enseña comentarios con nombres, el DOM los sustituye; mejor ocultar el panel con un
    `selector` del bloque.

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
