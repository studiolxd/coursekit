# {name}

Un proyecto de cursos hecho con [coursekit](https://github.com/studiolxd/coursekit): desde aquí se diseñan, escriben,
revisan, ilustran, maquetan y entregan sus cursos, con agentes de IA que hacen el trabajo y personas que lo
firman. Este fichero lo genera `coursekit init` y lo refresca `coursekit init --update` (salvo que lo edites): las reglas de
este proyecto van en `brief/notes.md` y en `config/`.

La referencia completa está en la documentación de coursekit ([español](https://github.com/studiolxd/coursekit/tree/main/docs/es),
[inglés](https://github.com/studiolxd/coursekit/tree/main/docs/en)); `coursekit help` lista todos los comandos y
`coursekit <comando> --help` explica uno.

## Primeros pasos en una máquina

```bash
coursekit setup            # lo que el proyecto necesita en esta máquina (añade --media para vídeo y voz)
coursekit doctor           # lo comprueba: herramientas, claves, conexiones
coursekit roles            # qué herramienta y modelo usa cada rol de agente (en .env)
```

Copia `.env.example` a `.env` y rellena las claves y los roles que uses. `coursekit config` muestra las reglas de producción
en vigor.

## El proceso

```text
 brief -> diseño -> [FIRMA DEL DISEÑO] -> redacción -> revisión IA -> revisión editorial -> [FIRMA DE CADA UNIDAD]
          \                                                                                       |
           +-> tema (una vez por proyecto, antes de los medios) ----+                             |
                                                                    v                             |
 entregado <- [revisión del cliente: opcional] <- maquetación <- medios <-------------------------+
```

Los comandos con `/` se lanzan dentro de tu herramienta de IA (Claude Code, opencode; en Codex, pide el comando por su
nombre). Los demás, en una terminal. Solo firma una persona: desde el chat de un agente, empieza la línea con `!`
(`! coursekit approve design PWD`).

| # | Fase | Quién | Comandos |
|---|---|---|---|
| 1 | Brief | persona | deja el material en `courses/<CODE>/brief/` y lanza `coursekit brief <CODE>` |
| 2 | Diseño instruccional | agente de diseño | `/new-course "Título" <horas>`, `/design-change` |
| 2b | Firma del diseño | **persona** | `/approve-design` y después `coursekit approve design <CODE>` |
| 2c | Tema (una vez por proyecto) | agente de diseño y después **persona** | `/define-theme`, `coursekit theme show` |
| 3 | Redacción | agente redactor | `coursekit write <CODE> [N]` (o `/write-unit`), `coursekit verify <CODE>` |
| 4 | Revisión IA | agente revisor | `coursekit review <CODE> [N]` (o `/review-unit`) |
| 5 | Revisión editorial | **persona** | lee y edita cada unidad, `/approve-unit` y después `coursekit approve content <CODE> --unit N` |
| 6 | Medios | agente de medios | `/produce-media`, `coursekit media …`, `coursekit video …` |
| 7 | Maquetación | agente de maquetación | `/assemble`, `coursekit assemble …` |
| 8 | Revisión del cliente (opcional) | **persona** y después agente de maquetación | `coursekit client …`, `/client-feedback` |
| 9 | Entrega | agente de maquetación | `/deliver`, `coursekit delivery …` |

El Markdown de cada unidad (`courses/<CODE>/units/`) es la fuente de verdad: lo que esté mal en el resultado se corrige ahí y
se vuelve a maquetar, nunca se edita en la salida.

**Sin revisiones.** `coursekit handoff "Título" <horas>` lleva un curso de su título a su entrega sin nadie, y coursekit firma
como Coursekit Handoff; `coursekit handoff <CODE>` continúa uno que se paró. Su informe queda en
`courses/<CODE>/handoff-report.md`.

## Cada día

```bash
coursekit status [CODE]             # dónde está cada curso y qué viene después
coursekit verify <CODE>             # comprueba las unidades contra las reglas del proyecto
coursekit hold <CODE> / resume      # pausar un curso y reanudarlo
coursekit sync <CODE>               # traer otra vez el diseño de la plataforma
```

## Medios y vídeo

```bash
coursekit media plan <CODE>                    # los recursos que faltan y cómo se puede hacer cada uno
coursekit video gallery --serve                # las escenas y capas de los vídeos, en vivo, con el estilo del proyecto
coursekit video gallery                        # lo mismo, renderizado: la prueba antes de firmar la guía de estilo
coursekit video check|voice|render <CODE> <ID> # un vídeo: comprobar su guion, locutarlo, renderizarlo
coursekit voice                                # la voz de las locuciones
```

El aspecto de los vídeos está en `config/video.yaml` (formas, pesos, tipografía, transiciones, lo que puede hacer cada
escena); su versión completa y comentada, con todos los valores, es `config/video.example.yaml`.

## Maquetación y entrega

```bash
coursekit assemble plan <CODE>      # backend creator: el plan de cada unidad, después diff y applied (lo hace /assemble)
coursekit assemble build <CODE>     # backend html: el paquete SCORM de cada unidad
coursekit preview <CODE>            # verlo antes de entregar
coursekit delivery check <CODE>     # si el curso se puede entregar, o por qué no (/deliver hace el resto)
```

El backend de maquetación de este proyecto es `{backend}`.

## Las carpetas

| Carpeta | Qué contiene |
|---|---|
| `brief/` | material y notas para todos los cursos del proyecto (`notes.md`: las reglas del cliente) |
| `courses/<CODE>/` | un curso: su `course.yaml`, su brief, su diseño, sus unidades, sus medios, sus revisiones |
| `config/` | las reglas del proyecto (`<name>.yaml`) y sus ejemplos completos (`<name>.example.yaml`) |
| `theme/` | el tema y los tokens de diseño; `theme/branding/`, el material de la marca |
| `.agents/` | ajustes propios de las skills y comandos de los agentes (`coursekit agents` los regenera) |
