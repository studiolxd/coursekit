# Getting started

Install coursekit, create a project with `coursekit init` and launch your first course.

## Requirements

| Need | Why |
|---|---|
| macOS, Windows or Linux | coursekit runs on all three |
| [uv](https://docs.astral.sh/uv/) | installs coursekit and brings the right Python (3.12 or 3.13) |
| git | `init` runs `git init`; approvals are committed in the signer's name; the project hooks use it |
| An AI tool: Claude Code (`claude`), opencode or Codex (`codex`) | the agents that draft, review, produce and assemble. At least one is needed to work on courses |
| The URL of your SLXD Creator MCP server | the instructional design is always done in creator; with the creator backend, assembly and delivery run on it too (see the note on backends below) |
| Node and npm (optional) | download the web links of `brief/links.md`; used by Remotion for videos and, in projects that assemble with the html backend, to prepare the package builder. `coursekit setup --media` can install Node |

Everything else (ffmpeg, voices, API keys) is optional and only matters for media production: see [Media](07-media.md).

## Install

coursekit is not on PyPI yet. Install it from the repository:

```bash
uv tool install git+https://github.com/studiolxd/coursekit
coursekit --version
```

To try it from a clone, with your changes taking effect immediately (an editable install):

```bash
git clone https://github.com/studiolxd/coursekit
uv tool install --editable ./coursekit
```

The package is called `slxd-coursekit`; the command is `coursekit`. To update it:

```bash
uv tool upgrade slxd-coursekit
```

If the shell does not find `coursekit` after installing, run `uv tool update-shell` and open a new terminal.

### Uninstall

`coursekit setup` can install things outside your projects: the media tools, a draft voice, the Remotion dependencies and, if you accept, lines in your shell files. Take them away **first**, while the command still exists, and then remove the package:

```bash
coursekit uninstall --dry-run      # only shows what it would remove
coursekit uninstall                # asks, group by group, before removing
uv tool uninstall slxd-coursekit
```

`coursekit uninstall` removes what `setup` recorded in the coursekit store (see [Where the tools live](07-media.md#where-the-tools-live)): the Node dependencies shared by the projects, the media tools installed with uv, the voice files it downloaded and the lines it added to your shell files. System packages (`ffmpeg`, `node`, `vhs`, `asciinema`) are only listed, with the command to remove them yourself, because other programs may use them. Your projects stay as they are: folders, `.env` and courses. If you want the generated files of a project gone too, delete `.claude/`, `.opencode/`, `.codex/`, `.coursekit/` and `tools/` by hand. Its options are in [Commands](03-commands.md#coursekit-uninstall), and the short answer is in the [FAQ](09-troubleshooting.md#faq).

## Create a project

A project is a folder with a `project.yaml` at its root. It holds all the courses of one client or team and is versioned in git.

```bash
coursekit init acme-courses
```

Run it in a terminal and it starts a short wizard. Press Enter to accept the value in parentheses. The first question is bilingual; once you answer it, the wizard speaks your language.

| # | Question | What the answer is used for | Flag |
|---|---|---|---|
| 1 | `Idioma / Language` (`es`/`en`) | language of the interface (`project.yaml › ui_language`): coursekit's messages, what the agents tell you and every question of the wizard from here on; also saved in `.env` as `COURSEKIT_LANG` | `--ui-language` |
| 2 | Language of the courses | language of the content (`project.yaml › content_language`): content format, section headings, agent writing rules. Default: the interface language you just chose | `--language` |
| 3 | Project name | `project.yaml › name`, shown to the agents. Default: the folder name | `--name` |
| 4 | Client | `project.yaml › client` (for example `ACME`) | `--client` |
| 5 | Tone | writing tone for the agents (free text, may be empty) | `--tone` |
| 6 | Address | how learners are addressed: `tu` or `usted` in Spanish, `you` in English | `--address` |
| 7 | Assembly backend | `SLXD Creator` or `HTML`: where the course is assembled (`project.yaml › assembly.backend`; see the notes below). Default: Creator | `--backend creator\|html` |
| 8 | slxd MCP server URL | asked with either backend. `https://<tenant>.slxd.app/mcp/creator`; leave it empty to set it later. Must start with `http://` or `https://` | `--mcp-url` |
| 9 | Mirror folder | shared folder where courses and the catalog are published: `sharepoint`, `onedrive`, `google-drive`, `nextcloud`, `folder` or `none` | `--mirror` |
| 10 | Local path of the synced folder | only if the mirror is not `none`. Saved in `.env` as `MIRROR_DIR` (it is personal). A warning appears if the path does not exist yet | `--mirror-dir` |
| 11 | Web address of the folder | only for providers other than `folder`; optional, used for the links in the catalog (`mirror.url`) | `--mirror-url` |

Notes:

- A course is assembled in one of two ways. With the **creator backend** the content is loaded into SLXD Creator, which hosts it and exports the SCORM packages. With the **html backend** coursekit itself builds one SCORM package per unit (`coursekit assemble build`), with no platform in between. The choice is the project's default; a course may use the other one (`course.yaml › assembly › backend`), and `coursekit status CODE` shows which one applies. See [Assembly and delivery by backend](02-workflow.md#assembly-and-delivery-by-backend) and [Assembly and delivery](08-assembly-and-delivery.md).
- The MCP URL is asked with both backends: the instructional design (matrix, Excel) is always done in creator. If you skip it, the end of `init` reminds you, whichever backend you chose: without it the design cannot connect to Creator. Set `platform.slxd.mcp_url` in `project.yaml` and run `coursekit agents`.
- The mirror folder is optional. See [Assembly and delivery](08-assembly-and-delivery.md).

### Non-interactive use

With `--yes` (or when there is no terminal, for instance in a script) nothing is asked: flags and defaults are used.

```bash
coursekit init acme-courses --yes --language en --client ACME --mcp-url https://acme.slxd.app/mcp/creator
```

| Flag | Meaning |
|---|---|
| `--yes`, `-y` | do not ask; use the flags and the defaults |
| `--no-git` | do not run `git init` |
| `--update` | refresh the generated files of an existing project (see below) |

Defaults without the wizard: course language `es` (set `--language en` for English), `ui_language` equal to the course language, name equal to the folder name, backend `creator`, mirror `none`, address `tu` for Spanish and `you` for English. An invalid `--address` or a `--mcp-url` that does not start with `http://` or `https://` stops the command.

If the folder already has a `project.yaml`, `init` refuses and points you to `--update`.

## What init creates

```text
acme-courses/
├── project.yaml            project settings, shared and versioned
├── .env                    personal settings, never committed
├── .env.example            template of .env
├── AGENTS.md  CLAUDE.md    instructions for the AI tools working in the project
├── brief/                  reference material for all the courses
│   ├── sources/            documents of any format
│   ├── links.md            web addresses
│   └── notes.md            general indications
├── courses/                one folder per course (empty until you create one)
├── config/                 *.example.yaml: every default, for reference
├── theme/                  design tokens of the project theme (derived from the platform or, with html, from the stylesheet)
├── .agents/                your overrides of skills, commands and agents
├── .githooks/              post-merge, post-checkout
├── .claude/                skills, commands and settings for Claude Code
├── .opencode/              skills, commands and agents for opencode
├── opencode.json           opencode settings
├── .mcp.json               MCP server for Claude Code (only if a URL was given)
├── .codex/config.toml      MCP server for Codex (only if a URL was given)
└── .coursekit/             generated skills and docs for Codex, and generated.json
```

| Path | What it is for |
|---|---|
| `project.yaml` | name, client, languages, tone, address, assembly backend, MCP server, mirror folder and `network.ca_bundles`. Written once; from then on it is yours. See [Configuration](04-configuration.md) |
| `.env` | your identity (`COURSEKIT_USER_NAME`, `COURSEKIT_USER_EMAIL`), `COURSEKIT_LANG`, `MIRROR_DIR`, tool and model of each role, API keys. Ignored by git |
| `.env.example` | the template `.env` is created from. Versioned |
| `config/*.example.yaml` | the complete `rules`, `directives`, `media` and `delivery` defaults, for reference. They are **not read**: to change something create `config/<name>.yaml` with only what you change |
| `brief/` | reference material for every course of the project. Each course also has its own `brief/`. `coursekit brief` converts it for the agents |
| `courses/` | one folder per course, created by `coursekit new` (see [Content](06-content.md)) |
| `theme/` | design tokens of the project theme (`theme/tokens.json` and `tokens.css`). They are not written by hand: `/define-theme` derives them from the theme of the assembly platform (with the html backend, from the stylesheet `theme/maqueta.css`). Media production uses them; `coursekit theme` works on them (see [Theme and design tokens](02-workflow.md#theme-and-design-tokens) and [Media](07-media.md)) |
| `.agents/` | files with the same layout as the package skills, commands and agents (`skills/<name>/SKILL.md`, `commands/<name>.md`, `agents/<name>.md`); one with the same name replaces the package one |
| `.githooks/` | after every pull and checkout, `coursekit agents` refreshes the generated files; after a pull it also publishes to the mirror folder if you have one configured |
| `AGENTS.md`, `CLAUDE.md` | project instructions for the AI tools (`CLAUDE.md` points to `AGENTS.md`) |
| `.claude/`, `.opencode/`, `opencode.json`, `.mcp.json`, `.codex/config.toml` | what each tool reads: skills, commands, the MCP server, and the rule that agents cannot run `coursekit approve` or `git push` |
| `.coursekit/` | generated skills and commands for Codex and any other tool, the docs the agents read, and `generated.json`, which records what coursekit wrote so `init --update` knows what you edited |

Generated folders (`.claude/skills`, `.claude/commands`, `.opencode/skill`, `.opencode/command`, `.opencode/agent`, `.coursekit/agents`, `.coursekit/docs`) are git-ignored: every machine regenerates them. See [Agents](05-agents.md).

### Refreshing generated files

```bash
coursekit init --update      # AGENTS.md, CLAUDE.md, .env.example, .gitignore, config examples, hooks
coursekit agents             # skills, commands, agents and tool settings
```

`init --update` never touches `project.yaml` or the `brief/` notes. A generated file you edited by hand is kept and reported as `kept (edited by hand, not updated)`.

## What setup does

At the end of `init`, coursekit runs `coursekit setup` for you. It is safe to repeat at any time. In order:

1. **`.env`**: created from `.env.example` if missing.
2. **Identity**: your name and email, which sign approvals (`COURSEKIT_USER_NAME`, `COURSEKIT_USER_EMAIL`). The git identity is only suggested. Without a terminal this step only reports that the identity is missing: run `coursekit setup --identity` later.
3. **Network**: if `project.yaml › network › ca_bundles` lists a certificate that exists on your machine (a TLS-inspecting proxy), it offers to set `NODE_EXTRA_CA_CERTS` and `UV_NATIVE_TLS=1` for your user.
4. **Git hooks**: sets `core.hooksPath` to `.githooks` (on Windows also `core.autocrlf input`). If it already points somewhere else, it leaves it alone.
5. **Tool and model of each role**: `design`, `writer`, `reviewer`, `media` and `assembly`, saved in `.env` as `<ROLE>_AGENT` and `<ROLE>_MODEL`. It proposes the defaults and asks "Use these values?"; answer no to choose the tool (`claude`, `opencode`, `codex`) and the model of each role. Defaults: Claude Code with `opus` for design, review and media, and `sonnet` for writing and assembly. Repeat it with `coursekit setup --roles`.
6. **Skills, commands and agent settings**: the same as `coursekit agents`.
7. **html backend builder (only if the project assembles with `html`)**: prepares, once per machine, what the packages are built with: `@studiolxd/scorm` (the SCORM runtime) and esbuild, installed with `npm` in the coursekit store and shared by every project. It needs Node and npm; without npm it only warns, and if the install fails it warns too and `coursekit assemble build` tries again later. Repeat it with `coursekit setup`.
8. **Media tools (optional)**: it asks whether to install them; this downloads quite a lot. See below.
9. **Doctor report**: the output of `coursekit doctor`, so you see what is still missing (for an html project it includes a line for the builder). See [Troubleshooting](09-troubleshooting.md).

### Media tools

If you accept (or run `coursekit setup --media` later):

| System | What happens |
|---|---|
| macOS | `brew install ffmpeg node vhs asciinema` for what is missing (needs Homebrew) |
| Windows | `winget` installs ffmpeg, Node and vhs; asciinema has no Windows build, so terminal demos use VHS |
| Linux | nothing is installed: it prints the `sudo apt install ...` line for your package manager and the VHS address |

Then, on every system: `piper` and `stable-ts` as uv tools (Python 3.12), a draft Piper voice for the course language (stored in `~/.local/share/piper`, or `%LOCALAPPDATA%\piper` on Windows, and set as `PIPER_VOICE`), a Remotion workspace in `tools/remotion` (the sources stay in the project; its dependencies, `node_modules`, about 230 MB, are installed once per machine and each project links to them) and, in a terminal, optional API keys (ElevenLabs, Azure Speech, Google TTS, Magnific; Enter skips each one) saved in `.env`.

Each tool is installed once per machine, not once per project: see [Where the tools live](07-media.md#where-the-tools-live).

## Your first course

At the end, `init` prints the next steps:

```text
Next step: create your first course.

Before you start (optional, but worth it):
  · Reference material: drop the documents in brief/sources/, the URLs in brief/links.md and the general indications in brief/notes.md. `coursekit brief` converts them for the agents to read.
  · Project defaults: look at config/*.example.yaml (rules, directives, media and delivery) and, to change one, create config/<name>.yaml with only what you change. `coursekit config` shows what is in force.

Then:
  1. Go into the project:  cd acme-courses
  2. Open your AI tool in that folder: claude, opencode, codex
  3. And run:  /new-course "Course title" <hours>
  Or do it from here, with the design role agent:  coursekit run new-course "Course title" <hours>
  To see where you are at any time:  coursekit status
```

A tool that is not installed is shown as `(not installed)`. In Codex, ask for the same command by name: it follows `.coursekit/agents/commands/new-course.md`.

If you ran `init` in a terminal and the MCP URL is set, it also offers "Create your first course now with `<tool>`?" (the tool of the design role, if installed). Answer yes, then give the course title and its hours (`1.5` or `1,5`): it runs `coursekit run new-course` for you.

Before creating the course, it helps to drop reference material in `brief/sources/`, URLs in `brief/links.md` and general indications in `brief/notes.md`, then run `coursekit brief`.

### What /new-course does

```text
/new-course "Strong passwords" 2 --code PWD
```

| Argument | Meaning |
|---|---|
| `"Strong passwords"` | course title, in quotes |
| `2` | duration in hours |
| `--code PWD` | course code; by default it is the title in capitals, joined with hyphens |
| `--no-intro`, `--no-summary` | units without the opening introduction or the closing summary section |
| any other text | free indications for the design |

The design agent creates the course (`coursekit new`), converts the brief, builds an instructional design **proposal** in SLXD Creator, publishes it with `coursekit publish` and ends with a summary: units, hours, assumptions to check and how to go on. If the project has no design tokens yet, the summary also tells you to run `/define-theme` before producing media. It signs nothing. From here, follow [Workflow](02-workflow.md). The design is done in creator with either backend; the backend only matters from the assembly on.

You can also create the empty course record yourself, without an agent:

```bash
coursekit new "Strong passwords" 2 --code PWD
coursekit status PWD
```

### Define the theme

```text
/define-theme
```

The graphics, simulations and videos of a course use the colours and fonts of its theme, so they look like the course. With the creator backend the theme lives in the assembly platform; `/define-theme` (design role) lists the themes it has, lets you choose or create one, adapts it with the brand colours and fonts and derives the project's design tokens from it (`theme/tokens.json` and `tokens.css`). Do it once, ideally right after `/new-course` and before producing media: until the tokens come from the platform, `coursekit media set --status produced` refuses infographics, diagrams, animated GIFs, simulations and videos. You validate the theme as you validate the design. With the html backend there is no platform theme: `/define-theme` writes or adapts the stylesheet `theme/maqueta.css` with the brand in its CSS variables and runs `coursekit theme import theme/maqueta.css`. See [Theme and design tokens](02-workflow.md#theme-and-design-tokens).

### Assemble and deliver

Once the units are signed and the media is produced, the assembly depends on the backend of the course (`coursekit status PWD` shows it):

| Backend | Assemble | Deliver |
|---|---|---|
| `creator` | `/assemble PWD` loads the content into SLXD Creator and gives you a preview link and a review link per unit | `/deliver PWD 1.0` exports one SCORM package per unit from creator |
| `html` | `/assemble PWD` builds each unit with `coursekit assemble build PWD --unit N`: a preview folder you open in a browser (`courses/PWD/assembly/html/unit-01/`) | `/deliver PWD 1.0` builds the zip of each unit (`--version 1.0`, into `courses/PWD/delivery/`) and records it; nothing is exported from a platform |

Try an html package in the LMS you will deliver to (or in SCORM Cloud) before handing it over. Details in [Assembly and delivery by backend](02-workflow.md#assembly-and-delivery-by-backend).

Next: [Workflow](02-workflow.md)
