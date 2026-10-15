---
description: Check a written unit for content that has become out of date (facts, versions, regulations, tools, dates) against current official sources, and propose the changes with their source.
argument-hint: "<CODE> <N> [--apply]"
agent: reviewer
---

Check the unit for out-of-date content: $ARGUMENTS (course code and unit number; `--apply` to write the changes).

Load the `content-update` skill and follow it. Without `--apply`, and when `update.mode` of the rules is not `apply`, you
change nothing in the unit: you only write the report. With `--apply` (or `update.mode: apply`) you write the changes the
skill allows and leave the rest as proposals. Never sign anything and do not commit.
