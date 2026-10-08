---
description: Write a unit of a course with a signed design (writer agent of WRITER_AGENT / WRITER_MODEL).
argument-hint: "<CODE> <N>"
agent: writer
---

Write the unit: $ARGUMENTS (course code and unit number). If they are missing, ask.

Load the `content-writing` skill and follow it. Before writing anything, check with
`coursekit status <CODE>` that the instructional design is signed; if not, stop and say so.

- You work on one unit only: `courses/<CODE>/content/unit-NN/`. Do not touch other units, nor
  `config/`, nor `project.yaml`.
- Write section by section and run `coursekit verify <CODE> --unit N` after each one. Do not go
  on with errors.
- {{language_name}}, {{address_rule}}, no emojis.
- If a fact cannot be verified, mark it with `<!-- VERIFICAR: … -->`; do not invent it.
- Do not commit or push, and never run `coursekit approve`.
