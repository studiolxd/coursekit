---
description: AI review of a written unit (reviewer agent of REVIEWER_AGENT / REVIEWER_MODEL), with a report in reviews/.
argument-hint: "<CODE> <N>"
agent: reviewer
---

Review the unit: $ARGUMENTS (course code and unit number).

Load the `content-review` skill and follow it. If the message says PARTIAL REVIEW, follow its
"Partial review" section. The review should be done by a model other than the writer's: check
`written_with` of the unit in `courses/<CODE>/course.yaml`; if it matches the tool and model you
are running on, say so at the start and in the report, and go on with the review.
