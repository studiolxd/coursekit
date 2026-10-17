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
   design Excel, `design/proposal-notes.md` and the whole unit. In a decision-based course (`design.approach`), also
   `design/story.md` and the paths report (`coursekit paths <CODE> --unit N`).
3. Reference material: `coursekit brief <CODE>`, then `brief/index.md` and `brief/notes.md` of the
   course and of the project. Check technical accuracy (criterion 1) against `brief/text/` and
   resolve the `<!-- VERIFICAR -->` with it; anything contradicting the material is **blocking**. For a mark the brief does
   not settle, `coursekit research <CODE> "<the fact>" --fact` (with no search provider, your own web search) and propose
   in the report the official source and what it says.
4. The sources the writer added to `brief/links.md` (after `<!-- added by the writer -->`; `brief/research-log.md` says
   which search found each): each one must be official and say what the content takes from it. One that is not is
   **blocking**: the content cannot rest on it and its line leaves `links.md`.

## Rubric

Assess each section with these criteria. Every finding has a severity: **blocking** (cannot
reach the learner), **improvement** (noticeably better quality) or **minor** (style, typos).

| # | Criterion | What to check |
|---|---|---|
| 1 | Technical accuracy | Facts, versions, commands, prices, regulations and names correct and current. Find and resolve the `<!-- VERIFICAR -->`. |
| 2 | Alignment | Each content section lets the learner reach its objective at the declared Bloom level; activities practise and assess **that** objective. |
| 3 | Coherence with the design | Titles, sections and activities match the matrix; nothing out of scope. |
| 4 | Depth | Developed prose, no padding or repetition to reach the minimum; concrete professional examples. |
| 5 | Activities | Match the design; unambiguous questions, plausible distractors, one right answer in single-choice, useful feedback pointing to the section. {{questions_per_objective}} questions per objective assessed by questionnaire. Each distractor is the common error its `‹id›` names (`design/misconceptions.yaml`), worded as the learner would think it, and the feedback explains why it is wrong; a distractor that is absurd or tagged with an error it does not represent is a finding. |
| 6 | Interactivity | Directive suited to the kind of content; no flat section. |
| 7 | Media | Necessary placeholders, well specified, with accessibility (captions, alt text). |
| 8 | Style | {{language_name}}, {{address_rule}}, tone of `course.yaml`, inclusive language, no emojis. Readable for a {{readability_audience}} audience (the readability warnings of `verify`: split long sentences, plainer words). The unit closes with a `:::reflection` that makes the learner look back and plan how to apply it, not a disguised quiz. |
| 9 | Continuity | No overlap with other units nor content the design keeps for a later one (`coursekit outline <CODE>`; to check an overlap, `--section U.S`); correct cross-references. |
| 10 | Simulations (decision-based courses, or any simulation) | Run `coursekit paths <CODE> --unit N` and read every path of `reviews/unit-NN-paths.md`, and its table of scenes (what the learner sees in each one: text, screen of the skin, characters): no empty or contradictory screen. Each section opens with its simulation; the situation is realistic for the audience; options are plausible (none obviously right, none absurd); consequences follow from the decisions and some are delayed; there is a way to recover; points reward what an expert would do; a decision with `error` is that common error and its feedback or the debriefing explains it; every debriefing explains without preaching; the explanation after it starts from what the learner lived through, the `:::if` branches fit their path and every `:::else` is neutral (it never assumes a decision: whoever has not played and creator read it); no text outside a simulation states what the learner did (the end of the story lives in the endings of the scored simulation); characters, world and tone match `design/story.md`. A path that makes no sense or an ending that teaches the wrong thing is **blocking**. |

## Migrated courses (`design.origin: import`)

Add a ninth criterion: **fidelity to the package**. Compare each section with the Markdown the package was converted to
(`brief/text/files/NN-….md`) and with `brief/import-report.md`:

- Nothing of the client's text, no interactive and no image is lost or silently reworded, except what `brief/notes.md` and
  `rules › forbidden` ask to remove or replace. A loss is **blocking**: restore it. Wording changed without a reason in the
  notes is an **improvement** (propose reverting it).
- Each interactive keeps its kind from the package (a tab set is not turned into an accordion).
- Everything the report flags is settled: iDevices imported as text, embedded video on a forbidden host (kept because its
  channel is official, replaced by an equivalent from an official channel, by a placeholder or removed; read
  `reviews/external-videos.md` and say in the report which proposals a person still has to check), images the package did not
  bring, forbidden terms.
- What the writer added (new objectives' practice, assessment questions) is declared as new in the writer's summary; if it is
  not, list it in the report so the person can see it.
- The sizes (`unit … falls short / runs over`) are warnings of `coursekit verify`: say in the report which units are
  affected and what would fix it; they do not block.

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
<!-- result: ready | ready_with_changes | not_ready -->

## Summary
## Findings
| # | Section | Criterion | Severity | Finding | Action (applied / proposed) |
## Changes applied
## Proposals awaiting a human decision
```

   The `<!-- result: … -->` line repeats the **Result** with one of its three values, as written there (untranslated,
   with underscores): tools read it. In the findings table, write the **Severity** as `blocking`, `minor` or
   `improvement` and start the **Action** with `applied` or `proposed`, untranslated too (then your words): the handoff
   gives the writer exactly the blocking findings that are not `applied`. Update it too when a partial review changes the Result.
3. Run `coursekit reviewed <CODE> <N>`: it verifies again and marks the unit as reviewed (if it
   fails, fix and repeat). Never edit statuses by hand. Never pass `--by` to it: that option records the review
   of a person.
4. Remind the person that, after their editorial review, they sign with `/approve-unit <CODE> <N>`.

Do not commit or push unless asked.
