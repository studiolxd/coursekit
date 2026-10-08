---
name: content-writing
description: Writing a unit's content (content.md and assessment.md) from its approved instructional design. Use to write, extend or fix content in courses/<CODE>/content/unit-NN.
---

# Writing a unit

Mandatory format: `.coursekit/docs/content-format.md`. Write in {{language_name}};
{{address_rule}}; tone: {{tone}}.

## Before writing

1. `coursekit status <CODE>`: the instructional design must be **signed** and unchanged since.
   If it is not, **stop**: nothing is written on an unsigned design.
2. Read `courses/<CODE>/course.yaml › units[N]`: title, hours, objectives (`id`, `bloom`,
   `text`), **sections** (`kind`, `title`, `hours`, `min_words`, `objectives`, `subsections`) and
   activities (`activities.learning` / `activities.assessment`). That is your specification: do
   not change sections, titles, objectives or activities.
3. Read the design Excel in `courses/<CODE>/design/` and `design/proposal-notes.md`.
4. Read the unit's `content.md`: it already has the `## {{t_section}} N` headings with their
   minimum words and a `<!-- kind … -->` comment with objectives and subsections. Replace the
   comment with the content.
5. Continuity without loading the whole course: `coursekit outline <CODE>` shows the design of
   every unit and what is already written. Use it not to repeat what an earlier unit covers nor
   to advance what the design keeps for a later one. To check how a topic was handled, read only
   that section with `coursekit outline <CODE> --section U.S`; do not read whole units.
6. Reference material: `coursekit brief <CODE>`, then `brief/index.md` and `brief/notes.md` of
   the course and of the project. Open in `brief/text/` only the pages for this unit. Facts,
   commands, options and product names come from there; whatever is not in the material and you
   cannot be sure of, mark it with `<!-- VERIFICAR: … -->`.

## How to write

- **Section by section**, in order. After each one run `coursekit verify <CODE> --unit N` and fix
  it before going on. Do not rewrite a verified section unless asked.
- Complete, explanatory prose: each concept is defined, exemplified and connected with the
  professional practice of the audience. No bare word lists or unexpanded outlines.
- Facts, versions, commands and product names **real and verifiable**. If unsure, do not invent
  it: mark it with `<!-- VERIFICAR: … -->` for the review.
- **Minimum words** are floors, never targets. Aim about {{word_margin_pct}} % above. Placeholder
  text, objective tags and comments **do not count**.
- By section `kind`:
  - `intro`: present the unit, its professional use, the objectives and how to study it.
  - `content`: develop **its** objectives (`sections[].objectives`) and close with one
    `*[{{t_objective}} UN.M — Verb]*` tag per objective covered, one per line. Include distinct
    interactive directives in proportion to its hours (verify tells you how many). **Only the
    directives of the registry** (`coursekit config directives`) are valid; choose each by its
    `use` for the kind of content (equivalent alternatives → tabs; sequence → timeline;
    equivalent items one by one → carousel; secondary detail → accordion; parts of a diagram →
    labelled-graphic…). Integrate the learning activities of its objectives with question
    directives.
  - `activities`: the unit's learning activities (`activities.learning`) with question
    directives, each with `{{t_question_key}}` and feedback that points back to the section.
  - `summary`: key ideas, glossary (`:::accordion` or `:::flashcards`) and link with the next
    unit.
- Media placeholders where an asset really adds something, with all their fields and
  accessibility; verify gives the minimum per unit (by hours) and of types.
- Assessment: present each activity of `activities.assessment` in the relevant section (what it
  assesses, how it is graded, attempts). The detail and the question bank go in
  `assessment.md`: {{questions_per_objective}} questions per objective assessed by questionnaire.
- **No emojis.** Only `{{allowed_symbols}}`.

## Closing

1. `coursekit verify <CODE> --unit N` without errors (warnings justified).
2. Do not touch statuses: `coursekit verify` moves the unit and the course.
3. Summarise: words per section, directives used, placeholders and any pending
   `<!-- VERIFICAR -->`.

Do not commit or push unless asked.
