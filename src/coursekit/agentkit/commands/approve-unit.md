---
description: Check that a unit is ready for the editorial sign-off and tell the person how to sign it.
argument-hint: "<CODE> <N>"
---

Prepare the editorial approval of the unit: $ARGUMENTS (course code and unit number).

1. `coursekit verify <CODE> --unit <N>` without errors.
2. How the unit was reviewed (`course.yaml › units[N].review.kind`): `ai` (or missing) means that
   `courses/<CODE>/reviews/unit-NN-ai-review.md` exists and has no pending blocking findings; `human` means that a
   person recorded their review (`by`, `note`, `report`: read them); `skipped` means that the project does not use AI
   review. Say which one it is in the summary.
3. Summarise the state (words, directives, placeholders, proposals awaiting a decision).
4. If all is well, tell the person to sign it themselves:

   `! coursekit approve content <CODE> --unit <N> --yes`

   **You cannot run that command.**
