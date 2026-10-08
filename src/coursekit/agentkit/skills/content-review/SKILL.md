---
name: content-review
description: Quality review (second layer, by the reviewer agent of the .env, other than the writer) of a written unit. Use to review content.md/assessment.md of courses/<CODE> and write reviews/unit-NN-ai-review.md.
---

# AI review of a unit

The reviewer should **not** be the model that wrote the unit: compare with `written_with` of the
unit in `course.yaml`; if it matches, say so in the report and carry on.

## Preparation

1. `coursekit verify <CODE> --unit N`: errors are fixed first (they are objective and cheap).
2. Read `course.yaml` (objectives, sections and activities of the unit, audience, level), the
   design Excel, `design/proposal-notes.md` and the whole unit.
3. Reference material: `coursekit brief <CODE>`, then `brief/index.md` and `brief/notes.md` of the
   course and of the project. Check technical accuracy (criterion 1) against `brief/text/` and
   resolve the `<!-- VERIFICAR -->` with it; anything contradicting the material is **blocking**.

## Rubric

Assess each section with these criteria. Every finding has a severity: **blocking** (cannot
reach the learner), **improvement** (noticeably better quality) or **minor** (style, typos).

| # | Criterion | What to check |
|---|---|---|
| 1 | Technical accuracy | Facts, versions, commands, prices, regulations and names correct and current. Find and resolve the `<!-- VERIFICAR -->`. |
| 2 | Alignment | Each content section lets the learner reach its objective at the declared Bloom level; activities practise and assess **that** objective. |
| 3 | Coherence with the design | Titles, sections and activities match the matrix; nothing out of scope. |
| 4 | Depth | Developed prose, no padding or repetition to reach the minimum; concrete professional examples. |
| 5 | Activities | Match the design; unambiguous questions, plausible distractors, one right answer in single-choice, useful feedback pointing to the section. {{questions_per_objective}} questions per objective assessed by questionnaire. |
| 6 | Interactivity | Directive suited to the kind of content; no flat section. |
| 7 | Media | Necessary placeholders, well specified, with accessibility (captions, alt text). |
| 8 | Style | {{language_name}}, {{address_rule}}, tone of `course.yaml`, inclusive language, no emojis. |
| 9 | Continuity | No overlap with other units nor content the design keeps for a later one (`coursekit outline <CODE>`; to check an overlap, `--section U.S`); correct cross-references. |

## Partial review

When the unit was already reviewed and only some parts changed (`coursekit review` computes
them against the previous review, or the person names them with `--parts`):

1. Apply the rubric **only** to those parts (sections of `content.md`, activities of
   `assessment.md`). Of the rest, read only what you need to check how they fit: the objective
   they develop, the neighbouring sections (continuity, cross-references) and the bank questions
   and activities of the same objective. Use `coursekit outline <CODE>` and `--section U.S`
   instead of reading the whole unit.
2. Do not reopen findings already resolved in parts that did not change.
3. Do not write a new report: **append** to `reviews/unit-NN-ai-review.md` a section
   `## Partial review — YYYY-MM-DD (<model>)` with the parts reviewed, the findings table and the
   changes applied, and update the **Result** in the header if it changes.
4. Finish as usual: `coursekit reviewed <CODE> <N>`.

## Output

1. **Apply directly** the blocking and minor fixes in the `.md`. Leave the improvements that
   change the approach as proposals in the report.
2. Write `courses/<CODE>/reviews/unit-NN-ai-review.md` (in {{ui_language_name}}):

```markdown
# AI review — <CODE> · Unit N
> **Reviewer:** <model> · **Date:** YYYY-MM-DD · **Result:** ready | ready with changes | not ready

## Summary
## Findings
| # | Section | Criterion | Severity | Finding | Action (applied / proposed) |
## Changes applied
## Proposals awaiting a human decision
```

3. Run `coursekit reviewed <CODE> <N>`: it verifies again and marks the unit as reviewed (if it
   fails, fix and repeat). Never edit statuses by hand.
4. Remind the person that, after their editorial review, they sign with `/approve-unit <CODE> <N>`.

Do not commit or push unless asked.
