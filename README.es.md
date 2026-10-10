# coursekit

[English](README.md)

Producción de cursos e-learning asistida por IA: material de referencia, diseño instruccional,
redacción, revisión, multimedia, montaje y entrega SCORM, con firmas humanas en los puntos de
control. Funciona con [Claude Code](https://claude.com/claude-code), opencode y Codex, de forma
indistinta.

Paquete `slxd-coursekit`, comando `coursekit`. De Studio LXD.

> En desarrollo inicial (`0.1.4`). Publicado en PyPI como `slxd-coursekit`.

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

Para actualizar una copia instalada: `uv tool upgrade slxd-coursekit`. Nada más: el primer comando en cada proyecto regenera sus ficheros gestionados y los de los agentes. Una versión concreta: `uv tool install slxd-coursekit==0.1.4`.

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
