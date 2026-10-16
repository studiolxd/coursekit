# Referencia de comandos

Todos los comandos de `coursekit`, agrupados por fase de trabajo, con sus argumentos, opciones, efectos, códigos de salida y un ejemplo, más la tabla que relaciona los comandos de barra (slash) de los agentes con la CLI.

## Comportamiento global

### Encontrar el proyecto

Todos los comandos, salvo `coursekit init`, `coursekit help` y `coursekit uninstall`, trabajan sobre un proyecto: una carpeta con un `project.yaml` en su raíz. Puedes ejecutarlos desde cualquier subcarpeta (por ejemplo `courses/PWD/content/unit-01/`): coursekit sube por las carpetas hasta encontrar `project.yaml`, igual que git encuentra `.git`.

| Variable | Significado |
|---|---|
| `COURSEKIT_PROJECT` | Ruta de la raíz del proyecto. Si está definida, sustituye a la búsqueda: la carpeta debe contener `project.yaml` o el comando falla. Útil en scripts y tareas programadas. |
| `COURSEKIT_NO_UPDATE_CHECK` | Con cualquier valor, desactiva el aviso de que hay un coursekit más nuevo (mira [Instalación](01-getting-started.md#instalación)). |
| `COURSEKIT_NO_REFRESH` | Con cualquier valor, desactiva la actualización automática del proyecto tras actualizar coursekit (mira [Refrescar los ficheros generados](01-getting-started.md#refrescar-los-ficheros-generados)). |
| `COURSEKIT_HOME` | Carpeta del almacén de la máquina (las dependencias de Node compartidas y el registro de lo que instaló `coursekit setup`). Si no está definida, coursekit usa la carpeta de datos del usuario. Mira [El almacén de la máquina](04-configuration.md#el-almacén-de-la-máquina). |
| `COURSEKIT_LANG` | Idioma de los mensajes de coursekit (`es` o `en`; se aceptan valores como `es_ES`). Orden de preferencia: idioma forzado por el asistente de `init`, `COURSEKIT_LANG`, `ui_language` de `project.yaml` (o `content_language` si no hay), idioma del sistema (`LC_ALL`, `LC_MESSAGES`, `LANG`) e inglés. |

### El fichero `.env`

Los comandos cargan `.env` (en la raíz del proyecto) en el entorno del proceso antes de ejecutarse. El entorno real siempre gana: una variable ya definida en la terminal nunca se sobrescribe, y un valor vacío en `.env` cuenta como no definido. `.env` es personal y nunca se sube al repositorio; contiene la identidad de firma (`COURSEKIT_USER_NAME`, `COURSEKIT_USER_EMAIL`), `COURSEKIT_LANG`, `MIRROR_DIR`, la herramienta y el modelo de cada rol (`DESIGN_AGENT`, `DESIGN_MODEL`, `WRITER_AGENT`, `WRITER_MODEL`, `REVIEWER_AGENT`, `REVIEWER_MODEL`, `MEDIA_AGENT`, `MEDIA_MODEL`, `ASSEMBLY_AGENT`, `ASSEMBLY_MODEL`) y las claves opcionales de los proveedores multimedia. Consulta [04-configuration.md](04-configuration.md).

### Ayuda y versión

| Invocación | Resultado |
|---|---|
| `coursekit --help`, `coursekit -h` | Lista de comandos. Código de salida 0. |
| `coursekit help` | Igual que `--help`. Ejecutar `coursekit` sin comando hace lo mismo. |
| `coursekit <command> --help` | Argumentos y opciones de ese comando. |
| `coursekit --version` | Imprime `coursekit <versión>`. |

### Códigos de salida

| Código | Significado |
|---|---|
| `0` | Hecho (también con avisos que no impiden el trabajo). |
| `1` | El comando falló o una comprobación no pasó: mensaje de error en stderr como `coursekit: <mensaje>`, `verify` con errores, `theme check` con un par que falla, `directives check` con diferencias, `brief` con una conversión fallida, una herramienta de IA lanzada que terminó con error, un comando rechazado porque el curso está en pausa. |
| `2` | Uso incorrecto: argumento no válido (argparse) o falta un argumento acompañante obligatorio (por ejemplo `approve content` sin `--unit`, `delivery add` sin `--file`, `client approve` sin `--by`, `client skip` sin `--reason`, `reviewed --note` o `--report` sin `--by`, `assemble plan`, `diff`, `applied` o `link` sin `--unit`). |

`coursekit write`, `coursekit review` y `coursekit run` devuelven el código de salida de la herramienta de IA que lanzaron.

### Quién ejecuta qué

| Marca | Significado |
|---|---|
| Solo personas | El comando firma o cambia algo que pertenece a una persona. Las configuraciones de agente generadas lo deniegan (`coursekit approve`, `coursekit client`, `coursekit hold`, `coursekit resume`, `coursekit handoff`, `coursekit reviewed --by`, `coursekit capture login`, `logout`, `allow`, `revoke`, `approve` y `reject`). |
| Agentes | El agente de un rol lo ejecuta dentro de una skill o un comando de barra. Las personas también pueden ejecutarlo. |
| Ambos | Comandos de uso diario, para personas y agentes por igual. |

Cada comando de abajo indica su propio `Quién:` en su primer párrafo. Solo los comandos de la primera fila quedan bloqueados para los agentes por la configuración generada; "Quién: personas" en cualquier otro comando (`coursekit init`, `setup`, `uninstall`, `write`, `review`, `run`) indica quién debe ejecutarlo, no que se deniegue a los agentes.

### Estados de un vistazo

Las unidades avanzan `pending` -> `writing` -> `verified` -> `reviewed` -> `approved`, y retroceden cuando cambia su contenido. Un curso pasa por `design`, `design_approved`, `writing`, `ai_review`, `editorial_review`, `media`, `assembly`, `client_review`, `delivered` (y `on_hold`). Cada cambio de estado del curso se añade a `course.yaml › history`.

| Comando | Mueve |
|---|---|
| `coursekit new` | crea el curso en `design`. |
| `coursekit approve design` | curso `design` -> `design_approved`. |
| `coursekit handoff` | lleva el curso por todas las transiciones de esta tabla hasta `delivered`, firmando como Coursekit Handoff; se detiene, sin cambiar el estado, en `on_hold` y `client_review`, y se niega a empezar cuando la revisión del cliente es obligatoria. |
| `coursekit verify` | la unidad sube hasta `verified` cuando pasa; `pending` -> `writing` cuando tiene contenido pero con errores; vuelve a `writing` cuando el contenido verificado ya no pasa; vuelve a `verified` cuando el contenido cambió después de la revisión con IA; con `rules › review › ai: skip`, sube directamente hasta `reviewed`; el estado del curso se deriva del de sus unidades. |
| `coursekit reviewed` | unidad -> `reviewed` (revisión con IA, o de una persona con `--by`). |
| `coursekit approve content` | unidad -> `approved`. Cuando todas las unidades están aprobadas el curso pasa a `media`. |
| `coursekit assemble applied` | curso `media` -> `assembly` cuando todas las unidades en creator coinciden con su plan (backend creator). |
| `coursekit assemble build` | curso `media` -> `assembly` cuando todas las unidades tienen su paquete construido (backend html). |
| `coursekit client send` | curso `assembly` -> `client_review` (abre una ronda). |
| `coursekit client changes` | curso `client_review` -> `assembly` (cierra la ronda con cambios). |
| `coursekit client approve` | cierra la ronda como aprobada; el curso sigue en `client_review`. |
| `coursekit client skip` | registra una ronda omitida; el estado no cambia. |
| `coursekit delivery add` | curso `assembly` o `client_review` -> `delivered` cuando todas las unidades tienen un paquete de la misma versión. |
| `coursekit hold` | curso -> `on_hold`, recordando el estado anterior. |
| `coursekit resume` | curso `on_hold` -> el estado que tenía (derivado de nuevo de sus unidades si estaba en la fase de redacción). |

Mientras un curso está en `on_hold`, los comandos que cambian su trabajo se rechazan con un mensaje que indica el motivo y el estado al que volverá; consulta [`coursekit hold`](#coursekit-hold). Los comandos que solo leen siguen funcionando.

## Comandos de un vistazo

| Fase | Comandos |
|---|---|
| Proyecto y máquina | `coursekit help`, `coursekit init`, `coursekit config`, `coursekit rules`, `coursekit agents`, `coursekit setup`, `coursekit doctor`, `coursekit uninstall`, `coursekit roles` |
| Cursos y diseño | `coursekit new`, `coursekit handoff`, `coursekit status`, `coursekit design`, `coursekit sync`, `coursekit outline`, `coursekit brief`, `coursekit import`, `coursekit videos`, `coursekit download` |
| Verificación y firma | `coursekit verify`, `coursekit paths`, `coursekit reviewed`, `coursekit approve` |
| Estado del curso y revisión del cliente | `coursekit hold`, `coursekit resume`, `coursekit client` |
| Lanzar agentes | `coursekit write`, `coursekit review`, `coursekit run` |
| Multimedia | `coursekit media`, `coursekit video`, `coursekit voice`, `coursekit tts`, `coursekit subtitles`, `coursekit theme`, `coursekit capture` |
| Montaje y entrega | `coursekit assemble`, `coursekit preview`, `coursekit directives`, `coursekit delivery`, `coursekit publish`, `coursekit catalog` |

## Proyecto y máquina

### `coursekit help`

Muestra la lista de comandos (igual que `--help`). No tiene argumentos. Quién: ambos.

```
coursekit help
```

### `coursekit init`

Crea un proyecto en una carpeta, o refresca los ficheros que coursekit generó en uno existente. Úsalo una vez por proyecto; usa `--update` después de actualizar coursekit. Quién: personas.

```
coursekit init [folder] [--update] [--name NAME] [--client CLIENT]
               [--language {es,en}] [--ui-language {es,en}] [--tone TONE]
               [--address ADDRESS] [--backend {creator,html}]
               [--mirror {sharepoint,onedrive,google-drive,nextcloud,folder,none}]
               [--theme-source {tenant_default,branding}] [--mcp-url MCP_URL]
               [--mirror-dir MIRROR_DIR] [--mirror-url MIRROR_URL]
               [--yes] [--no-git]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `folder` | por defecto `.` | Carpeta del proyecto. Se crea si no existe. |
| `--update` | indicador | Refresca los ficheros generados de un proyecto existente en lugar de crear uno. Un fichero generado que hayas editado se conserva y se indica. |
| `--name NAME` | por defecto: nombre de la carpeta | Nombre del proyecto. |
| `--client CLIENT` | texto libre | Nombre del cliente (se usa en los metadatos de los cursos). |
| `--language {es,en}` | por defecto `es`; en el asistente, el idioma de la interfaz | Idioma del contenido de los cursos. |
| `--ui-language {es,en}` | por defecto: el idioma del curso | Idioma de la interfaz: los mensajes de coursekit y lo que te dicen los agentes. En el asistente es la primera pregunta. |
| `--tone TONE` | texto libre | Tono de voz del contenido. |
| `--address ADDRESS` | `tu` o `usted` (`es`); `you` (`en`) | Cómo se dirige el contenido al alumno. Un valor no válido sin terminal termina con código 1. |
| `--backend {creator,html}` | por defecto `creator` | Backend de montaje, que se guarda en `project.yaml › assembly.backend`: `creator` carga las unidades en slxd creator; `html` construye cada unidad como un paquete SCORM con coursekit (ver [`coursekit assemble`](#coursekit-assemble)). Un curso puede usar el otro: [04-configuration.md](04-configuration.md#projectyaml). |
| `--design-tool {local,slxd}` | por defecto `slxd` con `--backend creator`, `local` con `html` | Dónde se hace el diseño instruccional de los cursos nuevos: `local` (`design/design.yaml`, [`coursekit design`](#coursekit-design); no hace falta slxd) o `slxd` (la matriz de diseño de slxd). `local` se guarda en `project.yaml › rules › defaults.design_tool`. |
| `--theme-source {tenant_default,branding}` | por defecto `tenant_default` | Solo con el backend creator: de dónde sale el theme, que se guarda en `project.yaml › theme.source`. `tenant_default`: el theme por defecto de la organización en creator. `branding`: un theme que crea `/define-theme` con el material de `theme/branding/`. |
| `--mirror PROVIDER` | `sharepoint`, `onedrive`, `google-drive`, `nextcloud`, `folder`, `none`; por defecto `none` | Proveedor de la carpeta espejo compartida. |
| `--mcp-url MCP_URL` | URL | Dirección del servidor MCP de slxd; se guarda en `project.yaml › platform.slxd.mcp_url`. Se pide con el backend creator o con un diseño hecho en slxd. Una URL no válida termina con código 1. |
| `--mirror-dir MIRROR_DIR` | ruta local | Ruta de la carpeta espejo sincronizada; se guarda en `.env` como `MIRROR_DIR`. |
| `--mirror-url MIRROR_URL` | URL | Dirección web de la carpeta espejo; se guarda en `project.yaml › mirror.url`. |
| `--yes`, `-y` | indicador | No preguntar: usa las opciones y los valores por defecto. Sin terminal tampoco pregunta nunca. |
| `--no-git` | indicador | No ejecutar `git init`. |

Qué hace:

- Con terminal y sin `--yes` pregunta cada uno de los valores anteriores (la URL del MCP de slxd solo con el backend creator o con un diseño hecho en slxd) y después ofrece crear el primer curso con el agente de diseño, solo cuando no hace falta slxd o se dio su URL, y la herramienta de diseño está instalada (pregunta el título y las horas, y después si quieres ejecutar todo el proceso en modo handoff con [`coursekit handoff`](#coursekit-handoff), que espera él mismo al material; si no, pregunta si tienes material de partida, espera mientras lo dejas en `brief/` y lanza `/new-course`).
- Crea las carpetas `courses/`, `brief/sources/`, `config/`, `theme/`, `.agents/`; siembra `project.yaml`, `brief/notes.md` y `brief/links.md`; escribe los ficheros gestionados `AGENTS.md`, `CLAUDE.md`, `.env.example`, `.gitignore`, `config/<name>.example.yaml` (rules, directives, media, delivery, import) y `.githooks/post-merge`, `.githooks/post-checkout`; ejecuta `git init` salvo con `--no-git`.
- Después ejecuta los mismos pasos que [`coursekit setup`](#coursekit-setup) (`.env`, `COURSEKIT_LANG` en `.env`, identidad de firma, hooks de git, roles, agentes, el constructor html con el backend html, diagnóstico) e imprime los siguientes pasos. Cuando la URL del MCP está vacía y hace falta slxd (backend creator o un diseño hecho en slxd), los siguientes pasos avisan de que los agentes no pueden conectar con creator hasta que se rellene `project.yaml › platform.slxd.mcp_url` y se ejecute `coursekit agents`.
- `--update` no escribe nada fuera de los ficheros gestionados (solo vuelve a crear las carpetas del proyecto si faltan) e imprime `creado`, `actualizado`, `sin cambios` o `conservado` para cada uno.
- Código de salida 1 cuando la carpeta ya es un proyecto (sin `--update`) o no lo es (con `--update`).

```
coursekit init acme-courses --yes --language es --client ACME --name "Formación ACME"
```

### `coursekit config`

Muestra la configuración efectiva y la capa de la que viene cada valor. Úsalo para comprobar qué reglas están en vigor. Quién: ambos.

```
coursekit config [{rules,directives,media,delivery}] [--course COURSE] [--changed] [--json]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `name` | `rules`, `directives`, `media`, `delivery`; por defecto: las cuatro | Qué configuración mostrar. |
| `--course COURSE` | código o carpeta del curso | Incluye los ajustes propios de ese curso (`course.yaml`). Código de salida 1 si el curso no existe. |
| `--changed` | indicador | Solo los valores que difieren de los del paquete. |
| `--json` | indicador | Imprime los valores combinados como JSON (un objeto por configuración, o el valor directo cuando se indica `name`). |

Capas, de menor a mayor prioridad: `package` (valores por defecto que trae coursekit), `config` (`config/<name>.yaml`), `project` (la sección `<name>:` de `project.yaml`), `course` (la sección `<name>:` de `course.yaml`). Los mapas se combinan clave a clave; las listas sustituyen la lista entera. Cada línea es `clave  valor  (capa)`.

Los tipos de recurso aparecen con su id en inglés (`image`, `infographic`, `animated_gif`…) en `media` (`types`, `uses_theme`) y en `rules` (`content.placeholder_types`), y los textos de los valores por defecto (`use:`, `how:`, `component_equivalents`) están en inglés. Lo que la persona escribe en un fichero de contenido es la palabra del idioma del curso para cada tipo: consulta [06-content.md](06-content.md#recursos-multimedia).

```
coursekit config delivery --course PWD
```

### `coursekit rules`

Atajo para las reglas de producción (`coursekit config rules`) del proyecto o de un curso. Quién: ambos.

```
coursekit rules [course] [--changed]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `course` | código o carpeta del curso; opcional | Incluye los ajustes propios de ese curso. |
| `--changed` | indicador | Solo los valores que difieren de los del paquete. |

```
coursekit rules PWD --changed
```

### `coursekit agents`

Genera las skills, los comandos de barra y la configuración de los agentes para Claude Code, opencode y Codex a partir del paquete más tus ajustes en `.agents/`. Ejecútalo después de cambiar `project.yaml`, los roles de `.env` o `.agents/`; `coursekit setup` y los hooks de git lo ejecutan por ti. Quién: ambos.

```
coursekit agents
```

Sin argumentos. Escribe los ficheros generados en `.claude/`, `.opencode/`, `.coursekit/agents/` y `.coursekit/docs/`, y actualiza la configuración de las herramientas. Combina (nunca sustituye) en `.claude/settings.json` y `opencode.json` la denegación a los agentes de `coursekit approve`, `coursekit client`, `coursekit hold`, `coursekit resume`, `coursekit handoff`, `coursekit reviewed --by` y `git push`. Cuando `project.yaml › platform.slxd.mcp_url` está definida, añade además el servidor MCP de slxd a `.mcp.json` y a `opencode.json` (combinando) y escribe `.codex/config.toml`, que solo contiene ese servidor (Codex no recibe lista de denegaciones); ese fichero se reescribe entero mientras lleva la línea de marca de coursekit, y se deja como está cuando quitas la línea. Solo se sobrescriben o eliminan los ficheros que coursekit generó (llevan una marca). Imprime `agentes: N escritos, M sin cambios, K eliminados` y lista los ficheros de configuración que actualizó y los que conservó porque los editaste. Detalles en [05-agents.md](05-agents.md).

```
coursekit agents
```

### `coursekit setup`

Prepara esta máquina para el proyecto. Se puede repetir. Quién: personas.

```
coursekit setup [--identity] [--media] [--roles] [--name NAME] [--email EMAIL] [--yes]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `--identity` | indicador | Solo establece o cambia la identidad de firma y termina. Código de salida 1 si no se pudo establecer ninguna. |
| `--media` | indicador | Instala además las herramientas de producción multimedia (ver más abajo). |
| `--roles` | indicador | Vuelve a elegir la herramienta y el modelo de cada rol. |
| `--name NAME` | texto | Nombre de firma, sin preguntar. |
| `--email EMAIL` | texto | Correo de firma, sin preguntar. |
| `--yes`, `-y` | indicador | No preguntar. |

Pasos, por orden: crear `.env` desde `.env.example` si falta; establecer la identidad de firma (`COURSEKIT_USER_NAME`, `COURSEKIT_USER_EMAIL` en `.env`, sugiriendo la identidad de git); configurar el certificado de CA indicado en `project.yaml › network` para proxies que inspeccionan TLS; apuntar git a `.githooks`; escribir en `.env` la herramienta y el modelo por defecto de cada rol (`<ROLE>_AGENT`, `<ROLE>_MODEL`); ejecutar `coursekit agents`; con el backend html, preparar el constructor de los paquetes (más abajo); imprimir el diagnóstico de [`coursekit doctor`](#coursekit-doctor).

`--media` (o responder que sí cuando se pregunta) instala además `ffmpeg`, `node`, `vhs` y `asciinema` (Homebrew en macOS; en Windows winget instala `ffmpeg`, `node` y `vhs`, porque asciinema no tiene versión para Windows y se usa VHS en su lugar; en Linux imprime los comandos que debes ejecutar), instala `piper` y `stable-ts` como herramientas de `uv`, descarga una voz Piper por defecto, prepara el espacio de trabajo de Remotion en `tools/remotion/`, y pide (Intro lo omite) las claves opcionales de ElevenLabs, Azure Speech, Google TTS y Magnific.

Con el backend html (`project.yaml › assembly.backend: html`), `setup` prepara además el constructor de los paquetes, con o sin `--media`: instala `@studiolxd/scorm` (el runtime SCORM del reproductor) y `esbuild` (que empaqueta el reproductor) con `npm install`, una sola vez por máquina, en el [almacén de la máquina](04-configuration.md#el-almacén-de-la-máquina) (`workspaces/html-builder-<hash>/`; el `<hash>` sale del `package.json` del constructor, así que todos los proyectos de la misma versión de coursekit reutilizan la instalación). Sin `npm` imprime un aviso y sigue. Si la instalación falla imprime `aviso: no se pudo preparar el constructor del backend html (npm install); coursekit assemble build lo intentará de nuevo`: `coursekit assemble build` la reintenta cuando falta el constructor. No se instala nada dentro del proyecto.

El espacio de trabajo de Remotion lo comparten todos los proyectos de la máquina. `tools/remotion/` guarda los fuentes (copiados del paquete la primera vez); las dependencias se instalan una sola vez con `npm install` en el [almacén de la máquina](04-configuration.md#el-almacén-de-la-máquina) (`workspaces/remotion-<hash>/`), y el proyecto recibe un enlace `node_modules` hacia ellas (un enlace simbólico; una unión o *junction* en Windows). El hash sale del `package.json` y el `package-lock.json` del espacio de trabajo: los proyectos con las mismas dependencias reutilizan la misma instalación, y un proyecto que edita su `package.json` tiene la suya. Si no se puede crear el enlace, las dependencias se instalan en el propio proyecto; si `tools/remotion/` ya tiene una carpeta `node_modules` de verdad, se respeta tal cual. El `.gitignore` del proyecto ignora `node_modules/`.

Todo lo que `setup` instala fuera de los proyectos (las herramientas de `uv`, los ficheros de voz que descarga, las líneas que añade a los ficheros de la terminal para el certificado del proxy, las variables de usuario de Windows, los paquetes del sistema y los espacios de trabajo compartidos) queda anotado en `installed.json`, en el almacén, para que [`coursekit uninstall`](#coursekit-uninstall) pueda quitarlo.

```
coursekit setup --identity --name "Ana Reyes" --email ana@example.com
```

### `coursekit doctor`

Informa de lo que hay instalado y configurado en esta máquina para el proyecto. Solo lectura. Quién: ambos.

```
coursekit doctor
```

Sin argumentos. Imprime las secciones Base (versión de coursekit y de Python, la última versión publicada en PyPI cuando se puede consultar, `.env`, identidad de firma, hooks de git, MarkItDown, Node y, en un proyecto con el backend html, el constructor de los paquetes html), Herramientas de agente (servidor MCP de slxd, skills y comandos de cada herramienta, herramienta y modelo de cada rol), Red, Carpeta espejo, Theme del proyecto (`ok` cuando `theme/tokens.json` está derivado del tema de la plataforma o de la hoja de estilos del backend html; `info`, con la indicación `/define-theme antes de producir multimedia`, cuando no hay tokens o están escritos a mano) y Multimedia (ffmpeg, vhs, asciinema, piper, stable-ts, el almacén, las dependencias de Remotion, voz y claves opcionales) y, con `capture.yaml › enabled` activado, Captura (Playwright y el navegador para `--mode browser`, el OCR, OpenCV, ffmpeg y, para `--mode desktop`, lo que necesita el sistema: los permisos de Grabación de pantalla y Accesibilidad en macOS, una sesión X11 y `xdotool` en Linux). En Multimedia, una línea `info` muestra la ruta y el tamaño del almacén de la máquina (solo cuando la carpeta del almacén existe), y `dependencias de Remotion (tools/remotion/node_modules)` sale `ok` o `falta` (solo cuando el proyecto tiene `tools/remotion/`; sale `falta` cuando el enlace `node_modules` apunta a la nada, y se arregla con `coursekit setup --media`). En un proyecto cuyo `assembly.backend` es `html`, la sección Base añade `constructor del backend html (@studiolxd/scorm y esbuild)`: `ok` cuando el constructor está instalado en el almacén (`workspaces/html-builder-<hash>/`), `info` (con el comando `coursekit setup`) cuando todavía no; `coursekit assemble build` lo instala la primera vez que se usa; y `navegador para coursekit assemble check (Chrome o Edge)`: `ok` cuando está instalado Google Chrome, Microsoft Edge o Chromium, `info` cuando no (entonces `assemble check` solo comprueba los ficheros). Cada línea es `ok`, `falta` (seguido del comando que lo arregla) o `info`. Siempre termina con código 0.

```
coursekit doctor
```

### `coursekit uninstall`

Quita lo que `coursekit setup` instaló fuera de los proyectos. Funciona en cualquier sitio, con o sin proyecto. Ejecútalo **antes** de quitar el paquete: después el comando ya no existe. Quién: personas.

```
coursekit uninstall [--dry-run] [--yes]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `--dry-run` | indicador | Solo muestra lo que hay y lo que se quitaría. No pregunta ni quita nada. |
| `--yes`, `-y` | indicador | Quita todo sin preguntar. |

Empieza imprimiendo la ruta del almacén (mira [El almacén de la máquina](04-configuration.md#el-almacén-de-la-máquina)) y después muestra cada grupo que tenga algo, y pregunta `¿Quitar esto?` antes de quitar cada uno:

| Grupo | Qué contiene |
|---|---|
| Dependencias de Node compartidas | Los espacios de trabajo de `workspaces/` en el almacén (el de Remotion y el constructor html), con el tamaño de cada uno. |
| Perfiles de captura | Los perfiles de navegador y los permisos de `coursekit capture`, una carpeta por proyecto, con su tamaño. Guardan sesiones iniciadas. |
| Herramientas de multimedia instaladas con `uv` | `piper-tts` y `stable-ts`. Cada una se marca como *instalada por coursekit setup* (consta en el registro) o como *detectada* (está instalada pero no consta, así que puede que no la instalara coursekit: se pregunta antes de quitarla). |
| Ficheros descargados | Los ficheros de voz de Piper que descargó `setup`, con su tamaño. |
| Bloques de los ficheros de la terminal | Las líneas que `setup` añadió a `~/.zshrc` o `~/.bashrc` para el certificado del proxy, marcadas con `# coursekit (TLS-inspecting proxy)`, con el número de bloques de cada fichero. Solo se quitan la marca y la línea que la sigue. |
| Variables de Windows | Las variables de usuario que definió `setup` (solo en Windows, y solo si constan en el registro). |

Si respondes que no, ese grupo se deja como está y los demás se siguen ofreciendo. Sin terminal (un script, una tubería) y sin `--yes` no se puede responder, así que se conserva todo.

Los paquetes del sistema que `setup` instaló con Homebrew o winget no se quitan nunca, porque otras cosas pueden usarlos: solo se listan, cada uno con el comando para quitarlo a mano (`brew uninstall <paquetes>`; `winget uninstall --id <id> -e`). Tampoco se toca nunca ningún proyecto: el comando imprime qué carpetas y ficheros de un proyecto se pueden limpiar a mano (`.claude/`, `.opencode/`, `.codex/`, `.mcp.json`, `opencode.json`, `.coursekit/` y `tools/`). Cuando se ha quitado todo y no queda nada más, quita también la carpeta del almacén. Termina con la línea `Para quitar el propio paquete: uv tool uninstall slxd-coursekit`. Si no hay nada instalado, lo dice y aun así imprime las últimas líneas.

Código de salida 0 en todos los casos, también cuando se conserva algún grupo o no se pudo quitar una herramienta (se indica con el comando que puedes probar a mano).

```
coursekit uninstall --dry-run
coursekit uninstall
uv tool uninstall slxd-coursekit
```

### `coursekit roles`

Muestra la herramienta y el modelo que usará cada rol, según `.env`. Quién: ambos.

```
coursekit roles
```

Sin argumentos. Una línea por rol (`design`, `writer`, `reviewer`, `media`, `assembly`) como `<herramienta> · <modelo>`, con `(no instalado)` cuando la herramienta no está en el `PATH`. `modelo por defecto` significa el modelo propio de la herramienta.

```
coursekit roles
```

## Cursos y diseño

### `coursekit new`

Crea un curso a partir de su título y su duración. Úsalo para empezar un curso; después el agente de diseño propone el diseño instruccional. Quién: ambos (`/new-course` lo ejecuta).

```
coursekit new [--code CODE] [--language LANGUAGE] [--no-intro] [--no-summary] [--notes NOTES] [--approach {expository,decision-based}] [--design-tool {slxd,local}] title hours
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `title` | texto | Título del curso (entre comillas). |
| `hours` | número | Duración total en horas. |
| `--code CODE` | por defecto: el título en mayúsculas y como slug | Código del curso; es el nombre de la carpeta `courses/<CODE>/`. |
| `--language LANGUAGE` | por defecto: `project.yaml › content_language` | Idioma del curso. |
| `--no-intro` | indicador | Unidades sin el apartado inicial de introducción. |
| `--no-summary` | indicador | Unidades sin el apartado final de resumen. |
| `--notes NOTES` | texto | Instrucciones adicionales para el diseño instruccional. |
| `--approach APPROACH` | `expository` o `decision-based`; por defecto: `rules › defaults.approach` | Cómo enseña el curso: `expository` explica y después practica y evalúa; `decision-based` abre cada apartado de contenido con una simulación y explica después (ver [Cursos basados en decisiones](06-content.md#cursos-basados-en-decisiones)). |
| `--design-tool TOOL` | `slxd` o `local`; por defecto: `rules › defaults.design_tool` | Dónde se hace el diseño instruccional, que se guarda en `course.yaml › design.tool`: `slxd` (la matriz de diseño de slxd) o `local` (`design/design.yaml`, que comprueba y exporta [`coursekit design`](#coursekit-design); no hace falta slxd). |

Crea `courses/<CODE>/` con `course.yaml` (estado `design`), las carpetas `brief/sources/`, `design/`, `content/`, `media/`, `reviews/`, `brief/links.md`, `brief/notes.md` y `media/manifest.yaml`, y, con un diseño local, la plantilla `design/design.yaml` para que la rellene el agente de diseño. Las unidades y los apartados no se crean aquí: salen del diseño aprobado con [`coursekit sync`](#coursekit-sync). Código de salida 1 si la carpeta del curso ya existe.

```
coursekit new "Contraseñas seguras" 2 --code PWD --notes "Centrado en personal de oficina"
```

### `coursekit handoff`

Lleva un curso desde su título y sus horas hasta su entrega por sí solo, sin que nadie revise nada por el camino: el diseño, la redacción, la revisión con IA, las firmas, el multimedia, el montaje y la entrega. Quién: solo personas (los agentes no pueden ejecutarlo). Detalles y límites en [Modo handoff](02-workflow.md#modo-handoff).

```
coursekit handoff [--code CODE] [--no-intro] [--no-summary] [--notes NOTES] [--approach {expository,decision-based}] [--rounds ROUNDS] [--no-pause] [--new-version] target [hours]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `target` | texto | Con `hours`: el título del curso nuevo (entrecomíllalo). Sin ellas: el código de un curso para continuarlo donde se quedó. |
| `hours` | número; opcional | Duración total. Hace que `handoff` cree un curso nuevo. |
| `--code CODE` | por defecto: el título como slug en mayúsculas | Código del curso. Solo al crear; se rechaza con un código para continuar (código de salida 2). |
| `--no-intro`, `--no-summary`, `--notes NOTES`, `--approach APPROACH` | como en [`coursekit new`](#coursekit-new) | Solo al crear; con un código para continuar se rechazan (código de salida 2), igual que `--code`. |
| `--rounds ROUNDS` | número entero; por defecto `rules › handoff › rounds` (`2`) | Intentos por paso antes de parar. |
| `--no-pause` | flag | No esperar al material de partida tras crear las carpetas del curso. Sin terminal nunca espera. Solo al crear (se rechaza con un código para continuar, código de salida 2). |
| `--new-version` | indicador | Con el código de un curso `delivered` cuyo contenido has editado: lo reabre y lo lleva a la versión siguiente ([Modo handoff](02-workflow.md#modo-handoff)). Se rechaza (código de salida 1) si el curso no está `delivered`; con título y horas, código 2. |

Al crear, primero hace las carpetas del curso (como [`coursekit new`](#coursekit-new), con `--notes` como indicaciones del diseño) y, en una terminal, **espera a que dejes el material de partida** en `courses/<CODE>/brief/` (`sources/`, `links.md`, `notes.md`; también se lee el material del proyecto en `brief/`) y pulses Enter. A partir de ahí ejecuta, sin interfaz y en orden, el agente de cada rol, y decide cada paso según el estado del curso. Las firmas del diseño y de cada unidad las pone coursekit mismo como **Coursekit Handoff** (nunca como una persona), y cada aprobación anota `via: handoff`. No hace la revisión del cliente y no empieza si el proyecto la exige (`client_review.required`): se niega antes de crear el curso. Cuando un paso sigue fallando tras sus intentos, se para con código de salida 1, dice por qué y cómo seguir (`coursekit handoff <CODE>`). Puede tardar mucho y gastar créditos de los proveedores de multimedia configurados.

```
coursekit handoff "Contraseñas seguras" 2 --code PWD
coursekit handoff PWD
```

### `coursekit status`

Muestra el estado de todos los cursos, o el detalle y el siguiente paso de uno. Solo lectura. Quién: ambos (`/course-status` lo ejecuta).

```
coursekit status [code]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso; opcional | Sin él: una línea por curso (código, estado, horas, unidades, firma del diseño). Con él: título, estado, la línea `Montaje: backend <backend>` (`creator` o `html`: el backend del curso o, si no, el del proyecto), quién firmó el diseño (o por qué la firma ya no vale), una línea por unidad con su estado, una línea con la pausa (desde cuándo, quién, por qué y el estado en que estaba) cuando el curso está `on_hold`, una línea con la última ronda de la revisión del cliente (`abierta`, `pidió cambios`, `aprobada` u `omitida`, y a quién se envió) y el siguiente paso. El siguiente paso depende del estado: en `assembly` propone la revisión del cliente (`coursekit client <CODE> send`) o la entrega (`/deliver`), en `client_review` pide registrar la respuesta del cliente, en `on_hold` remite a `coursekit resume`, etcétera. |

```
coursekit status PWD
```

### `coursekit design`

Comprueba el diseño instruccional de un curso hecho en el proyecto (`course.yaml › design.tool: local`), `design/design.yaml`, y lo exporta. Úsalo cada vez que cambie ese fichero: el agente de diseño lo ejecuta mientras diseña, y la firma necesita su exportación. Quién: ambos (el agente de diseño, `/approve-design`).

```
coursekit design [--check] code
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso | Curso cuyo diseño se comprueba. |
| `--check` | indicador | Solo comprueba e imprime los hallazgos; no escribe nada. |

Aplica las comprobaciones de una matriz de diseño: referencias y estructura (ids, objetivos y competencias que existen, módulos solo con `con_modulos`), cobertura (cada objetivo desarrollado en un apartado, apartados y competencias sin objetivos), evidencia (cada objetivo con una actividad de evaluación), práctica antes de evaluar, el instrumento frente al nivel de Bloom (un test evidencia hasta *apply*, un caso práctico hasta *evaluate*, un portafolio o una rúbrica hasta *create*), horas (apartados sin ellas, partes que no suman lo de su unidad o módulo, un total distinto de `design.hours`), verbos (un objetivo que empieza con un verbo que no se puede observar, o con un verbo de otro nivel de Bloom, según las listas del idioma del curso) y progresión (una unidad que llega a *evaluate* o *create* sin ninguna unidad anterior en *apply* o más). Cada hallazgo se imprime con `✘` (error) o `·` (aviso), y después `N errores · M avisos`.

Sin `--check` escribe `design/matrix.json` (el diseño con la forma de la matriz de diseño de slxd, con ids que no cambian de una exportación a la siguiente, así que volver a exportar no rompe una firma), `design/validation.json` (los hallazgos) y `design/<CODE>-instructional-design.xlsx` (perfil, competencias, objetivos, estructura, actividades y validación, para que lo revise la persona), y refresca la carpeta espejo. Código de salida 1 cuando hay errores (los ficheros se escriben igualmente, para que la persona los vea) o cuando el curso se diseña en slxd. El formato del fichero está en [Diseño local](02-workflow.md#diseño-local).

```
coursekit design PWD --check
```

### `coursekit sync`

Escribe las unidades y los apartados de `course.yaml` a partir del diseño instruccional guardado en `courses/<CODE>/design/matrix.json`. Úsalo con `--check` para ver antes de firmar qué contiene un diseño, y sin él después de que el diseño cambie. Quién: ambos.

```
coursekit sync [--check] code
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso | Curso que sincronizar. |
| `--check` | indicador | Solo informa de lo que se sincronizaría; no escribe nada. |

Sin `--check` escribe `course.yaml › units` (título, horas, objetivos, apartados con sus palabras mínimas, actividades), conservando los campos que coursekit ya había establecido en cada unidad (`status`, `content_id`, `written_with`, `reviewed_with`, `reviewed_parts`, `review`, `links`), y crea los esqueletos `content/unit-NN/content.md` y `assessment.md` de las unidades que no los tienen. El contenido existente nunca se sobrescribe: `content.md` se regenera solo mientras sigue siendo el esqueleto intacto de un diseño anterior, y `assessment.md` se reescribe solo cuando falta o sigue siendo la plantilla en blanco. Imprime los avisos (encabezados de apartado que difieren del diseño, horas que no cuadran, horas que faltan) y un resumen `N unidades, M apartados, W palabras mínimas`, y después cada esqueleto escrito. Los avisos no cambian el código de salida. Sin `design/matrix.json` (o con un fichero que no es un resultado de `design_matrix_get`) se detiene con un mensaje y código de salida 1.

```
coursekit sync PWD --check
```

### `coursekit outline`

Imprime un mapa compacto de un curso (unidades, objetivos, apartados con sus palabras mínimas y cuánto hay escrito) o el texto de un apartado. Solo lectura. Quién: ambos (los agentes lo usan para no cargar todas las unidades).

```
coursekit outline [--section SECTION] code
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso | Curso del que sacar el mapa. |
| `--section SECTION` | `U.S`, por ejemplo `2.3` | Imprime solo el texto de ese apartado (unidad `U`, apartado `S`). Código de salida 2 si el formato no es `U.S`. |

```
coursekit outline PWD --section 1.2
```

### `coursekit download`

Guarda lo que sirve una dirección `https` en un fichero del proyecto: el agente de diseño lo usa para el Excel que exporta slxd (`design_matrix_export` da una `downloadUrl`), porque una sesión sin interfaz puede ejecutar `coursekit` pero no `curl`. Quién: ambos.

```
coursekit download --out OUT url
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `url` | `https://…` | Dirección que se descarga. Cualquier otro esquema se rechaza. |
| `--out OUT` | ruta (obligatoria) | Fichero que se escribe, relativo a la raíz del proyecto o absoluto; tiene que estar dentro del proyecto. |

Imprime `descargado <ruta> (<tamaño> bytes)`. Código de salida 1 si la dirección no es `https`, si la ruta queda fuera del proyecto o si el servidor responde con un error o no se puede alcanzar. Usa los certificados de `network.ca_bundles`, como el resto de llamadas de red.

```
coursekit download "https://…/export/download?t=…" --out courses/PWD/design/PWD-instructional-design.xlsx
```

### `coursekit brief`

Convierte el material de referencia de un curso (o del proyecto) a Markdown para los agentes. Úsalo después de dejar ficheros en `brief/sources/` o URL en `brief/links.md`. Quién: ambos.

```
coursekit brief [--refresh] [--find FIND] [--section SECTION] [--top TOP] [code]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso; por defecto: el `brief/` del proyecto | Brief que convertir. Con un código, también se convierte el brief del proyecto y el índice del curso enlaza con él. |
| `--refresh` | indicador | Vuelve a descargar las URL de `links.md` (por defecto cada URL se descarga una sola vez). |
| `--find FIND` | texto; necesita `code` | No convierte: escribe los fragmentos del material (del curso y del proyecto, `brief/text/`) que más tienen que ver con este texto. |
| `--section SECTION` | `U.S`, p. ej. `1.2`; necesita `code` | Como `--find`, con el título y los objetivos de ese apartado del diseño y el título de su unidad. |
| `--top TOP` | número; por defecto `rules › brief › passages` (`8`) | Cuántos fragmentos escriben `--find` y `--section`. |

Convierte los ficheros de `brief/sources/` en `brief/text/files/` (MarkItDown) y las URL de `links.md` en `brief/text/web/` (necesita Node), solo cuando son nuevos o han cambiado, y escribe `brief/index.md`, que es lo que leen los agentes, en el idioma del contenido del proyecto (o del curso). Las imágenes se listan para que los agentes las abran; el audio y el vídeo necesitan una transcripción. Con un código trabaja en `courses/<CODE>/brief/` y crea `sources/`, `links.md` y `notes.md` si faltan. Imprime una línea de resumen `brief:` (documentos, webs, imágenes/audio/vídeo y la ruta del índice) y un aviso por cada problema. Código de salida 1 si no se pudo convertir algún fichero o si no se pueden descargar las URL porque falta Node; una descarga que falla mientras se ejecuta se avisa como advertencia y el código de salida sigue siendo 0.

Con `--find` o `--section` no convierte nada: corta el Markdown de `brief/text/` en fragmentos (en cada encabezado y por párrafos de unas `rules › brief › passage_words` palabras) y los ordena con BM25, en local (no cuentan las tildes, los plurales ni las palabras comunes del idioma del curso). Escribe `# N fragmento(s) del material para «…» (de M)` y cada fragmento bajo `## i · <fichero>:<primera línea>-<última línea> · <encabezado>`, para que el redactor lea solo esas líneas y las cite. Código de salida 1 cuando el curso no tiene material convertido o el apartado no existe, 2 sin código de curso. El redactor lo usa cuando el material pasa de `rules › brief › large_words` palabras.

```
coursekit brief PWD --refresh
coursekit brief PWD --section 1.2
coursekit brief PWD --find "aplicación autenticadora frente a SMS" --top 3
```

### `coursekit import`

Crea cursos a partir de paquetes de eXeLearning (`.elp`, eXeLearning 2 y 3). Una carpeta con ficheros `.elp` es un curso y cada paquete es una unidad; una carpeta con una subcarpeta por curso crea un curso por subcarpeta. Quién: personas (los agentes diseñan después a partir del brief que deja).

```
coursekit import [--plan] [--plan-file PLAN_FILE] [--hours-file HOURS_FILE]
                 [--default-hours DEFAULT_HOURS] [--hours HOURS] [--title TITLE] [--code CODE]
                 [--handoff] [--rounds ROUNDS] path
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `path` | carpeta | La carpeta con los `.elp` de un curso, o la carpeta padre de varios cursos. Las subcarpetas sin ningún paquete (por ejemplo una exportación HTML de un sitio web) se listan y se omiten. |
| `--plan` | opción sin valor | Solo escribe el plan (`import.yaml` en la raíz del proyecto) para revisarlo y completarlo; no importa nada. |
| `--plan-file PLAN_FILE` | fichero; por defecto `import.yaml` en la raíz del proyecto | El plan que se escribe (`--plan`) o se lee. |
| `--hours-file HOURS_FILE` | `.xlsx` o CSV | Una fila por curso: la carpeta (o el código), las horas y, si se quiere, el título. Las columnas se reconocen por su cabecera (`folder`/`carpeta`, `hours`/`horas`, `title`/`título`); sin cabecera se usan las dos primeras (y una tercera). |
| `--default-hours DEFAULT_HOURS` | número | Horas para los cursos que no las tengan en el plan ni en el fichero de horas. |
| `--hours HOURS` | número | Horas del curso, cuando `path` es un solo curso. |
| `--title TITLE` | texto | Título del curso, cuando `path` es un solo curso. |
| `--code CODE` | código de curso | Código del curso, cuando `path` es un solo curso; por defecto el nombre de la carpeta. |
| `--handoff` | opción sin valor | Tras importar cada curso, lo lleva hasta la entrega en [modo handoff](02-workflow.md#modo-handoff). |
| `--rounds ROUNDS` | número | Con `--handoff`: rondas de revisión con IA y correcciones, como en `coursekit handoff`. |

Las horas no están en los paquetes, así que cada curso las necesita: del plan, del fichero de horas o de `--default-hours` (por ese orden de prioridad). El título sale de los mismos sitios; sin él se usa el nombre de la carpeta y el curso se avisa como provisional. El orden de las unidades se lee del número del nombre de cada paquete (`..._2_vREV`, `MOD3`, `Unidad 2. …`, `3_…`); si no se puede leer, van por nombre, y si dos paquetes reclaman la misma unidad el curso se omite hasta que el plan liste las unidades que se usan.

Cada curso importado se crea con `design.origin: import`, sus paquetes se copian a `brief/sources/` como `01-…`, `02-…` y el brief los convierte ([Importar desde eXeLearning](02-workflow.md#importar-desde-exelearning)). Un curso que ya existe no se toca nunca. Código de salida 1 cuando faltó una decisión en algún curso y no se pudo importar ninguno.

```
coursekit import ../exe/catalogo --plan                 # escribe import.yaml: completa título y horas y revisa las unidades
coursekit import ../exe/catalogo --hours-file horas.xlsx
coursekit import ../exe/catalogo --default-hours 20 --handoff
```

### `coursekit videos`

Conserva los vídeos de un curso alojados en un sitio que `rules › forbidden` lista (YouTube, Vimeo…) cuando son de un **canal oficial**, y gestiona los reemplazos del resto. Quién: ambos (los agentes comprueban y proponen; solo una persona aprueba o rechaza).

```
coursekit videos [--why WHY] [--replaces REPLACES] {check,propose,approve,reject} code [url]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `action` | `check`, `propose`, `approve`, `reject` | Ver más abajo. |
| `code` | código de curso o carpeta | Curso. |
| `url` | dirección del vídeo | Obligatoria en `propose`, `approve` y `reject` (vale cualquier forma de la dirección del mismo vídeo). |
| `--why WHY` | texto | `propose`: la evidencia de que el canal es oficial (por ejemplo la página oficial que lo enlaza). Obligatoria. |
| `--replaces REPLACES` | dirección de vídeo | `propose`: el vídeo al que sustituye. |

Acciones:

- `check`: busca cada dirección de un sitio prohibido en el `content.md` y el `assessment.md` del curso, pregunta al sitio quién la publica (oEmbed, sin clave) y la registra en `media/external-videos.yaml`: `approved` cuando su canal está en `rules › forbidden › allow_channels` (por alias, id, nombre o dirección), `pending` en caso contrario (hay que sustituirlo). Lo que ya está `approved`, `proposed` o `rejected` no se vuelve a preguntar. El idioma del vídeo no importa. Código de salida 1 mientras algo esté `pending` o `rejected`.
- `propose`: el agente de redacción registra como `proposed` un vídeo que encontró en un canal oficial, con `--why` y, si sustituye a otro, `--replaces`. `coursekit verify` lo deja pasar con un aviso hasta que una persona lo compruebe.
- `approve` / `reject`: una persona resuelve un vídeo registrado; queda anotado quién lo hizo, así que necesita la identidad del `.env`. Un vídeo rechazado hace fallar `verify` hasta que se sustituya. Los agentes no pueden ejecutarlos.

Un canal de `allow_channels` puede darse por alias (`@nombre`), por nombre, por id (`UC…`) o por su dirección, también una personalizada (`youtube.com/nombre`): los ids y las direcciones se resuelven al id del canal, que se compara con el del canal que publica cada vídeo.

Cada acción reescribe `reviews/external-videos.md` (en el idioma del curso), con primero los vídeos propuestos por el agente para comprobar, luego los que hay que sustituir, los aprobados y los rechazados. `coursekit verify` lee solo el registro, nunca la red. Se rechaza mientras el curso está en pausa.

```
coursekit videos check ACME
coursekit videos propose ACME https://www.youtube.com/watch?v=abc --replaces https://youtu.be/xyz --why "Enlazado desde la web de soporte del producto"
coursekit videos approve ACME https://www.youtube.com/watch?v=abc
```

## Verificación y firma

### `coursekit verify`

Comprueba el contenido de un curso con las reglas de producción. Úsalo después de cada apartado que escribas y antes de cualquier revisión. Quién: ambos.

```
coursekit verify [--unit UNIT] [--no-update] code
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso | Curso que comprobar. |
| `--unit UNIT` | número de unidad; por defecto: todas | Comprueba solo esa unidad. |
| `--no-update` | indicador | No actualiza el estado de la unidad ni del curso. |

Por unidad comprueba (sobre `content.md` y `assessment.md`): que el diseño está aprobado y no ha cambiado desde la firma; apartados presentes y en el orden del diseño; palabras mínimas por apartado; etiqueta de objetivo en cada apartado de contenido y todos los objetivos cubiertos; directivas interactivas distintas por apartado de contenido; recursos multimedia por hora (cantidad, tipos distintos, campos obligatorios; el tipo se escribe con la palabra del idioma del curso, y la palabra del otro idioma es un error que enumera las válidas); directivas bien formadas (conocidas, cerradas, no anidadas); preguntas con objetivo; ningún emoji fuera de los símbolos permitidos; que el contenido se convierte para el backend de montaje (incluido que las claves de las directivas, como `pregunta:` o `respuesta:`, son las del idioma del curso: una clave del otro idioma se muestra como `assembly: …` con el idioma al que pertenece y las claves válidas; con el backend html comprueba además que cada componente de la unidad se puede dibujar, y una que no se puede se indica como `<lección>: <BRICK>: este componente no está disponible en el backend html`). ninguna dirección de un sitio ni término de `rules › forbidden`. En un curso con `design.origin: import` las carencias de palabras, interactivos y recursos son avisos, con un aviso por cada unidad que se queda corta o se pasa de las palabras de sus horas ([`design.origin`](04-configuration.md#courseyaml-qué-puede-fijar-una-persona-por-curso)). Las cifras salen de `coursekit rules`. Salida: una cabecera `[OK]` o `[FALLO]` por unidad, una línea de estadísticas y después líneas `ERROR` y `AVISO`. Salvo con `--no-update`, mueve el estado de la unidad (ver [Estados de un vistazo](#estados-de-un-vistazo)) e imprime el cambio. Código de salida 1 cuando el diseño no está aprobado o cambió después de la firma, cuando la unidad no existe o cuando alguna unidad tiene errores; los avisos no hacen fallar.

```
coursekit verify PWD --unit 1
```

### `coursekit paths`

Escribe todos los caminos de las simulaciones de un curso (`:::scenario`, `:::conversation`) en `courses/<CODE>/reviews/unit-NN-paths.md`, un fichero por unidad que las tenga, para revisar las ramas sin jugarlas una a una. Quién: ambos (lo ejecutan quien redacta y quien revisa).

```
coursekit paths [--unit UNIT] code
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso | Curso cuyas simulaciones se recorren. |
| `--unit UNIT` | número; por defecto: todas las unidades | Solo esta unidad. |

Para cada simulación el informe tiene un resumen (fichero y línea, escenas, finales alcanzados, número de caminos, puntos de menos a más, minutos del camino más largo, si es evaluable, objetivos), una tabla de las escenas tal como las ve el alumno (texto, la pantalla de la piel, personajes y fondo), un diagrama Mermaid de escenas y decisiones (con condiciones, efectos y puntos) y una tabla con todos los caminos completos, de más a menos puntos: sus decisiones, el final, los puntos, la nota (las evaluables) y el estado final. Imprime `unidad N: K simulaciones → <fichero>` por unidad; `<CODE>: ninguna unidad tiene simulaciones` si no hay. Una unidad cuyas simulaciones tienen errores no recibe informe: se imprimen los errores y el código de salida es 1 (corrígelos con `coursekit verify`). Ver [Simulaciones](06-content.md#simulaciones).

```
coursekit paths PWD --unit 1
```

### `coursekit reviewed`

Marca una unidad como revisada: por la IA (lo ejecuta el agente revisor al terminar su revisión) o, con `--by`, por una persona que la revisó sin la IA. Quién: agentes para la revisión con IA; personas para `--by`.

```
coursekit reviewed code unit [--by NOMBRE] [--note NOTA] [--report FICHERO]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso | Curso. |
| `unit` | número de unidad | Unidad revisada. |
| `--by` | nombre | La revisión es de una persona: registra `review: {kind: human, by, at}` en la unidad y en el historial, y no hace falta el informe de IA. Los agentes tienen la opción denegada. |
| `--note` | texto | Nota de la revisión de la persona (necesita `--by`; código de salida 2 si falta). |
| `--report` | fichero | Informe de la revisión de la persona (necesita `--by`; código de salida 2 si falta); debe estar dentro de la carpeta del curso, normalmente en `reviews/`, y se incluye en el commit de la firma. |

Sin `--by` exige el informe `courses/<CODE>/reviews/unit-NN-ai-review.md` (y registra `review: {kind: ai}`); con `--by` no. En ambos casos la unidad debe seguir verificando sin errores. Mueve la unidad a `reviewed` (el curso deriva su estado) y guarda la huella de cada apartado y actividad en `course.yaml › units[N].reviewed_parts`, de modo que las revisiones posteriores puedan ser parciales. Imprime `unidad N: revisada`, añadiendo el cambio del curso si lo hay. Código de salida 1 si falta el informe, la unidad no existe o no verifica.

```
coursekit reviewed PWD 1
coursekit reviewed PWD 1 --by "Ana Pérez" --note "Revisada con la formadora del cliente"
```

### `coursekit approve`

Firma el diseño instruccional o una unidad, en nombre de la persona que lo ejecuta. Solo personas: las configuraciones de agente generadas lo deniegan y los comandos de barra solo preparan la firma. Quién: personas.

```
coursekit approve [--unit UNIT] [--yes] [--no-commit] [--force] {design,content,style} code
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `gate` | `design`, `content` o `style` | Qué firmar: el diseño instruccional, el contenido de una unidad o la lámina de estilo de las imágenes de las simulaciones. |
| `code` | código o carpeta del curso | Curso. |
| `--unit UNIT` | número de unidad | Unidad que firmar (obligatorio con `content`; sin él el comando termina con código 2). |
| `--yes` | indicador | Confirma sin preguntar. Hace falta cuando no hay terminal; desde el chat de un agente, escríbelo con el prefijo `!` para que se ejecute como tú. |
| `--no-commit` | indicador | Registra la aprobación sin hacer el commit de git. |
| `--force` | indicador | Solo con `content`: firma la unidad aunque su contenido haya cambiado después de la revisión con IA. |

Sin `--yes` necesita una terminal interactiva (si no, código de salida 1) y pregunta `[s/N]` tras mostrar un resumen. Quien firma es la identidad de `.env` (`COURSEKIT_USER_NAME`, `COURSEKIT_USER_EMAIL`), nunca la identidad de git; sin ella el comando termina con código 1 (`coursekit setup --identity`).

`design`: necesita `design/matrix.json`; con un diseño local, también que `design/design.yaml` diga lo mismo que esa exportación (si no, ejecuta [`coursekit design`](#coursekit-design)); se niega si `design/validation.json` contiene hallazgos de severidad `error`. Ejecuta [`coursekit sync`](#coursekit-sync), añade la aprobación a `course.yaml › approvals` (firmante, fecha y hora, id de la matriz, SHA-256 de `matrix.json`, nombre del Excel), pone el curso en `design_approved` y hace commit de la carpeta del curso como `Design approval <CODE>`. Cualquier cambio posterior de `matrix.json` invalida la firma. En un curso basado en decisiones necesita además la biblia narrativa `design/story.md` con una cabecera válida, registra su SHA-256 (`story_sha256`) y un cambio posterior de ella también invalida la firma (ver [Biblia narrativa](06-content.md#biblia-narrativa)). Cuando `misconceptions.per_objective` es mayor que 0 (2 por defecto) necesita además `design/misconceptions.yaml`, con al menos esos errores típicos para cada objetivo del diseño e ids válidos, registra su SHA-256 (`misconceptions_sha256`, también cuando la regla es 0 y el fichero existe) y un cambio posterior de él invalida la firma (ver [Errores típicos](06-content.md#errores-típicos)).

`style`: necesita las muestras de la lámina de estilo en `courses/<CODE>/media/style/` (PNG, JPG, WebP o SVG) y un `media › visual` válido. Registra el estilo firmado (el configurado, o `visual.fallback` cuando no hay generador de imágenes) y el SHA-256 de cada muestra, y hace commit de la carpeta del curso como `Style approval <CODE>`. Mientras no está firmada, `coursekit media set … --status produced` (o `uploaded`) rechaza las imágenes de las simulaciones salvo con `--force`; se vuelve a firmar cuando cambia el estilo. Ver [Imágenes de las simulaciones](07-media.md#imágenes-de-las-simulaciones).

`content`: necesita el diseño aprobado y sin cambios, la unidad pasando `verify` sin errores, el estado de la unidad en `reviewed` (o `approved`) y el informe de la revisión con IA, salvo que una persona haya registrado su propia revisión (`coursekit reviewed --by`) o el proyecto omita la revisión con IA (`rules › review › ai: skip`, donde basta una unidad `verified`). Se rechaza si el contenido cambió después de la revisión con IA: la referencia es la huella de cada apartado y actividad que guardó `coursekit reviewed`, y el mensaje nombra las partes que cambiaron (revísalas de nuevo con `coursekit review`, o firma igualmente con `--force`). Registra el SHA-256 de `content.md` y `assessment.md`, mueve la unidad a `approved` y hace commit de `course.yaml`, la carpeta de la unidad y el informe de revisión como `Content approval <CODE> U<N>`.

Si git no puede hacer el commit, la aprobación queda registrada y el mensaje dice `(registrada, sin commit)`; el código de salida sigue siendo 0.

```
coursekit approve content PWD --unit 1
```

## Estado del curso y revisión del cliente

### `coursekit hold`

Pone un curso en pausa, por ejemplo cuando el cliente detiene el proyecto. El curso conserva todo su trabajo y recuerda el estado en que estaba. Solo personas: las configuraciones de agente generadas lo deniegan. Quién: personas.

```
coursekit hold --reason REASON code
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso | Curso que pausar. |
| `--reason REASON` | texto (obligatorio) | Por qué se pausa. Queda en el historial. Código de salida 2 si falta. |

Registra en `course.yaml › hold` el estado anterior (`previous`), el motivo (`reason`), quién lo pausó (`by`, la identidad de firma) y cuándo (`at`), pone el curso en `on_hold` y añade el cambio a `course.yaml › history`. Imprime `<CODE> en pausa (estaba en «<estado>»)`. Código de salida 1 si el curso ya está en pausa.

Mientras el curso está en pausa se rechazan estos comandos (código de salida 1, con un mensaje que da la fecha, el motivo, el estado anterior y cómo salir): `coursekit write`, `coursekit review`, `coursekit approve`, `coursekit reviewed`, todas las acciones de `coursekit assemble`, `coursekit sync` (sin `--check`), `coursekit media set`, todas las acciones de `coursekit client` y `coursekit delivery check`, `name` y `add`. `coursekit handoff` se detiene con un mensaje que dice cómo reanudar, y `coursekit run` rechaza los comandos que trabajan sobre el curso (véase [`coursekit run`](#coursekit-run)). Los comandos que solo leen siguen funcionando: `coursekit status`, `coursekit verify`, `coursekit config`, `coursekit brief`, `coursekit publish`, `coursekit catalog`, `coursekit outline` y `coursekit sync --check`.

```
coursekit hold PWD --reason "El cliente detiene el proyecto hasta el próximo trimestre"
```

### `coursekit resume`

Saca un curso de la pausa y lo devuelve al estado que tenía. Solo personas. Quién: personas.

```
coursekit resume code
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso | Curso que reanudar. |

Restaura el estado guardado en `course.yaml › hold`; si ese estado pertenecía a la fase de redacción (`design_approved`, `writing`, `ai_review`, `editorial_review`, `media`) se deriva de nuevo de las unidades, por si algo cambió mientras tanto. Elimina el bloque `hold` y añade el cambio al historial. Imprime `<CODE> reanudado: «<anterior>» -> «<nuevo>»`: el estado previo a la pausa y el que tiene ahora el curso (solo difieren si cambiaron las unidades). Código de salida 1 si el curso no está en pausa.

```
coursekit resume PWD
```

### `coursekit client`

Registra la revisión opcional del curso por parte del cliente, ronda a ronda. El cliente comenta el curso montado a través de un enlace de revisión; este comando solo anota lo ocurrido y lo que decidió el cliente. Solo personas: las configuraciones de agente generadas lo deniegan y `/client-feedback` nunca lo ejecuta. Quién: personas.

```
coursekit client [--to TO] [--where WHERE] [--by BY] [--note NOTE] [--reason REASON] code {send,changes,approve,skip}
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso | Curso. |
| `action` | `send`, `changes`, `approve`, `skip` | Ver más abajo. |
| `--to TO` | texto (`send`) | A quién se envía la revisión. Se guarda en la ronda. |
| `--where WHERE` | URL (`send`) | Un único enlace que enviar, en lugar del enlace de revisión de cada unidad. |
| `--by BY` | texto (`approve`) | Nombre de la persona que aprueba en nombre del cliente. Obligatorio en `approve` (código de salida 2 si falta). |
| `--note NOTE` | texto (`changes`, `approve`) | Nota opcional: qué pidió el cliente o sus comentarios. |
| `--reason REASON` | texto (`skip`) | Por qué se entrega el curso sin la aprobación del cliente. Obligatorio en `skip` (código de salida 2 si falta). |

Las rondas se guardan en `course.yaml › client_review`; cada una lleva su número, quién la envió y cuándo, `to`, los enlaces y el resultado (`changes`, `approved` o `skipped`) con la fecha de cierre. Cada acción se añade también al historial. Acciones:

- `send`: abre la ronda N. El curso debe estar en `assembly`. Registra `--to` y los enlaces de cada unidad (`course.yaml › units[N].links.review`, que se guardan con [`coursekit assemble link`](#coursekit-assemble) `--review`), o el único enlace de `--where`. El curso pasa a `client_review`. Se rechaza (código de salida 1) si el curso está en otro estado, si hay una ronda abierta o si no hay ningún enlace.
- `changes`: el cliente pidió cambios. Cierra la ronda abierta con el resultado `changes` y la `--note` opcional, y el curso vuelve a `assembly` para aplicar los cambios (`/client-feedback`) y abrir otra ronda. Se rechaza si no hay ronda abierta.
- `approve`: el cliente aprobó. Cierra la ronda abierta con el resultado `approved`, el nombre de `--by` y la `--note` opcional. El curso sigue en `client_review`; ya se puede entregar. Se rechaza si no hay ronda abierta.
- `skip`: registra una ronda con el resultado `skipped` y el motivo, sin enviar nada. El estado no cambia. Es la forma de entregar un curso sin la revisión del cliente cuando el proyecto la exige. El curso debe estar en `assembly` o `client_review` y no tener ronda abierta.

La revisión es opcional salvo que `delivery.yaml › client_review.required` sea `true`; consulta [`coursekit delivery`](#coursekit-delivery).

```
coursekit client PWD send --to "ana@acme.example"
coursekit client PWD approve --by "Ana Reyes" --note "Aprobado sin cambios"
```

## Lanzar agentes

### `coursekit write`

Escribe unidades con el agente redactor. Sin número de unidad procesa en orden todas las unidades pendientes (`pending` o `writing`) y se detiene en la primera que no termina verificada. Quién: personas (o una tarea programada con `--headless`).

```
coursekit write [--headless] [--agent {claude,opencode,codex}] [--model MODEL] code [n]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso | Curso. |
| `n` | número de unidad; por defecto: todas las pendientes | Unidad que escribir. |
| `--headless` | indicador | Ejecuta la herramienta sin su interfaz; la sesión se guarda en `.cache/logs/`. |
| `--agent {claude,opencode,codex}` | por defecto: `WRITER_AGENT` | Herramienta para este lanzamiento. Sola, usa el modelo por defecto de esa herramienta. |
| `--model MODEL` | por defecto: `WRITER_MODEL` | Modelo para este lanzamiento. |

Registra la herramienta y el modelo en `course.yaml › units[N].written_with` y lanza `/write-unit <CODE> <N>` con el agente redactor. Imprime `write <CODE> · unidad N con <herramienta> · <modelo>` y, con `--headless`, al terminar el resumen final, el estado de la unidad y la ruta del registro de la sesión (una sesión interactiva no imprime nada más). Interactivo: código de salida de la herramienta. Headless: 0 cuando la unidad termina en `verified`, `reviewed` o `approved`; si no, el código de la herramienta o 1. Con varias unidades imprime `detenido en la unidad N` si falla. Cuando no hay nada pendiente imprime `nada que escribir en <CODE>` y termina con 0.

```
coursekit write PWD 1 --agent opencode --model anthropic/claude-sonnet-5-5
```

### `coursekit review`

Ejecuta la revisión con IA de unidades con el agente revisor. Sin número de unidad procesa todas las unidades `verified`. Quién: personas (o una tarea programada con `--headless`).

```
coursekit review [--headless] [--full] [--parts PARTS] [--agent {claude,opencode,codex}] [--model MODEL] code [n]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso | Curso. |
| `n` | número de unidad; por defecto: todas las pendientes | Unidad que revisar. |
| `--headless` | indicador | Ejecuta la herramienta sin su interfaz; la sesión se guarda en `.cache/logs/`. |
| `--full` | indicador | Revisa la unidad entera, aunque ya se revisara antes. |
| `--parts PARTS` | por ejemplo `"section 4, activity 1.2"` | Revisa solo estas partes (separadas por comas). |
| `--agent {claude,opencode,codex}` | por defecto: `REVIEWER_AGENT` | Herramienta para este lanzamiento. |
| `--model MODEL` | por defecto: `REVIEWER_MODEL` | Modelo para este lanzamiento. |

Una unidad ya revisada recibe una revisión parcial solo de las partes que han cambiado desde entonces (a partir de las huellas guardadas), salvo con `--full`; `--parts` las indica a mano. El revisor se registra en `reviewed_with`; se imprime un aviso cuando la unidad no tiene `written_with` o el revisor es la misma herramienta y modelo que el redactor, y la revisión continúa. El agente escribe `reviews/unit-NN-ai-review.md` y ejecuta `coursekit reviewed`. Códigos de salida como en `write` (una unidad está hecha cuando termina en `reviewed` o `approved`).

```
coursekit review PWD 1 --full
```

### `coursekit run`

Lanza cualquier comando de barra (`new-course`, `design-change`, `approve-design`, `define-theme`, `produce-media`, `assemble`, `client-feedback`, `deliver`, `sync-directives`, `course-status`, etc.) con el agente de su rol. Úsalo desde una terminal o un script en lugar de abrir la herramienta de IA. Quién: personas.

```
coursekit run [--role {design,writer,reviewer,media,assembly}] [--headless] [--agent {claude,opencode,codex}] [--model MODEL] name ...
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `name` | nombre del comando sin la barra | Comando que lanzar. |
| `arguments` | el resto de la línea | Se pasan al comando tal cual. |
| `--role {design,writer,reviewer,media,assembly}` | por defecto: el rol del comando (`design` si el nombre es desconocido) | Rol cuyo agente lo ejecuta. |
| `--headless` | indicador | Ejecuta sin la interfaz de la herramienta; la sesión va a `.cache/logs/<name>-<role>-<marca de tiempo>.log`. |
| `--agent {claude,opencode,codex}` | por defecto: `<ROLE>_AGENT` | Herramienta para este lanzamiento. |
| `--model MODEL` | por defecto: `<ROLE>_MODEL` | Modelo para este lanzamiento. |

`--headless`, `--agent`, `--model` y `--role` también pueden ir después del nombre del comando. Imprime `/<name> <arguments> con el agente <role> (<herramienta> · <modelo>)` y devuelve el código de salida de la herramienta. Codex, y opencode con `--headless`, no pueden recibir un comando de barra de proyecto, así que se les indica que sigan `.coursekit/agents/commands/<name>.md`. Cuando el comando trabaja sobre un curso (su primer argumento es un código de curso) y el curso está en pausa, se rechaza con código de salida 1 antes de arrancar la herramienta; `new-course` y `course-status` no se ven afectados.

```
coursekit run new-course "Contraseñas seguras" 2 --code PWD
```

## Multimedia

### `coursekit media`

Gestiona el manifiesto multimedia de un curso (`media/manifest.yaml`) e indica cómo producir cada recurso. Quién: agentes (el agente multimedia) y personas.

```
coursekit media [--status STATUS] [--recipe RECIPE] [--asset-path ASSET_PATH] [--file FILE]
                [--alt ALT] [--transcript TRANSCRIPT] [--subtitles-path SUBTITLES_PATH]
                [--made-with MADE_WITH] [--download DOWNLOAD] [--download-title DOWNLOAD_TITLE]
                [--download-asset-path DOWNLOAD_ASSET_PATH] [--depicts {interface,concept}] [--force]
                [--url URL] [--content-type CONTENT_TYPE] [--method METHOD] [--all] [--clean] [--size SIZE] [--fix] [--frames FRAMES]
                {extract,plan,providers,set,upload,redo,embed,fit,render,narrate,optimize,adopt,check,sheet,transcript} [code] [id] [more ...]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `action` | `extract`, `plan`, `providers`, `set`, `upload`, `redo`, `embed`, `fit`, `render`, `narrate`, `optimize`, `adopt`, `check`, `sheet`, `transcript` | Ver más abajo. |
| `code` | código o carpeta del curso | Obligatorio en todas las acciones salvo `providers` (código de salida 2 si falta). |
| `id` | id de recurso como `U1-S2-M1` | Obligatorio en `set` (código de salida 2 si falta). |
| `--status STATUS` | `pending`, `scripted`, `produced`, `uploaded` | Nuevo estado del recurso (se comprueba con `coursekit config media`). |
| `--recipe RECIPE` | id de opción, por ejemplo `agent-svg` | Opción de producción utilizada. |
| `--file FILE` | ruta dentro de `media/` del curso | Fichero local producido. Con el backend html es lo que lleva el paquete: un fichero o, en simulaciones y demos, la carpeta del paquete o su `index.html`. |
| `--asset-path ASSET_PATH` | texto | Ruta del recurso una vez subido a la plataforma. |
| `--alt ALT` | texto | Texto alternativo. |
| `--transcript TRANSCRIPT` | texto o ruta | Transcripción del audio o vídeo. |
| `--subtitles-path SUBTITLES_PATH` | texto | Fichero de subtítulos. Con el backend html, un `.vtt` local (por ejemplo `media/files/u1-s2-m1.vtt`). |
| `--made-with MADE_WITH` | texto | Herramienta o modelo que lo produjo. |
| `--download DOWNLOAD` | nombre de fichero | Añade o actualiza un fichero descargable adicional del recurso. |
| `--download-title DOWNLOAD_TITLE` | texto | Título de esa descarga (necesita `--download`). |
| `--download-asset-path DOWNLOAD_ASSET_PATH` | texto | Ruta subida de esa descarga (necesita `--download`). |
| `--depicts DEPICTS` | `interface`, `concept` | `set`: qué muestra el recurso: la interfaz de una aplicación real (nunca dibujada ni recreada: solo material real) o una idea, diagrama o escena. Una receta generada lo necesita antes del primer `produced`; ver [la interfaz de una aplicación real](07-media.md#la-interfaz-de-una-aplicación-real-no-se-inventa). |
| `--url URL` | dirección `https://` | `upload`: el `uploadUrl` que dio la plataforma (`request_asset_upload` o `request_embed_upload` de creator). |
| `--content-type CONTENT_TYPE` | tipo MIME, por ejemplo `image/png` | `upload`: el mismo con el que se pidió la subida. |
| `--method METHOD` | por defecto `PUT` | `upload`: método HTTP. |
| `--fix` | indicador | Solo `check`: lleva a la sonoridad objetivo los audios y vídeos que no la tienen, en el sitio. |
| `--frames FRAMES` | número; por defecto `media › checks › sheet_frames` | Solo `sheet`: fotogramas de la hoja de contactos. |
| `--size SIZE` | `ANCHOxALTO` | `fit` (obligatorio) y `render`: el tamaño, p. ej. `1920x1080`. |
| `--all` | indicador | Solo en `redo`: rehace todos los recursos que usan el tema, no solo los hechos con otros tokens. |
| `--clean` | indicador | Solo en `redo`: los recursos olvidan además su fichero, texto alternativo, transcripción, subtítulos y la herramienta que los hizo (los ficheros se quedan en disco), para lo que se hace de nuevo desde cero, como un recurso que mostraba una interfaz inventada. |
| `--force` | indicador | Solo en `set`: marca como `produced` o `uploaded` un recurso que usa los tokens del tema aunque los tokens falten o estén escritos a mano (ver más abajo). |

Acciones:

- `extract`: sincroniza `media/manifest.yaml` con los marcadores de posición (placeholders) que hay en el contenido. Los ids de recurso son `U<unidad>-S<apartado>-M<k>`; el `type` de cada recurso es el id en inglés del tipo (`image`, `infographic`…), sea cual sea la palabra que use el contenido ([07-media.md](07-media.md#recursos-multimedia-y-tipos)). Un recurso cuyo marcador cambió vuelve a `pending`; uno cuyo marcador desapareció pasa a `orphaned`. Imprime `manifest: N recursos (pending 3, ...)`.
- `plan`: para cada recurso `pending` o `scripted`, las opciones de producción disponibles aquí por orden de preferencia (la línea empieza por el id del tipo, `U1-S2-M1 [infographic] Título`), más las opciones de voz y subtítulos para audio y vídeo, y avisos por descargas que faltan y por el tema (ver más abajo). Imprime `nada que producir` cuando no hay nada.
- `providers`: cada proveedor opcional y si está `disponible`, `falta` o `MCP del agente` (solo el agente puede saberlo). No lleva curso.
- `set`: actualiza el recurso `id` con las opciones indicadas; imprime `<id>: <estado>`.
- `upload`: envía el `--file` local (una ruta desde la carpeta del curso o del proyecto) a la `--url` con el `--content-type` e imprime `subido <nombre> (<n> bytes)`. Existe para que el agente de multimedia no necesite `curl`, que una sesión sin interfaz no puede ejecutar. No cambia el manifiesto: el agente registra después el `path` que dio la plataforma con `set --status uploaded --asset-path`. Código de salida 2 sin `--file`, `--url` o `--content-type`; código 1 si el fichero no existe, la dirección no es `https://` o la subida falla.
- `embed`: envuelve el `.svg` que el recurso `id` tiene como `--file` en `media/src/<id>/index.html` (el SVG en línea, adaptable, en el idioma del curso, con las animaciones en pausa si se pide `prefers-reduced-motion`) y dice cómo subirlo: creator no admite el SVG como imagen, así que un SVG se sube como paquete EMBED, y el montaje pone un bloque EMBED donde el fichero del recurso es un `.svg`. Código de salida 1 si el recurso no tiene un fichero `.svg`.
- `fit`: lleva el fichero del recurso `id` a `--size ANCHOxALTO` (obligatorio), escalado para cubrirlo y recortado desde el centro, conservando la transparencia de un PNG; en local, sin gastar créditos de un proveedor. Imprime `<fichero>: <antes> → <después>`.
- `render`: dibuja el `.svg` del recurso `id` como un PNG a su lado (`<nombre>.png`), con el Chrome, Chromium o Edge de la máquina y sin interfaz, al tamaño de su `viewBox` o de `--size`: para mirarlo antes de marcarlo producido, y el PNG que necesita creator. Código de salida 1 si el fichero no es un SVG o no hay ese navegador.
- `optimize`: aligera los ficheros de los recursos `produced` o `uploaded`, en su sitio y en local: las imágenes (PNG, JPEG, WebP) se reducen a `optimize.image.max_width` y se recomprimen, los vídeos MP4 se recodifican como H.264/AAC con tope en `optimize.video.max_height` (necesita `ffmpeg`); un fichero solo se sustituye si el resultado pesa menos. SVG, GIF, audio y paquetes se dejan como están. Con ids, esos recursos; sin ellos, todos. Imprime `<id>: <fichero>: <antes> → <después> bytes` por fichero, o `nada que aligerar`. Ejecútalo antes de subir a creator; el backend html hace lo equivalente con la copia que pone en el paquete. Los límites están en `media.yaml › optimize` ([Medios más ligeros](07-media.md#medios-más-ligeros)). Código de salida 1 si falta `ffmpeg` o falla. Se rechaza mientras el curso está en pausa.
- `adopt`: toma una imagen que ya existe, como una de un paquete de eXeLearning importado (`brief/text/media/<paquete>/<fichero>`), como el recurso `id`: `--file` es el origen (una ruta desde la carpeta del curso o del proyecto), se copia a `media/files/<id>.<ext>` y el recurso queda `produced` con `--alt` y `recipe: imported`, así no se produce de nuevo. Código de salida 2 sin `id` o `--file`; código 1 si el fichero o el recurso no existe. Se rechaza mientras el curso está en pausa.
- `narrate`: produce la narración de las escenas de las simulaciones con `audio: true` (los recursos `VO-…`) con las voces configuradas: el personaje de una conversación con su propia voz (`coursekit voice set --character`), el resto con la voz del curso. Por defecto las pendientes; con ids, esas; con `--all`, todas de nuevo. Cada una va a `media/files/<id>.mp3`, con el texto como transcripción, y queda `produced`. Escribe `N narración(es) de escena producidas`; código de salida 1 si falla el proveedor de voz (lo producido antes se conserva).
- `check`: revisa los audios y vídeos `produced` o `uploaded` (los nombrados, o todos): su sonoridad frente a `media › checks` (EBU R128 para la web: -16 LUFS, pico -1 dBTP, medidos con ffmpeg); los subtítulos (el `.vtt` o `.srt` junto al fichero, con su nombre) más rápidos de `max_cps` caracteres por segundo; y, en un vídeo con sus escenas descritas ([Accesibilidad de los vídeos](07-media.md#accesibilidad-de-los-vídeos)), el texto de pantalla que su locución no dice. Una línea `AVISO <id> [<código>] <qué>` por cada cosa (códigos `LOUDNESS`, `CAPTIONS_FAST`, `NOT_SAID`, `NOT_CHECKED`), y código de salida 1 mientras quede alguna; `--fix` lleva la sonoridad a su objetivo en el sitio (dos pasadas de `loudnorm`; la imagen de un vídeo se copia, no se vuelve a codificar). Necesita `ffmpeg` y `ffprobe`.
- `sheet`: la hoja de contactos del vídeo `id`: `--frames` fotogramas (por defecto 24) repartidos a lo largo de su duración en una sola imagen, con el tiempo de cada uno, en `.cache/media/<CODE>/<id>-sheet.png`, para mirar un vídeo sin reproducirlo.
- `transcript`: a partir de las escenas descritas en `media/scripts/<id>.scenes.yaml`, escribe la transcripción accesible del vídeo `id` (escena a escena, el minuto, lo que se ve y lo que se dice) en `<fichero>.transcript.txt` y una pista WebVTT de descripciones en `<fichero>.descriptions.vtt`, y hace de esa transcripción la del recurso (la que el montaje lleva al curso). Mira [Accesibilidad de los vídeos](07-media.md#accesibilidad-de-los-vídeos).
- `redo`: marca recursos para producirlos de nuevo e imprime sus ids. Con uno o más ids (`redo CODE U1-S3-M1 U1-S5-M4`), esos; sin ellos, los recursos producidos o subidos de los tipos que usan el tema (`uses_theme`) cuya huella difiere de los tokens actuales (todos con `--all`). Vuelven a `scripted` y olvidan su huella y su ruta subida; su guion y su fichero se conservan. Después `/produce-media` (o `coursekit handoff`) los produce otra vez. Mira [Cambiar el theme después de producir el multimedia](07-media.md#cambiar-el-theme-después-de-producir-el-multimedia). Se niega mientras el curso está en pausa.

Los tipos que usan los tokens del tema figuran en `media.yaml › uses_theme` (por defecto `infographic`, `diagram`, `animated_gif`, `simulation`, `video` y `terminal_demo`). Para ellos:

- `plan` avisa, una vez por curso, cuando el curso tiene recursos de esos tipos y sus tokens (los propios del curso o, si no, los del proyecto) faltan o están escritos a mano en lugar de derivados con [`coursekit theme import`](#coursekit-theme) (del tema de la plataforma o de la hoja de estilos del backend html). También avisa por cada recurso `produced` o `uploaded` que se hizo con otros tokens distintos de los actuales.
- `set --status produced` o `--status uploaded` se rechaza (código de salida 1) salvo que los tokens estén derivados (del tema de la plataforma o de la hoja de estilos del backend html) o se indique `--force`. Cuando se acepta, el recurso guarda una huella de los tokens (`theme` en `media/manifest.yaml`), que es lo que permite a `plan` darse cuenta después de que el tema cambió y de que hay que volver a producir el recurso.

Con el backend html no hay subida: un recurso `produced` con su `--file` es definitivo, y `coursekit assemble build` copia el fichero en el paquete. Ver [Multimedia para el backend html](07-media.md#multimedia-para-el-backend-html).

```
coursekit media set PWD U1-S2-M1 --status produced --recipe agent-svg --file media/files/u1-s2-m1.svg --alt "Medidor de fortaleza de contraseñas"
```

### `coursekit video`

Un vídeo como datos: un montaje de escenas (`media/scripts/<id>.video.yaml`) que se renderiza con la biblioteca de escenas de coursekit en Remotion, con el tema del curso; mira [Montaje de vídeo](07-media.md#montaje-de-vídeo). Quién: agentes (el agente de multimedia) y personas.

```
coursekit video {new,check,voice,preview,render,catalog} code [id]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `action` | `new`, `check`, `voice`, `preview`, `render`, `catalog` | Mira abajo. |
| `code` | código o carpeta del curso | Curso. |
| `id` | id del recurso | El recurso de vídeo; todas las acciones salvo `catalog` lo necesitan (código de salida 2 sin él). |

Acciones:

- `new`: un primer montaje para el recurso (una apertura con su título, una escena por rellenar y un cierre) en `media/scripts/<id>.video.yaml`. Nunca escribe sobre uno que exista.
- `check`: el montaje antes de su voz y su render: el formato; cada escena tiene un id, un `type` conocido, sus props obligatorias, sus medios en la carpeta de medios del curso, y `says` o `duration`; textos más largos de lo que cabe en la escena (`TEXT_LONG`); texto en pantalla que la locución no dice (`NOT_SAID`, salvo que la escena lo describa con `shows`). Una línea por hallazgo, `ERROR` o `AVISO`, con la escena y un código; código de salida 1 mientras haya un error.
- `voice`: la locución de cada escena con la voz del curso, y los tiempos de sus palabras (`media/files/<id>/<escena>.mp3` y `.words.json`); solo se vuelven a hacer las escenas cuyo texto o voz cambió. Necesita una voz (mira [`coursekit voice`](#coursekit-voice)) y, salvo con ElevenLabs, `stable-ts`.
- `preview`: un fotograma de cada escena (al 70 %, cuando ya ha entrado lo que entra), pequeño, en una sola imagen: `.cache/media/<CODE>/<id>-preview.png`, antes del render completo.
- `render`: el vídeo en `media/files/<id>.mp4`, con sus subtítulos (`.vtt`, uno por frase que sigue hasta que empieza el siguiente), sus palabras (`.words.json`), sus escenas descritas (`media/scripts/<id>.scenes.yaml`) y su transcripción accesible y pista de descripciones ([Accesibilidad de los vídeos](07-media.md#accesibilidad-de-los-vídeos)); el recurso pasa a `produced` con la receta `montage` (`screen-recording` cuando muestra una interfaz real y tiene un `screencast` de una grabación real). Como todo recurso generado, dice antes qué muestra (`coursekit media set CODE ID --depicts`).
- `catalog`: las escenas que puede usar el curso, de la biblioteca, del proyecto y del curso (cuál tapa a cuál), con qué es cada una, de qué está hecha y sus props (tipo, obligatoria, máximo de caracteres, en pantalla); y los átomos y moléculas de la biblioteca.

`voice`, `preview` y `render` se rechazan mientras el curso está en pausa. `preview` y `render` necesitan el espacio de Remotion (`coursekit setup --media`) y rechazan un montaje con errores (`coursekit video check`).

```
coursekit video new PWD U1-S2-M1
coursekit video check PWD U1-S2-M1
coursekit video voice PWD U1-S2-M1
coursekit video preview PWD U1-S2-M1
coursekit video render PWD U1-S2-M1
coursekit video catalog PWD
```

### `coursekit voice`

Muestra los proveedores de locución disponibles en esta máquina, o fija la voz única de un curso. Un curso nunca mezcla voces. Quién: ambos.

```
coursekit voice [--voice VOICE] [--speaker SPEAKER] [--character CHARACTER] {list,set} [code] [{elevenlabs,azure,google,piper}]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `action` | `list`, `set` | Mostrar o fijar. |
| `code` | código o carpeta del curso | Obligatorio en `set`; opcional en `list` (añade la voz del curso). |
| `provider` | `elevenlabs`, `azure`, `google`, `piper` | Obligatorio en `set`. |
| `--voice VOICE` | id de voz del proveedor; por defecto: la variable de voz del proveedor en `.env` y después la voz por defecto del idioma | Voz que usar. |
| `--speaker SPEAKER` | entero | Locutor de las voces Piper multilocutor. |
| `--character CHARACTER` | nombre (`set`) | Fija la voz de este personaje en vez de la del curso: tiene que ser del proveedor del curso (si no, código de salida 1) y necesita `--voice` (o `--speaker` con Piper). Se guarda en `course.yaml › media.voices`. |

`list` imprime una línea por proveedor (`disponible` o `falta`, con una nota) y, con un curso, qué voz usa o qué hacer a continuación. `set` escribe `course.yaml › media.voice` (`provider`, `voice`, `speaker`), o con `--character` la voz de ese personaje en `media.voices`, y avisa, sin fallar, cuando el proveedor no está configurado en esta máquina. Código de salida 2 cuando a `set` le falta el curso o el proveedor.

```
coursekit voice set PWD azure --voice es-ES-ElviraNeural
```

### `coursekit tts`

Produce la locución de un guion. Quién: agentes (el agente multimedia) y personas.

```
coursekit tts [--course COURSE] [--engine {elevenlabs,azure,google,piper}] --in INPUT --out OUT [--voice VOICE] [--speaker SPEAKER] [--character CHARACTER]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `--course COURSE` | código o carpeta del curso | Usa la voz de ese curso (`course.yaml › media.voice`) y su idioma. |
| `--engine {elevenlabs,azure,google,piper}` | por defecto: la voz del curso, o el único proveedor configurado | Proveedor para esta ejecución. |
| `--in INPUT` | ruta (obligatorio) | Fichero de texto con el guion. |
| `--out OUT` | ruta (obligatorio) | Fichero de audio que escribir (`.mp3`). |
| `--voice VOICE` | texto | Voz, que sustituye a la del curso. |
| `--speaker SPEAKER` | entero | Locutor de las voces Piper multilocutor. |
| `--character CHARACTER` | nombre | Usa la voz de este personaje (`voice set --character`). Con Piper y sin voz propia, los locutores de la voz se turnan en el orden del reparto de la biblia narrativa (un borrador); con otro proveedor y sin voz propia falla y dice cómo fijarla. |

Falla con un mensaje (código de salida 1) cuando el proveedor no está configurado, cuando hay varios proveedores disponibles y no se ha elegido ninguno (usa `coursekit voice set`) o cuando no hay ninguno, cuando el fichero de `--in` no existe, cuando un programa que necesita (`ffmpeg`, `piper`) no está instalado o falla (`<programa> no está instalado o no se encuentra en el PATH (coursekit setup --media)`, `<programa> terminó con error (código N)`), y cuando la API de voz responde con un error o no se puede alcanzar (`<host> respondió <estado> <motivo>: revisa la clave, la región y la voz configuradas`, `no se pudo conectar con <host>: <motivo>`). ElevenLabs escribe además un fichero `.vtt` (subtítulos) junto al audio, con el nombre de `--out` y la extensión `.vtt` (`u1.mp3` da `u1.vtt`), a partir de las marcas de tiempo por carácter que devuelve la API, y los tiempos de cada palabra en `<nombre>.words.json` (`u1.words.json`); con los demás proveedores usa [`coursekit subtitles`](#coursekit-subtitles).

```
coursekit tts --course PWD --in media/scripts/u1-s2-m1.txt --out media/files/u1-s2-m1.mp3
```

### `coursekit subtitles`

Alinea un guion conocido con su audio y escribe subtítulos WebVTT (usa `stable-ts`, que instala `coursekit setup --media`). Quién: agentes (el agente multimedia) y personas.

```
coursekit subtitles --audio AUDIO --text TEXT --out OUT [--course COURSE] [--language LANGUAGE] [--model MODEL]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `--audio AUDIO` | ruta (obligatorio) | Fichero de audio. |
| `--text TEXT` | ruta (obligatorio) | Fichero de texto del guion. |
| `--out OUT` | ruta (obligatorio) | Fichero `.vtt` que escribir. |
| `--course COURSE` | código o carpeta del curso | Toma el idioma del curso (sustituye a `--language`). |
| `--language LANGUAGE` | por defecto `es` | Idioma del audio. |
| `--model MODEL` | por defecto `base` | Tamaño del modelo Whisper que se usa para la alineación. |

Junto a `OUT` escribe también los tiempos de cada palabra dicha, `<nombre>.words.json` (`{"words": [{"w", "start", "end"}]}`, en segundos), que anclan un zoom o una capa de un vídeo a una palabra ([El componente Screencast](07-media.md#el-componente-screencast)). Imprime `escrito <OUT>`. Código de salida 1, con un mensaje, si `stable-ts` no está instalado o falla (`<programa> terminó con error (código N)`), o si el audio o el texto no existen.

```
coursekit subtitles --audio media/files/u1-s2-m1.mp3 --text media/scripts/u1-s2-m1.txt --out media/files/u1-s2-m1.vtt --course PWD
```

### `coursekit theme`

Deriva los tokens de diseño del tema (`tokens.json`, `tokens.css`) a partir del tema de la plataforma de montaje (backend creator) o de la hoja de estilos del proyecto (backend html), indica de dónde salen y comprueba su contraste. Los recursos multimedia (infografías, esquemas, simulaciones, vídeos) usan estos tokens para que parezcan parte del curso. Los tokens nunca se escriben a mano. Quién: ambos (`/define-theme` lo ejecuta).

```
coursekit theme [--course COURSE] {tokens,check,import,show} [file]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `action` | `tokens`, `check`, `import`, `show` | Ver más abajo. |
| `file` | ruta; obligatorio en `import` con el backend creator | Backend creator: el fichero con el resultado guardado de la herramienta de la plataforma `get_theme` (el agente lo guarda en `.cache/theme/get_theme.json`). Backend html: la hoja de estilos `.css` del proyecto (por ejemplo `theme/maqueta.css`). La extensión decide: un fichero que acaba en `.css` se lee como hoja de estilos, cualquier otro como resultado de `get_theme`. Con el backend html el fichero puede omitirse: los tokens son entonces los de la maqueta base sola (el origen dice `base layout`). |
| `--course COURSE` | código o carpeta del curso | Trabaja con el tema propio de ese curso (`courses/<CODE>/theme/`) en lugar del del proyecto (`theme/`). |

Dónde están los tokens: un curso usa sus tokens propios cuando existe `courses/<CODE>/theme/tokens.json`; si no, los del proyecto en `theme/tokens.json`. `tokens`, `check` y `show` aplican esa regla cuando reciben `--course`; `import --course` crea los tokens propios del curso. `coursekit theme show PWD` se acepta como atajo de `coursekit theme show --course PWD`.

Acciones:

- `import FILE` con un resultado de `get_theme` (backend creator): lo convierte en `tokens.json` y `tokens.css`, en la carpeta del proyecto o, con `--course`, en la del curso; además el curso recibe `slxd.theme_id` en su `course.yaml`. Los colores `background`, `text`, `headings`, `accent`, `on-accent`, `link`, `correct`, `on-correct`, `wrong` y `on-wrong` salen de los roles semánticos de color del tema, con las referencias a la paleta resueltas. Los tokens `text-soft`, `surface`, `highlight`, `line` y `accent-strong` no existen en la plataforma y se derivan de esos colores (el texto suave se mantiene al menos a 4,5:1 sobre el fondo). Las tipografías (`font.family`, `font.headings`, `font.ui`) salen de las asignaciones de fuentes, y `size-base` y `line-height` del tamaño base y del interlineado. `radius`, `space` y `shadow` son valores por defecto del paquete, porque la plataforma no los tiene. `tokens.json` anota en `origin` de dónde sale todo. Imprime el fichero escrito, las notas como líneas `AVISO` (una fuente incluida en la plataforma que se usa por su nombre, un rol de color que no se pudo resolver, un modo oscuro) y el contraste de cada par. Un par por debajo de su mínimo no hace fallar la importación: la salida indica que corrijas el color en la plataforma con `update_theme` y vuelvas a importar, nunca que edites los tokens a mano.
- `import FILE` con un fichero `.css` (backend html): los tokens se derivan de las variables CSS de la maqueta base del paquete con ese fichero encima, así que la hoja de estilos solo necesita declarar lo que cambia. Las variables que se leen son `--color-<nombre>` (cada una pasa a ser `color.<nombre>`: `background`, `text`, `text-soft`, `headings`, `accent`, `accent-strong`, `on-accent`, `link`, `surface`, `highlight`, `line`, `correct`, `wrong` y cualquier otra que añadas), `--font-family`, `--font-family-headings` y `--font-family-ui` (`font.family`, `font.headings`, `font.ui`), `--font-size-base`, `--line-height`, `--radius`, `--space-<nombre>` y `--shadow-<nombre>`. Una referencia `var(--x)` se resuelve con los valores de la maqueta base y del fichero (`--color-headings: var(--color-text)` toma el color del texto); gana la última declaración de una variable, esté donde esté en el fichero, y los comentarios se ignoran. `tokens.json` anota en `origin`: `source: css`, `file` (el nombre de la hoja de estilos), `sha256` (los 12 primeros caracteres del hash del fichero), `imported_at` y `notes`; no hay id de theme, así que el curso no recibe `slxd.theme_id`. Imprime `tokens escritos en <ruta> desde las variables CSS de <fichero> (sobre la maqueta base del paquete) y tokens.css al lado`, un `AVISO` por cada color que no es un valor simple (un degradado o un `color-mix()`, por ejemplo: se conserva tal como está escrito y queda fuera de la comprobación de contraste) y el contraste de cada par. Un par por debajo de su mínimo tampoco hace fallar la importación; la indicación que imprime dice que corrijas el color en la hoja de estilos y la vuelvas a importar.
- `tokens`: reescribe `tokens.css` a partir del `tokens.json` que corresponde: propiedades personalizadas de `:root` y clases base para simulaciones. No edites el CSS a mano.
- `check`: imprime el contraste WCAG de los pares de colores que usan los recursos y los componentes, una línea por par, `ok` o `FALLO`.
- `show`: imprime qué tokens se aplican (`tokens del proyecto: theme/tokens.json` o `tokens propios del curso: courses/<CODE>/theme/tokens.json`) y en qué estado están: ausentes (indica que definas el tema con `/define-theme`), escritos a mano (no derivados; indica que los importes) o derivados. Un tema de la plataforma muestra `origen: theme «ACME training» de la plataforma (<id del theme>, versión 3), importado el <fecha>`; una hoja de estilos muestra `origen: variables CSS de maqueta.css (huella <12 caracteres>), importado el <fecha>`. Los agentes leen de la primera forma el id del theme para vincularlo a los contenidos con `set_content_theme`. Los tokens derivados de una hoja de estilos cuentan como derivados para [el control de los recursos](07-media.md#el-control-de-los-recursos) y para `coursekit doctor`.

Códigos de salida: `0` si todo va bien (también en `show`, sea cual sea el estado). `2` cuando `import` no recibe `FILE`. `1`, con un mensaje, cuando el fichero no existe o (si no es un `.css`) no es un resultado de `get_theme`, cuando el curso no existe, cuando faltan los tokens o no son un JSON válido (`tokens`, `check`), y cuando `check` encuentra un par por debajo de su mínimo (4,5 para texto, 3,0 para el acento sobre el fondo). En [Tokens del tema](07-media.md#tokens-del-tema) están el formato de los tokens, qué se deriva y sus límites.

```
coursekit theme import .cache/theme/get_theme.json
coursekit theme import .cache/theme/get_theme.json --course PWD
coursekit theme import theme/maqueta.css
coursekit theme show --course PWD
coursekit theme check
```

### `coursekit capture`

Las capturas reales de una aplicación para los recursos que muestran una interfaz real (`depicts: interface`, recetas `screenshot` y `screen-recording`): los perfiles de las aplicaciones web, el permiso para capturar, el servidor con el que un agente maneja una aplicación web y la captura con los datos personales ya sustituidos, y el tapado de los datos personales de una captura o una grabación que aportó una persona. La ventana de un programa de escritorio funciona en macOS, Windows y Linux con X11 (Windows y Linux aún no se han probado en máquinas reales). Quién: personas (`login`, `logout`, `allow`, `revoke`, `approve` y `reject` se deniegan a los agentes); `profiles`, `redact`, `review`, `replay` y `serve`: ambos (`serve` lo arranca la herramienta de IA).

```
coursekit capture [--mode {browser,desktop}] [--profile PROFILE] [--window WINDOW] [--minutes MINUTES] [--file FILE] [--note NOTE] [--mask MASK] {login,logout,profiles,allow,revoke,redact,review,approve,reject,serve,replay} [target] [ids ...]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `action` | `login`, `logout`, `profiles`, `allow`, `revoke`, `redact`, `review`, `approve`, `reject`, `serve`, `replay` | Mira abajo. |
| `target` | nombre de perfil o código de curso | `login` y `logout`: el perfil; las demás acciones: el curso. |
| `ids` | ids de recursos | `allow`: los recursos que se pueden capturar (sin ids, todos los recursos del curso que muestran una interfaz). `redact`, `review`, `approve`, `reject` y `replay`: el recurso. |
| `--mode MODE` | `browser`, `desktop` | `allow`: una aplicación web abierta en un navegador (`browser`) o una ventana de un programa de la máquina (`desktop`). Obligatorio. Tiene que estar en `capture.yaml › modes`. |
| `--profile PROFILE` | nombre de perfil | `allow --mode browser`: el perfil con el que se abre. Obligatorio en ese modo; el perfil tiene que tener sesión. |
| `--window WINDOW` | nombre de ventana | `allow --mode desktop`: la única ventana que se puede capturar y manejar. Obligatorio en ese modo. |
| `--minutes MINUTES` | número; por defecto `capture.yaml › grant_minutes` | `allow`: cuánto dura el permiso. |
| `--file FILE` | ruta; por defecto `media/recordings/<id>.*` | `redact`: la captura (`.png`, `.jpg`, `.webp`) o la grabación (`.mp4`, `.mov`, `.webm`, `.mkv`) que aportó la persona. |
| `--note NOTE` | texto | `reject`: qué faltó tapar o qué está mal. |
| `--mask MASK` | texto; se puede repetir | `reject`: un texto que hay que tapar siempre en este recurso a partir de ahora. |

Nada funciona hasta que el proyecto lo activa (`enabled: true` en `config/capture.yaml`, mira [`capture`](04-configuration.md#capture-capturas-reales-de-una-aplicación)). Acciones:

- `login PROFILE`: abre el Chrome, Edge o Chromium de la máquina, visible, con un perfil de navegador propio guardado en el almacén de la máquina (`capture/<project>/profiles/<name>/`, que solo puede leer su dueño), en la `start_url` del perfil. La persona inicia sesión (con inicio de sesión único y segundo factor incluidos) y cierra el navegador; la sesión se queda en el perfil. coursekit nunca ve ni guarda la contraseña, y cada proyecto tiene sus propios perfiles. Necesita el extra `capture` del paquete (`uv tool install "slxd-coursekit[capture]"`); no se descarga ningún navegador.
- `logout PROFILE`: borra el perfil y su sesión.
- Un perfil con `login: false` abre un sitio que no necesita cuenta: no hay `login`, y `allow` no pide sesión. El perfil `course` viene incorporado: graba el propio curso (un vídeo de cómo se navega el curso, una demo para el cliente), sin iniciar sesión y sin datos de nadie. El bloque `capture` del guion dice `start: unit:N` (seguido, si hace falta, de una ruta): con el backend html, el paquete de la unidad N (`assembly/html/unit-NN/`, construido con `coursekit assemble build`) se sirve en esta máquina (`127.0.0.1`, un puerto libre, solo mientras dura la sesión); con creator, la sesión abre el enlace de revisión de la unidad N (el que crea el agente de montaje y usa `coursekit client`), y su dominio es el único permitido. Si la página de revisión enseña comentarios con nombres, se sustituyen como cualquier dato personal; mejor oculta ese panel con un `selector` de la `mask` del bloque.
- `profiles`: lista los perfiles de `capture.yaml › profiles` con la etiqueta de su cuenta, dónde empiezan y si tienen sesión (y desde cuándo); también aparece una sesión cuyo perfil ya no está configurado, para poder borrarla.
- `allow CODE [ID…]`: da el permiso para capturar, firmado con la identidad del `.env`, hasta que caduca. Dice el modo y el perfil o la ventana. Un permiso nuevo sustituye al que tenía el curso. Se rechaza un recurso que no muestra una interfaz.
- `revoke CODE`: retira el permiso antes de que caduque.
- `serve`: el servidor MCP de captura, por stdio; lo arranca la herramienta de IA (`coursekit agents` lo registra cuando la captura está activada, mira [El servidor MCP de captura](05-agents.md#el-servidor-mcp-de-captura)). El agente empieza una sesión para un recurso con un permiso en vigor y una receta `screenshot` o `screen-recording`. Con `--mode browser`, se abre el navegador de la máquina, visible, con el perfil, en el `start` del bloque `capture` del guion o en la `start_url` del perfil. Antes de que se vea la página, cada texto en pantalla (textos, los atributos `title`, `placeholder` y `alt`, el título de la pestaña, el shadow DOM abierto y cerrado, lo que aparece después) tiene sus datos personales sustituidos por datos inventados del idioma del curso; los campos y las áreas editables se difuminan, nunca se cambian (un Guardar enviaría los datos inventados a la aplicación real); las fotos y los avatares, y los `redact › selectors` y el `selector` de la `mask` del guion, se difuminan; con `redact › pixel_check`, cada pantalla se lee también sobre los píxeles y lo que quede se tapa. El agente ve la pantalla con `screenshot › max_edge` píxeles como mucho de ancho o de alto, y sus coordenadas están en ese espacio. La navegación fuera de `allow_domains` se bloquea; se rechaza escribir en un campo de contraseña o de código de un solo uso; el permiso se comprueba antes de cada acción, y la sesión termina cuando caduca o se retira, o cuando el navegador llega a la `login_url` del perfil (una persona vuelve a iniciar sesión). `save_shot` guarda `media/recordings/<id>.png`; `session_end` escribe los pasos en el bloque `capture` de `media/scripts/<id>.md` (el destino de cada clic por rol y nombre, para poder repetirlo) y deja la captura `captured`, a la espera de una persona (`review`, `approve`). La sesión no graba vídeo: el modelo piensa entre acciones y el vídeo saldría lleno de pausas; lo graba `replay`.
  Con `--mode desktop`, la sesión busca la ventana del permiso entre las que hay en pantalla, por el nombre del programa o el título de la ventana (tiene que coincidir exactamente un programa; si no, lista las ventanas que hay). No hay página que limpiar, así que hace falta un OCR: cada pantalla se lee sobre los píxeles y sus datos personales se tapan antes de que el agente la vea, diga lo que diga `pixel_check`. El agente solo ve la zona de esa ventana, con el programa traído al frente y cualquier ventana de otro programa que esté encima pintada (en macOS y Windows; en X11 no se conocen, así que el programa solo se trae al frente); un clic, un arrastre o un desplazamiento solo llega al sistema si lo que hay bajo el puntero es de ese programa (sus menús y diálogos incluidos); se rechaza escribir en un campo de contraseña: en macOS, un campo de texto seguro o un campo cuyo nombre dice que es una contraseña o un código (y también cuando no se puede saber cuál es el campo activo); en Windows, un cuadro de edición clásico con el estilo de contraseña (en otros tipos de programa no se puede saber, y no se rechaza); en X11 no se puede saber. Allí no existe `navigate`. Lo que necesita cada sistema: en macOS, dos permisos para la terminal que ejecuta coursekit (Ajustes del Sistema › Privacidad y seguridad: Grabación de pantalla y Accesibilidad); en Windows, nada; en Linux, una sesión X11 (Wayland no deja que un programa maneje otro: se rechaza) y el programa `xdotool`. `coursekit doctor` dice qué falta.
- `replay CODE ID`: repite los pasos del bloque `capture` del guion sin modelo, en el mismo navegador limpio, al ritmo de una persona (`capture.yaml › replay`: una pausa tras cada paso, el puntero que viaja hasta cada destino, el texto tecleado letra a letra) y con un puntero visible y un círculo en cada clic. Necesita el mismo permiso que una sesión. Un paso nombra su destino por rol y nombre, por etiqueta o por texto, y un paso escrito por una sesión tiene además su posición: se prueba primero el nombre, así que una versión nueva de la aplicación que movió un botón se sigue repitiendo, y la posición es el recurso. Los tramos entre `record: start` y `record: stop` (o hasta el final) se graban con el screencast del navegador y se unen en `media/recordings/<id>.mp4` (necesita ffmpeg); con `redact › pixel_check` el vídeo se tapa también sobre los píxeles. Un paso `shot` guarda `media/recordings/<id>.png`. El resultado espera a una persona, como cualquier captura. Un paso que no encuentra lo detiene, con su número, para poder corregir el bloque. Junto al vídeo escribe `media/recordings/<id>.events.json`: cuándo (segundos desde el principio del vídeo) y dónde (fracciones de la pantalla) ocurrió cada clic y cada `point`, con su etiqueta, para que un zoom del vídeo nunca adivine una coordenada ([El componente Screencast](07-media.md#el-componente-screencast)). Un paso `point` (`{point: {label: …, note: …}}`, o `point` en una sesión) marca un sitio de la pantalla sin tocarlo, para lo que nombrará la locución. Los pasos que conoce: `click` y `fill` (`{label: …, value: …}`), `point`, `move`, `drag`, `scroll`, `type`, `key`, `wait`, `navigate`, `shot` y `record`. En el escritorio los destinos van por su posición dentro de la ventana, el vídeo es la zona de la ventana grabada con ffmpeg (`avfoundation` en macOS, donde la ventana tiene que estar entera en la pantalla principal; `gdigrab` en Windows; `x11grab` en Linux), con el puntero del sistema, y siempre se tapa sobre los píxeles: si no se puede, el vídeo se borra y la repetición falla.
- `redact CODE ID`: tapa los datos personales de la captura o la grabación que aportó una persona. El original sale del proyecto en el acto (se guarda en el almacén, `capture/<project>/raw/`, para taparlo de nuevo tras un rechazo, y se borra al aprobarlo o pasados `raw › keep_days`); el tapado va a `media/recordings/<id>.png` (una imagen) o `<id>.mp4` (un vídeo). Se lee el texto (OCR, mira [`capture`](04-configuration.md#capture-capturas-reales-de-una-aplicación)), se tapa cada tramo con la forma de un tipo de `redact › patterns`, el nombre de una persona o un `extra_terms`, y también las caras; un vídeo se lee `video_fps` veces por segundo y lo que encuentra una lectura sigue tapado hasta la siguiente. El recurso recibe `capture.state: captured` en el manifiesto, y `coursekit media set --status produced` lo rechaza hasta que una persona lo aprueba. Si el original ya estaba en git, lo avisa: sale del proyecto, pero no del historial. Una captura rechazada se vuelve a tapar desde el original, con los textos de `--mask`.
- `review CODE ID`: imprime la ruta de la hoja de revisión (`.cache/capture/<CODE>/<id>/review.html`): cada lectura, tapada, con un marco alrededor de lo tapado, los tipos encontrados y lo que no se pudo comprobar (las caras, si falta el extra `capture`). Nunca contiene los valores reales.
- `approve CODE ID`: una persona aprueba la captura tapada, firmada con la identidad del `.env`; el original se borra y `/produce-media` ya puede componer el recurso.
- `reject CODE ID --note "…" [--mask "…"]`: una persona la rechaza, diciendo qué falta (`--note`) o qué hay que tapar (`--mask`, al menos una de las dos); después `redact` la vuelve a tapar.

Tapar sobre los píxeles encuentra lo que tiene forma de dato personal, no todo: se puede escapar un nombre que las listas no conocen, un número con una forma propia (añádelo a `patterns`) o un texto dentro de una foto, así que la revisión de una persona no es opcional. Usa una cuenta o un entorno de pruebas con datos inventados: tapar es una red de seguridad, no la medida principal. Códigos de salida: `0` si todo va bien; `2` si falta `target`, `--mode` o el recurso; `1`, con un mensaje, si la captura está desactivada, el perfil no está configurado o no tiene sesión, el modo no está permitido, un recurso no muestra una interfaz, no hay grabación o no hay OCR, la captura no espera revisión o no hay identidad.

```
coursekit capture login acme-admin
coursekit capture allow PWD U1-S2-M1 --mode browser --profile acme-admin --minutes 30
coursekit capture allow PWD --mode desktop --window "Gestor de contraseñas"
coursekit capture allow PWD U1-S1-M1 --mode browser --profile course
coursekit capture revoke PWD
coursekit capture redact PWD U1-S2-M1
coursekit capture review PWD U1-S2-M1
coursekit capture reject PWD U1-S2-M1 --note "el número de cuenta de la cabecera" --mask "ACME-0042"
coursekit capture approve PWD U1-S2-M1
coursekit capture replay PWD U1-S2-M1
```

## Montaje y entrega

### `coursekit assemble`

Monta una unidad con el backend de su curso (`project.yaml › assembly.backend`, o `course.yaml › assembly.backend` para un curso; `coursekit status CODE` imprime cuál). Con el backend creator planifica, compara y registra el montaje en slxd creator: el agente de montaje aplica el plan con el MCP y registra aquí los ids resultantes, de modo que las ediciones posteriores se convierten en operaciones mínimas. Con el backend html construye la unidad como un paquete SCORM, sin plataforma de por medio. Se rechaza mientras el curso está en pausa. Quién: agentes (el agente de montaje) y personas.

```
coursekit assemble [--unit UNIT] [--version VERSION] [--no-check] [--browser BROWSER] [--lesson LESSON] [--lesson-id LESSON_ID]
                   [--brick-ids BRICK_IDS] [--brick-ids-file BRICK_IDS_FILE] [--keep-ids] [--replace-id REPLACE_ID] [--content] [--content-id CONTENT_ID]
                   [--preview PREVIEW] [--review REVIEW]
                   {plan,diff,applied,checked,link,build,check} code
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `action` | `plan`, `diff`, `applied`, `checked`, `link`, `build`, `check` | `plan`, `diff`, `applied`, `checked` y `link` son del backend creator; `build` y `check` son del backend html. Ver más abajo. |
| `code` | código o carpeta del curso | Curso. |
| `--unit UNIT` | número de unidad | Unidad que montar. Obligatorio en `plan`, `diff`, `applied`, `checked` y `link` (código de salida 2 si falta); opcional en `build` y `check`, que sin él toman todas las unidades. Código de salida 1 si la unidad no existe. |
| `--version VERSION` | texto, por ejemplo `1.0` (`build`) | Versión del paquete. Con ella, `build` además juega la unidad (`check`) y, si no tiene errores, escribe el zip en `courses/<CODE>/delivery/`; sin ella, solo la vista previa. |
| `--no-check` | indicador (`build`) | Con `--version`, escribir el zip sin jugar antes la unidad. |
| `--browser BROWSER` | ruta al ejecutable (`build`, `check`) | El navegador con el que se juega la unidad; por defecto el Google Chrome instalado y, si no, Microsoft Edge. |
| `--lesson LESSON` | clave de lección del plan (`applied`) | Lección que registrar. |
| `--lesson-id LESSON_ID` | id de la lección en creator (`applied`) | Id de esa lección en creator. |
| `--brick-ids BRICK_IDS` | ids separados por comas; por defecto vacío (`applied`) | Ids de los bricks en el orden del plan; su número debe coincidir con los bricks de la lección. |
| `--brick-ids-file BRICK_IDS_FILE` | ruta (`applied`) | Un fichero con los ids de los bricks (separados por comas, espacios o líneas) en lugar de `--brick-ids`, cuando la lista es demasiado larga para la línea de órdenes. |
| `--keep-ids` | indicador (`applied`) | Conserva los ids de bloque ya registrados de la lección, en sus posiciones, y toma las huellas nuevas del plan: para cuando los bloques solo se actualizaron en su sitio (`update_brick` conserva sus ids). Necesita el mismo número de bloques que el plan y, sin `--lesson-id`, conserva el registrado. |
| `--replace-id REPLACE_ID` | `VIEJO=NUEVO`, separados por comas (`applied`, con `--keep-ids`) | El id nuevo de un bloque que se borró y se añadió de nuevo. |
| `--content` | indicador (`applied`) | Registra el título del contenido como aplicado (tras renombrar el contenido en creator) en lugar de una lección. |
| `--content-id CONTENT_ID` | id del contenido en creator (`link`) | Id del contenido de la unidad en creator. |
| `--preview PREVIEW` | URL (`link`) | Enlace de vista previa en vivo de la unidad, sin comentarios. |
| `--review REVIEW` | URL (`link`) | Enlace de revisión de la unidad: aquel donde comenta el cliente. |

`link` necesita al menos una de las opciones `--content-id`, `--preview` y `--review` (código de salida 2 si no se da ninguna).

Cada backend rechaza las acciones del otro, con código de salida 1 y antes de leer la unidad:

```
PWD se monta con el backend html: `plan` es del backend creator; usa `coursekit assemble build`
PWD se monta con el backend «creator»: `build` es del backend html (project.yaml › assembly.backend o course.yaml › assembly.backend)
```

El primero es la respuesta a `plan`, `diff`, `applied` o `link` en un curso del backend html; el segundo, a `build` en un curso del backend creator.

Acciones del backend creator:

- `plan`: convierte `content.md` y `assessment.md` en el plan de lecciones y bricks y escribe `courses/<CODE>/assembly/unit-NN.plan.json`. El mismo Markdown da siempre el mismo plan. Imprime avisos y errores y `plan assembly/unit-NN.plan.json: N lecciones, M bricks (tipos)`. Con errores no escribe nada y termina con código 1. Las claves y palabras de las directivas son las del idioma del curso (`pregunta:` en un curso en español, `question:` en uno en inglés); una clave del otro idioma es un error que nombra su idioma y enumera las claves válidas ([08-assembly-and-delivery.md](08-assembly-and-delivery.md#qué-contiene-el-plan)).
- `diff`: imprime, como JSON, las operaciones que ponen creator al día con el plan: por lección `create`, `update`, `unchanged` o `delete`, con las operaciones `add`, `update`, `delete`, `rename_lesson` y `update_quiz`. Necesita el plan.
- `applied`: registra lo que ahora hay en creator (`unit-NN.applied.json`): una lección con `--lesson`, `--lesson-id` y `--brick-ids`, o el título del contenido con `--content`. Código de salida 2 cuando faltan `--lesson` y `--lesson-id` y no se da `--content`. Cuando todas las unidades coinciden con su plan y el curso está en `media`, el curso pasa a `assembly`. `assembly/*.json` (`unit-NN.plan.json`, `unit-NN.applied.json`) los escribe `coursekit assemble` y nunca se editan a mano: los permisos que se generan para Claude Code deniegan editarlos.
- `checked`: registra, en `unit-NN.applied.json`, que las comprobaciones de cierre del montaje (accesibilidad, texto frente al `.md`, instantánea, enlaces y versión de revisión) se hicieron sobre lo que ahora hay en creator. Código de salida 1 mientras lo registrado no coincida con el plan. Un `applied` posterior que cambie los bloques registrados las deja pendientes otra vez. `coursekit handoff` no entrega una unidad con las comprobaciones pendientes: lanza al agente de montaje solo para el cierre (un montaje que se paró antes de hacerlo, o registrado a mano). Igual que `applied`, pasa un curso de `media` a `assembly` cuando todas las unidades están en sincronía: así llega un curso reabierto que no tiene nada que aplicar.
- `link`: guarda el id del contenido de creator en `course.yaml › units[N].content_id`, y los enlaces de vista previa y de revisión en `course.yaml › units[N].links` (`preview`, `review`). Los enlaces sobreviven a [`coursekit sync`](#coursekit-sync) y alimentan la revisión del cliente (`coursekit client send`) y el catálogo. Cada opción dada sustituye al valor anterior; las que no se dan se conservan.

Acciones del backend html:

- `build`: construye cada unidad (la de `--unit` o todas, por orden) en `courses/<CODE>/assembly/html/unit-NN/`, una carpeta que se abre desde el disco en un navegador (`index.html`, `assets/styles.css`, el reproductor empaquetado `assets/player.js`, los recursos producidos en `media/` e `imsmanifest.xml`). La carpeta se rehace desde cero cada vez y el `.gitignore` del proyecto la ignora (`courses/*/assembly/html/`). El contenido es el mismo `content.md` y `assessment.md` que lee el backend creator, convertido al mismo plan, con los recursos `produced` (o `uploaded`) copiados en el paquete. Los estilos son la maqueta base del paquete, los tokens del curso, `theme/maqueta.css`, `courses/<CODE>/theme/maqueta.css` y `components/*.css`; el reproductor empaqueta los `components/*.js` del proyecto ([04-configuration.md](04-configuration.md#ficheros-del-backend-html)). El estándar SCORM sale de `delivery.yaml › export.standard` y los ajustes del cuestionario (nota para aprobar, intentos) del curso. Con `--version X.Y` escribe además el zip `courses/<CODE>/delivery/<nombre de delivery.yaml › file_name>` (por ejemplo `PWD-U01-v1.0-scorm12.zip`, el nombre que imprime `coursekit delivery name`), con `imsmanifest.xml` el primero en la raíz, listo para `coursekit delivery add`. La primera construcción prepara el constructor (`npm install` de `@studiolxd/scorm` y `esbuild` en el almacén) si `coursekit setup` no lo ha hecho todavía. Cuando todas las unidades del curso están construidas y el curso está en `media`, pasa a `assembly` e imprime `todas las unidades están construidas: el curso pasa a assembly`.

- `check`: juega cada unidad construida (la de `--unit`, o todas; una unidad aún sin construir se construye antes) como lo haría el alumno en una plataforma e informa de lo que no funciona. Sin navegador solo comprueba que el paquete contiene todos los ficheros a los que apuntan la página y sus estilos. Con él (el Chrome o el Edge instalados, manejados sin ventana por Playwright; la primera vez prepara el verificador, `npm install` de `playwright-core` y `axe-core` en el almacén) juega la unidad dentro de la página de [`coursekit preview`](#coursekit-preview), cuyo LMS simulado rechaza lo que rechazaría una plataforma estricta, y comprueba: que no hay errores en la consola ni ficheros que no cargan; cada lección con axe (las infracciones `critical` y `serious` son errores; el resto, avisos); que cada prueba, respondida bien y tras el mejor camino de sus simulaciones evaluables, manda al SCORM la nota que debe; que en una unidad sin prueba sus simulaciones evaluables le dan la nota que deben; que cada camino de cada simulación (los de [`coursekit paths`](#coursekit-paths)) se puede jugar y acaba donde debe con sus puntos; que tras cada camino los bloques adaptativos muestran la rama que pide su condición; que el LMS no rechaza ningún valor; que el estado guardado cabe en el estándar (aviso desde el 80 %); y que al salir y volver a entrar la unidad sigue donde estaba. Escribe los errores (`ERROR …`) y avisos (`AVISO …`) y `unidad N: L lecciones, T prueba(s), S simulación(es) y P camino(s) jugados — E error(es), W aviso(s)`; sin navegador, `unidad N: comprobados solo los ficheros — …` y un aviso que dice por qué. Ver [Comprobar el paquete](08-assembly-and-delivery.md#comprobar-el-paquete).

Salida de `build`, por unidad: los avisos (`AVISO …`: por ejemplo un recurso producido cuyo fichero no existe, o la imagen de un gráfico etiquetado que todavía no está producida; un marcador sin fichero producido se queda en la página como una nota visible), después `unidad N: F ficheros en courses/<CODE>/assembly/html/unit-NN` y, con `--version`, `paquete <nombre> (<tamaño>)` o, sin ella, `vista previa: coursekit preview <CODE> (con LMS simulado), o abre courses/<CODE>/assembly/html/unit-NN/index.html en el navegador`. Abierta desde el disco, sin LMS, la carpeta guarda el estado del alumno solo en memoria: [`coursekit preview`](#coursekit-preview) la juega con un LMS simulado.

`build` se detiene en la primera unidad que no se puede construir (código de salida 1, los problemas por stderr tras `coursekit:`, uno por línea) y no empaqueta nada de ella. Los problemas son:

- Los errores del plan, los mismos que da `coursekit assemble plan` (una clave de directiva en el idioma equivocado, una pregunta sin opciones, etcétera).
- `<lección>: <BRICK>: este componente no está disponible en el backend html`, por una directiva del registro del proyecto que el backend no sabe dibujar (un brick añadido solo para creator). `coursekit verify` indica lo mismo.
- `el paquete no contiene N palabra(s) del contenido: …`: la construcción compara las palabras que lee el alumno en `content.md` y `assessment.md` con las de la página, y una línea que el formato no dibuja (por ejemplo una pregunta sin su clave `pregunta:`) aparece aquí. Corrige el Markdown, nunca la salida.
- ``no se pudo preparar el constructor (npm install de @studiolxd/scorm y esbuild): comprueba Node y npm con `coursekit doctor` ``, cuando falta `npm` o la instalación falla.
- `ha fallado esbuild al empaquetar el reproductor: …`, con el principio de la salida de esbuild (por ejemplo un error en un fichero de `components/*.js`).

Con `--version`, `build` pasa `check` a la unidad antes de escribir el zip (salvo `--no-check`): con errores los escribe junto a `la comprobación ha encontrado errores: no se escribe el paquete (corrígelos, o --no-check para escribirlo igualmente)`, no escribe el zip de esa unidad y el código de salida es 1. Si la unidad no se puede jugar (no hay navegador), el aviso lo dice y el zip se escribe.

Códigos de salida: `0` cuando se construyeron todas las unidades (y, con `check` o `--version`, pasaron la comprobación); `1` por los problemas anteriores, por una comprobación con errores, por una unidad que no existe, por una acción que rechaza el backend o por un curso en pausa; `2` para `plan`, `diff`, `applied` o `link` sin `--unit`, y para `applied` o `link` sin sus opciones.

```
coursekit assemble plan PWD --unit 1
coursekit assemble build PWD --unit 1
coursekit assemble build PWD --version 1.0
```

### `coursekit preview`

Juega las unidades de un curso con el backend html como lo haría el alumno en una plataforma, con un LMS simulado. Quién: los dos (quien construye el paquete y quien revisa). Ver [Vista previa con LMS simulado](08-assembly-and-delivery.md#vista-previa-con-lms-simulado).

```
coursekit preview [--unit UNIT] [--build] [--port PORT] [--no-open] code
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código o carpeta del curso | Curso que se juega. |
| `--unit UNIT` | número; por defecto: la primera unidad | La unidad que se abre primero; si no está construida, se construye. |
| `--build` | indicador | Construir antes las unidades: todas, o la de `--unit`. |
| `--port PORT` | número; por defecto: `8765` | Puerto local del servidor (`127.0.0.1`); si está ocupado, uno libre. |
| `--no-open` | indicador | No abrir el navegador: solo escribe la dirección. |

Escribe `vista previa en http://127.0.0.1:8765/` y sirve hasta Ctrl+C. Códigos de salida: `0` al pararla; `1` con un curso del backend creator (usa la vista previa de creator), una unidad que no existe o una construcción que falla.

```
coursekit preview PWD --unit 2
```

### `coursekit directives`

Compara el registro de directivas (`coursekit config directives`) con el catálogo de bricks de creator. Úsalo para saber si creator añadió o retiró tipos de brick. Quién: agentes (el agente de montaje, mediante `/sync-directives`) y personas.

```
coursekit directives {check} file
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `action` | `check` | La única acción. |
| `file` | ruta | JSON guardado de la herramienta de creator `list_brick_types` (por ejemplo `.cache/list_brick_types.json`). |

Imprime `NUEVO <brick> [categoría] <cuándo usarlo>` por cada brick de creator que no es una directiva ni figura en `not_directives`, y `RETIRADO <brick> ...` por cada entrada del registro cuyo brick ya no existe. Imprime `ok: el registro de directivas coincide con creator (N bricks)` y termina con 0 cuando no hay diferencias; si las hay, código de salida 1. Si `FILE` no existe o no es un resultado de `list_brick_types`, se detiene con un mensaje y código de salida 1.

```
coursekit directives check .cache/list_brick_types.json
```

### `coursekit delivery`

Comprueba que un curso puede entregarse, registra un paquete SCORM entregado en `course.yaml › deliveries`, o imprime el nombre de fichero que debe tener un paquete. Quién: agentes (el agente de montaje) y personas.

```
coursekit delivery [--file FILE] [--job JOB] [--snapshot SNAPSHOT] [--unit UNIT] [--version VERSION] [--url URL] {add,name,check,download} code
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `action` | `add`, `name`, `check`, `download` | Registrar un paquete, imprimir el nombre de fichero esperado, comprobar que el curso puede entregarse o descargar un paquete exportado. |
| `code` | código o carpeta del curso | Curso. |
| `--unit UNIT` | número de unidad (obligatorio en `add` y `name`) | Unidad del paquete. |
| `--version VERSION` | texto (obligatorio en `add` y `name`), por ejemplo `1.0` | Versión de la entrega. |
| `--file FILE` | ruta (`add`) | El `.zip` descargado; una ruta relativa se toma desde la carpeta actual. Debe estar directamente dentro de `courses/<CODE>/delivery/`. Código de salida 2 si falta. |
| `--job JOB` | texto (`add`) | Id del trabajo de exportación de creator. No se usa con el backend html. |
| `--snapshot SNAPSHOT` | texto (`add`) | Id de la instantánea de creator desde la que se exportó el paquete. No se usa con el backend html. |
| `--url URL` | dirección `https://` (`download`) | El `downloadUrl` del trabajo de exportación. Código de salida 2 sin ella. |

Con el backend html el paquete no se exporta desde una plataforma: `coursekit assemble build CODE --unit N --version X.Y` lo escribe en `courses/<CODE>/delivery/` con el nombre que imprime `name`, y `add` lo registra sin `--job` ni `--snapshot`.

`check` imprime que el curso puede entregarse, o se niega indicando el motivo (código de salida 1); cuando el curso está en un estado en el que la entrega no suele empezar (por ejemplo `media`) imprime un aviso en su lugar y termina con 0. `name` y `add` se niegan en los mismos casos, antes de hacer nada: el curso está en pausa, o la revisión del cliente es obligatoria y no está aprobada. `add` y `name` sin `--unit` o sin `--version` terminan con código 2.

La revisión del cliente es obligatoria cuando `delivery.yaml › client_review.required` es `true` (por defecto `false`; se puede sustituir para todo el proyecto en `config/delivery.yaml` y por curso en `course.yaml › delivery`). Entonces el curso necesita al menos una ronda en `course.yaml › client_review` y la última debe estar `approved` u `omitida` (`skipped`); el mensaje dice si no se abrió ninguna ronda, si el cliente pidió cambios o si aún no ha respondido. Consulta [`coursekit client`](#coursekit-client).

`download` guarda el paquete de un trabajo de exportación (su `downloadUrl`, una dirección `https://` que caduca) como `courses/<CODE>/delivery/<nombre>`, con el nombre que imprime `name`, comprueba que es un zip válido con `imsmanifest.xml` en su raíz e imprime su ruta, lista para `add`; una descarga fallida o inválida no deja fichero. Existe para que el agente de montaje no necesite `curl`, que una sesión sin interfaz no puede ejecutar. Se niega en los mismos casos que `name` y `add`.

`name` construye el nombre a partir de `delivery › file_name` (por defecto `{code}-U{unit:02d}-v{version}-{standard}.zip`, por ejemplo `PWD-U01-v1.0-scorm12.zip`). `add` comprueba que el fichero es un zip válido con `imsmanifest.xml` en su raíz y que está en la carpeta de entrega, y registra versión, unidad, fecha, firmante, estándar, nombre de fichero, SHA-256, trabajo e instantánea. Un paquete válido siempre se registra. Cuando todas las unidades tienen un paquete de la misma versión y el curso estaba en `assembly` o `client_review`, el curso pasa a `delivered`; si faltan unidades imprime las que quedan. En cualquier otro estado (por ejemplo `media`) el paquete se registra y un aviso dice que el curso no se marca como entregado. Código de salida 1 ante un paquete no válido, una carpeta incorrecta, una unidad desconocida, un curso en pausa o una revisión del cliente obligatoria que falta.

```
coursekit delivery check PWD
coursekit delivery download PWD --unit 1 --version 1.0 --url "https://…/download?t=…"
coursekit delivery add PWD --unit 1 --version 1.0 --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip --job job-123 --snapshot snap-9
```

### `coursekit publish`

Replica los cursos en la carpeta compartida y escribe allí el catálogo. El espejo es una copia de solo lectura de git: todo lo que se edite en él se sobrescribe en la siguiente publicación. Quién: ambos (también lo ejecutan los hooks de git).

```
coursekit publish [--check] [--only-if-configured] [code]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `code` | código de curso; por defecto: todos los cursos | Publica solo ese curso. Código de salida 1 si no existe. |
| `--check` | indicador | Solo informa de la configuración del espejo: proveedor, carpeta, si se pueden construir enlaces. No copia nada; código de salida 0. |
| `--only-if-configured` | indicador | No hace nada, en silencio y con código 0, cuando no hay espejo (proveedor `none` o `MIRROR_DIR` sin definir), para los hooks de git. Un `MIRROR_DIR` que apunta a una carpeta que no existe sigue fallando con código de salida 1. |

El espejo se define con `project.yaml › mirror` (proveedor y dirección web) más `MIRROR_DIR` en `.env` (ruta local). Por cada curso copia `course.yaml`, `design/`, `content/`, `reviews/` y `delivery/` a `<MIRROR_DIR>/courses/<CODE>/`, solo cuando el contenido cambió, elimina los ficheros que ya no existen en git (registrados en `.published.json`) y nunca borra los paquetes de `delivery/`. Después escribe el Excel del catálogo en la raíz del espejo. Imprime una línea por cada curso que cambió y la línea del catálogo escrito en el espejo. Con `mirror.provider: none` imprime `sin carpeta espejo (project.yaml › mirror.provider: none): nada que publicar` y termina con 0, porque los comandos de los agentes lo llaman en todos los proyectos. Con un proveedor pero sin `MIRROR_DIR`, o con una carpeta que no existe, termina con código 1.

Antes de tocar el espejo actualiza también el catálogo del proyecto en `courses/` (igual que `coursekit catalog`; imprime antes su línea `escrito courses/... (N cursos, M unidades)`, o `... sin cambios` cuando sus datos no han cambiado desde la última escritura, salvo con `--only-if-configured`, donde no imprime nada de eso), así que funciona también en proyectos sin espejo.

Rara vez hace falta ejecutarlo a mano: cuando el proyecto tiene carpeta espejo, los comandos que cambian un curso lo publican al terminar (mira [Publicación automática](08-assembly-and-delivery.md#publicación-automática)).

```
coursekit publish PWD
```

### `coursekit catalog`

Escribe el Excel de seguimiento de todos los cursos (hojas Cursos, Unidades e Información), construido a partir de cada `courses/*/course.yaml`. La hoja Unidades incluye, por unidad, el id del contenido de creator y los enlaces «Enlace compartido» (el de vista previa) y Review como hipervínculos (de `course.yaml › units[N].links`). Es un fichero generado: no lo edites a mano. Quién: ambos.

```
coursekit catalog [--output OUTPUT]
```

| Argumento | Valores / por defecto | Significado |
|---|---|---|
| `--output OUTPUT` | ruta; por defecto `courses/course-catalog.xlsx` en un proyecto en inglés y `courses/catalogo-cursos.xlsx` en los demás (el idioma es `ui_language`, si no `content_language`) | Fichero que escribir. |

Imprime `escrito <ruta> (N cursos, M unidades)`; siempre escribe (la actualización automática tras otros comandos solo escribe cuando los datos cambiaron). `coursekit publish` escribe el mismo catálogo en la carpeta espejo, y dice `sin cambios` cuando no tiene nada nuevo que escribir.

```
coursekit catalog --output build/catalog.xlsx
```

## Comandos de barra y la CLI que usan

Los comandos de barra viven en `src/coursekit/agentkit/commands/` y `coursekit agents` los genera en cada herramienta de IA. Una persona los escribe en el chat de su herramienta de IA, o los lanza desde la terminal con `coursekit run <name> <arguments>`. Los ejecuta el agente del rol indicado. Los agentes nunca firman ni registran las decisiones del cliente: `/approve-design` y `/approve-unit` solo preparan la firma, y `coursekit client`, `coursekit hold` y `coursekit resume` son para personas.

| Comando de barra | CLI que usa | Rol | Quién puede ejecutarlo |
|---|---|---|---|
| `/new-course "<title>" <hours> [--code ABC101] [--approach expository|decision-based] [--no-intro] [--no-summary] [--no-material] [notas]` | `coursekit new`, `coursekit brief`, `coursekit theme show` | `design` | Personas, desde la herramienta de IA o con `coursekit run new-course`. El agente nunca firma ni hace commit. Si falta `--approach` y el curso es nuevo, el agente pregunta qué enfoque quieres (expositivo o basado en decisiones) antes de crearlo. Si el curso ya existe (handoff lo crea antes), se salta `coursekit new` y diseña sobre él. Cuando el proyecto no tiene tokens del tema, su resumen indica a la persona que ejecute `/define-theme`. Si no hay material, el agente pregunta antes de diseñar (salvo con `--no-material`) y, si sigues sin él, marca el temario como suposición. |
| `/design-change <CODE> <cambios>` | `coursekit brief`, `coursekit design`, `coursekit publish` | `design` | Personas. El diseño se aplica en slxd o en `design/design.yaml` (diseño local); un diseño ya firmado debe firmarse de nuevo. |
| `/approve-design <CODE>` | `coursekit design` (diseño local), `coursekit sync --check`, `coursekit publish`; después la persona ejecuta `coursekit approve design <CODE> --yes` | `design` | El agente lo prepara; solo una persona firma. |
| `/define-theme [CODE]` | `coursekit theme show`, `coursekit theme import` | `design` | Personas, o el agente de diseño. Con el backend creator elige o adapta el tema en la plataforma, guarda `get_theme` en `.cache/theme/get_theme.json` y deriva los tokens. Con el backend html no hay tema de plataforma: escribe o adapta `theme/maqueta.css` y ejecuta `coursekit theme import theme/maqueta.css`. Sin código define el tema del proyecto; con código, el tema propio de ese curso. Nunca edita `tokens.json` a mano. |
| `/write-unit <CODE> [N]` | `coursekit status`, `coursekit verify`, `coursekit outline`; lo lanza `coursekit write` | `writer` | Personas (`coursekit write`) o el agente de ese rol. Nunca `coursekit approve`. |
| `/review-unit <CODE> <N>` | `coursekit verify`, `coursekit brief`, `coursekit outline`, `coursekit reviewed`; lo lanza `coursekit review` | `reviewer` | Personas (`coursekit review`) o el agente de ese rol. |
| `/update-unit <CODE> <N> [--apply]` | `coursekit verify`, `coursekit brief`, `coursekit config`; lectura y búsqueda web | `reviewer` | Personas (`coursekit run update-unit CODE N`) o el handoff, cuando `update.mode` no es `off`. |
| `/approve-unit <CODE> <N>` | `coursekit verify`; después la persona ejecuta `coursekit approve content <CODE> --unit <N> --yes` | `reviewer` | El agente lo prepara; solo una persona firma. |
| `/produce-media <CODE> [id de recurso]` | `coursekit media extract`, `coursekit media plan`, `coursekit media set`, `coursekit voice`, `coursekit tts`, `coursekit subtitles`, `coursekit theme show` | `media` | Personas, o el agente multimedia. Avisa a la persona de lo que va a producir antes de gastar créditos de APIs de pago. Si los tokens faltan o no están derivados del tema de la plataforma, se detiene e indica a la persona que ejecute `/define-theme`. |
| `/assemble <CODE> [N]` | creator: `coursekit assemble plan`, `diff`, `applied`, `link`, `coursekit theme show`; html: `coursekit assemble build`, `coursekit theme show` | `assembly` | Personas, o el agente de montaje. Necesita el diseño firmado y las unidades `approved`. Carga la skill `creator-assembly` o la `html-assembly` según el backend del curso. Con creator aplica el tema a los contenidos con `set_content_theme`, con el id que da `coursekit theme show --course <CODE>`; con html construye la vista previa de cada unidad (`assembly/html/unit-NN/`) y dice a la persona qué revisar en ella. |
| `/client-feedback <CODE> [N]` | `coursekit outline`, `coursekit verify`, `coursekit assemble plan`, `diff`, `applied` | `assembly` | Personas, o el agente de montaje. Lee los comentarios del cliente en creator, aplica en el `.md` los cambios acordados, recarga, publica una nueva versión de revisión y responde a cada comentario. Nunca ejecuta `coursekit client`: la ronda la registra la persona. |
| `/deliver <CODE> [versión]` | `coursekit delivery check`, `coursekit config delivery`, `coursekit delivery name`, `coursekit delivery download`, `coursekit delivery add`; html: `coursekit assemble build` | `assembly` | Personas, o el agente de montaje. Se rechaza mientras el curso está en pausa o falta la revisión del cliente exigida. Con el backend html no hay exportación en una plataforma: para cada unidad ejecuta `coursekit assemble build <CODE> --unit N --version X.Y` y después `coursekit delivery add` sin `--job` ni `--snapshot`. |
| `/course-status [CODE]` | `coursekit status` | `design` | Cualquiera. |
| `/sync-directives` | `coursekit directives check`, `coursekit config directives` | `assembly` | Personas, o el agente de montaje. |

Siguiente: [04-configuration.md](04-configuration.md)
