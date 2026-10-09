# Command reference

Every `coursekit` command, grouped by phase of work, with its arguments, options, effects, exit codes and one example, plus the table that maps the agents' slash commands to the CLI.

## Global behavior

### Finding the project

Every command except `coursekit init`, `coursekit help` and `coursekit uninstall` works on a project: a folder with a `project.yaml` at its root. You can run commands from any subfolder (`courses/PWD/content/unit-01/`, for example): coursekit walks up the folders until it finds `project.yaml`, the way git finds `.git`.

| Variable | Meaning |
|---|---|
| `COURSEKIT_PROJECT` | Path of the project root. When set, it overrides the search: the folder must contain `project.yaml`, otherwise the command fails. Useful for scripts and scheduled tasks. |
| `COURSEKIT_HOME` | Folder of the per-machine store (shared Node dependencies and the record of what `coursekit setup` installed). When it is not set, coursekit uses the user's data folder. See [The per-machine store](04-configuration.md#the-per-machine-store). |
| `COURSEKIT_LANG` | Language of coursekit's own messages (`es` or `en`; values such as `es_ES` are accepted). Order of precedence: language forced by the `init` wizard, `COURSEKIT_LANG`, `ui_language` of `project.yaml` (or `content_language` when there is none), the system language (`LC_ALL`, `LC_MESSAGES`, `LANG`), English. |

### The `.env` file

Commands load `.env` (at the project root) into the process environment before running. The real environment always wins: a variable already set in the shell is never overridden, and an empty value in `.env` counts as not set. `.env` is personal and never committed; it holds the signing identity (`COURSEKIT_USER_NAME`, `COURSEKIT_USER_EMAIL`), `COURSEKIT_LANG`, `MIRROR_DIR`, the tool and model of each role (`DESIGN_AGENT`, `DESIGN_MODEL`, `WRITER_AGENT`, `WRITER_MODEL`, `REVIEWER_AGENT`, `REVIEWER_MODEL`, `MEDIA_AGENT`, `MEDIA_MODEL`, `ASSEMBLY_AGENT`, `ASSEMBLY_MODEL`) and the optional keys of the media providers. See [04-configuration.md](04-configuration.md).

### Help and version

| Invocation | Result |
|---|---|
| `coursekit --help`, `coursekit -h` | List of commands. Exit code 0. |
| `coursekit help` | Same as `--help`. Running `coursekit` with no command does the same. |
| `coursekit <command> --help` | Arguments and options of that command. |
| `coursekit --version` | Prints `coursekit <version>`. |

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Done (also for warnings that do not stop the work). |
| `1` | The command failed or a check did not pass: error message on stderr as `coursekit: <message>`, `verify` with errors, `theme check` with a failing pair, `directives check` with differences, `brief` with a failed conversion, a launched AI tool that ended with an error, a command refused because the course is on hold. |
| `2` | Wrong usage: invalid argument (argparse) or a required companion argument is missing (for example `approve content` without `--unit`, `delivery add` without `--file`, `client approve` without `--by`, `client skip` without `--reason`, `reviewed --note` or `--report` without `--by`, `assemble plan`, `diff`, `applied` or `link` without `--unit`). |

`coursekit write`, `coursekit review` and `coursekit run` return the exit code of the AI tool they launched.

### Who runs what

| Marker | Meaning |
|---|---|
| People only | The command signs or changes something that belongs to a person. The generated agent configurations deny it (`coursekit approve`, `coursekit client`, `coursekit hold`, `coursekit resume`, `coursekit handoff`, `coursekit reviewed --by`). |
| Agents | The agent of a role runs it as part of a skill or slash command. People can run it too. |
| Both | Everyday commands for people and agents alike. |

Each command below gives its own `Who:` in its first paragraph. Only the commands of the first row are blocked for the agents by the generated configuration; "Who: people" on any other command (`coursekit init`, `setup`, `uninstall`, `write`, `review`, `run`) says who is meant to run it, not that the agents are denied.

### Statuses at a glance

Units move `pending` -> `writing` -> `verified` -> `reviewed` -> `approved`, and move back when their content changes. A course moves through `design`, `design_approved`, `writing`, `ai_review`, `editorial_review`, `media`, `assembly`, `client_review`, `delivered` (and `on_hold`). Every course status change is appended to `course.yaml › history`.

| Command | Moves |
|---|---|
| `coursekit new` | creates the course in `design`. |
| `coursekit approve design` | course `design` -> `design_approved`. |
| `coursekit handoff` | takes the course through every transition of this table up to `delivered`, signing as Coursekit Handoff; it stops, without changing the status, at `on_hold` and `client_review`, and refuses to start when the client's review is required. |
| `coursekit verify` | unit up to `verified` when it passes; `pending` -> `writing` when it has content but errors; back to `writing` when verified content no longer passes; back to `verified` when content changed after the AI review; an `approved` unit whose files changed after the approval goes back to `reviewed` (to `verified` if parts changed since the AI review, to `writing` if it has errors); with `rules › review › ai: skip`, up to `reviewed` straight away; course status is derived from its units. |
| `coursekit reviewed` | unit -> `reviewed` (AI review, or a person's with `--by`). |
| `coursekit approve content` | unit -> `approved`. When every unit is approved the course becomes `media`. |
| `coursekit assemble applied` | course `media` -> `assembly` when every unit in creator matches its plan (creator backend). |
| `coursekit assemble build` | course `media` -> `assembly` when every unit has its package built (html backend). |
| `coursekit client send` | course `assembly` -> `client_review` (opens a round). |
| `coursekit client changes` | course `client_review` -> `assembly` (closes the round with changes). |
| `coursekit client approve` | closes the round as approved; the course stays in `client_review`. |
| `coursekit client skip` | records a skipped round; the status does not change. |
| `coursekit delivery add` | course `assembly` or `client_review` -> `delivered` when every unit has a package of the same version. |
| `coursekit hold` | course -> `on_hold`, remembering the previous status. |
| `coursekit resume` | course `on_hold` -> the status it had (re-derived from its units when it was in the writing phase). |

While a course is `on_hold`, the commands that change its work are refused with a message that names the reason and the status it will return to; see [`coursekit hold`](#coursekit-hold). The commands that only read still work.

## Commands at a glance

| Phase | Commands |
|---|---|
| Project and machine | `coursekit help`, `coursekit init`, `coursekit config`, `coursekit rules`, `coursekit agents`, `coursekit setup`, `coursekit doctor`, `coursekit uninstall`, `coursekit roles` |
| Courses and design | `coursekit new`, `coursekit handoff`, `coursekit status`, `coursekit sync`, `coursekit outline`, `coursekit brief` |
| Verification and sign-off | `coursekit verify`, `coursekit reviewed`, `coursekit approve` |
| Course state and client review | `coursekit hold`, `coursekit resume`, `coursekit client` |
| Launching agents | `coursekit write`, `coursekit review`, `coursekit run` |
| Media | `coursekit media`, `coursekit voice`, `coursekit tts`, `coursekit subtitles`, `coursekit theme` |
| Assembly and delivery | `coursekit assemble`, `coursekit directives`, `coursekit delivery`, `coursekit publish`, `coursekit catalog` |

## Project and machine

### `coursekit help`

Shows the list of commands (same as `--help`). Takes no arguments. Who: both.

```
coursekit help
```

### `coursekit init`

Creates a project in a folder, or refreshes the files coursekit generated in an existing one. Use it once per project; use `--update` after upgrading coursekit. Who: people.

```
coursekit init [folder] [--update] [--name NAME] [--client CLIENT]
               [--language {es,en}] [--ui-language {es,en}] [--tone TONE]
               [--address ADDRESS] [--backend {creator,html}]
               [--mirror {sharepoint,onedrive,google-drive,nextcloud,folder,none}]
               [--theme-source {tenant_default,branding}] [--mcp-url MCP_URL]
               [--mirror-dir MIRROR_DIR] [--mirror-url MIRROR_URL]
               [--yes] [--no-git]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `folder` | default `.` | Project folder. Created if it does not exist. |
| `--update` | flag | Refresh the generated files of an existing project instead of creating one. A generated file you edited is kept and reported. |
| `--name NAME` | default: folder name | Project name. |
| `--client CLIENT` | free text | Client name (used in course metadata). |
| `--language {es,en}` | default `es`; in the wizard, the interface language | Language of the course content. |
| `--ui-language {es,en}` | default: the course language | Language of the interface: coursekit's messages and what the agents tell you. In the wizard it is the first question. |
| `--tone TONE` | free text | Tone of voice for the content. |
| `--address ADDRESS` | `tu` or `usted` (`es`); `you` (`en`) | How the content addresses the learner. An invalid value without a terminal exits with code 1. |
| `--backend {creator,html}` | default `creator` | Assembly backend, saved in `project.yaml › assembly.backend`: `creator` loads the units into slxd creator; `html` builds each unit as a SCORM package with coursekit (see [`coursekit assemble`](#coursekit-assemble)). A course can use the other one: [04-configuration.md](04-configuration.md#projectyaml). |
| `--theme-source {tenant_default,branding}` | default `tenant_default` | Creator backend only: where the theme comes from, saved in `project.yaml › theme.source`. `tenant_default`: the default theme of the organization in creator. `branding`: a theme made by `/define-theme` from the material in `theme/branding/`. |
| `--mirror PROVIDER` | `sharepoint`, `onedrive`, `google-drive`, `nextcloud`, `folder`, `none`; default `none` | Provider of the shared mirror folder. |
| `--mcp-url MCP_URL` | URL | Address of the slxd MCP server; saved in `project.yaml › platform.slxd.mcp_url`. Asked with either backend, because the instructional design is always done in creator. An invalid URL exits with code 1. |
| `--mirror-dir MIRROR_DIR` | local path | Path of the synced mirror folder; saved in `.env` as `MIRROR_DIR`. |
| `--mirror-url MIRROR_URL` | URL | Web address of the mirror folder; saved in `project.yaml › mirror.url`. |
| `--yes`, `-y` | flag | Do not ask: use the options and defaults. Without a terminal it never asks either. |
| `--no-git` | flag | Do not run `git init`. |

What it does:

- With a terminal and without `--yes` it asks for every value above (the slxd MCP URL with either backend), then offers to create the first course with the design agent, only when the URL was given and the design tool is installed (it asks the title and the hours, then whether to run the whole process in handoff mode with [`coursekit handoff`](#coursekit-handoff), which waits for the material itself; otherwise it asks whether you have reference material, waits while you drop it in `brief/` and launches `/new-course`).
- Creates the folders `courses/`, `brief/sources/`, `config/`, `theme/`, `.agents/`; seeds `project.yaml`, `brief/notes.md` and `brief/links.md`; writes the managed files `AGENTS.md`, `CLAUDE.md`, `.env.example`, `.gitignore`, `config/<name>.example.yaml` (rules, directives, media, delivery) and `.githooks/post-merge`, `.githooks/post-checkout`; runs `git init` unless `--no-git`.
- Then runs the same steps as [`coursekit setup`](#coursekit-setup) (`.env`, `COURSEKIT_LANG` in `.env`, signing identity, git hooks, roles, agents, the html builder with the html backend, diagnosis) and prints the next steps. When the MCP URL is empty, with either backend, the next steps warn that the design cannot connect to creator until `project.yaml › platform.slxd.mcp_url` is set and `coursekit agents` is run.
- `--update` writes nothing outside the managed files (it only recreates the project folders if they are missing) and prints `created`, `updated`, `unchanged` or `kept` for each.
- Exit code 1 when the folder already is a project (without `--update`) or is not one (with `--update`).

```
coursekit init acme-courses --yes --language en --client ACME --name "ACME training"
```

### `coursekit config`

Shows the effective configuration and the layer each value comes from. Use it to check which rules are in force. Who: both.

```
coursekit config [{rules,directives,media,delivery}] [--course COURSE] [--changed] [--json]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `name` | `rules`, `directives`, `media`, `delivery`; default: all four | Which configuration to show. |
| `--course COURSE` | course code or folder | Include the overrides of that course (`course.yaml`). Exit code 1 if the course does not exist. |
| `--changed` | flag | Only values that differ from the package defaults. |
| `--json` | flag | Print the merged values as JSON (one object per configuration, or the bare value when `name` is given). |

Layers, from lowest to highest priority: `package` (defaults shipped with coursekit), `config` (`config/<name>.yaml`), `project` (the `<name>:` section of `project.yaml`), `course` (the `<name>:` section of `course.yaml`). Mappings merge key by key; lists replace the whole list. Each line is `key  value  (layer)`.

The resource types appear by their English id (`image`, `infographic`, `animated_gif`…) in `media` (`types`, `uses_theme`) and in `rules` (`content.placeholder_types`), and the texts of the defaults (`use:`, `how:`, `component_equivalents`) are in English. What the author writes in a content file is the word of the course language for each type: see [06-content.md](06-content.md#media-placeholders).

```
coursekit config delivery --course PWD
```

### `coursekit rules`

Shortcut for the production rules (`coursekit config rules`) of the project or of one course. Who: both.

```
coursekit rules [course] [--changed]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `course` | course code or folder; optional | Include that course's overrides. |
| `--changed` | flag | Only values that differ from the package defaults. |

```
coursekit rules PWD --changed
```

### `coursekit agents`

Generates the skills, slash commands and agent settings for Claude Code, opencode and Codex from the package plus your overrides in `.agents/`. Run it after changing `project.yaml`, `.env` roles or `.agents/`; `coursekit setup` and the git hooks run it for you. Who: both.

```
coursekit agents
```

No arguments. Writes the rendered files to `.claude/`, `.opencode/`, `.coursekit/agents/` and `.coursekit/docs/`, and updates the tool configuration. It merges (never replaces) into `.claude/settings.json` and `opencode.json` the denial to the agents of `coursekit approve`, `coursekit client`, `coursekit hold`, `coursekit resume`, `coursekit handoff`, `coursekit reviewed --by` and `git push`. When `project.yaml › platform.slxd.mcp_url` is set, it also adds the slxd MCP server to `.mcp.json` and `opencode.json` (merged) and writes `.codex/config.toml`, which holds only that server (Codex gets no denial list); that file is rewritten as a whole while it carries the coursekit marker line, and left alone once you remove the line. Only files coursekit generated (they carry a marker) are overwritten or removed. Prints `agents: N written, M unchanged, K removed` and lists the configuration files it updated and the files it kept because you edited them. Details in [05-agents.md](05-agents.md).

```
coursekit agents
```

### `coursekit setup`

Prepares this machine for the project. Repeatable. Who: people.

```
coursekit setup [--identity] [--media] [--roles] [--name NAME] [--email EMAIL] [--yes]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `--identity` | flag | Only set or change the signing identity, then stop. Exit code 1 if no identity could be set. |
| `--media` | flag | Also install the media production tools (see below). |
| `--roles` | flag | Choose again the tool and model of each role. |
| `--name NAME` | text | Signing name, without asking. |
| `--email EMAIL` | text | Signing email, without asking. |
| `--yes`, `-y` | flag | Do not ask. |

Steps, in order: create `.env` from `.env.example` if missing; set the signing identity (`COURSEKIT_USER_NAME`, `COURSEKIT_USER_EMAIL` in `.env`, suggesting the git identity); configure the CA certificate listed in `project.yaml › network` for TLS-inspecting proxies; point git to `.githooks`; write the default tool and model of each role in `.env` (`<ROLE>_AGENT`, `<ROLE>_MODEL`); run `coursekit agents`; with the html backend, prepare the builder of the packages (below); print the diagnosis of [`coursekit doctor`](#coursekit-doctor).

`--media` (or answering yes when asked) additionally installs `ffmpeg`, `node`, `vhs` and `asciinema` (Homebrew on macOS; on Windows winget installs `ffmpeg`, `node` and `vhs`, because asciinema has no Windows version and VHS is used instead; on Linux it prints the commands to run), installs `piper` and `stable-ts` as `uv` tools, downloads a default Piper voice, prepares the Remotion workspace in `tools/remotion/`, and asks (Enter skips) for the optional keys of ElevenLabs, Azure Speech, Google TTS and Magnific.

With the html backend (`project.yaml › assembly.backend: html`), `setup` also prepares the builder of the packages, with or without `--media`: it installs `@studiolxd/scorm` (the SCORM runtime of the player) and `esbuild` (which bundles the player) with `npm install`, once per machine, in the [per-machine store](04-configuration.md#the-per-machine-store) (`workspaces/html-builder-<hash>/`; `<hash>` comes from the `package.json` of the builder, so every project of the same coursekit version reuses the install). Without `npm` it prints a warning and goes on. If the install fails it prints `warning: the html backend builder could not be prepared (npm install); coursekit assemble build will try again`: `coursekit assemble build` retries it when the builder is missing. Nothing is installed inside the project.

The Remotion workspace is shared by all the projects of the machine. `tools/remotion/` keeps the sources (copied from the package the first time); the dependencies are installed once with `npm install` in the [per-machine store](04-configuration.md#the-per-machine-store) (`workspaces/remotion-<hash>/`), and the project gets a `node_modules` link to them (a symbolic link; a junction on Windows). The hash comes from the `package.json` and `package-lock.json` of the workspace: projects with the same dependencies reuse the same install, and a project that edits its `package.json` gets its own. If the link cannot be made, the dependencies are installed in the project itself; if `tools/remotion/` already has a real `node_modules` folder, it is kept as it is. The project `.gitignore` ignores `node_modules/`.

Everything `setup` installs outside the projects (`uv` tools, the voice files it downloads, the lines it adds to the shell files for the proxy certificate, the Windows user variables, the system packages and the shared workspaces) is recorded in `installed.json` in the store, so that [`coursekit uninstall`](#coursekit-uninstall) can take it away.

```
coursekit setup --identity --name "Ana Reyes" --email ana@example.com
```

### `coursekit doctor`

Reports what is installed and configured on this machine for the project. Read-only. Who: both.

```
coursekit doctor
```

No arguments. Prints sections Base (coursekit and Python version, `.env`, signing identity, git hooks, MarkItDown, Node and, in a project with the html backend, the builder of the html packages), Agent tools (slxd MCP server, skills and commands of each tool, tool and model of each role), Network, Mirror folder, Project theme (`ok` when `theme/tokens.json` is derived from the theme of the platform or from the stylesheet of the html backend; `info`, with the hint `/define-theme before producing media`, when there are no tokens or they were written by hand) and Media (ffmpeg, vhs, asciinema, piper, stable-ts, the store, the Remotion dependencies, voice and optional keys). In Media, a line `info` shows the path and size of the per-machine store (only when the store folder exists), and `Remotion dependencies (tools/remotion/node_modules)` is `ok` or `missing` (only when the project has `tools/remotion/`; it is `missing` when the `node_modules` link points at nothing, and the fix is `coursekit setup --media`). In a project whose `assembly.backend` is `html`, the Base section adds `html backend builder (@studiolxd/scorm and esbuild)`: `ok` when the builder is installed in the store (`workspaces/html-builder-<hash>/`), `info` (with the command `coursekit setup`) when it is not yet; `coursekit assemble build` installs it on first use. Each line is `ok`, `missing` (followed by the command that fixes it) or `info`. Always exits with code 0.

```
coursekit doctor
```

### `coursekit uninstall`

Takes away what `coursekit setup` installed outside the projects. It works anywhere, with or without a project. Run it **before** removing the package: afterwards the command no longer exists. Who: people.

```
coursekit uninstall [--dry-run] [--yes]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `--dry-run` | flag | Only show what there is and what would be removed. Nothing is asked and nothing is removed. |
| `--yes`, `-y` | flag | Remove everything without asking. |

It starts by printing the path of the store (see [The per-machine store](04-configuration.md#the-per-machine-store)) and then shows each group that has something in it, asking `Remove this?` before removing each one:

| Group | What it holds |
|---|---|
| Shared Node dependencies | The workspaces in `workspaces/` of the store (the Remotion one and the html builder), with the size of each. |
| Media tools installed with `uv` | `piper-tts` and `stable-ts`. Each one is marked as *installed by coursekit setup* (it is in the record) or as *detected* (it is installed but not recorded, so coursekit may not have installed it: you are asked before it is removed). |
| Downloaded files | The Piper voice files that `setup` downloaded, with their size. |
| Shell-file blocks | The lines that `setup` added to `~/.zshrc` or `~/.bashrc` for the proxy certificate, marked `# coursekit (TLS-inspecting proxy)`, with the number of blocks per file. Only the marker and the line after it are removed. |
| Windows variables | The user variables `setup` defined (Windows only, and only when recorded). |

An answer of no leaves that group as it is and the others are still offered. Without a terminal (a script, a pipe) and without `--yes`, nothing can be answered, so everything is kept.

The system packages that `setup` installed with Homebrew or winget are never removed, because other things may use them: they are only listed, each with the command to remove it by hand (`brew uninstall <packages>`; `winget uninstall --id <id> -e`). The projects are never touched either: the command prints which folders and files of a project can be cleaned by hand (`.claude/`, `.opencode/`, `.codex/`, `.mcp.json`, `opencode.json`, `.coursekit/` and `tools/`). When every group was removed and nothing else is left, it also removes the store folder. It ends with the line `To remove the package itself: uv tool uninstall slxd-coursekit`. When there is nothing installed it says so and still prints the last lines.

Exit code 0 in every case, including when a group was kept or a tool could not be removed (that one is reported with the command to try by hand).

```
coursekit uninstall --dry-run
coursekit uninstall
uv tool uninstall slxd-coursekit
```

### `coursekit roles`

Shows the tool and model each role will use, from `.env`. Who: both.

```
coursekit roles
```

No arguments. One line per role (`design`, `writer`, `reviewer`, `media`, `assembly`) as `<tool> · <model>`, with `(not installed)` when the tool is not in the `PATH`. `default model` means the tool's own default.

```
coursekit roles
```

## Courses and design

### `coursekit new`

Creates a course from its title and duration. Use it to start a course; the design agent then proposes the instructional design. Who: both (`/new-course` runs it).

```
coursekit new [--code CODE] [--language LANGUAGE] [--no-intro] [--no-summary] [--notes NOTES] title hours
```

| Argument | Values / default | Meaning |
|---|---|---|
| `title` | text | Course title (quote it). |
| `hours` | number | Total duration in hours. |
| `--code CODE` | default: the title as an upper-case slug | Course code; becomes the folder name `courses/<CODE>/`. |
| `--language LANGUAGE` | default: `project.yaml › content_language` | Course language. |
| `--no-intro` | flag | Units without the opening introduction section. |
| `--no-summary` | flag | Units without the closing summary section. |
| `--notes NOTES` | text | Extra instructions for the instructional design. |

Creates `courses/<CODE>/` with `course.yaml` (status `design`), the folders `brief/sources/`, `design/`, `content/`, `media/`, `reviews/`, `brief/links.md`, `brief/notes.md` and `media/manifest.yaml`. Units and sections are not created here: they come from the approved design with [`coursekit sync`](#coursekit-sync). Exit code 1 if the course folder already exists.

```
coursekit new "Strong passwords" 2 --code PWD --notes "Focus on office staff"
```

### `coursekit handoff`

Takes a course from its title and hours to its delivery by itself, with nobody reviewing anything on the way: the design, the writing, the AI review, the sign-offs, the media, the assembly and the delivery. Who: people only (the agents cannot run it). Details and limits in [Handoff mode](02-workflow.md#handoff-mode).

```
coursekit handoff [--code CODE] [--no-intro] [--no-summary] [--notes NOTES] [--rounds ROUNDS] [--no-pause] target [hours]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `target` | text | With `hours`: the title of the new course (quote it). Without them: the code of a course to carry on from where it stopped. |
| `hours` | number; optional | Total duration. It makes `handoff` create a new course. |
| `--code CODE` | default: the title as an upper-case slug | Course code. Only when creating; refused with a code to carry on (exit code 2). |
| `--no-intro`, `--no-summary`, `--notes NOTES` | as in [`coursekit new`](#coursekit-new) | Only when creating; with a code to carry on they are refused (exit code 2), like `--code`. |
| `--rounds ROUNDS` | whole number; default `rules › handoff › rounds` (`2`) | Attempts per step before it stops. |
| `--no-pause` | flag | Do not wait for the reference material after creating the course folders. Without a terminal it never waits. Only when creating (refused with a code to carry on, exit code 2). |

When creating, it first makes the course folders (as [`coursekit new`](#coursekit-new) does, with `--notes` as the indications of the design) and, in a terminal, **waits for you to drop the reference material** in `courses/<CODE>/brief/` (`sources/`, `links.md`, `notes.md`; the material of the project in `brief/` is read too) and press Enter. From there it runs, headless and in order, the agent of each role, and decides each step from the status of the course. The signatures of the design and of every unit are given by coursekit itself as **Coursekit Handoff** (never as a person), and each approval records `via: handoff`. It does not do the client's review and it does not start if the project requires it (`client_review.required`): it refuses before creating the course. When a step still fails after its attempts it stops with exit code 1, says why and how to go on (`coursekit handoff <CODE>`). It can take a long time and spend credits of the configured media providers.

```
coursekit handoff "Strong passwords" 2 --code PWD
coursekit handoff PWD
```

### `coursekit status`

Shows the state of every course, or the detail and next step of one. Read-only. Who: both (`/course-status` runs it).

```
coursekit status [code]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `code` | course code or folder; optional | Without it: one line per course (code, status, hours, units, design signature). With it: title, status, the line `Assembly: <backend> backend` (`creator` or `html`: the backend of the course, else the project's), who signed the design (or why the signature no longer holds), one line per unit with its status, a line with the hold (since when, who, why and the status it was in) when the course is `on_hold`, a line with the last round of the client's review (`open`, `asked for changes`, `approved` or `skipped`, and who it was sent to), and the next step. The next step depends on the status: for `assembly` it offers the client's review (`coursekit client <CODE> send`) or delivery (`/deliver`), for `client_review` it asks you to record the client's answer, for `on_hold` it points to `coursekit resume`, and so on. |

```
coursekit status PWD
```

### `coursekit sync`

Writes the units and sections of `course.yaml` from the instructional design saved in `courses/<CODE>/design/matrix.json`. Use it with `--check` to preview a design before signing it, and without it after the design changed. Who: both.

```
coursekit sync [--check] code
```

| Argument | Values / default | Meaning |
|---|---|---|
| `code` | course code or folder | Course to sync. |
| `--check` | flag | Only report what would be synced; write nothing. |

Without `--check` it writes `course.yaml › units` (title, hours, objectives, sections with minimum words, activities), keeping the fields coursekit already set on each unit (`status`, `content_id`, `written_with`, `reviewed_with`, `reviewed_parts`, `review`, `links`), and creates `content/unit-NN/content.md` and `assessment.md` skeletons for units that have none. Existing content is never overwritten: `content.md` is regenerated only while it is still the untouched skeleton of a previous design, and `assessment.md` is rewritten only when it is missing or still the blank template. Prints the warnings (section headings that differ from the design, hours that do not add up, a missing hours value) and a summary `N units, M sections, W minimum words`, then each skeleton written. Warnings do not change the exit code. Without `design/matrix.json` (or with a file that is not a `design_matrix_get` result) it stops with a message and exit code 1.

```
coursekit sync PWD --check
```

### `coursekit outline`

Prints a compact map of a course (units, objectives, sections with minimum words and how much is written) or the text of one section. Read-only. Who: both (agents use it to avoid loading every unit).

```
coursekit outline [--section SECTION] code
```

| Argument | Values / default | Meaning |
|---|---|---|
| `code` | course code or folder | Course to map. |
| `--section SECTION` | `U.S`, for example `2.3` | Print only the text of that section (unit `U`, section `S`). Exit code 2 if the format is not `U.S`. |

```
coursekit outline PWD --section 1.2
```

### `coursekit brief`

Converts the reference material of a course (or of the project) to Markdown for the agents. Use it after dropping files in `brief/sources/` or URLs in `brief/links.md`. Who: both.

```
coursekit brief [--refresh] [code]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `code` | course code or folder; default: the project `brief/` | Brief to convert. With a code, the project brief is converted too and the course index links to it. |
| `--refresh` | flag | Download the URLs of `links.md` again (by default each URL is downloaded once). |

Converts files of `brief/sources/` to `brief/text/files/` (MarkItDown) and the URLs of `links.md` to `brief/text/web/` (needs Node), only when new or changed, and writes `brief/index.md`, which the agents read, in the content language of the project (or of the course). Images are listed for the agents to open; audio and video need a transcript. With a code it works in `courses/<CODE>/brief/` and creates `sources/`, `links.md` and `notes.md` if missing. Prints a `brief:` summary line (documents, webs, images/audio/video and the index path) and one warning per problem. Exit code 1 if a file could not be converted or if the URLs cannot be downloaded because Node is missing; a download that fails while it runs is reported as a warning and the exit code stays 0.

```
coursekit brief PWD --refresh
```

## Verification and sign-off

### `coursekit verify`

Checks a course's content against the production rules. Use it after each section you write, and before any review. Who: both.

```
coursekit verify [--unit UNIT] [--no-update] code
```

| Argument | Values / default | Meaning |
|---|---|---|
| `code` | course code or folder | Course to check. |
| `--unit UNIT` | unit number; default: every unit | Check only that unit. |
| `--no-update` | flag | Do not update the unit and course status. |

Per unit it checks (on `content.md` and `assessment.md`): the design is approved and unchanged since it was signed; sections present and in design order; minimum words per section; objective tag in every content section and every objective covered; distinct interactive directives per content section; media placeholders per hour (count, distinct types, required fields; the type is written with the word of the course language, and the word of the other language is an error that lists the valid ones); directives well formed (known, closed, not nested); questions carry an objective; no emojis outside the allowed symbols; the content converts for the assembly backend (including that the keys of the directives, such as `question:` or `answer:`, are those of the course language: a key of the other language is reported as `assembly: …` with the language it belongs to and the valid keys; with the html backend it also checks that every component of the unit can be rendered, and a directive it cannot yet, such as the games, is reported as `<lesson>: <BRICK>: this component is not available in the html backend yet (the games come in a later delivery)`). The numbers come from `coursekit rules`. Output: `[OK]` or `[FAIL]` header per unit, a statistics line, then `ERROR` and `WARNING` lines. Unless `--no-update`, it moves the unit status (see [Statuses at a glance](#statuses-at-a-glance)) and prints the change. Exit code 1 when the design is not approved or changed after approval, when the unit does not exist, or when any unit has errors; warnings do not fail.

```
coursekit verify PWD --unit 1
```

### `coursekit reviewed`

Marks a unit as reviewed: by the AI (the review agent runs it at the end of its review) or, with `--by`, by a person who reviewed it without the AI. Who: agents for the AI review; people for `--by`.

```
coursekit reviewed code unit [--by NAME] [--note NOTE] [--report FILE]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `code` | course code or folder | Course. |
| `unit` | unit number | Unit reviewed. |
| `--by` | name | The review is a person's: records `review: {kind: human, by, at}` in the unit and the history, and the AI report is not needed. Agents are denied the option. |
| `--note` | text | Note of the person's review (needs `--by`; exit code 2 without it). |
| `--report` | file | Report of the person's review (needs `--by`; exit code 2 without it); it must be inside the course folder, usually in `reviews/`, and is committed with the signature. |

Without `--by` it requires the report `courses/<CODE>/reviews/unit-NN-ai-review.md` (and records `review: {kind: ai}`); with `--by` it does not. In both cases the unit must still verify without errors. Moves the unit to `reviewed` (the course derives its status), and stores the fingerprint of each section and activity in `course.yaml › units[N].reviewed_parts`, so later reviews can be partial. Prints `unit N: reviewed`, adding the course change when there is one. Exit code 1 if the report is missing, the unit does not exist or it does not verify.

```
coursekit reviewed PWD 1
coursekit reviewed PWD 1 --by "Ana Pérez" --note "Reviewed with the client's trainer"
```

### `coursekit approve`

Signs off the instructional design or one unit, in the name of the person who runs it. People only: the generated agent configurations deny it, and the slash commands only prepare the sign-off. Who: people.

```
coursekit approve [--unit UNIT] [--yes] [--no-commit] [--force] {design,content} code
```

| Argument | Values / default | Meaning |
|---|---|---|
| `gate` | `design` or `content` | What to sign: the instructional design, or the content of one unit. |
| `code` | course code or folder | Course. |
| `--unit UNIT` | unit number | Unit to sign (required with `content`; without it the command exits with code 2). |
| `--yes` | flag | Confirm without a prompt. Needed when there is no terminal; from an agent chat, type it with the `!` prefix so it runs as you. |
| `--no-commit` | flag | Record the approval without making the git commit. |
| `--force` | flag | `content` only: sign the unit even if its content changed after its AI review. |

Without `--yes` it needs an interactive terminal (otherwise exit code 1) and asks `[y/N]` after showing a summary. The signer is the identity of `.env` (`COURSEKIT_USER_NAME`, `COURSEKIT_USER_EMAIL`), never the git identity; without it the command exits with code 1 (`coursekit setup --identity`).

`design`: needs `design/matrix.json`; refuses when `design/validation.json` holds findings of severity `error`. Runs [`coursekit sync`](#coursekit-sync), appends the approval to `course.yaml › approvals` (signer, timestamp, matrix id, SHA-256 of `matrix.json`, Excel name), sets the course to `design_approved`, and commits the course folder as `Design approval <CODE>`. Any later change of `matrix.json` invalidates the signature.

`content`: needs the design approved and unchanged, the unit passing `verify` without errors, unit status `reviewed` (or `approved`) and the AI review report, unless a person recorded their own review (`coursekit reviewed --by`) or the project skips the AI review (`rules › review › ai: skip`, where a `verified` unit is enough). It is refused when the content changed after the AI review: the baseline is the fingerprint of each section and activity stored by `coursekit reviewed`, and the message names the parts that changed (review them again with `coursekit review`, or sign anyway with `--force`). Records the SHA-256 of `content.md` and `assessment.md`, moves the unit to `approved`, and commits `course.yaml`, the unit folder and the review report as `Content approval <CODE> U<N>`.

If git cannot commit, the approval stays recorded and the message says `(recorded, not committed)`; the exit code is still 0.

```
coursekit approve content PWD --unit 1
```

## Course state and client review

### `coursekit hold`

Puts a course on hold, for example when the client pauses the project. The course keeps all its work and remembers the status it was in. People only: the generated agent configurations deny it. Who: people.

```
coursekit hold --reason REASON code
```

| Argument | Values / default | Meaning |
|---|---|---|
| `code` | course code or folder | Course to pause. |
| `--reason REASON` | text (required) | Why it is paused. It stays in the history. Exit code 2 without it. |

Records in `course.yaml › hold` the previous status (`previous`), the reason (`reason`), who paused it (`by`, the signing identity) and when (`at`), sets the course to `on_hold` and appends the change to `course.yaml › history`. Prints `<CODE> on hold (it was in '<status>')`. Exit code 1 if the course already is on hold.

While the course is on hold these commands are refused (exit code 1, with a message that gives the date, the reason, the previous status and the way out): `coursekit write`, `coursekit review`, `coursekit approve`, `coursekit reviewed`, every action of `coursekit assemble`, `coursekit sync` (without `--check`), `coursekit media set`, every action of `coursekit client`, and `coursekit delivery check`, `name` and `add`. `coursekit handoff` stops with a message that says how to resume, and `coursekit run` refuses the commands that work on the course (see [`coursekit run`](#coursekit-run)). The commands that only read still work: `coursekit status`, `coursekit verify`, `coursekit config`, `coursekit brief`, `coursekit publish`, `coursekit catalog`, `coursekit outline` and `coursekit sync --check`.

```
coursekit hold PWD --reason "Client paused the project until the next quarter"
```

### `coursekit resume`

Takes a course off hold and returns it to the status it had. People only. Who: people.

```
coursekit resume code
```

| Argument | Values / default | Meaning |
|---|---|---|
| `code` | course code or folder | Course to resume. |

Restores the status stored in `course.yaml › hold`; when that status belonged to the writing phase (`design_approved`, `writing`, `ai_review`, `editorial_review`, `media`) it is derived again from the units, in case something changed meanwhile. Removes the `hold` block and appends the change to the history. Prints `<CODE> resumed: '<previous>' -> '<new>'`: the status before the hold and the one the course has now (they differ only when the units changed). Exit code 1 if the course is not on hold.

```
coursekit resume PWD
```

### `coursekit client`

Records the optional review of the course by the client, round by round. The client comments on the assembled course through a review link; this command only registers what happened and what the client decided. People only: the generated agent configurations deny it, and `/client-feedback` never runs it. Who: people.

```
coursekit client [--to TO] [--where WHERE] [--by BY] [--note NOTE] [--reason REASON] code {send,changes,approve,skip}
```

| Argument | Values / default | Meaning |
|---|---|---|
| `code` | course code or folder | Course. |
| `action` | `send`, `changes`, `approve`, `skip` | See below. |
| `--to TO` | text (`send`) | Who the review is sent to. Stored in the round. |
| `--where WHERE` | URL (`send`) | One link to send, instead of the review link of each unit. |
| `--by BY` | text (`approve`) | Name of the person who approves on behalf of the client. Required by `approve` (exit code 2 without it). |
| `--note NOTE` | text (`changes`, `approve`) | Optional note: what the client asked for, or their comments. |
| `--reason REASON` | text (`skip`) | Why the course is delivered without the client's approval. Required by `skip` (exit code 2 without it). |

Rounds are stored in `course.yaml › client_review`; each one has its number, who sent it and when, `to`, the links, and the outcome (`changes`, `approved` or `skipped`) with the date it was closed. Every action is also appended to the history. Actions:

- `send`: opens round N. The course must be in `assembly`. It records `--to` and the links of each unit (`course.yaml › units[N].links.review`, stored with [`coursekit assemble link`](#coursekit-assemble) `--review`), or the single `--where` link. The course becomes `client_review`. Refused (exit code 1) when the course is in another status, when a round is still open, or when there is no link at all.
- `changes`: the client asked for changes. Closes the open round with the outcome `changes` and the optional `--note`, and the course goes back to `assembly` so the changes can be applied (`/client-feedback`) and a new round opened. Refused if there is no open round.
- `approve`: the client approved. Closes the open round with the outcome `approved`, the name in `--by` and the optional `--note`. The course stays in `client_review`; delivering is now allowed. Refused if there is no open round.
- `skip`: records a round with the outcome `skipped` and the reason, without sending anything. The status does not change. It is how a course is delivered without the client's review when the project requires it. The course must be in `assembly` or `client_review` and have no open round.

The review is optional unless `delivery.yaml › client_review.required` is `true`; see [`coursekit delivery`](#coursekit-delivery).

```
coursekit client PWD send --to "ana@acme.example"
coursekit client PWD approve --by "Ana Reyes" --note "Approved with no changes"
```

## Launching agents

### `coursekit write`

Writes units with the writer agent. Without a unit number it processes every unit still to do (`pending` or `writing`) in order and stops at the first that does not end verified. Who: people (or a scheduled task with `--headless`).

```
coursekit write [--headless] [--agent {claude,opencode,codex}] [--model MODEL] code [n]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `code` | course code or folder | Course. |
| `n` | unit number; default: every unit still to do | Unit to write. |
| `--headless` | flag | Run the tool without its interface; the session is logged in `.cache/logs/`. |
| `--agent {claude,opencode,codex}` | default: `WRITER_AGENT` | Tool for this launch. Alone, it uses that tool's default model. |
| `--model MODEL` | default: `WRITER_MODEL` | Model for this launch. |

It records the tool and model in `course.yaml › units[N].written_with` and launches `/write-unit <CODE> <N>` with the writer agent. Prints `write <CODE> · unit N with <tool> · <model>` and, with `--headless`, afterwards the final summary, the unit status and the session log path (an interactive session prints nothing more). Interactive: exit code of the tool. Headless: 0 when the unit ends `verified`, `reviewed` or `approved`, otherwise the tool's code or 1. With several units it prints `stopped at unit N` on failure. When nothing is pending it prints `nothing to write in <CODE>` and exits with 0.

```
coursekit write PWD 1 --agent opencode --model anthropic/claude-sonnet-5-5
```

### `coursekit review`

Runs the AI review of units with the reviewer agent. Without a unit number it processes every `verified` unit. Who: people (or a scheduled task with `--headless`).

```
coursekit review [--headless] [--full] [--parts PARTS] [--agent {claude,opencode,codex}] [--model MODEL] code [n]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `code` | course code or folder | Course. |
| `n` | unit number; default: every unit still to do | Unit to review. |
| `--headless` | flag | Run the tool without its interface; the session is logged in `.cache/logs/`. |
| `--full` | flag | Review the whole unit, even if it was reviewed before. |
| `--parts PARTS` | for example `"section 4, activity 1.2"` | Review only these parts (comma-separated). |
| `--agent {claude,opencode,codex}` | default: `REVIEWER_AGENT` | Tool for this launch. |
| `--model MODEL` | default: `REVIEWER_MODEL` | Model for this launch. |

A unit already reviewed gets a partial review of only the parts that changed since (from the stored fingerprints), unless `--full`; `--parts` names them by hand. The reviewer is recorded in `reviewed_with`; a warning is printed when the unit has no `written_with` or the reviewer is the same tool and model as the writer, and the review goes on. The agent writes `reviews/unit-NN-ai-review.md` and runs `coursekit reviewed`. Exit codes as in `write` (a unit is done when it ends `reviewed` or `approved`).

```
coursekit review PWD 1 --full
```

### `coursekit run`

Launches any slash command (`new-course`, `design-change`, `approve-design`, `define-theme`, `produce-media`, `assemble`, `client-feedback`, `deliver`, `sync-directives`, `course-status`, and so on) with the agent of its role. Use it from a terminal or a script instead of opening the AI tool. Who: people.

```
coursekit run [--role {design,writer,reviewer,media,assembly}] [--headless] [--agent {claude,opencode,codex}] [--model MODEL] name ...
```

| Argument | Values / default | Meaning |
|---|---|---|
| `name` | command name without the slash | Command to launch. |
| `arguments` | the rest of the line | Passed to the command as they are. |
| `--role {design,writer,reviewer,media,assembly}` | default: the role of the command (`design` for an unknown name) | Role whose agent runs it. |
| `--headless` | flag | Run without the tool's interface; the session goes to `.cache/logs/<name>-<role>-<timestamp>.log`. |
| `--agent {claude,opencode,codex}` | default: `<ROLE>_AGENT` | Tool for this launch. |
| `--model MODEL` | default: `<ROLE>_MODEL` | Model for this launch. |

`--headless`, `--agent`, `--model` and `--role` may also come after the command name. Prints `/<name> <arguments> with the <role> agent (<tool> · <model>)` and returns the tool's exit code. Codex, and opencode with `--headless`, cannot take a project slash command, so they are told to follow `.coursekit/agents/commands/<name>.md`. When the command works on a course (its first argument is a course code) and the course is on hold, it is refused with exit code 1 before the tool starts; `new-course` and `course-status` are not affected.

```
coursekit run new-course "Strong passwords" 2 --code PWD
```

## Media

### `coursekit media`

Manages the media manifest of a course (`media/manifest.yaml`) and tells how to produce each asset. Who: agents (the media agent) and people.

```
coursekit media [--status STATUS] [--recipe RECIPE] [--asset-path ASSET_PATH] [--file FILE]
                [--alt ALT] [--transcript TRANSCRIPT] [--subtitles-path SUBTITLES_PATH]
                [--made-with MADE_WITH] [--download DOWNLOAD] [--download-title DOWNLOAD_TITLE]
                [--download-asset-path DOWNLOAD_ASSET_PATH] [--force]
                {extract,plan,providers,set} [code] [id]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `action` | `extract`, `plan`, `providers`, `set` | See below. |
| `code` | course code or folder | Required by every action except `providers` (exit code 2 without it). |
| `id` | asset id such as `U1-S2-M1` | Required by `set` (exit code 2 without it). |
| `--status STATUS` | `pending`, `scripted`, `produced`, `uploaded` | New status of the asset (checked against `coursekit config media`). |
| `--recipe RECIPE` | option id, for example `agent-svg` | Production option used. |
| `--file FILE` | path inside the course `media/` | Local file produced. With the html backend it is what the package carries: a file, or, for simulations and demos, the folder of the package or its `index.html`. |
| `--asset-path ASSET_PATH` | text | Path of the asset once uploaded to the platform. |
| `--alt ALT` | text | Alternative text. |
| `--transcript TRANSCRIPT` | text or path | Transcript of audio or video. |
| `--subtitles-path SUBTITLES_PATH` | text | Captions file. With the html backend, a local `.vtt` (for example `media/files/u1-s2-m1.vtt`). |
| `--made-with MADE_WITH` | text | Tool or model that produced it. |
| `--download DOWNLOAD` | file name | Add or update an extra downloadable file of the asset. |
| `--download-title DOWNLOAD_TITLE` | text | Title of that download (needs `--download`). |
| `--download-asset-path DOWNLOAD_ASSET_PATH` | text | Uploaded path of that download (needs `--download`). |
| `--force` | flag | `set` only: mark an asset that uses the theme tokens as `produced` or `uploaded` even though the tokens are missing or were written by hand (see below). |

Actions:

- `extract`: syncs `media/manifest.yaml` with the placeholders found in the content. Asset ids are `U<unit>-S<section>-M<k>`; the `type` of each asset is the English id of the resource type (`image`, `infographic`…) whatever word the content uses ([07-media.md](07-media.md#placeholders-and-types)). An asset whose placeholder changed goes back to `pending`; one whose placeholder disappeared becomes `orphaned`. Prints `manifest: N assets (pending 3, ...)`.
- `plan`: for each `pending` or `scripted` asset, the production options available here in order of preference (the line starts with the id of the type, `U1-S2-M1 [infographic] Title`), plus the voice and subtitle options for audio and video, and warnings for missing downloads and for the theme (see below). Prints `nothing to produce` when there is none.
- `providers`: every optional provider and whether it is `available`, `missing` or `agent MCP` (only the agent can tell). Takes no course.
- `set`: updates the asset `id` with the options given; prints `<id>: <status>`.

The types that use the theme tokens are listed in `media.yaml › uses_theme` (by default `infographic`, `diagram`, `animated_gif`, `simulation` and `video`). For them:

- `plan` warns, once per course, when the course has assets of those types and its tokens (its own, else the project's) are missing or were written by hand instead of derived with [`coursekit theme import`](#coursekit-theme) (from the platform theme, or from the stylesheet of the html backend). It also warns for each `produced` or `uploaded` asset that was made with other tokens than the current ones.
- `set --status produced` or `--status uploaded` is refused (exit code 1) unless the tokens are derived (from the platform theme or from the stylesheet of the html backend), or `--force` is given. When it goes through, the asset stores a fingerprint of the tokens (`theme` in `media/manifest.yaml`), which is how `plan` notices later that the theme changed and the asset must be produced again.

With the html backend there is no upload: a `produced` asset with its `--file` is final, and `coursekit assemble build` copies the file into the package. See [Media for the html backend](07-media.md#media-for-the-html-backend).

```
coursekit media set PWD U1-S2-M1 --status produced --recipe agent-svg --file media/files/u1-s2-m1.svg --alt "Password strength meter"
```

### `coursekit voice`

Shows the voice-over providers available on this machine, or fixes the single voice of a course. A course never mixes voices. Who: both.

```
coursekit voice [--voice VOICE] [--speaker SPEAKER] {list,set} [code] [{elevenlabs,azure,google,piper}]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `action` | `list`, `set` | Show or fix. |
| `code` | course code or folder | Required by `set`; optional for `list` (adds the course's voice). |
| `provider` | `elevenlabs`, `azure`, `google`, `piper` | Required by `set`. |
| `--voice VOICE` | provider voice id; default: the provider's voice variable in `.env`, then the language default | Voice to use. |
| `--speaker SPEAKER` | integer | Speaker of multi-speaker Piper voices. |

`list` prints one line per provider (`available` or `missing`, with a note) and, with a course, which voice it uses or what to do next. `set` writes `course.yaml › media.voice` (`provider`, `voice`, `speaker`) and warns, without failing, when the provider is not configured on this machine. Exit code 2 when `set` lacks the course or the provider.

```
coursekit voice set PWD azure --voice es-ES-ElviraNeural
```

### `coursekit tts`

Produces the voice-over of a script. Who: agents (the media agent) and people.

```
coursekit tts [--course COURSE] [--engine {elevenlabs,azure,google,piper}] --in INPUT --out OUT [--voice VOICE] [--speaker SPEAKER]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `--course COURSE` | course code or folder | Use the voice of that course (`course.yaml › media.voice`) and its language. |
| `--engine {elevenlabs,azure,google,piper}` | default: the course voice, or the only configured provider | Provider for this run. |
| `--in INPUT` | path (required) | Text file with the script. |
| `--out OUT` | path (required) | Audio file to write (`.mp3`). |
| `--voice VOICE` | text | Voice, overriding the course's. |
| `--speaker SPEAKER` | integer | Speaker of multi-speaker Piper voices. |

Fails with a message (exit code 1) when the provider is not configured, when several providers are available and none is chosen (use `coursekit voice set`), or when none is, when the `--in` file does not exist, when a program it needs (`ffmpeg`, `piper`) is not installed or fails (`<program> is not installed or not on the PATH (coursekit setup --media)`, `<program> failed (exit code N)`), and when the voice API answers with an error or cannot be reached (`<host> answered <status> <reason>: check the key, the region and the voice configured`, `could not reach <host>: <reason>`). ElevenLabs also writes a `.vtt` file (captions) next to the audio, with the name of `--out` and the extension `.vtt` (`u1.mp3` gives `u1.vtt`), from the character timestamps the API returns; for the other providers use [`coursekit subtitles`](#coursekit-subtitles).

```
coursekit tts --course PWD --in media/scripts/u1-s2-m1.txt --out media/files/u1-s2-m1.mp3
```

### `coursekit subtitles`

Aligns a known script with its audio and writes WebVTT captions (uses `stable-ts`, installed by `coursekit setup --media`). Who: agents (the media agent) and people.

```
coursekit subtitles --audio AUDIO --text TEXT --out OUT [--course COURSE] [--language LANGUAGE] [--model MODEL]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `--audio AUDIO` | path (required) | Audio file. |
| `--text TEXT` | path (required) | Script text file. |
| `--out OUT` | path (required) | `.vtt` file to write. |
| `--course COURSE` | course code or folder | Take the language from the course (overrides `--language`). |
| `--language LANGUAGE` | default `es` | Language of the audio. |
| `--model MODEL` | default `base` | Whisper model size used for the alignment. |

Prints `wrote <OUT>`. Exit code 1, with a message, if `stable-ts` is not installed or fails (`<program> failed (exit code N)`), or if the audio or the text file does not exist.

```
coursekit subtitles --audio media/files/u1-s2-m1.mp3 --text media/scripts/u1-s2-m1.txt --out media/files/u1-s2-m1.vtt --course PWD
```

### `coursekit theme`

Derives the design tokens of the theme (`tokens.json`, `tokens.css`) from the theme of the assembly platform (creator backend) or from the stylesheet of the project (html backend), says where they come from, and checks their contrast. The media (infographics, diagrams, simulations, videos) use these tokens so they look like the course. The tokens are never written by hand. Who: both (`/define-theme` runs it).

```
coursekit theme [--course COURSE] {tokens,check,import,show} [file]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `action` | `tokens`, `check`, `import`, `show` | See below. |
| `file` | path; required by `import` with the creator backend | Creator backend: the file with the saved result of the platform tool `get_theme` (the agent saves it to `.cache/theme/get_theme.json`). Html backend: the `.css` stylesheet of the project (for example `theme/maqueta.css`). The extension decides: a file ending in `.css` is read as a stylesheet, any other as a `get_theme` result. With the html backend the file may be left out: the tokens are then those of the base layout alone (the origin says `base layout`). |
| `--course COURSE` | course code or folder | Work on the own theme of that course (`courses/<CODE>/theme/`) instead of the project's (`theme/`). |

Where the tokens are: a course uses its own tokens when `courses/<CODE>/theme/tokens.json` exists, otherwise the project's `theme/tokens.json`. `tokens`, `check` and `show` apply that rule when given `--course`; `import --course` creates the course's own tokens. `coursekit theme show PWD` is accepted as a shortcut of `coursekit theme show --course PWD`.

Actions:

- `import FILE` with a `get_theme` result (creator backend): converts it into `tokens.json` and `tokens.css`, in the folder of the project or, with `--course`, of the course; the course also gets `slxd.theme_id` in its `course.yaml`. The colours `background`, `text`, `headings`, `accent`, `on-accent`, `link`, `correct`, `on-correct`, `wrong` and `on-wrong` come from the semantic colour roles of the theme, with palette references resolved. The tokens `text-soft`, `surface`, `highlight`, `line` and `accent-strong` do not exist in the platform and are derived from those colours (the soft text is kept at least 4.5:1 on the background). The fonts (`font.family`, `font.headings`, `font.ui`) come from the font assignments, and `size-base` and `line-height` from the base size and line height. `radius`, `space` and `shadow` are package defaults, because the platform has none. `tokens.json` records where everything comes from in `origin`. It prints the file written, the notes as `WARNING` lines (a font included in the platform that is used by its name, a colour role that could not be resolved, a dark mode) and the contrast of each pair. A pair below its minimum does not fail the import: the output tells you to fix the colour in the platform with `update_theme` and import again, never to edit the tokens by hand.
- `import FILE` with a `.css` file (html backend): the tokens are derived from the CSS variables of the base layout of the package with that file over it, so the stylesheet only needs to declare what it changes. The variables read are `--color-<name>` (each one becomes `color.<name>`: `background`, `text`, `text-soft`, `headings`, `accent`, `accent-strong`, `on-accent`, `link`, `surface`, `highlight`, `line`, `correct`, `wrong` and any other you add), `--font-family`, `--font-family-headings` and `--font-family-ui` (`font.family`, `font.headings`, `font.ui`), `--font-size-base`, `--line-height`, `--radius`, `--space-<name>` and `--shadow-<name>`. A `var(--x)` reference is resolved with the values of the base layout and of the file (`--color-headings: var(--color-text)` takes the text colour); the last declaration of a variable wins wherever it is in the file, and comments are ignored. `tokens.json` records in `origin`: `source: css`, `file` (the name of the stylesheet), `sha256` (the first 12 characters of the hash of the file), `imported_at` and `notes`; there is no theme id, so the course does not get `slxd.theme_id`. It prints `tokens written to <path> from the CSS variables of <file> (over the base layout of the package) and tokens.css next to it`, one `WARNING` per colour that is not a plain value (a gradient or a `color-mix()`, for example: it is kept as written and left out of the contrast check) and the contrast of each pair. A pair below its minimum does not fail the import either; the hint it prints says to fix the colour in the stylesheet and import it again.
- `tokens`: rewrites `tokens.css` from the `tokens.json` that applies: `:root` custom properties and the base classes for simulations. Do not edit the CSS by hand.
- `check`: prints the WCAG contrast of the colour pairs the media and components use, one line per pair, `ok` or `FAIL`.
- `show`: prints which tokens apply (`project tokens: theme/tokens.json` or `tokens of the course: courses/<CODE>/theme/tokens.json`) and their state: missing (it says to define the theme with `/define-theme`), written by hand (not derived; it says to import them), or derived. A theme of the platform shows `origin: platform theme 'ACME training' (<theme id>, version 3), imported on <date>`; a stylesheet shows `origin: CSS variables of maqueta.css (fingerprint <12 characters>), imported on <date>`. The agents read the theme id of the first form to link the theme to the contents with `set_content_theme`. Tokens derived from a stylesheet count as derived for [the media guard](07-media.md#the-media-guard) and for `coursekit doctor`.

Exit codes: `0` on success (`show` too, whatever the state). `2` when `import` has no `FILE`. `1`, with a message, when the file does not exist or (not being a `.css`) is not a `get_theme` result, when the course does not exist, when the tokens are missing or not a valid JSON (`tokens`, `check`), and when `check` finds a pair below its minimum (4.5 for text, 3.0 for the accent on the background). See [Theme tokens](07-media.md#theme-tokens) for the format of the tokens, what is derived and the limits.

```
coursekit theme import .cache/theme/get_theme.json
coursekit theme import .cache/theme/get_theme.json --course PWD
coursekit theme import theme/maqueta.css
coursekit theme show --course PWD
coursekit theme check
```

## Assembly and delivery

### `coursekit assemble`

Assembles a unit with the backend of its course (`project.yaml › assembly.backend`, or `course.yaml › assembly.backend` for one course; `coursekit status CODE` prints which one). With the creator backend it plans, compares and records the assembly in slxd creator: the assembly agent applies the plan with the MCP and records the resulting ids here, so later edits become minimal operations. With the html backend it builds the unit as a SCORM package, with no platform in between. Refused while the course is on hold. Who: agents (the assembly agent) and people.

```
coursekit assemble [--unit UNIT] [--version VERSION] [--lesson LESSON] [--lesson-id LESSON_ID]
                   [--brick-ids BRICK_IDS] [--content] [--content-id CONTENT_ID]
                   [--preview PREVIEW] [--review REVIEW]
                   {plan,diff,applied,link,build} code
```

| Argument | Values / default | Meaning |
|---|---|---|
| `action` | `plan`, `diff`, `applied`, `link`, `build` | `plan`, `diff`, `applied` and `link` are the creator backend's; `build` is the html backend's. See below. |
| `code` | course code or folder | Course. |
| `--unit UNIT` | unit number | Unit to assemble. Required by `plan`, `diff`, `applied` and `link` (exit code 2 without it); optional for `build`, which without it builds every unit. Exit code 1 if the unit does not exist. |
| `--version VERSION` | text, for example `1.0` (`build`) | Version of the package. With it, `build` also writes the zip in `courses/<CODE>/delivery/`; without it, only the preview. |
| `--lesson LESSON` | lesson key from the plan (`applied`) | Lesson to record. |
| `--lesson-id LESSON_ID` | creator lesson id (`applied`) | Id of that lesson in creator. |
| `--brick-ids BRICK_IDS` | comma-separated ids; default empty (`applied`) | Brick ids in plan order; their number must equal the bricks of the lesson. |
| `--content` | flag (`applied`) | Record the content title as applied (after renaming the content in creator) instead of a lesson. |
| `--content-id CONTENT_ID` | creator content id (`link`) | Id of the unit's content in creator. |
| `--preview PREVIEW` | URL (`link`) | Live preview link of the unit, without comments. |
| `--review REVIEW` | URL (`link`) | Review link of the unit: the one where the client comments. |

`link` needs at least one of `--content-id`, `--preview` and `--review` (exit code 2 without any).

Each backend refuses the actions of the other, with exit code 1 and before the unit is read:

```
PWD is assembled with the html backend: `plan` is for the creator backend; use `coursekit assemble build`
PWD is assembled with the 'creator' backend: `build` is for the html backend (project.yaml › assembly.backend or course.yaml › assembly.backend)
```

The first is the answer to `plan`, `diff`, `applied` or `link` on a course of the html backend; the second, to `build` on a course of the creator backend.

Actions of the creator backend:

- `plan`: converts `content.md` and `assessment.md` into the plan of lessons and bricks and writes `courses/<CODE>/assembly/unit-NN.plan.json`. The same Markdown always gives the same plan. Prints warnings and errors and `plan assembly/unit-NN.plan.json: N lessons, M bricks (types)`. With errors it writes nothing and exits with code 1. The keys and words of the directives are those of the course language (`question:` in an English course, `pregunta:` in a Spanish one); a key of the other language is an error that names its language and lists the valid keys ([08-assembly-and-delivery.md](08-assembly-and-delivery.md#what-the-plan-contains)).
- `diff`: prints, as JSON, the operations that bring creator in line with the plan: per lesson `create`, `update`, `unchanged` or `delete`, with the `add`, `update`, `delete`, `rename_lesson` and `update_quiz` operations. Needs the plan.
- `applied`: records what is now in creator (`unit-NN.applied.json`): a lesson with `--lesson`, `--lesson-id` and `--brick-ids`, or the content title with `--content`. Exit code 2 when `--lesson` and `--lesson-id` are missing and `--content` is not given. When every unit is in sync with its plan and the course is in `media`, the course moves to `assembly`.
- `link`: stores the creator content id in `course.yaml › units[N].content_id`, and the preview and review links in `course.yaml › units[N].links` (`preview`, `review`). The links survive [`coursekit sync`](#coursekit-sync) and feed the client's review (`coursekit client send`) and the catalog. Each option given replaces the previous value; the ones not given are kept.

Action of the html backend:

- `build`: builds each unit (the one in `--unit`, or every unit in order) into `courses/<CODE>/assembly/html/unit-NN/`, a folder that opens from the disk in a browser (`index.html`, `assets/styles.css`, the bundled player `assets/player.js`, the produced media in `media/` and `imsmanifest.xml`). The folder is rebuilt from scratch every time and the project `.gitignore` ignores it (`courses/*/assembly/html/`). The content is the same `content.md` and `assessment.md` the creator backend reads, converted to the same plan, with the media that are `produced` (or `uploaded`) copied into the package. The styles are the base layout of the package, the tokens of the course, `theme/maqueta.css`, `courses/<CODE>/theme/maqueta.css` and `components/*.css`; the player bundles `components/*.js` of the project ([04-configuration.md](04-configuration.md#files-of-the-html-backend)). The SCORM standard comes from `delivery.yaml › export.standard` and the quiz settings (passing score, attempts) from the course. With `--version X.Y` it also writes the zip `courses/<CODE>/delivery/<name from delivery.yaml › file_name>` (for example `PWD-U01-v1.0-scorm12.zip`, the name `coursekit delivery name` prints), with `imsmanifest.xml` first at its root, ready for `coursekit delivery add`. The first build prepares the builder (`npm install` of `@studiolxd/scorm` and `esbuild` in the store) if `coursekit setup` has not done it yet. When every unit of the course has been built and the course is in `media`, it moves to `assembly` and prints `every unit is built: the course moves to assembly`.

Output of `build`, per unit: the warnings (`WARNING …`: for example a produced asset whose file does not exist, or the image of a labelled graphic that is not produced yet; a placeholder without a produced file stays in the page as a visible note), then `unit N: F files in courses/<CODE>/assembly/html/unit-NN` and either `package <name> (<size>)` with `--version` or `preview: open courses/<CODE>/assembly/html/unit-NN/index.html in the browser` without it. Without an LMS the preview keeps the learner's state only in memory.

`build` stops at the first unit that cannot be built (exit code 1, the problems on stderr after `coursekit:`, one per line) and nothing is packaged for it. The problems are:

- The errors of the plan, the same `coursekit assemble plan` gives (a directive key in the wrong language, a question without options, and so on).
- `<lesson>: <BRICK>: this component is not available in the html backend yet (the games come in a later delivery)`, for each directive the backend cannot render yet (the games). `coursekit verify` reports the same.
- `the package does not contain N word(s) of the content: …`: the build compares the words the learner reads in `content.md` and `assessment.md` with the words of the page, and a line the format does not render (for example a question without its `question:` key) shows up here. Fix the Markdown, never the output.
- ``the builder could not be prepared (npm install of @studiolxd/scorm and esbuild): check Node and npm with `coursekit doctor` ``, when `npm` is missing or the install fails.
- `esbuild failed to bundle the player: …`, with the first part of the output of esbuild (for example an error in a file of `components/*.js`).

Exit codes: `0` when every unit was built; `1` for the problems above, for a unit that does not exist, for an action refused by the backend or for a course on hold; `2` for `plan`, `diff`, `applied` or `link` without `--unit`, and for `applied` or `link` without their options.

```
coursekit assemble plan PWD --unit 1
coursekit assemble build PWD --unit 1
coursekit assemble build PWD --version 1.0
```

### `coursekit directives`

Compares the directive registry (`coursekit config directives`) with the creator brick catalog. Use it to find out whether creator added or removed brick types. Who: agents (the assembly agent, via `/sync-directives`) and people.

```
coursekit directives {check} file
```

| Argument | Values / default | Meaning |
|---|---|---|
| `action` | `check` | The only action. |
| `file` | path | JSON saved from the creator tool `list_brick_types` (for example `.cache/list_brick_types.json`). |

Prints `NEW <brick> [category] <when to use>` for each creator brick that is neither a directive nor listed in `not_directives`, and `REMOVED <brick> ...` for each registry entry whose brick no longer exists. Prints `ok: the directive registry matches creator (N bricks)` and exits with 0 when there are no differences; otherwise exit code 1. If `FILE` does not exist or is not a `list_brick_types` result, it stops with a message and exit code 1.

```
coursekit directives check .cache/list_brick_types.json
```

### `coursekit delivery`

Checks that a course can be delivered, records a delivered SCORM package in `course.yaml › deliveries`, or prints the file name a package must have. Who: agents (the assembly agent) and people.

```
coursekit delivery [--file FILE] [--job JOB] [--snapshot SNAPSHOT] [--unit UNIT] [--version VERSION] {add,name,check} code
```

| Argument | Values / default | Meaning |
|---|---|---|
| `action` | `add`, `name`, `check` | Record a package, print the expected file name, or check that the course can be delivered. |
| `code` | course code or folder | Course. |
| `--unit UNIT` | unit number (required by `add` and `name`) | Unit of the package. |
| `--version VERSION` | text (required by `add` and `name`), for example `1.0` | Delivery version. |
| `--file FILE` | path (`add`) | The downloaded `.zip`; a relative path is taken from the current folder. It must be directly inside `courses/<CODE>/delivery/`. Exit code 2 without it. |
| `--job JOB` | text (`add`) | Id of the creator export job. Not used with the html backend. |
| `--snapshot SNAPSHOT` | text (`add`) | Id of the creator snapshot the package was exported from. Not used with the html backend. |

With the html backend the package is not exported from a platform: `coursekit assemble build CODE --unit N --version X.Y` writes it in `courses/<CODE>/delivery/` with the name that `name` prints, and `add` records it without `--job` or `--snapshot`.

`check` prints that the course can be delivered, or refuses with the reason (exit code 1); when the course is in a status where delivery does not normally start (for example `media`) it prints a warning instead and exits with 0. `name` and `add` refuse in the same cases, before doing anything: the course is on hold, or the client's review is required and not approved. `add` and `name` without `--unit` or `--version` exit with code 2.

The client's review is required when `delivery.yaml › client_review.required` is `true` (default `false`; it can be overridden for the whole project in `config/delivery.yaml` and per course in `course.yaml › delivery`). Then the course needs at least one round in `course.yaml › client_review` and the last one must be `approved` or `skipped`; the message says whether no round was opened, the client asked for changes, or the client has not answered yet. See [`coursekit client`](#coursekit-client).

`name` builds the name from `delivery › file_name` (default `{code}-U{unit:02d}-v{version}-{standard}.zip`, for example `PWD-U01-v1.0-scorm12.zip`). `add` checks that the file is a valid zip with `imsmanifest.xml` at its root and lives in the delivery folder, then records version, unit, date, signer, standard, file name, SHA-256, job and snapshot. A valid package is always recorded. When every unit has a package of the same version and the course was in `assembly` or `client_review`, the course becomes `delivered`; if units are missing it prints the ones still pending. In any other status (for example `media`) the package is recorded and a warning says the course is not marked as delivered. Exit code 1 on an invalid package, a wrong folder, an unknown unit, a course on hold or a client's review still required.

```
coursekit delivery check PWD
coursekit delivery add PWD --unit 1 --version 1.0 --file courses/PWD/delivery/PWD-U01-v1.0-scorm12.zip --job job-123 --snapshot snap-9
```

### `coursekit publish`

Mirrors the courses to the shared folder and writes the catalog there. The mirror is a read-only copy of git: anything edited in it is overwritten on the next publication. Who: both (also run by git hooks).

```
coursekit publish [--check] [--only-if-configured] [code]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `code` | course code; default: every course | Publish only that course. Exit code 1 if it does not exist. |
| `--check` | flag | Only report the mirror configuration: provider, folder, whether links can be built. Copies nothing; exit code 0. |
| `--only-if-configured` | flag | Do nothing, silently and with exit code 0, when there is no mirror (provider `none` or `MIRROR_DIR` not set), for git hooks. A `MIRROR_DIR` that points to a folder that does not exist still fails with exit code 1. |

The mirror is `project.yaml › mirror` (provider and web address) plus `MIRROR_DIR` in `.env` (local path). Per course it copies `course.yaml`, `design/`, `content/`, `reviews/` and `delivery/` to `<MIRROR_DIR>/courses/<CODE>/`, only when the content changed, removes files that no longer exist in git (tracked in `.published.json`), and never deletes `delivery/` packages. Then writes the catalog Excel in the root of the mirror. Prints one line per course that changed and the line of the catalog written in the mirror. With `mirror.provider: none` it prints `no mirror folder (project.yaml › mirror.provider: none): nothing to publish` and exits with 0, because the commands of the agents call it in every project. With a provider but no `MIRROR_DIR`, or with a folder that does not exist, it exits with code 1.

Before touching the mirror it also refreshes the catalog of the project in `courses/` (the same as `coursekit catalog`; it prints its `wrote courses/... (N courses, M units)` line first, except with `--only-if-configured`), so it works in projects without a mirror too.

You rarely need to run it yourself: when the project has a mirror folder, the commands that change a course publish it when they finish (see [Automatic publication](08-assembly-and-delivery.md#automatic-publication)).

```
coursekit publish PWD
```

### `coursekit catalog`

Writes the tracking Excel of every course (sheets Courses, Units and About), built from every `courses/*/course.yaml`. The Units sheet has, per unit, the creator content id and the Preview and Review links as hyperlinks (from `course.yaml › units[N].links`). It is a generated file: never edit it by hand. Who: both.

```
coursekit catalog [--output OUTPUT]
```

| Argument | Values / default | Meaning |
|---|---|---|
| `--output OUTPUT` | path; default `courses/course-catalog.xlsx` in an English project and `courses/catalogo-cursos.xlsx` otherwise (the language is `ui_language`, else `content_language`) | File to write. |

Prints `wrote <path> (N courses, M units)`. `coursekit publish` writes the same catalog in the mirror folder.

```
coursekit catalog --output build/catalog.xlsx
```

## Slash commands and the CLI they use

The slash commands live in `src/coursekit/agentkit/commands/` and are generated into each AI tool by `coursekit agents`. A person types them in the chat of their AI tool, or launches them from the terminal with `coursekit run <name> <arguments>`. The agent of the listed role executes them. The agents never sign or record the client's decisions: `/approve-design` and `/approve-unit` only prepare the sign-off, and `coursekit client`, `coursekit hold` and `coursekit resume` are for people.

| Slash command | CLI it uses | Role | Who may run it |
|---|---|---|---|
| `/new-course "<title>" <hours> [--code ABC101] [--no-intro] [--no-summary] [--no-material] [notes]` | `coursekit new`, `coursekit brief`, `coursekit theme show` | `design` | People, from the AI tool or `coursekit run new-course`. The agent never signs or commits. If the course already exists (handoff creates it first), it skips `coursekit new` and designs on it. When the project has no theme tokens, its summary tells the person to run `/define-theme`. If there is no material the agent asks before designing (unless `--no-material`) and, if you go on without it, marks the syllabus as an assumption. |
| `/design-change <CODE> <changes>` | `coursekit brief`, `coursekit publish` | `design` | People. The design is applied in slxd; a signed design must be signed again. |
| `/approve-design <CODE>` | `coursekit sync --check`, `coursekit publish`; the person then runs `coursekit approve design <CODE> --yes` | `design` | The agent prepares it; only a person signs. |
| `/define-theme [CODE]` | `coursekit theme show`, `coursekit theme import` | `design` | People, or the design agent. With the creator backend it chooses or adapts the theme in the platform, saves `get_theme` to `.cache/theme/get_theme.json` and derives the tokens. With the html backend there is no platform theme: it writes or adapts `theme/maqueta.css` and runs `coursekit theme import theme/maqueta.css`. Without a code it defines the project theme; with one, the own theme of that course. Never edits `tokens.json` by hand. |
| `/write-unit <CODE> [N]` | `coursekit status`, `coursekit verify`, `coursekit outline`; launched by `coursekit write` | `writer` | People (`coursekit write`) or the agent of that role. Never `coursekit approve`. |
| `/review-unit <CODE> <N>` | `coursekit verify`, `coursekit brief`, `coursekit outline`, `coursekit reviewed`; launched by `coursekit review` | `reviewer` | People (`coursekit review`) or the agent of that role. |
| `/approve-unit <CODE> <N>` | `coursekit verify`; the person then runs `coursekit approve content <CODE> --unit <N> --yes` | `reviewer` | The agent prepares it; only a person signs. |
| `/produce-media <CODE> [asset id]` | `coursekit media extract`, `coursekit media plan`, `coursekit media set`, `coursekit voice`, `coursekit tts`, `coursekit subtitles`, `coursekit theme show` | `media` | People, or the media agent. It tells the person what it will produce before spending paid-API credits. If the tokens are missing or were not derived from the platform theme, it stops and tells the person to run `/define-theme`. |
| `/assemble <CODE> [N]` | creator: `coursekit assemble plan`, `diff`, `applied`, `link`, `coursekit theme show`; html: `coursekit assemble build`, `coursekit theme show` | `assembly` | People, or the assembly agent. Needs the design signed and the units `approved`. It loads the `creator-assembly` or the `html-assembly` skill according to the backend of the course. With creator it applies the theme to the contents with `set_content_theme`, using the id that `coursekit theme show --course <CODE>` gives; with html it builds the preview of each unit (`assembly/html/unit-NN/`) and tells the person what to check in it. |
| `/client-feedback <CODE> [N]` | `coursekit outline`, `coursekit verify`, `coursekit assemble plan`, `diff`, `applied` | `assembly` | People, or the assembly agent. Reads the client's comments from creator, applies the agreed changes in the `.md`, reloads, publishes a new review version and answers each comment. Never runs `coursekit client`: the person records the round. |
| `/deliver <CODE> [version]` | `coursekit delivery check`, `coursekit config delivery`, `coursekit delivery name`, `coursekit delivery add`; html: `coursekit assemble build` | `assembly` | People, or the assembly agent. Refused while the course is on hold or the required client's review is missing. With the html backend there is no export in a platform: for each unit it runs `coursekit assemble build <CODE> --unit N --version X.Y` and then `coursekit delivery add` without `--job` or `--snapshot`. |
| `/course-status [CODE]` | `coursekit status` | `design` | Anyone. |
| `/sync-directives` | `coursekit directives check`, `coursekit config directives` | `assembly` | People, or the assembly agent. |

Next: [04-configuration.md](04-configuration.md)
