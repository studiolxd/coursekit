---
description: Check that a unit is ready for the editorial sign-off and tell the person how to sign it.
argument-hint: "<CODE> <N>"
---

Prepare the editorial approval of the unit: $ARGUMENTS (course code and unit number).

1. `coursekit verify <CODE> --unit <N>` without errors.
2. `courses/<CODE>/reviews/unit-NN-ai-review.md` exists and has no pending blocking findings.
3. Summarise the state (words, directives, placeholders, proposals awaiting a decision).
4. If all is well, tell the person to sign it themselves:

   `! coursekit approve content <CODE> --unit <N> --yes`

   **You cannot run that command.**
