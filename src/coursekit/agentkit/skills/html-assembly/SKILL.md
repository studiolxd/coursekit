---
name: html-assembly
description: Assembly of a course with the html backend — each unit becomes a SCORM package of its own (page, components, player and manifest) built by `coursekit assemble build` from the content.md/assessment.md, with no platform in between. Use with /assemble when the course is assembled with the html backend, or to rebuild a unit.
---

# Assembly with the html backend

The `.md` rules: never edit the package by hand; if something is wrong, fix the `.md` and build again. The build reads the same
files, the same directives and the same produced media as the creator backend, but its result is a folder (`assembly/html/unit-NN/`)
and a zip per unit (`delivery/`), not blocks in a platform. `coursekit status <CODE>` says which backend the course uses
(`Assembly: html backend`); with the creator backend use the `creator-assembly` skill instead.

## Requirements

- Signed design (`coursekit status <CODE>`) and signed units (`approved`). Build unsigned units only if the person asks (a preview).
- Design tokens of the project (`coursekit theme show --course <CODE>`): the package uses the colours and fonts of the theme. If
  there are none, tell the person about `/define-theme` (for this backend it derives them from the stylesheet `theme/maqueta.css`);
  without it the package uses the neutral layout of coursekit.
- The produced media: for this backend a produced asset is final, there is no upload. Make sure the assets that are `produced` have
  their file (`coursekit media set … --status produced --file media/files/<id>.<ext>`); the build copies them into the package.
  An asset that is not produced stays as a visible note with its description.

## 1. Build

For each unit, in order: `coursekit assemble build <CODE> --unit N` (without `--unit`, every unit). It prints the folder of the preview.

- Errors name the lesson and the directive (a key written in the wrong language, a directive that is not available yet — the games
  are not in the html backend, a question without options…). Fix them in the `.md`, never in the output, and build again.
- The build also checks that the package carries every word of the content: a line of the `.md` that the format does not render
  (for example a question without its `pregunta:`/`question:` key) is reported as missing words.
- Warnings (a labelled-graphic whose image is not produced, a produced asset without a file) are shown to the person.

## 2. Look at it

The preview opens from the disk: `assembly/html/unit-NN/index.html` in a browser (without an LMS it keeps its state only in
memory). Check, and tell the person to check, at least: the navigation between lessons, one component of each kind used in the unit,
the practice questions (check and try again) and the test (submit, score, attempts).

## 3. Package

When the person wants the packages: `coursekit assemble build <CODE> --unit N --version X.Y` also writes
`delivery/<CODE>-UNN-vX.Y-<standard>.zip` (the name and the standard come from `coursekit config delivery`). Register it with
`coursekit delivery add` (see the `delivery` skill) after the client review, if the project requires one.

## 4. Summary

Units built, files and size of each package, warnings, what the person has to check, and the next step: the client review
(`coursekit client <CODE> send --where <link of the hosted package>` — the person uploads the zip to a test LMS or a server and
gives you the link) or `/deliver`.

Do not commit unless asked. The folder `assembly/html/` is generated: it is not versioned.
