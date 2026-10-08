---
name: instructional-design
description: Proposal and changes of a course's instructional design in the slxd design matrix (MCP design_matrix_*), from its title and hours. Use with /new-course, /design-change and /approve-design, or to create, change, validate or export the design of courses/<CODE>.
---

# Instructional design in slxd

Tools: `.coursekit/docs/slxd-mcp.md`. Only `design_matrix_create`, `_get`, `_list`, `_validate`
and `_generate_course` are direct; the rest of `design_matrix_*` (competencies, objectives,
nodes, activities, `_export`…) go through `find_tools` → `tool_schema` → `run_tool`.

**Principle:** you make a **proposal**; the person reviews it, asks for changes and signs it.
Never sign (`coursekit approve` is forbidden to you) and never present the proposal as final.

{{> _slxd-tools}}

## Input

- `courses/<CODE>/course.yaml`: title, hours, `design.intro_section`, `design.summary_section`,
  `design.notes` (the person's indications), audience, level, tone.
- Reference material: run `coursekit brief <CODE>` and read the course `brief/index.md` and
  `brief/notes.md`, and the project ones (`brief/` at the root); open in `brief/text/` what you
  need for the syllabus (not the originals in `brief/sources/`, except images). Course notes
  prevail over project notes. Base competencies, objectives and sections on that material and
  cite the sources used in `proposal-notes.md`. If there is no material, propose a reasonable
  syllabus for the title and audience and **mark it as an assumption**.

## Before starting: directive registry up to date

Call `list_brick_types`, save the JSON in `.cache/list_brick_types.json` and run
`coursekit directives check .cache/list_brick_types.json`. If it is not `ok`, tell the person
that creator changed its catalog and that `/sync-directives` should run before writing (it does
not block the design proposal).

## Proposal (from /new-course)

Design in this order. The structure is **not fixed**: decide how many units, objectives and
sections the course needs, and justify it.

1. **Matrix.** `design_matrix_create` with `nombre`, `duracionHoras`, `patronEstructural`
   (`design.structure`; **it cannot be changed later**; `con_modulos` only for long courses with
   clear blocks), `palabrasPorHora: {{words_per_hour}}` ({{pages_per_hour}} pages per hour ×
   {{words_per_page}} words per page; never the tool default) and the profile
   (`publicoObjetivo`, `nivel`, `conocimientosPrevios`, `tono`, `contexto`). Save
   `slxd.matrix_id` in `course.yaml` as soon as you have it.
2. **Competencies** (`design_matrix_competencia_create`): the ones the course needs (usually
   {{competencies_per_course}}), as verb + object + context.
3. **Units and objectives.** Split the syllabus into units that make sense on their own. Each
   unit has the objectives its content needs (usually {{objectives_per_unit}}; fewer than 2 or
   more than 5 must be justified). Revised Bloom, **one observable verb**, `nivelBloom` coherent
   with the verb, linked to their competencies, progressing along the course.
4. **Sections** (`design_matrix_node_create`, type `apartado`) per unit, with real titles:
   - if `intro_section` is `true`, the **first** is "{{t_intro_title}}";
   - if `summary_section` is `true`, the **last** is "{{t_summary_title}}";
   - in between, the content sections the subject needs (one or several per objective);
     optionally an activities section if the practice is not integrated.
   - Subsections only if they add real structure.
5. **Links** (`design_matrix_node_link_objetivo`): each content section with the objectives it
   develops. Every objective is covered by at least one section.
6. **Activities** per unit: learning activities (`design_matrix_aa_create`, formative, not
   graded) to practise each objective, and assessment activities (`design_matrix_ae_create`)
   that give evidence of all of them. Instrument according to the Bloom level (the validator
   requires it: questionnaire up to *apply*; case study up to *evaluate*; portfolio/rubric for
   *create*). Grading: `design.grading` of `course.yaml`.
7. **Hours, last.** With the content defined, split the hours **by real load**: breadth, Bloom
   level (apply/analyse/evaluate need more time than remember), practice and activities. Never
   split evenly. `design_matrix_node_update_horas` on sections and units; the total must be
   exactly `design.hours`. Introduction and summary usually take {{intro_summary_hours}} h per
   unit. Each hour means {{words_per_hour}} minimum words.
8. **Validation.** `design_matrix_validate` until **0 errors**. Review every warning.
9. **Own pedagogical review** (without spending slxd credits): apply the "Self-review" rubric
   below and fix what you find before presenting the proposal.
10. **Export** (see "Export").
11. **Proposal notes** in `courses/<CODE>/design/proposal-notes.md` ({{ui_language_name}}):
    structure and why, hour split and criterion, assumptions (syllabus, audience, level),
    questions for the person, accepted validation warnings and why.

## Changes (from /design-change)

1. `design_matrix_get` for the current IDs and `updatedAt` (the person may have edited in
   slxd). Pass `expectedUpdatedAt` when the tool accepts it.
2. Apply exactly what was asked; if a change forces others (hours, links, activities), make
   them and explain them.
3. Validate again, self-review, export and update `proposal-notes.md` (a dated "Changes"
   section).
4. If the design was signed, say that the signature is no longer valid.

## Export (always the three together, so they match the same version)

1. `design_matrix_get` → save the JSON **as it is** in `courses/<CODE>/design/matrix.json`.
2. `design_matrix_validate` → `courses/<CODE>/design/validation.json`.
3. `design_matrix_export` → download the `downloadUrl` (expires in 24 h) to
   `courses/<CODE>/design/<CODE>-instructional-design.xlsx`. That is what the person reviews.
4. `coursekit sync <CODE> --check` to confirm the structure is understood and the hours add up.
5. `coursekit publish <CODE>` so the Excel is in the mirror folder.

## Self-review (rubric)

For each element, if there is a problem, fix it and note it in `proposal-notes.md`:
- **Competencies:** verb + object + context; broad (not a disguised objective); no vague verbs
  (understand, know); one idea.
- **Objectives:** observable, measurable verb; Bloom level coherent with the verb; one
  behaviour; achievable in the hours given.
- **Objective ↔ assessment activity:** the task asks for the behaviour of the verb (neither
  easier nor harder); the criterion measures it; the evidence is recorded.
- **Objective ↔ learning activity:** the activity lets the learner practise the behaviour
  (nothing passive for apply/analyse/evaluate/create).

## Fixed rules

- No emojis. Course language: {{language_name}}.
- Always keep the slxd IDs in `course.yaml › slxd`.
- Never edit `course.yaml › units` by hand: `coursekit sync` writes it after the approval.
