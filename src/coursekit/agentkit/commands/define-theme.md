---
description: Define the theme of the project (or of one course) in the authoring platform and derive the design tokens for the media.
argument-hint: "[CODE]"
---

Theme definition: $ARGUMENTS (without a course code, the theme of the project; with one, the own theme of that course).

Load the `theme-definition` skill and follow it (it reads the brand material in `theme/branding/` and the project's choice,
`project.yaml › theme › source`). Never write or edit `tokens.json` by hand: it is derived from the
theme of the platform with `coursekit theme import`.
