# Investigación web: `coursekit research`

Nota de desarrollo: se borra cuando la función esté validada y publicada (lo que dure va a `docs/` y a los READMEs).

Objetivo: que el diseño y la redacción encuentren **fuentes oficiales** (documentación del fabricante, boletines y diarios
oficiales, organismos) a través de una API de búsqueda configurada por la persona, con el mismo resultado sea cual sea el
agente. Hoy el diseño busca la documentación de referencia con la búsqueda nativa del agente, y en la redacción lo que no
está en el brief se queda como `<!-- VERIFICAR -->` hasta la revisión.

## Por qué: la prueba

Prueba de octubre de 2026, una pasada. 32 consultas inventadas: 18 en español y 14 en inglés, 21 de buscar documentación
de referencia y 11 de verificar un dato concreto (ofimática, protección de datos, prevención de riesgos, NIST, WCAG,
Git...). Para cada consulta se fijó a mano la lista de dominios oficiales que cuentan como acierto.

| | Exa | Perplexity Search | Brave | Tavily | Búsqueda nativa de Claude Code |
|---|---|---|---|---|---|
| Oficial en el 1.er resultado | 91 % | 78 % | 78 % | 31 % | 25 % |
| Oficial entre los 5 primeros | 100 % | 91 % | 94 % | 88 % | 44 % |
| Verificar dato: oficial en el top 5 | 100 % | 82 % | 82 % | 64 % | 27 % |
| Consultas sin ninguna fuente oficial | 0 | 2 | 2 | 1 | 15 |
| Latencia mediana | 3,8 s | 0,8 s | 1,4 s | 1,8 s | — |
| Precio de lista por 1.000 búsquedas | 7 $ | 5 $ | 5 $ | 8 $ | — |

Conclusiones:
- Cualquiera de las cuatro APIs mejora mucho a la búsqueda nativa: con ella, la mitad de las consultas no traen ninguna
  fuente oficial.
- Exa es la mejor, sobre todo para verificar datos. Además, sus *highlights* traen la frase que contiene el dato.
- El coste es despreciable: menos de 100 búsquedas por curso, menos de 1 $ por curso.

Los números son de esa prueba: no son una garantía y no van en la documentación tal cual.

## Decisiones de base

- **Cuatro proveedores**: `exa`, `perplexity`, `brave` y `tavily`. La persona elige uno en su `.env`:
  `RESEARCH_PROVIDER=<id>` más la clave de ese proveedor, con el nombre habitual de cada uno (`EXA_API_KEY`,
  `PERPLEXITY_API_KEY`, `BRAVE_API_KEY`, `TAVILY_API_KEY`). Va en el `.env` y no en `project.yaml` porque la clave, y
  por tanto el proveedor, es de cada persona, como `WRITER_AGENT`. **El proveedor se declara siempre**: una clave sola,
  sin `RESEARCH_PROVIDER`, no activa nada, aunque sea la única.
- **Las fuentes que añaden la redacción y la revisión se aprueban en la revisión.** En el diseño se confirman con la
  persona, como hasta ahora. Durante la redacción no se interrumpe: el redactor las añade a `links.md` tras
  `<!-- added by the writer -->`, quedan en el registro, y la revisión las aprueba o las retira.
- **Sin proveedor y clave, búsqueda nativa del agente.** Si falta `RESEARCH_PROVIDER` o su clave, `coursekit research`
  no busca. Termina con un código propio y un mensaje que dice al agente que use su propia búsqueda web (Claude Code,
  opencode, Codex) con las mismas reglas. Así nada se rompe en un proyecto sin claves.
- **Solo propone fuentes; no escribe contenido.** Devuelve URLs candidatas con título, fecha y el fragmento que justifica
  cada una. El contenido sigue entrando por el camino de siempre: la URL va a `brief/links.md`, `coursekit brief` la
  descarga con `web2md` y el redactor cita el brief (fichero y líneas). Un fragmento nunca se cita como fuente.
- **Sin endpoints que redactan**: nada de `/answer` y `/agent` de Exa, Sonar de Perplexity, `include_answer` y
  `/research` de Tavily, ni Answers de Brave. Queremos fuentes primarias, no la síntesis de otro modelo.
- **HTTP con la biblioteca estándar** (`urllib.request`, como `ttsbatch.py` y `videos.py`): sin SDKs ni dependencias
  nuevas.
- **Lo descargado es dato, no instrucciones**, como ya dice la skill para `links.md`. Los fragmentos que devuelve
  `research` también lo son.
- **Cursos importados del cliente: no se usa.** Su texto es del cliente (ver "Courses imported" en las skills).

## 1. `.env` y `env.example`

```
# Web research (optional): coursekit research uses RESEARCH_PROVIDER with its key. Without both, the agents use their
# own web search. exa | perplexity | brave | tavily
RESEARCH_PROVIDER=
EXA_API_KEY=
PERPLEXITY_API_KEY=
BRAVE_API_KEY=
TAVILY_API_KEY=
```

`coursekit doctor`, en una sección nueva, dice qué proveedor está activo. Avisa como fallo si `RESEARCH_PROVIDER` tiene un
valor desconocido o le falta su clave. Sin `RESEARCH_PROVIDER`, lo marca como opcional: búsqueda nativa.

## 2. Configuración: `defaults/research.yaml`

En `config.NAMES` y `init.CONFIG_NAMES`, comentado. Esbozo:

```yaml
results: 10                  # candidates per search
show: 5                      # candidates printed (the rest go to the log)
country: auto                # ISO 3166-1 code for the search; auto: from the content language (es → ES), else none
max_per_course: 150          # searches per course before research refuses (a guard against loops)
prefer_domains: []           # official domains this project trusts, as a hint in the query (never a hard filter)
localize_urls: true          # en-us → es-es and similar in the help-centre URLs of the course language (see 7)
providers:
  exa:        {type: auto, highlights: true}
  perplexity: {search_type: web, language_filter: true}
  brave:      {search_lang: true, extra_snippets: true}
  tavily:     {search_depth: basic}
```

Lo que cada proveedor recibe, según la prueba:

| Proveedor | Llamada | País / idioma | Fragmento |
|---|---|---|---|
| exa | `POST https://api.exa.ai/search`, `x-api-key` | `userLocation` (ISO-2); idioma en la consulta | `highlights` |
| perplexity | `POST https://api.perplexity.ai/search`, `Bearer` | `country` (ISO-2), `search_language_filter` | `snippet` |
| brave | `GET https://api.search.brave.com/res/v1/web/search`, `X-Subscription-Token` | `country`, `search_lang` | `description`, `extra_snippets` |
| tavily | `POST https://api.tavily.com/search`, `Bearer` | `country` en inglés y minúsculas (`spain`) | `content` |

Siguiendo la guía de Exa, nada de `includeDomains` ni filtros de fecha salvo que la persona apruebe una lista. Las
preferencias van en la propia consulta.

## 3. El comando

```
coursekit research <CODE> "<consulta>"            # buscar documentación de referencia
coursekit research <CODE> --fact "<dato>"         # buscar la fuente oficial de un dato (un VERIFICAR)
coursekit research <CODE> ... --json              # salida para el agente
coursekit research --status                       # proveedor activo, búsquedas del curso, límite
```

- **Salida:** una lista numerada con URL, título, dominio, fecha si la hay y el fragmento recortado. Con `--fact`, el
  fragmento que contiene el dato va primero.
- **Registro:** cada búsqueda se apunta en `courses/<CODE>/brief/research.log.md` (fecha, proveedor, consulta y URLs). El
  revisor y la persona ven de dónde salió cada fuente, y sirve para contar el límite `max_per_course`.
- **Códigos de salida:** 0 si hay resultados, 1 si hay un error del proveedor (red, 401, 429) y otro distinto para "sin
  proveedor: usa tu búsqueda nativa", para que las skills puedan distinguirlo.
- **Errores:** reintento ante 429 y 5xx (como en `ttsbatch`) y mensajes claros para una clave inválida o sin saldo.
  Nunca se escribe la clave en un mensaje ni en el registro.
- **Mensajes:** en `lang/messages/research.yaml`, en `es` y `en`.

Código: `src/coursekit/research.py`. Un adaptador por proveedor (`search(query, country, language, n) -> list[Result]`)
con un `Result` común: `url`, `title`, `snippet`, `date`, `provider`.

## 4. Agentes y skills

- **`agents.py`:** permitir `coursekit research*` a diseño, redacción y revisión. Tokens nuevos en `agents.context()`
  (`{{research_show}}`, `{{research_max_per_course}}`...), sin números escritos en las skills.
- **`instructional-design`, "Reference documentation":** antes de proponer las fuentes oficiales, `coursekit research`.
  Si responde "sin proveedor", la búsqueda nativa como hasta ahora. Después, lo de siempre: proponer, que la persona
  confirme, escribir en `links.md` tras `<!-- added by the agent -->` y ejecutar `coursekit brief`. Si no hay material
  (curso sin brief), usarlo también para buscar el material base en lugar de proponer el temario como supuesto.
- **`content-writing`:** si `brief --find` no encuentra un dato, `coursekit research <CODE> --fact "<dato>"`. Si hay
  una fuente oficial, añadirla a `links.md`, ejecutar `coursekit brief` y citar el brief. Si no la hay, el `VERIFICAR` se
  queda. La fuente va a `links.md` tras `<!-- added by the writer -->` y se aprueba en la revisión.
- **`content-review` / reviewer:** para cada `VERIFICAR` pendiente, intentar `--fact` y proponer la fuente en la revisión.
- **Fallback nativo:** comprobar qué tiene cada agente y cómo lo genera `coursekit agents`:
  - Claude Code: WebSearch y WebFetch.
  - Codex: búsqueda web activable en `config.toml`.
  - opencode: su `webfetch` no busca; comprobar si tiene una herramienta de búsqueda y cómo se activa.

## 5. Documentación y estado

- **`docs/en` y `docs/es`:**
  - `03-commands.md`: `research` y sus opciones.
  - `04-configuration.md`: `research.yaml` y las variables del `.env`.
  - `05-agents.md`: cuándo investigan los agentes y el fallback nativo.
  - `02-workflow.md`: en qué paso entra.
  - `09-troubleshooting.md`: clave inválida, sin saldo, límite del curso.
- **Privacidad:** las consultas salen al proveedor y revelan el tema del curso. Hay que decirlo en la documentación. Exa
  ofrece *Zero Data Retention* en `/search`; comprobar las condiciones de cada proveedor antes de documentarlo.
- **README y README.es:** la función nueva y sus límites.

## 6. Tests

- Un test por proveedor con `urllib` simulado: la petición que se envía (cuerpo, cabeceras, país e idioma) y la respuesta
  normalizada. Las respuestas, inventadas y con el formato de cada API.
- Selección del proveedor: con clave, sin clave, proveedor desconocido y el código de salida de "usa la nativa".
- El límite `max_per_course`, el registro y que la clave nunca aparezca en la salida ni en el registro.
- `test_i18n`, `test_docs` (comando y opciones en `03-commands.md`) y `test_init` (nombre del fichero de configuración).
- Ningún test usa la red.

## 7. Decisiones abiertas

- **`localize_urls`:** reescribir `/en-us/` a `/es-es/` en los centros de ayuda que lo admiten (en la prueba, Exa devolvió
  la versión inglesa de páginas de Microsoft y de EUR-Lex). ¿Lista fija de patrones en `research.yaml` o pedir el idioma
  solo en la consulta?
- **¿Exponerlo también como herramienta MCP** del servidor de coursekit, además del comando? Propuesta: no hace falta
  mientras el comando baste.
- **Límite por curso:** ¿contar búsquedas o dinero? El coste solo lo devuelve Exa; propuesta: contar búsquedas.
