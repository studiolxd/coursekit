---
description: Assemble a course or one unit: load it into slxd creator (only what changed) or build its SCORM package with the html backend.
argument-hint: "<CODE> [N]"
---

Assembly of: $ARGUMENTS (course code and, optionally, the unit).

The project assembles with the **{{backend}}** backend by default; `coursekit status <CODE>` says the one of the course (a course
may use the other). With `creator` load the `creator-assembly` skill; with `html` load the `html-assembly` skill. Follow it.
Without a unit number, process every unit in order.
