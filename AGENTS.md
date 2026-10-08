# AGENTS.md — coursekit (development)

Instructions for any coding agent (Claude Code, opencode, Codex) working on the coursekit package
itself. The instructions that coursekit generates for course projects live in
`src/coursekit/templates/project/AGENTS.md`, not here.

## Read first

- `docs/plan.md`: the plan, its phases and the state of each step.
- `CONTRIBUTING.md`: hooks, the private list of forbidden terms, environment.

## Public repository: nothing about clients or origin

- This repository is public. Never write the name of a client, a person, a tenant, an internal
  URL, a course of a real project or any data of a real project: not in code, tests, fixtures,
  docs, comments or commit messages.
- Never say or imply where coursekit comes from ("a previous pipeline", "the reference project",
  "migrated from", "as before"…). Write the package, its docs and its history as a standalone
  product.
- Examples and test fixtures are generic and invented (e.g. a course on strong passwords, client
  "ACME").
- `tools/check_terms.py` checks staged files (pre-commit) and the commit message (commit-msg)
  against a private list (`.forbidden-terms`, git-ignored; `FORBIDDEN_TERMS` secret in CI). Keep
  the hooks on: `git config core.hooksPath .githooks`. Never print the matched terms.

## Languages

- Code, identifiers, comments, file names, YAML keys, CLI messages, skills, commands and agents:
  **English**.
- `docs/` for people, commit messages and conversation with the maintainer: **Spanish (Spain)**.
- Course content formats are per language (`src/coursekit/lang/es.yaml`, `en.yaml`); never
  hard-code a content token (section heading, objective tag, placeholder) in Python.

## Working rules

- `uv sync --group dev`, then `uv run ruff check .` and `uv run pytest -q` before every commit;
  CI runs both on Linux, macOS and Windows (paths in messages with `as_posix()`; read git output as
  UTF-8).
- Production rules and numbers live in `src/coursekit/defaults/*.yaml` and reach skills as
  `{{tokens}}` (`coursekit agents`): never write a number in a skill.
- Skills, commands and agents are edited only in `src/coursekit/agentkit/`; every `{{token}}` must
  exist in `agents.context()` (a test fails otherwise).
- Do not commit or push unless the maintainer asks. Never force-push without explicit permission.
- No emojis anywhere (only `★ ✔ ✘ · — ‹ ›`).
- Do not install software on the maintainer's machine; say what to run.
