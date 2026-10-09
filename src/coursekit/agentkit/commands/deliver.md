---
description: Export the SCORM packages of a course from slxd, record them in the course.
argument-hint: "<CODE> [version]"
---

Delivery of the course: $ARGUMENTS (code and, optionally, version).

Load the `delivery` skill and follow it unit by unit. First run `coursekit delivery check <CODE>`: if it
refuses, stop and tell the person why. With the html backend (`coursekit status <CODE>`) there is no export in a platform: the
steps for each unit are `coursekit assemble build <CODE> --unit N --version X.Y` and then `coursekit delivery add` without
`--job` or `--snapshot`; skip steps 1 to 4 below.
