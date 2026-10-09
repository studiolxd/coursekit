# Montaje y entrega

Cómo se monta un curso aprobado (se carga en la plataforma de montaje o se construye como paquete web), se exporta como paquetes SCORM, se registra, se publica en la carpeta compartida y se sigue en el catálogo.

```text
backend creator:  unidades aprobadas ─► multimedia subida ─► montaje (plan · diff · aplicar · registrar) ─► vista previa y enlaces de revisión
backend html:     unidades aprobadas ─► multimedia producida ─► assemble build (página · reproductor · manifiesto) ─► carpeta de vista previa y zip
                                                                                                  │
                                                         revisión del cliente (opcional) ◄────────┘
                                                                  │
                      catálogo ◄─ publish (carpeta espejo) ◄─ delivery add (registrar paquetes) ◄─ paquete SCORM (exportación o zip)
```

## Backends de montaje

El backend se elige al crear el proyecto (`coursekit init --backend creator|html`) y se guarda en `project.yaml › assembly.backend` (`creator` por defecto). Un curso puede usar el otro: `course.yaml › assembly.backend` prevalece sobre el del proyecto. `coursekit status PWD` imprime el que está en vigor (`Montaje: backend html`).

| Backend | Qué hace | Dónde acaba la unidad |
|---|---|---|
| `creator` | Convierte `content.md` y `assessment.md` en bricks de creator (`coursekit assemble plan`, `diff`, `applied`, `link`), los carga de forma incremental mediante el servidor MCP de slxd y exporta el paquete SCORM desde la plataforma | Un contenido en creator, con enlaces de vista previa y de revisión |
| `html` | Construye cada unidad como una página web con su propio reproductor (`coursekit assemble build`) y la empaqueta por sí mismo como SCORM 1.2 o 2004. Mismas directivas y mismo formato que `creator`; los juegos aún no están disponibles (mira [Límites](#límites)) | Una carpeta `courses/PWD/assembly/html/unit-01/` que se abre en un navegador, y un zip en `delivery/` |

Cada backend rechaza los comandos del otro para un curso: `plan`, `diff`, `applied` y `link` fallan en un curso html (indican `build`), y `build` falla en un curso creator. `coursekit verify` convierte el contenido en ambos casos: con `html` informa además de las directivas que aún no están disponibles.

El diseño instruccional se hace en creator con cualquiera de los dos backends (el agente de diseño guarda la matriz desde el servidor MCP de slxd), así que el proyecto siempre necesita el servidor MCP: `project.yaml › platform.slxd.mcp_url` y `mcp_name` (por defecto `slxd-creator`). El asistente de `coursekit init` pide la URL en ambos casos. `coursekit agents` escribe el servidor en `.mcp.json`, `opencode.json` y `.codex/config.toml` (consulta [05-agents.md](05-agents.md)).

Las secciones [El flujo de montaje](#el-flujo-de-montaje) a [Registro de directivas](#registro-de-directivas-directives-check-y-sync-directives) describen el **backend creator**. El backend html tiene su propia sección, [El backend html](#el-backend-html). [Revisión del cliente](#revisión-del-cliente) y [Entrega](#entrega) valen para ambos, con las diferencias que se indican allí.

## El flujo de montaje

Esta sección y las siguientes tratan del backend creator. No edites nunca el contenido directamente en creator: si algo está mal, corrige el `.md` y vuelve a cargarlo. La conversión es determinista (el mismo Markdown siempre da los mismos bricks), de modo que las ediciones posteriores se convierten en operaciones de actualización pequeñas en vez de una reconstrucción.

**Requisitos.** El diseño está firmado, cada unidad que vayas a montar está `approved` (las unidades sin firmar solo si quieres expresamente una vista previa) y `course.yaml` tiene `slxd.matrix_id` (y `slxd.theme_id`, si el curso tiene un theme propio: lo escribe `coursekit theme import --course`). Para que los contenidos lleven theme, los tokens de diseño tienen que estar ya derivados de la plataforma (`/define-theme`): mira [El theme del curso](#el-theme-del-curso).

| Paso | Quién | Comando o herramienta |
|---|---|---|
| 1. Esqueleto, solo la primera vez | agente de montaje | Genera en creator un contenido por unidad con una lección por apartado; después `coursekit assemble link PWD --unit 1 --content-id <id>` guarda `units[].content_id`. También aplica el theme del curso a cada contenido (mira más abajo) |
| 2. Plan | `coursekit` | `coursekit assemble plan PWD --unit 1` escribe `assembly/unit-01.plan.json` |
| 3. Diferencias | `coursekit` | `coursekit assemble diff PWD --unit 1` imprime las operaciones para poner creator al día con el plan |
| 4. Aplicar | agente de montaje | Aplica las operaciones con las herramientas de creator (`create_lesson`, `add_brick`, `update_brick`, `delete_brick`, `update_quiz_settings`…) |
| 5. Registrar | agente de montaje | `coursekit assemble applied PWD --unit 1 --lesson U1-S1 --lesson-id <id> --brick-ids id1,id2,…` tras cada lección; `--content` tras renombrar el contenido |
| 6. Repetir | | `diff` hasta que el contenido y todas las lecciones estén `unchanged` |
| 7. Comprobaciones | agente de montaje | Auditoría de accesibilidad, comparación del texto con el `.md`, una instantánea llamada `assembly-AAAA-MM-DD` y los dos enlaces de cada unidad (vista previa en vivo y revisión del cliente) guardados con `coursekit assemble link --preview URL --review URL` |

Lanzas al agente con `/assemble PWD 1` en Claude Code u opencode, o con `coursekit run assemble PWD 1` desde un terminal; sin número de unidad procesa todas las unidades en orden. Ejecuta `plan` de nuevo después de `link`, para que el plan lleve el `content_id`.

### El theme del curso

Los colores y las fuentes de los contenidos en creator salen de un theme de la plataforma, y los gráficos, simulaciones y vídeos de la multimedia se hicieron con los tokens de diseño derivados de ese mismo theme (`/define-theme`, mira [Theme y tokens de diseño](02-workflow.md#theme-y-tokens-de-diseño)). Por eso el montaje no toma el id del theme de un campo rellenado a mano. El agente ejecuta `coursekit theme show --course PWD`:

```text
tokens del proyecto: theme/tokens.json
origen: theme «ACME corporate» de la plataforma (th_8c41, versión 3), importado el 2026-10-09
```

y aplica el id de la línea `origen:` con `set_content_theme` a cada contenido del curso. El theme de un curso es el suyo propio cuando lo tiene (`courses/PWD/theme/`, anotado en `slxd.theme_id`) y, si no, el del proyecto. Cuando no hay tokens derivados de la plataforma (`coursekit theme show` dice que faltan o que están escritos a mano) no hay theme que aplicar: los contenidos conservan el theme por defecto de la plataforma y el agente te avisa de `/define-theme`. Un theme que se cambia después en la plataforma cambia todos los contenidos que lo usan. El backend html no usa un theme de la plataforma: da estilo al paquete con su propio layout base y los tokens del proyecto (mira [Estilos](#estilos)).

### `coursekit assemble`

| Acción | Opciones | Resultado |
|---|---|---|
| `plan` | `--unit N` | Escribe el plan e imprime los avisos; código de salida 1 y sin plan si hay errores |
| `diff` | `--unit N` | Imprime JSON con las operaciones (necesita el plan) |
| `applied` | `--unit N --lesson KEY --lesson-id ID --brick-ids ID1,ID2,…` | Registra una lección como aplicada; el número de ids debe coincidir con los bricks de la lección en el plan |
| `applied` | `--unit N --content` | Registra el título del contenido como aplicado (tras renombrarlo) |
| `link` | `--unit N --content-id ID` | Guarda el id del contenido de creator de la unidad |
| `link` | `--unit N --preview URL` y/o `--review URL` | Guarda el enlace de vista previa en vivo y/o el de revisión del cliente de la unidad. Hace falta al menos uno de `--content-id`, `--preview` y `--review`, y se pueden combinar |
| `build` | `[--unit N] [--version X.Y]` | Solo backend html: construye el paquete de la unidad (mira [`coursekit assemble build`](#coursekit-assemble-build)) |

`plan`, `diff`, `applied` y `link` son del backend creator y necesitan `--unit` (sin él: código de salida 2). En un curso montado con el backend html se rechazan.

```text
$ coursekit assemble plan PWD --unit 1
plan assembly/unit-01.plan.json: 4 lecciones, 16 bricks (ACCORDION 1, NOTE 3, SINGLE_CHOICE 6, TABS 1, TEXT 4, TIMELINE 1)
```

### Ficheros que escribe

| Fichero | Lo escribe | Contenido |
|---|---|---|
| `assembly/unit-NN.plan.json` | `assemble plan` | `course`, `unit`, `content_id`, `content_title` y las lecciones con sus bricks (`type`, `data`, `meta`, `hash`) |
| `assembly/unit-NN.applied.json` | `assemble applied` | Por lección: `lessonId`, `title` y sus bricks (`brickId`, `type`, `hash`); además `content_title` |
| `course.yaml › units[].content_id` | `assemble link` | El contenido de creator de la unidad |
| `course.yaml › units[].links.preview` | `assemble link --preview` | Vista previa en vivo de la unidad: sigue al contenido, sin comentarios |
| `course.yaml › units[].links.review` | `assemble link --review` | Enlace de revisión de la unidad, donde comenta el cliente (mira [Revisión del cliente](#revisión-del-cliente)) |
| `course.yaml › status` | `assemble applied` | Pasa de `media` a `assembly` por sí solo cuando todas las unidades están en creator exactamente como se planificó |

Los dos JSON se versionan con el curso: permiten que coursekit vuelva a cargar solo lo que cambia. No los edites a mano.

Los enlaces son **por unidad**, no por curso, porque cada unidad es un contenido propio en creator. No existe un bloque `links` a nivel de curso. Un comando que modifica el curso (incluido `assemble`) se niega mientras el curso está en pausa: antes, [`coursekit resume`](03-commands.md#coursekit-resume).

### Qué contiene el plan

El backend html construye sus páginas a partir de este mismo plan. Las claves de lección son `U<unidad>-S<apartado>` para las lecciones de contenido y `U<unidad>-E<N.M>` para las actividades de evaluación. El contenido se titula con el título del curso cuando tiene una sola unidad y, si no, `Unidad N. <título de la unidad>`. Las lecciones de evaluación toman `passingGrade` y `maxAttempts` de `design.grading.passing_score` y `design.grading.attempts` en `course.yaml`.

| Markdown | Brick |
|---|---|
| Párrafos consecutivos | `TEXT` (fundidos en uno) |
| `###` a `######` | `HEADING` |
| Listas | `LIST` (con viñetas o numerada) |
| Tablas | `TABLE` |
| Bloques de código | `CODE` (el lenguaje si se conoce y, si no, automático) |
| Cita simple `> …` | `HIGHLIGHT` |
| Directiva `:::nombre` | El brick del registro (tabla en [06-content.md](06-content.md)) |
| Recurso multimedia sin subir | `NOTE` titulada `Recurso multimedia — <tipo>: <título>` (las primeras palabras son las del idioma del curso, y el tipo se escribe como en el contenido, por ejemplo `Infografía`), con descripción y especificaciones |
| Recurso multimedia subido | Según el id del tipo: `image`, `infographic`, `diagram` y `animated_gif` pasan a `IMAGE`; `video` pasa a `VIDEO` (con subtítulos y transcripción si están registrados); `audio` pasa a `AUDIO`; `simulation` y `terminal_demo` pasan a `EMBED`. Más un `ATTACHMENT` por cada descarga subida |
| Etiquetas de objetivo, `---`, comentarios HTML | No se publican |

Solo los subapartados **Instrucciones para el alumno** y **Banco de preguntas** de una actividad de `assessment.md` pasan a su lección de evaluación.

`plan` imprime avisos para un `labelled-graphic` cuya imagen aún no está producida y para una lección sin contenido. Falla (y `verify` lo muestra como `ensamblado: …`) cuando una directiva es desconocida o no sigue su estructura: `single-choice` sin exactamente una opción correcta, `true-false` sin `respuesta: verdadero|falso`, `fill-in-the-blank` sin huecos escritos como `{respuesta}` en la línea `pregunta:`, una directiva de paneles sin paneles `#### Título`, un elemento de `pasapalabra` que no encaja con `- A (empieza): definición :: RESPUESTA`, una clave de la directiva escrita en el otro idioma, o un apartado que no está en el diseño.

Las claves de las líneas de las directivas (`pregunta:`, `respuesta:`, `respuestas:`, `feedback:`, `feedback-correcto:`, `feedback-incorrecto:`, `imagen:`, `posición:`, `título:` y la clave del objetivo) y las palabras que toman algunas (`verdadero`/`falso`; `empieza`/`contiene`) son las del idioma del curso. Un curso en inglés escribe `question:`, `answer: true`, `(starts)`, `(contains)`… Las tablas con las claves y las palabras de cada idioma están en [06-content.md](06-content.md#directivas). Una clave del otro idioma no se ignora: `plan` falla, y `verify` lo muestra como `ensamblado: …`, con el idioma al que pertenece la clave y las claves válidas:

```text
U1-S2: la clave 'question:' es del idioma «en»; en este curso se usan: feedback, feedback-correcto, feedback-incorrecto, imagen, objetivo, posición, pregunta, respuesta, respuestas, título
```

### `diff`

Por cada lección, `diff` da una acción y sus operaciones; el `data` de cada operación es la carga útil para la herramienta de creator:

| Acción | Significado |
|---|---|
| `create` | La lección no está en `applied.json`: una operación `add` por brick |
| `update` | Operaciones `update`, `delete`, `add` (con `position`) y `rename_lesson`, calculadas a partir de las huellas de los bricks |
| `unchanged` | Nada que hacer |
| `delete` | La lección está en `applied.json` pero ya no en el plan; el agente te pregunta antes de borrarla |

El propio contenido tiene `action: rename` cuando su título difiere del aplicado y, si no, `unchanged`.

## Registro de directivas: `directives check` y `/sync-directives`

Los dos backends leen el registro de directivas, que se mantiene al día con los bricks de creator. El registro (`defaults/directives.yaml`, que se puede cambiar en `config/directives.yaml`) debe listar todos los tipos de brick de creator, ya sea como directiva o en `not_directives`. Cuando creator añade o retira bricks:

```bash
coursekit run sync-directives
```

o `/sync-directives` en tu agente. El agente guarda el resultado de la herramienta de creator `list_brick_types` como `.cache/list_brick_types.json` y ejecuta:

```bash
coursekit directives check .cache/list_brick_types.json
```

| Salida | Significado |
|---|---|
| `NUEVO <BRICK> [categoría] cuándo usarlo` | Un brick de creator que no es una directiva ni está en `not_directives` |
| `RETIRADO <BRICK> (en la directiva 'nombre')` o `(en not_directives)` | El registro nombra un brick que ya no existe |
| `ok: el registro de directivas coincide con creator (N bricks)` | Nada que hacer; código de salida 0 (1 si hay alguna línea anterior) |

Por cada `NUEVO`, el agente comprueba el esquema del brick y o bien añade una directiva (nombre en kebab-case, `brick`, `role`, `use`) o lo lista en `not_directives` con un motivo. Por cada `RETIRADO`, elimina la entrada y lista los ficheros de contenido que la usaban (no los cambia). Edita `config/directives.yaml`, actualiza `synced_with_creator` con la fecha de hoy y repite `check` hasta que diga `ok`. No hace commit.

## El backend html

Con `assembly.backend: html` no se carga nada en ninguna plataforma. `coursekit assemble build` convierte cada unidad en un paquete SCORM propio: una página web con todas sus lecciones, un reproductor, estilos, la multimedia producida y el manifiesto. Lee los mismos `content.md`, `assessment.md` y multimedia producida que el backend creator, y reutiliza su plan (mismas directivas, mismo formato, mismos errores). No edites nunca el paquete: si algo está mal, corrige el `.md` y vuelve a construirlo.

### Requisitos y constructor

- El diseño está firmado y las unidades `approved` antes de construir el paquete que vas a entregar (se puede hacer una vista previa de una unidad sin firmar; `build` no comprueba el estado de la unidad). Un curso en pausa se rechaza: antes, [`coursekit resume`](03-commands.md#coursekit-resume).
- El reproductor se empaqueta en cada construcción a partir de dos paquetes de npm, `@studiolxd/scorm` (el runtime de SCORM) y `esbuild`. Se instalan una sola vez por máquina en el almacén de coursekit (mira [04-configuration.md](04-configuration.md#el-almacén-de-la-máquina)), no en el proyecto. `coursekit setup` los prepara cuando el proyecto usa el backend html, `coursekit assemble build` lo intenta de nuevo si faltan y `coursekit doctor` informa de si están. Hacen falta Node y npm, y acceso a la red la primera vez.
- La multimedia producida con sus ficheros (mira [Multimedia](#multimedia)), si la unidad tiene marcadores.

### `coursekit assemble build`

```bash
coursekit assemble build PWD                          # todas las unidades: carpeta de vista previa
coursekit assemble build PWD --unit 1                 # una unidad
coursekit assemble build PWD --unit 1 --version 1.0   # además el zip, listo para `delivery add`
```

| Opción | Significado |
|---|---|
| `--unit N` | Construye solo esa unidad; sin ella, todas las unidades del curso |
| `--version X.Y` | Escribe además el zip `courses/PWD/delivery/<file_name de delivery.yaml>` (por defecto `{code}-U{unit:02d}-v{version}-{standard}.zip`, por ejemplo `PWD-U01-v1.0-scorm12.zip`) |

```text
$ coursekit assemble build PWD --unit 1 --version 1.0
unidad 1: 5 ficheros en courses/PWD/assembly/html/unit-01
paquete PWD-U01-v1.0-scorm12.zip (212.4 KB)
```

Sin `--version` la última línea es `vista previa: abre courses/PWD/assembly/html/unit-01/index.html en el navegador`. Los avisos se imprimen antes (`AVISO …`): un `labelled-graphic` cuya imagen aún no está producida y un recurso producido cuyo fichero no existe.

Cada construcción empieza de cero: la carpeta de la unidad se borra y se escribe de nuevo. El estándar (SCORM 1.2 o 2004 4.ª edición) es `export.standard` de la configuración de entrega ([Ajustes de exportación SCORM](#ajustes-de-exportación-scorm)). El comando falla, con código de salida 1 y la lista de problemas, cuando:

- el plan tiene errores (una directiva desconocida, una pregunta sin su opción correcta, una clave escrita en el otro idioma…: los mismos mensajes que `verify`);
- la unidad usa una directiva que aún no está disponible (los juegos);
- el paquete no lleva todas las palabras del contenido (mira [La comprobación de las palabras](#la-comprobación-de-las-palabras));
- no se puede preparar el constructor (Node, npm o la instalación han fallado: `coursekit doctor`).

No se escribe nada en `assembly/unit-NN.plan.json`: el plan se construye en memoria y `assemble plan`, `diff`, `applied` y `link` no se aplican. Cuando todas las unidades tienen su paquete construido y el curso estaba en `media`, `build` lo pasa a `assembly` (el historial anota `Every unit built`).

### El paquete

```text
courses/PWD/assembly/html/unit-01/
├── index.html          todas las lecciones de la unidad en una página
├── imsmanifest.xml     un SCO; SCORM 1.2 o 2004 4.ª edición
├── assets/
│   ├── styles.css      layout, tokens, maqueta y componentes, en ese orden
│   └── player.js       runtime de SCORM y comportamiento de los componentes (empaquetado)
└── media/              multimedia producida, descargas y subtítulos
```

La carpeta se genera y git la ignora (`courses/*/assembly/html/`). Se abre directamente desde el disco en un navegador (abre `index.html`): sin LMS el runtime de SCORM es un simulacro en memoria, de modo que el paquete funciona igual y no se envía nada a ninguna parte. El zip lleva los mismos ficheros, con `imsmanifest.xml` el primero y en la raíz, que es lo que comprueba `coursekit delivery add`.

La página se construye con mejora progresiva. Las lecciones (una por apartado de `content.md`, luego una por actividad de `assessment.md`) son secciones de una sola página, y la página está completa y se lee sin JavaScript: todas las lecciones una tras otra, los paneles abiertos y el texto de cada respuesta en el marcado. El reproductor muestra entonces una lección cada vez. El HTML del contenido se sanea con una lista de etiquetas y atributos permitidos: sin scripts, sin manejadores de eventos, sin enlaces `javascript:` (un enlace eliminado conserva su texto).

### Componentes

| Directiva o Markdown | Brick | En el paquete |
|---|---|---|
| Párrafos, `###`–`######`, listas, tablas, bloques de código | `TEXT`, `HEADING`, `LIST`, `TABLE`, `CODE` | Texto, títulos (nivel 3 a 6; el título de la lección es el nivel 2), listas, tablas en una caja con desplazamiento, bloques de código |
| `note`, `highlight`, cita en bloque simple, `quote` | `NOTE`, `HIGHLIGHT`, `QUOTE` | Una nota con título, un bloque destacado, una cita con su autoría |
| `accordion` | `ACCORDION` | Elementos `details` nativos (funcionan sin JavaScript) |
| `tabs` | `TABS` | Lista de pestañas con las teclas de flecha, Inicio y Fin; todos los paneles están en el marcado |
| `carousel`, `carousel-quotes` | `CAROUSEL`, `CAROUSEL_QUOTES` | Una diapositiva cada vez con botones de anterior y siguiente y un estado «Diapositiva n de N» |
| `timeline` | `TIMELINE` | Lista ordenada con la fecha y el título de cada hito |
| `flashcards`, `flashcard-gallery` | `FLASHCARD_CAROUSEL`, `FLASHCARD_GALLERY` | Tarjetas que se giran (clic, Intro o Espacio), una a una o en cuadrícula |
| `labelled-graphic` | `LABELLED_GRAPHIC` | La imagen con puntos numerados que abren su explicación (Escape o Cerrar para descartarla). Sin imagen producida: una lista simple de los puntos |
| `dialog` | `DIALOG` | Las intervenciones de la conversación con el nombre de cada interlocutor |
| Marcador de imagen, infografía, esquema o GIF animado (producido) | `IMAGE` | Figura con texto alternativo y pie |
| Marcador de vídeo (producido) | `VIDEO` | Vídeo con controles, pista de subtítulos (si hay un `.vtt`) y la transcripción en un `details` |
| Marcador de audio (producido) | `AUDIO` | Audio con controles y la transcripción |
| Marcador de simulación y de demo de terminal (producido) | `EMBED` | Un `iframe` de la carpeta del paquete (`media/<id>/index.html`) |
| Descarga de un recurso | `ATTACHMENT` | Un enlace de descarga |
| `single-choice`, `multi-select`, `true-false` | `SINGLE_CHOICE`, `MULTI_SELECT`, `TRUE_FALSE` | Botones de opción o casillas; verdadero-falso ofrece Verdadero y Falso |
| `sorting` | `SORTING` | Los elementos desordenados, con botones para subir y bajar |
| `match` | `MATCH` | Una lista desplegable por término de la izquierda, con los términos de la derecha desordenados |
| `sorting-groups` | `SORTING_GROUPS` | Una lista desplegable por elemento con las categorías |
| `fill-in-the-blank` | `FILL_IN_THE_BLANK` | Un cuadro de texto en cada hueco de la frase (`{a/b}` admite varias respuestas) |
| `order-words` | `ORDER_WORDS` | Botones con palabras que se pulsan para colocarlas en la frase por orden, una línea por frase |
| `short-answer` | `SHORT_ANSWER` | Un cuadro de texto que se compara con las respuestas admitidas |

Las respuestas de texto (`fill-in-the-blank`, `short-answer`) se comparan sin tener en cuenta mayúsculas, tildes ni espacios sobrantes. Una pregunta de selección múltiple es correcta solo cuando cada opción está como dice la clave. La retroalimentación sigue a la directiva: `feedback-correcto:` tras una respuesta correcta, `feedback-incorrecto:` tras una incorrecta y `feedback:` siempre. Las directivas se explican en [06-content.md](06-content.md#directivas); los juegos no están en esta tabla porque aún no están disponibles.

### El reproductor

Con JavaScript la página se convierte en un pequeño reproductor de curso:

- Se muestra una lección cada vez. La lista de lecciones (la navegación «Lecciones») marca la lección actual y las visitadas; **Anterior** y **Siguiente** mueven entre ellas; la barra de progreso muestra el porcentaje de lecciones visitadas; un enlace para **saltar al contenido** es el primer elemento de la página. Al cambiar de lección la página vuelve arriba y el foco pasa al título de la lección.
- La unidad se reabre en la lección donde la dejó la persona.
- Las **preguntas de práctica** (en las lecciones de contenido) tienen un botón **Comprobar**. No hace nada hasta que la pregunta está contestada; entonces bloquea las respuestas, las marca y muestra la retroalimentación, y el botón pasa a **Reintentar**, que borra la respuesta y vuelve a desordenar.
- **Las lecciones de evaluación** (`assessment.md`) se corrigen juntas con un solo botón **Enviar respuestas**. Las preguntas sin contestar impiden el envío («Responde todas las preguntas antes de enviar.»). La puntuación es el porcentaje de preguntas totalmente correctas, redondeado; se aprueba cuando llega a `design.grading.passing_score` de `course.yaml`. `design.grading.attempts` limita los intentos (vacío o 0: sin límite). Tras enviar, cada pregunta muestra su marca y su retroalimentación, y el informe indica la puntuación y si se ha aprobado; si no, aparece **Reintentar** mientras queden intentos (el informe dice cuántos) y «No quedan intentos.» cuando no queda ninguno. Los intentos usados y la mejor puntuación se guardan en los datos de suspensión, de modo que reabrir la unidad no da intentos nuevos.
- Los textos de la interfaz (etiquetas de botones y mensajes) están en el idioma del curso.
- La página es adaptable (la lista de lecciones es una columna lateral en pantallas anchas), respeta el movimiento reducido y los colores forzados, y se imprime con todas las lecciones.

### Seguimiento SCORM

El runtime es `@studiolxd/scorm`, empaquetado en `assets/player.js`.

| Qué | Cómo se informa |
|---|---|
| Ubicación | La clave de la lección actual (`U1-S2`, `U1-E1.1`); la unidad se reabre ahí |
| Datos de suspensión | Las lecciones visitadas, los intentos usados y la mejor puntuación |
| Progreso | Lecciones visitadas dividido entre las lecciones de la unidad (medida de progreso, SCORM 2004) |
| Finalización | Sin test: completada cuando se han visitado todas las lecciones, incompleta hasta entonces. Con test, en SCORM 2004: completada cuando se han visitado todas las lecciones, y aprobada o suspensa cuando se envía el test. Con test, en SCORM 1.2, que tiene un único estado: aprobada o suspensa cuando se envía el test |
| Puntuación | Bruta (porcentaje), mínimo 0 y máximo 100; en SCORM 2004 también la escalada |
| Interacciones | Una por pregunta del test: su id, el tipo (choice para la opción simple y múltiple, fill-in para el resto), la respuesta de la persona (cortada a 250 caracteres), correcta o incorrecta, peso 1 |
| Sesión | Tiempo de sesión y salida `suspend`; los datos se confirman tras cada cambio y la sesión se termina cuando la página se oculta o se cierra |

### Estilos

`assets/styles.css` se construye por capas, cada una sobre la anterior:

1. **El layout base** del paquete: neutro, accesible, gobernado por variables CSS (`--color-background`, `--color-text`, `--color-accent`, `--color-surface`, `--color-line`, `--color-correct`, `--color-wrong`, `--font-family`, `--font-size-base`, `--radius`, `--space-*`…). Sus clases empiezan por `ck-`.
2. **Los tokens** del curso: `courses/PWD/theme/tokens.css` si el curso tiene theme propio y, si no, `theme/tokens.css` del proyecto. Si no hay tokens, esta capa queda vacía y se ve el layout base tal cual.
3. **`theme/maqueta.css`** del proyecto y después **`courses/PWD/theme/maqueta.css`**: la hoja de estilos que da otro aspecto a lo que haga falta (la «maqueta»).
4. **Todos los `components/*.css`** del proyecto, por orden de nombre de fichero.

`coursekit theme import theme/maqueta.css` deriva los tokens de diseño de las variables CSS de la hoja de estilos sobre el layout base y anota de dónde proceden, de modo que los gráficos, simulaciones y vídeos de la multimedia se hacen con los mismos colores y fuentes (mira [Theme y tokens de diseño](02-workflow.md#theme-y-tokens-de-diseño)).

Los ficheros `*.js` de la carpeta `components/` del proyecto se empaquetan en el reproductor, antes de que arranque, por orden de nombre de fichero. Son módulos ES normales que pueden usar el DOM, para un comportamiento que el paquete no tiene. Un proyecto sin carpeta `components/` solo tiene las capas anteriores.

### Multimedia

No hay subida a ninguna plataforma: la multimedia son ficheros que viajan dentro del paquete. Un recurso con estado `produced` o `uploaded` y `--file` apuntando a un fichero local se copia a `media/` y lo usa el componente que corresponde; para una simulación o una demo, `--file` es la carpeta del paquete o su `index.html`, y se copia la carpeta entera. La ruta se lee relativa a la carpeta del curso o a su carpeta `media/` (o absoluta). Mira [07-media.md](07-media.md).

- `--subtitles-path` apunta a un `.vtt` local de un vídeo; se copia a `media/` y se añade como pista de subtítulos. Un valor que no sea un fichero local existente (por ejemplo, una ruta de otra plataforma) se ignora.
- La transcripción, si se registró con `--transcript`, va en un bloque plegable bajo el vídeo o el audio.
- Las descargas registradas para el recurso (`--download`) se copian a `media/files/` y se enlazan.
- Un recurso que no está producido queda como una nota visible con su descripción y sus especificaciones, de modo que el paquete nunca tiene un hueco. Un recurso producido cuyo fichero no existe es un aviso y también queda como esa nota.

### La comprobación de las palabras

La construcción compara las palabras de `content.md` y `assessment.md` que lee la persona con las palabras de la página. De `assessment.md` solo cuenta el texto bajo **Instrucciones para el alumno** y **Banco de preguntas**, porque solo eso llega al paquete (los demás subapartados documentan la actividad para el equipo). Deja fuera lo que no es texto para la persona: la sintaxis del formato (las líneas `:::`, las claves `pregunta:` y `respuesta:`, las viñetas), los metadatos (las etiquetas de objetivo, la clave de objetivo, los comentarios, `imagen:` y `posición:`), los marcadores multimedia (su caja se sustituye por el recurso o por su nota) y los destinos de los enlaces. Si falta alguna palabra, la construcción falla con `el paquete no contiene N palabra(s) del contenido: …` y las veinte primeras palabras.

La causa típica es una línea que el formato no renderiza, por ejemplo una pregunta sin su clave `pregunta:` (escrita como una línea normal dentro de la directiva). Corrígela en el `.md` y vuelve a construir. La comparación es por conjuntos de palabras, así que no depende de cómo disponga el texto un componente.

### Límites

- **Los juegos aún no están disponibles**: `word-search`, `wordle`, `hangman`, `pasapalabra`, `memory` y `trivial`. `coursekit assemble build` rechaza una unidad que los use (`MEMORY: este componente aún no está disponible en el backend html…`) y `coursekit verify` los informa como `assembly: …`. Usa otra directiva, o el backend creator.
- **No se ha probado en un LMS real.** Prueba el paquete en el LMS de destino (o en SCORM Cloud) antes de entregarlo: comprueba que se reanuda la ubicación, que se registran la puntuación y el estado, y que el test se comporta como esperas.
- El paquete es un SCO por unidad. Un curso de varias unidades da varios paquetes.
- `export.reporting` y `export.scoreSource` no se aplican: el estado y la puntuación son los de [Seguimiento SCORM](#seguimiento-scorm).

## Revisión del cliente

Opcional: el cliente revisa el curso montado y lo comenta antes de la entrega. Que sea obligatoria es un ajuste, `client_review.required` de la configuración de entrega (por defecto `false`; por proyecto en `config/delivery.yaml`, por curso en `course.yaml › delivery › client_review`: mira [04-configuration.md](04-configuration.md#delivery-exportación-scorm-y-revisión-del-cliente)). El proceso y sus estados están en [02-workflow.md](02-workflow.md#revisión-del-cliente-opcional).

Con el backend html no hay enlaces de plataforma que crear ni anotar: la persona aloja el paquete (el zip en un LMS de pruebas, o la carpeta de vista previa en un servidor web) y da el enlace al abrir la ronda: `coursekit client PWD send --where URL`. Las rondas, `changes`, `approve` y `skip` funcionan como se describe más abajo; para aplicar los comentarios del cliente, edita el `.md`, ejecuta `coursekit verify` y vuelve a construir (`coursekit assemble build`), y después aloja el paquete nuevo.

### Los enlaces de cada unidad

Este apartado trata del backend creator. Al final de `/assemble`, el agente de montaje crea para cada unidad (cada una es un contenido propio de creator) dos enlaces y los anota con `coursekit assemble link`:

| Enlace | Herramienta de creator | Para quién |
|---|---|---|
| Vista previa en vivo (`links.preview`) | `share_content` (activado, con actualizaciones en vivo) | El equipo. Muestra el contenido tal como está, sin comentarios |
| Revisión (`links.review`) | `enable_review` (sin contraseña salvo que la pidas) | El cliente. Publica la versión `v1` de la revisión y deja que el cliente comente sin cuenta. `get_review` la vuelve a leer |

```bash
coursekit assemble link PWD --unit 1 --preview https://acme.example.com/p/abc --review https://acme.example.com/r/xyz
# unidad 1 -> preview https://acme.example.com/p/abc; enlace de revisión https://acme.example.com/r/xyz
```

### Rondas

Una ronda es el ciclo «se envía al cliente, el cliente responde». Solo una persona ejecuta `coursekit client`; a los agentes se les deniega.

```bash
coursekit client PWD send --to "equipo de formación de ACME"     # ronda 1: el curso pasa a client_review
```

`send` necesita el curso en `assembly`, ninguna ronda abierta y los enlaces de revisión de las unidades anotados (o un solo enlace dado con `--where URL`, que los sustituye). Anota en `course.yaml › client_review` el número de ronda, quién la envió y cuándo, `--to` y los enlaces. Los enlaces se los envías tú al cliente.

Mientras el cliente comenta, el agente de montaje trata los comentarios con `/client-feedback PWD` (o `/client-feedback PWD 2` para una sola unidad). Usa la skill `client-review` y estas herramientas de creator:

| Paso | Herramienta de creator |
|---|---|
| Leer el estado y los hilos pendientes | `get_review`, `list_review_comments` (estado `pending`; `since` para leer solo lo nuevo). Cada hilo indica la lección, el texto y, si lo hay, una captura de pantalla |
| Aplicar lo acordado | edita el `.md` (nunca creator), `coursekit verify`, y después `assemble plan`, `diff` y aplicar como en [el flujo de montaje](#el-flujo-de-montaje) |
| Publicar lo que cambió | `publish_review_version` con una etiqueta (`v1.1`, `v1.2`...). Solo la última versión admite comentarios |
| Responder | `reply_review_comment` en cada hilo y después `set_review_comment_status` con `resolved`. `verified` lo marca el cliente |

Antes de cambiar nada, el agente te muestra una tabla con cada comentario, el apartado al que se refiere y lo que propone (aplicar, no aplicar y por qué, o te lo deja a ti), y espera tu decisión; sin interfaz, aplica solo correcciones de texto claras que encajen con el diseño. Un comentario que cambia objetivos, horas, actividades o estructura es un cambio de diseño (`/design-change`), no una edición de contenido. Una unidad editada después de su firma vuelve a `verified` y necesita nueva revisión con IA y nueva firma.

Después cierras la ronda:

| Comando | Cuándo |
|---|---|
| `coursekit client PWD changes --note "..."` | El cliente quiere cambios. La ronda se cierra (resultado `changes`) y el curso vuelve a `assembly`. Aplica, vuelve a montar y ejecuta `send` otra vez: es la ronda 2 |
| `coursekit client PWD approve --by "Nombre" --note "..."` | El cliente está conforme. La ronda se cierra (resultado `approved`) con el nombre del cliente y la fecha, y el curso se puede entregar |
| `coursekit client PWD skip --reason "..."` | Entregas sin la aprobación del cliente. Anota una ronda con resultado `skipped` y el motivo; necesita el curso en `assembly` o `client_review` sin ronda abierta |

Al cerrar una ronda, el agente puede exportar los comentarios de la ronda con `export_review_comments`: devuelve un CSV mediante un enlace firmado válido durante 24 horas, y el fichero se guarda como `.cache/client-review/PWD-round-N.csv`, que git ignora y `coursekit publish` nunca copia. El CSV contiene los correos de los invitados que comentaron: no lo pegues en ningún sitio ni lo muevas al curso.

`coursekit status PWD` muestra la última ronda y su resultado (`abierta`, `pidió cambios`, `aprobada` u `omitida`), y el siguiente paso en `client_review` es anotar la respuesta del cliente.

## Entrega

Cada unidad es un paquete SCORM: con el backend creator, un contenido de creator exportado desde la plataforma; con el backend html, el zip que escribe `coursekit assemble build --version`.

### Antes de exportar: `delivery check`

```bash
coursekit delivery check PWD
# PWD: se puede entregar
```

`/deliver` empieza con este comando, y `delivery name` y `delivery add` aplican las mismas reglas. Se niega (código de salida 1, con un mensaje) cuando:

| Caso | El mensaje dice | Qué hacer |
|---|---|---|
| El curso está en pausa | «PWD está en pausa desde ...» | `coursekit resume PWD` |
| `client_review.required` es `true` y no hay ninguna ronda | «PWD necesita la revisión del cliente antes de entregarse ...» | Abre una ronda (`send`), o omítela con un motivo (`skip`) |
| La última ronda pidió cambios | «el cliente pidió cambios en PWD ...» | Aplica los cambios, vuelve a montar y abre la ronda siguiente (`send`) |
| La última ronda sigue abierta | «PWD espera a la respuesta del cliente (ronda N, enviada a ...)» | Anota la respuesta: `approve` o `changes` |

Los textos exactos están en [Solución de problemas](09-troubleshooting.md#el-curso-está-en-pausa-o-la-revisión-del-cliente-bloquea-la-entrega).

Cuando es solo cuestión de estado, imprime un aviso en lugar de negarse: `aviso: PWD está en «<estado>», no en un estado de entrega (assembly, client_review): el paquete se registra, pero el curso no se marca como entregado`. Sin la exigencia (`required: false`) las rondas no importan: un curso en `assembly` siempre se puede entregar.

### Ajustes de exportación SCORM

De `src/coursekit/defaults/delivery.yaml`; cámbialos en `config/delivery.yaml`, `project.yaml › delivery` o `course.yaml › delivery` ([04-configuration.md](04-configuration.md)).

| Clave | Por defecto | Valores |
|---|---|---|
| `export.deliveryType` | `lms` | |
| `export.standard` | `scorm_1_2` | `scorm_1_2`, `scorm_2004` |
| `export.reporting` | `passed_incomplete` | `passed_incomplete`, `completed_incomplete` |
| `export.scoreSource` | `quiz` | `quiz`, `lessonProgress` |
| `file_name` | `{code}-U{unit:02d}-v{version}-{standard}.zip` | Patrón del nombre de fichero |

Con el backend creator, el agente llama a la herramienta de exportación de creator con los valores de `export`, espera a que termine el trabajo y descarga el paquete. Con el backend html solo se usan `export.standard` y `file_name`: el estándar decide el manifiesto y el seguimiento del paquete, y `reporting` y `scoreSource` no se aplican (mira [Seguimiento SCORM](#seguimiento-scorm)).

### Nombre del fichero y registro

```bash
coursekit delivery name PWD --unit 1 --version 1.0
# PWD-U01-v1.0-scorm12.zip
```

`{standard}` pierde los guiones bajos (`scorm_1_2` pasa a `scorm12`, `scorm_2004` pasa a `scorm2004`). El paquete se descarga a `courses/PWD/delivery/` con ese nombre y se registra:

```bash
coursekit delivery add PWD --unit 1 --version 1.0 \
  --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip --job <id-del-trabajo-de-exportación> --snapshot <id-de-la-instantánea>
# registrado PWD-U01-v1.0-scorm12.zip · curso entregado
```

Con el backend html, `build` escribe el zip directamente en `courses/PWD/delivery/` con ese nombre, así que no hay nada que descargar ni trabajo de exportación ni instantánea:

```bash
coursekit assemble build PWD --unit 1 --version 1.0
coursekit delivery add PWD --unit 1 --version 1.0 --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip
# registrado PWD-U01-v1.0-scorm12.zip · curso entregado
```

`delivery add` comprueba que el fichero sea un zip válido con `imsmanifest.xml` en su raíz, que esté directamente dentro de `courses/PWD/delivery/` y que la unidad exista. Después añade una entrada a `course.yaml › deliveries` con `version`, `unit`, `date`, `by` (la identidad de firma de `.env`), `standard`, `file`, `sha256`, `export_job` y `snapshot` (vacíos en un paquete html). Cuando todas las unidades tienen un paquete de la misma versión **y el curso está en `assembly` o `client_review`**, el estado del curso pasa a `delivered` y se añade una entrada al historial. En cualquier otro estado el paquete se registra con el aviso de arriba y el estado del curso no cambia. Mientras alguna unidad no tiene paquete de esa versión, imprime `registrado <fichero> · unidades pendientes de la v<versión>: [2, 3]`. `courses/*/delivery/` está en el `.gitignore` del proyecto: los zip no se versionan, `course.yaml` sí.

## Publicación en la carpeta espejo

La carpeta espejo es una copia de solo lectura de los cursos en una carpeta sincronizada por el cliente de escritorio de tu proveedor (o cualquier carpeta). Todo lo que se edite allí se sobrescribe en la siguiente publicación.

| Ajuste | Dónde | Significado |
|---|---|---|
| `mirror.provider` | `project.yaml` | `sharepoint`, `onedrive`, `google-drive`, `nextcloud`, `folder` o `none` |
| `MIRROR_DIR` | `.env` (personal) | Ruta local de la carpeta sincronizada. La escribe `coursekit init --mirror-dir RUTA` |
| `mirror.url` | `project.yaml` (compartido) | Dirección web de la carpeta espejo, usada para los enlaces a los cursos del catálogo. La escribe `coursekit init --mirror-url URL` |

`mirror.url` según el proveedor, y el enlace que se escribe en el catálogo para el curso `PWD`:

| Proveedor | Qué pegar en `mirror.url` | Enlace para `PWD` |
|---|---|---|
| `sharepoint`, `onedrive` | La dirección de la carpeta en la barra del navegador de la biblioteca (`…/Forms/AllItems.aspx?id=<ruta de la carpeta>`), una dirección de «copiar vínculo» (`…/:f:/r/<ruta>`) o una ruta simple (`/sites/<sitio>/<biblioteca>/<carpeta>`) | Desde la dirección de la biblioteca: la misma dirección con `/courses/PWD` añadido a la ruta de `id`. Desde un «copiar vínculo»: `https://<host>/<ruta de la carpeta>/courses/PWD` (se descartan el prefijo `/:f:/r` y la consulta). Desde una ruta simple: la ruta con `/courses/PWD` añadido. Un enlace para compartir (`/:f:/s/<token>`) no lleva ruta, así que no se escriben enlaces (la comprobación avisa) |
| `nextcloud` | La dirección de la aplicación Archivos con `?dir=/Carpeta` | La misma dirección con `dir=/Carpeta/courses/PWD` |
| `google-drive` | La dirección de la carpeta | La misma dirección para todos los cursos (los ids de carpeta no van en la ruta) |
| `folder` | Cualquier dirección base; `{code}` se sustituye por el código del curso | La dirección con `{code}` sustituido; sin `{code}`, la misma dirección |

```bash
coursekit publish --check    # informa de la configuración; no escribe nada
coursekit publish            # todos los cursos
coursekit publish PWD        # un curso
```

`--check` imprime una de estas líneas: `info: sin carpeta espejo (project.yaml › mirror.provider: none)`, `aviso: MIRROR_DIR no está definido en .env; no se publicará nada`, `aviso: MIRROR_DIR no existe: …` u `ok: carpeta espejo de <proveedor> en <ruta>`, seguida de una línea sobre los enlaces (`ok: enlaces a las carpetas de curso como …`, `info: no hay mirror.url…` o el aviso del enlace para compartir). `--only-if-configured` hace que `publish` no haga nada, en silencio, cuando no hay carpeta espejo; el hook de git `post-merge` lo usa para publicar tras cada pull.

### Publicación automática

Rara vez ejecutas `coursekit publish` tú. Cuando el proyecto tiene carpeta espejo, estos comandos publican el curso que han cambiado en cuanto terminan: `coursekit new`, `sync` (sin `--check`), `verify` (sin `--no-update`), `reviewed`, `approve`, `assemble applied`, `assemble link`, `assemble build`, `media set`, `delivery add`, `hold`, `resume`, `client` y `handoff` (tras cada paso). Por eso los enlaces de preview y review, el estado y los paquetes llegan al espejo y al catálogo sin que nadie lo pida.

- El catálogo del proyecto (`courses/catalogo-cursos.xlsx`) se actualiza siempre, en silencio.
- Sin espejo (`mirror.provider: none`, o sin `MIRROR_DIR`) no ocurre nada más y no se imprime nada.
- Si el espejo no se puede actualizar (la carpeta no existe, el Excel está abierto), el comando imprime un aviso por la salida de error y conserva su propio código de salida: su trabajo está hecho y `coursekit publish` lo reintenta.
- La única publicación que ejecuta un agente es la posterior a exportar el diseño instruccional: descargar el Excel no es un comando de `coursekit` que pueda hacerlo.

Qué hace `publish`:

- Por cada curso copia `course.yaml`, `design/`, `content/` y `reviews/` a `<MIRROR_DIR>/courses/PWD/`, solo los ficheros cuyo contenido cambió. `brief/`, `media/` y `assembly/` no se reflejan.
- Los ficheros que publicó antes y que ya no existen en el curso se eliminan de la carpeta espejo (se registran en `courses/PWD/.published.json`, dentro de la carpeta espejo), junto con las carpetas que queden vacías. Los ficheros que nunca publicó no se tocan.
- `delivery/` solo añade: un paquete se copia una vez y nunca se sobrescribe ni se borra en la carpeta espejo, aunque se elimine en local. Una versión nueva tiene un nombre de fichero nuevo.
- Escribe el catálogo en `<MIRROR_DIR>/<fichero del catálogo>`, con enlaces a las carpetas de curso. Si el Excel está abierto, falla con `no se puede reemplazar … (¿está abierto en Excel?)`.
- Primero actualiza el catálogo de `courses/` e imprime `escrito <ruta> (N cursos, M unidades)` (no con `--only-if-configured`). Después imprime una línea por cada curso que cambió (`publicado PWD: 5 copiados, 0 eliminados, 0 sin cambios`) y una para el catálogo del espejo. Con `mirror.provider: none` imprime la primera línea y dice que no hay nada que publicar (código 0). Con un proveedor y sin `MIRROR_DIR`, falla con `no hay carpeta espejo configurada (project.yaml › mirror y MIRROR_DIR en .env)`.

## El catálogo de seguimiento

`coursekit catalog` construye el Excel de seguimiento a partir de todos los `courses/*/course.yaml`. Es un fichero generado: no lo edites nunca (los cambios se hacen en cada `course.yaml`). Se escribe junto a los cursos, en `courses/` (`--output RUTA` para cambiarlo; git lo ignora), y, con `publish`, en la carpeta espejo. La copia de `courses/` la actualizan los mismos comandos que publican, con o sin espejo, y no lleva enlaces a carpetas. El nombre del fichero y todas las etiquetas siguen el `ui_language` del proyecto: `course-catalog.xlsx` en inglés, `catalogo-cursos.xlsx` en español. El color de la cabecera es el token `accent-strong` (o, si no, `accent`) de `theme/tokens.json`, o gris oscuro; las hojas `Cursos` y `Unidades` tienen la cabecera inmovilizada y filtros. `coursekit catalog` por sí solo deja vacía la columna **Carpeta**: los enlaces los escribe `publish`.

Hojas, en el idioma del catálogo (español / inglés): `Cursos` / `Courses`, `Unidades` / `Units` e `Información` / `About`.

**Hoja de cursos** (una fila por curso)

| Columna (español) | Column (English) | Valor |
|---|---|---|
| Código | Code | `code` |
| Título | Title | `title` |
| Estado | Status | Estado del curso, traducido |
| Horas | Hours | `design.hours` |
| Unidades | Units | Número de unidades |
| Palabras mínimas | Minimum words | Suma de las palabras mínimas de los apartados |
| Palabras actuales | Current words | Palabras para el alumno escritas en cada `content.md` (el mismo recuento que `verify`) |
| % palabras | % words | Actuales entre mínimas, como porcentaje (puede superar el 100 %) |
| Recursos multimedia | Media assets | El mayor entre los recursos reservados en el contenido y los recursos del manifiesto |
| Recursos producidos | Assets produced | Recursos del manifiesto que están `produced` o `uploaded` |
| Carpeta | Folder | Enlace a la carpeta del curso en la carpeta espejo (hipervínculo; solo lo escribe `publish`, y solo con un `mirror.url` utilizable) |
| DI aprobado por | Design approved by | Quién firmó el diseño |
| DI aprobado el | Design approved on | Fecha y hora de esa firma |
| Resp. DI · Resp. redacción · Resp. revisión · Resp. multimedia · Resp. montaje | Design lead · Writing lead · Review lead · Media lead · Assembly lead | `owners` (`instructional_design`, `writing`, `review`, `media`, `assembly`) |
| Última actualización | Last update | Fecha de la última entrada de `history` |
| Última nota | Last note | Nota de esa entrada |

**Hoja de unidades** (una fila por unidad)

| Columna (español) | Column (English) | Valor |
|---|---|---|
| Código | Code | Código del curso |
| Unidad | Unit | Número de la unidad |
| Título | Title | Título de la unidad |
| Estado | Status | Estado de la unidad tal cual: `pending`, `writing`, `verified`, `reviewed` o `approved` |
| Horas | Hours | Horas de la unidad |
| Palabras mínimas · Palabras actuales | Minimum words · Current words | Como arriba, para la unidad |
| Recursos multimedia | Media assets | Recursos reservados en el `content.md` de la unidad |
| Aprobación editorial | Editorial approval | Quién firmó la unidad |
| Aprobada el | Approved on | Fecha y hora de esa firma |
| ID de contenido | Content ID | `units[].content_id` |
| Preview | Preview | `units[].links.preview` (hipervínculo): vista previa en vivo de la unidad |
| Review | Review | `units[].links.review` (hipervínculo): enlace de revisión del cliente de la unidad |

**Hoja de información**: cuándo se generó, el origen (`courses/*/course.yaml`), la rama y el commit, el usuario de git que lo generó y un aviso de que el fichero es generado y no debe editarse.

## Lista de comprobación de la entrega

Antes de exportar:

- [ ] Diseño firmado y sin cambios, y todas las unidades `approved` (`coursekit status PWD`).
- [ ] Todos los recursos multimedia `uploaded` y validados en la vista previa (ningún recurso de `media/manifest.yaml` está `pending`, `scripted` ni `produced`, y `coursekit media plan PWD` no muestra avisos: `plan` solo lista los recursos `pending` y `scripted`). Con el backend html: todos los recursos `produced` con su fichero, que `build` copia en el paquete.
- [ ] Todas las unidades montadas. Creator: `content_id` definido y `coursekit assemble diff` informa `unchanged` para el contenido y todas las lecciones. Html: `coursekit assemble build PWD` termina sin errores y has leído sus avisos. El estado del curso es `assembly` (o `client_review`, si abriste una ronda).
- [ ] Creator: enlaces de vista previa y de revisión de todas las unidades anotados (`units[].links`). Html: la vista previa abierta en un navegador (`courses/PWD/assembly/html/unit-01/index.html`) y comprobadas las lecciones, un componente de cada tipo y el test.
- [ ] Curso fuera de pausa, y `coursekit delivery check PWD` pasa.
- [ ] Revisión del cliente, si el proyecto la exige (`client_review.required`) o tú la quieres: la última ronda `approved` (`coursekit client PWD approve --by "..."`) o omitida con un motivo (`coursekit client PWD skip --reason "..."`).
- [ ] Versión decidida: `1.0` la primera vez y después `1.1`, `1.2`… según `course.yaml › deliveries`.
- [ ] Ajustes de exportación comprobados (`coursekit config delivery`).

Por cada unidad, con el backend creator:

- [ ] Instantánea del contenido llamada `v<versión>`.
- [ ] Exportación con los ajustes de `export` y espera a `COMPLETE` (con `FAILED`, detente y lee el error).
- [ ] Nombre de fichero obtenido con `coursekit delivery name`, descargado en `courses/PWD/delivery/`.
- [ ] `coursekit delivery add` (comprueba el zip y lo registra).

Por cada unidad, con el backend html:

- [ ] `coursekit assemble build PWD --unit N --version <versión>` (el zip se escribe en `courses/PWD/delivery/` con el nombre de `coursekit delivery name`).
- [ ] `coursekit delivery add` sin `--job` ni `--snapshot` (comprueba el zip y lo registra).

Al final:

- [ ] Estado del curso `delivered` (`coursekit status PWD`).
- [ ] Paquetes y catálogo en la carpeta espejo (`coursekit delivery add` los publica; `coursekit publish PWD` si en ese momento no tenías espejo).
- [ ] Al menos una unidad probada en el LMS de destino (o en SCORM Cloud). Con el backend html es imprescindible: coursekit no ha probado los paquetes en un LMS real.
- [ ] `course.yaml` con commit (los zip no se versionan); los commits solo se hacen cuando tú lo pides.

El agente hace los pasos de exportación (creator) o los de construcción y registro (html) con `/deliver PWD 1.0` o `coursekit run deliver PWD 1.0`.

## Ejemplo completo

Curso `PWD`, una unidad, cliente ACME, proveedor de carpeta espejo `folder`, backend creator:

```bash
coursekit assemble link PWD --unit 1 --content-id c-123
coursekit assemble plan PWD --unit 1
coursekit assemble diff PWD --unit 1        # contenido: rename; lecciones: create…
# el agente aplica las operaciones y registra cada lección:
coursekit assemble applied PWD --unit 1 --lesson U1-S1 --lesson-id l-1 --brick-ids a,b
coursekit assemble applied PWD --unit 1 --content
coursekit assemble diff PWD --unit 1        # hasta que todo esté "unchanged"
```

El agente anota los enlaces de la unidad:

```bash
coursekit assemble link PWD --unit 1 --preview https://acme.example.com/p/abc --review https://acme.example.com/r/xyz
```

El cliente revisa (opcional); tú abres y cierras la ronda, y el agente trata los comentarios:

```bash
coursekit client PWD send --to "equipo de formación de ACME"
# ronda 1 abierta; el curso pasa a client_review. Enlaces: ...
# /client-feedback PWD   (en el agente)
coursekit client PWD approve --by "responsable de formación de ACME"
# ronda 1 aprobada por responsable de formación de ACME: se puede entregar
```

Entrega la versión 1.0:

```bash
coursekit delivery check PWD
# PWD: se puede entregar
coursekit delivery name PWD --unit 1 --version 1.0
# PWD-U01-v1.0-scorm12.zip  (el agente lo exporta y lo descarga en courses/PWD/delivery/)
coursekit delivery add PWD --unit 1 --version 1.0 --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip \
  --job job-1 --snapshot snap-1
# registrado PWD-U01-v1.0-scorm12.zip · curso entregado
coursekit publish --check
# ok: carpeta espejo de folder en /ruta/a/MIRROR_DIR
# info: no hay mirror.url en project.yaml; el catálogo no tendrá enlaces a las carpetas
coursekit publish PWD
# escrito /ruta/al/proyecto/courses/catalogo-cursos.xlsx (1 cursos, 1 unidades)
# publicado PWD: 5 copiados, 0 eliminados, 0 sin cambios
# escrito /ruta/a/MIRROR_DIR/catalogo-cursos.xlsx (1 cursos, 1 unidades)
```

El mismo curso con el backend html (`assembly.backend: html`) se salta los enlaces, la carga y la exportación; el enlace de revisión es el del paquete que alojas:

```bash
coursekit assemble build PWD --unit 1
# unidad 1: 5 ficheros en courses/PWD/assembly/html/unit-01
# vista previa: abre courses/PWD/assembly/html/unit-01/index.html en el navegador
coursekit assemble build PWD --unit 1 --version 1.0
# paquete PWD-U01-v1.0-scorm12.zip (212.4 KB)
# (prueba el zip en el LMS de destino o en SCORM Cloud, y aloja el paquete para el cliente si hay revisión)
coursekit client PWD send --to "equipo de formación de ACME" --where https://lms.acme.example.com/courses/pwd
coursekit client PWD approve --by "responsable de formación de ACME"
coursekit delivery add PWD --unit 1 --version 1.0 --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip
# registrado PWD-U01-v1.0-scorm12.zip · curso entregado
```

Siguiente: [09-troubleshooting.md](09-troubleshooting.md)
