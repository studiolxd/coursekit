# Contenido del curso

Cómo se organiza la carpeta de un curso, el formato de `content.md` y `assessment.md`, las directivas interactivas y las reglas que aplica `coursekit verify`.

## Carpeta del curso

`coursekit new` crea la carpeta; el resto de ficheros aparecen a medida que el curso avanza por el flujo de trabajo (consulta [02-workflow.md](02-workflow.md)).

```text
courses/PWD/
├── course.yaml                  ficha del curso: unidades, estado, aprobaciones, entregas, historial
├── brief/                       material de referencia (links.md, notes.md, sources/; text/ e index.md tras `coursekit brief`)
├── design/
│   ├── matrix.json              diseño instruccional, tal como se exporta de la plataforma
│   ├── PWD-instructional-design.xlsx   el fichero que revisan las personas
│   ├── proposal-notes.md        notas del agente de diseño
│   └── validation.json          hallazgos de la validación (opcional)
├── content/
│   └── unit-01/
│       ├── content.md           las lecciones de la unidad
│       └── assessment.md        actividades sumativas y banco de preguntas
├── reviews/
│   └── unit-01-ai-review.md     informe de la revisión con IA
├── media/
│   ├── manifest.yaml            una entrada por cada recurso multimedia
│   ├── scripts/ · src/ · files/ guiones, fuentes y ficheros producidos (consulta 07-media.md)
├── theme/                       theme propio del curso (opcional): tokens.json, tokens.css, maqueta.css (backend html)
├── assembly/
│   ├── unit-01.plan.json        plan generado, backend creator (consulta 08-assembly-and-delivery.md)
│   ├── unit-01.applied.json     lo que hay cargado en la plataforma, backend creator
│   └── html/unit-01/            paquete construido por el backend html (generado, no se versiona)
└── delivery/
    └── PWD-U01-v1.0-scorm12.zip paquetes SCORM
```

`coursekit new` crea `brief/`, `design/`, `content/`, `media/` (con un `manifest.yaml` vacío), `reviews/` y `course.yaml`. `assembly/` aparece con el primer `coursekit assemble plan` (backend creator) o `coursekit assemble build` (backend html) y `delivery/` con el primer paquete. `theme/` existe solo si el curso tiene un theme propio (`/define-theme PWD`); si no, el curso usa el `theme/` del proyecto (junto a `courses/`), que guarda los tokens de diseño que heredan todos los cursos.

Otras dos carpetas del proyecto importan al backend html, ambas junto a `courses/` y ambas escritas por personas:

| Ruta | Qué es |
|---|---|
| `theme/maqueta.css` | La hoja de estilos que da otro aspecto al paquete del backend html (la «maqueta»). Un curso puede tener la suya en `courses/PWD/theme/maqueta.css`; va por encima de la del proyecto. `coursekit theme import theme/maqueta.css` deriva los tokens de diseño de sus variables CSS |
| `components/` | `*.css` adicionales (estilos que se añaden a todos los paquetes) y `*.js` (comportamiento que se empaqueta en el reproductor) del proyecto. Opcional |

Ambas se explican en [Estilos](08-assembly-and-delivery.md#estilos).

### Quién escribe qué

| Ruta | La crea | La modifica |
|---|---|---|
| `course.yaml` | `coursekit new` | Los comandos de coursekit escriben `units`, `status`, `history`, `approvals` y `deliveries`; las personas y los agentes rellenan `owners`, `links`, `design` y `slxd`. No edites `units` ni `approvals` a mano |
| `design/*` | agente de diseño | agente de diseño. `matrix.json` no se edita a mano: al firmar el diseño se registra su huella |
| `content/unit-NN/*.md` | `coursekit sync` (esqueleto, solo si faltan) | agente redactor; las personas, para cambios editoriales |
| `reviews/unit-NN-ai-review.md` | agente revisor | agente revisor |
| `media/manifest.yaml` | `coursekit media extract` | `coursekit media extract` y `coursekit media set` |
| `media/scripts`, `src`, `files` | agente de multimedia | agente de multimedia |
| `theme/{tokens.json,tokens.css}` (proyecto) y `courses/<CODE>/theme/{tokens.json,tokens.css}` (curso) | `coursekit theme import` (lo ejecuta `/define-theme`) | `coursekit theme import` otra vez, `coursekit theme tokens` para el CSS. Nunca a mano: se derivan del theme de la plataforma y llevan su `origin` (id del theme, nombre, versión, fecha). La importación escribe `course.yaml › slxd.theme_id` en un curso con theme propio |
| `theme/maqueta.css` y `courses/<CODE>/theme/maqueta.css`, `components/*` (backend html) | Las personas | Las personas. Son el único lugar donde se escribe el aspecto del paquete html; el paquete en sí no se edita nunca |
| `assembly/*.json` | `coursekit assemble` (backend creator) | `coursekit assemble` (nunca a mano) |
| `assembly/html/` | `coursekit assemble build` (backend html) | `coursekit assemble build` lo reconstruye desde cero; es generado y git lo ignora |
| `delivery/*.zip` | agente de montaje (descarga, backend creator) o `coursekit assemble build --version` (backend html) | se registran con `coursekit delivery add` |
| `brief/` | `coursekit new` | las personas dejan el material; `coursekit brief` lo convierte |

Las aprobaciones (`approvals` en `course.yaml`) las escribe solo `coursekit approve`, y solo lo ejecuta una persona.

## Idioma del contenido e idioma de la interfaz

| | Ajuste | Qué controla |
|---|---|---|
| Idioma del contenido | `content_language` en `project.yaml` (`language` en `course.yaml` lo sustituye por curso; `coursekit new --language`) | Las palabras del formato de contenido (encabezado de apartado, etiqueta de objetivo, recurso multimedia, nombres de campo), las plantillas del esqueleto, el formato de los números (`5,000` en inglés, `5.000` en español), el idioma en que escriben los agentes y el tratamiento (`tu` / `usted` / `you`) |
| Idioma de la interfaz | `ui_language` en `project.yaml`; `COURSEKIT_LANG` en `.env` lo sustituye para una persona | Los mensajes de coursekit (incluidos los hallazgos de `verify`), los informes de revisión, las notas de diseño y el idioma del Excel de catálogo |

Ambos aceptan `es` o `en`. Si no hay `ui_language`, se usa `content_language`. Un idioma de curso como `es-ES` se lee como `es`.

## Formato de `content.md`

Las palabras del formato salen de `src/coursekit/lang/en.yaml` y `es.yaml`. `verify`, `outline`, `media` y `assemble` las leen, así que los encabezados deben escribirse exactamente como se muestran. Las palabras del contenido son las del idioma del curso: no las mezcles (consulta [Tipos de recurso y claves de las directivas por idioma](#tipos-de-recurso-y-claves-de-las-directivas-por-idioma)).

| Elemento | Contenido en inglés | Contenido en español |
|---|---|---|
| Título de la unidad | `# Unit N — <title>` | `# Unidad N — <título>` |
| Encabezado de apartado | `## Section N — <title> *(min. 1,000 words)*` | `## Apartado N — <título> *(mín. 1.000 palabras)*` |
| Etiqueta de objetivo | `*[Objective U1.2 — Verb]*` | `*[Objetivo U1.2 — Verbo]*` |
| Recurso multimedia | `> **[MEDIA ASSET — <type>]**` (`<type>`: `Image`, `Infographic`…) | `> **[RECURSO MULTIMEDIA — <tipo>]**` (`<tipo>`: `Imagen`, `Infografía`…) |
| Campos del recurso | `Title`, `Description`, `How it is made`, `Specifications` | `Título`, `Descripción`, `Cómo se elabora`, `Especificaciones` |
| Encabezado de actividad de evaluación | `## ASSESSMENT ACTIVITY N.M — <name>` | `## ACTIVIDAD DE EVALUACIÓN N.M — <nombre>` |
| Clave de objetivo en las preguntas | `objective:` | `objetivo:` |
| Otras claves y palabras de las directivas | `question:`, `answer:`, `feedback-correct:`, `true`/`false`, `(starts)` | `pregunta:`, `respuesta:`, `feedback-correcto:`, `verdadero`/`falso`, `(empieza)` |
| Título de introducción (por defecto) | `Introduction and objectives` | `Introducción y objetivos` |
| Título de resumen (por defecto) | `Summary` | `Resumen` |

### Cabecera de la unidad y apartados

`coursekit sync` escribe el esqueleto. Sustituye cada comentario `<!-- kind … -->` por el contenido de ese apartado:

```markdown
# Unidad 1 — Contraseñas que protegen

> **Duración:** 1 horas · **Páginas mínimas:** 10 · **Palabras mínimas:** 5.000
> **Objetivos de la unidad:**
> - **U1.1** — Crear contraseñas robustas
> - **U1.2** — Identificar contraseñas débiles

---

## Apartado 1 — Introducción y objetivos *(mín. 1.000 palabras)*

<!-- kind: intro -->

## Apartado 2 — Qué hace fuerte a una contraseña *(mín. 3.000 palabras)*

<!-- kind: content · objectives: U1.1, U1.2 -->
```

- El número, el orden y el título de cada apartado vienen del diseño aprobado. La parte `*(mín. …)*` es opcional e informativa. El guion puede ser `—` o `-`.
- Cada apartado se convierte en una lección. Usa `###` para los subapartados; la prosa, las listas, las tablas Markdown y los bloques de código se convierten tal cual.
- Cada apartado tiene un `kind`: `intro` (el primero, si `design.intro_section` es `true`), `summary` (el último, si `design.summary_section` es `true`), `content` (desarrolla objetivos) o `activities` (sin objetivos: actividades de aprendizaje).
- Prosa completa, sin listas sueltas, **sin emojis** (consulta los símbolos permitidos más abajo). `verify` solo comprueba la regla de los emojis; la calidad de la prosa es una norma editorial.

### Etiquetas de objetivo

Todo apartado `content` termina con una etiqueta por cada objetivo que cubre, una por línea:

```markdown
*[Objetivo U1.1 — Crear]*
*[Objetivo U1.2 — Identificar]*
```

La etiqueta es metadato editorial: no se publica. `verify` lee los identificadores (`U1.1`) para comprobar que cada objetivo de la unidad se cubre al menos una vez. Solo exige una etiqueta por apartado `content` (las etiquetas en otros tipos de apartado no se leen) y cada objetivo de la unidad etiquetado en algún sitio: no compara las etiquetas con los objetivos que el diseño asigna a ese apartado ni comprueba que el identificador exista.

### Recursos multimedia

Un recurso multimedia reserva el sitio de una imagen, un vídeo u otro recurso hasta que se produce:

```markdown
> **[RECURSO MULTIMEDIA — Imagen]**
> **Título:** Nota adhesiva en un monitor
> **Descripción:** Una contraseña escrita en una nota pegada a la pantalla.
> **Cómo se elabora:** Fotografía de stock con licencia.
> **Especificaciones:** 1280x720 px, texto alternativo obligatorio.
```

Los cuatro campos son obligatorios. El `<tipo>` es uno de ocho tipos de recurso, escrito con la palabra del idioma del curso (en español: `Imagen`, `Vídeo`, `GIF animado`, `Infografía`, `Esquema/Diagrama`, `Simulación interactiva`, `Demo interactiva en terminal`, `Audio`; las palabras en inglés están en la tabla siguiente). Cada tipo tiene además un id (`image`, `video`, `animated_gif`, `infographic`, `diagram`, `simulation`, `terminal_demo`, `audio`) que se usa en la configuración y en el manifiesto. La producción se explica en [07-media.md](07-media.md).

### Qué cuenta como palabra

Solo cuenta el texto que lee el alumno: se descartan el recuadro del recurso (sus líneas `>`, hasta la primera línea que no empiece por `>`), las etiquetas de objetivo (cada una en su propia línea), los comentarios HTML y las líneas `:::` de las directivas. El texto *dentro* de una directiva sí cuenta, y también una cita Markdown simple (`> texto`). Las palabras son los fragmentos separados por espacios en blanco de lo que queda, así que un marcador de lista, un `####` o las barras de una tabla cuentan como uno cada uno. Se cuentan por apartado; la cabecera de la unidad no cuenta.

`coursekit outline` muestra otra cifra, aproximada: cuenta todas las palabras del apartado sin comentarios, incluidos los recuadros de recurso, las etiquetas y los nombres de directiva, así que sale más alta que la de `verify`. El número que vale es el que imprime `verify`.

### Tipos de recurso y claves de las directivas por idioma

Algunas palabras del formato se escriben en el idioma del curso, pero la configuración y el manifiesto no deben depender de ese idioma. Por eso un tipo de recurso tiene un **id** (siempre en inglés, igual en todos los cursos) y una **palabra** por idioma de contenido (`media_types` en `src/coursekit/lang/<código>.yaml`):

| Id | Contenido en inglés | Contenido en español |
|---|---|---|
| `image` | `Image` | `Imagen` |
| `video` | `Video` | `Vídeo` |
| `animated_gif` | `Animated GIF` | `GIF animado` |
| `infographic` | `Infographic` | `Infografía` |
| `diagram` | `Diagram` | `Esquema/Diagrama` |
| `simulation` | `Interactive simulation` | `Simulación interactiva` |
| `terminal_demo` | `Interactive terminal demo` | `Demo interactiva en terminal` |
| `audio` | `Audio` | `Audio` |

- En `content.md` escribes en el recurso la **palabra** del idioma del curso (`> **[RECURSO MULTIMEDIA — Infografía]**`). No importan las mayúsculas ni los espacios alrededor, pero sí las tildes: en un curso en español `Video` e `Infografia` son errores, solo se aceptan `Vídeo` e `Infografía`. El guion del encabezado del recurso puede ser `—` o `-`.
- En cualquier otro sitio se usa el **id**: `content.placeholder_types` en `config/rules.yaml`, las claves de `types` y la lista `uses_theme` en `config/media.yaml` (consulta [04-configuration.md](04-configuration.md)) y `type` en `media/manifest.yaml › assets`. `coursekit media extract` convierte la palabra en el id, así que el manifiesto es el mismo sea cual sea el idioma del curso.
- Una palabra del otro idioma es un error: en un curso en español, `Infographic` falla con `tipo de recurso multimedia desconocido o no permitido 'Infographic' (usa: Imagen, Vídeo, GIF animado, …)`.

Las claves de las líneas `clave: valor` dentro de las directivas, y las pocas palabras que algunas admiten, también siguen el idioma del contenido (`directive_keys` y `directive_words` en el mismo fichero; la clave de objetivo es `question_objective_key`):

| Para qué | Contenido en inglés | Contenido en español |
|---|---|---|
| Texto de la pregunta | `question:` | `pregunta:` |
| Respuesta de `true-false` | `answer:` | `respuesta:` |
| Respuestas aceptadas de `short-answer` | `answers:` | `respuestas:` |
| Retroalimentación general, correcta e incorrecta | `feedback:` · `feedback-correct:` · `feedback-incorrect:` | `feedback:` · `feedback-correcto:` · `feedback-incorrecto:` |
| Imagen de `labelled-graphic` | `image:` | `imagen:` |
| Posición de un punto | `position:` | `posición:` |
| Título de `note` | `title:` | `título:` |
| Objetivo de una pregunta | `objective:` | `objetivo:` |
| Valor de `true-false` | `true` · `false` | `verdadero` · `falso` |
| Modo de un elemento de `pasapalabra` | `(starts)` · `(contains)` | `(empieza)` · `(contiene)` |

Los **nombres** de las directivas (`:::single-choice`, `:::tabs`…) son los mismos en los dos idiomas. Una clave que pertenece al otro idioma no se ignora: `coursekit assemble plan` y `coursekit verify` fallan con `la clave 'question:' es del idioma «en»; en este curso se usan: …` y enumeran las válidas. La referencia de formato que leen los agentes (`.coursekit/docs/content-format.md`) muestra las palabras del idioma del curso. Un idioma nuevo necesita `media_types`, `directive_keys` y `directive_words` en su `lang/<código>.yaml` (consulta `CONTRIBUTING.md`).

### Dudas y marcas VERIFICAR

Cuando quien redacta no puede confirmar un dato (una versión, un comando, una opción, el nombre de un producto) con el material de referencia de `brief/`, no se lo inventa: deja `<!-- VERIFICAR: qué comprobar -->` junto al texto. Es un comentario HTML, así que no cuenta como palabras y no se publica. `coursekit verify` no busca estas marcas y una unidad pasa con ellas dentro: son una convención entre quien redacta y quien revisa. Quien revisa localiza cada una, la resuelve con el material (una afirmación que contradice el material es un hallazgo bloqueante) y la elimina. En el [modo handoff](02-workflow.md#modo-handoff), donde no se puede preguntar a nadie, las dudas quedan escritas en las unidades y en los informes. Las mejoras que cambian el enfoque no las aplica quien revisa: van bajo «Propuestas pendientes de decisión humana» en `reviews/unit-NN-ai-review.md`, para que la persona las resuelva antes de firmar.

## Formato de `assessment.md`

Las actividades sumativas de la unidad, en el orden en que se hacen. Un encabezado `##` por cada actividad del diseño, con estos subapartados `###`:

```markdown
# Unidad 1 — Actividades de evaluación

## ACTIVIDAD DE EVALUACIÓN 1.1 — Test de la unidad
### Objetivos que evalúa
### Instrucciones para el alumno
### Desarrollo e implementación
### Corrección automática y puntuación
### Intentos y retroalimentación
### Banco de preguntas
```

| Español | Inglés |
|---|---|
| `Objetivos que evalúa` | `Objectives assessed` |
| `Instrucciones para el alumno` | `Instructions for the learner` |
| `Desarrollo e implementación` | `Development and implementation` |
| `Corrección automática y puntuación` | `Automatic marking and scoring` |
| `Intentos y retroalimentación` | `Attempts and feedback` |
| `Banco de preguntas` | `Question bank` |

El montaje carga en la lección de evaluación de la plataforma solo lo que hay bajo **Instrucciones para el alumno** y **Banco de preguntas** (texto y directivas); los demás subapartados documentan la actividad para el equipo. Pon las directivas de pregunta (consulta más abajo) en el banco. Toda pregunta lleva la clave de objetivo y retroalimentación.

- `verify` no comprueba los encabezados de `assessment.md`, pero el montaje los empareja exactamente, con las palabras del idioma del curso: un `### Banco de preguntas` mal escrito no carga ninguna pregunta. Se construye una lección de evaluación por cada encabezado `## ACTIVIDAD DE EVALUACIÓN`.
- `verify` cuenta todas las directivas de pregunta del fichero, estén donde estén. Una colocada en otro subapartado cuenta para `verify`, pero nunca llega al alumno.
- La nota de aprobado, los intentos y el peso de un test no se leen del Markdown: salen de su actividad de evaluación en el diseño (`notaAprobado`, `intentosMax`, `peso`) y, para lo que el diseño deja vacío, de `course.yaml › design.grading` (`passing_score` y `attempts`; consulta [Calificación de un test](08-assembly-and-delivery.md#calificación-de-un-test)). Los subapartados `Corrección automática y puntuación` e `Intentos y retroalimentación` solo documentan la actividad.

## Directivas

Una directiva es un bloque que se convierte en un elemento interactivo del curso:

```markdown
:::tabs
#### Longitud
La longitud importa más que la complejidad.
#### Unicidad
No reutilices nunca una contraseña.
:::
```

`:::nombre` abre el bloque y una línea con solo `:::` lo cierra. Las directivas no se pueden anidar y las líneas dentro de bloques de código se ignoran. El registro está en `src/coursekit/defaults/directives.yaml`; un proyecto puede cambiarlo en `config/directives.yaml` (su copia completa está en `config/directives.example.yaml`).

### Roles

| Rol | Significado |
|---|---|
| `interactive` | Cuenta para el mínimo de interactivas de un apartado `content` |
| `question` | Pregunta de práctica o de evaluación; necesita la clave de objetivo |
| `static` | Texto destacado; **no** cuenta como interactivo |

### Tabla de directivas

| Directiva | Brick de creator | Rol | Uso | Backend html |
|---|---|---|---|---|
| `accordion` | `ACCORDION` | interactive | Contenido largo dividido en secciones plegables que se abren a demanda | ✔ |
| `tabs` | `TABS` | interactive | Vistas alternativas de contenido relacionado en pestañas | ✔ |
| `carousel` | `CAROUSEL` | interactive | Diapositivas paso a paso, con portada y resumen opcionales | ✔ |
| `carousel-quotes` | `CAROUSEL_QUOTES` | interactive | Conjunto rotatorio de citas o testimonios | ✔ |
| `flashcards` | `FLASHCARD_CAROUSEL` | interactive | Memorizar y recordar, una tarjeta cada vez (término ↔ definición) | ✔ |
| `flashcard-gallery` | `FLASHCARD_GALLERY` | interactive | Rejilla de tarjetas para autoevaluar el recuerdo | ✔ |
| `labelled-graphic` | `LABELLED_GRAPHIC` | interactive | Imagen con puntos calientes que explican sus partes (diagramas) | ✔ |
| `timeline` | `TIMELINE` | interactive | Hechos o pasos cronológicos o secuenciales | ✔ |
| `dialog` | `DIALOG` | interactive | Conversación guionizada entre personajes (roleplay, ejemplos resueltos) | ✔ |
| `word-search` | `WORD_SEARCH` | interactive | Sopa de letras; refuerzo de vocabulario | aún no disponible |
| `wordle` | `WORDLE` | interactive | Adivinar la palabra; vocabulario | aún no disponible |
| `hangman` | `HANGMAN` | interactive | Ahorcado; vocabulario | aún no disponible |
| `pasapalabra` | `PASAPALABRA` | interactive | Rosco con una pista por letra; repaso amplio de un tema | aún no disponible |
| `memory` | `MEMORY` | interactive | Parejas de memoria; recuerdo y asociación | aún no disponible |
| `trivial` | `TRIVIAL` | interactive | Trivial por categorías; repaso gamificado | aún no disponible |
| `single-choice` | `SINGLE_CHOICE` | question | Comprobar la comprensión con una única opción correcta | ✔ |
| `multi-select` | `MULTI_SELECT` | question | Evaluar cuando varias opciones pueden ser correctas | ✔ |
| `true-false` | `TRUE_FALSE` | question | Comprobación rápida de una afirmación | ✔ |
| `sorting` | `SORTING` | question | Ordenar elementos en la secuencia correcta | ✔ |
| `match` | `MATCH` | question | Emparejar elementos de la izquierda con los de la derecha | ✔ |
| `sorting-groups` | `SORTING_GROUPS` | question | Clasificar elementos en sus categorías | ✔ |
| `fill-in-the-blank` | `FILL_IN_THE_BLANK` | question | Recordar palabras concretas dentro de una frase (huecos) | ✔ |
| `order-words` | `ORDER_WORDS` | question | Reconstruir frases a partir de palabras desordenadas | ✔ |
| `short-answer` | `SHORT_ANSWER` | question | Respuesta libre comparada con una lista de respuestas aceptadas | ✔ |
| `note` | `NOTE` | static | Nota, consejo o advertencia separada del texto principal | ✔ |
| `highlight` | `HIGHLIGHT` | static | Destacar una idea clave | ✔ |
| `quote` | `QUOTE` | static | Cita de una persona experta o fuente, con atribución | ✔ |

Los juegos (`word-search` a `trivial`) cuentan como interactivos; úsalos con moderación, para repasar o premiar. Son las únicas directivas que el backend html aún no renderiza (última columna): `coursekit assemble build` rechaza una unidad que use alguna, y `coursekit verify` la informa con el backend html (`MEMORY: este componente aún no está disponible en el backend html…`). Todo lo demás se construye como se describe en [Componentes](08-assembly-and-delivery.md#componentes). Una cita Markdown simple (`> texto`) que no sea un recurso multimedia se convierte en un brick `HIGHLIGHT`.

El resto del Markdown se convierte en bricks sin directiva: los párrafos en `TEXT`, los encabezados `###`–`######` en `HEADING`, las listas en `LIST`, las tablas en `TABLE` y los bloques de código en `CODE`. Los recursos multimedia se explican en [07-media.md](07-media.md).

### Estructura interna

Lo que no siga estas formas falla al convertir la unidad (`verify` lo indica).

| Directiva | Estructura interna |
|---|---|
| `accordion`, `tabs`, `carousel` | Un `#### Título` por panel, pestaña o diapositiva, seguido de texto Markdown |
| `timeline` | `#### <fecha> — <título>` por hito (sin ` — `, toda la línea es el título) + texto |
| `flashcards`, `flashcard-gallery` | `#### Anverso` + texto del reverso |
| `labelled-graphic` | `imagen: <título exacto del recurso de imagen>`, después `#### Punto` + texto; opcional `posición: x,y` (0–100) bajo cada punto |
| `dialog` | `**Personaje:** línea`, una por línea |
| `carousel-quotes` | Una cita por párrafo, con `— autor` en su última línea |
| `note` | Línea opcional `título: …` (título por defecto: `Nota`) + texto |
| `highlight` | Texto |
| `quote` | Cita + `— autor` en la última línea |
| `word-search`, `wordle`, `hangman` | `- PALABRA` por línea |
| `memory` | `- contenido de la tarjeta` por línea |
| `pasapalabra` | `- A (empieza): definición :: RESPUESTA` (o `(contiene)`) por línea; la respuesta admite alternativas separadas por `/` (`RESPUESTA/OTRA`) |
| `trivial` | `#### Categoría`, después bloques con `pregunta: …` y opciones `- [x]` / `- [ ]`, separados por una línea en blanco |

La `imagen:` de un `labelled-graphic` se empareja con el título de un recurso de `media/manifest.yaml`, así que el recurso debe existir en el manifiesto (ejecuta antes `coursekit media extract`) y estar producido. Si no, `assemble` solo avisa (`labelled-graphic: la imagen 'X' aún no está producida`) y el gráfico se queda sin imagen. Solo las líneas anteriores al primer `####` son claves del propio gráfico; una `posición:` va bajo el punto al que pertenece.

Dentro de una directiva, una línea que empieza por una palabra en minúsculas y dos puntos (`consejo: …`) se lee como una clave, no como texto. En `note`, `highlight`, `quote` y `carousel-quotes` se elimina en silencio del texto publicado; en las demás directivas, una clave del otro idioma provoca el error descrito más arriba. Escribe `Consejo:` con mayúscula o reformula la frase. Las claves van en una línea propia, no detrás de un marcador de lista.

### Directivas de pregunta

```markdown
:::single-choice
objetivo: U1.1
pregunta: ¿Cuál es la contraseña más robusta?
- [ ] Verano2024!
- [x] caballo correcto bateria grapa rio
- [ ] P@ssw0rd
feedback-correcto: Ganan la longitud y la aleatoriedad.
feedback-incorrecto: Repasa el apartado sobre la longitud.
:::
```

| Directiva | Cuerpo |
|---|---|
| `single-choice` | Opciones `- [x]` / `- [ ]`; exactamente una `- [x]` |
| `multi-select` | Opciones `- [x]` / `- [ ]` |
| `true-false` | `respuesta: verdadero` o `respuesta: falso` |
| `sorting` | Una lista en el orden correcto |
| `match` | Líneas `- término :: definición` |
| `sorting-groups` | `#### Categoría` + lista de sus elementos |
| `fill-in-the-blank` | Huecos escritos en `pregunta:` con la palabra correcta entre llaves, como `{larga}` (varias respuestas aceptadas: `{a/b}`); no hay línea `respuesta:` |
| `order-words` | Una `- frase completa` por frase |
| `short-answer` | `respuestas: a \| b \| c` |

Cada clave va en una sola línea. Los nombres de clave dentro de las directivas (`pregunta:`, `respuesta:`, `respuestas:`, `feedback-correcto:`, `feedback-incorrecto:`, `feedback:`, `título:`, `imagen:`, `posición:`) y la clave de objetivo (`objetivo:`) son los del idioma del contenido que se muestra aquí; un curso en inglés escribe `question:`, `answer:`, `objective:`… (consulta [Tipos de recurso y claves de las directivas por idioma](#tipos-de-recurso-y-claves-de-las-directivas-por-idioma)). Mezclar idiomas es un error.

`pregunta:` es obligatoria, pero `verify` solo avisa cuando falta `objetivo:`. Una pregunta sin `pregunta:`, un `multi-select` sin ningún `- [x]`, un `match` sin ningún par `::` o un `short-answer` sin `respuestas:` pasa `verify` y se publica vacía o rota, así que revísalas a mano. `objetivo:` lleva el identificador de un objetivo de la unidad (`U1.1`); su valor no se valida. Toda pregunta debería llevar además retroalimentación (`feedback-correcto:`, `feedback-incorrecto:` o `feedback:`); es una norma editorial que `verify` no comprueba.

### Componentes que no son directivas

Si el nombre de una directiva no está en el registro, `verify` falla y sugiere el equivalente:

| Componente habitual | Usa en su lugar |
|---|---|
| stepper | `carousel` (o `timeline` si es una secuencia temporal) |
| hotspots | `labelled-graphic` |
| reveal | `accordion` o `flashcards` |
| toggle-compare | `tabs` |
| checklist | `multi-select` (como autoevaluación) |
| tooltips | `note`, o un glosario en un `accordion` |
| modal | `accordion` |
| branching-scenario | `dialog` (ramas complejas: recurso `Simulación interactiva`) |
| simulated-terminal | recurso `Demo interactiva en terminal` |

## `coursekit sync` y `coursekit outline`

### `coursekit sync CODE [--check]`

Lee `design/matrix.json` y reescribe las `units` de `course.yaml`: título, horas, objetivos (renombrados `U1.1`, `U1.2`… por orden de aparición), apartados (`kind`, `title`, `hours`, `min_words`, objetivos, subapartados) y actividades. Después, por cada unidad que no tenga `content.md`, escribe el esqueleto de `content.md` y de `assessment.md` en el idioma del contenido.

- El contenido existente nunca se sobrescribe. `content.md` se regenera solo mientras siga siendo el esqueleto intacto de un diseño anterior, y `assessment.md` se escribe solo cuando falta o sigue siendo la plantilla en blanco. Si los encabezados de `content.md` difieren del diseño, `sync` avisa y los actualizas a mano.
- Los campos de progreso (`content_id`, `status`, `written_with`, `reviewed_with`, `reviewed_parts`, `review`, `links`) se conservan, emparejados por el identificador de la unidad en la plataforma.
- `--check` solo informa de lo que se sincronizaría y no escribe nada.
- Avisa cuando un apartado no tiene horas, cuando las horas de la unidad no coinciden con las de sus apartados, cuando las unidades no suman las horas del curso, o cuando el primer o el último apartado no es una introducción o un resumen estando activados `intro_section` o `summary_section` (el título debe cumplir `introducci[oó]n` y `resumen|s[ií]ntesis|conclusi[oó]n`; en inglés `introduction` y `summary|wrap-up|conclusion`).
- Palabras mínimas de un apartado: `ceil(horas × 10)` páginas × 500 palabras (1 hora = 5.000 palabras; 0,2 h = 1.000; 0,6 h = 3.000).

`coursekit approve design` ejecuta `sync` por sí mismo cuando firmas. Si editas `matrix.json` después de la firma, `verify` se niega a ejecutarse hasta que el diseño se apruebe de nuevo.

### `coursekit outline CODE [--section U.S]`

Un mapa compacto para agentes y personas: cada unidad con su estado y sus objetivos, y cada apartado con sus objetivos, sus palabras mínimas y cuánto está escrito. `--section 1.2` imprime solo el texto del apartado 2 de la unidad 1 (sin comentarios), para comprobar qué dice una unidad anterior sin leerla entera. Un valor erróneo (`x`) termina con código 2; un apartado sin escribir imprime `apartado 1.2: sin escribir`.

```text
U1 Contraseñas que protegen · 1 h · pending
  U1.1 (aplicar): Crear contraseñas robustas
  1.2 Qué hace fuerte a una contraseña [U1.1, U1.2] · mín. 3.000 · 3.200 palabras escritas
```

## `coursekit verify`

```bash
coursekit verify PWD              # todas las unidades
coursekit verify PWD --unit 1     # una unidad
coursekit verify PWD --no-update  # no mueve el estado de la unidad ni del curso
```

El código de salida es 1 si alguna unidad tiene errores; los avisos nunca hacen fallar. Antes, el diseño debe estar aprobado y sin cambios; si no, el comando se detiene con `PWD: el diseño instruccional aún no está aprobado (coursekit approve design PWD)` o `design/matrix.json cambió después de la aprobación: hay que aprobar el diseño de nuevo`.

### Reglas y cifras reales

Las cifras son los valores por defecto del paquete (`src/coursekit/defaults/rules.yaml`). Un proyecto las cambia en `config/rules.yaml` o en `project.yaml › rules`, y un curso en `course.yaml › rules` (consulta [04-configuration.md](04-configuration.md)).

| Comprobación | Regla | Por defecto | Gravedad |
|---|---|---|---|
| Apartados | Los números de apartado de `content.md` coinciden con los del diseño | — | error |
| Título del apartado | Mismo título que el diseño | — | aviso |
| Palabras mínimas | `ceil(horas × pages_per_hour)` páginas de `words_per_page` palabras por apartado | 10 páginas/hora, 500 palabras/página (5.000 palabras por hora) | error |
| Margen de palabras | Margen recomendado sobre el mínimo (`word_margin`) | 5 % | aviso |
| Etiqueta de objetivo | Cada apartado `content` tiene al menos una etiqueta; cada objetivo de la unidad está etiquetado en algún sitio | — | error |
| Mínimo de interactivas | Directivas interactivas distintas por apartado `content`: `max(min_interactive_per_content_section, ceil(horas × interactive_per_hour))` | 4 por hora, al menos 1 (0,6 h exige 3) | error |
| Recursos multimedia | Al menos `ceil(horas de la unidad × placeholders_per_hour)` en la unidad | 2,5 por hora (1 h exige 3) | error |
| Tipos de recurso | Al menos `min(min_placeholder_types, recursos exigidos)` tipos distintos | 4 (1 h exige 3) | error |
| Forma del recurso | Tipo conocido (una palabra del idioma del curso) y los cuatro campos presentes | 8 tipos | error |
| Directivas | Nombre conocido, cerrada y sin anidar | — | error |
| Objetivo de la pregunta | Toda directiva de pregunta lleva la clave de objetivo (`objetivo:` / `objective:`) | — | aviso |
| Banco de preguntas | `questions_per_objective` × número de objetivos distintos evaluados por una actividad cuyo instrumento es `cuestionario` (el valor del campo de instrumento del diseño, sea cual sea el idioma del curso) | 5 por objetivo | aviso |
| Símbolos | Ningún emoji ni pictograma fuera de `allowed_symbols` | `★ ✔ ✘ · — ‹ ›` | error |
| Montaje | El Markdown se convierte en bricks (mismo análisis que `assemble plan`). Con el backend html informa además de las directivas que aún no están disponibles | — | error |
| Ficheros | Existen `content.md` y `assessment.md` | — | error |

Notas: el mínimo de interactivas cuenta nombres de directiva **distintos**, así que repetir `tabs` tres veces cuenta una; `note`, `highlight`, `quote` y las directivas de pregunta no cuentan. Solo los apartados `content` necesitan etiquetas y directivas interactivas; los apartados `intro`, `summary` y `activities` solo necesitan sus palabras. Las preguntas se cuentan en `content.md` (formativas) y en `assessment.md` (banco); solo el banco se compara con el número esperado, y solo como total: `verify` no comprueba cómo se reparten las preguntas entre los objetivos ni el valor de su `objetivo:`.

La comprobación de símbolos lee `content.md` y `assessment.md` enteros, con comentarios y bloques de código incluidos. Rechaza los emojis y los bloques de símbolos U+2300–23FF, U+2600–27BF y U+2B00–2BFF, así que una marca de verificación como U+2713 o un signo de advertencia como U+26A0 falla: usa `✔` o `✘`. Las flechas no se ven afectadas.

### Cómo leer los mensajes

```text
[FALLO] PWD · U1 — Contraseñas que protegen
  palabras 0/5.000 · recursos multimedia 0 (0 tipos) · preguntas formativas 0 · preguntas del banco 0
  ERROR   content.md › Apartado 1: 0 palabras < mínimo 1.000
  ERROR   content.md › Apartado 2: 0 palabras < mínimo 3.000
  ERROR   content.md › Apartado 2: falta la etiqueta de objetivo *[Objetivo UN.M — …]*
  ERROR   content.md › Apartado 2: 0 directivas interactivas distintas < 3
  ERROR   content.md › Apartado 3: 0 palabras < mínimo 1.000
  ERROR   content.md: el objetivo U1.1 no está etiquetado en ningún apartado de contenido
  ERROR   content.md: el objetivo U1.2 no está etiquetado en ningún apartado de contenido
  ERROR   content.md: 0 recursos multimedia < 3
  ERROR   content.md: 0 tipos de recurso multimedia < 3
  AVISO   assessment.md: 0 preguntas en el banco, se esperaban 5 (5 por objetivo evaluado con cuestionario)
```

Esta es la salida para el esqueleto intacto del ejemplo completo de más abajo.

La cabecera dice `[OK]` o `[FALLO]`. La segunda línea da las palabras (escritas/mínimo), los recursos multimedia (y sus tipos distintos), las preguntas formativas y las del banco. Después va una línea por hallazgo: `ERROR` hace fallar la unidad, `AVISO` no. Un hallazgo sobre un apartado lleva la etiqueta `content.md › Apartado N`; los de sintaxis llevan `fichero:línea`.

| Mensaje | Qué hacer |
|---|---|
| `Apartado N: X palabras < mínimo Y` | Escribe más; los recursos multimedia, las etiquetas, los comentarios y las líneas `:::` no cuentan |
| `Apartado N: X palabras, por debajo del margen recomendado del 5 %` | Apunta algo por encima del mínimo (aviso) |
| `Apartado N: falta la etiqueta de objetivo *[Objetivo UN.M — …]*` | Añade la línea de etiqueta al final del apartado |
| `el objetivo U1.1 no está etiquetado en ningún apartado de contenido` | Cubre ese objetivo en un apartado `content` y etiquétalo |
| `Apartado N: X directivas interactivas distintas < Y` | Añade directivas de otros tipos |
| `X recursos multimedia < Y` · `X tipos de recurso multimedia < Y` | Añade recursos o varía su tipo |
| `tipo de recurso multimedia desconocido o no permitido 'Image' (usa: Imagen, Vídeo, …)` | Usa una de las palabras que indica el mensaje, que son las del idioma del curso (en un curso en español `Imagen`, no `Image`) |
| `al recurso multimedia le faltan campos: …` | Añade las líneas `> **Campo:** …` que faltan |
| `directiva desconocida ':::nombre'` (`usa: …`) | Usa una directiva del registro; la pista nombra el equivalente |
| `directiva anidada dentro de ':::tabs'` · `la directiva ':::tabs' no está cerrada` | Una directiva cada vez; ciérrala con `:::` |
| `pregunta sin 'objetivo:'` | Añade `objetivo: U1.1` como primera línea de la pregunta |
| `ensamblado: U1-S2: la clave 'question:' es del idioma «en»; en este curso se usan: …` | Una clave del otro idioma: escribe la del idioma del curso (`pregunta:`) |
| `emoji o pictograma no permitido (U+…)` | Quítalo, o usa uno de los símbolos permitidos |
| `los apartados [1, 2] no coinciden con el diseño [1, 2, 3]` | Recupera el encabezado `## Apartado N` que falta o sobra |
| `el título 'X' difiere del diseño 'Y'` | Aviso: alinea el encabezado con el diseño |
| `ensamblado: …` | El Markdown no se convierte (por ejemplo `:::single-choice necesita exactamente una opción correcta`); corrígelo en el `.md` |
| `falta …/content.md` · `falta assessment.md` | Ejecuta `coursekit sync` o crea el fichero |

### Qué hace `verify` con el estado de la unidad

Si no pasas `--no-update`, `verify` también mueve la unidad. Una unidad sin errores pasa a `verified`; la excepción es un proyecto con `review.ai: skip` (consulta [04-configuration.md](04-configuration.md)), donde pasa directamente a `reviewed` (`review.kind: skipped`) y tu firma es la revisión. Una unidad con errores vuelve a `writing` si estaba en `verified` o más allá, o si estaba en `pending` y ya tiene palabras; una unidad `pending` sin palabras sigue en `pending`. Imprime una línea como `estado: unidad pending -> verified · curso design_approved -> ai_review`. Los estados se explican en [02-workflow.md](02-workflow.md).

### Qué cambió desde la revisión con IA

Cuando la revisión con IA es obligatoria, `coursekit reviewed` guarda una huella de cada parte de la unidad en `course.yaml › units[N].reviewed_parts`: cada apartado de `content.md` (`section 2`) y cada actividad de `assessment.md` (`activity 1.1`), desde su encabezado `##` hasta el siguiente, comentarios incluidos. El texto anterior al primer encabezado `##` (la cabecera de la unidad, el título de `assessment.md`) no pertenece a ninguna parte. Una parte cuenta como cambiada cuando su texto difiere de cualquier modo, aunque sea un espacio o un comentario `VERIFICAR`, o cuando se añade o se elimina.

| Tras una edición, `verify` encuentra | La unidad pasa a |
|---|---|
| Errores | `writing` |
| Unidad `reviewed`, sin errores, una parte cambiada | `verified`, con `cambió tras la revisión con IA: section 2 (coursekit review: revisión parcial)`; el siguiente `coursekit review` cubre solo esas partes |
| Unidad `approved`, sin errores, una parte cambiada | `verified`; la aprobación anterior queda en el historial y firmas de nuevo |
| Unidad `approved`, sin errores, un fichero cambiado pero ninguna parte (por ejemplo la cabecera de la unidad) | `reviewed` |
| Cualquier unidad que pasa con `review.ai: skip` | `reviewed` |

## Ejemplo completo

Un curso de una hora sobre contraseñas seguras (código `PWD`, cliente ACME) cuyo diseño se ha exportado a `courses/PWD/design/matrix.json` y está firmado.

```bash
coursekit new "Contraseñas seguras" 1 --code PWD
# el agente de diseño guarda design/matrix.json; una persona lo firma:
coursekit sync PWD
```

```text
1 unidad, 3 apartados, 5.000 palabras mínimas · sincronizado en course.yaml
  escrito: content/unit-01/content.md
```

El agente redactor rellena `content/unit-01/content.md`. El apartado 2 (0,6 h) necesita al menos 3.000 palabras, 3 directivas interactivas distintas y las dos etiquetas de objetivo; la unidad necesita 3 recursos multimedia de 3 tipos distintos y un banco de 5 preguntas por cada objetivo evaluado por el test de la unidad (5 aquí, porque el test del diseño evalúa un objetivo; 10 si evaluara los dos). El fragmento siguiente muestra solo una parte de lo que cuenta `verify`:

```markdown
## Apartado 2 — Qué hace fuerte a una contraseña *(mín. 3.000 palabras)*

La longitud importa más que la complejidad. Una frase de paso larga es más fácil de recordar y mucho más difícil de adivinar…

:::tabs
#### Longitud
Cada carácter adicional multiplica el trabajo de un ataque por adivinación.
#### Unicidad
No reutilices nunca una contraseña.
:::

> **[RECURSO MULTIMEDIA — Infografía]**
> **Título:** Anatomía de una contraseña robusta
> **Descripción:** Diagrama de longitud, variedad y unicidad.
> **Cómo se elabora:** SVG con los tokens del tema.
> **Especificaciones:** 1280 px de ancho, texto alternativo.

*[Objetivo U1.1 — Crear]*
*[Objetivo U1.2 — Identificar]*
```

```bash
coursekit verify PWD --unit 1
```

```text
[OK] PWD · U1 — Contraseñas que protegen
  palabras 5.947/5.000 · recursos multimedia 3 (3 tipos) · preguntas formativas 1 · preguntas del banco 5
```

La unidad queda en `verified`. Después vienen la revisión con IA y la firma (consulta [02-workflow.md](02-workflow.md)) y, luego, la multimedia ([07-media.md](07-media.md)).

Siguiente: [07-media.md](07-media.md)
