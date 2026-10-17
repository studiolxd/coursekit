# AGENTS.md — coursekit (development)

Instructions for any coding agent (Claude Code, opencode, Codex) working on the coursekit package
itself. The instructions that coursekit generates for course projects live in
`src/coursekit/templates/project/AGENTS.md`, not here.

## Read first

- `docs/` (English and Spanish): how each part works and how it is used; it is the reference for the design of the package. `README.md` has the status of the project and what is not done yet.
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
- coursekit is a product of Studio LXD: its own interface (the pages it serves to people, such as the
  video gallery) carries the brand of Studio LXD, through its design system `@studiolxd/brand` (a
  pinned dependency of the Remotion workspace). What a project makes (its videos, its resources)
  carries the brand of that project, never Studio LXD's. The rules above still hold for clients and
  real projects.

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
  every language file (`tests/test_content_words.py` checks it). The defaults and their texts are in English. The exception
  are the simulations (`:::scenario`, `:::conversation`, `coursekit/simulation.py`): their body is YAML with a fixed schema
  in English and conditions in code syntax, the same in every language; only their texts are in the course language.

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
- `README.md` / `README.es.md` carry the status of the project (what is solid, what is new, what is not done) and
  `docs/*/08-assembly-and-delivery.md` the known limits of the creator platform: update them when something changes.
- Development notes (the plan of a feature in progress, its open decisions) go in `dev-notes/<feature>.md`, in Spanish
  (Spain), under the same public-repository rules. They are working material, not documentation: once the feature is
  validated and published, what lasts is in `docs/` and the READMEs and its note is deleted. No maintainers' notes anywhere
  else in the repository.
- Skills, commands and agents are edited only in `src/coursekit/agentkit/`; every `{{token}}` must
  exist in `agents.context()` (a test fails otherwise).
- The PyPI distribution is `slxd-coursekit` (the package and the command stay `coursekit`). The PyPI
  name `coursekit` belongs to an unrelated project: check published versions at
  `https://pypi.org/pypi/slxd-coursekit/json`.
- Do not commit or push unless the maintainer asks. Never force-push without explicit permission.
- No emojis anywhere (only `★ ✔ ✘ · — ‹ ›`).
- Do not install software on the maintainer's machine; say what to run.
