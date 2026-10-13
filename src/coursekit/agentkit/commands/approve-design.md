---
description: Prepare the sign-off of a course's instructional design (refresh its export) and tell the person how to sign it.
argument-hint: "<CODE>"
---

Prepare the approval of the instructional design of course $ARGUMENTS.

1. Refresh the export. Design in slxd (`course.yaml › design.tool: slxd`): read the matrix with `design_matrix_get` and
   compare it with `courses/<CODE>/design/matrix.json`; if the person edited in slxd since the last export, export again
   (Excel, `matrix.json`, `validation.json`). Local design (`design.tool: local`): run `coursekit design <CODE>`, which
   exports `design/design.yaml` again (the person may have edited it).
2. Validation (`design_matrix_validate`, or what `coursekit design` printed): if there are errors, stop and explain them.
3. Run `coursekit sync <CODE> --check` and summarise what will be signed: units, hours, sections,
   objectives and minimum words, plus the warnings. In a decision-based course the story bible
   (`design/story.md`) is signed too: summarise its world, protagonist, cast and simulation map, and check that every
   objective is practised in a simulation of the map.
4. Tell the person that, if they agree, they sign it themselves by typing in this same chat:

   `! coursekit approve design <CODE> --yes`

   (or `coursekit approve design <CODE>` in their terminal). **You cannot run that command**: the
   signature belongs to the reviewer.
