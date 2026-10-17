---
description: Create a course from its title and hours and build the instructional design proposal (in slxd or in the project) for human review.
argument-hint: "\"<title>\" <hours> [--code ABC101] [--approach expository|decision-based] [--no-intro] [--no-summary] [--no-material] [indications]"
---

Create a new course and its instructional design **proposal**. Arguments from the person:

$ARGUMENTS

1. Separate the title (in quotes), the hours, the options `--code`, `--approach`, `--no-intro`, `--no-summary`,
   `--no-material` (only for you: do not pass it to `coursekit new`) and the rest as free indications. If the title or the hours are missing, ask for them and stop.
   The approach: `--approach expository` (each section explains, then practises and assesses) or
   `--approach decision-based` (each section opens with a simulation where the learner decides, and the explanation comes
   after). If `--approach` is not given and the course does not exist yet (step 2), **ask the person, in
   {{ui_language_name}}, which one they want** before creating it, describing both in one line each, and pass their
   answer. If the indications already make it clear (learning by deciding, practising first, scenarios or simulations
   point to `decision-based`), propose that one and ask them to confirm. If you cannot ask (non-interactive session,
   or the course already exists), leave the option out and the project default applies.
2. Run `coursekit new "<title>" <hours> [options] --notes "<indications>"`, unless `courses/<CODE>/course.yaml` already
   exists (the course was created before, for example in handoff mode): then skip this step and work on it as it is.
3. Run `coursekit brief <CODE>` and read `brief/index.md` and `brief/notes.md`. If there is no
   material (no documents, no web links, no notes beyond the template, in the course or in the
   project) and `--no-material` was not given, **stop before designing** and ask the person, in
   {{ui_language_name}}: they can drop files in `courses/<CODE>/brief/sources/` (or the project's
   `brief/sources/`), URLs in `brief/links.md` and indications in `brief/notes.md`, and say when
   it is there (then run `coursekit brief <CODE>` again), or tell you to go on without it. If you
   cannot ask (non-interactive session) or the person goes on without material, say in the final
   summary that the syllabus is an assumption and that `/design-change` redoes it with material.
4. Load the `instructional-design` skill and follow its **Proposal** section (and **Migrated courses** when `course.yaml › design.origin`
   is `import`: the course was created by `coursekit import` and the brief holds its converted packages; and **Reference
   documentation** when the subject is an application or a regulation) (and **Decision-based courses** when
   `course.yaml › design.approach` is `decision-based`).
5. Run `coursekit theme show`. If the project has no theme tokens, say in the summary that `/define-theme`
   must be run before producing media.
6. Finish with a short summary for the person, in {{ui_language_name}}: units with hours and
   objectives, decisions and assumptions to check, the questions of the proposal (step 12 of the skill, each with its
   options and your recommendation) asked to the person, where the Excel is (and, in a decision-based course, the story in
   two lines and where `design/story.md` is), and how to go on: changes
   with `/design-change <CODE> <changes>` and sign-off with `/approve-design <CODE>`.

Do not sign anything and do not commit.
