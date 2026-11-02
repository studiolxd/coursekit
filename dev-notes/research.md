# Búsqueda web (`coursekit research`): lo pendiente

La función está publicada y documentada (`docs/*/03-commands.md › coursekit research`, `04-configuration.md`,
`05-agents.md › Source search`). Esta nota guarda lo que falta por comprobar y por qué se diseñó así.

## Pendiente

- Que los agentes la usen en un curso entero (el README lo da por demostrar).
- La búsqueda nativa de opencode, cuando no hay proveedor: sin comprobar.
- Codex sin interfaz: que `--search` funcione con `exec` no está comprobado en una sesión real (`launch.py` lo añade a los
  roles que buscan y `05-agents.md` lo da por bueno).
- Las condiciones de datos de cada proveedor (Exa ofrece *Zero Data Retention* en `/search`): la documentación solo dice
  que se revisen; comprobarlas antes de nombrar ninguna.
- `--status` no muestra el tope de fuentes de referencia del diseño (`reference_sources_max`), como preveía el plan:
  añadirlo o descartarlo.

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

## Fundamento de las decisiones

- El proveedor va en el `.env` y no en `project.yaml` porque la clave, y por tanto el proveedor, es de cada persona, como
  `WRITER_AGENT`.
- Sin endpoints que responden: queremos fuentes primarias, no la síntesis de otro modelo.
- Siguiendo la guía de Exa, nada de `includeDomains` ni filtros de fecha salvo que la persona apruebe una lista: las
  preferencias van en la consulta, y coursekit reordena, nunca filtra.
- Localización por hreflang comprobada con 103 URL oficiales en inglés de la prueba: encuentra la versión en español en
  Microsoft, Google, GitHub, Apple, Slack, EDPB, la Oficina de Publicaciones de la UE, MDN, LibreOffice y OWASP Top 10, y
  las deja en inglés cuando el sitio no la tiene (NIST, W3C, git-scm, ICO).
- No es herramienta del servidor MCP de coursekit (sería un segundo camino para lo que el comando ya da con `--json`), ni
  se usan los servidores MCP o conectores de los proveedores: se saltarían el país y el idioma, la localización, el
  registro, el límite y la salida común, y traen herramientas que redactan.
- ISO responde `403` y sus normas son de pago: no es fuente para el brief. EUR-Lex se abre con el navegador de la máquina
  (probado con el RGPD: 66.119 palabras, con el artículo 33).
