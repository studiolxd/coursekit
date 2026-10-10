# Contributing to coursekit

Español: [CONTRIBUTING.es.md](CONTRIBUTING.es.md)

## Welcome

coursekit (package `slxd-coursekit`, command `coursekit`) is a command-line tool that drives the production of AI-assisted e-learning courses: brief, instructional design, writing, review, media, assembly and SCORM delivery, with people signing off at every control point. See the [README](README.md) for the overview and the user documentation ([English](docs/en/index.md), [Español](docs/es/index.md)) for how it works from the user's side.

Contributions of any size are welcome: bug reports, fixes, documentation, translations and new features. This guide explains how to set up the project, what must pass before a change is ready and where things live.

The repository is public. Never include the name of a client, a person, a tenant, an internal URL or any data of a real project in code, tests, fixtures, docs, comments or commit messages. Examples and fixtures are generic and invented (for instance, a course on strong passwords for a client called "ACME").

## Set up the environment

You need Python 3.12 or 3.13 (`requires-python = ">=3.12,<3.14"`; `.python-version` pins 3.12) and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/studiolxd/coursekit
cd coursekit
uv sync --group dev
```

`uv sync --group dev` creates `.venv` and installs the package and the development tools (`pytest`, `ruff`). Run coursekit from the source tree, without installing it:

```bash
uv run coursekit --version
uv run coursekit help
```

To try it the way a user would, install it as a tool (CI does the same with `uv tool install .`) and work in a throwaway folder outside the repository:

```bash
uv tool install --editable .
mkdir -p ~/tmp/coursekit-try && cd ~/tmp/coursekit-try
coursekit init demo --yes --no-git --client ACME
cd demo
coursekit status
```

`--editable` makes the installed command follow your changes. When you are done: `uv tool uninstall slxd-coursekit`. If the shell does not find `coursekit` after installing, run `uv tool update-shell` and open a new terminal.

### Windows, macOS and Linux

CI runs on all three (see `.github/workflows/ci.yml`), so a change must work on all three:

- Paths shown in messages go through `Path.as_posix()`, so the output is the same everywhere.
- Read the output of `git` (and any other tool) as UTF-8.
- Files coursekit generates are written as UTF-8 with `\n` line endings (`write_text(..., encoding="utf-8", newline="\n")`).
- Build paths with `pathlib`, not by concatenating strings with `/` or `\`.

## Checks before every change

```bash
uv run ruff check .
uv run pytest -q
```

Both must pass; CI runs both (plus `uv tool install .` and `coursekit --version`) on Linux, macOS and Windows for every push to `main` and every pull request. Ruff is configured in `pyproject.toml`: line length 140, target Python 3.12, rules `E`, `F`, `I` (imports), `UP` and `B`. `uv run ruff check . --fix` fixes most import-order and style findings.

`tests/conftest.py` sets `COURSEKIT_LANG=en` for every test and restores the environment afterwards, so messages in tests are in English. A test that needs Spanish says so explicitly (`monkeypatch.setenv("COURSEKIT_LANG", "es")` or `i18n.use("es")`).

Besides the behaviour tests (`test_cli.py`, `test_course_flow.py`, `test_assemble.py`, `test_delivery.py`, `test_media.py`, `test_launch.py`, `test_setup.py`, `test_config.py`, ...), some tests guard the project's conventions and will fail if a change forgets a part:

| Test | What it checks |
|------|----------------|
| `tests/test_i18n.py` | Every message of `src/coursekit/lang/messages/*.yaml` exists in `es` and `en` with the same `{values}`; every `t("module", "key")` used in the code exists in its catalog and receives the values it needs; no emojis in the catalogs. |
| `tests/test_docs.py` | `docs/en` and `docs/es` have the same files and the same heading structure; links resolve; no emojis; `docs/*/03-commands.md` mentions every command and every option of the CLI; the two READMEs point to each other. |
| `tests/test_init.py` | `init.CONFIG_NAMES` equals `config.NAMES`; `config/<name>.example.yaml` is the complete package default of each configuration. |
| `tests/test_agents.py` | Every skill, command and agent is generated for every tool, with no `{{token}}` left unrendered. |

## Repository map

| Path | What is there |
|------|---------------|
| `src/coursekit/cli.py` | Entry point (`coursekit = "coursekit.cli:main"`): the parser, `init`, `config`, `rules`, `agents` and the top-level error handling. |
| `src/coursekit/commands.py` | The rest of the commands: `register(sub)` adds each sub-command and its options; `cmd_*` functions call the modules below. |
| `src/coursekit/project.py`, `envfile.py`, `config.py` | Finding the project, loading `.env`, and the layered configuration (package defaults, `config/`, `project.yaml`, `course.yaml`). |
| `src/coursekit/init.py`, `setup.py`, `doctor.py` | `coursekit init` (project scaffolding and the files it keeps up to date), `setup` (machine tools) and `doctor` (diagnosis). |
| `src/coursekit/course.py`, `new.py`, `sync.py`, `outline.py`, `status.py`, `states.py` | The course model, creating a course, syncing the approved design into the content skeleton, reading the design and the course status. |
| `src/coursekit/verify.py`, `approve.py`, `fingerprint.py`, `identity.py` | Checking content against the production rules, sign-offs and the fingerprints that detect later changes. |
| `src/coursekit/agents.py`, `launch.py` | Rendering skills, commands and agents for each AI tool (`context()` holds the `{{tokens}}`), and launching the tools. |
| `src/coursekit/brief.py`, `media.py`, `mediatools.py`, `voices.py`, `theme.py` | Brief conversion, media planning and production, voices and subtitles, theme tokens. |
| `src/coursekit/assemble.py`, `directives.py`, `delivery.py`, `publish.py`, `catalog.py` | Assembly into the authoring platform, directives, SCORM delivery, publishing and the course catalog. |
| `src/coursekit/i18n.py` | Messages for people: `t("module", "key", value=...)` and the choice of language. |
| `src/coursekit/lang/` | `es.yaml` and `en.yaml`: tokens of the course content format per language. `lang/messages/<module>.yaml`: the CLI message catalogs (`es` and `en`). |
| `src/coursekit/defaults/` | Package defaults, commented: `rules.yaml`, `directives.yaml`, `media.yaml`, `delivery.yaml` (overridable by a project) and `agents.yaml` (default tool and model per role). |
| `src/coursekit/agentkit/` | Source of the skills, commands, agents and reference docs generated into course projects. |
| `src/coursekit/templates/` | Files copied into projects and courses (`project/`, `course/`, `brief/`, `remotion/`). |
| `src/coursekit/tools/` | Helper scripts shipped with the package (`web2md.js`). |
| `tests/` | The test suite; `tests/fixtures/` holds invented data. |
| `docs/en/`, `docs/es/` | User documentation in English and Spanish (Spain), same files in both. |

## Conventions

- **Languages.** Code, identifiers, comments, file names, YAML keys, skills, commands and agents are in English. Messages for people (output, errors, `--help`) are never written in Python: they live in the catalogs, in Spanish and English. Documentation is written in both languages. Commit messages are written in Spanish (Spain), as in the existing history.
- **Content tokens.** The words of the course content format (section heading, objective tag, placeholder, ...) belong to `src/coursekit/lang/<code>.yaml`. Never hard-code one in Python.
- **No numbers in skills.** Production rules and numbers live in `src/coursekit/defaults/*.yaml` and reach skills as `{{tokens}}`.
- **No emojis** anywhere (code, docs, messages, commit messages). The only symbols allowed are `★ ✔ ✘ · — ‹ ›`.
- **Comments** explain why, not what; keep them short, in English, and update them with the code. The commented defaults in `src/coursekit/defaults/` double as user-facing documentation of each rule.
- **Examples and fixtures** are generic and invented. Never copy material from a real project, not even partially.
- **Standalone product.** Write code, docs and history as a product on its own; do not describe where coursekit or any of its parts come from.

## How to

### Add a command or an option

1. Put the logic in the module it belongs to (or a new module) and add a `cmd_<name>(args)` function in `src/coursekit/commands.py`. Commands about the project itself (`init`, `config`, `rules`, `agents`) are in `cli.py`.
2. Register the sub-command and its options in `register(sub)` (`commands.py`) or `build_parser()` (`cli.py`). Help texts are messages too: `help=t("commands", "help_<name>")`.
3. For errors the person can fix, raise the module's exception and make sure it is caught in `cli.main` (the exceptions listed in `commands.ERRORS`): it prints `coursekit: <message>` to stderr and exits with 1.
4. Add the messages (below) and a test; the CLI tests call `main([...])` from `coursekit.cli` and read output with `capsys`.
5. Document it in `docs/en/03-commands.md` and `docs/es/03-commands.md`: a `### \`coursekit <name>\`` section, the entry in the command tables and every option string. `tests/test_docs.py` fails if a command or an option is missing from either file.

### Add or change a message

Messages live in `src/coursekit/lang/messages/<module>.yaml`, one catalog per module, each key with both languages:

```yaml
created_env:
  es: "ok: .env creado"
  en: "ok: created .env"
```

Use it as `t("setup", "created_env")`; with values, `t("module", "key", path=...)` and `{path}` in both texts (a literal brace is written `{{`). Both texts must use the same `{values}`; `tests/test_i18n.py` checks it, and also that every key used in the code exists. A new module is a new `<module>.yaml` file in that folder.

### Add or change a production rule or a configuration file

A rule a project can override lives in `src/coursekit/defaults/<name>.yaml`, with a comment saying what it does. `coursekit init` copies each of those files to the project as `config/<name>.example.yaml` (complete, not read by coursekit; `init --update` refreshes it), so a new rule or a changed default reaches the examples by itself: just keep its comment up to date.

- A new rule inside an existing file: add the key with its default and comment, use it from the code through `config`, and document it in `docs/en/04-configuration.md` and `docs/es/04-configuration.md`. If a skill needs the value, add a token to `agents.context()` (see below).
- A new configuration file: create `defaults/<name>.yaml` and add its name to **both** `config.NAMES` (`src/coursekit/config.py`) and `init.CONFIG_NAMES` (`src/coursekit/init.py`); `tests/test_init.py` fails otherwise. Document it in both configuration pages and in `03-commands.md` if `coursekit config` should mention it.

### Edit skills, commands and agents

Edit them only in `src/coursekit/agentkit/` (`skills/<name>/SKILL.md`, `commands/<name>.md`, `agents/<name>.md`, `docs/`). Never edit the generated copies inside a course project. Every `{{token}}` you use must exist in `agents.context()` in `src/coursekit/agents.py`; an unknown token raises an error and `tests/test_agents.py` fails. Partials start with `_` and are included with `{{> _name}}`. To see the result, run `coursekit agents` in a throwaway project and read the generated files.

### Add a content language

The content format is per language. At least:

- `src/coursekit/lang/<code>.yaml` with all the tokens (copy `en.yaml`), including `media_types` (the word of each resource type id), `directive_keys` and `directive_words`, and the code added to `LANGUAGES` in `src/coursekit/lang/__init__.py`. A new resource type or directive key gets an id and a word in every language file (`tests/test_content_words.py` checks it).
- The code in `init.LANGUAGES` and its address forms in `init.ADDRESS`; its name in `agents.LANGUAGE_NAMES`; the default address in `agents.context()`.
- A course template: `src/coursekit/templates/course/<code>/` (`content.md`, `assessment.md`).
- Language-dependent defaults: `catalog.CATALOG_NAME` and its column texts, `setup.PIPER_DEFAULT`, `voices.LOCALES` and the default voices in `voices.py`.
- Documentation in both `docs/en` and `docs/es`, and tests.

The language of the interface (`ui_language`, `COURSEKIT_LANG`) is separate: it is `es` or `en` (`i18n.LANGUAGES`). Adding one means adding its text to every catalog entry, and `tests/test_i18n.py` requires all of them.

### Add documentation

User documentation lives in `docs/en/` and `docs/es/`, with the same file names and the same heading structure (numbers and levels). A new or changed command, option, process, configuration or rule is documented in both languages in the same change. Links are relative and must resolve; fenced code blocks are not checked, so keep commands in them accurate. If you add a page, add it to both trees and link it from `index.md`.

## Pull requests and commits

- Keep changes small and focused: one fix or feature per pull request, without unrelated reformatting.
- Code, tests and documentation travel together. A pull request that changes behaviour includes the test that covers it and the updates in `docs/en` and `docs/es`.
- Run `uv run ruff check .` and `uv run pytest -q` first. Check that the output reads well in both languages for anything a person sees (`COURSEKIT_LANG=es` and `COURSEKIT_LANG=en`).
- Commit messages are written in Spanish (Spain): a short first line saying what changes, then details if needed. Example: `Rutas con barras normales en los mensajes de error`.
- Do not force-push shared branches, and do not rewrite history that others have pulled.
- Do not commit generated or local files: `.venv/`, `dist/`, `build/`, caches and any `.env`.

## Releases

A tag `vX.Y.Z` that matches the version of `pyproject.toml` runs `.github/workflows/release.yml`: it checks, builds, attaches the wheel and the source distribution to a GitHub release and uploads to PyPI (trusted publishing: the `pypi` environment of the repository is the publisher registered on PyPI). To release: bump `version`, commit, `git tag vX.Y.Z`, `git push --tags`. Projects follow the installed version by themselves (the first command after an update regenerates their managed and agent files). The version is the `version` field in `pyproject.toml` (currently `0.1.3`); `coursekit --version` reads it from the installed package metadata and prints `0.0.0` when run from a checkout that is not installed. The package builds with hatchling:

```bash
uv build
```

which writes the source distribution and the wheel to `dist/` (ignored by git). Version bumps and releases are decided by the maintainers.

## Reporting problems

Open an issue in the [repository](https://github.com/studiolxd/coursekit). Include:

- The output of `coursekit --version`, and how you installed it (`uv tool install`, `uv run` from a checkout).
- Your operating system and version, and the Python version if you run from source.
- The exact command and its complete output (add `COURSEKIT_LANG=en` to get messages in English), plus the output of `coursekit doctor` when the problem is about the machine's tools.
- What you expected and what happened, and the smallest steps that reproduce it, ideally in a new project made with `coursekit init`.

Do not paste secrets or real course material: remove API keys, tokens, `.env` contents, URLs of internal systems and any text from a client's course. Replace them with invented examples.
