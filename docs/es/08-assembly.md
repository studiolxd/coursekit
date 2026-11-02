# Montaje

Cómo se monta un curso aprobado: se carga en la plataforma de montaje o coursekit lo construye como paquete web. La revisión del cliente está en [Revisión del cliente](10-client-review.md); la exportación de los paquetes SCORM, su registro, la carpeta compartida y el catálogo, en [Entrega y publicación](09-delivery.md).

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
| `html` | Construye cada unidad como una página web con su propio reproductor (`coursekit assemble build`) y la empaqueta por sí mismo como SCORM 1.2 o 2004. Mismas directivas y mismo formato que `creator` | Una carpeta `courses/PWD/assembly/html/unit-01/` que se abre en un navegador, y un zip en `delivery/` |

Cada backend rechaza los comandos del otro para un curso: `plan`, `diff`, `applied` y `link` fallan en un curso html (indican `build`), y `build` falla en un curso creator. `coursekit verify` convierte el contenido en ambos casos: con `html` informa además de las directivas que aún no están disponibles.

El diseño instruccional se hace en slxd (el agente de diseño guarda la matriz desde el servidor MCP de slxd) o en el proyecto (`design/design.yaml`, [`coursekit design`](03-commands.md#coursekit-design)), con cualquiera de los dos backends. El servidor MCP (`project.yaml › platform.slxd.mcp_url` y `mcp_name`, por defecto `slxd-creator`) hace falta con el backend creator o con un diseño hecho en slxd; con el backend html y un diseño local, nada pasa por slxd. El asistente de `coursekit init` pide la URL solo cuando hace falta. `coursekit agents` escribe el servidor en `.mcp.json`, `opencode.json` y `.codex/config.toml` (consulta [05-agents.md](05-agents.md)).

Las secciones [El flujo de montaje](#el-flujo-de-montaje) a [Registro de directivas](#registro-de-directivas-directives-check-y-sync-directives) describen el **backend creator**. El backend html tiene su propia sección, [El backend html](#el-backend-html). [Revisión del cliente](10-client-review.md#revisión-del-cliente) y [Entrega](09-delivery.md#entrega) valen para ambos, con las diferencias que se indican allí.

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
| 7. Comprobaciones | agente de montaje | Auditoría de accesibilidad, comparación del texto con el `.md`, una instantánea llamada `assembly-AAAA-MM-DD` y los dos enlaces de cada unidad (vista previa en vivo y revisión del cliente) guardados con `coursekit assemble link --preview URL --review URL`. Los enlaces (y una versión nueva de la revisión) se crean solo cuando no queda ningún recurso sin subir: con creator el primer montaje aún muestra recuadros, así que los enlaces esperan al montaje que sigue a la subida |

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
| `course.yaml › units[].links.review` | `assemble link --review` | Enlace de revisión de la unidad, donde comenta el cliente (mira [Revisión del cliente](10-client-review.md#revisión-del-cliente)) |
| `course.yaml › status` | `assemble applied` | Pasa de `media` a `assembly` por sí solo cuando todas las unidades están en creator exactamente como se planificó |

Los dos JSON se versionan con el curso: permiten que coursekit vuelva a cargar solo lo que cambia. No los edites a mano.

Los enlaces son **por unidad**, no por curso, porque cada unidad es un contenido propio en creator. No existe un bloque `links` a nivel de curso. Un comando que modifica el curso (incluido `assemble`) se niega mientras el curso está en pausa: antes, [`coursekit resume`](03-commands.md#coursekit-resume).

### Qué contiene el plan

El backend html construye sus páginas a partir de este mismo plan. Las claves de lección son `U<unidad>-S<apartado>` para las lecciones de contenido y `U<unidad>-E<N.M>` para las actividades de evaluación. El contenido se titula con el título del curso cuando tiene una sola unidad y, si no, `Unidad N. <título de la unidad>`. Las lecciones de evaluación llevan en el plan los ajustes de su test (mira [Calificación de un test](#calificación-de-un-test)).

| Markdown | Brick |
|---|---|
| Párrafos consecutivos | `TEXT` (fundidos en uno) |
| `###` a `######` | `HEADING` |
| Listas | `LIST` (con viñetas o numerada) |
| Tablas | `TABLE` |
| Bloques de código | `CODE` (el lenguaje si se conoce y, si no, automático) |
| Cita simple `> …` | `HIGHLIGHT` |
| Directiva `:::nombre` | El brick del registro (tabla en [06-content.md](06-content.md)) |
| Marcador de imagen con `Disposición: junto al texto`, seguido de un párrafo | `IMAGE_TEXT`: la imagen al lado de ese párrafo, con su pie |
| Una línea `> **[Vídeo]** <dirección> <pie>` de YouTube, Vimeo o un fichero de vídeo | `VIDEO` con `videoUrl` y su pie ([Vídeos de canales oficiales](06-content.md#vídeos-de-canales-oficiales)) |
| Dos o más marcadores de imagen seguidos, sin nada entre ellos | `IMAGE_GALLERY` (hasta cuatro) o `IMAGE_CAROUSEL` (más), cada imagen con su texto alternativo y su pie |
| Un marcador dentro de un panel de `:::accordion`, `:::tabs` o `:::carousel` | El medio de ese panel (`mediaType`, `imagePath` e `imageAlt`, o `videoPath`), o su imagen provisional; mientras no hay ninguno, una línea en su texto |
| Recurso visual sin subir, con su imagen provisional subida | `IMAGE` con la imagen provisional ([Imágenes provisionales](07-media.md#imágenes-provisionales)) |
| Recurso multimedia sin subir | `NOTE` titulada `Recurso multimedia — <tipo>: <título>` (las primeras palabras son las del idioma del curso, y el tipo se escribe como en el contenido, por ejemplo `Infografía`), con descripción y especificaciones |
| Recurso multimedia subido | Según el id del tipo: `image`, `infographic`, `diagram` y `animated_gif` pasan a `IMAGE`; `video` pasa a `VIDEO` (con subtítulos y transcripción si están registrados); `audio` pasa a `AUDIO`; `simulation` y `terminal_demo` pasan a `EMBED`; `job_aid` pasa a un `ATTACHMENT` (el PDF). Más un `ATTACHMENT` por cada descarga subida |
| Etiquetas de objetivo, `---`, comentarios HTML | No se publican |

Solo los subapartados **Instrucciones para el alumnado** y **Banco de preguntas** de una actividad de `assessment.md` pasan a su lección de evaluación.

`plan` imprime avisos para un `labelled-graphic` cuya imagen aún no está producida y para una lección sin contenido. Falla (y `verify` lo muestra como `ensamblado: …`) cuando una directiva es desconocida o no sigue su estructura: `single-choice` sin exactamente una opción correcta, `true-false` sin `respuesta: verdadero|falso`, `fill-in-the-blank` sin huecos escritos como `{respuesta}` en la línea `pregunta:`, una directiva de paneles sin paneles `#### Título`, un elemento de `pasapalabra` que no encaja con `- A (empieza): definición :: RESPUESTA`, una clave de la directiva escrita en el otro idioma, o un apartado que no está en el diseño.

Las claves de las líneas de las directivas (`pregunta:`, `respuesta:`, `respuestas:`, `feedback:`, `feedback-correcto:`, `feedback-incorrecto:`, `imagen:`, `posición:`, `título:` y la clave del objetivo) y las palabras que toman algunas (`verdadero`/`falso`; `empieza`/`contiene`) son las del idioma del curso. Un curso en inglés escribe `question:`, `answer: true`, `(starts)`, `(contains)`… Las tablas con las claves y las palabras de cada idioma están en [06-content.md](06-content.md#directivas). Una clave del otro idioma no se ignora: `plan` falla, y `verify` lo muestra como `ensamblado: …`, con el idioma al que pertenece la clave y las claves válidas:

```text
U1-S2: la clave 'question:' es del idioma «en»; en este curso se usan: feedback, feedback-correcto, feedback-incorrecto, imagen, objetivo, posición, pregunta, respuesta, respuestas, título
```

### Calificación de un test

Cada actividad de evaluación del diseño tiene su propia calificación en creator (`design_matrix_ae_create` y `design_matrix_ae_update`): su peso (`peso`), su nota de aprobado (`notaAprobado`, de 0 a 100) y sus intentos (`intentosMax`, `0` es sin límite). `coursekit sync` los lee en `course.yaml › units[].activities.assessment`, y el plan da el test de cada lección de evaluación:

| Campo del plan (`quiz`) | Del diseño | Cuando el diseño lo deja vacío |
|---|---|---|
| `passingGrade` | `notaAprobado` | `design.grading.passing_score` de `course.yaml` (por defecto `50`) |
| `maxAttempts` | `intentosMax` | `design.grading.attempts` (por defecto `2`; `0` es sin límite) |
| `courseWeight` | `peso` | `1` |

La actividad de una lección es la que tiene el mismo título en el diseño y, si no, la que ocupa la misma posición en la unidad (`U1-E1.2` es la segunda). Con el backend creator, el agente de montaje pasa los tres valores a `update_quiz_settings`. `courseWeight` es el peso del test entre los tests de la misma unidad, normalizado (60 y 40 pesan como 3 y 2), y `0` lo deja fuera de la nota. Cada unidad es su propio curso y su propio paquete, así que los pesos nunca comparan tests de unidades distintas: combinar unidades en una nota corresponde al LMS.

Un cambio solo en la calificación de un test (tras firmar de nuevo el diseño y ejecutar `plan`) aparece en `diff` como una operación `update_quiz` de esa lección, y el curso no vuelve a `assembly` hasta que se aplica. Con el backend html los tres valores se escriben en los ajustes de cada test, pero el paquete informa de una sola nota por unidad (la mejor de sus tests), así que el peso no la cambia.

### Dónde van las evaluaciones

Las evaluaciones se escriben en el `assessment.md` de su unidad, y ahí las ven la redacción, la revisión y `verify`. Dónde acaban se decide en el montaje y la entrega con `delivery › assessment` (un curso puede fijar lo suyo en `course.yaml › delivery › assessment`):

| `placement` | Qué se monta y se entrega |
|---|---|
| `unit` (por defecto) | Cada unidad lleva sus evaluaciones como lecciones de evaluación, y su paquete informa de su nota. |
| `separate` | Las unidades no llevan evaluaciones e informan del avance (`lessonProgress`), completadas o incompletas (`completed_incomplete`). Todas las evaluaciones del curso van en un paquete propio, una unidad más después de la última (`coursekit status` da su número), con el título del curso y «Evaluación» («Assessment» en inglés); informa de la nota (`quiz`). El plan de cada unidad lo dice en `score_source` (y `reporting: completed_incomplete` en una unidad sin evaluaciones), y el agente de entrega los pasa a la exportación de creator. Con el backend creator y un diseño hecho en slxd, lo crea el generador (`design_matrix_generate_course` con `leccionesEvaluacion: "separadas"`: un contenido «Evaluaciones — …» después de las unidades, con la calificación del curso) y el agente lo enlaza; con un diseño local se crea con `create_content`. Se registra en `course.yaml › assessment_unit`. |

| `format` | Las preguntas de las evaluaciones |
|---|---|
| `platform` (por defecto) | Lecciones de evaluación de los paquetes, en creator o en el paquete html. |
| `aiken`, `gift`, `moodle-xml`, `qti` | Un banco de preguntas que importa el LMS, registrado por `coursekit delivery questions` en `delivery/`. Con el backend creator (`gift`, `moodle-xml`, `qti`) las preguntas de todas las evaluaciones van en un contenido propio en creator, el contenido del banco (una unidad más después de las otras, que nunca se entrega como paquete, registrada en `course.yaml › bank_unit`), y creator exporta el banco (`create_export` con `deliveryType: question_bank`; `qti` es un zip IMS QTI 2.1); `delivery questions --url` lo guarda. Con html, o en `aiken`, `delivery questions` lo escribe a partir de los `assessment.md`. Las preguntas salen de los paquetes; una actividad con una simulación puntuable deja la simulación en su paquete (el de su unidad, o el de las evaluaciones con `separate`), y una actividad que solo tiene preguntas no tiene lección. Un paquete que se queda sin evaluaciones informa del avance, completado o incompleto (`score_source: lessonProgress` y `reporting: completed_incomplete` en su plan), diga lo que diga `export`. |

Cada formato de banco admite unos tipos de pregunta: `verify` rechaza los demás en `assessment.md` mientras se redacta la unidad, y `delivery questions` también los rechaza.

| Directiva | `aiken` | `gift` | `moodle-xml` | `qti` (creator) |
|---|---|---|---|---|
| `single-choice` | ✔ | ✔ | ✔ (`multichoice`, una respuesta) | ✔ |
| `multi-select` | ✘ | ✔ (cada respuesta correcta vale 100/n %, cada incorrecta resta) | ✔ (`multichoice`, varias respuestas) | ✔ |
| `true-false` | ✘ | ✔ | ✔ | ✔ |
| `match` | ✘ | ✔ | ✔ (`matching`) | ✔ |
| `sorting-groups` | ✘ | ✔ (como emparejamiento: cada elemento con su grupo) | ✔ (`matching`) | ✔ |
| `short-answer` | ✘ | ✔ | ✔ | ✔ |
| `fill-in-the-blank` | ✘ | ✔ (un hueco por pregunta) | ✔ (`cloze`, varios huecos) | ✔ |
| `sorting`, `order-words` | ✘ | ✘ | `sorting` ✔ (tipo `ordering` del núcleo, Moodle 4.4 o posterior), `order-words` ✘ | `sorting` ✔, `order-words` ✘ |

La tabla es lo que exige coursekit; la exportación de creator puede dejar fuera algo más (las imágenes en GIFT, un tipo que un formato no puede llevar) y lo lista en los `warnings` de `get_export_status`, que el agente de entrega enseña. Qué conserva cada fichero que escribe coursekit: el texto de la pregunta, sus opciones, las respuestas correctas y la retroalimentación (de acierto, de error y general; Aiken no tiene retroalimentación), con el HTML de los textos (texto plano en Aiken). Cada pregunta se llama como su actividad y su posición, con su objetivo (`U1-E1.1-q3 · U1.2`). El id del error común que representa un distractor nunca se escribe. Moodle XML indica si se barajan las opciones de cada pregunta (`shuffleanswers`, según `delivery › shuffle_options › assessment` o el `barajar:` de la pregunta; un emparejamiento, siempre); GIFT y Aiken no pueden, y decide el cuestionario de Moodle. GIFT y Moodle XML ponen cada actividad en su propia categoría (`<CODE>/U1 E1.1 <título>`); Aiken no tiene categorías, así que es un fichero por actividad. La nota para aprobar, los intentos y los pesos no forman parte de estos formatos: se fijan en el cuestionario del LMS.

### Simulaciones en creator

Creator no tiene un bloque para una simulación ni comparte estado entre bloques, así que en su plan:

- Una **simulación** es un `EMBED` de su propio paquete: `coursekit media extract` añade el recurso `SIM-<ID>` (kind `package`), `coursekit media embed <CODE> SIM-<ID>` construye `media/src/SIM-<ID>/` (`index.html` con el reproductor de las simulaciones, las pieles, los estilos y el theme, y las imágenes producidas en `media/`, además del manifiesto de creator `slxd-embed.json`), y el agente de multimedia sube esa carpeta con `request_embed_upload` y la registra (`media set … --status uploaded --asset-path <embedFolderPrefix>`). Mientras, una nota ocupa su lugar y `plan` avisa. La simulación se juega dentro del embed, y creator guarda su estado, cuenta su nota y registra sus decisiones (abajo).
- El paquete habla el protocolo `slxd-embed` de creator (versión 1) y declara `complete`, `resize`, `state`, `result` e `interaction` en `slxd-embed.json` (creator lo lee al escribir la carpeta en el bloque y muestra lo que ha entendido en `properties.embedPackage`; un SVG envuelto declara solo `resize`):
  - al cargar dice `ready` y creator le devuelve el último estado que guardó, así que el alumno la encuentra donde la dejó (en la exportación SCORM, entre sesiones; en las vistas previas, durante la sesión);
  - después de cada paso manda su estado (escena, variables, puntos, intento, decisiones; muy por debajo de los 1.024 caracteres que guarda creator) y, tras cada decisión, una `interaction` (`<simulationId>-<intento>-<n>` en `cmi.interactions`, la letra de la opción, su texto como descripción, correcta, incorrecta o neutral, sus puntos como peso);
  - al llegar a un final manda su `result` (puntos, máximo, nota de 0 a 100, final y su tipo), después su estado con `done` y `complete`: creator cierra la simulación con esa nota y completa el bloque;
  - cuando la prueba abre un intento nuevo, creator manda `reset` y la simulación vuelve a empezar (otro intento para las interacciones); el alto de su contenido va en `resize`, que el iframe toma sin barra de desplazamiento propia.
- El EMBED lleva `simulationId` (el id de la simulación), `scored` y `weight`. Una simulación evaluable en una prueba cuenta con la fórmula del backend html (`100 × (preguntas acertadas + Σ peso · nota / 100) / (preguntas + Σ pesos)`, donde creator pondera cada pregunta con su propio peso); una prueba formada solo por simulaciones se califica sola cuando termina la última; en un contenido sin pruebas, sus simulaciones evaluables dan la nota del contenido. Las simulaciones evaluables fuera de las pruebas de un contenido que las tiene no cuentan (`verify` avisa).
- En un curso basado en decisiones, el EMBED de la simulación que abre cada apartado de contenido lleva `blocker_enabled`: la lección no deja seguir al alumno hasta que la simulación llega a un final, para que decida antes de leer la explicación. Las demás simulaciones (una segunda en el apartado, las de las pruebas) no bloquean.
- Un **bloque adaptativo** se monta con su rama neutra (`:::else`), y `plan` avisa.

El bloque adaptativo es la fase siguiente del protocolo de creator (ver [Límites conocidos del backend creator](#límites-conocidos-del-backend-creator)).

### `diff`

Por cada lección, `diff` da una acción y sus operaciones; el `data` de cada operación es la carga útil para la herramienta de creator:

| Acción | Significado |
|---|---|
| `create` | La lección no está en `applied.json`: una operación `add` por brick |
| `update` | Operaciones `update`, `delete`, `add` (con `position`) `rename_lesson` y `update_quiz` (cambió la calificación de un test), calculadas a partir de las huellas de los bricks y de los ajustes del test |
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

Sin `--version` la última línea es `vista previa: coursekit preview PWD (con LMS simulado), o abre courses/PWD/assembly/html/unit-01/index.html en el navegador` (ver [Vista previa con LMS simulado](#vista-previa-con-lms-simulado)). Los avisos se imprimen antes (`AVISO …`): un `labelled-graphic` cuya imagen aún no está producida y un recurso producido cuyo fichero no existe.

Cada construcción empieza de cero: la carpeta de la unidad se borra y se escribe de nuevo. El estándar (SCORM 1.2 o 2004 4.ª edición) es `export.standard` de la configuración de entrega ([Ajustes de exportación SCORM](09-delivery.md#ajustes-de-exportación-scorm)). El comando falla, con código de salida 1 y la lista de problemas, cuando:

- el plan tiene errores (una directiva desconocida, una pregunta sin su opción correcta, una clave escrita en el otro idioma…: los mismos mensajes que `verify`);
- la unidad usa una directiva del registro del proyecto que el backend no sabe dibujar;
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
| Párrafos, `###`–`######`, listas, tablas, bloques de código | `TEXT`, `HEADING`, `LIST`, `TABLE`, `CODE` | Texto, títulos (nivel 3 a 6; el título de la lección es el nivel 2), listas, tablas en una caja con desplazamiento, bloques de código. Todo bloque indica su lenguaje, nunca la detección automática de creator: el lenguaje de la valla o su alias si creator lo tiene (`bash`, `python`, `yaml`, `powershell`, `diff`…); `shell` («Terminal») para un bloque `text` o sin lenguaje que es una sesión de terminal o solo órdenes, y para `console`, `terminal` y `cmd`; `plaintext` para cualquier otro texto y para un lenguaje que creator no tiene (consulta `rules › assembly › code_languages` en [Configuración](04-configuration.md)) |
| `note`, `highlight`, cita en bloque simple, `quote` | `NOTE`, `HIGHLIGHT`, `QUOTE` | Una nota con título, un bloque destacado, una cita con su autoría |
| `accordion` | `ACCORDION` | Elementos `details` nativos (funcionan sin JavaScript) |
| `tabs` | `TABS` | Lista de pestañas con las teclas de flecha, Inicio y Fin; todos los paneles están en el marcado |
| `carousel`, `carousel-quotes` | `CAROUSEL`, `CAROUSEL_QUOTES` | Una diapositiva cada vez con botones de anterior y siguiente y un estado «Diapositiva n de N» |
| `timeline` | `TIMELINE` | Lista ordenada con la fecha y el título de cada hito |
| `flashcards`, `flashcard-gallery` | `FLASHCARD_CAROUSEL`, `FLASHCARD_GALLERY` | Tarjetas que se giran (clic, Intro o Espacio), una a una o en cuadrícula |
| `labelled-graphic` | `LABELLED_GRAPHIC` | La imagen con puntos numerados que abren su explicación (Escape o Cerrar para descartarla). Sin imagen producida: una lista simple de los puntos |
| `dialog` | `DIALOG` | Las intervenciones de la conversación con el nombre de cada interlocutor |
| `scenario`, `conversation` | `SIMULATION` | La simulación jugada escena a escena: el fondo con sus capas y las zonas que se pueden pulsar (botones enfocables con la etiqueta como nombre), los retratos de los personajes, el texto con las variantes que se cumplen, las opciones como botones, el feedback de una decisión antes de seguir y, al final, el final, el debriefing, las decisiones tomadas, la puntuación (las evaluables) y los botones para volver al último punto de control (`decision_based.rewind`) y empezar de nuevo. Con una `skin`, la aplicación ([Pieles](06-content.md#pieles)) ocupa el lugar del fondo. Una `conversation` muestra el intercambio como un chat. Sin JavaScript: la situación inicial y sus opciones. Las imágenes aún sin producir se omiten (los retratos se sustituyen por iniciales) |
| `:::if` / `:::else` | `CONDITIONAL` | Las dos ramas están en la página; el reproductor muestra la de `:::if` cuando todas las simulaciones que lee se han jugado y su condición se cumple, y si no la neutra (también sin JavaScript) |
| Marcador de imagen, infografía, esquema o GIF animado (producido) | `IMAGE` | Figura con texto alternativo y pie |
| Imagen junto a su texto, imágenes seguidas | `IMAGE_TEXT`, `IMAGE_GALLERY`, `IMAGE_CAROUSEL` | La imagen al lado del párrafo (una encima de otro en una pantalla estrecha); una rejilla de figuras; un carrusel de figuras |
| Recurso visual aún sin producir | `IMAGE` | Su imagen provisional, dibujada con el tema ([Imágenes provisionales](07-media.md#imágenes-provisionales)) |
| Marcador de vídeo (producido) | `VIDEO` | Vídeo con controles, pista de subtítulos (si hay un `.vtt`) y la transcripción en un `details` |
| Marcador de audio (producido) | `AUDIO` | Audio con controles y la transcripción |
| Marcador de simulación y de demo de terminal (producido) | `EMBED` | Un `iframe` de la carpeta del paquete (`media/<id>/index.html`) |
| Descarga de un recurso, ayuda de trabajo | `ATTACHMENT` | Un enlace de descarga |
| `single-choice`, `multi-select`, `true-false` | `SINGLE_CHOICE`, `MULTI_SELECT`, `TRUE_FALSE` | Botones de opción o casillas, en otro orden en cada intento cuando el plan las baraja (`delivery › shuffle_options`); verdadero-falso ofrece Verdadero y Falso |
| `sorting` | `SORTING` | Los elementos desordenados, con botones para subir y bajar |
| `match` | `MATCH` | Una lista desplegable por término de la izquierda, con los términos de la derecha desordenados |
| `sorting-groups` | `SORTING_GROUPS` | Una lista desplegable por elemento con las categorías; los elementos desordenados cuando el plan lo dice |
| `fill-in-the-blank` | `FILL_IN_THE_BLANK` | Un cuadro de texto en cada hueco de la frase (`{a/b}` admite varias respuestas) |
| `order-words` | `ORDER_WORDS` | Botones con palabras que se pulsan para colocarlas en la frase por orden, una línea por frase |
| `short-answer` | `SHORT_ANSWER` | Un cuadro de texto que se compara con las respuestas admitidas |

Las respuestas de texto (`fill-in-the-blank`, `short-answer`) se comparan sin tener en cuenta mayúsculas, tildes ni espacios sobrantes. Una pregunta de selección múltiple es correcta solo cuando cada opción está como dice la clave. La retroalimentación sigue a la directiva: `feedback-correcto:` tras una respuesta correcta, `feedback-incorrecto:` tras una incorrecta y `feedback:` siempre. Las directivas se explican en [06-content.md](06-content.md#directivas); los juegos están más abajo, en [Juegos](#juegos).

### El reproductor

Con JavaScript la página se convierte en un pequeño reproductor de curso:

- Se muestra una lección cada vez. La lista de lecciones (la navegación «Lecciones») marca la lección actual y las visitadas; **Anterior** y **Siguiente** mueven entre ellas; la barra de progreso muestra el porcentaje de lecciones visitadas; un enlace para **saltar al contenido** es el primer elemento de la página. Al cambiar de lección la página vuelve arriba y el foco pasa al título de la lección.
- La unidad se reabre en la lección donde la dejó la persona.
- Las **preguntas de práctica** (en las lecciones de contenido) tienen un botón **Comprobar**. No hace nada hasta que la pregunta está contestada; entonces bloquea las respuestas, las marca y muestra la retroalimentación, y el botón pasa a **Reintentar**, que borra la respuesta y vuelve a desordenar.
- **Las lecciones de evaluación** (`assessment.md`) se corrigen juntas con un solo botón **Enviar respuestas**. Las preguntas sin contestar impiden el envío («Responde todas las preguntas antes de enviar.»). La puntuación es el porcentaje de preguntas totalmente correctas, redondeado; se aprueba cuando llega a la nota de aprobado del test (mira [Calificación de un test](#calificación-de-un-test)). Los intentos del test los limitan (vacío o 0: sin límite). Tras enviar, cada pregunta muestra su marca y su retroalimentación, y el informe indica la puntuación y si se ha aprobado; si no, aparece **Reintentar** mientras queden intentos (el informe dice cuántos) y «No quedan intentos.» cuando no queda ninguno. Los intentos usados y la mejor puntuación se guardan en los datos de suspensión, de modo que reabrir la unidad no da intentos nuevos.
- **Las simulaciones** conservan su estado (la escena, las variables, los puntos y si han terminado) al cambiar de lección y al volver a abrir la unidad, y cada decisión actualiza los bloques adaptativos de la unidad. Una simulación **evaluable** dentro de una lección de evaluación cuenta en su prueba: pesa `weight` preguntas y suma su nota (los puntos de su camino sobre el máximo alcanzable); la prueba no se puede enviar hasta que esas simulaciones han terminado, y **Reintentar** también las reinicia. Una prueba formada solo por simulaciones evaluables no tiene botón **Enviar respuestas**: se califica sola cuando todas llegan a un final, y volver a empezarlas abre un intento nuevo mientras queden intentos (después se pueden jugar, sin nota). En una unidad sin prueba, la puntuación es la nota ponderada de sus simulaciones evaluables cuando todas han terminado; en una unidad con prueba, las simulaciones evaluables del contenido son de práctica.
- **La simulación que abre un apartado** de un curso basado en decisiones retiene el resto de la lección hasta llegar a un final: lo que la sigue queda oculto, con una línea que lo dice, y **Siguiente** se desactiva. El alumno decide antes de leer la explicación, como en creator, donde su EMBED bloquea la lección. Quien vuelve a una simulación ya terminada encuentra la lección abierta.
- Los textos de la interfaz (etiquetas de botones y mensajes) están en el idioma del curso.
- La página es adaptable (la lista de lecciones es una columna lateral en pantallas anchas), respeta el movimiento reducido y los colores forzados, y se imprime con todas las lecciones.

### Juegos

Los juegos son práctica: no se califican ni se mandan al LMS. Funcionan con teclado y con lector de pantalla (lo que
pasa se dice en una región en vivo bajo el juego), y el orden de letras y cartas depende solo del id del juego, así que
todos ven el mismo tablero. Sin JavaScript la página lista de qué trata cada juego.

| Directiva | En el reproductor |
|---|---|
| `word-search` | Una cuadrícula con las palabras en horizontal, vertical o diagonal: se pulsa la primera letra de una palabra y después la última; las flechas mueven por la cuadrícula; las palabras encontradas se tachan |
| `wordle` | Una palabra detrás de otra: seis intentos; cada letra dice si está en su sitio, en otra posición o no está (con color y con palabras) |
| `hangman` | Una palabra detrás de otra: una tecla por letra (con la Ñ); seis fallos como mucho |
| `pasapalabra` | Las letras del rosco; para cada una, su definición («Empieza por» o «Contiene la»), un campo de respuesta y **Pasapalabra**; valen las alternativas con `/`, y no cuentan tildes ni mayúsculas |
| `memory` | Cada línea es una pareja de cartas; se destapan de dos en dos; cuenta parejas y jugadas |
| `trivial` | El alumno elige una categoría y responde una de sus preguntas; una categoría se gana con un acierto |

### Seguimiento SCORM

El runtime es `@studiolxd/scorm`, empaquetado en `assets/player.js`.

| Qué | Cómo se informa |
|---|---|
| Ubicación | La clave de la lección actual (`U1-S2`, `U1-E1.1`); la unidad se reabre ahí |
| Datos de suspensión | Las lecciones visitadas, los intentos usados, la mejor puntuación, el número de interacciones registradas y, de cada simulación, su escena, variables, puntos, si ha terminado, su intento y cuántas decisiones lleva (nada más, para no pasar de los 4.096 caracteres de SCORM 1.2) |
| Progreso | Lecciones visitadas dividido entre las lecciones de la unidad (medida de progreso, SCORM 2004) |
| Finalización | Sin test: completada cuando se han visitado todas las lecciones, incompleta hasta entonces. Con test, en SCORM 2004: completada cuando se han visitado todas las lecciones, y aprobada o suspensa cuando se envía el test. Con test, en SCORM 1.2, que tiene un único estado: aprobada o suspensa cuando se envía el test |
| Puntuación | Bruta (porcentaje), mínimo 0 y máximo 100; en SCORM 2004 también la escalada |
| Interacciones | Una por pregunta del test: su id, el tipo (choice para la opción simple y múltiple, fill-in para el resto), la respuesta (en una choice, las letras de las opciones elegidas: `a,c` en SCORM 1.2, `a[,]c` en 2004; en el resto, la respuesta de la persona cortada a 250 caracteres), correcta o incorrecta (`wrong` en 1.2, `incorrect` en 2004), peso 1. Y una por decisión en una simulación: `<simulación>-<intento>-<n>` (cada vez que empieza de nuevo es otro intento, así que los ids no se repiten), choice, la letra de la decisión entre las de su escena (`a`, `b`…), su texto como descripción (solo SCORM 2004: 1.2 no tiene descripción), correcta si sumó puntos, incorrecta si los restó y neutral si no, con sus puntos como peso. Todos los valores son de los que admite el estándar: un LMS estricto rechaza el resto y se pierden |
| Sesión | Tiempo de sesión y salida `suspend`; los datos se confirman tras cada cambio y la sesión se termina cuando la página se oculta o se cierra |

### Vista previa con LMS simulado

La carpeta de una unidad se abre desde el disco, pero entonces el paquete no tiene LMS: su seguimiento se queda en
memoria y se pierde al cerrar. [`coursekit preview`](03-commands.md#coursekit-preview) la juega como lo haría una
plataforma:

```bash
coursekit preview PWD            # abre http://127.0.0.1:8765/ en el navegador
```

- Un servidor local muestra una página que tiene las API de SCORM 1.2 y 2004, con la unidad dentro: el paquete
  encuentra su LMS y manda lo que mandaría en una plataforma. Nada sale de la máquina. El LMS simulado es tan estricto
  como una plataforma: un valor que el estándar no admite (un resultado, una respuesta, una nota fuera de rango, un
  estado guardado demasiado largo) se rechaza con su código de error y sale en rojo en el panel, en **Valores que un
  LMS rechazaría**.
- Lo que manda la unidad se guarda en el navegador, por curso y unidad: **Salir y volver a entrar** cierra la sesión
  (salida y cierre) y la abre otra vez, para ver si sigue donde estaba (`entry: resume`, la ubicación, el estado de
  cada simulación). **Borrar el seguimiento** empieza la unidad de cero.
- Un panel lateral muestra el seguimiento en vivo: finalización, superación, nota, ubicación, entrada y salida; el
  estado guardado (`suspend_data`) con su tamaño frente al límite del estándar (4.096 caracteres en SCORM 1.2); cada
  interacción (id, respuesta, resultado y peso: una por pregunta de una prueba y una por decisión de una simulación); y
  las llamadas a la API.
- Cuando una unidad se vuelve a construir (`coursekit assemble build` en otro terminal), se vuelve a abrir sola.
- Un selector cambia de unidad. Una unidad sin construir muestra el comando que la construye.

Es una comprobación del paquete, no sustituye a probarlo en la plataforma real (SCORM Cloud o el LMS del cliente)
antes de entregar.

### Comprobar el paquete

Antes de entregar, [`coursekit assemble check`](03-commands.md#coursekit-assemble) juega cada unidad como lo haría el
alumno, y `coursekit assemble build --version` lo hace por sí solo antes de escribir el zip (`--no-check` lo salta):

```bash
coursekit assemble check PWD            # todas las unidades
coursekit assemble check PWD --unit 2
```

| Qué comprueba | Es un error cuando |
|---|---|
| Ficheros | La página o sus estilos apuntan a un fichero que no está en el paquete |
| Consola y carga | El reproductor escribe un error en la consola, o un fichero no carga |
| Accesibilidad | axe encuentra una infracción `critical` o `serious` en una lección (`moderate` y `minor` son avisos); un problema de contraste muestra su relación y sus colores |
| Pruebas | Respondida bien, tras el mejor camino de sus simulaciones evaluables, una prueba no manda la nota que debe |
| Nota de la unidad | En una unidad sin prueba, sus simulaciones evaluables (por su mejor camino) no dan la nota que deben |
| Simulaciones | Un camino de [`coursekit paths`](03-commands.md#coursekit-paths) no se puede jugar, o acaba en otra escena o con otros puntos |
| Bloques adaptativos | Tras un camino, un bloque `:::if` muestra otra rama que la que pide su condición |
| SCORM | El LMS rechazaría un valor; el estado guardado no cabe en el estándar (aviso desde el 80 %) |
| Reanudar | Al salir y volver a entrar, la unidad no está donde estaba |

Necesita Node y un navegador: el Google Chrome instalado o, si no, Microsoft Edge (`--browser RUTA` para otro), manejado
sin ventana por Playwright. La primera vez prepara el verificador en el almacén (`npm install` de `playwright-core` y
`axe-core`; no se descarga ningún navegador). Sin navegador solo se comprueban los ficheros, con un aviso. Una unidad con
muchos caminos tarda unos segundos: se juegan todos los caminos de todas las simulaciones.

### Estilos

`assets/styles.css` se construye por capas, cada una sobre la anterior:

1. **El layout base** del paquete: neutro, accesible, gobernado por variables CSS (`--color-background`, `--color-text`, `--color-accent`, `--color-surface`, `--color-border`, `--color-correct`, `--color-wrong`, `--font-family`, `--font-size-base`, `--radius`, `--space-*`…). Sus clases empiezan por `ck-`.
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

La construcción compara las palabras de `content.md` y `assessment.md` que lee la persona con las palabras de la página. De `assessment.md` solo cuenta el texto bajo **Instrucciones para el alumnado** y **Banco de preguntas**, porque solo eso llega al paquete (los demás subapartados documentan la actividad para el equipo). Deja fuera lo que no es texto para la persona: la sintaxis del formato (las líneas `:::`, las claves `pregunta:` y `respuesta:`, las viñetas), los metadatos (las etiquetas de objetivo, la clave de objetivo, los comentarios, `imagen:` y `posición:`), los marcadores multimedia (su caja se sustituye por el recurso o por su nota) y los destinos de los enlaces. Si falta alguna palabra, la construcción falla con `el paquete no contiene N palabra(s) del contenido: …` y las veinte primeras palabras.

La causa típica es una línea que el formato no renderiza, por ejemplo una pregunta sin su clave `pregunta:` (escrita como una línea normal dentro de la directiva). Corrígela en el `.md` y vuelve a construir. La comparación es por conjuntos de palabras, así que no depende de cómo disponga el texto un componente.

### Límites

- **No se ha probado en un LMS real.** Prueba el paquete en el LMS de destino (o en SCORM Cloud) antes de entregarlo: comprueba que se reanuda la ubicación, que se registran la puntuación y el estado, y que el test se comporta como esperas.
- El paquete es un SCO por unidad. Un curso de varias unidades da varios paquetes.
- `export.reporting` y `export.scoreSource` no se aplican: el estado y la puntuación son los de [Seguimiento SCORM](#seguimiento-scorm).

## Límites conocidos del backend creator

Son huecos de la plataforma de autoría, no de coursekit. El pipeline los esquiva o avisa en lugar de fallar, y cada uno desaparece cuando creator lo cierra. La lista se mantiene al día con cada versión de coursekit; la vista previa del curso montado es donde comprobar si uno sigue vigente.

- **Theme.** Creator no publica por MCP qué campos del theme admite cada bloque, su tipo, su valor por defecto ni qué pintan, y `update_theme` no dice qué campos descartó ni por qué. Tras importar un theme, mira el resultado en creator.
- **Embeds en la vista compartida.** Un EMBED (una simulación, una demo de terminal) puede verse en blanco en la vista compartida de un contenido, porque la plataforma se niega a enmarcarlo (`X-Frame-Options: DENY`). En la vista del alumno y en el paquete exportado funciona.
- **Campos de una línea.** Las opciones de una pregunta (`single-choice`, `multi-select`, `sorting`, `order-words`, los dos lados de un `match`, los elementos y grupos de un `sorting-groups`), las líneas de un `dialog` y los títulos de paneles, diapositivas, puntos calientes y eventos de una línea de tiempo admiten un párrafo con negrita, cursiva, subíndice y superíndice solamente. El plan los envía sin código en línea, enlaces ni saltos de línea (su texto se queda) y la pregunta sin enlaces, para que creator los acepte; `assemble plan` y `verify` avisan de cada campo cambiado.
- **Bloque de código.** Las líneas largas se cortan (coursekit nunca deja un bloque a su detección automática: siempre envía un lenguaje de su lista, consulta `assembly.code_languages` en [Configuración](04-configuration.md)). Tampoco tratan bien el código en línea, los bloques de código dentro de pestañas o desplegables ni los textos alternativos largos.
- **Flashcards.** Algunos campos del theme dejan en blanco la cara frontal, y la etiqueta «Voltear» se ve bajo la tarjeta.
- **Fuentes del theme.** Una fuente del theme puede no cargar en el reproductor (CORS).
- **Bloques adaptativos (`:::if`).** Creator tiene el brick `CONDITIONAL`, pero coursekit sigue montando la rama neutra (`:::else`) y `plan` avisa, hasta que el reproductor del alumno muestre las ramas. Las simulaciones sí informan de su estado, su nota y cada decisión al SCORM del contenido (el protocolo `slxd-embed`, ver [Simulaciones en creator](#simulaciones-en-creator)).

Siguiente: [Entrega y publicación](09-delivery.md)
