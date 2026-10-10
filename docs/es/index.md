# Documentación de coursekit

coursekit convierte una carpeta en un proyecto de producción de cursos e-learning asistida por IA, con personas que firman en cada punto de control.

## Qué es coursekit

coursekit es una herramienta de línea de comandos (`coursekit`) que dirige la producción de cursos e-learning a través de un proceso fijo:

1. **Brief**: dejas el material de referencia (documentos, enlaces, notas) y coursekit lo convierte para los agentes.
2. **Diseño instruccional**: un agente propone unidades, apartados, objetivos y horas; **tú lo firmas**.
3. **Redacción**: un agente escribe cada unidad en un formato Markdown fijo, y `coursekit verify` lo comprueba con las reglas de producción.
4. **Revisión con IA**: un segundo agente (otra herramienta u otro modelo) revisa cada unidad.
5. **Revisión editorial y firma**: **tú lees cada unidad y la firmas**.
6. **Multimedia**: se planifican y producen imágenes, gráficos, vídeo, audio y demos. Los gráficos, simulaciones y vídeos usan el theme del proyecto, que `/define-theme` define una sola vez.
7. **Montaje**: el Markdown aprobado se monta, nunca al revés: se carga en la plataforma de autoría (SLXD Creator) o, con el backend html, es el propio coursekit quien construye un paquete SCORM por unidad.
8. **Revisión del cliente** y **entrega**: los paquetes SCORM (exportados de la plataforma o construidos por coursekit) se registran y se publican en una carpeta compartida con una hoja de seguimiento.

Los agentes redactan; las decisiones son de las personas. Solo una persona puede firmar (`coursekit approve`): los ajustes de agente que se generan para Claude Code y opencode prohíben a los agentes ejecutarlo (y las demás decisiones de las personas: `client`, `hold`, `resume`, `handoff`).

coursekit funciona con [Claude Code](https://claude.com/claude-code), opencode y Codex, de forma intercambiable, y se ejecuta en macOS, Windows y Linux.

## Para quién es

- **Responsables de producción y diseñadores instruccionales** que firman diseños y unidades y siguen cada curso con `coursekit status`.
- **Editores y revisores** que leen las unidades y las firman.
- **Responsables técnicos** que preparan el proyecto, los equipos, las herramientas de agente y la carpeta compartida.

No hace falta programar. Necesitas una terminal y una de las herramientas de IA compatibles.

## Mapa de la documentación

| Fichero | Qué cubre |
|---|---|
| [Primeros pasos](01-getting-started.md) | requisitos, instalación, `coursekit init` paso a paso, el primer curso |
| [Flujo de trabajo](02-workflow.md) | todo el proceso, estados del curso y de las unidades, quién hace qué, cambios tras la aprobación |
| [Comandos](03-commands.md) | todos los comandos y opciones |
| [Configuración](04-configuration.md) | `project.yaml`, `.env`, `config/`, `course.yaml` |
| [Agentes](05-agents.md) | Claude Code, opencode, Codex, roles, modelos, skills, MCP |
| [Contenido](06-content.md) | carpetas del curso, formato del contenido, directivas, verificación |
| [Multimedia](07-media.md) | planificar y producir multimedia, voz, subtítulos |
| [Montaje y entrega](08-assembly-and-delivery.md) | SLXD Creator, SCORM, carpeta compartida, catálogo |
| [Solución de problemas](09-troubleshooting.md) | `coursekit doctor`, `coursekit setup`, problemas habituales, preguntas frecuentes |

## Inicio rápido

```bash
uv tool install slxd-coursekit
coursekit init acme-courses
cd acme-courses
coursekit doctor
coursekit run new-course "Contraseñas seguras" 2 --code PWD
```

El mismo último paso funciona dentro de tu herramienta de IA: ábrela en la carpeta del proyecto y escribe `/new-course "Contraseñas seguras" 2 --code PWD`. Ejecuta `/define-theme` una vez por proyecto antes de producir multimedia. Después, `coursekit status` te dice siempre en qué punto está cada curso y cuál es el siguiente paso.

Siguiente: [Primeros pasos](01-getting-started.md)
