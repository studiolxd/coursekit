---
description: Write one unit of a course with a signed design, or every unit still to write (writer agent of WRITER_AGENT / WRITER_MODEL).
argument-hint: "<CODE> [N]"
agent: writer
---

Write: $ARGUMENTS (course code and, optionally, a unit number). If the code is missing, ask.

Load the `content-writing` skill and follow it. Before writing anything, check with
`coursekit status <CODE>` that the instructional design is signed; if not, stop and say so.

- **With a unit number**, write that unit only.
- **Without a number**, write every unit still to write, in order: the ones whose status in
  `courses/<CODE>/course.yaml › units[].status` is `pending` or `writing`. Finish a unit completely
  (`coursekit verify <CODE> --unit N` passes and it is `verified`) before starting the next, and stop at
  the first one that does not verify, saying why. Between units give a one-line summary and go on without
  asking. Do not re-read the units you finished: for continuity use `coursekit outline <CODE>` and
  `coursekit outline <CODE> --section U.S`, as the skill says.
- You work on one unit at a time: `courses/<CODE>/content/unit-NN/`. Do not touch the other units, nor
  `config/`, nor `project.yaml`.
- Write section by section and run `coursekit verify <CODE> --unit N` after each one. Do not go
  on with errors.
- {{language_name}}, {{address_rule}}, no emojis.
- If a fact cannot be verified, mark it with `<!-- VERIFICAR: … -->`; do not invent it.
- Do not commit or push, and never run `coursekit approve`.
