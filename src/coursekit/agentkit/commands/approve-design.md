---
description: Prepare the sign-off of a course's instructional design (refresh the export from slxd) and tell the person how to sign it.
argument-hint: "<CODE>"
---

Prepare the approval of the instructional design of course $ARGUMENTS.

1. Read the matrix with `design_matrix_get` and compare it with `courses/<CODE>/design/matrix.json`.
   If the person edited in slxd since the last export, export again (Excel, `matrix.json`,
   `validation.json`).
2. `design_matrix_validate`: if there are errors, stop and explain them.
3. Run `coursekit sync <CODE> --check` and summarise what will be signed: units, hours, sections,
   objectives and minimum words, plus the warnings.
4. Tell the person that, if they agree, they sign it themselves by typing in this same chat:

   `! coursekit approve design <CODE> --yes`

   (or `coursekit approve design <CODE>` in their terminal). **You cannot run that command**: the
   signature belongs to the reviewer.
