# coursekit

[English](README.md)

Producción de cursos e-learning asistida por IA: material de referencia, diseño instruccional,
redacción, revisión, multimedia, montaje y entrega SCORM, con firmas humanas en los puntos de
control. Funciona con [Claude Code](https://claude.com/claude-code), opencode y Codex, de forma
indistinta.

Paquete `slxd-coursekit`, comando `coursekit`. De Studio LXD.

> En desarrollo inicial (`0.5.0`). Publicado en PyPI como `slxd-coursekit`.

## Qué hace

`coursekit` convierte una carpeta en un **proyecto de producción de cursos** y guía el trabajo por un
proceso fijo en el que los agentes de IA redactan y las personas deciden:

1. **Brief** — dejas el material de referencia (documentos, enlaces, notas); coursekit lo convierte para los agentes.
2. **Diseño instruccional** — un agente propone unidades, apartados, objetivos y horas; **tú lo firmas**.
3. **Redacción** — un agente escribe cada unidad en un formato Markdown fijo; `coursekit verify` lo comprueba con las reglas de producción.
4. **Revisión** — un segundo agente (otra herramienta u otro modelo) revisa cada unidad; **tú firmas cada unidad**.
5. **Multimedia** — imágenes, gráficos, vídeo, audio y demos interactivas se planifican y se producen con las herramientas que tengas.
6. **Montaje** — a partir del Markdown aprobado, nunca al revés, con uno de dos backends: el contenido se carga en la plataforma de autoría (slxd creator), o es el propio coursekit quien construye un paquete SCORM por unidad (el backend html, sin plataforma de por medio). Se elige por proyecto o por curso.
7. **Entrega** — los paquetes SCORM (exportados de la plataforma o construidos por coursekit) se registran y se publican en una carpeta compartida con un Excel de seguimiento.

Solo una persona puede firmar (`coursekit approve`); a los agentes les está prohibido ejecutarlo.

## Estado

Desarrollo temprano (`0.3`). Qué está asentado y qué falta por demostrar:

- **Usado de extremo a extremo:** el proceso del brief a la entrega SCORM, con los dos backends (slxd creator y el backend html), en español y en inglés; el enfoque basado en decisiones con simulaciones; el diseño instruccional local; el modo handoff.
- **Nuevo y menos probado:** migrar un curso que ya existe desde paquetes de eXeLearning (`coursekit import`, `/update-unit`, vídeos de canales oficiales). Convierte paquetes reales sin perder texto, pero el flujo completo con agentes reales aún se está pilotando.
- **Nuevo:** vídeos como datos (`coursekit video`): un montaje de escenas en el tema del curso, con una biblioteca de átomos, moléculas y escenas que amplían el proyecto y cada curso, y cada escena dura lo que su voz; y su línea de tiempo para un editor (`coursekit video export`: DaVinci Resolve, Final Cut, Premiere).
- **Nuevo:** revisión de los audios y vídeos producidos (`coursekit media check`: sonoridad, subtítulos demasiado rápidos para leerlos, lo que está en pantalla y no se dice), su transcripción accesible y su pista de descripciones (`coursekit media transcript`), una hoja de contactos para mirar un vídeo sin reproducirlo (`coursekit media sheet`) y zooms de una grabación de pantalla que siguen a la locución (el componente `Screencast`).
- **Nuevo:** la voz de Gemini TTS (proveedor `gemini`, con indicación de estilo y el modelo fijado en cada curso), a mitad de precio: en el nivel `flex` por defecto, o en batch para todo un curso (`coursekit tts-batch`: en cola con `--batch`, recogido horas después, también por el handoff). Probada contra el servicio real; el batch aún no ha llevado un curso entero. Los guiones largos de Azure, Google y Gemini se unen ahora como audio sin comprimir y se codifican una sola vez.
- **Nuevo:** la marca en los recursos. `coursekit brand` lee el material de marca que se deja en `theme/branding/` (un libro de marca, un Storybook entero, la web de la empresa observada en un navegador) y saca sus fuentes, logos y tokens; el agente del theme escribe con él la guía de estilo de los recursos, que firma una persona (`coursekit approve media-style`), y propone el color de la marca para cada rol que la plataforma no tiene (`project.yaml › theme.roles`, `coursekit theme roles`). Las fuentes de la marca van dentro de los vídeos y de los SVG exportados a PNG. Probado con un Storybook y una web reales; el paso del agente aún no ha llevado un proyecto entero.
- **Nuevo:** fuentes de ilustraciones de la marca. La página de Magnific de un autor cuyas ilustraciones encajan con la marca va en `theme/branding/links.md`; `coursekit brand` guarda vistas previas de su obra como referencia del estilo, y `coursekit media stock` busca entre sus ilustraciones la que necesita un concepto, la toma en SVG y la recolorea a la tinta y el papel de la marca (`media › stock`), con su origen y su licencia en el manifiesto. Necesita `MAGNIFIC_API_KEY`; aún no se ha usado en un curso entero.
- **Nuevo:** dónde van las evaluaciones (`delivery › assessment`): dentro de cada unidad, como hasta ahora, o aparte en un paquete propio después de las unidades (`placement: separate`); y sus preguntas como lecciones de los paquetes o como banco de preguntas que importa el LMS (`format: aiken | gift | moodle-xml | qti`: con el backend creator lo exporta creator desde un contenido propio, con html lo escribe `coursekit delivery questions`), con `verify` rechazando los tipos de pregunta que el formato no admite. Probado con el backend html y los ficheros que escribe coursekit en los tests; aún no se ha montado aparte en creator ni importado en un LMS real.
- **Nuevo:** lenguaje inclusivo (`rules › inclusive_language`: `none`, `neutral` por defecto, `split`, `slash`): lo siguen el diseño, la redacción y la revisión, y `verify` avisa del masculino genérico y de las barras con un léxico por idioma.
- **Nuevo:** criterio pedagógico en la redacción. Cada apartado de contenido de un curso expositivo sigue un ciclo (`rules › expository.cycle`: un problema del trabajo del público, activación de lo que ya sabe, un ejemplo resuelto, práctica con menos ayuda cada vez, integración en su trabajo; un proyecto o un curso puede quitar cualquier parte), que comparten la introducción y el resumen de la unidad; la redacción sigue reglas de carga cognitiva, `verify` avisa de los tramos de prosa largos (`content.chunk_max_words`) y la revisión tiene un criterio de pedagogía. Aún sin probar en un curso completo.
- **Nuevo:** ayudas de trabajo (`job_aid`): una lista de comprobación o una guía rápida que el alumno descarga en PDF, escrita por la redacción en su recurso e impresa con una plantilla del tema (`theme/templates/job-aid.html`, firmada con la guía de estilo de los medios; `coursekit theme sample` imprime una muestra para ajustarla), etiquetada para lectores de pantalla y montada como descarga en los dos backends. Probado con el Chrome de macOS; aún no en un curso completo ni subido a creator.
- **Nuevo:** crucetas en las imágenes con puntos (`coursekit media anchors`): dónde va cada punto de un gráfico etiquetado y cada zona activa de una simulación, dibujado en la imagen desde el contenido para que quien revisa lo vea y pueda pedir moverlo; `verify` falla cuando dejan de coincidir. Aún sin usar en un curso completo.
- **Nuevo:** el mismo Excel de revisión para un diseño hecho en slxd que para uno local (`coursekit design CODE` lo escribe a partir de `matrix.json` y `validation.json`): competencias, objetivos con dónde se desarrollan, se practican y se evalúan, horas y palabras mínimas por apartado, calificación de los tests, errores comunes y la validación con los avisos esperados aparte. El Excel que exporta slxd se guarda como copia, en el idioma de la persona.
- **Nuevo:** fuentes oficiales con una API de búsqueda web (`coursekit research`: Exa, Perplexity, Brave o Tavily, elegida en el `.env`). El diseño busca con ella la documentación de referencia y quien redacta la fuente de un dato que el brief no tiene; solo propone direcciones, en el idioma del curso cuando el sitio tiene traducción, y entran en el curso por `brief/links.md`. Sin proveedor, los agentes usan su propia búsqueda web. `coursekit brief` abre ahora con el navegador de la máquina las páginas oficiales que rechazan una descarga directa (EUR-Lex, por ejemplo). Probado contra los cuatro servicios reales; los agentes aún no lo han usado en un curso entero.
- **Nuevo:** lo aprendido en un curso piloto completo. Cada curso guarda un registro de lo que decidieron las personas y de los rótulos de interfaz que comprobaron (`decisions.md`), que respetan la redacción y la revisión, y el revisor comprueba cada pendiente contra el estado actual antes de repetirlo. `verify` avisa de una actividad que no está escrita con la directiva de su tipo, de una pregunta del test que repite una situación de la práctica y de un error de una simulación sin consecuencia; las normas de redacción cubren las preguntas de ordenar con un solo orden, la retroalimentación y la interfaz actual. El manifiesto de recursos se bloquea mientras se escribe (agentes en paralelo), `media render` reintenta el navegador, `brief` convierte los PDF enlazados, la guía de estilo de los recursos cita cada línea de `notes.md` (y `approve media-style` avisa de las que faltan), los hablantes pueden ir sin retrato o con un avatar de la marca, y se firman varios guiones a la vez. Aún sin probar en un curso entero.
- **En desarrollo:** capturas de aplicaciones reales que hace el propio coursekit (`coursekit capture`): ya están los perfiles de las aplicaciones web, el permiso para capturar y el tapado de los datos personales de una grabación que aporta una persona (OCR, revisado y aprobado por una persona), y también un agente que maneja una aplicación web en el navegador con los datos personales sustituidos en pantalla (servidor MCP), con su vídeo grabado al repetir los pasos (`coursekit capture replay`), el propio curso (su paquete html servido en local o su enlace de revisión en creator, sin iniciar sesión), y la ventana de un programa de escritorio (tapada sobre los píxeles): en macOS; en Windows y Linux con X11 está escrita pero aún sin probar en máquinas reales.
- **Huecos conocidos de la plataforma creator** que el pipeline esquiva: [Límites conocidos del backend creator](docs/es/08-assembly-and-delivery.md#límites-conocidos-del-backend-creator).
- **Todavía no:** leer paquetes de eXeLearning 4 (`.elpx`) ni exportaciones HTML de un sitio, publicar los componentes del backend html como paquete propio, más idiomas que español e inglés.

## Instalación

Necesitas [uv](https://docs.astral.sh/uv/); él aporta el Python adecuado (3.12 o 3.13). Para trabajar los cursos necesitas además git, una herramienta de IA (Claude Code, opencode o Codex) y la URL de tu servidor MCP de SLXD Creator; mira [Primeros pasos](docs/es/01-getting-started.md#requisitos).

```bash
uv tool install slxd-coursekit
coursekit --version
```

Para instalar en su lugar la versión en desarrollo directamente desde el repositorio: `uv tool install git+https://github.com/studiolxd/coursekit`.

Para probarlo desde un clon, con los cambios aplicándose al instante:

```bash
uv tool install --editable /ruta/a/coursekit
```

Las capturas reales de aplicaciones (`coursekit capture`) necesitan el extra opcional `capture`: `uv tool install --force "slxd-coursekit[capture]"` (desde un clon: `uv tool install --force --editable "/ruta/a/coursekit[capture]"`).

Para actualizar una copia instalada: `uv tool upgrade slxd-coursekit`. Nada más: el primer comando en cada proyecto regenera sus ficheros gestionados y los de los agentes. Una versión concreta: `uv tool install slxd-coursekit==0.2.1`.

## Inicio rápido

```bash
coursekit init mis-cursos        # un asistente breve: primero el idioma, luego todo lo demás
cd mis-cursos
coursekit doctor                 # qué hay instalado y configurado aquí
```

Después abre tu herramienta de IA en esa carpeta y lanza:

```text
/new-course "Contraseñas seguras" 2
```

o, desde la terminal, sin abrir nada tú:

```bash
coursekit run new-course "Contraseñas seguras" 2
```

`coursekit status` te dice siempre en qué punto está cada curso y cuál es el siguiente paso.

## Idiomas

La herramienta habla **español e inglés**: el asistente pregunta primero el idioma y todo lo que
viene después (mensajes, ayuda, Excel, plantillas para personas) lo sigue. Los cursos se pueden
escribir en cualquiera de los dos; el formato del contenido se adapta.

## Documentación

La documentación completa, en español e inglés, está en [`docs/`](docs/es/index.md)
([English version](docs/en/index.md)):

| | |
|---|---|
| [Primeros pasos](docs/es/01-getting-started.md) | instalación, `init`, primer curso |
| [Flujo de trabajo](docs/es/02-workflow.md) | el proceso, los estados y las firmas |
| [Comandos](docs/es/03-commands.md) | todos los comandos y opciones |
| [Configuración](docs/es/04-configuration.md) | `project.yaml`, `.env`, `config/`, `course.yaml` |
| [Agentes](docs/es/05-agents.md) | Claude Code, opencode, Codex, roles, modelos, MCP |
| [Contenido](docs/es/06-content.md) | estructura del curso, formato, directivas, verificación |
| [Multimedia](docs/es/07-media.md) | planificar y producir multimedia, voz, subtítulos |
| [Montaje y entrega](docs/es/08-assembly-and-delivery.md) | backends creator y html, SCORM, carpeta compartida, catálogo |
| [Resolución de problemas](docs/es/09-troubleshooting.md) | `doctor`, problemas habituales |

## Contribuir

Mira [`CONTRIBUTING.es.md`](CONTRIBUTING.es.md) (en inglés: [`CONTRIBUTING.md`](CONTRIBUTING.md)) y [`AGENTS.md`](AGENTS.md) (para los agentes de código que trabajan en el paquete).

## Licencia

MIT — ver [`LICENSE`](LICENSE).
