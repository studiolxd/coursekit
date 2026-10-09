# Agentes

Cómo usa coursekit las herramientas de IA para programar: qué herramientas y roles hay, qué genera `coursekit agents` para cada herramienta y cómo lanzar, limitar y personalizar los agentes.

## Herramientas y roles

coursekit trabaja con tres herramientas. No las instala: tienen que estar en tu `PATH` (`coursekit doctor` te dice cuáles faltan).

| Herramienta | Valor en `.env` | Cómo la usas |
|---|---|---|
| Claude Code | `claude` | Abre `claude` en la carpeta del proyecto y escribe comandos con barra, como `/write-unit PWD 1`. |
| opencode | `opencode` | Abre `opencode` en la carpeta del proyecto y escribe los mismos comandos con barra. |
| Codex | `codex` | Abre `codex` en la carpeta del proyecto y pide el comando (por ejemplo «ejecuta /write-unit PWD 1»). Codex no tiene comandos con barra de proyecto: lee el fichero del comando `.coursekit/agents/commands/write-unit.md` y lo sigue. |

Cualquiera de ellas también se puede lanzar por ti con `coursekit write`, `coursekit review` y `coursekit run` (mira más abajo).

El trabajo se reparte en cinco roles. Cada rol tiene una herramienta y un modelo.

| Rol | Qué hace | Comandos con barra que ejecuta | Herramienta por defecto | Modelo por defecto (Claude Code) | Modelo por defecto (opencode) |
|---|---|---|---|---|---|
| `design` | Propuesta y cambios del diseño instruccional; el theme y los tokens de diseño | `/new-course`, `/design-change`, `/approve-design`, `/define-theme`, `/course-status` | `claude` | `opus` | `anthropic/claude-opus-5-5` |
| `writer` | Redacta el contenido de una unidad | `/write-unit` | `claude` | `sonnet` | `anthropic/claude-sonnet-5-5` |
| `reviewer` | Revisión con IA de una unidad redactada | `/review-unit`, `/approve-unit` | `claude` | `opus` | `anthropic/claude-opus-5-5` |
| `media` | Produce y sube los recursos multimedia | `/produce-media` | `claude` | `opus` | `anthropic/claude-opus-5-5` |
| `assembly` | Carga el contenido en creator o construye los paquetes html, trata los comentarios de la revisión del cliente, exporta o registra paquetes, sincroniza directivas | `/assemble`, `/client-feedback`, `/deliver`, `/sync-directives` | `claude` | `sonnet` | `anthropic/claude-sonnet-5-5` |

Codex no tiene modelo propuesto: con `codex`, el modelo es el que Codex trae por defecto salvo que indiques uno. El rol de revisión (`reviewer`) lleva por defecto un modelo distinto del de redacción (`writer`) a propósito: otro modelo detecta más.

## Elegir la herramienta y el modelo de cada rol

Tres formas, de más duradera a puntual:

1. **Guiada**: `coursekit setup --roles` muestra la propuesta, te pide que la confirmes y, si no la aceptas, te pregunta la herramienta y el modelo de cada rol. Con `--yes` (o sin terminal) conserva lo que ya hay en `.env` y rellena los valores por defecto de arriba.
2. **A mano en `.env`** (personal, no se versiona):

   ```bash
   WRITER_AGENT=opencode
   WRITER_MODEL=anthropic/claude-sonnet-5-5
   REVIEWER_AGENT=claude
   REVIEWER_MODEL=opus
   ```

   `<ROLE>_AGENT` es `claude`, `opencode` o `codex` (`claude` si no está definida). `<ROLE>_MODEL` es un identificador que entienda esa herramienta; vacío significa el modelo por defecto de la herramienta. Mira [Configuración](04-configuration.md).
3. **Para un solo lanzamiento**: `--agent TOOL` y `--model MODEL` en `coursekit write`, `coursekit review` y `coursekit run`. `--agent` solo usa el modelo por defecto de esa herramienta, no el de `.env`.

```bash
coursekit roles      # herramienta y modelo vigentes de cada rol (y si la herramienta está instalada)
coursekit doctor     # además comprueba que la herramienta de cada rol esté instalada
```

En la interfaz de opencode el modelo viene de los agentes `writer` y `reviewer` generados (mira más abajo), que lo toman de `WRITER_MODEL` y `REVIEWER_MODEL` cuando ese rol usa opencode; coursekit los regenera cuando lanza un rol con opencode, o ejecuta tú `coursekit agents`. En esa interfaz `--model` no se aplica, y los demás roles (`design`, `media`, `assembly`) usan el modelo por defecto de opencode. Con `--headless`, `--model` siempre se pasa a la herramienta.

## Qué genera `coursekit agents`

```bash
coursekit agents
# agentes: 4 escritos, 51 sin cambios, 0 eliminados
```

El origen es el paquete más tus cambios en `.agents/` (mira más abajo). Cada fichero se renderiza con los valores del proyecto y se copia donde lo lee cada herramienta. También se ejecuta dentro de `coursekit setup` y desde los git hooks del proyecto tras cada pull y cada cambio de rama (una vez que `coursekit setup` los ha activado).

| Contenido | Claude Code | opencode | Codex y cualquier otra herramienta |
|---|---|---|---|
| Skills | `.claude/skills/<name>/SKILL.md` | `.opencode/skill/<name>/SKILL.md` | `.coursekit/agents/skills/<name>/SKILL.md` |
| Comandos con barra | `.claude/commands/<name>.md` | `.opencode/command/<name>.md` | `.coursekit/agents/commands/<name>.md` |
| Agentes | ninguno | `.opencode/agent/writer.md`, `.opencode/agent/reviewer.md` | ninguno |
| Documentos de referencia | `.coursekit/docs/content-format.md` y `.coursekit/docs/slxd-mcp.md` (compartidos por todas las herramientas) | | |
| Instrucciones | `CLAUDE.md` (importa `AGENTS.md`) | `AGENTS.md`, listado en `opencode.json` | `AGENTS.md` |
| Servidor MCP de slxd | `.mcp.json` | `opencode.json` | `.codex/config.toml` |
| Reglas de denegación | `.claude/settings.json` | `opencode.json` | ninguna |

`AGENTS.md` y `CLAUDE.md` los crea `coursekit init` y los actualiza `coursekit init --update`; el resto lo produce `coursekit agents`. Las skills, comandos, agentes y documentos de `.claude/`, `.opencode/` y `.coursekit/` están ignorados por git: se regeneran y nunca se editan a mano. Los ficheros de MCP y permisos (`.mcp.json`, `opencode.json`, `.claude/settings.json`, `.codex/config.toml`) no están ignorados, así que se pueden versionar con el proyecto.

Cómo trata coursekit los ficheros:

- Todo fichero generado lleva un comentario `generated by coursekit agents` y el lugar donde editarlo. Los ficheros con esa marca se sobrescriben cuando cambia el origen y se eliminan cuando el origen desaparece.
- Un fichero de esas carpetas **sin** la marca (uno que hayas escrito tú) no se sobrescribe ni se elimina nunca; `coursekit agents` lo lista como conservado.
- `.mcp.json`, `opencode.json`, `.claude/settings.json` y `.codex/config.toml` se fusionan, nunca se reemplazan: tus otras entradas se quedan.
- Los demás ficheros de la carpeta de una skill (ejemplos, recursos) se copian tal cual junto a su `SKILL.md`.

### Skills

| Skill | Se usa cuando |
|---|---|
| `instructional-design` | Se propone y se cambia el diseño instruccional de un curso en slxd (`/new-course`, `/design-change`, `/approve-design`). |
| `content-writing` | Se redactan el `content.md` y el `assessment.md` de una unidad (`/write-unit`). |
| `content-review` | Se revisa una unidad redactada por otro modelo y se escribe el informe en `reviews/` (`/review-unit`). |
| `theme-definition` | Se elige o se crea el theme del proyecto (o de un curso) en slxd creator, se adapta a la marca y se derivan de él los tokens de diseño con `coursekit theme import` (`/define-theme`). |
| `media-production` | Se producen y se suben los recursos multimedia, con los tokens de diseño del theme (`/produce-media`). |
| `creator-assembly` | Se carga y se recarga el contenido en slxd creator, y se crean los enlaces de vista previa y de revisión de cada unidad (`/assemble`, backend creator). |
| `html-assembly` | Se construye con `coursekit assemble build` el paquete SCORM de cada unidad, se mira la vista previa y se empaqueta una versión (`/assemble`, backend html). Lee los mismos `.md` y los mismos recursos producidos; el resultado nunca se edita a mano. |
| `client-review` | Se leen los comentarios del cliente en los enlaces de revisión, se aplican al `.md` los acordados, se publica una versión nueva de la revisión y se responde a cada comentario (`/client-feedback`). |
| `delivery` | Se exportan (creator) o se construyen (html), se registran y se publican los paquetes SCORM (`/deliver`). |

Cuál de las dos skills de montaje se aplica depende del backend del curso (`assembly.backend` en `project.yaml`, o en `course.yaml`; `coursekit status CODE` lo muestra). La skill `theme-definition` cubre también los dos backends.

Las skills y los comandos leen los números de producción de tu configuración: las palabras por hora, las directivas por hora, las preguntas por objetivo y demás se renderizan desde [Configuración](04-configuration.md); en una skill no se escribe ningún número a mano.

### Comandos con barra

| Comando | Argumentos | Qué hace |
|---|---|---|
| `/new-course` | `"<title>" <hours> [--code ABC101] [--no-intro] [--no-summary] [indications]` | Crea el curso y construye en slxd la propuesta de diseño instruccional para revisión humana. Ejecuta `coursekit theme show` y, si el proyecto no tiene tokens de diseño, te avisa en su resumen de que ejecutes `/define-theme` antes de producir multimedia. |
| `/design-change` | `<CODE> <changes>` | Aplica en slxd los cambios que pidas sobre la propuesta de diseño. |
| `/approve-design` | `<CODE>` | Prepara la firma del diseño y te dice cómo firmarlo. |
| `/define-theme` | `[CODE]` | Define el theme en slxd creator y deriva de él los tokens de diseño de la multimedia. Con el backend html no hay theme de plataforma: escribe o adapta la hoja de estilos `theme/maqueta.css` con la marca en sus variables CSS y ejecuta `coursekit theme import theme/maqueta.css`. Sin código trabaja sobre el theme del proyecto, que heredan todos los cursos; con código, sobre el theme propio de ese curso (`courses/<CODE>/theme/`, anotado en `slxd.theme_id`), que gana para él. Lista los themes de la plataforma, eliges o creas uno (desde cero, desde un preset o como copia), lo adapta con los colores y las fuentes de la marca, guarda el resultado de `get_theme` en `.cache/theme/get_theme.json` y ejecuta `coursekit theme import`. Nunca escribe `tokens.json` a mano. El theme lo validas tú, como validas el diseño. Mira [Theme y tokens de diseño](02-workflow.md#theme-y-tokens-de-diseño). |
| `/course-status` | `[CODE]` | Muestra el estado de los cursos y el siguiente paso. |
| `/write-unit` | `<CODE> [N]` | Redacta una unidad de un curso con el diseño firmado. Sin `N`, redacta todas las unidades pendientes, en orden, en la misma sesión (se detiene en la primera que no verifica). `coursekit write` la lanza con un número: una sesión por unidad. |
| `/review-unit` | `<CODE> <N>` | Revisión con IA de una unidad redactada, con informe en `reviews/`. |
| `/approve-unit` | `<CODE> <N>` | Comprueba que una unidad está lista para la firma editorial y te dice cómo firmarla. |
| `/produce-media` | `<CODE> [asset id]` | Produce los recursos multimedia pendientes y los sube. |
| `/assemble` | `<CODE> [N]` | Carga la skill del backend del curso. Creator: carga en creator el contenido de un curso o una unidad (solo lo que ha cambiado) y aplica el theme del curso a cada contenido (`set_content_theme`, con el id de `coursekit theme show --course CODE`); sin tokens derivados de la plataforma deja el theme por defecto y te avisa de `/define-theme`. Html: construye el paquete de cada unidad con `coursekit assemble build CODE --unit N` y te dice qué comprobar en la vista previa. Sin número de unidad procesa todas en orden. |
| `/client-feedback` | `<CODE> [N]` | Lee los comentarios del cliente en los enlaces de revisión de un curso (o de una unidad), aplica al `.md` los acordados, recarga, publica una versión nueva de la revisión y responde a cada comentario. Nunca abre ni cierra una ronda: eso lo haces tú con `coursekit client`. |
| `/deliver` | `<CODE> [version]` | Empieza con `coursekit delivery check`; después exporta los paquetes SCORM, los registra y los publica en la carpeta espejo. Con el backend html no hay exportación desde ninguna plataforma: para cada unidad ejecuta `coursekit assemble build CODE --unit N --version X.Y` y registra el zip con `coursekit delivery add` sin `--job` ni `--snapshot`. |
| `/sync-directives` | ninguno | Sincroniza el registro de directivas con el catálogo de bricks de creator. |

Cuando escribes un comando con barra en una sesión ya abierta, se aplican la herramienta y el modelo de esa sesión. Los roles de `.env` se aplican cuando coursekit lanza la herramienta por ti. En opencode, `/write-unit` y `/review-unit` seleccionan los agentes `writer` y `reviewer`.

En Codex, esos mismos comandos son ficheros normales. Pídele el comando («ejecuta /assemble PWD») y seguirá `.coursekit/agents/commands/assemble.md`; las skills están en `.coursekit/agents/skills/<name>/SKILL.md`. Cuando coursekit lanza Codex, le pasa esa instrucción él mismo.

## El servidor MCP de slxd

Los agentes hablan con slxd creator mediante un servidor MCP configurado en `project.yaml`. Hace falta con los dos backends de montaje, porque el diseño instruccional (matriz, Excel) se hace siempre en creator; con el backend html, el montaje en sí no lo usa:

```yaml
platform:
  slxd:
    mcp_name: slxd-creator
    mcp_url: https://acme.example.com/mcp/creator
```

`coursekit agents` lo escribe en cada herramienta, solo cuando `mcp_url` está definida:

| Herramienta | Fichero | Entrada |
|---|---|---|
| Claude Code | `.mcp.json` | `mcpServers.<mcp_name>` con `type: http` y la URL |
| opencode | `opencode.json` | `mcp.<mcp_name>` con `type: remote`, la URL y `enabled: true` |
| Codex | `.codex/config.toml` | `[mcp_servers."<mcp_name>"]` con `url` |

Cada persona se autentica con su cuenta de slxd (OAuth) la primera vez que una herramienta usa el servidor. `.codex/config.toml` solo se genera si no existe o si todavía tiene la línea `generated by coursekit agents`; quita esa línea para gestionar el fichero a mano. Sin `mcp_url`, `coursekit doctor` lo indica y el rol de diseño (y, con el backend creator, los de multimedia y montaje) no puede llegar a slxd. Las skills explican cómo llamar a las herramientas que no aparecen listadas directamente (`find_tools`, `tool_schema`, `run_tool`); la referencia está en `.coursekit/docs/slxd-mcp.md`.

## Permisos: qué no pueden hacer los agentes

Los agentes nunca deben firmar nada. Las aprobaciones solo las registra `coursekit approve`, que solo ejecuta una persona; los agentes te dicen qué escribir. Lo mismo vale para las decisiones de personas que anotan otros comandos: `coursekit client` (rondas de revisión del cliente y lo que decidió el cliente) y `coursekit hold` / `coursekit resume` (pausar un curso). El `AGENTS.md` del proyecto también indica a cada herramienta que no haga commit ni push salvo que se lo pidas, que no escriba credenciales en ficheros versionados y que no instale software (te piden que ejecutes `coursekit setup`).

coursekit aplica lo esencial en cada herramienta:

| Herramienta | Denegado por configuración | Dónde |
|---|---|---|
| Claude Code | `coursekit approve`, `coursekit client`, `coursekit hold`, `coursekit resume`, `coursekit reviewed ... --by`, `git push` | `permissions.deny` en `.claude/settings.json` |
| opencode | `coursekit approve`, `coursekit client`, `coursekit hold`, `coursekit resume`, `git push` | `permission.bash` en `opencode.json` |
| Agentes `writer` y `reviewer` de opencode | los mismos cuatro comandos `coursekit`, además `git commit`; cualquier otro comando de shell pregunta antes; `coursekit verify`, `status`, `brief`, `outline`, `config`, `git status` y `git diff` están permitidos (el revisor también puede ejecutar `coursekit reviewed`) | `.opencode/agent/*.md` |
| Codex | nada en la configuración: se apoya en las instrucciones de `AGENTS.md` | |

Los lanzamientos headless añaden sus propios límites (mira más abajo). Las reglas que debes aplicar tú: revisa `git diff` antes de hacer commit y ejecuta `coursekit approve` solo en tu propia terminal.

## Lanzar un agente

### `write` y `review`: unidad a unidad

```bash
coursekit write PWD 1                 # redacta la unidad 1 con el rol writer
coursekit write PWD                   # todas las unidades pendientes, en orden
coursekit review PWD 1                # revisa la unidad 1 con el rol reviewer
coursekit review PWD 1 --full         # unidad completa, aunque ya se revisara
coursekit review PWD 1 --parts "section 4"   # solo esas partes
coursekit write PWD 2 --agent opencode --model anthropic/claude-sonnet-5-5
```

| Opción | Significado |
|---|---|
| `CODE` `[N]` | Código del curso y número de unidad. Sin `N`, todas las unidades pendientes: en `write`, las unidades pendientes o en redacción; en `review`, las unidades ya verificadas. |
| `--agent`, `--model` | Herramienta y modelo para este lanzamiento (sustituyen a `.env`). |
| `--headless` | Ejecuta sin la interfaz de la herramienta (mira más abajo). |
| `--full`, `--parts` | Solo revisión. Por defecto, una unidad ya revisada se vuelve a revisar solo en las partes que han cambiado desde entonces; `--full` revisa la unidad entera y `--parts` nombra las partes. `write` no los acepta. |

Qué hace coursekit en cada lanzamiento:

- Registra al redactor en `units[N].written_with` y al revisor en `reviewed_with` de `course.yaml`, como `herramienta · modelo` (por ejemplo `claude · sonnet`, o `claude · default model`).
- Arranca la herramienta con `/write-unit CODE N` o `/review-unit CODE N` (en Codex, con la instrucción de seguir el fichero del comando).
- Con varias unidades, pasa a la siguiente cuando la herramienta termina bien (interactivo) o cuando la unidad alcanzó el estado esperado (headless), y se detiene en la primera que no: «detenido en la unidad N: corrígela y lanza el comando de nuevo».

### Un revisor distinto del redactor

La revisión vale más cuando la hace otro modelo. Si la herramienta y el modelo del revisor son los mismos que los del redactor de la unidad, coursekit avisa y continúa:

```text
aviso: la unidad 1 se escribió con claude · sonnet, la misma herramienta y modelo que esta revisión; otro modelo detecta más (REVIEWER_AGENT / REVIEWER_MODEL en .env)
```

Si `course.yaml` no dice quién redactó la unidad, el aviso te pide comprobar que no fue el mismo modelo. El comando de revisión también indica al agente revisor que lo mencione al principio del informe, y `coursekit doctor` señala un proyecto cuyos roles de redacción y revisión son la misma herramienta y el mismo modelo.

### `run`: cualquier otro comando

```bash
coursekit run new-course "Strong passwords" 2 --code PWD
coursekit run define-theme
coursekit run assemble PWD
coursekit run deliver PWD 1
coursekit run course-status
coursekit run produce-media PWD --agent opencode --model anthropic/claude-opus-5-5
coursekit run assemble PWD --role design     # lo ejecuta con el agente de otro rol
```

`coursekit run NAME [ARGS]` lanza cualquier comando con el agente de su rol (tabla de arriba). `--role` elige otro rol (`design`, `writer`, `reviewer`, `media`, `assembly`); para un comando que no está en la tabla, el rol por defecto es `design`. `--headless`, `--agent`, `--model` y `--role` pueden ir después del nombre del comando.

### Headless (`--headless`)

Headless ejecuta la herramienta sin su interfaz para que otro agente o una tarea programada pueda lanzarla:

- Se avisa al agente de que nadie puede responderle: no debe hacer preguntas, decide con lo que tiene, deja las dudas anotadas en el contenido o en su informe y termina con un resumen breve de lo que hizo y de lo que queda pendiente.
- La sesión completa va a `.cache/logs/` (ignorado por git): `<CODE>-uNN-write-<fecha>-<hora>.log` o `...-review-...` para las unidades, `<command>-<role>-<fecha>-<hora>.log` para `run`. En Codex hay además un `.last.txt` con su mensaje final.
- coursekit imprime el mensaje final de la sesión y dónde está el log: `unidad 1: reviewed · sesión en .cache/logs/PWD-u01-review-20261009-101500.log`. Si la herramienta falló, añade `· exit N`.
- En `write` y `review`, el código de salida es 0 solo si la unidad alcanzó el estado esperado (redactada: `verified` o posterior; revisada: `reviewed` o `approved`); si no, es el código de salida de la herramienta, o 1.
- La herramienta se ejecuta desde la carpeta del proyecto en una sesión limpia: las variables de entorno que empiezan por `CLAUDE` no se transmiten.

Cómo se llama a cada herramienta y sus límites:

| Herramienta | Comando (simplificado) | Límites |
|---|---|---|
| Claude Code | `claude -p ... --permission-mode acceptEdits --allowedTools ... --disallowedTools ...` | Permitido: leer, editar y escribir ficheros, skills, y solo estos comandos de shell: `coursekit verify`, `brief`, `status`, `outline`, `config`, `git status`, `git diff` (el revisor también `coursekit reviewed`). Los roles `design`, `media` y `assembly` reciben además el servidor MCP de slxd, cualquier comando `coursekit` y la descarga web. Siempre denegado: `git commit`, `git push`, `coursekit approve`, `coursekit client`, `coursekit hold`, `coursekit resume`. |
| opencode | `opencode run [--agent writer\|reviewer] --auto --format json ...` | El redactor y el revisor se ejecutan como los agentes generados, con sus permisos; la instrucción apunta al fichero del comando porque `run` no tiene comandos con barra. |
| Codex | `codex exec --sandbox workspace-write --json -o <log>.last.txt ...` | Sandbox con escritura en el espacio de trabajo. |

## Personalizar con `.agents/`

Para cambiar lo que genera coursekit, añade ficheros en `.agents/` dentro del proyecto, con la misma estructura que el paquete:

```text
.agents/
  skills/<name>/SKILL.md
  commands/<name>.md
  agents/<name>.md
  docs/<name>.md
```

- Un fichero con el mismo nombre **sustituye** al del paquete; un nombre nuevo **añade** uno.
- Los ficheros que empiezan por `_` (por ejemplo `.agents/skills/_house-rules.md`) son parciales: inclúyelos en cualquier fichero con `{{> _house-rules}}` (el nombre incluye el guion bajo).
- Los textos pueden usar valores `{{token}}`. Un token o un parcial desconocido detiene `coursekit agents` con un error que nombra el fichero.
- Ejecuta `coursekit agents` después. Los ficheros generados indican arriba dónde se editan.

```bash
mkdir -p .agents/skills/content-writing
# escribe ahí tu propio SKILL.md y después:
coursekit agents
```

Tokens disponibles:

| Token | Valor |
|---|---|
| `{{project_name}}`, `{{client}}`, `{{tone}}` | `name`, `client` y `tone` de `project.yaml` |
| `{{language_name}}`, `{{ui_language_name}}` | Nombre del idioma del contenido y del idioma de la interfaz |
| `{{address_rule}}` | La regla para tratar a los alumnos, a partir de `address` |
| `{{backend}}`, `{{mcp_name}}` | `assembly.backend` y `platform.slxd.mcp_name` |
| `{{t_section}}`, `{{t_objective}}`, `{{t_placeholder}}`, `{{t_assessment}}`, `{{t_intro_title}}`, `{{t_summary_title}}`, `{{t_unit}}`, `{{t_question_key}}`, `{{placeholder_field_lines}}` | Palabras del formato de contenido para el idioma del contenido (palabra del encabezado, etiqueta de objetivo, etiqueta de recurso multimedia...) |
| `{{k_question}}`, `{{k_answer}}`, `{{k_answers}}`, `{{k_feedback}}`, `{{k_feedback_correct}}`, `{{k_feedback_incorrect}}`, `{{k_image}}`, `{{k_position}}`, `{{k_title}}`, `{{k_objective}}` | Claves de las líneas de las directivas en el idioma del contenido (`pregunta`, `feedback-correcto`… en español; `question`, `feedback-correct`… en inglés) |
| `{{w_true}}`, `{{w_false}}`, `{{w_starts}}`, `{{w_contains}}` | Palabras que toman algunas claves en el idioma del contenido (`verdadero`/`falso` en `true-false`; `empieza`/`contiene` en `pasapalabra`) |
| `{{pages_per_hour}}`, `{{words_per_page}}`, `{{words_per_hour}}`, `{{word_margin_pct}}` | Reglas de palabras de `rules` |
| `{{questions_per_objective}}`, `{{placeholders_per_hour}}`, `{{min_placeholder_types}}`, `{{placeholder_types}}`, `{{interactive_per_hour}}`, `{{min_interactive_per_content_section}}`, `{{allowed_symbols}}` | Reglas de contenido de `rules`. `{{placeholder_types}}` enumera cada tipo permitido como la palabra que se escribe en el contenido seguida de su id entre paréntesis |
| `{{competencies_per_course}}`, `{{objectives_per_unit}}`, `{{intro_summary_hours}}` | Orientaciones de diseño de `rules` |
| `{{model}}` | Solo en ficheros de `agents/`: el modelo del rol cuando ese rol usa opencode; en otro caso se descarta la línea |

Siguiente: [Contenido](06-content.md)
