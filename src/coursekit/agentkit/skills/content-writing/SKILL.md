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
  `assessment.md`: {{questions_per_objective}} questions per objective assessed by questionnaire. Of each activity the
  learner sees **only** the instructions, its simulations and its question bank, exactly as written: they are for the
  learner, never notes for people ("this activity has no question bank…"). An activity that is only a scored simulation
  leaves its bank empty; the other subsections (objectives, development, marking, attempts) are for people.
- **Common errors** (`courses/<CODE>/design/misconceptions.yaml`, signed with the design): every error of the unit's
  objectives is put in front of the learner at least once in the unit, and explained. In `single-choice` and
  `multi-select`, each distractor is one of those errors and ends with its id, `- [ ] <option> ‹reuse›` (the learner
  never sees it), and the feedback says why it is wrong; in a simulation, a decision that represents one says so with
  `error: reuse` and its `feedback` or the debriefing explains it. `coursekit verify` fails when an error of the unit
  appears nowhere or an id is not in the file, and warns of distractors and decisions that lose points without one.
- **No emojis.** Only `{{allowed_symbols}}`.

## Decision-based courses

When `course.yaml › design.approach` is `decision-based` (read it before writing), the learner does not start by reading.
Read also the story bible `courses/<CODE>/design/story.md` (world, protagonist, cast, arc, **simulation map**) and the
simulation format in `.coursekit/docs/content-format.md` (section 2.1).

- **Every content section follows the cycle** {{decision_cycle}}:
  - *challenge*: the section **opens with the simulation** of the simulation map (`:::scenario` or `:::conversation`),
    with no text before it (headings and comments only). Its `objective` lists the objectives it practises; every objective
    of the unit is practised in some simulation.
  - *explanation*: any content (prose, tabs, labelled graphics, timelines, dialogs, media) that **starts from what the
    learner has just lived through**: name the situation, the decision and its consequence, then the principle behind
    it. Use `:::if` / `:::else` to speak to the path they took. The `:::else` branch is **neutral**: it is what reads
    whoever did not meet the condition, whoever has not finished the simulation yet and every learner in creator, so it
    never assumes a decision ("Whether you chose X or Y, …", not "You did not choose X, so …").
  - *practice*: interactive directives and questions on what was explained, as in any course.
  - *decide_again* (optional): a second, shorter simulation or a variant in a new situation; leave it out when the
    section has already practised enough.
  - *closing*: the key idea in one `> ` highlight or `:::highlight`, and the link to the next challenge of the story.
- **The end of the story** goes in the endings of the last scored simulation of the unit (or of the course), one per
  ending, coherent with what the learner did: it is the last thing they play, and the assessment comes after the summary.
  The summary keeps the key ideas and never states what the learner did ("you reported it in time", "you gave away no
  password"): they may have done the opposite.
- **Inside the story.** Use the world, the protagonist and the cast of the bible; a character not in the cast cannot
  appear (`coursekit verify` checks it). Keep their personality and way of speaking. Every unit moves the arc.
- **Writing a simulation:**
  - The situation first, in the second person, short and concrete: where you are, who is there, what is at stake.
  - Options are what real people do, including the common mistakes and the shortcuts under pressure; none obviously
    right, none absurd, similar length. Three is usual; hotspots when the decision is to notice something in the scene.
  - Consequences in the story, not "Correct!": what happens next. Make some appear later (state + `variants`, layers
    with `if`, conditional choices, `next`) and give paths to recover from a mistake.
  - `score` rewards the decisions an expert would take (and subtracts the harmful ones); a scored simulation must have a
    path that earns points. Give it `pass_requires` with the key behaviour of the objective (a state variable), and make
    the endings and the grades agree: a good ending passes, a bad one fails (`coursekit verify` checks both). `checkpoint: true` on the scenes worth trying again (rewind is {{simulation_rewind}}).
  - Every ending has a `debriefing`: what happened and why, what an expert would have done and the principle, without
    preaching or blaming.
  - When the situation happens on a screen (email, chat, call, web page), use a `skin` with its `screen`, and make
    noticing the signal the decision (`hotspots` with `target`). In the chat skins (`chat-workspace`, `messenger`, `phone`)
    the `messages` of each scene **add up** along the path: write in each scene only the new messages. Any other screen
    shows what its scene says (or the simulation's `screen`), so give each scene the screen it needs. When the situation
    moves to another application (a chat message sends you to an email), give that scene its own `skin` and `screen`. A
    scene with a `background` happens in that place, not on the screen: give a background only to the scenes that happen
    away from the screen (Ramón's desk), and none to the scenes on the screen.
  - `background` and `layers.image` are **descriptions of the image** (what it shows, from the point of view of the
    learner); the media is produced from them, one image per description in the whole course, so repeat the exact same
    text when a scene reuses an image. Portraits come from the cast of the story bible (`look`) with the `expression` of
    each scene. In a scene with a background the characters stand in it, full size: give each one the `position`
    (`left`, `right`, `center`) that leaves free what matters in the background (the monitor, the sticky note). Do not add media placeholders for them.
  - Time: what is read on the longest path counts as words of the section (plus {{decision_seconds}} s per decision), so
    a simulation fills part of the section minimum, never more than the whole section. The scored simulations of
    `assessment.md` count in the activities section of the unit.
- After each simulation run `coursekit verify <CODE> --unit N` (it walks every path) and `coursekit paths <CODE> --unit N`,
  and read `reviews/unit-NN-paths.md`: play each path in your head and fix what does not make sense.

## Closing

1. `coursekit verify <CODE> --unit N` without errors (warnings justified).
2. Do not touch statuses: `coursekit verify` moves the unit and the course.
3. Summarise: words per section, directives used, placeholders and any pending
   `<!-- VERIFICAR -->`.

Do not commit or push unless asked.
