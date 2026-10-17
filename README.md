# coursekit

[Español](README.es.md)

AI-assisted e-learning course production: reference material, instructional design, writing, review,
media, assembly and SCORM delivery, with human sign-offs at the control points. It works with
[Claude Code](https://claude.com/claude-code), opencode and Codex, interchangeably.

Package `slxd-coursekit`, command `coursekit`. By Studio LXD.

> Early development (`0.3.0`). Published on PyPI as `slxd-coursekit`.

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

Early development (`0.3`). What is solid and what is still to prove:

- **Used end to end:** the process from brief to SCORM delivery, with both backends (slxd creator and the html backend), in Spanish and English; the decision-based approach with simulations; the local instructional design; the handoff mode.
- **New and less proven:** migrating an existing course from eXeLearning packages (`coursekit import`, `/update-unit`, videos from official channels). It converts real packages without losing text, but the whole flow with real agents is still being piloted.
- **New:** videos as data (`coursekit video`): a montage of scenes in the theme of the course, from a library of atoms, molecules and scenes that the project and each course extend, each scene lasting what its voice lasts; and its timeline for an editor (`coursekit video export`: DaVinci Resolve, Final Cut, Premiere).
- **New:** checks of the audios and videos produced (`coursekit media check`: loudness, captions too fast to read, what is on screen and not said), their accessible transcript and track of descriptions (`coursekit media transcript`), a contact sheet to look at a video without playing it (`coursekit media sheet`), and zooms of a screen recording that follow the narration (the `Screencast` component).
- **New:** the Gemini TTS voice (provider `gemini`, with a style instruction and the model fixed in each course), at half the price: in the `flex` tier by default, or in batch for a whole course (`coursekit tts-batch`: queued with `--batch`, collected hours later, by the handoff too). Tried against the real service; the batch has not yet carried a whole course. The long scripts of Azure, Google and Gemini are now joined as uncompressed audio and encoded once.
- **New:** the brand in the media. `coursekit brand` reads the brand material left in `theme/branding/` (a brand book, a Storybook read whole, the website of the company observed in a browser) and takes out its fonts, logos and tokens; the theme agent writes from it the style guide of the media, which a person signs (`coursekit approve media-style`), and proposes the colour of the brand for each role the platform lacks (`project.yaml › theme.roles`, `coursekit theme roles`). The fonts of the brand go inside the videos and the SVGs exported as PNG. Tried with a real Storybook and website; the agent step has not yet carried a whole project.
- **New:** official sources through a web search API (`coursekit research`: Exa, Perplexity, Brave or Tavily, chosen in the `.env`). The design looks for the reference documentation with it and the writer for the source of a fact the brief does not have; it only proposes addresses, in the language of the course when the site has a translation, and they enter the course through `brief/links.md`. Without a provider the agents use their own web search. `coursekit brief` now opens in the browser of the machine the official pages that refuse a direct download (EUR-Lex, for one). Tried against the four real services; not yet used by the agents on a whole course.
- **In progress:** captures of real applications that coursekit makes itself (`coursekit capture`): profiles of the web applications, the permission to capture, and covering the personal data of a recording a person provides (OCR, reviewed and approved by a person) are in place, and so is an agent driving a web application in the browser with the personal data replaced on screen (MCP server), with its video recorded by repeating the steps (`coursekit capture replay`), the course itself (its html package served locally or its review link in creator, with no login), and a window of a desktop program (covered on the pixels): on macOS; on Windows and Linux with X11 it is written but not yet tested on real machines.
- **Known gaps of the creator platform** that the pipeline works around: [Known limits of the creator backend](docs/en/08-assembly-and-delivery.md#known-limits-of-the-creator-backend).
- **Not yet:** reading eXeLearning 4 packages (`.elpx`) or HTML exports of a site, publishing the components of the html backend as a package of their own, more languages than Spanish and English.

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

The real captures of applications (`coursekit capture`) need the optional `capture` extra: `uv tool install --force "slxd-coursekit[capture]"` (from a clone: `uv tool install --force --editable "/path/to/coursekit[capture]"`).

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
