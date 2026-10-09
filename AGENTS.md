# AGENTS.md — coursekit (development)

Instructions for any coding agent (Claude Code, opencode, Codex) working on the coursekit package
itself. The instructions that coursekit generates for course projects live in
`src/coursekit/templates/project/AGENTS.md`, not here.

## Read first

- `dev/plan.md`: the plan, its phases and the state of each step (maintainers' notes, in Spanish; not user documentation).
- `CONTRIBUTING.md` (English) and `CONTRIBUTING.es.md` (Spanish): environment, tests, how to contribute; keep both in step.

## Public repository: nothing about clients or origin

- This repository is public. Never write the name of a client, a person, a tenant, an internal
  URL, a course of a real project or any data of a real project: not in code, tests, fixtures,
  docs, comments or commit messages.
- Never say or imply where coursekit comes from ("a previous pipeline", "the reference project",
  "migrated from", "as before"…). Write the package, its docs and its history as a standalone
  product.
- Examples and test fixtures are generic and invented (e.g. a course on strong passwords, client
  "ACME").

## Languages

- Code, identifiers, comments, file names, YAML keys, skills, commands and agents: **English**.
- CLI messages (output, errors, `--help`) speak the language of the person (`es` or `en`: `COURSEKIT_LANG`
  in the `.env`, else `project.yaml › ui_language`, else the system's). Never write one in Python: add it
  to `src/coursekit/lang/messages/<module>.yaml` with its `es` and `en` text and use
  `t("<module>", "<key>", value=...)` from `coursekit.i18n` (`tests/test_i18n.py` checks both languages
  and the `{values}`). The tests run with `COURSEKIT_LANG=en`.
- `docs/` is the user documentation, in **English** (`docs/en/`) and **Spanish (Spain)** (`docs/es/`) with the
  same files, and `README.md` / `README.es.md`. Commit messages and conversation with the maintainer:
  **Spanish (Spain)**.
- Course content formats are per language (`src/coursekit/lang/es.yaml`, `en.yaml`); never
  hard-code a content token (section heading, objective tag, placeholder) in Python. Resource types
  and the keys and words of the directives (`question:`, `answer: true`...) have an English **id** in the
  code, the configuration and the manifest (`image`, `infographic`...) and the word each language writes in
  `media_types`, `directive_keys` and `directive_words` of its `lang/<code>.yaml`: a new type or key is added to
  every language file (`tests/test_content_words.py` checks it). The defaults and their texts are in English.

## Working rules

- `uv sync --group dev`, then `uv run ruff check .` and `uv run pytest -q` before every commit;
  CI runs both on Linux, macOS and Windows (paths in messages with `as_posix()`; read git output as
  UTF-8).
- Production rules and numbers live in `src/coursekit/defaults/*.yaml` and reach skills as
  `{{tokens}}` (`coursekit agents`): never write a number in a skill.
- Every rule a project can override lives in `src/coursekit/defaults/<name>.yaml`, commented. `coursekit init`
  copies each file to the project as `config/<name>.example.yaml` (complete, with every value; not read;
  `init --update` refreshes it), so a new rule or a changed default reaches the examples by itself: just keep
  its comment up to date. A new configuration file needs its name in `config.NAMES` **and** `init.CONFIG_NAMES`
  (`tests/test_init.py` fails otherwise), and its documentation in `docs/en` and `docs/es`.
- Documentation travels with the change: a new or changed command, option, process, configuration or rule is
  documented in `docs/en` and `docs/es` (same files, same structure) in the same change.
  `tests/test_docs.py` checks that both trees have the same files, that links resolve, and that
  `docs/*/03-commands.md` mentions every command and every option of the CLI.
- Skills, commands and agents are edited only in `src/coursekit/agentkit/`; every `{{token}}` must
  exist in `agents.context()` (a test fails otherwise).
- Do not commit or push unless the maintainer asks. Never force-push without explicit permission.
- No emojis anywhere (only `★ ✔ ✘ · — ‹ ›`).
- Do not install software on the maintainer's machine; say what to run.
