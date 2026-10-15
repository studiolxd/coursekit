# Flujo de trabajo

Todo el proceso de producción de un curso, del brief a la entrega: quién hace qué, qué estados existen y qué los mueve.

## El proceso de un vistazo

```text
 brief -> diseño -> [FIRMA DEL DISEÑO] -> redacción -> revisión con IA -> revisión editorial -> [FIRMA DE CADA UNIDAD]
         \                                                                                              |
          +-> theme (una vez por proyecto, antes de multimedia) ----+                                   |
                                                                    v                                   |
 entregado <- [revisión del cliente: opcional] <- montaje <- multimedia <-------------------------------+
```

En cualquier momento una persona puede pausar el curso (`on_hold`) y reanudarlo después. Mira [Pausar un curso](#pausar-un-curso).

Hay un camino alternativo para los cursos que nadie tiene que revisar: el [modo handoff](#modo-handoff) recorre solo las fases 2 a 9 (sin la revisión del cliente), y coursekit firma en lugar de una persona, con marca, como Coursekit Handoff.

| # | Fase | Quién | Comandos principales | Resultado |
|---|---|---|---|---|
| 1 | Brief | persona | `coursekit brief [CODE]` | material de referencia convertido en `brief/` |
| 2 | Diseño instruccional | agente de diseño, luego persona | `/new-course`, `/design-change`, `/approve-design` | propuesta en SLXD Creator, exportada a `courses/<CODE>/design/` |
| 2b | Firma del diseño | **persona** | `coursekit approve design <CODE>` | unidades y apartados escritos en `course.yaml` |
| 2c | Theme y tokens de diseño | agente de diseño, luego **persona** valida | `/define-theme [CODE]`, `coursekit theme show` | theme en la plataforma; `theme/tokens.json` y `tokens.css` derivados de él. Una vez por proyecto, antes de multimedia: mira [Theme y tokens de diseño](#theme-y-tokens-de-diseño) |
| 3 | Redacción | agente redactor | `coursekit write <CODE> [N]`, `/write-unit`, `coursekit verify` | `content.md` y `assessment.md` por unidad |
| 4 | Revisión con IA | agente revisor | `coursekit review <CODE> [N]`, `/review-unit` | `reviews/unit-NN-ai-review.md` |
| 5 | Revisión editorial y firma | **persona** | `/approve-unit`, `coursekit approve content <CODE> --unit N` | unidad `approved` |
| 6 | Multimedia | agente de multimedia | `coursekit media ...`, `/produce-media` | recursos producidos y subidos |
| 7 | Montaje | agente de montaje | `coursekit assemble ...`, `/assemble` | backend creator: contenido cargado en SLXD Creator. Backend html: un paquete SCORM por unidad construido por coursekit (`coursekit assemble build`). Mira [Montaje y entrega según el backend](#montaje-y-entrega-según-el-backend) |
| 8 | Revisión del cliente (opcional) | **persona**, luego agente de montaje | [`coursekit client`](03-commands.md#coursekit-client), `/client-feedback` | rondas anotadas en `course.yaml`; comentarios del cliente aplicados al Markdown y respondidos |
| 9 | Entrega | agente de montaje | `coursekit delivery ...`, `/deliver` | paquetes SCORM (exportados de creator, o construidos por coursekit con el backend html) registrados y publicados |

El Markdown de cada unidad es la fuente de verdad. Lo que esté mal en Creator (o en un paquete html) se corrige en el `.md` y se vuelve a cargar o a construir; nunca se edita en el resultado.

## Quién hace qué

| | Persona | Agente |
|---|---|---|
| Brief | reúne el material | lo convierte (`coursekit brief`) y lo lee |
| Diseño | revisa la propuesta, pide cambios, **firma** | la propone y la cambia en SLXD Creator |
| Redacción | la lanza, lee el resultado | escribe y ejecuta `coursekit verify` |
| Revisión con IA | la lanza | revisa con otra herramienta u otro modelo, escribe el informe, ejecuta `coursekit reviewed` |
| Revisión editorial | lee y edita cada unidad, **firma** | prepara la firma (`/approve-unit`) |
| Theme | elige o aprueba el theme, lo valida como el diseño | lo define en la plataforma con los colores y las fuentes de la marca y deriva los tokens (`/define-theme`) |
| Multimedia, montaje, entrega | decide, comprueba el resultado | produce, carga, exporta |
| Revisión del cliente | abre y cierra cada ronda y anota lo que decidió el cliente | lee los comentarios del cliente, aplica al Markdown los acordados y los responde (`/client-feedback`) |
| Pausar y reanudar | decide (`coursekit hold`, `coursekit resume`) | no puede hacerlo |
| Handoff (camino alternativo) | lo lanza y acepta el resultado sin revisarlo | ejecuta cada paso; coursekit firma como Coursekit Handoff |
| Commits y pushes | los hace | no los hace, salvo que se lo pidas |

Cada agente trabaja con uno de seis **roles**: `design`, `writer`, `reviewer`, `media`, `illustration` y `assembly`. Cada rol tiene una herramienta (`claude`, `opencode`, `codex`) y un modelo, que se guardan en `.env` (`DESIGN_AGENT`, `DESIGN_MODEL`, etc.). `coursekit roles` los muestra. Conviene que revise un modelo distinto del que redactó: coursekit avisa cuando son el mismo. Mira [Agentes](05-agents.md).

**Solo firma una persona.** `coursekit approve` registra tu nombre, la hora y una huella de lo que apruebas, y lo confirma (commit) contigo como autor. Los ajustes de agente de Claude Code y opencode prohíben a los agentes ejecutarlo, y también `coursekit client`, `coursekit hold`, `coursekit resume`, `coursekit handoff` y `coursekit reviewed --by`, que anotan decisiones de personas o firman en su lugar; Codex no tiene esa denegación en su configuración y se apoya en las instrucciones de `AGENTS.md` (mira [Agentes](05-agents.md#permisos-qué-no-pueden-hacer-los-agentes)). La única excepción es el [modo handoff](#modo-handoff), donde coursekit mismo firma, con marca, como Coursekit Handoff. Desde el chat de un agente puedes ejecutarlo tú poniendo `!` delante de la línea:

```text
! coursekit approve design PWD --yes
```

En tu propia terminal, sin `--yes`, antes te pide confirmación. Sin terminal y sin `--yes`, se niega. `--no-commit` registra la aprobación sin hacer commit.

## Modo handoff

`coursekit handoff "<título>" <horas>` lleva un curso desde su título hasta su entrega **por sí solo**: nadie revisa el diseño, las unidades ni el multimedia por el camino, y no hay revisión del cliente. Sirve para cursos cuya calidad aceptas sin la lectura de una persona; usa el flujo normal cuando alguien tenga que revisar.

```bash
coursekit handoff "Contraseñas seguras" 2 --code PWD   # un curso nuevo, desde su título y sus horas
coursekit handoff PWD                                  # continúa un curso que se paró
```

`--rounds` fija los intentos. `--code`, `--no-intro`, `--no-summary` y `--notes` crean el curso como [`coursekit new`](03-commands.md#coursekit-new); ellos y `--no-pause` solo tienen sentido al crearlo, y al continuar coursekit los rechaza (código de salida 2).

La única pausa es al principio: con las carpetas del curso ya creadas, en una terminal, espera a que dejes el material de partida del curso (`courses/<CODE>/brief/`) y pulses Enter. `--no-pause` la omite; sin terminal nunca espera. Cuando el aspecto del proyecto sale de material de marca que aún no está (backend html, o creator con `theme.source: branding`), la pausa también te recuerda que lo dejes en `theme/branding/`. Después sigue solo, y nunca pregunta por el theme: sigue `theme.source`.

| Estado del curso | Qué hace handoff |
|---|---|
| (nuevo) | coursekit crea las carpetas del curso y espera al material de partida (mira arriba); después el agente de diseño propone el diseño (`/new-course` sobre el curso ya creado; no pide material). |
| `design` | Si todavía no existe `design/matrix.json`, el agente de diseño exporta la propuesta (`/design-change`; con un diseño local, `coursekit design`). Después actualiza y valida la exportación (`/approve-design`); coursekit firma el diseño como **Coursekit Handoff**. Si no se puede firmar, el agente de diseño lo corrige y se intenta de nuevo. |
| `design_approved`, `writing` | El agente redactor escribe cada unidad hasta que verifica. Cuando un intento deja errores, el siguiente los recibe en `reviews/unit-NN-fix.md` (mira *Corrige solo esto* más abajo). |
| `ai_review` | El agente revisor revisa cada unidad. Si la línea `<!-- result: ... -->` de su informe dice `not_ready` (mira [Revisión con IA](#4-revisión-con-ia)), el redactor corrige solo lo que lista `reviews/unit-NN-fix.md` (los errores de `verify` y los hallazgos bloqueantes que la revisión no aplicó) y se revisa de nuevo. Con `review.ai: skip` esta fase no ocurre: las unidades ya están `reviewed`. |
| `editorial_review` | coursekit firma cada unidad como Coursekit Handoff. |
| `media` | coursekit extrae el manifiesto de multimedia. Si un recurso pendiente es de un tipo que usa el theme (`uses_theme`) y los tokens de diseño no están derivados (faltan o están escritos a mano), el agente de diseño define el theme (`/define-theme`) según `project.yaml › theme.source` y el material de `theme/branding/`, sin preguntar; el agente de multimedia produce los recursos (`/produce-media`); el de montaje monta (`/assemble`). |
| `assembly` | Con el backend creator, si hay recursos producidos sin subir (solo se pueden subir al contenido de su unidad, que crea el montaje), el agente de multimedia los sube y el agente de montaje vuelve a montar para que sustituyan a sus recuadros; se para si siguen sin subir o el curso no queda en creator como se planificó. Con el backend html, coursekit juega antes cada paquete (`coursekit assemble check`) y, si encuentra errores, los escribe en `reviews/package-check.md` y se para. Después el agente de montaje entrega (`/deliver`). |

- **Firmas.** Toda aprobación que da es de `Coursekit Handoff <handoff@coursekit.local>` y lleva `via: handoff` en `course.yaml › approvals`, y el commit tiene ese autor, así que nunca se confunde con la de una persona. Los agentes siguen sin poder firmar ni ejecutar `coursekit handoff`: la firma la pone coursekit, no ellos.
- **Intentos.** Cada paso se intenta `rules › handoff › rounds` veces (`--rounds`). Si sigue fallando (una unidad que no verifica, una revisión con IA que sigue en `not_ready`, recursos multimedia sin producir, un curso que no se monta o no se entrega) se para, con código de salida 1, y el mensaje dice qué falló y dónde queda el registro de la sesión del agente (`.cache/logs/`). También se para, con una indicación de `coursekit status`, cuando un paso no cambia nada (ni el estado del curso, ni las unidades, ni las aprobaciones). Si la causa es una negativa que otro intento volvería a encontrar (un programa o un servidor que una sesión sin interfaz no puede usar), no repite el paso: se para y lo nombra.
- **Corrige solo esto.** Cuando una unidad falla (no verifica, o la revisión dice `not_ready`), coursekit escribe `reviews/unit-NN-fix.md`: los errores de `coursekit verify` con el lugar al que apuntan y los hallazgos bloqueantes de la revisión con IA que no se aplicaron, con su apartado y su criterio (la revisión escribe la gravedad `blocking` y la acción `applied` o `proposed` sin traducir, para poder leerlas). Al redactor se le pide corregir esa lista y nada más. Cada informe guarda la huella de sus hallazgos: si una ronda termina con los mismos hallazgos que la anterior (aunque hayan cambiado sus números de línea), el handoff se para ahí en vez de gastar otra ronda, y el informe dice lo que queda. El informe se borra cuando la unidad pasa.
- **Una versión nueva de un curso entregado.** Tras editar el contenido de un curso `delivered`, `coursekit handoff <CODE> --new-version` vuelve a verificar todas las unidades y deja el curso en el estado que implican (las unidades editadas retroceden a `verified`, así que la revisión con IA mira las partes que cambiaron y coursekit las firma de nuevo; si ninguna retrocedió, sigue desde `media`). Después recorre las etapas de siempre: produce el multimedia marcado para rehacer (`coursekit media redo`), el montaje aplica solo las diferencias y la entrega hace la versión siguiente (`1.1`, `1.2`…). La reapertura queda en el `history` del `course.yaml`.
- **Continuar.** `coursekit handoff <CODE>` sigue desde el estado actual, sin repetir lo ya firmado. Si el curso está `on_hold` (el mensaje dice que antes ejecutes `coursekit resume <CODE>`) o en `client_review` se para: handoff no gestiona ninguno. `coursekit handoff "<título>" <horas>` rechaza un código de curso que ya existe y señala `coursekit handoff <CODE>`.
- **Qué rechaza.** Si el proyecto exige la revisión del cliente (`delivery › client_review › required`), se niega a empezar, antes de crear el curso, y a continuar mientras esa revisión no esté aprobada u omitida: handoff no la hace. Ambos casos terminan con código de salida 1.
- **Cómo se ejecuta.** Todos los agentes se ejecutan en modo headless, con los límites de [Agentes](05-agents.md#headless---headless). Las sesiones quedan en `.cache/logs/` (`<CODE>-<paso>-handoff-<fecha>-<hora>.log`, y `<CODE>-uNN-write-…` o `-review-…` para las unidades). Tras cada paso se refrescan la carpeta espejo y el catálogo, si el proyecto los tiene. Al final imprime `handoff terminado`, con el estado del curso.
- **Qué necesita.** Los roles del `.env` y, cuando el curso usa slxd (backend creator o un diseño hecho en slxd), la URL del MCP de slxd, como el flujo normal, con creator ya autorizado (una sesión sin interfaz no puede iniciar sesión; mira [Problemas con el servidor MCP](09-troubleshooting.md#problemas-con-el-servidor-mcp)), y los proveedores del multimedia que quieras producir. No puede preguntar: las dudas quedan escritas en las unidades (`<!-- VERIFICAR -->`) y en los informes.

## Estados

### Curso

Un curso tiene un único estado en `course.yaml › status`:

| Estado | Significado | Qué lo lleva aquí |
|---|---|---|
| `design` | propuesta de diseño en curso | `coursekit new` crea el curso en este estado |
| `design_approved` | diseño firmado, redacción sin empezar | `coursekit approve design` |
| `writing` | al menos una unidad está empezada | se deriva de las unidades |
| `ai_review` | todas las unidades pasan la verificación | se deriva de las unidades |
| `editorial_review` | todas las unidades están revisadas con IA | se deriva de las unidades |
| `media` | todas las unidades están firmadas | se deriva de las unidades |
| `assembly` | todas las unidades están en Creator tal como se planificó (backend creator) | `coursekit assemble applied`, automáticamente, solo desde `media`. `coursekit assemble build` (backend html), automáticamente, cuando todas las unidades tienen su paquete construido y el curso estaba en `media` |
| `client_review` | hay una ronda de revisión del cliente abierta (fase opcional) | [`coursekit client`](03-commands.md#coursekit-client) `CODE send`, solo desde `assembly` |
| `delivered` | todas las unidades tienen un paquete de la misma versión | `coursekit delivery add`, automáticamente, solo desde `assembly` o `client_review` |
| `on_hold` | en pausa por una persona | [`coursekit hold`](03-commands.md#coursekit-hold) `CODE --reason "..."`; [`coursekit resume`](03-commands.md#coursekit-resume) `CODE` lo devuelve a su estado |

Desde `design_approved` hasta `media`, el estado se **deriva** de la unidad menos avanzada y se recalcula cada vez que una unidad cambia de estado. Por eso también puede retroceder cuando retrocede una unidad. Firmar de nuevo un diseño cambiado conserva el progreso de las unidades, y el estado se vuelve a derivar de ellas. Desde `assembly` en adelante no se recalcula.

`client_review` y `on_hold` no se derivan de las unidades: los fijan los comandos que siguen.

#### Revisión del cliente (opcional)

El cliente revisa el curso montado antes de la entrega. Está **desactivada por defecto**: `client_review.required` es `false` en la configuración de entrega, así que el flujo `assembly` -> entrega funciona como siempre, y aun así puedes abrir una ronda si quieres. Cuando un proyecto fija `client_review.required: true`, la entrega se niega hasta que la última ronda esté aprobada u omitida. El ajuste puede sobrescribirse por proyecto (`config/delivery.yaml`) y por curso (`course.yaml › delivery › client_review`); mira [Configuración](04-configuration.md#delivery-exportación-scorm-y-revisión-del-cliente).

```text
 assembly --send--> client_review --approve--> (entregar)
    ^                    |
    +------changes-------+          skip: entregar sin la aprobación del cliente, con un motivo
```

| Comando (solo personas) | Efecto |
|---|---|
| `coursekit client CODE send [--to QUIÉN] [--where URL]` | Abre la ronda N. El curso pasa de `assembly` a `client_review` y los enlaces de revisión de las unidades se anotan en la ronda |
| `coursekit client CODE changes [--note TEXTO]` | El cliente pidió cambios: la ronda se cierra con resultado `changes` y el curso vuelve a `assembly` |
| `coursekit client CODE approve --by "Nombre" [--note TEXTO]` | El cliente aprobó: la ronda se cierra con resultado `approved`, con el nombre del cliente y la fecha. El curso se queda en `client_review` y se puede entregar |
| `coursekit client CODE skip --reason TEXTO` | Decides entregar sin la aprobación del cliente. Anota una ronda con resultado `skipped` y el motivo, lo que desbloquea la entrega (después `/deliver`); no entrega ni cambia el estado. Se permite desde `assembly` o `client_review`, y se rechaza mientras haya una ronda abierta |

Una ronda en un flujo normal:

1. El agente de montaje ha anotado un enlace de vista previa y uno de revisión por unidad (`coursekit assemble link`). Con el backend html no hay enlaces de plataforma: alojas tú el zip o la vista previa y envías un solo enlace con `--where URL`.
2. Envías los enlaces al cliente y abres la ronda: `coursekit client PWD send --to "equipo de formación de ACME"`.
3. El cliente comenta en los enlaces de revisión, sin necesidad de cuenta.
4. `/client-feedback PWD` (agente de montaje, solo con el backend creator: lee los comentarios de los enlaces de revisión): lee los comentarios, aplica en el `.md` los acordados, recarga los cambios, publica una versión nueva de la revisión para el cliente y responde a cada comentario. Los comentarios que cambian objetivos, horas, actividades o estructura son un cambio de diseño y se te dejan a ti (`/design-change`).
5. Cierras la ronda: `coursekit client PWD changes --note "..."` si el cliente quiere más cambios; después aplica, vuelve a montar y haz `send` otra vez (ronda 2). Si el cliente está conforme, `coursekit client PWD approve --by "..."`.
6. Entrega con `/deliver`.

Una unidad editada después de su firma vuelve a `verified`: necesita nueva revisión con IA y nueva firma antes de la entrega, como en [Cambios tras la aprobación](#cambios-tras-la-aprobación). Mira [Montaje y entrega](08-assembly-and-delivery.md#revisión-del-cliente) para los enlaces de revisión y las herramientas de creator que intervienen.

#### Pausar un curso

`coursekit hold CODE --reason "..."` deja el curso en `on_hold`; `coursekit resume CODE` lo devuelve a su estado. Solo los ejecuta una persona. Al pausar se guardan en `course.yaml › hold` el estado anterior, el motivo, quién y cuándo, y se añade una entrada a `history`.

Mientras un curso está en pausa se niegan los comandos que lo modifican: `write`, `review`, `reviewed`, `approve`, `assemble` (todas sus acciones, incluidas `plan` y `diff`), `sync` (sin `--check`), `media set`, `run` (con el código de un curso, salvo `new-course` y `course-status`), `client` y los comandos de entrega (`delivery check`, `name` y `add`). Los comandos que solo leen o comprueban siguen funcionando (`status`, `verify`, `outline`, `config`, `sync --check`, `catalog`...). `coursekit status CODE` muestra quién lo pausó, cuándo, por qué y en qué estado estaba. El mensaje de un comando rechazado termina con el camino de vuelta: `coursekit resume CODE`.

`resume` restaura el estado anterior y elimina el bloque `hold`. Si el curso se estaba redactando (de `design_approved` a `media`), el estado se vuelve a calcular a partir de sus unidades.

### Unidad

Cada unidad tiene su propio estado en `course.yaml › units[].status`:

```text
pending -> writing -> verified -> reviewed -> approved
```

| Estado | Significado | Qué lo lleva aquí |
|---|---|---|
| `pending` | aún sin contenido | `coursekit approve design` (las unidades se crean a partir del diseño) |
| `writing` | contenido empezado, pero no pasa `coursekit verify` | `verify` encuentra errores en una unidad con palabras, o en una unidad que estaba más avanzada |
| `verified` | pasa todas las comprobaciones de `coursekit verify` | `verify` sin errores |
| `reviewed` | existe el informe de revisión con IA (o una persona registró su revisión, o el proyecto omite la revisión con IA) y la unidad sigue verificando | `coursekit reviewed <CODE> <N>` (lo ejecuta el agente revisor), `coursekit reviewed <CODE> <N> --by NOMBRE`, o `coursekit verify` con `review.ai: skip` |
| `approved` | firmada por una persona | `coursekit approve content <CODE> --unit N` |

Reglas que deciden el estado del curso: cualquier unidad que pase de `pending` lo deja en `writing`; todas las unidades en `verified` o más allá, en `ai_review`; todas en `reviewed` o más allá, en `editorial_review`; todas en `approved`, en `media`.

### Qué muestra `coursekit status`

```bash
coursekit status           # una línea por curso
coursekit status PWD       # detalle y siguiente paso
```

```text
PWD — Contraseñas seguras (2 h)
Estado: design_approved
Montaje: backend creator
Diseño: firmado por Ana Ruiz <ana@acme.example> el 2026-10-09T01:18:52+02:00
  U1 Contraseñas seguras · 2 h · 3 apartados · 2 objetivos · mín. 10.000 palabras · pending
Siguiente paso: escribe las unidades con `coursekit write PWD <N>`
```

El detalle lista cada unidad con su estado y, si se conoce, la herramienta que la escribió. Si el curso está en pausa añade quién lo pausó, cuándo, por qué y el estado que tenía; si hay revisión del cliente, añade la última ronda y su resultado (`abierta`, `pidió cambios`, `aprobada` u `omitida`). La última línea es el siguiente paso para el estado actual. Si el diseño cambió después de firmarse, la línea "Diseño" lo dice y el siguiente paso es firmarlo de nuevo.

### Qué se anota en `course.yaml`

| Clave | Contenido |
|---|---|
| `status` | el estado del curso |
| `units[].status` | el estado de la unidad |
| `units[].written_with`, `reviewed_with` | herramienta y modelo del redactor y del revisor |
| `units[].review` | cómo se revisó la unidad: `kind` (`ai`, `human` con `by`, `at`, `note`, `report`, o `skipped`) |
| `units[].reviewed_parts` | huella de cada apartado y actividad en el momento de la revisión con IA |
| `approvals` | cada firma: puerta (`design` o `content`), quién, cuándo y los hashes de lo aprobado |
| `units[].links.preview`, `units[].links.review` | vista previa en vivo de la unidad (sin comentarios) y su enlace de revisión del cliente, que escribe `coursekit assemble link` |
| `client_review` | las rondas de revisión del cliente: `round`, `sent_at`, `sent_by`, `to`, `links`, `outcome`, `closed_at`, `by`, `note` |
| `hold` | solo mientras está en `on_hold`: estado `previous`, `reason`, `by` y `at` |
| `deliveries` | cada paquete SCORM registrado: versión, unidad, fecha, fichero y hash |
| `history` | una entrada por cada cambio de estado del curso y por cada aprobación: `date`, `status`, `by`, `note` |
| `assembly.backend` | opcional: el backend de este curso (`creator` o `html`) cuando difiere del del proyecto |

No edites a mano `status`, `units`, `client_review` ni `hold`: los escriben los comandos. Las aprobaciones las escribe solo `coursekit approve`.

## Fase a fase

### 1. Brief

Deja documentos en `brief/sources/`, URLs en `brief/links.md` e indicaciones generales en `brief/notes.md`. Cada curso tiene su propio `brief/` con la misma estructura, y sus notas se imponen a las del proyecto. Después:

```bash
coursekit brief            # brief del proyecto
coursekit brief PWD        # brief de un curso (incluye el del proyecto)
coursekit brief --refresh  # vuelve a descargar las URLs
```

Esto escribe `brief/index.md` y el texto convertido en `brief/text/`, que es lo que leen los agentes. Solo se convierten los ficheros nuevos o cambiados.

### Importar desde eXeLearning

Un curso que ya existe como paquetes de eXeLearning (`.elp`, eXeLearning 2 y 3) no se escribe otra vez desde cero: su contenido se convierte a Markdown, conservando su estructura y su tipo de interactividad, y los agentes trabajan a partir de él. Deja los `.elp` en `brief/sources/` y `coursekit brief` los convierte como cualquier otro documento, o crea cursos enteros con [`coursekit import`](03-commands.md#coursekit-import).

Qué hace la conversión:

| En el paquete | En el Markdown |
|---|---|
| Árbol de páginas | Un encabezado por página (`##`, `###`…); las páginas sin contenido se omiten |
| Texto, listas, tablas, imágenes | Markdown; las imágenes se copian a `brief/text/media/<paquete>/` |
| `exe-accordion`, `exe-tabs`, `exe-carousel` (en cualquier iDevice) | `:::accordion`, `:::tabs`, `:::carousel`, un `#### Título` por panel (una diapositiva sin título recibe su número) |
| Tarjetas, juego de relacionar, mapa | `:::flashcards`, `:::match`, `:::labelled-graphic` (con la posición de cada punto) |
| Elección múltiple, selección múltiple, verdadero o falso | `:::single-choice`, `:::multi-select`, `:::true-false`, con el feedback de las opciones; las preguntas llegan sin objetivo, que asigna el diseño |
| iDevices genéricos (atención, definición, ejemplo, "¿sabías que…?", reflexión) | `:::note`, `:::highlight`, `:::reflection`, según las reglas de [`import`](04-configuration.md#import-paquetes-de-exelearning) |
| El aviso previo a un interactivo ("Pulsa sobre las flechas…") y las instrucciones de los juegos | Se dejan fuera: los interactivos de coursekit traen el suyo |
| Vídeos y otro contenido incrustado | Una línea `> **[Video]** dirección`, contada por proveedor en el informe |

Nada se descarta en silencio. `brief/import-report.md` lista, por paquete, lo que las reglas dejaron fuera (con su texto y cuántas veces), los iDevices sin regla (importados como texto), el contenido incrustado por proveedor, las páginas omitidas y una **comprobación palabra a palabra**: cada palabra del texto del origen tiene que estar en el Markdown, y el informe nombra las que no. `coursekit brief` marca en `brief/index.md` los paquetes con algo que mirar. Solo se leen los `.elp` de eXeLearning 2 y 3; un paquete de eXeLearning 4 (`.elpx`) hay que exportarlo de nuevo como `.elp`.

Cursos desde una carpeta: una carpeta con ficheros `.elp` es un curso y cada paquete una unidad; una carpeta padre con una subcarpeta por curso los crea todos. Las horas (y el título) no están en los paquetes, así que salen del plan (`coursekit import <carpeta> --plan` escribe `import.yaml` para completar y revisar), de un Excel o CSV con la carpeta y las horas (`--hours-file`) o de un valor para todos (`--default-hours`). Las unidades se ordenan por el número del nombre de cada paquete, y un curso con dos versiones de la misma unidad espera hasta que el plan diga cuál usar. Con `--handoff` cada curso sigue solo hasta la entrega.

Un curso creado con `coursekit import` tiene `design.origin: import`, y los agentes trabajan en él como una **migración**: el diseño propone las unidades y los apartados a partir de la estructura de los paquetes (una unidad por paquete, un apartado por página), conserva cada interactivo tal como está, usa las horas que diste y propone los objetivos y las actividades de aprendizaje y de evaluación que faltan en los paquetes, marcando lo nuevo; la redacción reutiliza el texto del cliente sin reescribirlo (el esqueleto de cada unidad muestra, en lugar de un mínimo de palabras, la página del paquete de la que sale cada apartado y sus palabras, y `coursekit verify` falla si la unidad crece más de [`content.import_max_growth`](04-configuration.md#rules-reglas-de-producción) veces su paquete), registra las imágenes de los paquetes en lugar de producirlas de nuevo (`coursekit media adopt`) y sustituye el vídeo incrustado de un sitio prohibido por un recurso de vídeo; la revisión con IA añade un criterio de **fidelidad al paquete** (nada perdido, nada reescrito sin motivo, cada interactivo del mismo tipo). En este tipo de curso `coursekit verify` solo avisa cuando un apartado se queda corto de palabras, interactivos o recursos, e indica las unidades que se quedan cortas o se pasan de las palabras de sus horas.

Los vídeos alojados en un sitio que prohíbes (YouTube, Vimeo…) pueden quedarse cuando son de un **canal oficial**: lista los canales en `rules › forbidden › allow_channels` y `coursekit videos check` aprueba esos vídeos. Para el resto el agente de redacción busca en la web un vídeo equivalente en un canal oficial y lo registra con su evidencia (`coursekit videos propose`); `reviews/external-videos.md` lista esas propuestas para que una persona las compruebe (`coursekit videos approve` o `reject`), y `coursekit verify` avisa mientras alguna esté sin comprobar. El handoff no puede preguntarte, así que se detiene antes de que el contenido pase a creator mientras haya una propuesta sin comprobar (`handoff.stop_on_unchecked_videos`) y sigue con `coursekit handoff CODE` cuando la hayas resuelto; un canal que listes en `allow_channels` nunca espera. Sin equivalente oficial, el vídeo pasa a ser un recurso multimedia.

Un curso migrado se **corrige, no se amplía**: las horas son las que diste, el contenido conserva el tamaño de los paquetes (una unidad que se queda corta de las palabras que piden sus horas es un aviso de `coursekit verify`, nunca un motivo para escribir más), y solo se cambia lo que está desactualizado, erróneo o prohibido.

Para que la migración siga los deseos del cliente, escríbelos en `brief/notes.md` (por ejemplo "quita toda referencia a una región" o "no conserves vídeos alojados en otros sitios") y lista en `rules › forbidden` lo que no debe quedar: direcciones de sitios (`hosts`, subdominios incluidos) y palabras o frases (`terms`). Los agentes aplican las notas, el informe de importación cuenta lo que los paquetes tienen de ello y `coursekit verify` rechaza cada aparición que quede. Si un curso trata de una aplicación o de una normativa, el agente de diseño propone además su documentación o su texto oficial para `brief/links.md` ([`brief.reference_sources_max`](04-configuration.md#rules-reglas-de-producción)), para que el revisor pueda comprobar el contenido con ella.

### 2. Diseño instruccional

```text
/new-course "Contraseñas seguras" 2 --code PWD
```

El agente de diseño crea el curso, lee el brief y construye una **propuesta**: competencias, unidades, objetivos, apartados, actividades y horas. Dónde depende de `course.yaml › design.tool`: en la matriz de diseño de SLXD Creator (`slxd`) o en `courses/PWD/design/design.yaml` (`local`, mira [Diseño local](#diseño-local)). En los dos casos exporta el diseño a `courses/PWD/design/` (`matrix.json`, `validation.json` y el Excel que revisas) y termina con un resumen. Revísalo y pide cambios con tus palabras:

```text
/design-change PWD Añade una unidad sobre gestores de contraseñas y pásale 0,5 horas
```

Cuando estés conforme:

```text
/approve-design PWD
```

El agente refresca la exportación si editaste en Creator (o en `design.yaml`), valida el diseño, ejecuta `coursekit sync PWD --check` y resume lo que vas a firmar. No puede firmar. Después firmas tú:

```bash
coursekit approve design PWD
```

La firma exige `design/matrix.json` y que `design/validation.json` no tenga errores de validación (y, en un curso basado en decisiones, la [biblia narrativa](06-content.md#biblia-narrativa)). Escribe las unidades y sus apartados en `course.yaml` (el progreso ya anotado se conserva: estado, registro de revisión y enlaces), crea un esqueleto de `content.md` y `assessment.md` por unidad en `content/unit-NN/`, registra la aprobación, deja el curso en `design_approved` y hace commit.

#### Diseño local

Un curso con `design.tool: local` (la elección de `coursekit init`, `rules › defaults.design_tool` o `coursekit new --design-tool local`) no necesita slxd: su diseño es `courses/<CODE>/design/design.yaml`, que escribe el agente de diseño (`coursekit new` deja una plantilla comentada) y que también puedes editar tú. Claves en inglés, textos en el idioma del curso:

```yaml
profile: {audience: Personal de oficina, level: Básico, prerequisites: "", context: "", tone: ""}
passing: all_tests                  # o course_score, con course_passing_score: 0-100
competencies:
  - {id: C1, text: Proteger las cuentas de trabajo en el día a día de la oficina}
objectives:                         # los del curso, en orden
  - {id: O1, text: Aplicar los criterios de una contraseña segura a una cuenta nueva, bloom: apply, competencies: [C1]}
  - {id: O2, text: Analizar por qué una contraseña es débil, bloom: analyze, competencies: [C1]}
units:                              # con design.structure con_modulos: modules: [{title, hours, general_objective, units}]
  - title: Contraseñas que protegen
    sections:
      - {title: Introducción y objetivos, hours: 0.2}
      - {title: Cómo es una contraseña segura, hours: 0.6, objectives: [O1, O2]}
      - {title: Resumen, hours: 0.2}
    learning_activities:
      - {title: Clasifica las contraseñas, type: classification, objectives: [O1, O2]}
    assessment_activities:
      - {title: Test de la unidad, instrument: case_study, criterion: La mitad bien, weight: 1, passing_score: 50,
         attempts: 2, objectives: [O1, O2]}
```

- `bloom`: `remember`, `understand`, `apply`, `analyze`, `evaluate`, `create`. `type` de una actividad de aprendizaje: `self_assessed`, `classification`, `interactive_decision`, `branching_scenario`, `hotspot_analysis`, `guided_simulation`, `template_practice`. `instrument` de evaluación: `quiz`, `case_study`, `portfolio`, `rubric`. `weight`, `passing_score` y `attempts` son opcionales (se aplica `design.grading` del curso).
- Un apartado puede dividirse en `subsections` (cada una con sus horas y objetivos); una unidad o un módulo sin `hours` toma la suma de sus partes, y con ellas tienen que cuadrar. El total es `course.yaml › design.hours`.
- Los ids de objetivos y competencias son libres y únicos (`O1`, `C1`...). El contenido nombra los objetivos de cada unidad `U1.1`, `U1.2`... tal como los muestra `coursekit sync --check`. Da a una unidad o a un apartado un `id` propio si lo mueves dentro de un diseño que ya se sincronizó.

[`coursekit design PWD`](03-commands.md#coursekit-design) lo comprueba con las reglas de una matriz de diseño (cobertura, evidencia, práctica antes de evaluar, instrumento y nivel de Bloom, horas, verbos, progresión) y exporta `matrix.json`, `validation.json` y `PWD-instructional-design.xlsx`; a partir de ahí el flujo es el mismo que con slxd. La firma rechaza un `design.yaml` que no se ha exportado, y una exportación posterior que cambie el diseño invalida la firma (volver a exportar sin cambios no).

### 3. Redacción

```bash
coursekit write PWD 1      # unidad 1
coursekit write PWD        # todas las unidades pendientes, en orden
```

O `/write-unit PWD 1` en tu herramienta de IA (`/write-unit PWD`, sin número, redacta todas las unidades pendientes, en orden, en la misma sesión y se detiene en la primera que no verifica; `coursekit write`, en cambio, abre una sesión por unidad). El agente redactor trabaja en una unidad cada vez, apartado a apartado, y ejecuta `coursekit verify` después de cada uno. Añade `--headless` para ejecutar sin la interfaz de la herramienta (la sesión va a `.cache/logs/`; entonces se detiene en la primera unidad que no termine en `verified`), y `--agent`/`--model` para usar otra herramienta u otro modelo en este lanzamiento.

```bash
coursekit verify PWD --unit 1
```

`verify` comprueba el contenido con las reglas de producción (mínimo de palabras, etiquetas de objetivo, directivas interactivas, recursos multimedia, símbolos prohibidos...) y mueve el estado de la unidad. Se niega a ejecutarse si el diseño no está firmado o cambió después de firmarse. Mira [Contenido](06-content.md).

### 4. Revisión con IA

```bash
coursekit review PWD 1
```

O `/review-unit PWD 1`. El agente revisor escribe `reviews/unit-01-ai-review.md` (hallazgos, cambios aplicados, propuestas pendientes de tu decisión) y ejecuta `coursekit reviewed PWD 1`, que comprueba otra vez que la unidad verifica y la marca como `reviewed`. Revisar una unidad ya revisada es una revisión parcial: solo los apartados y actividades que han cambiado desde la última revisión. Usa `--full` para revisarlo todo, o `--parts "apartado 4, actividad 1.2"` para elegir.

El informe empieza con su **resultado** (listo, listo con cambios o no listo), repetido en un comentario que leen las herramientas: `<!-- result: ready | ready_with_changes | not_ready -->` (un solo valor, con guiones bajos). El resto es un resumen, una tabla de hallazgos (cada uno bloqueante, mejora o menor), los cambios aplicados y las propuestas pendientes de tu decisión. Una revisión parcial añade su propia sección al mismo informe y actualiza el resultado si cambia. En el [modo handoff](#modo-handoff), un resultado `not_ready` devuelve la unidad al redactor.

#### Sin revisión con IA

Hay dos formas, y en ambas firma una persona:

- **Una unidad, revisada por una persona.** Tras leerla, ejecuta `coursekit reviewed PWD 1 --by "Ana Pérez" [--note "..."] [--report reviews/notas.md]`. La unidad pasa a `reviewed` sin el informe de IA, y `course.yaml › units[].review` y el historial registran quién la revisó. El contenido editado después vuelve a `verified`, igual que con la revisión con IA. `--note` y `--report` necesitan `--by`, y el informe debe ser un fichero dentro de la carpeta del curso. El registro `units[].review` se elimina si la unidad retrocede por debajo de `reviewed`. Los agentes tienen `--by` denegado.
- **Todo el proyecto (o un curso), sin revisión con IA.** Pon `review.ai: skip` en `rules` (`config/rules.yaml`, `project.yaml › rules` o `course.yaml › rules`). Una unidad que pasa `coursekit verify` queda `reviewed` de inmediato (`review.kind: skipped`), el curso pasa de `writing` a `editorial_review` sin la fase `ai_review`, y tu firma es la revisión. `coursekit review` sigue funcionando si quieres igualmente una revisión con IA de una unidad.

#### Actualizar contenido desactualizado (opcional)

Los cursos envejecen: los productos cambian de nombre y de interfaz, las versiones y los precios se mueven, las normas se sustituyen. `/update-unit PWD 1` (o `coursekit run update-unit PWD 1`) pide al agente revisor que compruebe la unidad con fuentes oficiales actuales: primero la documentación que descargó el brief, después la web. Escribe `reviews/unit-01-currency.md` con cada hallazgo (qué dice la unidad, qué es cierto ahora con su fuente, el texto que propone) y las afirmaciones que no pudo verificar, y **no cambia nada** salvo que añadas `--apply`. Incluso entonces solo escribe datos simples que tengan fuente oficial (un nombre, una versión, una cifra, una fecha, una ruta de interfaz, un enlace); lo que cambie lo que enseña la unidad queda como propuesta para ti. Una unidad cuyo contenido cambió vuelve a `verified` y necesita de nuevo la revisión con IA.

La regla `update.mode` (`config/rules.yaml`, `project.yaml` o `course.yaml › rules` de un curso) hace que el handoff la ejecute antes de la revisión con IA de cada unidad: `off` (por defecto; no se ejecuta sola), `propose` (solo informe) o `apply`. Ver [`rules`](04-configuration.md#rules-reglas-de-producción).

### 5. Revisión editorial y firma

Lee la unidad en `courses/PWD/content/unit-01/`, resuelve las propuestas del informe de revisión con IA y edita el Markdown como haga falta. Tras editar, ejecuta `coursekit verify PWD --unit 1`: si la edición tocó partes que la IA revisó, la unidad vuelve a `verified` y necesita otra revisión (parcial) antes de poder firmarse. Después:

```text
/approve-unit PWD 1
```

El agente comprueba que la unidad verifica y que existe el informe, y te dice que firmes:

```bash
coursekit approve content PWD --unit 1
```

Para firmar se exige: el diseño sigue firmado y sin cambios, ningún error de verificación, la unidad en `reviewed` (o `approved`) y su informe de revisión con IA (no hace falta si una persona registró su revisión con `coursekit reviewed --by`, ni con `review.ai: skip`). Registra los hashes de `content.md` y `assessment.md` y hace commit de la unidad, el informe y `course.yaml`. Cuando se firma la última unidad, el curso pasa a `media`.

### 6. Multimedia

```text
/produce-media PWD
```

El agente de multimedia extrae los recursos del contenido a un manifiesto (`coursekit media extract`), muestra el plan (`coursekit media plan`, que nombra cada tipo por su id en inglés: `image`, `infographic`, `video`…) y te dice qué va a producir y con qué antes de gastar créditos de APIs de pago. Las infografías, los esquemas, los GIF animados, las simulaciones y los vídeos se hacen con los tokens de diseño del theme, así que antes hace falta `/define-theme`: mira [Theme y tokens de diseño](#theme-y-tokens-de-diseño). Mira [Multimedia](07-media.md).

### 7. Montaje

```text
/assemble PWD
```

`/assemble` carga la skill del backend del curso: `creator-assembly` o `html-assembly` (`coursekit status PWD` lo muestra: `Montaje: backend creator` o `Montaje: backend html`).

**Backend creator.** El agente de montaje construye un plan por unidad (`coursekit assemble plan`), lo compara con lo que ya hay en Creator (`coursekit assemble diff`), aplica solo las diferencias y registra cada lección (`coursekit assemble applied`). Cuando todas las unidades están en Creator exactamente como se planificó, el curso pasa de `media` a `assembly`. El agente crea los enlaces de cada unidad (cada unidad es un contenido propio de creator): una vista previa en vivo, sin comentarios, y un enlace de revisión donde comenta el cliente; los anota con `coursekit assemble link` y te los da. También aplica el theme del curso a cada contenido (`set_content_theme`, con el id que da `coursekit theme show --course PWD`).

**Backend html.** El agente ejecuta `coursekit assemble build PWD --unit N` para cada unidad (sin `--unit`, todas). Escribe una carpeta de vista previa, `courses/PWD/assembly/html/unit-NN/`, que se abre desde el disco en un navegador, y rechaza el contenido que no puede representar (una clave en el idioma equivocado, una pregunta sin sus opciones...); la carpeta es generada y no se versiona. Con `--version X.Y` escribe además el zip de la unidad en `courses/PWD/delivery/`. El agente te dice qué comprobar en la vista previa (la navegación, un componente de cada tipo, las preguntas y el test).

Mira [Montaje y entrega](08-assembly-and-delivery.md).

### 8. Revisión del cliente

Opcional. Una persona abre y cierra cada ronda con [`coursekit client`](03-commands.md#coursekit-client) (mira [Revisión del cliente (opcional)](#revisión-del-cliente-opcional) más arriba); el agente solo trata los comentarios con `/client-feedback PWD`. Con el backend html no hay enlace de revisión de ninguna plataforma: alojas tú el zip o la carpeta de vista previa y das el enlace con `coursekit client PWD send --where URL`. `/client-feedback` funciona solo con el backend creator; con html los comentarios te llegan por tu propio medio, los aplicas editando el `.md` y `/assemble PWD` vuelve a construir. Si una unidad retrocede al editarla, ejecuta `coursekit verify`, revisa y firma de nuevo donde haga falta, y `/assemble PWD` carga solo lo que cambió.

### 9. Entrega

```text
/deliver PWD 1.0
```

El agente empieza con `coursekit delivery check PWD`: se niega mientras el curso está en pausa y, si el proyecto exige la revisión del cliente, hasta que la última ronda esté aprobada u omitida. Después exporta un paquete SCORM por unidad, lo descarga en `courses/PWD/delivery/` y lo registra con `coursekit delivery add`. Cuando todas las unidades tienen un paquete de la misma versión, el curso pasa a `delivered` (solo desde `assembly` o `client_review`; en otro estado el paquete se registra con un aviso). Cada `coursekit delivery add` copia además el curso a la carpeta espejo y refresca el catálogo (cuando el proyecto tiene una). Mira [Montaje y entrega](08-assembly-and-delivery.md).

Con el backend html no se exporta nada de ninguna plataforma: para cada unidad el agente ejecuta `coursekit assemble build PWD --unit N --version 1.0` (escribe el zip en `courses/PWD/delivery/`) y después `coursekit delivery add` sin `--job` ni `--snapshot`. La comprobación inicial, el registro y la publicación son los mismos.

### En cualquier momento

Dos comandos no pertenecen a ninguna fase:

- `/course-status [CODE]` (rol de diseño) ejecuta `coursekit status` y explica el resultado y el siguiente paso en dos o tres líneas.
- `/sync-directives` (rol de montaje) mantiene el registro de directivas al día con el catálogo de bricks de creator. Ejecútalo cuando cambie el catálogo, no una vez por curso. Guarda `list_brick_types` en `.cache/list_brick_types.json`, lo comprueba con `coursekit directives check` y, por cada tipo de brick nuevo, decide si pasa a ser una directiva en `config/directives.yaml` (o va a `not_directives` con el motivo). Quita los tipos que desaparecieron, listando el contenido que los usaba sin modificarlo, y actualiza `synced_with_creator`.

## Montaje y entrega según el backend

Un curso se monta o en **slxd creator** o con el **backend html**. La elección se hace una vez por proyecto en `project.yaml › assembly.backend` (el asistente de `init` la pregunta; por defecto, `creator`) y un curso puede sobrescribirla en `course.yaml › assembly › backend`. `coursekit status CODE` muestra `Montaje: backend <backend>`. Todo lo anterior al montaje (brief, diseño, redacción, revisión, multimedia) es igual, y el diseño instruccional se hace en creator con cualquiera de los dos backends.

| | backend creator | backend html |
|---|---|---|
| Dónde se monta | en SLXD Creator, a través del servidor MCP de slxd | en tu proyecto: coursekit representa cada unidad como una página con su navegación, progreso, componentes y seguimiento SCORM |
| Qué construye el paquete | la plataforma exporta el SCORM (`/deliver`, con las herramientas de exportación) | coursekit (`coursekit assemble build CODE [--unit N] [--version X.Y]`, con @studiolxd/scorm y esbuild del almacén de coursekit) |
| Resultado | contenido en creator; el zip se descarga en `delivery/` | carpeta de vista previa `assembly/html/unit-NN/`; con una versión, el zip en `delivery/` |
| Skill del agente | `creator-assembly` | `html-assembly` |
| Cómo revisa el cliente | enlaces de vista previa y de revisión de creator, anotados con `coursekit assemble link`; los comentarios se hacen en el enlace | alojas tú el zip o la vista previa y envías el enlace con `coursekit client CODE send --where URL`; los comentarios te llegan por tu propio medio |
| Qué registra la entrega | `coursekit delivery add` con el `--job` y el `--snapshot` de la exportación | `coursekit delivery add` sin ellos |
| Theme | un theme de la plataforma, tokens derivados con `coursekit theme import <get_theme.json>` | la hoja de estilos `theme/maqueta.css`, tokens derivados con `coursekit theme import theme/maqueta.css` |

Los comandos de un backend se rechazan en el otro, con un mensaje que señala el correcto (mira [Solución de problemas](09-troubleshooting.md#el-backend-html)). El backend html no necesita la plataforma para montar, pero el paquete debe probarse en el LMS al que se va a entregar (o en SCORM Cloud) antes de dárselo a nadie. Los detalles están en [Montaje y entrega](08-assembly-and-delivery.md).

## Theme y tokens de diseño

Los gráficos, simulaciones y vídeos de un curso usan los colores y las fuentes de su theme, para que se parezcan al curso. El theme vive en la plataforma de maquetación (creator). coursekit nunca toma los colores y las fuentes de un fichero escrito a mano: **deriva** los tokens de diseño del theme de la plataforma y anota de dónde vienen.

```text
/define-theme            # el theme del proyecto, que heredan todos los cursos
/define-theme PWD        # el theme propio de un curso
```

Qué hace `/define-theme [CODE]` (rol de diseño, skill `theme-definition`):

1. Mira `coursekit theme show` para saber si los tokens ya vienen de un theme de la plataforma (si es así, pregunta antes de rehacerlos) y lee el material de marca en busca de colores, fuentes y logotipos: `theme/branding/` (logos, ficheros de tipografías, guía, listas de colores) y `brief/`. La elección hecha al crear el proyecto es `project.yaml › theme.source`.
2. Con `tenant_default` toma el theme que la plataforma marca por defecto (`isDefault`) y no crea ni cambia nada. Con `branding` crea el theme a partir de `theme/branding/` (sin material, usa el por defecto y lo dice). En una sesión con una persona, o cuando esta pide otra cosa, lista los themes de la plataforma y eliges uno o creas uno nuevo: desde cero, desde un preset o como copia de uno existente. Un cambio en un theme cambia todos los contenidos que lo usan, así que, para cambiar solo un curso, el agente copia el theme y enlaza la copia.
3. Lo adapta con los colores y las fuentes de la marca (`update_theme`) y te cuenta los avisos de la plataforma.
4. Guarda el resultado de `get_theme` en `.cache/theme/get_theme.json` y ejecuta `coursekit theme import .cache/theme/get_theme.json`. Eso escribe `theme/tokens.json` y `theme/tokens.css` con un `origin`: id del theme, nombre, versión y fecha. Imprime las notas y el contraste de cada par de colores; si algún par no llega al mínimo, el color se corrige en la plataforma y se vuelve a importar, nunca se edita en los tokens.
5. Te resume el resultado. **El theme lo validas tú, como validas el diseño.**

Dónde están los tokens:

| Ámbito | Ficheros | Cómo |
|---|---|---|
| Proyecto (lo heredan todos los cursos) | `theme/tokens.json`, `theme/tokens.css` | `/define-theme` |
| Un curso (gana para ese curso) | `courses/<CODE>/theme/tokens.json`, `tokens.css`; el id del theme se anota en `course.yaml › slxd.theme_id` | `/define-theme <CODE>` |

`coursekit theme show` imprime qué tokens se aplican (`coursekit theme show --course PWD` para un curso) y de dónde vienen: los del proyecto o los del curso, el theme de la plataforma con su id y su versión, y cuándo se importaron. `coursekit theme tokens` reescribe el CSS, `coursekit theme check` mide el contraste y `coursekit theme import FILE [--course CODE]` deriva los tokens; las opciones están en [`coursekit theme`](03-commands.md#coursekit-theme).

Dónde encaja en el flujo: cuando el proyecto ya existe y antes de producir multimedia, idealmente justo después de `/new-course` (que en su resumen te avisa si el proyecto no tiene tokens). El montaje usa el mismo theme (mira [Montaje y entrega](08-assembly-and-delivery.md#el-theme-del-curso)).

La salvaguarda. Los tokens de diseño solo se dan por buenos cuando vienen de la plataforma:

- `coursekit media plan` avisa cuando un curso tiene infografías, esquemas, GIF animados, simulaciones o vídeos y los tokens faltan o están escritos a mano.
- `coursekit media set CODE ID --status produced` (o `uploaded`) para esos cinco tipos se **rechaza** salvo que los tokens estén derivados de la plataforma. `--force` se salta la salvaguarda cuando asumes el riesgo.
- El recurso recuerda con qué tokens se hizo. Si vuelves a importar el theme y cambian los colores o las fuentes, `coursekit media plan` dice qué recursos hay que producir otra vez.
- `coursekit doctor` tiene una sección «Theme del proyecto» que te dice si los tokens del proyecto están derivados, faltan o están escritos a mano.

La lista de tipos que necesitan tokens es `uses_theme` en la configuración de `media` ([Configuración](04-configuration.md#media-opciones-de-producción)).

Notas: si el theme de la plataforma tiene modo oscuro, los tokens son los del modo claro. El texto atenuado, las superficies, la línea, el radio, el espaciado y la sombra no existen en el theme de la plataforma; coursekit los deriva y la importación los enumera.

Con el backend de montaje `html` no hay theme de plataforma. Los tokens se derivan de las variables CSS de la hoja de estilos `theme/maqueta.css` puesta sobre el layout base del paquete (`--color-accent`, `--color-text`, `--font-family`, `--radius`...). `/define-theme` escribe o adapta esa hoja de estilos con el material de `theme/branding/` y ejecuta `coursekit theme import theme/maqueta.css` (sin hoja y sin material, `coursekit theme import` sin fichero deriva los tokens de la maqueta base); los tokens llevan como origen la hoja de estilos y su huella. El paquete se estila con el layout base, después los tokens, después `theme/maqueta.css` del proyecto y `courses/<CODE>/theme/maqueta.css` del curso si existe, que pueden reestilar cualquier cosa.

## Cambios tras la aprobación

coursekit compara lo que hay en disco con las huellas tomadas en cada paso, así que ningún cambio pasa inadvertido.

| Qué cambia | Qué ocurre |
|---|---|
| El diseño se exporta de nuevo con contenido distinto después de firmarse | `status` muestra "hay que aprobar el diseño de nuevo". `verify`, `approve content` y la skill de redacción se detienen hasta que firmes otra vez con `coursekit approve design`. Las unidades conservan su progreso (estado, quién las redactó y revisó, registro de revisión y enlaces; se emparejan por su id de SLXD) y las unidades nuevas empiezan en `pending`. Hasta el montaje el estado del curso se vuelve a derivar de las unidades (no retrocede a `design_approved` si ellas van más adelantadas); desde `assembly` en adelante se queda como está |
| Se edita una unidad revisada | el siguiente `verify` la devuelve a `verified` y lista las partes cambiadas; `coursekit review` revisa entonces solo esas partes |
| Se edita una unidad aprobada | el siguiente `verify` la devuelve a `verified` (o a `writing` si ya no pasa, o a `reviewed` si no cambió ninguna parte revisada). La aprobación anterior queda en `approvals` como historial; firmas de nuevo |
| Una unidad deja de pasar `verify` | vuelve a `writing` |
| Una unidad retrocede mientras el curso está entre `design_approved` y `media` | el estado del curso retrocede con ella |
| Una unidad retrocede mientras el curso está en `assembly` o más allá | retrocede la unidad, pero el estado del curso se queda; firma la unidad otra vez y vuelve a montar |
| Cambia un recurso multimedia | su recurso vuelve a `pending` la próxima vez que ejecutes `coursekit media extract` |
| El cliente pide cambios (`coursekit client CODE changes`) | la ronda se cierra y el curso vuelve a `assembly`; aplica los cambios, vuelve a montar y abre la ronda siguiente con `send` |
| Firmas una unidad cuyo contenido cambió después de su revisión con IA | `coursekit approve content` se niega y nombra las partes; revisa de nuevo, o `--force` para firmar igualmente |

Regla práctica: tras cambiar cualquier cosa a mano, ejecuta `coursekit verify <CODE>`. `verify` es lo que hace retroceder una unidad; como red de seguridad, `coursekit approve content` también se niega a firmar una unidad que cambió después de su revisión con IA (nombra las partes), salvo que añadas `--force`.

## Ejemplo completo

Un curso de dos horas sobre contraseñas seguras para el cliente ACME, con código `PWD`. Los comandos que empiezan por `/` se escriben en la herramienta de IA, que abres con `claude` (u `opencode`, `codex`) en la carpeta del proyecto.

```bash
coursekit init acme-courses
cd acme-courses
```

Primero el material de referencia (opcional) y luego el diseño:

```bash
cp ~/Documents/politica-de-contrasenas.pdf brief/sources/
coursekit brief
```

```text
/new-course "Contraseñas seguras" 2 --code PWD
/design-change PWD Añade una unidad sobre gestores de contraseñas
/approve-design PWD
```

Define el theme una vez, en cualquier momento antes de producir multimedia (el agente lo propone a partir del material de marca; lo validas tú):

```text
/define-theme
```

Firma tú el diseño, en una terminal o desde el chat:

```bash
coursekit approve design PWD
coursekit status PWD
```

Redacta y revisa, unidad a unidad o todas a la vez:

```bash
coursekit write PWD 1
coursekit verify PWD --unit 1
coursekit review PWD 1
```

Lee la unidad y la revisión con IA, edita lo que quieras, comprueba y firma:

```bash
coursekit verify PWD --unit 1
coursekit approve content PWD --unit 1
```

Con todas las unidades firmadas (`coursekit status PWD` muestra `media`), produce y monta:

```text
/produce-media PWD
/assemble PWD
```

Si el cliente revisa el curso, abre una ronda, deja que el agente trate los comentarios y cierra la ronda (paso opcional, obligatorio solo si el proyecto lo exige):

```bash
coursekit client PWD send --to "equipo de formación de ACME"
```

```text
/client-feedback PWD
```

```bash
coursekit client PWD changes --note "Dos cambios de redacción en la unidad 1"
coursekit client PWD send --to "equipo de formación de ACME"
coursekit client PWD approve --by "responsable de formación de ACME"
```

Después entrega:

```text
/deliver PWD 1.0
```

```bash
coursekit status
```

Siguiente: [Comandos](03-commands.md)
