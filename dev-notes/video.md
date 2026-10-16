# Vídeos: lo pendiente

Nota de desarrollo: se borra cuando lo que recoge esté hecho, validado y publicado.

## Grabar el propio curso (el 4): hecho

Perfil incorporado `course` (`start: unit:N`: paquete html servido en local o enlace de revisión de creator) y perfiles con
`login: false`. Falta probarlo a mano con un enlace de revisión real de creator.

## Montaje en datos (el 6)

Los vídeos de Remotion pasan de "el agente escribe React para cada vídeo" a un montaje en datos
(`media/scripts/<id>.video.yaml`) con piezas atómicas que usan el tema. Componer a mano sigue siendo una receta (`remotion`);
el montaje es la primera opción para vídeos nuevos (`montage`).

### Niveles (cada uno solo con el de abajo)

- **Tokens**: los del tema del curso (o del proyecto), que llegan a Remotion como props (no importados: un curso puede tener
  tema propio), más tokens de movimiento por defecto (duraciones, curvas, ritmo).
- **Átomos**: `Heading`, `Text`, `MediaSlot`, `Counter`, `Underline`, `Ring`, `Background`; de movimiento `Enter`, `Stagger`,
  y el gancho `useAt("palabra")` (cuándo se dice algo, en fotogramas de la escena).
- **Moléculas**: bloque de título, lista con marcas, cifra con fuente, columna de comparación, rótulo inferior.
- **Escenas**: carpeta con `index.tsx` y `scene.yaml` (descripción, props con su tipo, límite de caracteres, si es texto de
  pantalla, de qué está hecha). Contrato fijo: props, tokens, duración, palabras de su locución, `at()`.

### Dónde viven y quién manda

1. `courses/<CODE>/video/scenes/<nombre>/` (solo ese curso)
2. `tools/remotion/src/scenes/<nombre>/` (el proyecto, todos sus cursos; aquí crea el agente)
3. la biblioteca de coursekit, en `tools/remotion/kit/` (gestionada: la escribe cada comando `coursekit video` desde el
   paquete; ignorada por git; nunca se edita).

Un nombre del curso tapa al del proyecto, y el del proyecto al de la biblioteca. `coursekit video catalog` lista todo, con
props y de qué está hecho cada uno: así el agente ve cómo se arman las piezas y lo que creó en vídeos anteriores.

### Comandos

`video new` (esqueleto desde el guion), `video check` (esquema, tipos de escena, límites de texto, medios, lo que se ve y no
se dice), `video voice` (voz por escena, palabras, duraciones; solo lo que cambió), `video preview` (un fotograma por escena en
una hoja, sin render completo), `video render` (MP4, subtítulos, palabras, transcripción accesible, recurso `produced`),
`video catalog`. Una sola composición `Montage` en una entrada propia de la biblioteca (`kit/entry.ts`): el agente no toca
`Root.tsx`. Los medios se sirven desde `courses/<CODE>/media` (`--public-dir`).

### Fases

1. Base: tokens de movimiento, átomos, moléculas básicas, escenas `title`, `split`, `stat`, `outro`, `screencast`;
   `Montage`; esquema versionado y resolución de tiempos; `video new|check|voice|preview|render|catalog`; escenas del
   proyecto y del curso con su precedencia; skill (orden de decisión: biblioteca → componer con átomos → átomo nuevo).
2. Más escenas (comparación, lista, cita, diagrama que se construye) y capas ancladas a palabras (rótulos, resaltados).
3. Sustituir átomos por nombre (alias de webpack) y sección `video` de estilo del proyecto (carácter del movimiento, fondo,
   logo, rótulos).
4. Opcional: exportar a DaVinci (FCPXML 1.10 y OTIO).

### Estado

- [x] Fase 1 (sin commit todavía): `coursekit/videokit/` (tema y movimiento por contexto, `useAt`, átomos, moléculas, escenas
  `title`, `split`, `stat`, `outro`, `screencast` con su `scene.yaml`, `Montage` en `kit/entry.ts`), `video.py` y
  `coursekit video new|check|voice|preview|render|catalog`, precedencia curso → proyecto → biblioteca (las escenas del curso
  se renderizan desde una copia en `src/.course/`, a la misma profundidad que las del proyecto), receta `montage`,
  `.gitignore` de los proyectos, skill con el orden de decisión. Probado de punta a punta con Piper, stable-ts y Remotion
  reales: voz, vista previa, render, `media check` y transcripción. El diseño visual de las escenas es básico: se pule en
  la fase 2.
- [x] Fase 2 (sin commit todavía): átomos `Card`, `Badge`, `Arrow`; moléculas `CompareColumn`, `StepNode`; escenas `compare`,
  `list`, `quote`, `diagram`; capas `lower-third`, `callout`, `highlight` con `at`/`until`/`hold` resueltos en Python con las
  palabras (`video check` avisa de anclas que no se dicen); fondo `shape`; tamaños revisados mirando la vista previa real;
  `video render` normaliza la sonoridad. Probado de punta a punta con 8 escenas y una capa.
- [ ] Fase 3
