# Primeros pasos

Instala coursekit, crea un proyecto con `coursekit init` y lanza tu primer curso.

## Requisitos

| Necesitas | Para qué |
|---|---|
| macOS, Windows o Linux | coursekit funciona en los tres |
| [uv](https://docs.astral.sh/uv/) | instala coursekit y trae el Python adecuado (3.12 o 3.13) |
| git | `init` ejecuta `git init`; las aprobaciones se confirman (commit) a nombre de quien firma; los hooks del proyecto lo usan |
| Una herramienta de IA: Claude Code (`claude`), opencode o Codex (`codex`) | los agentes que redactan, revisan, producen y montan. Hace falta al menos una para trabajar los cursos |
| La URL de tu servidor MCP de SLXD Creator | el diseño instruccional se hace siempre en creator; con el backend creator, el montaje y la entrega se apoyan también en él (mira la nota sobre los backends más abajo) |
| Node y npm (opcionales) | descargan los enlaces web de `brief/links.md`; los usa Remotion para los vídeos y, en los proyectos que montan con el backend html, sirven para preparar el constructor de paquetes. `coursekit setup --media` puede instalar Node |

Todo lo demás (ffmpeg, voces, claves de API) es opcional y solo importa para producir multimedia: mira [Multimedia](07-media.md).

## Instalación

coursekit aún no está en PyPI. Instálalo desde el repositorio:

```bash
uv tool install git+https://github.com/studiolxd/coursekit
coursekit --version
```

Para probarlo desde un clon, con tus cambios aplicados al instante (instalación editable):

```bash
git clone https://github.com/studiolxd/coursekit
uv tool install --editable ./coursekit
```

El paquete se llama `slxd-coursekit`; el comando es `coursekit`. Para actualizarlo:

```bash
uv tool upgrade slxd-coursekit
```

Si el shell no encuentra `coursekit` tras instalarlo, ejecuta `uv tool update-shell` y abre una terminal nueva.

### Desinstalar

`coursekit setup` puede instalar cosas fuera de tus proyectos: las herramientas de multimedia, una voz de borrador, las dependencias de Remotion y, si lo aceptas, líneas en los ficheros de tu terminal. Quítalas **primero**, mientras el comando todavía existe, y después quita el paquete:

```bash
coursekit uninstall --dry-run      # solo muestra lo que quitaría
coursekit uninstall                # pregunta, grupo a grupo, antes de quitar
uv tool uninstall slxd-coursekit
```

`coursekit uninstall` quita lo que `setup` anotó en el almacén de coursekit (mira [Dónde están las herramientas](07-media.md#dónde-están-las-herramientas)): las dependencias de Node que comparten los proyectos, las herramientas de multimedia instaladas con uv, los ficheros de voz que descargó y las líneas que añadió a los ficheros de tu terminal. Los paquetes del sistema (`ffmpeg`, `node`, `vhs`, `asciinema`) solo se listan, con el comando para quitarlos tú, porque otros programas pueden usarlos. Tus proyectos se quedan como están: carpetas, `.env` y cursos. Si quieres que desaparezcan también los ficheros generados de un proyecto, borra a mano `.claude/`, `.opencode/`, `.codex/`, `.coursekit/` y `tools/`. Sus opciones están en [Comandos](03-commands.md#coursekit-uninstall) y la respuesta corta, en las [Preguntas frecuentes](09-troubleshooting.md#preguntas-frecuentes).

## Crear un proyecto

Un proyecto es una carpeta con un `project.yaml` en su raíz. Reúne todos los cursos de un cliente o de un equipo y se versiona en git.

```bash
coursekit init acme-courses
```

Si lo ejecutas en una terminal, arranca un asistente corto. Pulsa Intro para aceptar el valor entre paréntesis. La primera pregunta es bilingüe; en cuanto la respondes, el asistente te habla en tu idioma.

| # | Pregunta | Para qué se usa la respuesta | Opción |
|---|---|---|---|
| 1 | `Idioma / Language` (`es`/`en`) | idioma de la interfaz (`project.yaml › ui_language`): los mensajes de coursekit y lo que te dicen los agentes, y todo lo que pregunta el asistente a partir de aquí; también se guarda en `.env` como `COURSEKIT_LANG` | `--ui-language` |
| 2 | Idioma de los cursos | idioma del contenido (`project.yaml › content_language`): formato del contenido, títulos de apartado, reglas de redacción de los agentes. Por defecto, el idioma de la interfaz que acabas de elegir | `--language` |
| 3 | Nombre del proyecto | `project.yaml › name`, que ven los agentes. Por defecto, el nombre de la carpeta | `--name` |
| 4 | Cliente | `project.yaml › client` (por ejemplo `ACME`) | `--client` |
| 5 | Tono | tono de redacción para los agentes (texto libre, puede quedar vacío) | `--tone` |
| 6 | Tratamiento | cómo se trata a quien aprende: `tu` o `usted` en español, `you` en inglés | `--address` |
| 7 | Backend de montaje | `SLXD Creator` o `HTML`: dónde se monta el curso (`project.yaml › assembly.backend`; mira las notas más abajo). Por defecto, Creator | `--backend creator\|html` |
| 8 | URL del servidor MCP de slxd | se pregunta con cualquiera de los dos backends. `https://<tenant>.slxd.app/mcp/creator`; déjala vacía para ponerla después. Debe empezar por `http://` o `https://` | `--mcp-url` |
| 9 | Carpeta espejo | carpeta compartida donde se publican los cursos y el catálogo: `sharepoint`, `onedrive`, `google-drive`, `nextcloud`, `folder` o `none` | `--mirror` |
| 10 | Ruta local de la carpeta sincronizada | solo si la carpeta espejo no es `none`. Se guarda en `.env` como `MIRROR_DIR` (es personal). Si la ruta aún no existe, avisa | `--mirror-dir` |
| 11 | Dirección web de la carpeta | solo para proveedores distintos de `folder`; opcional, sirve para los enlaces del catálogo (`mirror.url`) | `--mirror-url` |

Notas:

- Un curso se monta de una de dos maneras. Con el **backend creator**, el contenido se carga en SLXD Creator, que lo aloja y exporta los paquetes SCORM. Con el **backend html**, es el propio coursekit quien construye un paquete SCORM por unidad (`coursekit assemble build`), sin plataforma de por medio. La elección es el valor por defecto del proyecto; un curso puede usar el otro (`course.yaml › assembly › backend`), y `coursekit status CODE` muestra cuál se aplica. Mira [Montaje y entrega según el backend](02-workflow.md#montaje-y-entrega-según-el-backend) y [Montaje y entrega](08-assembly-and-delivery.md).
- La URL del MCP se pregunta con los dos backends: el diseño instruccional (matriz, Excel) se hace siempre en creator. Si la omites, el final de `init` te lo recuerda, elijas el backend que elijas: sin ella el diseño no puede conectar con Creator. Pon `platform.slxd.mcp_url` en `project.yaml` y ejecuta `coursekit agents`.
- La carpeta espejo es opcional. Mira [Montaje y entrega](08-assembly-and-delivery.md).

### Uso sin preguntas

Con `--yes` (o cuando no hay terminal, por ejemplo en un script) no se pregunta nada: se usan las opciones y los valores por defecto.

```bash
coursekit init acme-courses --yes --language es --client ACME --mcp-url https://acme.slxd.app/mcp/creator
```

| Opción | Significado |
|---|---|
| `--yes`, `-y` | no pregunta; usa las opciones y los valores por defecto |
| `--no-git` | no ejecuta `git init` |
| `--update` | refresca los ficheros generados de un proyecto existente (mira más abajo) |

Valores por defecto sin el asistente: idioma del curso `es` (usa `--language en` para inglés), `ui_language` igual al idioma del curso, nombre igual al de la carpeta, backend `creator`, carpeta espejo `none`, tratamiento `tu` en español y `you` en inglés. Un `--address` no válido, o un `--mcp-url` que no empiece por `http://` o `https://`, detiene el comando.

Si la carpeta ya tiene un `project.yaml`, `init` se niega y te remite a `--update`.

## Qué crea init

```text
acme-courses/
├── project.yaml            ajustes del proyecto, compartidos y versionados
├── .env                    ajustes personales, nunca se sube a git
├── .env.example            plantilla de .env
├── AGENTS.md  CLAUDE.md    instrucciones para las herramientas de IA del proyecto
├── brief/                  material de referencia de todos los cursos
│   ├── sources/            documentos de cualquier formato
│   ├── links.md            direcciones web
│   └── notes.md            indicaciones generales
├── courses/                una carpeta por curso (vacía hasta que crees uno)
├── config/                 *.example.yaml: todos los valores por defecto, de referencia
├── theme/                  tokens de diseño del theme del proyecto (derivados de la plataforma o, con html, de la hoja de estilos)
├── .agents/                tus sustituciones de skills, comandos y agentes
├── .githooks/              post-merge, post-checkout
├── .claude/                skills, comandos y ajustes para Claude Code
├── .opencode/              skills, comandos y agentes para opencode
├── opencode.json           ajustes de opencode
├── .mcp.json               servidor MCP para Claude Code (solo si diste una URL)
├── .codex/config.toml      servidor MCP para Codex (solo si diste una URL)
└── .coursekit/             skills y docs generados para Codex, y generated.json
```

| Ruta | Para qué sirve |
|---|---|
| `project.yaml` | nombre, cliente, idiomas, tono, tratamiento, backend de montaje, servidor MCP, carpeta espejo y `network.ca_bundles`. Se escribe una vez; desde entonces es tuyo. Mira [Configuración](04-configuration.md) |
| `.env` | tu identidad (`COURSEKIT_USER_NAME`, `COURSEKIT_USER_EMAIL`), `COURSEKIT_LANG`, `MIRROR_DIR`, herramienta y modelo de cada rol, claves de API. Git lo ignora |
| `.env.example` | la plantilla de la que se crea `.env`. Versionada |
| `config/*.example.yaml` | los valores por defecto completos de `rules`, `directives`, `media` y `delivery`, de referencia. **No se leen**: para cambiar algo crea `config/<nombre>.yaml` solo con lo que cambies |
| `brief/` | material de referencia de todos los cursos del proyecto. Cada curso tiene además su propio `brief/`. `coursekit brief` lo convierte para los agentes |
| `courses/` | una carpeta por curso, que crea `coursekit new` (mira [Contenido](06-content.md)) |
| `theme/` | tokens de diseño del theme del proyecto (`theme/tokens.json` y `tokens.css`). No se escriben a mano: `/define-theme` los deriva del theme de la plataforma de maquetación (con el backend html, de la hoja de estilos `theme/maqueta.css`). La producción multimedia los usa; `coursekit theme` trabaja sobre ellos (mira [Theme y tokens de diseño](02-workflow.md#theme-y-tokens-de-diseño) y [Multimedia](07-media.md)) |
| `.agents/` | ficheros con la misma estructura que las skills, comandos y agentes del paquete (`skills/<nombre>/SKILL.md`, `commands/<nombre>.md`, `agents/<nombre>.md`); uno con el mismo nombre sustituye al del paquete |
| `.githooks/` | tras cada pull y checkout, `coursekit agents` refresca los ficheros generados; tras un pull también publica en la carpeta espejo si tienes una configurada |
| `AGENTS.md`, `CLAUDE.md` | instrucciones del proyecto para las herramientas de IA (`CLAUDE.md` remite a `AGENTS.md`) |
| `.claude/`, `.opencode/`, `opencode.json`, `.mcp.json`, `.codex/config.toml` | lo que lee cada herramienta: skills, comandos, el servidor MCP y la regla de que los agentes no pueden ejecutar `coursekit approve` ni `git push` |
| `.coursekit/` | skills y comandos generados para Codex y cualquier otra herramienta, los documentos que leen los agentes y `generated.json`, que anota lo que escribió coursekit para que `init --update` sepa qué has editado tú |

Las carpetas generadas (`.claude/skills`, `.claude/commands`, `.opencode/skill`, `.opencode/command`, `.opencode/agent`, `.coursekit/agents`, `.coursekit/docs`) las ignora git: cada equipo las regenera. Mira [Agentes](05-agents.md).

### Refrescar los ficheros generados

```bash
coursekit init --update      # AGENTS.md, CLAUDE.md, .env.example, .gitignore, ejemplos de config, hooks
coursekit agents             # skills, comandos, agentes y ajustes de las herramientas
```

`init --update` nunca toca `project.yaml` ni las notas de `brief/`. Un fichero generado que hayas editado a mano se conserva y se informa como `conservado (editado a mano, no se actualiza)`.

## Qué hace setup

Al final de `init`, coursekit ejecuta `coursekit setup` por ti. Se puede repetir en cualquier momento. En orden:

1. **`.env`**: se crea a partir de `.env.example` si falta.
2. **Identidad**: tu nombre y tu email, que firman las aprobaciones (`COURSEKIT_USER_NAME`, `COURSEKIT_USER_EMAIL`). La identidad de git solo se sugiere. Sin terminal, este paso se limita a avisar de que falta la identidad: ejecuta `coursekit setup --identity` más tarde.
3. **Red**: si `project.yaml › network › ca_bundles` lista un certificado que existe en tu equipo (un proxy que inspecciona TLS), te ofrece definir `NODE_EXTRA_CA_CERTS` y `UV_NATIVE_TLS=1` para tu usuario.
4. **Hooks de git**: fija `core.hooksPath` en `.githooks` (en Windows, también `core.autocrlf input`). Si ya apunta a otro sitio, lo deja como está.
5. **Herramienta y modelo de cada rol**: `design`, `writer`, `reviewer`, `media` y `assembly`, que se guardan en `.env` como `<ROLE>_AGENT` y `<ROLE>_MODEL`. Propone los valores por defecto y pregunta "¿Usar estos valores?"; responde que no para elegir la herramienta (`claude`, `opencode`, `codex`) y el modelo de cada rol. Por defecto: Claude Code con `opus` para diseño, revisión y multimedia, y `sonnet` para redacción y montaje. Se repite con `coursekit setup --roles`.
6. **Skills, comandos y ajustes de agente**: lo mismo que `coursekit agents`.
7. **Constructor del backend html (solo si el proyecto monta con `html`)**: prepara, una vez por equipo, con qué se construyen los paquetes: `@studiolxd/scorm` (el runtime SCORM) y esbuild, que se instalan con `npm` en el almacén de coursekit y comparten todos los proyectos. Necesita Node y npm; sin npm solo avisa, y si la instalación falla también avisa y `coursekit assemble build` lo intenta de nuevo más tarde. Se repite con `coursekit setup`.
8. **Herramientas de multimedia (opcional)**: pregunta si instalarlas; descarga bastante. Mira más abajo.
9. **Informe de doctor**: la salida de `coursekit doctor`, para que veas qué falta aún (en un proyecto html incluye una línea para el constructor). Mira [Solución de problemas](09-troubleshooting.md).

### Herramientas de multimedia

Si aceptas (o ejecutas `coursekit setup --media` más tarde):

| Sistema | Qué ocurre |
|---|---|
| macOS | `brew install ffmpeg node vhs asciinema` para lo que falte (necesita Homebrew) |
| Windows | `winget` instala ffmpeg, Node y vhs; asciinema no tiene versión para Windows, así que las demos de terminal usan VHS |
| Linux | no se instala nada: imprime la línea `sudo apt install ...` para tu gestor de paquetes y la dirección de VHS |

Después, en todos los sistemas: `piper` y `stable-ts` como herramientas de uv (Python 3.12), una voz de borrador de Piper para el idioma del curso (se guarda en `~/.local/share/piper`, o en `%LOCALAPPDATA%\piper` en Windows, y se fija como `PIPER_VOICE`), un espacio de Remotion en `tools/remotion` (las fuentes se quedan en el proyecto; sus dependencias, `node_modules`, unos 230 MB, se instalan una sola vez por equipo y cada proyecto las enlaza) y, en una terminal, claves de API opcionales (ElevenLabs, Azure Speech, Google TTS, Magnific; Intro omite cada una) que se guardan en `.env`.

Cada herramienta se instala una vez por equipo, no una vez por proyecto: mira [Dónde están las herramientas](07-media.md#dónde-están-las-herramientas).

## Tu primer curso

Al terminar, `init` imprime los siguientes pasos:

```text
Siguiente paso: crea tu primer curso.

Antes de empezar (opcional, pero conviene):
  · Material de partida: deja los documentos en brief/sources/, las URLs en brief/links.md y las indicaciones generales en brief/notes.md. `coursekit brief` los convierte para que los agentes los lean.
  · Valores por defecto del proyecto: mira config/*.example.yaml (reglas, directivas, multimedia y entrega) y, para cambiar alguno, crea config/<nombre>.yaml solo con lo que cambies. `coursekit config` muestra lo que está en vigor.

Después:
  1. Entra en el proyecto:  cd acme-courses
  2. Abre tu herramienta de IA en esa carpeta: claude, opencode, codex
  3. Y lanza:  /new-course "Título del curso" <horas>
  También puedes hacerlo desde aquí, con el agente del rol de diseño:  coursekit run new-course "Título del curso" <horas>
  Para ver dónde estás en cualquier momento:  coursekit status
```

Una herramienta que no esté instalada aparece como `(no instalado)`. En Codex, pide el mismo comando por su nombre: seguirá `.coursekit/agents/commands/new-course.md`.

Si ejecutaste `init` en una terminal y la URL del MCP está puesta, también te ofrece "¿Crear ya tu primer curso con `<herramienta>`?" (la herramienta del rol de diseño, si está instalada). Responde que sí y antes te pregunta si tienes material de partida (documentos, enlaces o indicaciones): si lo tienes, te muestra dónde dejarlo (`brief/sources/`, `brief/links.md`, `brief/notes.md`) y espera a que pulses Enter; si no, el diseño parte sin él y su temario queda marcado como suposición. Después escribe el título del curso y sus horas (`1.5` o `1,5`) y te pregunta si hacer todo el proceso solo (modo handoff, mira [Flujo de trabajo](02-workflow.md#modo-handoff)): con no ejecuta `coursekit run new-course` por ti, con sí ejecuta `coursekit handoff`.

Antes de crear el curso conviene dejar material de referencia en `brief/sources/`, URLs en `brief/links.md` e indicaciones generales en `brief/notes.md`, y ejecutar `coursekit brief`.

### Qué hace /new-course

```text
/new-course "Contraseñas seguras" 2 --code PWD
```

| Argumento | Significado |
|---|---|
| `"Contraseñas seguras"` | título del curso, entre comillas |
| `2` | duración en horas |
| `--code PWD` | código del curso; por defecto es el título en mayúsculas, unido con guiones |
| `--no-intro`, `--no-summary` | unidades sin el apartado de introducción inicial o sin el de resumen final |
| cualquier otro texto | indicaciones libres para el diseño |

El agente de diseño crea el curso (`coursekit new`), convierte el brief, construye una **propuesta** de diseño instruccional en SLXD Creator, la publica con `coursekit publish` y termina con un resumen: unidades, horas, supuestos que comprobar y cómo seguir. Si el proyecto aún no tiene tokens de diseño, el resumen también te dice que ejecutes `/define-theme` antes de producir multimedia. No firma nada. A partir de aquí, sigue el [Flujo de trabajo](02-workflow.md). El diseño se hace en creator con cualquiera de los dos backends; el backend solo importa a partir del montaje.

También puedes crear tú mismo la ficha del curso vacío, sin agente:

```bash
coursekit new "Contraseñas seguras" 2 --code PWD
coursekit status PWD
```

### Define el theme

```text
/define-theme
```

Los gráficos, simulaciones y vídeos de un curso usan los colores y las fuentes de su theme, para que se parezcan al curso. Con el backend creator, el theme vive en la plataforma de maquetación; `/define-theme` (rol de diseño) lista los que hay, te deja elegir o crear uno, lo adapta con los colores y las fuentes de la marca y deriva de él los tokens de diseño del proyecto (`theme/tokens.json` y `tokens.css`). Hazlo una vez, idealmente justo después de `/new-course` y antes de producir multimedia: mientras los tokens no vengan de la plataforma, `coursekit media set --status produced` rechaza infografías, esquemas, GIF animados, simulaciones y vídeos. El theme lo validas tú, como validas el diseño. Con el backend html no hay theme de plataforma: `/define-theme` escribe o adapta la hoja de estilos `theme/maqueta.css` con la marca en sus variables CSS y ejecuta `coursekit theme import theme/maqueta.css`. Mira [Theme y tokens de diseño](02-workflow.md#theme-y-tokens-de-diseño).

### Monta y entrega

Cuando las unidades están firmadas y el multimedia producido, el montaje depende del backend del curso (`coursekit status PWD` lo muestra):

| Backend | Montar | Entregar |
|---|---|---|
| `creator` | `/assemble PWD` carga el contenido en SLXD Creator y te da un enlace de vista previa y otro de revisión por unidad | `/deliver PWD 1.0` exporta de creator un paquete SCORM por unidad |
| `html` | `/assemble PWD` construye cada unidad con `coursekit assemble build PWD --unit N`: una carpeta de vista previa que abres en un navegador (`courses/PWD/assembly/html/unit-01/`) | `/deliver PWD 1.0` construye el zip de cada unidad (`--version 1.0`, en `courses/PWD/delivery/`) y lo registra; no se exporta nada de ninguna plataforma |

Prueba un paquete html en el LMS al que vas a entregar (o en SCORM Cloud) antes de dárselo a nadie. Detalles en [Montaje y entrega según el backend](02-workflow.md#montaje-y-entrega-según-el-backend).

Siguiente: [Flujo de trabajo](02-workflow.md)
