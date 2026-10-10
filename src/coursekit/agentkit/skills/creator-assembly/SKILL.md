---
name: creator-assembly
description: Assembly of a course in slxd creator — skeleton from the matrix, content.md/assessment.md turned into bricks with `coursekit assemble` and applied by MCP incrementally, keeping the IDs. Use with /assemble or to load or reload content of courses/<CODE> into creator.
---

# Assembly in creator

The `.md` rules: never edit content directly in creator; if something is wrong, fix the `.md`
and reload it.

{{> _slxd-tools}}

## Requirements

- Signed design (`coursekit status <CODE>`) and signed units (`approved`). Assemble unsigned
  units only if the person asks explicitly (e.g. for a preview).
- `course.yaml › slxd.matrix_id` and, if any, `slxd.theme_id`.

## 1. Skeleton (first time only)

If a unit has no `content_id`:
1. `design_matrix_generate_course` with `alcance: {tipo: "curso"}` (or `{tipo: "modulo"}`). It
   creates one content per unit and one lesson per section, with skeleton bricks. Follow
   `design_matrix_redaccion_status` until it finishes.
2. `browse_workspace` / `get_content` to find each unit's content (folder named after the matrix)
   and `coursekit assemble link <CODE> --unit N --content-id <id>`.
3. The theme: `coursekit theme show --course <CODE>` gives the theme of the course (its own or the project's) in the
   `origin:` line, with its id: `set_content_theme` with that id on each content of the course. Without
   tokens from the platform there is no theme to apply: leave the default and tell the person about
   `/define-theme`.

The generator names each content after its **unit**. The plan gives the title it must have
(`content_title`): the course title when it has a single unit, otherwise
"{{t_unit}} N. <unit title>". Step 3 applies it.

## Theme of the contents (every run)

`coursekit theme show --course <CODE>` gives the id of the theme of the course. At the start of every run, also when the contents
already exist, `set_content_theme` with that id on each content of the course: setting it again does no harm and it is what makes
the contents follow a theme that was changed and imported again.

## 2. Plan and differences, per unit

1. `coursekit assemble plan <CODE> --unit N`: writes `assembly/unit-NN.plan.json`. Errors are
   fixed in the `.md` (never in the plan) and the command is run again.
2. `coursekit assemble diff <CODE> --unit N`: operations per lesson (`create`, `update`,
   `unchanged`, `delete`). Each `data` is the payload as it is for `add_brick`/`update_brick`.

## 3. Apply, per lesson

- Content title: if `diff` gives `content.action: rename`, `update_content` with
  `title: content.title` and record it with `coursekit assemble applied <CODE> --unit N --content`.
- **Before the first brick of a type**, `get_brick_type_schema` to confirm its shape.
- `create`: find the lesson the generator created for that section (`get_content`; same order
  and title; assessment lessons by the activity title). If it exists, delete its skeleton bricks
  (`get_lesson` + `delete_brick`); otherwise `create_lesson` (`type: content` or `evaluation`, in
  its position). Then `add_brick` for each op in order.
- `update`: apply the ops in order (`update_brick`, `delete_brick`, `add_brick` with `position`,
  `update_lesson` for `rename_lesson`, `update_quiz_settings` for `update_quiz`).
- Assessment lessons: `update_quiz_settings` with the plan's `quiz` as its `config` (`passingGrade`,
  `maxAttempts`, where 0 is unlimited, and `courseWeight`, the weight of the quiz among the quizzes of the unit).
- `delete`: **ask the person** before `delete_lesson`.
- After each lesson: `get_lesson`, take the brick IDs **in order** and record
  `coursekit assemble applied <CODE> --unit N --lesson <key> --lesson-id <id> --brick-ids id1,id2,…`.
  If the count does not match the plan, something was not applied: check before going on.
- Repeat `diff` until the content and every lesson are `unchanged`.
- **Never edit `assembly/*.json` by hand**: they are written by `coursekit assemble applied` (the permissions deny editing them). If
  the list of brick ids is too long for the command line, write the ids in a file (one per line or separated by commas) and
  use `--brick-ids-file <file>`; to record one replaced brick, record the whole lesson again with the ids that `get_lesson` gives.

## 4. Checks

1. `audit_content_accessibility` of each content; fix content issues in the `.md` (alt text,
   links) and use `apply_accessibility_autofix` only for technical ones.
2. `get_content_text` and compare with the `.md`: no text may be missing.
3. `create_snapshot` named `assembly-YYYY-MM-DD`.
4. Links of each unit, **only when the media is in place**: run `coursekit media extract <CODE>` and, if it counts assets that are
   not `uploaded` (`pending`, `scripted` or `produced`), the course still shows their placeholders: do not enable the review nor
   publish a review version yet, say that they will be created in the last assembly (the one after the media is uploaded) and skip
   this step. Otherwise (each unit is its own content, so each has its own links); the first time:
   - `share_content` (`enabled: true`, `liveUpdates: true`): the live preview, without comments.
   - `enable_review` (no password unless the person asks for one): the review link where the client
     comments; it publishes the first review version. Use `get_review` to read it again.
   - Record both: `coursekit assemble link <CODE> --unit N --preview <url> --review <url>`.
   When a unit is reloaded and its review is already enabled (after the client's comments, or because the media was uploaded
   after the first assembly), its review needs a new version so the client sees the changes: `publish_review_version` (see the
   `client-review` skill).
5. Summarise for the person: lessons and bricks created or updated, warnings (unproduced
   placeholders, pending labelled-graphic images), and the preview and review link of each unit.
   Tell them that, to open a round with the client, they run `coursekit client <CODE> send`.

`assembly/*.json` is versioned with the course: it is what allows reloading only what changes.
Do not commit unless asked.
