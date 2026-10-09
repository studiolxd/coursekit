# Configuración

Dónde vive cada ajuste de un proyecto coursekit, en qué orden se combinan y cómo ver y cambiar el valor vigente.

Los ejemplos usan un proyecto genérico: cliente «ACME», un curso sobre contraseñas seguras con código `PWD`.

## Dónde vive cada valor

| Lugar | Se versiona | Quién lo edita | Qué contiene |
|---|---|---|---|
| Valores por defecto del paquete (dentro de coursekit) | no (viene con la herramienta) | nadie | Las reglas de producción, directivas, opciones de multimedia y ajustes de entrega por defecto, y la herramienta y el modelo por defecto de cada rol. |
| `config/<nombre>.yaml` | sí | el equipo | Cambios sobre una de las cuatro configuraciones: `rules`, `directives`, `media`, `delivery`. |
| `project.yaml` | sí | el equipo | Identidad del proyecto, idiomas, backend de montaje, servidor slxd, carpeta espejo, red. También puede llevar secciones `rules:`, `directives:`, `media:` y `delivery:`. |
| `course.yaml` | sí | los comandos y las personas | El registro de un curso. Puede llevar secciones `rules:`, `directives:`, `media:` y `delivery:` que se aplican solo a ese curso. |
| `theme/` y `courses/<CODE>/theme/` | sí | `coursekit theme import` (tokens); el equipo (`maqueta.css`) | Tokens de diseño del tema, derivados del tema de la plataforma de montaje o, con el backend html, de la hoja de estilos (mira [Tokens del tema y carpetas de caché](#tokens-del-tema-y-carpetas-de-caché)). No es una capa de configuración: nadie edita los tokens a mano. Con el backend html, `maqueta.css` es la hoja de estilos que da otro aspecto al paquete y se edita a mano (mira [Ficheros del backend html](#ficheros-del-backend-html)). |
| Almacén de la máquina (fuera de todo proyecto) | no | `coursekit setup` y `coursekit uninstall` | Dependencias de Node compartidas por los proyectos y el registro de lo que instaló `coursekit setup` (mira [El almacén de la máquina](#el-almacén-de-la-máquina)). No es una capa de configuración. |
| `.env` (y el entorno real) | no (ignorado por git) | cada persona | Datos personales: identidad de firma, idioma de la interfaz, rutas locales, herramienta y modelo de cada rol, claves de API. |
| Opciones de un comando | no | quien lo ejecuta | `--agent` y `--model` para un solo lanzamiento. |

Regla práctica: lo que debe ser igual para todo el equipo va en ficheros versionados (`project.yaml`, `config/`); lo personal o secreto va en `.env`. Las reglas de producción nunca se leen de `.env`.

## Cómo se combinan los valores

### Las cuatro configuraciones de producción

`rules`, `directives`, `media` y `delivery` se construyen fusionando, en este orden (gana la última):

1. Valores por defecto del paquete.
2. `config/<name>.yaml`, si existe.
3. La sección `<name>:` de `project.yaml`, si existe.
4. La sección `<name>:` del `course.yaml` del curso, cuando hay un curso de por medio.

Reglas de la fusión:

- Un mapa se fusiona clave a clave: escribes solo las claves que cambias.
- Cualquier otro valor sustituye al anterior. **Las listas se sustituyen enteras**, no se les añade: para cambiar un elemento de una lista tienes que escribir la lista completa.
- Dar un valor nuevo a una clave nunca elimina las claves hermanas.

### Ajustes personales

- Una variable ya definida en el entorno real (tu terminal) gana a la misma variable de `.env`. Un valor vacío en `.env` cuenta como no definido.
- `--agent` y `--model` en un comando ganan a `<ROLE>_AGENT` y `<ROLE>_MODEL` solo en ese lanzamiento. `--agent` sin `--model` usa el modelo por defecto de esa herramienta (no reutiliza el de `.env`).

### Idioma de la interfaz

`coursekit` elige el idioma de sus mensajes (`es` o `en`) en este orden:

1. El idioma elegido en el asistente de `coursekit init`, durante esa ejecución.
2. `COURSEKIT_LANG` (entorno real o `.env`).
3. `ui_language` de `project.yaml` (si falta, `content_language`).
4. El idioma del sistema (`LC_ALL`, `LC_MESSAGES`, `LANG`).
5. Inglés.

Todos los textos, `--help` incluido, siguen `COURSEKIT_LANG` (la variable de la terminal o la del `.env` del proyecto en el que estás), si no `ui_language`, y si no el idioma del sistema.

## Ver el valor vigente

```bash
coursekit config                     # las cuatro configuraciones, cada valor con su origen
coursekit config rules               # solo una: rules | directives | media | delivery
coursekit config rules --changed     # solo lo que difiere de los valores por defecto del paquete
coursekit config rules --course PWD  # incluye los cambios de courses/PWD/course.yaml
coursekit config delivery --json     # valores fusionados en JSON
coursekit rules                      # atajo de `coursekit config rules`
coursekit rules PWD --changed        # atajo con un curso y --changed
```

Cada línea es `clave  valor  (origen)`, donde el origen es la capa que fijó el valor: `package`, `config` (`config/<name>.yaml`), `project` (una sección de `project.yaml`) o `course`. Las claves anidadas se muestran con puntos, por ejemplo `defaults.grading.passing_score`.

Las skills y los comandos reciben las reglas como números que se renderizan cuando se ejecuta `coursekit agents`, con los valores a nivel de proyecto (paquete, `config/`, `project.yaml`). Tras cambiar una regla, ejecuta `coursekit agents` (también se ejecuta con `coursekit setup` y tras cada `git pull` o cambio de rama mediante los git hooks del proyecto, una vez que `coursekit setup` los ha activado). Los cambios a nivel de curso se aplican en las comprobaciones (`coursekit verify`, `coursekit sync`), pero no se escriben en los textos de las skills.

## `project.yaml`

Lo crea `coursekit init` y desde entonces es del proyecto: `coursekit init --update` nunca lo reescribe. Edítalo a mano.

| Clave | Por defecto | Valores permitidos | Significado |
|---|---|---|---|
| `name` | nombre de la carpeta | texto libre | Nombre del proyecto. Se muestra a los agentes como nombre del equipo. |
| `client` | vacío | texto libre | Nombre del cliente (por ejemplo `ACME`). Se copia al `course.yaml` de cada curso nuevo. |
| `content_language` | `es` | `es`, `en` | Idioma del contenido de los cursos. Selecciona los tokens del formato de contenido (palabra del encabezado de apartado, etiqueta de objetivo, etiqueta de recurso multimedia), el `language` por defecto de los cursos nuevos y las voces de locución por defecto. Un curso puede ser distinto: `coursekit new --language`. |
| `ui_language` | igual que `content_language` | `es`, `en` | Idioma de los mensajes de coursekit, de la hoja de cálculo del catálogo y de lo que los agentes dicen a las personas. Cada persona puede cambiar los mensajes con `COURSEKIT_LANG`. |
| `tone` | vacío | texto libre | Tono de los cursos (por ejemplo «cercano y práctico»). Se copia a `design.tone` de los cursos nuevos. Si está vacío, se indica a los agentes que usen el tono del `course.yaml`. |
| `address` | `tu` en `es`, `you` en `en` | `tu`, `usted` (español); `you` (inglés) | Cómo se trata a los alumnos. Se da a los agentes como regla de redacción. `coursekit init` rechaza un valor que no encaje con el idioma. |
| `assembly.backend` | `creator` | `creator`, `html` | Dónde se montan los cursos. Con `creator` las unidades se cargan en slxd creator (`coursekit assemble plan`, `diff`, `applied`, `link`) y `coursekit verify` comprueba además que el contenido se pueda convertir en bricks de creator. Con `html` coursekit construye cada unidad como un paquete SCORM (`coursekit assemble build`) y `coursekit verify` comprueba además que se pueda dibujar cada componente. El diseño instruccional siempre se hace en creator, así que `platform.slxd.mcp_url` hace falta con cualquiera de los dos backends. Un curso puede usar el otro backend: `assembly.backend` en su `course.yaml` (ver más abajo). `coursekit init --backend` lo fija. |
| `theme.source` | `tenant_default` | `tenant_default`, `branding` | Solo con el backend creator: de dónde sale el theme de los cursos. `tenant_default` usa el theme por defecto de la organización en creator; `branding` hace que `/define-theme` cree uno con el material de `theme/branding/` (sin material, se usa el del tenant). Con el backend html no se usa. El handoff lo lee para no tener que preguntar. |
| `platform.slxd.mcp_name` | `slxd-creator` | texto libre sin espacios | Nombre del servidor MCP de slxd en `.mcp.json`, `opencode.json` y `.codex/config.toml`. |
| `platform.slxd.mcp_url` | vacío | URL que empiece por `http://` o `https://` | Dirección del servidor MCP de slxd (por ejemplo `https://acme.example.com/mcp/creator`). Hace falta con cualquiera de los dos backends, porque el diseño instruccional se hace en creator. Si está vacío, no se configura el servidor en ninguna herramienta, `coursekit doctor` lo indica y `coursekit init` avisa al terminar. |
| `platform.slxd.connector` | vacío | texto libre | El conector de creator con el que iniciaste sesión a nivel de cuenta, con el nombre con que tu herramienta de IA lo lista (por ejemplo `SLXD Creator Studio LXD`; el prefijo `claude.ai ` es opcional). Cuando está puesto, las sesiones sin interfaz que lanza coursekit (el handoff, `--headless`) pueden usar sus herramientas, además del servidor de `mcp_name`. Claude Code nombra esas herramientas `mcp__claude_ai_<nombre con guiones bajos>__<herramienta>`. Sin él solo se permite el servidor del proyecto. Mira [Problemas con el servidor MCP](09-troubleshooting.md#problemas-con-el-servidor-mcp). |
| `platform.slxd.organization_id` | vacío | texto libre | Reservado. coursekit no lo lee hoy. |
| `mirror.provider` | `none` | `sharepoint`, `onedrive`, `google-drive`, `nextcloud`, `folder`, `none` | Tipo de carpeta compartida que refleja los cursos (carpeta espejo). `none` desactiva `coursekit publish`. |
| `mirror.url` | vacío | URL (o, para `folder`, texto con `{code}`) | Dirección web de la carpeta espejo, usada para construir los enlaces por curso del catálogo. Para `folder`, un `{code}` en el texto se sustituye por el código del curso. Un enlace para compartir de SharePoint u OneDrive (`/:f:/s/...`) no lleva la ruta de la carpeta, así que no sirve para construir enlaces por curso. `coursekit publish --check` te dice qué forma de enlace se usa. |
| `network.ca_bundles` | `[]` | lista de rutas de fichero | Certificados CA adicionales para redes que inspeccionan TLS. Se expanden las variables de entorno y `~`; se usa el primer fichero que exista. Mira `NODE_EXTRA_CA_CERTS` más abajo. |

Ejemplo mínimo:

```yaml
name: Contraseñas seguras
client: ACME
content_language: es
ui_language: es
tone: cercano y práctico
address: tu

assembly:
  backend: creator   # creator | html

platform:
  slxd:
    mcp_name: slxd-creator
    mcp_url: https://acme.example.com/mcp/creator

mirror:
  provider: sharepoint
  url: https://acme.example.com/sites/training/Shared%20Documents/Courses

network:
  ca_bundles:
    - ~/certs/acme-proxy.pem
```

La ruta local de la carpeta espejo es personal y no va aquí: es `MIRROR_DIR` en `.env`.

Además de estas claves, `project.yaml` admite las secciones `rules:`, `directives:`, `media:` y `delivery:` (más abajo).

## `.env`

`coursekit init` y `coursekit setup` crean `.env` a partir de `.env.example` cuando falta. `.env` está ignorado por git; `.env.example` lo genera coursekit y lo actualiza `coursekit init --update`.

Formato del fichero: un `CLAVE=valor` por línea; las líneas que empiezan por `#` son comentarios; se acepta `export CLAVE=valor`; un valor con espacios o `#` va entre comillas; un ` # comentario` sin comillas detrás de un valor se ignora.

### Identidad e idioma

| Variable | Por defecto | Significado |
|---|---|---|
| `COURSEKIT_USER_NAME` | vacío | Nombre que firma las aprobaciones (`coursekit approve`) y aparece en el historial del curso. |
| `COURSEKIT_USER_EMAIL` | vacío | Correo que acompaña al nombre. Hacen falta ambos para firmar. `coursekit setup` te los pide (sugiriendo tu identidad de git); `coursekit setup --identity` los cambia, y puedes pasar `--name` y `--email`. |
| `COURSEKIT_LANG` | `ui_language` del proyecto (lo escribe `coursekit init`) | `es` o `en`. Idioma de los mensajes de coursekit para ti. |

### Carpeta espejo

| Variable | Por defecto | Significado |
|---|---|---|
| `MIRROR_DIR` | vacío | Ruta local de la carpeta espejo (`project.yaml` › `mirror`), la que mantiene sincronizada tu cliente de escritorio. La necesitan `coursekit publish` y `coursekit doctor`. |

### Roles: herramienta y modelo

Cinco roles, dos variables cada uno. Detalles en [Agentes](05-agents.md).

| Variable | Por defecto tras `coursekit setup` | Significado |
|---|---|---|
| `DESIGN_AGENT` / `DESIGN_MODEL` | `claude` / `opus` | Diseño instruccional. |
| `WRITER_AGENT` / `WRITER_MODEL` | `claude` / `sonnet` | Redacción de unidades. |
| `REVIEWER_AGENT` / `REVIEWER_MODEL` | `claude` / `opus` | Revisión con IA de las unidades. |
| `MEDIA_AGENT` / `MEDIA_MODEL` | `claude` / `opus` | Producción multimedia. |
| `ASSEMBLY_AGENT` / `ASSEMBLY_MODEL` | `claude` / `sonnet` | Montaje, entrega y sincronización de directivas. |

- `<ROLE>_AGENT` es `claude`, `opencode` o `codex`. Si no está definida o está vacía, `claude`. Cualquier otro valor da error al lanzar el rol.
- `<ROLE>_MODEL` es un identificador que entienda la herramienta (Claude Code: un alias como `opus` o un id; opencode: `proveedor/modelo`). Vacío significa el modelo por defecto de la herramienta.
- `.env.example` viene con los modelos vacíos; `coursekit setup` rellena los propuestos (mira [Agentes](05-agents.md)).

### Proveedores de voz, subtítulos e imagen (opcionales)

Un proveedor se usa solo si su clave está definida. En [Multimedia](07-media.md) se explica cómo elige coursekit entre ellos.

| Variable | Por defecto | Significado |
|---|---|---|
| `ELEVENLABS_API_KEY` | vacío | Clave de ElevenLabs. Activa la locución con subtítulos exactos a partir de las marcas de tiempo por carácter. |
| `ELEVENLABS_VOICE_ID` | vacío | Voz de ElevenLabs. Obligatoria junto con la clave (no hay voz por defecto). |
| `AZURE_SPEECH_KEY` | vacío | Clave de Azure AI Speech. |
| `AZURE_SPEECH_REGION` | vacío | Región de Azure de esa clave. Obligatoria junto con la clave. |
| `AZURE_SPEECH_VOICE` | vacío | Voz de Azure. Vacío: `es-ES-ElviraNeural` (español) o `en-GB-SoniaNeural` (inglés). |
| `GOOGLE_TTS_API_KEY` | vacío | Clave de Google Cloud Text-to-Speech. |
| `GOOGLE_TTS_VOICE` | vacío | Voz de Google. Vacío: `es-ES-Chirp3-HD-Aoede` (español) o `en-GB-Chirp3-HD-Aoede` (inglés). |
| `MAGNIFIC_API_KEY` | vacío | Clave de Magnific, para imágenes generadas. coursekit comprueba que esté definida; la usa el agente de multimedia. |
| `PIPER_VOICE` | vacío | Ruta a un modelo de voz de Piper (`.onnx`) para locuciones locales de borrador. `coursekit setup --media` descarga uno y rellena esta variable. |
| `PIPER_SPEAKER` | `0` en `.env.example` | Número de hablante de la voz de Piper. |

### Variables fuera de `.env`

| Variable | Significado |
|---|---|
| `COURSEKIT_PROJECT` | Variable del entorno real: ruta de la raíz del proyecto. Si está definida, coursekit la usa en lugar de buscar `project.yaml` hacia arriba desde la carpeta actual. |
| `COURSEKIT_HOME` | Variable del entorno real: carpeta del almacén de la máquina. Si está definida, sustituye a la carpeta de datos del usuario que se usa por defecto (mira [El almacén de la máquina](#el-almacén-de-la-máquina)). La leen `coursekit setup`, `coursekit doctor` y `coursekit uninstall`: defínela igual para los tres. |
| `NODE_EXTRA_CA_CERTS` | Ruta del certificado CA corporativo para las herramientas de Node (Claude Code, opencode, npm). Si `network.ca_bundles` lista un fichero que existe, `coursekit setup` te ofrece definirla (y `UV_NATIVE_TLS=1` para uv) de forma permanente para tu usuario, y `coursekit doctor` indica si está definida. |
| `UV_NATIVE_TLS` | `1` hace que uv use el almacén de certificados del sistema. `coursekit setup` lo define durante su propia ejecución cuando encuentra un bundle de CA. |
| `LC_ALL`, `LC_MESSAGES`, `LANG` | Idioma del sistema, usado para los mensajes cuando nada más lo indica. |

## Los ficheros de `config/`

Las cuatro configuraciones son `rules`, `directives`, `media` y `delivery`. Cada proyecto recibe `config/<name>.example.yaml` con los valores por defecto completos del paquete (referencia, nunca se lee). Para cambiar algo, crea `config/<name>.yaml` con **solo las claves que cambias**; `coursekit init --update` actualiza los ejemplos sin tocar tus cambios.

Las mismas claves se pueden escribir en una sección `<name>:` de `project.yaml` (gana a `config/`) o del `course.yaml` de un curso (gana a ambos, solo para ese curso).

### `rules`: reglas de producción

La estructura (unidades, apartados, objetivos, horas) no se fija aquí: sale del diseño instruccional aprobado de cada curso. Estas son las comprobaciones que se aplican por encima.

| Clave | Por defecto | Significado |
|---|---|---|
| `pages_per_hour` | `10` | Páginas de texto para el alumno por hora de estudio. |
| `words_per_page` | `500` | Palabras por página. Palabras mínimas de un apartado = páginas (redondeadas hacia arriba) × `words_per_page`; el mínimo lo guarda `coursekit sync` en `course.yaml`. |
| `defaults.intro_section` | `true` | Los cursos nuevos empiezan cada unidad con un apartado de introducción y objetivos. |
| `defaults.summary_section` | `true` | Los cursos nuevos cierran cada unidad con un apartado de resumen. |
| `defaults.structure` | `sin_modulos` | Estructura de los cursos nuevos: `sin_modulos` o `con_modulos` (patrón estructural de slxd). |
| `defaults.grading.passing_score` | `50` | Nota para aprobar un test, cuando el diseño no da a esa actividad de evaluación la suya (`notaAprobado`). |
| `defaults.grading.attempts` | `2` | Intentos permitidos por test, cuando el diseño no da a esa actividad de evaluación los suyos (`intentosMax`; `0` es sin límite). |
| `design.competencies_per_course` | `"2–4"` | Orientación para el agente de diseño: competencias por curso. |
| `design.objectives_per_unit` | `"2–4"` | Orientación: objetivos por unidad. |
| `design.intro_summary_hours` | `"0.2–0.3"` | Orientación: horas de la introducción y del resumen. |
| `review.ai` | `required` | `required` o `skip`. `required`: una revisión con IA precede a la firma de cada unidad. `skip`: una unidad que pasa `coursekit verify` cuenta como revisada y la revisión es la firma de la persona. En ambos casos una persona puede registrar su propia revisión de una unidad con `coursekit reviewed --by`. |
| `handoff.rounds` | `2` | Intentos por paso de `coursekit handoff` (redactar una unidad, su revisión con sus correcciones, la firma del diseño, el multimedia, el montaje, la entrega) antes de parar. `--rounds` lo cambia en una ejecución. |
| `handoff.media_tools` | `[]` | Programas que el agente de multimedia puede ejecutar cuando nadie puede aprobarlos (el handoff, `--headless`). Sin esta regla puede ejecutar `coursekit`, `npx`, Python y todos los programas que las recetas de la configuración de media declaran en `needs` (`bin`, `media`: `vhs`, `piper`, `stable-ts`…, también los de tu propio `config/media.yaml`). Añade aquí el resto, por ejemplo `[blender, gs]`. `bash`, `sh` y `node` dejan al agente ejecutar cualquier orden y nunca se toman de las recetas: añádelos solo si lo aceptas. El agente también puede leer la carpeta del almacén donde vive el workspace de Remotion. |
| `content.word_margin` | `0.05` | Margen recomendado sobre las palabras mínimas (`0.05` = 5 %). Por debajo, `coursekit verify` avisa; por debajo del propio mínimo, da error. |
| `content.placeholders_per_hour` | `2.5` | Marcadores de recurso multimedia exigidos por hora de unidad (redondeado hacia arriba). |
| `content.min_placeholder_types` | `4` | Tipos distintos de marcador exigidos por unidad (limitado por el número de marcadores exigidos). |
| `content.interactive_per_hour` | `4` | Directivas interactivas distintas exigidas por hora de un apartado de contenido. |
| `content.min_interactive_per_content_section` | `1` | Suelo de la regla anterior: todo apartado de contenido necesita al menos tantas. |
| `content.questions_per_objective` | `5` | Tamaño del banco de preguntas por objetivo de la unidad (quedarse corto es un aviso). |
| `content.placeholder_types` | `image`, `video`, `animated_gif`, `infographic`, `diagram`, `simulation`, `terminal_demo`, `audio` | Tipos de marcador permitidos en el contenido, por **id**. El autor escribe en el marcador la palabra del idioma del curso (`Infografía`, `Infographic`…) y `verify` la convierte en el id; un tipo que no esté en la lista es un error. Una lista que escribas sustituye la lista entera, y los ids deben coincidir con las claves de `types` de la configuración `media`. La tabla de ids y palabras está en [Tipos de recurso y claves de las directivas por idioma](06-content.md#tipos-de-recurso-y-claves-de-las-directivas-por-idioma). |
| `content.allowed_symbols` | `★✔✘·—‹›` | Únicos símbolos pictográficos permitidos en el texto; cualquier otro es un error. |

`defaults.*` solo siembra los cursos **nuevos**: `coursekit new` lo copia a `course.yaml`. En un curso que ya existe, edita su `course.yaml` (más abajo).

### `directives`: directivas y bricks de creator

Registro de las directivas `:::nombre` del formato de contenido y del brick de creator en que se convierte cada una.

| Clave | Significado |
|---|---|
| `synced_with_creator` | Fecha de la última comparación del registro con el catálogo de bricks de creator (la actualiza `/sync-directives`). |
| `directives.<name>.brick` | Tipo de brick de creator en que se convierte la directiva (por ejemplo `ACCORDION`). |
| `directives.<name>.role` | `interactive` (cuenta para el mínimo de interactivas), `question` (pregunta de práctica o de evaluación) o `static` (texto destacado, no cuenta como interactiva). |
| `directives.<name>.use` | Orientación de una línea sobre cuándo usarla (escrita en inglés en los valores por defecto). |
| `not_directives.<BRICK>` | Bricks de creator que no son directivas (Markdown normal, marcadores, sin uso), con una nota. |
| `component_equivalents.<component>` | Qué usar en lugar de un componente habitual de e-learning que no tiene brick (se muestra como pista cuando un redactor lo usa). Los valores por defecto cubren `stepper`, `hotspots`, `reveal`, `toggle-compare`, `checklist`, `tooltips`, `modal`, `branching-scenario` y `simulated-terminal`. |

Las directivas por defecto son, por rol: `interactive` (`accordion`, `tabs`, `carousel`, `carousel-quotes`, `flashcards`, `flashcard-gallery`, `labelled-graphic`, `timeline`, `dialog` y los juegos `word-search`, `wordle`, `hangman`, `pasapalabra`, `memory`, `trivial`), `question` (`single-choice`, `multi-select`, `true-false`, `sorting`, `match`, `sorting-groups`, `fill-in-the-blank`, `order-words`, `short-answer`) y `static` (`note`, `highlight`, `quote`). Como los mapas se fusionan, puedes añadir una directiva o cambiar el `role` de una escribiendo solo esa entrada. `coursekit directives check FILE` compara el registro con un resultado guardado de `list_brick_types`.

### `media`: opciones de producción

Para cada tipo de marcador, una lista ordenada de opciones; `coursekit media plan` conserva, para cada recurso, las opciones cuyos requisitos se cumplen.

| Clave | Significado |
|---|---|
| `voice` | Opciones de locución (Vídeo y Audio). Un curso usa un solo proveedor para toda su locución. |
| `subtitles` | Opciones de subtítulos. |
| `types.<id>` | Opciones de cada tipo de marcador, con su id como clave: `image`, `infographic`, `diagram`, `animated_gif`, `terminal_demo`, `video`, `audio`, `simulation`. Un override de `types` en un proyecto usa los mismos ids (no las palabras del contenido); los mapas se fusionan, así que `types: {image: [...]}` sustituye solo las opciones de `image`. |
| `statuses` | Ciclo de vida de un recurso: `pending`, `scripted`, `produced`, `uploaded`. |
| `uses_theme` | Tipos de marcador cuya producción usa los tokens del tema. Ids de tipo; por defecto: `infographic`, `diagram`, `animated_gif`, `simulation`, `video`, `terminal_demo`. Para estos tipos `coursekit media plan` avisa cuando los tokens (los propios del curso o, si no, los del proyecto) faltan o están escritos a mano, y cuando un recurso se hizo con otros tokens; `coursekit media set --status produced` o `uploaded` se rechaza cuando los tokens faltan o están escritos a mano salvo que se indique `--force`, y anota con qué tokens se hizo el recurso. Es una lista, así que una lista que escribas sustituye la lista entera. Mira [Tokens del tema](07-media.md#tokens-del-tema). |

```yaml
# config/media.yaml: solo stock con licencia para las imágenes (la clave es el id, no la palabra `Imagen`)
types:
  image:
    - {id: creator-stock, needs: {mcp: search_stock_images}, how: "Solo stock con licencia"}
```

Cada opción tiene `id`, `how` (descripción), `needs` (requisitos) y, opcionalmente, `only` (limita la opción a cierto contenido, por ejemplo `terminal`). `needs` puede combinar:

| Requisito | Se cumple cuando |
|---|---|
| `env: VAR` | la variable está definida (`.env` o terminal); una lista `[A, B]` necesita todas |
| `bin: CMD` | el comando está instalado |
| `mcp: TOOL` | el agente tiene esa herramienta MCP (solo el agente puede comprobarlo) |
| `media: X` | el comando `X` está en el `PATH` (`coursekit setup --media` instala `piper` y `stable-ts`) |
| `path: P` | la ruta existe dentro del proyecto (por ejemplo `tools/remotion/node_modules`) |
| `none` | siempre |

La cadena de voz por defecto es `elevenlabs-api`, `azure-api`, `google-api`, `elevenlabs-mcp`, `piper`; subtítulos: `elevenlabs-timestamps`, `stable-ts`. Recuerda que las listas se sustituyen enteras: para quitar una opción de voz, escribe la lista `voice` completa sin ella.

### `delivery`: exportación SCORM y revisión del cliente

Con el backend creator las claves `export.*` van a la exportación de creator. Con el backend html coursekit construye el paquete por sí mismo y solo lee `export.standard` (la versión SCORM de `imsmanifest.xml` y del reproductor) y `file_name` (el nombre del zip); `deliveryType`, `reporting` y `scoreSource` no se aplican.

| Clave | Por defecto | Significado |
|---|---|---|
| `export.deliveryType` | `lms` | Tipo de entrega que se pasa a la exportación de creator. |
| `export.standard` | `scorm_1_2` | `scorm_1_2` o `scorm_2004`. Lo usan los dos backends. |
| `export.reporting` | `passed_incomplete` | `passed_incomplete` o `completed_incomplete`. |
| `export.scoreSource` | `quiz` | `quiz` o `lessonProgress`. |
| `file_name` | `{code}-U{unit:02d}-v{version}-{standard}.zip` | Nombre de cada paquete dentro de `courses/<CODE>/delivery/`. `{standard}` es el estándar sin guiones bajos (`scorm12`, `scorm2004`). `coursekit delivery name CODE --unit N --version V` imprime el nombre esperado. |
| `client_review.required` | `false` | Si el cliente debe revisar el curso montado antes de entregarlo. Con `true`, los comandos de entrega (`coursekit delivery check`, `name` y `add`, es decir, `/deliver`) se niegan hasta que la última ronda de `coursekit client` esté `approved` o `skipped` (`coursekit client CODE skip --reason "..."`). Con `false`, entregar no necesita ninguna ronda, y aun así puedes abrir una. |

La revisión del cliente es la fase opcional entre `assembly` y `delivered`; mira [Flujo de trabajo](02-workflow.md#revisión-del-cliente-opcional). Como toda clave de `delivery`, `client_review.required` puede sobrescribirse por proyecto (`config/delivery.yaml` o la sección `delivery:` de `project.yaml`) y por curso, así que un curso puede exigir la revisión en un proyecto que no la exige:

```yaml
# courses/PWD/course.yaml
delivery:
  client_review:
    required: true
```

## `course.yaml`: qué puede fijar una persona por curso

`course.yaml` es el registro de un curso y lo mantienen sobre todo los comandos. Estas son las claves que una persona puede editar a mano:

| Clave | Significado |
|---|---|
| `language` | Idioma de este curso (`es` o `en`); por defecto, el `content_language` del proyecto. |
| `assembly.backend` | `creator` o `html`: el backend que monta este curso, en lugar del del proyecto (`project.yaml › assembly.backend`). La clave no existe por defecto, así que el curso sigue al proyecto; añádela solo en un curso que necesite el otro backend. `coursekit status CODE` imprime el que está en vigor. |
| `client` | Cliente del curso. |
| `design.hours` | Horas totales. `coursekit sync` avisa si no coinciden con la suma de horas de las unidades del diseño aprobado. |
| `design.structure` | `sin_modulos` o `con_modulos`. |
| `design.intro_section`, `design.summary_section` | Si cada unidad abre con una introducción y cierra con un resumen. |
| `design.audience`, `design.level`, `design.prerequisites` | Texto libre para el agente de diseño. |
| `design.tone`, `design.notes` | Tono e instrucciones adicionales para este curso. |
| `design.grading.passing_score`, `attempts` | Calificación de este curso: la nota de aprobado y los intentos de un test cuando el diseño no los fija para su actividad de evaluación. Mira [Calificación de un test](08-assembly-and-delivery.md#calificación-de-un-test). |
| `owners.*` | Quién lidera cada etapa (`instructional_design`, `writing`, `review`, `media`, `assembly`); se muestra en el catálogo. |
| `rules:`, `directives:`, `media:`, `delivery:` | Cambios solo para este curso, con las mismas claves que los ficheros de `config/`. Por ejemplo, `delivery › client_review › required` hace obligatoria la revisión del cliente en este curso (mira arriba). |

No edites a mano: `units` (lo escribe `coursekit sync`), `approvals` (solo lo escribe `coursekit approve`), `deliveries`, `history`, `client_review` y `hold`. El bloque `slxd` (`matrix_id`, `folder_id`, `theme_id`, `organization_id`) lo van rellenando los agentes mientras trabajan; `theme_id` lo escribe también `coursekit theme import --course`.

Campos que escriben los comandos, que puedes leer pero no deberías editar:

| Clave | Lo escribe | Contenido |
|---|---|---|
| `status` | los comandos de cada fase | Estado del curso. `client_review` y `on_hold` los fijan `coursekit client` y `coursekit hold` |
| `client_review` | `coursekit client` | Lista de rondas de revisión del cliente. Cada una tiene `round`, `sent_at`, `sent_by`, `to`, `links` (los enlaces de revisión enviados), `outcome` (vacío mientras está abierta, luego `changes`, `approved` o `skipped`), `closed_at`, `by` (quién aprobó en nombre del cliente) y `note`. No lo confundas con el ajuste `delivery › client_review` de arriba |
| `slxd.theme_id` | `coursekit theme import --course` | Id del tema de la plataforma del que se derivaron los tokens propios del curso. El montaje vincula con él el tema a los contenidos |
| `hold` | `coursekit hold` | Solo mientras el curso está en `on_hold`: `previous` (estado anterior a la pausa), `reason`, `by` y `at`. `coursekit resume` lo elimina |
| `units[].links.preview` | `coursekit assemble link --preview` | Vista previa en vivo de la unidad, sin comentarios |
| `units[].links.review` | `coursekit assemble link --review` | Enlace de revisión de la unidad, donde comenta el cliente |

Los enlaces son por unidad porque cada unidad es un contenido propio en creator. No existe un bloque `links` a nivel de curso.

Una cosa que conviene saber sobre `media:` en `course.yaml`: su clave `voice` es donde `coursekit voice set` guarda la voz elegida para el curso. Mira [Multimedia](07-media.md).

## Tokens del tema y carpetas de caché

Los tokens de diseño del tema son datos derivados de la plataforma, no configuración. Se versionan con el proyecto.

| Ruta | Lo escribe | Contenido |
|---|---|---|
| `theme/tokens.json` | `coursekit theme import FILE` | Tokens del tema del proyecto: `color`, `font`, `radius`, `space`, `shadow` y `origin` |
| `theme/tokens.css` | `coursekit theme import`, `coursekit theme tokens` | Los mismos tokens como propiedades personalizadas de CSS, más clases base para simulaciones |
| `courses/<CODE>/theme/tokens.json`, `tokens.css` | `coursekit theme import FILE --course CODE` | Los tokens propios de un curso. El curso los usa cuando existen; si no, usa los del proyecto |
| `.cache/theme/get_theme.json` | el agente de diseño | Resultado guardado de la herramienta de la plataforma `get_theme`, la entrada de la importación con el backend creator. `.cache/` está ignorado por git |
| `theme/maqueta.css`, `courses/<CODE>/theme/maqueta.css` | el equipo | La hoja de estilos del backend html, la entrada de la importación con ese backend (mira [Ficheros del backend html](#ficheros-del-backend-html)). Se escribe a mano, a diferencia de los tokens |

`origin` en `tokens.json` anota de dónde salen los tokens:

| Clave | Contenido |
|---|---|
| `source` | `creator` cuando se derivaron del tema de la plataforma; `css` cuando se derivaron de la hoja de estilos del backend html. Un fichero con ninguna de las dos cuenta como escrito a mano: `coursekit doctor` y `coursekit media` lo tratan como no derivado |
| `theme_id`, `name`, `version` | Id, nombre y versión del tema de la plataforma (solo `creator`) |
| `file`, `sha256` | El nombre de la hoja de estilos y los 12 primeros caracteres del hash de su contenido (solo `css`). `coursekit theme show` los imprime como la huella |
| `imported_at` | Fecha y hora de la importación |
| `derived` | Tokens que la plataforma no tiene y que coursekit derivó de sus colores (`text-soft`, `surface`, `highlight`, `line`, `accent-strong`) (solo `creator`) |
| `defaults` | Grupos que son valores por defecto del paquete, porque la plataforma no los tiene (`radius`, `space`, `shadow`) (solo `creator`) |
| `notes` | Notas de la importación, por ejemplo que el tema tiene modo oscuro y los tokens son los del modo claro, o (`css`) una variable de color que no es un valor simple |

No edites estos ficheros: para cambiar un color o una tipografía, cambia el tema en la plataforma (o, con el backend html, `theme/maqueta.css`) y vuelve a importarlo. En [Tokens del tema](07-media.md#tokens-del-tema) está el flujo y en [03-commands.md](03-commands.md#coursekit-theme), `coursekit theme`.

## Ficheros del backend html

Con el backend html (`project.yaml › assembly.backend: html`, o `assembly.backend: html` en un `course.yaml`) `coursekit assemble build` construye cada unidad como un paquete SCORM. Estos son los ficheros del proyecto que le dan forma y lo que genera:

| Ruta | Versionado | Qué es |
|---|---|---|
| `theme/maqueta.css` | sí | La hoja de estilos del proyecto (la «maqueta»). Da otro aspecto al paquete y, mediante las variables CSS que declara (`--color-accent`, `--font-family`, `--radius`…), es el tema: `coursekit theme import theme/maqueta.css` deriva de ella los tokens. Las variables que puedes cambiar son el `:root` de la maqueta base del paquete, listadas en [Tokens del tema](07-media.md#tokens-del-tema). |
| `courses/<CODE>/theme/maqueta.css` | sí | Lo mismo para un curso: se añade después de la del proyecto, solo en los paquetes de ese curso. `coursekit theme import courses/<CODE>/theme/maqueta.css --course CODE` deriva los tokens propios de ese curso. |
| `components/*.css` | sí | Estilos adicionales, añadidos al paquete después de las hojas anteriores, por orden alfabético. |
| `components/*.js` | sí | Comportamiento adicional, empaquetado con esbuild en el reproductor (`assets/player.js`) de cada paquete, antes del código del reproductor. |
| `courses/<CODE>/assembly/html/unit-NN/` | no (`.gitignore`) | El paquete de una unidad, que rehace `coursekit assemble build` y se puede abrir desde el disco. |
| `courses/<CODE>/delivery/<nombre>.zip` | no (`.gitignore`) | El zip de una unidad, que escribe `coursekit assemble build --version X.Y`. |

Los estilos de un paquete (`assets/styles.css`) se juntan en este orden, de modo que cada capa gana a las anteriores: la maqueta base del paquete; el `tokens.css` que corresponde al curso (si el curso tiene tokens); `theme/maqueta.css`; `courses/<CODE>/theme/maqueta.css`; `components/*.css`.

`coursekit theme import` deriva los tokens del único fichero que le des, sobre la maqueta base del paquete, no sobre las demás capas. Edita `maqueta.css`, impórtalo de nuevo, y los tokens (y el control de los recursos) lo siguen; el paquete ya usa la hoja de estilos por sí mismo sin importarla. Mira [`coursekit theme`](03-commands.md#coursekit-theme) y, para lo que hace la construcción, [`coursekit assemble`](03-commands.md#coursekit-assemble) y [08-assembly-and-delivery.md](08-assembly-and-delivery.md).

El constructor que empaqueta el reproductor (`@studiolxd/scorm` y `esbuild`) no está en el proyecto: vive en el [almacén de la máquina](#el-almacén-de-la-máquina).

## El almacén de la máquina

Algunas cosas se instalan una vez por máquina, no por proyecto, para que diez proyectos no descarguen diez veces las mismas dependencias. Viven en el almacén: una carpeta fuera de todo proyecto que coursekit crea la primera vez que la necesita.

Dónde está, por orden de preferencia:

| Cuándo | Ruta |
|---|---|
| `COURSEKIT_HOME` está definida | Esa carpeta. |
| macOS | `~/Library/Application Support/coursekit` |
| Linux | `$XDG_DATA_HOME/coursekit`, o `~/.local/share/coursekit` si `XDG_DATA_HOME` no está definida |
| Windows | `%LOCALAPPDATA%\coursekit` |

Qué contiene:

| Ruta (dentro del almacén) | La escribe | Contenido |
|---|---|---|
| `workspaces/<name>-<hash>/` | `coursekit setup --media` (Remotion); `coursekit setup` y `coursekit assemble build` (constructor html) | Un espacio de trabajo de Node instalado una sola vez con `npm install`: el de Remotion (`workspaces/remotion-<hash>/`) y el constructor del backend html (`workspaces/html-builder-<hash>/`, con `@studiolxd/scorm` y `esbuild`). `<hash>` se calcula a partir de su `package.json` y su `package-lock.json`: los proyectos con las mismas dependencias comparten la carpeta, y un proyecto que edita su `package.json` tiene otra. El constructor html toma su `package.json` de coursekit, así que todos los proyectos de la misma versión lo comparten. |
| `installed.json` | `coursekit setup`, `coursekit assemble build` | El registro de lo que coursekit instaló fuera de los proyectos, para que `coursekit uninstall` pueda quitarlo. |

`installed.json` es un fichero JSON con una lista por cada tipo de cosa:

| Clave | Contiene |
|---|---|
| `uv_tools` | Nombres de las herramientas de `uv` que instaló `setup` (`piper-tts`, `stable-ts`). |
| `files` | Rutas de los ficheros de voz que descargó `setup` (`.onnx` y `.onnx.json`). |
| `shell_lines` | Las líneas que `setup` añadió a `~/.zshrc` o `~/.bashrc` (fichero y nombre de la variable): las variables del certificado para un proxy que inspecciona TLS, precedidas del comentario `# coursekit (TLS-inspecting proxy)`. |
| `windows_env` | Nombres de las variables de usuario que definió `setup` en Windows. |
| `system` | Paquetes que `setup` instaló con Homebrew o winget (`manager` y `packages`). `coursekit uninstall` no los quita nunca: los lista. |
| `workspaces` | Nombres de las carpetas de `workspaces/` que instaló coursekit (`remotion-<hash>`, `html-builder-<hash>`), tanto si lo hizo `setup` como la primera `coursekit assemble build`. |

No lo edites a mano. Es solo un registro: si se pierde, `coursekit uninstall` sigue reconociendo las líneas de los ficheros de la terminal, las herramientas de `uv` de coursekit y las carpetas de `workspaces/`, pero no los ficheros de voz, las variables de Windows ni los paquetes del sistema.

### Qué es de la máquina y qué es del proyecto

| De la máquina (fuera del proyecto) | Del proyecto |
|---|---|
| El almacén: `workspaces/` e `installed.json`. | `tools/remotion/`: los fuentes del espacio de trabajo de Remotion (`package.json`, composiciones), versionados con el proyecto. |
| Las herramientas de `uv` (`piper-tts`, `stable-ts`), en las carpetas de `uv`. | `tools/remotion/node_modules`: un enlace a `workspaces/remotion-<hash>/node_modules` en el almacén (un enlace simbólico; una unión o *junction* en Windows). No se versiona. |
| Los ficheros de voz de Piper, en `~/.local/share/piper` (`%LOCALAPPDATA%\piper` en Windows). | `.env`: `PIPER_VOICE` apunta al fichero de voz. |
| Las líneas de los ficheros de la terminal y las variables de usuario de Windows. | `project.yaml › network`: qué certificado de CA usar. |
| Los paquetes del sistema (`ffmpeg`, `node`, `vhs`, `asciinema`). | |
| `workspaces/html-builder-<hash>/`: el constructor del backend html (`@studiolxd/scorm`, `esbuild`). | Nada: el proyecto no guarda copia ni enlace; `coursekit assemble build` usa el del almacén. |

El `.gitignore` que escribe `coursekit init` ignora `node_modules/` (`coursekit init --update` refresca el `.gitignore` salvo que lo hayas editado a mano), así que el enlace nunca se sube. Si no se puede crear el enlace, o `tools/remotion/` ya tiene una carpeta `node_modules` de verdad, se usa esa carpeta tal cual.

`coursekit doctor` muestra la ruta y el tamaño del almacén y si las dependencias de Remotion están al alcance; `coursekit uninstall` desmonta el almacén. Mira [`coursekit setup`](03-commands.md#coursekit-setup), [`coursekit doctor`](03-commands.md#coursekit-doctor) y [`coursekit uninstall`](03-commands.md#coursekit-uninstall).

## Ejemplos prácticos

### Cambiar la nota para aprobar

Para los cursos nuevos, en `config/rules.yaml`:

```yaml
defaults:
  grading:
    passing_score: 70
```

```bash
coursekit rules --changed
# defaults.grading.passing_score  70  (config)
```

Los cursos que ya existen conservan el valor con el que se crearon. Para cambiar `PWD`, edita `courses/PWD/course.yaml`:

```yaml
design:
  grading:
    passing_score: 70
```

y vuelve a montar para que los tests de creator reciban el valor nuevo.

### Cambiar el estándar SCORM

En `config/delivery.yaml`:

```yaml
export:
  standard: scorm_2004
```

```bash
coursekit config delivery --changed
# export.standard  scorm_2004  (config)
coursekit delivery name PWD --unit 1 --version 2
# PWD-U01-v2-scorm2004.zip
```

Para un solo curso, escribe esas mismas dos líneas en una sección `delivery:` de `courses/PWD/course.yaml`.

### Cambiar las palabras por página

En `config/rules.yaml`:

```yaml
words_per_page: 450
```

Los mínimos se guardan en cada curso, así que actualízalos:

```bash
coursekit agents              # las skills muestran el número nuevo
coursekit sync PWD --check    # vista previa
coursekit sync PWD            # escribe los mínimos nuevos en course.yaml
```

### Exigir la revisión del cliente

Para todos los cursos del proyecto, en `config/delivery.yaml`:

```yaml
client_review:
  required: true
```

```bash
coursekit config delivery --changed
# client_review.required  true  (config)
coursekit delivery check PWD
# PWD necesita la revisión del cliente antes de entregarse (delivery.yaml › client_review.required): `coursekit client PWD send`
```

Para un solo curso, usa la sección `delivery:` de su `course.yaml` (mira arriba). `coursekit config delivery --course PWD` muestra el valor en vigor con su origen.

### Endurecer un solo curso

En `courses/PWD/course.yaml`:

```yaml
rules:
  content:
    questions_per_objective: 8
```

```bash
coursekit rules PWD --changed
# content.questions_per_objective  8  (course)
```

Siguiente: [Agentes](05-agents.md)
