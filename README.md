# coursekit

[Español](README.es.md)

AI-assisted e-learning course production: reference material, instructional design, writing, review,
media, assembly and SCORM delivery, with human sign-offs at the control points. It works with
[Claude Code](https://claude.com/claude-code), opencode and Codex, interchangeably.

Package `slxd-coursekit`, command `coursekit`. By Studio LXD.

> Early development (`0.7.0`). Published on PyPI as `slxd-coursekit`.

## What it does

`coursekit` turns a folder into a **course production project** and drives the work through a fixed
process in which AI agents do the drafting and people keep the decisions:

1. **Brief** — you drop the reference material (documents, links, notes); coursekit converts it for the agents.
2. **Instructional design** — an agent proposes units, sections, objectives and hours; **you sign it off**.
3. **Writing** — an agent writes every unit in a fixed Markdown format; `coursekit verify` checks it against the production rules.
4. **Review** — a second agent (another tool or model) reviews each unit; **you sign off each unit**.
5. **Media** — images, graphics, video, audio and interactive demos are planned and produced with the tools you have.
6. **Assembly** — from the approved Markdown, never the other way round, with one of two backends: the content is loaded into the authoring platform (slxd creator), or coursekit itself builds a SCORM package per unit (the html backend, no platform in between). You choose per project or per course.
7. **Delivery** — SCORM packages (exported from the platform, or built by coursekit) are recorded and published to a shared folder with a tracking spreadsheet.

Only a person can sign (`coursekit approve`); agents are forbidden to run it.

## Status

Early development. What changed in each version is in the [changelog](CHANGELOG.md).

- **Solid:** the process from brief to SCORM delivery, with both backends (slxd creator and the html backend), in Spanish and English; the decision-based approach with simulations; the local instructional design; the handoff mode. Used end to end.
- **New:** the options of the questions shuffled for each learner, with `verify` refusing a feedback that names an option by its position; the gallery of the media of a course (`coursekit media gallery`); the visual support of the sections and the resource types `illustration` and `icon`; pedagogical criteria in the writing, job aids and crosshairs on the images with points. The details are in the [changelog](CHANGELOG.md).
- **In progress:** captures of real applications that coursekit makes itself (`coursekit capture`): web applications in the browser, the course itself, a desktop window and the terminal mode. Tested on macOS, and the terminal mode on Linux; on Windows and Linux with X11 the desktop capture is written but not yet tested on real machines, and the terminal mode has not yet carried a whole handoff.
- **To prove on a whole course:** the migration from eXeLearning with real agents, the Gemini TTS batch, the brand step of the theme agent, the illustration sources of the brand (`coursekit media stock`), the tests apart or as a question bank (not yet assembled apart in creator nor imported in a real LMS), the pedagogical cycle, the job aids (not yet uploaded to creator), the crosshairs, the official sources found by the agents, the lessons of the pilot course and the shuffled options. Each one was tried on its own, against the real service where there is one.
- **Not yet:** reading eXeLearning 4 packages (`.elpx`) or HTML exports of a site, publishing the components of the html backend as a package of their own, more languages than Spanish and English.

The creator platform has known gaps that the pipeline works around: [Known limits of the creator backend](docs/en/08-assembly-and-delivery.md#known-limits-of-the-creator-backend).

## Install

You need [uv](https://docs.astral.sh/uv/); it brings the right Python (3.12 or 3.13). To work on courses you also need git, an AI tool (Claude Code, opencode or Codex) and the URL of your SLXD Creator MCP server; see [Getting started](docs/en/01-getting-started.md#requirements).

```bash
uv tool install slxd-coursekit
coursekit --version
```

To install the development version straight from the repository instead: `uv tool install git+https://github.com/studiolxd/coursekit`.

To try it from a clone, with changes taking effect immediately:

```bash
uv tool install --editable /path/to/coursekit
```

Two optional extras: `docs` converts the documents of the reference material and of the brand material (PDF, Word, PowerPoint, Excel, Outlook) to text, and `capture` makes the real captures of applications (`coursekit capture`). Name every extra you want in one command, because reinstalling with some removes the others: `uv tool install --force "slxd-coursekit[docs,capture]"` (from a clone: `uv tool install --force --editable "/path/to/coursekit[docs,capture]"`). `coursekit doctor` says which one is missing and gives the command. For now `capture` needs Python 3.12 (`--python 3.12`).

To update an installed copy: `uv tool upgrade slxd-coursekit`. Nothing else: the first command in each project regenerates its managed files and agent files. A specific version: `uv tool install slxd-coursekit==0.2.1`.

## Quick start

```bash
coursekit init my-courses        # a short wizard: language first, then everything else
cd my-courses
coursekit doctor                 # what is installed and configured here
```

Then open your AI tool in that folder and run:

```text
/new-course "Strong passwords" 2
```

or, from the terminal, without opening anything yourself:

```bash
coursekit run new-course "Strong passwords" 2
```

`coursekit status` always tells you where each course is and what the next step is.

## Languages

The tool speaks **Spanish and English**: the wizard asks the language first and everything after
(messages, help, spreadsheets, templates for people) follows it. Courses can be written in either
language; the content format adapts to it.

## Documentation

Full documentation, in English and Spanish, is in [`docs/`](docs/en/index.md)
([versión en español](docs/es/index.md)):

| | |
|---|---|
| [Getting started](docs/en/01-getting-started.md) | install, `init`, first course |
| [Workflow](docs/en/02-workflow.md) | the process, statuses and sign-offs |
| [Commands](docs/en/03-commands.md) | every command and option |
| [Configuration](docs/en/04-configuration.md) | `project.yaml`, `.env`, `config/`, `course.yaml` |
| [Agents](docs/en/05-agents.md) | Claude Code, opencode, Codex, roles, models, MCP |
| [Content](docs/en/06-content.md) | course layout, content format, directives, verification |
| [Media](docs/en/07-media.md) | planning and producing media, voice, subtitles |
| [Assembly and delivery](docs/en/08-assembly-and-delivery.md) | creator and html backends, SCORM, shared folder, catalog |
| [Troubleshooting](docs/en/09-troubleshooting.md) | `doctor`, common problems |

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`AGENTS.md`](AGENTS.md) (for coding agents working on the package).

## License

MIT — see [`LICENSE`](LICENSE).
